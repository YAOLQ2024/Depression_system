from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SpeechEmotionResult(Base):
    __tablename__ = "speech_emotion_results"
    __table_args__ = (
        UniqueConstraint(
            "consultation_turn_id",
            name="uq_speech_emotion_results_consultation_turn_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    consultation_turn_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("consultation_turns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consultation_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    primary_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    top3_payload: Mapped[list | None] = mapped_column(JSON, nullable=True)
    inference_status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    consultation_turn = relationship("ConsultationTurn", back_populates="speech_emotion_result")
    consultation_session = relationship("ConsultationSession", back_populates="speech_emotion_results")
