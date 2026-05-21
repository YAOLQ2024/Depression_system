from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConsultationTurn(Base):
    __tablename__ = "consultation_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    encounter_session_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    consultation_flow_run_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_id: Mapped[str] = mapped_column(String(128), nullable=False)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    turn_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    question_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_video_asset_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    question_video_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_subtitle_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_type: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_audio_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_wav_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    structured_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    turn_summary_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    branch_taken: Mapped[str] = mapped_column(String(64), nullable=False)
    turn_window_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    turn_window_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    response_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session = relationship("ConsultationSession", back_populates="turns")
