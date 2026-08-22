import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.answer import Answer

class Evaluation(Base, TimestampMixin):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    answer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("answers.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False) # 0.0 to 100.0
    concept_coverage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False) # 0.0 to 1.0
    semantic_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False) # 0.0 to 1.0
    rubric_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # {relevance, completeness, specificity, communication}
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    areas_for_improvement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluator_type: Mapped[str] = mapped_column(String(50), default="LOCAL_SEMANTIC", nullable=False) # LOCAL_SEMANTIC, DETERMINISTIC_CONCEPT, GEMINI_ESCALATED

    # Relationship
    answer: Mapped["Answer"] = relationship("Answer", back_populates="evaluation")
