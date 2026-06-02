from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RiskTrigger(Base):
    __tablename__ = "risk_triggers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    evaluation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("risk_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_key: Mapped[str] = mapped_column(String(128), nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(128), nullable=False)
    trigger_effect: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_summary: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    evidence_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
