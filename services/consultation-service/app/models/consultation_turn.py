from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConsultationTurn(Base):
    __tablename__ = "consultation_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("consultation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_stage_id: Mapped[str] = mapped_column(String(128), nullable=False)
    stage_id: Mapped[str] = mapped_column(String(128), nullable=False)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    turn_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_video_asset_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_video_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_subtitle_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_type: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    branch_taken: Mapped[str] = mapped_column(String(64), nullable=False)
    response_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session = relationship("ConsultationSession", back_populates="turns")
