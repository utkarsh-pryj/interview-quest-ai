import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.interview import SessionQuestion
    from app.models.evaluation import Evaluation

class Answer(Base, TimestampMixin):
    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    session_question_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("session_questions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    time_taken_seconds: Mapped[Optional[int]] = mapped_column(default=0, nullable=True)

    # Relationships
    session_question: Mapped["SessionQuestion"] = relationship("SessionQuestion", back_populates="answer")
    evaluation: Mapped[Optional["Evaluation"]] = relationship("Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")
