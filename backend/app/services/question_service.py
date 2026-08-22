"""
Interview Session & Question Management Service.
Coordinates RAG question selection, answer submissions, two-stage evaluations, and session reporting.
Conforms to RAG specifications.
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
from app.services.document_parser import DocumentParser
from app.services.skill_service import SkillService
from app.services.role_service import RoleService
from app.services.interview_strategy import InterviewStrategyGenerator
from app.services.evaluation_service import EvaluationService
from app.rag.retriever import RAGRetriever
from app.core.logging import logger

class QuestionService:
    """Handles interview session lifecycle, RAG orchestration, and answer scoring."""

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
        # 1. Fetch Resume & JD with strict ownership check
        resume_res = await db.execute(select(Resume).filter_by(id=resume_id, user_id=user_id))
        resume = resume_res.scalar_one_or_none()
        if not resume:
            raise ValueError("Resume not found or unauthorized.")

        jd_res = await db.execute(select(JobDescription).filter_by(id=jd_id, user_id=user_id))
        jd = jd_res.scalar_one_or_none()
        if not jd:
            raise ValueError("Job Description not found or unauthorized.")

        # 2. Build Structured Profiles & Extract Skills
        candidate_profile = DocumentParser.build_candidate_profile(resume.extracted_text, document_id=resume.id)
        jd_profile = DocumentParser.build_job_requirement_profile(jd.extracted_text, title=jd.title or "", document_id=jd.id)

        canonical_skills = await SkillService.get_all_canonical_skills(db)
        resume_skills = SkillService.extract_skills_from_text(
            resume.extracted_text, canonical_skills, section_hint="resume"
        )
        
        # Extract required vs preferred from JD
        jd_required_skills = SkillService.extract_skills_from_text(
            jd_profile.required_skills_text or jd.extracted_text, canonical_skills, section_hint="required", default_required_or_desired="REQUIRED"
        )
        jd_preferred_skills = SkillService.extract_skills_from_text(
            jd_profile.preferred_skills_text, canonical_skills, section_hint="preferred", default_required_or_desired="PREFERRED"
        )

        skill_gap = SkillService.compute_skill_gap(
            resume_skills=resume_skills,
            jd_skills=jd_required_skills,
            preferred_jd_skills=jd_preferred_skills
        )

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

        # 5. Retrieve & Rank Questions via RAG with Confidence Router
        selected_candidates, confidence_report = await RAGRetriever.retrieve_and_rank_questions(
            db=db,
            strategy=strategy,
            resume_text=candidate_profile.get_compact_retrieval_context(),
            jd_text=jd_profile.get_compact_retrieval_context(),
            matched_skills=skill_gap["matched_skills"],
            missing_jd_skills=skill_gap["missing_jd_skills"],
            role_family=role_family
        )

        # Attach confidence report to session strategy
        strategy["confidence_report"] = confidence_report.to_dict()

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

        # 7. Persist Session Questions with Explainable Metadata
        for idx, cand in enumerate(selected_candidates, 1):
            sq = SessionQuestion(
                id=str(uuid.uuid4()),
                session_id=session_id,
                question_id=cand.question_id if not cand.question_id.startswith("gemini-") else None,
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
        # 1. Fetch Session & Session Question with user ownership check
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

        # 4. Save or Update Answer
        if existing_ans:
            existing_ans.answer_text = answer_text
            existing_ans.time_taken_seconds = time_taken_seconds
            ans_record = existing_ans
        else:
            ans_record = Answer(
                id=str(uuid.uuid4()),
                session_question_id=session_question_id,
                answer_text=answer_text,
                time_taken_seconds=time_taken_seconds
            )
            db.add(ans_record)
            await db.flush()

        # 5. Save or Update Evaluation
        eval_stmt = select(Evaluation).filter_by(answer_id=ans_record.id)
        existing_eval = (await db.execute(eval_stmt)).scalar_one_or_none()

        if existing_eval:
            existing_eval.score = eval_result.score
            existing_eval.feedback = eval_result.feedback
            existing_eval.strengths = eval_result.strengths
            existing_eval.areas_for_improvement = eval_result.areas_for_improvement
            existing_eval.concept_coverage = eval_result.concept_coverage
            existing_eval.rubric_scores = eval_result.rubric_scores
            existing_eval.evaluator_type = eval_result.evaluator_type
        else:
            new_eval = Evaluation(
                id=str(uuid.uuid4()),
                answer_id=ans_record.id,
                score=eval_result.score,
                feedback=eval_result.feedback,
                strengths=eval_result.strengths,
                areas_for_improvement=eval_result.areas_for_improvement,
                concept_coverage=eval_result.concept_coverage,
                rubric_scores=eval_result.rubric_scores,
                evaluator_type=eval_result.evaluator_type
            )
            db.add(new_eval)

        # 6. Advance Session Position
        session = sq.session
        if session.current_position <= sq.position:
            session.current_position = min(session.total_questions, sq.position + 1)
            if sq.position == session.total_questions:
                session.status = "COMPLETED"

        await db.commit()

        return {
            "session_question_id": session_question_id,
            "position": sq.position,
            "evaluation": eval_result.to_dict(),
            "next_position": session.current_position,
            "session_status": session.status
        }
