import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.skill import Skill
    from app.models.interview import SessionQuestion

class InterviewQuestion(Base, TimestampMixin):
    __tablename__ = "interview_questions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skill_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("skills.id", ondelete="SET NULL"), index=True, nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    experience_level: Mapped[str] = mapped_column(String(50), default="UNKNOWN", index=True, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="INTERMEDIATE", index=True, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), default="CONCEPTUAL", index=True, nullable=False)
    keywords: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    source_dataset: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    quality_status: Mapped[str] = mapped_column(String(50), default="VALID", nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    # Relationships
    primary_skill: Mapped[Optional["Skill"]] = relationship("Skill", back_populates="questions")
    skill_links: Mapped[List["QuestionSkill"]] = relationship("QuestionSkill", back_populates="question", cascade="all, delete-orphan")
    session_questions: Mapped[List["SessionQuestion"]] = relationship("SessionQuestion", back_populates="question")

class QuestionSkill(Base):
    __tablename__ = "question_skills"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_questions.id", ondelete="CASCADE"), index=True, nullable=False)
    skill_id: Mapped[str] = mapped_column(String(64), ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)

    # Relationships
    question: Mapped["InterviewQuestion"] = relationship("InterviewQuestion", back_populates="skill_links")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="question_links")
