import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.candidate_profile import CandidateProfile
    from app.models.resume_skill import ResumeSkill
    from app.models.interview import InterviewSession

class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_type: Mapped[str] = mapped_column(String(50), default="pdf", nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resumes")
    profile: Mapped[Optional["CandidateProfile"]] = relationship("CandidateProfile", back_populates="resume", uselist=False, cascade="all, delete-orphan")
    skills: Mapped[List["ResumeSkill"]] = relationship("ResumeSkill", back_populates="resume", cascade="all, delete-orphan")
    interview_sessions: Mapped[List["InterviewSession"]] = relationship("InterviewSession", back_populates="resume")
