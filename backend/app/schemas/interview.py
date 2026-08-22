from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class CreateInterviewRequest(BaseModel):
    resume_id: str
    jd_id: str
    total_questions: int = Field(default=8, ge=3, le=25, description="Number of questions in the interview")
    difficulty_preference: Optional[str] = Field(default="ADAPTIVE")

class QuestionDisplay(BaseModel):
    session_question_id: str
    position: int
    question_text: str
    category: str
    target_skill: Optional[str] = None
    source_type: str
    selection_rationale: Optional[str] = None
    is_answered: bool = False
    answer_text: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None

class InterviewSessionDetail(BaseModel):
    id: str
    resume_id: str
    jd_id: str
    role_title: Optional[str] = None
    company: Optional[str] = None
    status: str
    is_saved: bool = False
    current_position: int
    total_questions: int
    role_family: str
    seniority: str
    created_at: datetime
    questions: List[QuestionDisplay] = Field(default_factory=list)

class SavedSessionSummary(BaseModel):
    id: str
    resume_id: str
    jd_id: str
    role_title: str
    company: str
    role_family: str
    seniority: str
    status: str
    is_saved: bool = True
    total_questions: int
    answered_questions: int
    created_at: datetime

class SubmitAnswerRequest(BaseModel):
    session_question_id: str
    answer_text: str = Field(..., min_length=2)
    time_taken_seconds: Optional[int] = 0

class AnswerEvaluationResponse(BaseModel):
    answer_id: str
    session_question_id: str
    score: float
    concept_coverage: float
    semantic_score: float
    feedback: str
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    evaluator_type: str
    is_last_question: bool = False
    next_question_position: Optional[int] = None
