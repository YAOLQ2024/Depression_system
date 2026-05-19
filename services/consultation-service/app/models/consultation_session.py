from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConsultationSession(Base):
    __tablename__ = "consultation_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    script_bundle: Mapped[str] = mapped_column(String(128), nullable=False)
    playlist_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    workflow_stage_id: Mapped[str] = mapped_column(String(128), nullable=False)
    current_stage_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_node_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_prompt_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_prompt_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_prompt_video_asset_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_prompt_video_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_prompt_question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_prompt_subtitle_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_prompt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_prompt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    assigned_doctor_persona: Mapped[str] = mapped_column(String(128), nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    participant_profile_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    context_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    slot_values: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    engine_state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    chief_complaint_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    chief_complaint_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_history_structured_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    high_risk_screening_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scale_handoff_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    multimodal_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    multimodal_live_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    multimodal_live_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subtitle_history_payload: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    turns = relationship("ConsultationTurn", back_populates="session", cascade="all, delete-orphan")
