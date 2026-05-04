from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
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
    input_type: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    branch_taken: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session = relationship("ConsultationSession", back_populates="turns")
