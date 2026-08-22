import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.resume import Resume
    from app.models.job_description import JobDescription
    from app.models.question import InterviewQuestion
    from app.models.answer import Answer

class InterviewSession(Base, TimestampMixin):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    resume_id: Mapped[str] = mapped_column(String(36), ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False)
    jd_id: Mapped[str] = mapped_column(String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True, nullable=False)
    strategy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="IN_PROGRESS", index=True, nullable=False) # IN_PROGRESS, COMPLETED, ABANDONED
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    current_position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    summary_report: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="interview_sessions")
    resume: Mapped["Resume"] = relationship("Resume", back_populates="interview_sessions")
    job_description: Mapped["JobDescription"] = relationship("JobDescription", back_populates="interview_sessions")
    session_questions: Mapped[List["SessionQuestion"]] = relationship(
        "SessionQuestion",
        back_populates="session",
        order_by="SessionQuestion.position",
        cascade="all, delete-orphan"
    )

class SessionQuestion(Base, TimestampMixin):
    __tablename__ = "session_questions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    question_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("interview_questions.id", ondelete="SET NULL"), index=True, nullable=True)
    custom_question_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Used if generated via fallback/personalization
    custom_ideal_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), default="TECHNICAL", nullable=False)
    target_skill: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="RAG_RETRIEVAL", nullable=False) # RAG_RETRIEVAL, LLM_FALLBACK, WEB_FALLBACK
    selection_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    selection_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="session_questions")
    question: Mapped[Optional["InterviewQuestion"]] = relationship("InterviewQuestion", back_populates="session_questions")
    answer: Mapped[Optional["Answer"]] = relationship("Answer", back_populates="session_question", uselist=False, cascade="all, delete-orphan")
