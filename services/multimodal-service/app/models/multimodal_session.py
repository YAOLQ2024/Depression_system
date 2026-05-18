from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MultimodalSession(Base):
    __tablename__ = "multimodal_sessions"
    __table_args__ = (
        UniqueConstraint(
            "owner_service",
            "owner_session_id",
            name="uq_multimodal_sessions_owner",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_service: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_session_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    stage_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
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
