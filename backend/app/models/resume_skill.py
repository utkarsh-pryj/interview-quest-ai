import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.resume import Resume
    from app.models.skill import Skill

class ResumeSkill(Base, TimestampMixin):
    __tablename__ = "resume_skills"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    resume_id: Mapped[str] = mapped_column(String(36), ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False)
    skill_id: Mapped[str] = mapped_column(String(64), ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    evidence_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    resume: Mapped["Resume"] = relationship("Resume", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="resume_skills")
