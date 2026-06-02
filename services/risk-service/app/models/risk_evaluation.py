from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RiskEvaluation(Base):
    __tablename__ = "risk_evaluations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    encounter_session_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    consultation_session_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    assessment_session_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    multimodal_session_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    workflow_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rule_set_id: Mapped[str] = mapped_column(String(128), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    depression_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    depression_severity: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    safety_risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    consultation_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assessment_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    multimodal_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    input_summary_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
