from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    encounter_session_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    source_consultation_flow_run_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    multimodal_session_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="created")
    required_scales: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    selected_scales: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    current_scale_slug: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_item_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scale_handoff_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    capture_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    aggregate_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    multimodal_live_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    multimodal_live_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
