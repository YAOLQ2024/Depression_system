from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MultimodalAudioTurn(Base):
    __tablename__ = "multimodal_audio_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    multimodal_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("multimodal_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flow_run_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    turn_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    stage_id: Mapped[str] = mapped_column(String(128), nullable=False)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    question_key: Mapped[str] = mapped_column(String(128), nullable=False)
    audio_uri: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_wav_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(Text, nullable=False)
    source_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(64), nullable=False)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    asr_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    response_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    session = relationship("MultimodalSession", back_populates="audio_turns")
