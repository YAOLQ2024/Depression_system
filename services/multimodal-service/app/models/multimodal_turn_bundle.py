from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MultimodalTurnBundle(Base):
    __tablename__ = "multimodal_turn_bundles"
    __table_args__ = (
        UniqueConstraint("session_id", "consultation_turn_id", name="uq_multimodal_turn_bundles_session_turn"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("multimodal_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consultation_turn_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    bundle_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
