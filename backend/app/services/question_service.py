"""
Interview Session & Question Management Service.
Coordinates RAG question selection, answer submissions, and final report generation.
Conforms to Blueprint Section 12, 14, 16.
"""

import uuid
from typing import List, Dict, Any, Optional
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.interview import InterviewSession, SessionQuestion
from app.models.resume import Resume
from app.models.job_description import JobDescription
from app.models.answer import Answer
from app.models.evaluation import Evaluation
from app.services.skill_service import SkillService
from app.services.role_service import RoleService
from app.services.interview_strategy import InterviewStrategyGenerator
from app.services.evaluation_service import EvaluationService
from app.rag.retriever import RAGRetriever
from app.core.logging import logger

class QuestionService:
    """Handles interview session lifecycle and scoring."""

    @classmethod
    async def create_interview_session(
        cls,
        db: AsyncSession,
        user_id: str,
        resume_id: str,
        jd_id: str,
        total_questions: int = 8
    ) -> InterviewSession:
        """Initialize a new adaptive interview session with retrieved & ranked questions."""
        # 1. Fetch Resume & JD
        resume_res = await db.execute(select(Resume).filter_by(id=resume_id, user_id=user_id))
        resume = resume_res.scalar_one_or_none()
        if not resume:
            raise ValueError("Resume not found or unauthorized.")

        jd_res = await db.execute(select(JobDescription).filter_by(id=jd_id, user_id=user_id))
        jd = jd_res.scalar_one_or_none()
        if not jd:
            raise ValueError("Job Description not found or unauthorized.")

        # 2. Extract Skills and Perform Gap Analysis
        canonical_skills = await SkillService.get_all_canonical_skills(db)
        resume_skills = SkillService.extract_skills_from_text(resume.extracted_text, canonical_skills)
        jd_skills = SkillService.extract_skills_from_text(jd.extracted_text, canonical_skills)
        skill_gap = SkillService.compute_skill_gap(resume_skills, jd_skills)

        # 3. Infer Role and Seniority
        role_family = jd.role_family or RoleService.infer_role_family(jd.title or "", jd.extracted_text)
        seniority = jd.seniority or RoleService.infer_seniority(jd.title or "", jd.extracted_text)

        # 4. Generate Role-Adaptive Strategy
        strategy = InterviewStrategyGenerator.generate_strategy(
            role_family=role_family,
            seniority=seniority,
            total_questions=total_questions,
            matched_skills=skill_gap["matched_skills"],
            missing_jd_skills=skill_gap["missing_jd_skills"],
            resume_only_skills=skill_gap["resume_only_skills"]
        )

        # 5. Retrieve & Rank Questions via RAG
        selected_candidates = await RAGRetriever.retrieve_and_rank_questions(
            db=db,
            strategy=strategy,
            resume_text=resume.extracted_text,
            jd_text=jd.extracted_text,
            matched_skills=skill_gap["matched_skills"],
            missing_jd_skills=skill_gap["missing_jd_skills"]
        )

        # 6. Persist Interview Session
        session_id = str(uuid.uuid4())
        interview_session = InterviewSession(
            id=session_id,
            user_id=user_id,
            resume_id=resume_id,
            jd_id=jd_id,
            strategy=strategy,
            status="IN_PROGRESS",
            current_position=1,
            total_questions=len(selected_candidates)
        )
        db.add(interview_session)
        await db.flush()

        # 7. Persist Session Questions
        for idx, cand in enumerate(selected_candidates, 1):
            sq = SessionQuestion(
                id=str(uuid.uuid4()),
                session_id=session_id,
                question_id=cand.question_id,
                custom_question_text=cand.question_text,
                custom_ideal_answer=cand.ideal_answer,
                category=cand.category,
                target_skill=cand.skill_name or cand.topic,
                position=idx,
                source_type=cand.source_type,
                selection_score=round(cand.final_score, 3),
                selection_rationale=cand.selection_rationale
            )
            db.add(sq)

        await db.commit()
        return interview_session

    @classmethod
    async def submit_and_evaluate_answer(
        cls,
        db: AsyncSession,
        user_id: str,
        session_id: str,
        session_question_id: str,
        answer_text: str,
        time_taken_seconds: int = 0
    ) -> Dict[str, Any]:
        """Submit candidate answer, run two-stage evaluation, and advance session position."""
        # 1. Fetch Session & Session Question
        stmt = (
            select(SessionQuestion)
            .join(InterviewSession)
            .filter(
                SessionQuestion.id == session_question_id,
                InterviewSession.id == session_id,
                InterviewSession.user_id == user_id
            )
            .options(
                selectinload(SessionQuestion.question),
                selectinload(SessionQuestion.session)
            )
        )
        res = await db.execute(stmt)
        sq = res.scalar_one_or_none()
        if not sq:
            raise ValueError("Session question not found or unauthorized.")

        # 2. Check if already answered
        ans_stmt = select(Answer).filter_by(session_question_id=session_question_id)
        existing_ans = (await db.execute(ans_stmt)).scalar_one_or_none()

        question_text = sq.custom_question_text or (sq.question.question if sq.question else "")
        ideal_answer = sq.custom_ideal_answer or (sq.question.answer if sq.question else "")
        expected_keywords = sq.question.keywords if sq.question and sq.question.keywords else []

        # 3. Run Two-Stage Evaluation
        eval_result = await EvaluationService.evaluate_answer(
            question_text=question_text,
            candidate_answer=answer_text,
            ideal_answer=ideal_answer,
            category=sq.category,
            expected_keywords=expected_keywords
        )

        # 4. Save Answer and Evaluation
        if not existing_ans:
            answer_obj = Answer(
                id=str(uuid.uuid4()),
                session_question_id=session_question_id,
                answer_text=answer_text,
                time_taken_seconds=time_taken_seconds
            )
            db.add(answer_obj)
            await db.flush()

            eval_obj = Evaluation(
                id=str(uuid.uuid4()),
                answer_id=answer_obj.id,
                score=eval_result.score,
                concept_coverage=eval_result.concept_coverage,
                semantic_score=eval_result.semantic_score,
                rubric_scores=eval_result.rubric_scores,
                feedback=eval_result.feedback,
                strengths=eval_result.strengths,
                areas_for_improvement=eval_result.areas_for_improvement,
                evaluator_type=eval_result.evaluator_type
            )
            db.add(eval_obj)
        else:
            answer_obj = existing_ans
            existing_eval = (await db.execute(select(Evaluation).filter_by(answer_id=answer_obj.id))).scalar_one_or_none()
            if existing_eval:
                existing_eval.score = eval_result.score
                existing_eval.concept_coverage = eval_result.concept_coverage
                existing_eval.semantic_score = eval_result.semantic_score
                existing_eval.feedback = eval_result.feedback
                existing_eval.strengths = eval_result.strengths
                existing_eval.areas_for_improvement = eval_result.areas_for_improvement
                existing_eval.evaluator_type = eval_result.evaluator_type

        # 5. Advance session state
        session = sq.session
        is_last = (sq.position >= session.total_questions)
        if not is_last:
            session.current_position = max(session.current_position, sq.position + 1)
        else:
            session.status = "COMPLETED"

        await db.commit()

        return {
            "answer_id": answer_obj.id,
            "session_question_id": session_question_id,
            "score": eval_result.score,
            "concept_coverage": eval_result.concept_coverage,
            "semantic_score": eval_result.semantic_score,
            "feedback": eval_result.feedback,
            "strengths": eval_result.strengths,
            "areas_for_improvement": eval_result.areas_for_improvement,
            "evaluator_type": eval_result.evaluator_type,
            "is_last_question": is_last,
            "next_question_position": None if is_last else sq.position + 1
        }
