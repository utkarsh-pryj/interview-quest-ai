import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.skill import Skill

class Occupation(Base, TimestampMixin):
    __tablename__ = "occupations"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="ONET_30.3", nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Relationships
    skills: Mapped[List["OccupationSkill"]] = relationship("OccupationSkill", back_populates="occupation", cascade="all, delete-orphan")

class OccupationSkill(Base):
    __tablename__ = "occupation_skills"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    occupation_id: Mapped[str] = mapped_column(String(64), ForeignKey("occupations.id", ondelete="CASCADE"), index=True, nullable=False)
    skill_id: Mapped[str] = mapped_column(String(64), ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False)
    relationship_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Relationships
    occupation: Mapped["Occupation"] = relationship("Occupation", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="occupations")
