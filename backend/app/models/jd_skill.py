import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.job_description import JobDescription
    from app.models.skill import Skill

class JdSkill(Base, TimestampMixin):
    __tablename__ = "jd_skills"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    jd_id: Mapped[str] = mapped_column(String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True, nullable=False)
    skill_id: Mapped[str] = mapped_column(String(64), ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False)
    required_or_desired: Mapped[str] = mapped_column(String(50), default="REQUIRED", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    evidence_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    job_description: Mapped["JobDescription"] = relationship("JobDescription", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="jd_skills")
