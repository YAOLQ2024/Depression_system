from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AssessmentResult(Base):
    __tablename__ = "assessment_results"
    __table_args__ = (
        UniqueConstraint("session_id", "scale_slug", name="uq_assessment_results_session_scale"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scale_slug: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_score: Mapped[int] = mapped_column(Integer, nullable=False)
    derived_score: Mapped[int] = mapped_column(Integer, nullable=False)
    interpretation_level: Mapped[str | None] = mapped_column(String(128), nullable=True)
    interpretation_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_flags: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
