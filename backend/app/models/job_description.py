import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.jd_skill import JdSkill
    from app.models.interview import InterviewSession

class JobDescription(Base, TimestampMixin):
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    role_family: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    seniority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="job_descriptions")
    skills: Mapped[List["JdSkill"]] = relationship("JdSkill", back_populates="job_description", cascade="all, delete-orphan")
    interview_sessions: Mapped[List["InterviewSession"]] = relationship("InterviewSession", back_populates="job_description")
