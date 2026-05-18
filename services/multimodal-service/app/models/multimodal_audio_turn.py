from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
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
    consultation_session_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    question_key: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audio_uri: Mapped[str] = mapped_column(Text, nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    stored_relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(64), nullable=False)
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
