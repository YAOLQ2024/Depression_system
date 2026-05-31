from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MultimodalVisualFrame(Base):
    __tablename__ = "multimodal_visual_frames"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("multimodal_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    flow_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    origin_flow_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    stage_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    question_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    sample_index: Mapped[int | None] = mapped_column(nullable=True)
    sample_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sample_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    storage_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    capture_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
