from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MultimodalEegExplanation(Base):
    __tablename__ = "multimodal_eeg_explanations"
    __table_args__ = (
        Index("ix_eeg_explanations_history", "session_id", "created_at", "id"),
        Index("ix_eeg_explanations_queue", "status", "lease_expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("multimodal_sessions.id", ondelete="CASCADE"), nullable=False)
    sample_id: Mapped[str] = mapped_column(ForeignKey("multimodal_captures.id", ondelete="CASCADE"), nullable=False)
    inference_id: Mapped[str] = mapped_column(ForeignKey("multimodal_inference_results.id", ondelete="CASCADE"), nullable=False)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_class: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    config_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
