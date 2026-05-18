from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MultimodalSession(Base):
    __tablename__ = "multimodal_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    consultation_session_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    workflow_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    audio_turns = relationship(
        "MultimodalAudioTurn",
        back_populates="session",
        cascade="all, delete-orphan",
    )
