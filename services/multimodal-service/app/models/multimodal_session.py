from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, JSON, String, Text, UniqueConstraint
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

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    owner_service: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_session_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stage_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="created")
    enabled_modalities: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    latest_live_payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    session_summary_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    warmed_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    audio_turns = relationship(
        "MultimodalAudioTurn",
        back_populates="session",
        cascade="all, delete-orphan",
    )
