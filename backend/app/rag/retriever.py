"""
RAG Question Retriever.
Retrieves candidate questions from PostgreSQL/pgvector, executes multi-signal ranking, and enforces strategy quotas.
Conforms to Blueprint Section 12.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.question import InterviewQuestion
from app.models.skill import Skill
from app.rag.embeddings import EmbeddingService
from app.rag.ranker import QuestionCandidate, QuestionRanker
from app.rag.filters import RAGFilters
from app.core.logging import logger

class RAGRetriever:
    """Orchestrates candidate retrieval, metadata filtering, and multi-signal ranking."""

    @classmethod
    async def retrieve_and_rank_questions(
        cls,
        db: AsyncSession,
        strategy: Dict[str, Any],
        resume_text: str,
        jd_text: str,
        matched_skills: List[Dict[str, Any]],
        missing_jd_skills: List[Dict[str, Any]]
    ) -> List[QuestionCandidate]:
        """
        Executes full RAG selection workflow:
        1. Fetch all questions and skills from knowledge base.
        2. Embed JD and Resume contexts.
        3. Match candidates per category quota and target skill.
        4. Rank with composite formula.
        5. Filter for diversity and return final selected questions.
        """
        # Step 1: Query knowledge base
        stmt = select(InterviewQuestion).options(selectinload(InterviewQuestion.primary_skill))
        res = await db.execute(stmt)
        all_db_questions: List[InterviewQuestion] = list(res.scalars().all())

        if not all_db_questions:
            logger.warning("No questions found in knowledge base.")
            return []

        # Step 2: Embed resume and JD for multi-signal context
        resume_vec = EmbeddingService.embed_text(resume_text[:1500]) if resume_text else None
        jd_vec = EmbeddingService.embed_text(jd_text[:1500]) if jd_text else None

        role_family = strategy.get("role_family", "Software Engineer")
        category_quotas: Dict[str, int] = strategy.get("category_quotas", {"TECHNICAL": 4, "BEHAVIORAL": 2})
        target_skills = strategy.get("target_skills", [])
        missing_skill_ids = {s["skill_id"] for s in target_skills if s.get("type") == "MISSING_JD_SKILL"}

        # Map target skill vectors
        skill_vectors: Dict[str, List[float]] = {}
        for s in matched_skills + missing_jd_skills:
            s_name = s.get("canonical_name")
            if s_name and s_name not in skill_vectors:
                skill_vectors[s_name] = EmbeddingService.embed_text(f"Skill competency in {s_name}")

        final_selected_questions: List[QuestionCandidate] = []
        used_question_ids = set()

        # Step 3: For each category quota in the strategy, score and select candidates
        for category, quota in category_quotas.items():
            if quota <= 0:
                continue

            category_candidates: List[QuestionCandidate] = []

            for q in all_db_questions:
                if q.id in used_question_ids:
                    continue

                # Filter: primary category match or related category
                cat_match = (q.category == category)
                if not cat_match and category not in ["TECHNICAL", "DOMAIN"]:
                    continue

                skill_name = q.primary_skill.canonical_name if q.primary_skill else None
                is_missing = q.skill_id in missing_skill_ids if q.skill_id else False
                target_skill_vec = skill_vectors.get(skill_name) if skill_name else None

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

                # Compute multi-signal score
                QuestionRanker.score_candidate(
                    candidate=candidate,
                    target_skill_vec=target_skill_vec,
                    jd_vec=jd_vec,
                    resume_vec=resume_vec,
                    target_role_family=role_family,
                    target_category=category,
                    target_difficulty="INTERMEDIATE",
                    is_missing_skill=is_missing
                )

                category_candidates.append(candidate)

            # Step 4: Apply diversity filter to select top questions for this category
            chosen_for_cat = RAGFilters.filter_and_diversify(
                candidates=category_candidates,
                target_count=quota,
                similarity_ceiling=0.80
            )

            for c in chosen_for_cat:
                final_selected_questions.append(c)
                used_question_ids.add(c.question_id)

        # In case total questions chosen is less than requested, backfill with remaining top candidates
        total_needed = strategy.get("total_questions", 8)
        if len(final_selected_questions) < total_needed:
            remaining = [
                q for q in all_db_questions
                if q.id not in used_question_ids
            ]
            for q in remaining:
                if len(final_selected_questions) >= total_needed:
                    break
                skill_name = q.primary_skill.canonical_name if q.primary_skill else None
                c = QuestionCandidate(
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
                    candidate=c,
                    target_skill_vec=None,
                    jd_vec=jd_vec,
                    resume_vec=resume_vec,
                    target_role_family=role_family,
                    target_category=q.category,
                    target_difficulty="INTERMEDIATE"
                )
                final_selected_questions.append(c)
                used_question_ids.add(q.id)

        return final_selected_questions[:total_needed]
