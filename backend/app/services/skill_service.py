"""
Database-Driven Canonical Skill Extraction & Gap Analysis Service.
Features:
- DB-backed canonical skill & alias mapping (PostgreSQL skills & skill_aliases)
- 3-Tier Hybrid extraction: Exact Alias -> Normalized Text -> Conservative Semantic Similarity (>= 0.78)
- Distinguishes REQUIRED vs PREFERRED skills from JD sections
- Labels missing skills objectively as 'Not evidenced in resume'
Conforms to RAG Skill Analysis specifications.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.skill import Skill, SkillAlias
from app.rag.embeddings import EmbeddingService
from app.core.logging import logger

class SkillMatchResult:
    def __init__(
        self,
        skill_id: str,
        canonical_name: str,
        category: str,
        confidence: float,
        evidence_text: Optional[str] = None,
        source_section: Optional[str] = None,
        required_or_desired: str = "REQUIRED",
        match_type: str = "EXACT_ALIAS" # "EXACT_ALIAS", "NORMALIZED", "SEMANTIC_SIMILARITY"
    ):
        self.skill_id = skill_id
        self.canonical_name = canonical_name
        self.category = category
        self.confidence = confidence
        self.evidence_text = evidence_text
        self.source_section = source_section
        self.required_or_desired = required_or_desired
        self.match_type = match_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "canonical_name": self.canonical_name,
            "category": self.category,
            "confidence": round(self.confidence, 3),
            "evidence_text": self.evidence_text,
            "source_section": self.source_section,
            "required_or_desired": self.required_or_desired,
            "match_type": self.match_type
        }

class SkillService:
    """Extracts canonical skills from document text using database taxonomy lookup and semantic vector matching."""

    @classmethod
    async def get_all_canonical_skills(cls, db: AsyncSession) -> List[Skill]:
        """Fetch all canonical skills from PostgreSQL with aliases loaded."""
        stmt = select(Skill).options(selectinload(Skill.aliases))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    def extract_skills_from_text(
        cls,
        text: str,
        canonical_skills: List[Skill],
        semantic_threshold: float = 0.78,
        section_hint: Optional[str] = None,
        default_required_or_desired: str = "REQUIRED"
    ) -> List[SkillMatchResult]:
        """
        3-tier hybrid skill extraction pipeline:
        1. Exact Alias Matching (word-boundary regex) -> 0.95-1.0 confidence
        2. Normalized Text Substring Matching -> 0.85-0.90 confidence
        3. Conservative Semantic Similarity (>= 0.78) -> 0.78-0.84 confidence
        """
        if not text or not text.strip():
            return []

        # Split text into sentences for exact evidence extraction
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        sentences = []
        for p in paragraphs:
            for s in re.split(r"(?<=[.!?])\s+", p):
                if s.strip():
                    sentences.append(s.strip())

        matched_results: Dict[str, SkillMatchResult] = {}
        lower_text = text.lower()

        # Step 1 & 2: Exact Alias & Normalized Matching
        for skill in canonical_skills:
            all_aliases = [skill.canonical_name] + [a.alias for a in skill.aliases]
            best_evidence = None
            highest_conf = 0.0
            match_type = "EXACT_ALIAS"

            for term in all_aliases:
                term_clean = term.strip().lower()
                if not term_clean:
                    continue

                # Whole word match to avoid false positive substring matches (e.g. "go" vs "good")
                pattern = r"\b" + re.escape(term_clean) + r"\b"
                if re.search(pattern, lower_text):
                    is_canonical = (term_clean == skill.canonical_name.lower())
                    highest_conf = 1.0 if is_canonical else 0.92
                    match_type = "EXACT_ALIAS" if is_canonical else "NORMALIZED"

                    # Locate sentence containing the term as evidence
                    for sent in sentences:
                        if re.search(pattern, sent.lower()):
                            best_evidence = sent[:250]
                            break
                    if best_evidence:
                        break

            if highest_conf > 0.0:
                matched_results[skill.id] = SkillMatchResult(
                    skill_id=skill.id,
                    canonical_name=skill.canonical_name,
                    category=skill.category,
                    confidence=highest_conf,
                    evidence_text=best_evidence or f"Explicitly identified in document: {skill.canonical_name}",
                    source_section=section_hint,
                    required_or_desired=default_required_or_desired,
                    match_type=match_type
                )

        # Step 3: Conservative Semantic Vector Matching for Unresolved Candidate Skills
        unmatched_skills = [s for s in canonical_skills if s.id not in matched_results and s.embedding]
        if unmatched_skills and sentences:
            # Embed top representative sentences from key sections
            sample_sentences = sentences[:35]
            sent_embeddings = EmbeddingService.embed_texts(sample_sentences)

            for skill in unmatched_skills:
                skill_vec = skill.embedding
                best_sim = 0.0
                best_sent = None

                for sent_text, sent_vec in zip(sample_sentences, sent_embeddings):
                    sim = EmbeddingService.cosine_similarity(skill_vec, sent_vec)
                    if sim > best_sim:
                        best_sim = sim
                        best_sent = sent_text

                # Strict conservative threshold (>= 0.78) to avoid spurious matches
                if best_sim >= semantic_threshold:
                    matched_results[skill.id] = SkillMatchResult(
                        skill_id=skill.id,
                        canonical_name=skill.canonical_name,
                        category=skill.category,
                        confidence=best_sim,
                        evidence_text=best_sent[:250] if best_sent else f"Semantically inferred from context ({round(best_sim, 2)})",
                        source_section=section_hint,
                        required_or_desired=default_required_or_desired,
                        match_type="SEMANTIC_SIMILARITY"
                    )

        return list(matched_results.values())

    @classmethod
    def compute_skill_gap(
        cls,
        resume_skills: List[SkillMatchResult],
        jd_skills: List[SkillMatchResult],
        preferred_jd_skills: Optional[List[SkillMatchResult]] = None
    ) -> Dict[str, Any]:
        """
        Compute Matched Skills, Missing Required Skills, Missing Preferred Skills, and Candidate Strengths.
        Labels missing skills accurately as 'Not evidenced in resume'.
        """
        resume_skill_ids = {s.skill_id: s for s in resume_skills}
        required_jd_map = {s.skill_id: s for s in jd_skills}
        preferred_jd_map = {s.skill_id: s for s in (preferred_jd_skills or [])}

        matched_skills = []
        missing_required_skills = []
        missing_preferred_skills = []
        resume_only_skills = []

        # 1. Evaluate Required JD Skills
        for s_id, jd_skill in required_jd_map.items():
            if s_id in resume_skill_ids:
                matched_item = jd_skill.to_dict()
                matched_item["evidence_in_resume"] = resume_skill_ids[s_id].evidence_text
                matched_skills.append(matched_item)
            else:
                missing_item = jd_skill.to_dict()
                missing_item["status"] = "Not evidenced in resume"
                missing_item["required_or_desired"] = "REQUIRED"
                missing_required_skills.append(missing_item)

        # 2. Evaluate Preferred JD Skills
        for s_id, pref_skill in preferred_jd_map.items():
            if s_id in resume_skill_ids:
                if s_id not in required_jd_map:
                    matched_item = pref_skill.to_dict()
                    matched_item["evidence_in_resume"] = resume_skill_ids[s_id].evidence_text
                    matched_skills.append(matched_item)
            else:
                if s_id not in required_jd_map:
                    missing_item = pref_skill.to_dict()
                    missing_item["status"] = "Not evidenced in resume"
                    missing_item["required_or_desired"] = "PREFERRED"
                    missing_preferred_skills.append(missing_item)

        # 3. Evaluate Candidate-only Strengths
        all_jd_skill_ids = set(required_jd_map.keys()).union(set(preferred_jd_map.keys()))
        for s_id, res_skill in resume_skill_ids.items():
            if s_id not in all_jd_skill_ids:
                resume_only_skills.append(res_skill.to_dict())

        total_required = len(required_jd_map)
        matched_required_count = sum(1 for s in matched_skills if s.get("required_or_desired") == "REQUIRED")
        
        match_percentage = round((matched_required_count / total_required) * 100.0, 1) if total_required > 0 else 100.0

        all_missing_jd = missing_required_skills + missing_preferred_skills

        return {
            "matched_skills": matched_skills,
            "missing_jd_skills": all_missing_jd,
            "missing_required_skills": missing_required_skills,
            "missing_preferred_skills": missing_preferred_skills,
            "resume_only_skills": resume_only_skills,
            "match_percentage": match_percentage
        }
