"""
Skill Identification, Semantic Extraction & Gap Analysis Service.
Matches Resume and JD against O*NET Canonical Skill Taxonomy with evidence spans and confidence scores.
Conforms to Blueprint Section 10.
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
        required_or_desired: str = "REQUIRED"
    ):
        self.skill_id = skill_id
        self.canonical_name = canonical_name
        self.category = category
        self.confidence = confidence
        self.evidence_text = evidence_text
        self.required_or_desired = required_or_desired

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "canonical_name": self.canonical_name,
            "category": self.category,
            "confidence": round(self.confidence, 3),
            "evidence_text": self.evidence_text,
            "required_or_desired": self.required_or_desired
        }

class SkillService:
    """Extracts canonical skills from document text using taxonomy lookup and semantic vector matching."""

    @classmethod
    async def get_all_canonical_skills(cls, db: AsyncSession) -> List[Skill]:
        """Fetch all canonical skills with aliases loaded."""
        stmt = select(Skill).options(selectinload(Skill.aliases))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    def extract_skills_from_text(
        cls,
        text: str,
        canonical_skills: List[Skill],
        semantic_threshold: float = 0.72
    ) -> List[SkillMatchResult]:
        """
        Extract canonical skills from text by combining exact alias matching and semantic similarity.
        Stores the sentence context as evidence text.
        """
        if not text:
            return []

        # Break text into sentences/paragraphs for evidence extraction
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        sentences = []
        for p in paragraphs:
            for s in re.split(r"(?<=[.!?])\s+", p):
                if s.strip():
                    sentences.append(s.strip())

        matched_results: Dict[str, SkillMatchResult] = {}
        lower_text = text.lower()

        # Step 1: Deterministic Alias Matching with word boundaries
        for skill in canonical_skills:
            all_terms = [skill.canonical_name] + [a.alias for a in skill.aliases]
            best_evidence = None
            highest_conf = 0.0

            for term in all_terms:
                term_clean = term.strip().lower()
                if not term_clean:
                    continue
                
                # Match whole words to avoid sub-word false positives (e.g. "go" vs "good")
                pattern = r"\b" + re.escape(term_clean) + r"\b"
                if re.search(pattern, lower_text):
                    highest_conf = max(highest_conf, 0.95 if term_clean == skill.canonical_name.lower() else 0.88)
                    # Find first sentence containing the term as evidence
                    for sent in sentences:
                        if re.search(pattern, sent.lower()):
                            best_evidence = sent[:300]
                            break
                    if best_evidence:
                        break

            if highest_conf > 0.0:
                matched_results[skill.id] = SkillMatchResult(
                    skill_id=skill.id,
                    canonical_name=skill.canonical_name,
                    category=skill.category,
                    confidence=highest_conf,
                    evidence_text=best_evidence or f"Mentioned: {skill.canonical_name}"
                )

        # Step 2: Semantic vector match for unmatched skills against text chunks
        # Only check skills that haven't matched yet
        unmatched_skills = [s for s in canonical_skills if s.id not in matched_results and s.embedding]
        if unmatched_skills and sentences:
            # Embed sample sentences from key sections
            sample_sentences = sentences[:30] # Top 30 sentences
            sent_embeddings = EmbeddingService.embed_batch(sample_sentences)

            for skill in unmatched_skills:
                skill_vec = skill.embedding
                best_sim = 0.0
                best_sent = None
                for sent_text, sent_vec in zip(sample_sentences, sent_embeddings):
                    sim = EmbeddingService.cosine_similarity(skill_vec, sent_vec)
                    if sim > best_sim:
                        best_sim = sim
                        best_sent = sent_text

                if best_sim >= semantic_threshold:
                    matched_results[skill.id] = SkillMatchResult(
                        skill_id=skill.id,
                        canonical_name=skill.canonical_name,
                        category=skill.category,
                        confidence=best_sim,
                        evidence_text=best_sent[:300] if best_sent else f"Semantically inferred ({round(best_sim, 2)})"
                    )

        return list(matched_results.values())

    @classmethod
    def compute_skill_gap(
        cls,
        resume_skills: List[SkillMatchResult],
        jd_skills: List[SkillMatchResult]
    ) -> Dict[str, Any]:
        """
        Compute Matched Skills, Missing JD Skills, and Resume-only Skills.
        Blueprint Section 10.
        """
        resume_skill_ids = {s.skill_id: s for s in resume_skills}
        jd_skill_ids = {s.skill_id: s for s in jd_skills}

        matched_skills = []
        missing_jd_skills = []
        resume_only_skills = []

        # Find JD skills present in Resume (Matched) vs Missing
        for s_id, jd_skill in jd_skill_ids.items():
            if s_id in resume_skill_ids:
                matched_skills.append(jd_skill.to_dict())
            else:
                missing_jd_skills.append(jd_skill.to_dict())

        # Find Resume skills not mentioned in JD
        for s_id, res_skill in resume_skill_ids.items():
            if s_id not in jd_skill_ids:
                resume_only_skills.append(res_skill.to_dict())

        total_jd = len(jd_skill_ids)
        match_percentage = round((len(matched_skills) / total_jd) * 100.0, 1) if total_jd > 0 else 100.0

        return {
            "matched_skills": matched_skills,
            "missing_jd_skills": missing_jd_skills,
            "resume_only_skills": resume_only_skills,
            "match_percentage": match_percentage
        }
