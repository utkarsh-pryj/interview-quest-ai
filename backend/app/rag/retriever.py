"""
RAG Question Retriever & Confidence Orchestrator.
Retrieves top-K candidate questions from PostgreSQL, scores via multi-signal ranking, diversifies via MMR,
and gates through the explicit RetrievalConfidenceRouter.
Conforms to RAG specifications.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.question import InterviewQuestion
from app.models.skill import Skill
from app.rag.embeddings import EmbeddingService
from app.rag.ranker import QuestionCandidate, QuestionRanker
from app.rag.filters import RAGFilters
from app.rag.confidence import RetrievalConfidenceRouter, ConfidenceReport
from app.llm.gemini import gemini_client
from app.core.config import settings
from app.core.logging import logger

class RAGRetriever:
    """Orchestrates candidate retrieval, metadata filtering, ranking, confidence gating, and LLM fallback."""

    @classmethod
    async def retrieve_and_rank_questions(
        cls,
        db: AsyncSession,
        strategy: Dict[str, Any],
        resume_text: str,
        jd_text: str,
        matched_skills: List[Dict[str, Any]],
        missing_jd_skills: List[Dict[str, Any]],
        role_family: str
    ) -> Tuple[List[QuestionCandidate], ConfidenceReport]:
        """
        Full RAG Retrieval & Confidence Pipeline:
        1. Query top-K candidate pool from PostgreSQL knowledge base.
        2. Embed compact Resume & JD contexts.
        3. Score candidates with multi-signal ranker.
        4. Apply semantic vector MMR diversity filter per category quota.
        5. Evaluate explicit confidence via RetrievalConfidenceRouter.
        6. If confidence is LOW or specific gaps are uncovered, trigger targeted Gemini fallback.
        """
        # Step 1: Query knowledge base
        stmt = select(InterviewQuestion).options(selectinload(InterviewQuestion.primary_skill))
        res = await db.execute(stmt)
        all_db_questions: List[InterviewQuestion] = list(res.scalars().all())

        total_needed = strategy.get("total_questions", 8)
        category_quotas: Dict[str, int] = strategy.get("category_quotas", {"TECHNICAL": 4, "BEHAVIORAL": 2})
        target_skills = strategy.get("target_skills", [])
        missing_skill_names = {s["canonical_name"].lower() for s in target_skills if s.get("type") == "MISSING_JD_SKILL"}

        # Step 2: Compact context embeddings
        resume_vec = EmbeddingService.embed_text(resume_text[:1200]) if resume_text else None
        jd_vec = EmbeddingService.embed_text(jd_text[:1200]) if jd_text else None

        # Pre-compute skill vector representations
        skill_vectors: Dict[str, List[float]] = {}
        for s in matched_skills + missing_jd_skills:
            s_name = s.get("canonical_name")
            if s_name and s_name not in skill_vectors:
                skill_vectors[s_name.lower()] = EmbeddingService.embed_text(f"Technical interview competency in {s_name}")

        final_selected: List[QuestionCandidate] = []
        used_question_ids = set()
        covered_skill_names = set()

        # Step 3: Category & Skill Based Multi-Signal Candidate Scoring
        all_scored_candidates: List[QuestionCandidate] = []

        for q in all_db_questions:
            skill_name = q.primary_skill.canonical_name if q.primary_skill else (q.topic or "General")
            skill_key = skill_name.lower()
            is_missing = skill_key in missing_skill_names
            target_skill_vec = skill_vectors.get(skill_key)

            candidate = QuestionCandidate(
                question_id=q.id,
                question_text=q.question,
                ideal_answer=q.answer,
                category=q.category,
                difficulty=q.difficulty,
                role=q.role,
                topic=q.topic,
                skill_id=q.skill_id,
                skill_name=skill_name,
                source_type="RAG_RETRIEVAL",
                vector_embedding=q.embedding
            )

            QuestionRanker.score_candidate(
                candidate=candidate,
                target_skill_vec=target_skill_vec,
                jd_vec=jd_vec,
                resume_vec=resume_vec,
                target_role_family=role_family,
                target_category=q.category,
                target_difficulty="INTERMEDIATE",
                is_missing_skill=is_missing
            )
            all_scored_candidates.append(candidate)

        # Step 4: Quota & Diversity Selection per category
        for category, quota in category_quotas.items():
            if quota <= 0:
                continue

            cat_candidates = [
                c for c in all_scored_candidates
                if c.category == category and c.question_id not in used_question_ids
            ]

            # If not enough exact category matches, include general technical/domain
            if len(cat_candidates) < quota and category in ["TECHNICAL", "DOMAIN"]:
                cat_candidates = [
                    c for c in all_scored_candidates
                    if c.category in ["TECHNICAL", "SYSTEM_DESIGN", "CODING", "DOMAIN"]
                    and c.question_id not in used_question_ids
                ]

            chosen = RAGFilters.filter_and_diversify(
                candidates=cat_candidates,
                target_count=quota,
                similarity_ceiling=settings.DIVERSITY_SIMILARITY_CEILING
            )

            for c in chosen:
                final_selected.append(c)
                used_question_ids.add(c.question_id)
                if c.skill_name:
                    covered_skill_names.add(c.skill_name.lower())

        # Step 5: Evaluate Measurable Retrieval Confidence
        confidence_report = RetrievalConfidenceRouter.evaluate_retrieval_confidence(
            candidates=final_selected,
            target_role_family=role_family,
            target_skills=matched_skills + missing_jd_skills,
            total_questions_needed=total_needed
        )

        logger.info(f"RAG Retrieval Confidence: {confidence_report.level} ({confidence_report.confidence_score}). Decision: {confidence_report.decision_reason}")

        # Step 6: Targeted Gemini Fallback (Triggered only when needed)
        # Condition A: Total selected questions is less than required quota
        # Condition B: Confidence is LOW or critical missing skills have zero questions
        needed_count = total_needed - len(final_selected)
        uncovered_gaps = [
            s for s in missing_jd_skills 
            if s.get("canonical_name", "").lower() not in covered_skill_names
        ]

        if (needed_count > 0 or confidence_report.level == "LOW") and gemini_client.is_available():
            logger.info(f"Triggering Gemini fallback to generate {max(needed_count, len(uncovered_gaps))} targeted questions...")

            for gap_skill in uncovered_gaps[:max(needed_count, 3)]:
                if len(final_selected) >= total_needed:
                    break

                skill_name = gap_skill.get("canonical_name", "Technical Skill")
                generated = await gemini_client.generate_question_fallback(
                    role=role_family,
                    target_skill=skill_name,
                    requirement_context=gap_skill.get("evidence_text", f"Missing requirement in {skill_name}"),
                    difficulty="INTERMEDIATE",
                    category="TECHNICAL"
                )

                if generated:
                    fallback_cand = QuestionCandidate(
                        question_id=f"gemini-{skill_name.lower().replace(' ', '-')}",
                        question_text=generated["question"],
                        ideal_answer=generated["ideal_answer"],
                        category=generated.get("category", "TECHNICAL"),
                        difficulty=generated.get("difficulty", "INTERMEDIATE"),
                        role=role_family,
                        topic=skill_name,
                        skill_id=gap_skill.get("skill_id"),
                        skill_name=skill_name,
                        source_type="GEMINI_FALLBACK",
                        vector_embedding=EmbeddingService.embed_text(generated["question"])
                    )
                    fallback_cand.final_score = 0.88
                    fallback_cand.selection_rationale = generated.get("selection_rationale", f"Gemini Fallback: Synthesized for {skill_name} gap.")
                    final_selected.append(fallback_cand)
                    covered_skill_names.add(skill_name.lower())

        # Step 7: Backfill remaining from top ranked candidates if still under quota
        if len(final_selected) < total_needed:
            remaining = [
                c for c in sorted(all_scored_candidates, key=lambda x: x.final_score, reverse=True)
                if c.question_id not in used_question_ids
            ]
            for c in remaining:
                if len(final_selected) >= total_needed:
                    break
                final_selected.append(c)
                used_question_ids.add(c.question_id)

        return final_selected[:total_needed], confidence_report
