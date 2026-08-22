import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.occupation import OccupationSkill
    from app.models.resume_skill import ResumeSkill
    from app.models.jd_skill import JdSkill
    from app.models.question import InterviewQuestion, QuestionSkill

class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True, default="TECHNICAL", nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="ONET_30.3", nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    # Relationships
    aliases: Mapped[List["SkillAlias"]] = relationship("SkillAlias", back_populates="skill", cascade="all, delete-orphan")
    occupations: Mapped[List["OccupationSkill"]] = relationship("OccupationSkill", back_populates="skill")
    resume_skills: Mapped[List["ResumeSkill"]] = relationship("ResumeSkill", back_populates="skill")
    jd_skills: Mapped[List["JdSkill"]] = relationship("JdSkill", back_populates="skill")
    questions: Mapped[List["InterviewQuestion"]] = relationship("InterviewQuestion", back_populates="primary_skill")
    question_links: Mapped[List["QuestionSkill"]] = relationship("QuestionSkill", back_populates="skill")

class SkillAlias(Base):
    __tablename__ = "skill_aliases"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    skill_id: Mapped[str] = mapped_column(String(64), ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False)
    alias: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    # Relationship
    skill: Mapped["Skill"] = relationship("Skill", back_populates="aliases")
