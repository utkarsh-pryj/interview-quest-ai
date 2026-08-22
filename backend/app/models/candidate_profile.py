import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.resume import Resume

class CandidateProfile(Base, TimestampMixin):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    resume_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    role_family: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    seniority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_extraction: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationship
    resume: Mapped["Resume"] = relationship("Resume", back_populates="profile")
