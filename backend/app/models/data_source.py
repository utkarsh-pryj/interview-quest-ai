import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin

class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    source_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    license: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
