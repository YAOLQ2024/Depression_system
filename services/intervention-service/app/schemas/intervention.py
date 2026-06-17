from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateInterventionSessionRequest(BaseModel):
    user_id: str = Field(min_length=1)
    encounter_session_id: str | None = None
    consultation_session_id: str | None = None
    assessment_session_id: str | None = None
    plan_id: str | None = None
    risk_evaluation_id: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecordInterventionEventRequest(BaseModel):
    event_type: str = Field(min_length=1)
    program_id: str | None = None
    program_title: str | None = None
    delivery_mode: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
