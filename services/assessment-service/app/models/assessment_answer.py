from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"
    __table_args__ = (
        UniqueConstraint("session_id", "scale_slug", "item_id", name="uq_assessment_answers_session_scale_item"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scale_slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_option: Mapped[str] = mapped_column(String(255), nullable=False)
    score_value: Mapped[int] = mapped_column(Integer, nullable=False)
    capture_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
