from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MultimodalInferenceResult(Base):
    __tablename__ = "multimodal_inference_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("multimodal_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    flow_run_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    stage_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    question_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    sample_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    modality: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    inference_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
