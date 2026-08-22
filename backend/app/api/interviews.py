from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.db.session import get_async_db
from app.models.user import User
from app.models.interview import InterviewSession, SessionQuestion
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.models.answer import Answer
from app.models.evaluation import Evaluation
from app.api.auth import get_current_user
from app.services.question_service import QuestionService
from app.schemas.interview import (
    CreateInterviewRequest, InterviewSessionDetail, QuestionDisplay,
    SubmitAnswerRequest, AnswerEvaluationResponse, SavedSessionSummary
)

router = APIRouter(prefix="/interviews", tags=["Interviews"])

@router.get("", response_model=List[SavedSessionSummary])
async def list_user_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List only explicitly saved interview sessions for the current user."""
    stmt = (
        select(InterviewSession)
        .filter(
            InterviewSession.user_id == current_user.id,
            InterviewSession.is_saved == True
        )
        .options(
            selectinload(InterviewSession.job_description),
            selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.answer)
        )
        .order_by(desc(InterviewSession.created_at))
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    summaries = []
    for s in sessions:
        answered_cnt = sum(1 for sq in s.session_questions if sq.answer is not None)
        role_title = s.job_description.title if s.job_description else s.strategy.get("role_family", "Candidate")
        company = s.job_description.company if s.job_description else "Company"

        summaries.append(SavedSessionSummary(
            id=s.id,
            resume_id=s.resume_id,
            jd_id=s.jd_id,
            role_title=role_title or "Target Role",
            company=company or "Target Company",
            role_family=s.strategy.get("role_family", "Software Engineer"),
            seniority=s.strategy.get("seniority", "Mid-Level"),
            status=s.status,
            is_saved=True,
            total_questions=s.total_questions,
            answered_questions=answered_cnt,
            created_at=s.created_at
        ))

    return summaries

@router.post("", response_model=InterviewSessionDetail, status_code=status.HTTP_201_CREATED)
async def create_interview(
    payload: CreateInterviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Initialize an adaptive interview session."""
    try:
        session = await QuestionService.create_interview_session(
            db=db,
            user_id=current_user.id,
            resume_id=payload.resume_id,
            jd_id=payload.jd_id,
            total_questions=payload.total_questions
        )
        session.is_saved = False
        await db.commit()

        return await _format_interview_session_response(db, current_user.id, session.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{id}/save", response_model=Dict[str, Any])
async def save_session_explicitly(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Explicitly save an interview session to user's saved history."""
    stmt = select(InterviewSession).filter_by(id=id, user_id=current_user.id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session.is_saved = True
    await db.commit()
    return {"status": "success", "is_saved": True, "id": id, "message": "Session saved successfully"}

@router.post("/{id}/unsave", response_model=Dict[str, Any])
async def unsave_session_explicitly(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Remove session from saved history."""
    stmt = select(InterviewSession).filter_by(id=id, user_id=current_user.id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session.is_saved = False
    await db.commit()
    return {"status": "success", "is_saved": False, "id": id, "message": "Session removed from saved list"}

@router.get("/{id}", response_model=InterviewSessionDetail)
async def get_interview_session(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Fetch current state of interview session with all questions and answers."""
    return await _format_interview_session_response(db, current_user.id, id)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview_session(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a saved interview session and associated questions."""
    stmt = select(InterviewSession).filter_by(id=id, user_id=current_user.id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    await db.delete(session)
    await db.commit()
    return None

@router.post("/{id}/answers", response_model=AnswerEvaluationResponse)
async def submit_answer(
    id: str,
    payload: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Submit candidate answer and evaluate using Two-Stage Evaluator."""
    try:
        result = await QuestionService.submit_and_evaluate_answer(
            db=db,
            user_id=current_user.id,
            session_id=id,
            session_question_id=payload.session_question_id,
            answer_text=payload.answer_text,
            time_taken_seconds=payload.time_taken_seconds or 0
        )
        return AnswerEvaluationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

async def _format_interview_session_response(
    db: AsyncSession,
    user_id: str,
    session_id: str
) -> InterviewSessionDetail:
    """Helper to format interview session payload."""
    stmt = (
        select(InterviewSession)
        .filter_by(id=session_id, user_id=user_id)
        .options(
            selectinload(InterviewSession.job_description),
            selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.question),
            selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.answer).selectinload(Answer.evaluation)
        )
    )
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")

    questions_display = []
    for sq in session.session_questions:
        q_text = sq.custom_question_text or (sq.question.question if sq.question else "Question")
        is_ans = sq.answer is not None
        ans_text = sq.answer.answer_text if is_ans else None
        score = sq.answer.evaluation.score if (is_ans and sq.answer.evaluation) else None
        fb = sq.answer.evaluation.feedback if (is_ans and sq.answer.evaluation) else None
        str_text = sq.answer.evaluation.strengths if (is_ans and sq.answer.evaluation) else None
        imp_text = sq.answer.evaluation.areas_for_improvement if (is_ans and sq.answer.evaluation) else None

        questions_display.append(QuestionDisplay(
            session_question_id=sq.id,
            position=sq.position,
            question_text=q_text,
            category=sq.category,
            target_skill=sq.target_skill,
            source_type=sq.source_type,
            selection_rationale=sq.selection_rationale,
            is_answered=is_ans,
            answer_text=ans_text,
            score=score,
            feedback=fb,
            strengths=str_text,
            areas_for_improvement=imp_text
        ))

    role_title = session.job_description.title if session.job_description else session.strategy.get("role_family", "Candidate")
    company = session.job_description.company if session.job_description else "Company"

    return InterviewSessionDetail(
        id=session.id,
        resume_id=session.resume_id,
        jd_id=session.jd_id,
        role_title=role_title,
        company=company,
        status=session.status,
        is_saved=bool(session.is_saved),
        current_position=session.current_position,
        total_questions=session.total_questions,
        role_family=session.strategy.get("role_family", "Candidate"),
        seniority=session.strategy.get("seniority", "Mid-Level"),
        created_at=session.created_at,
        questions=questions_display
    )
