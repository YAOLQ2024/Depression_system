from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ConsultationInputType = Literal[
    "speech",
    "manual_input",
    "continue_button",
    "silence",
    "recognition_failure",
]


class CreateConsultationRequest(BaseModel):
    device_status: dict[str, Any] = Field(default_factory=dict)
    audio_channel_ready: bool = True
    consent_confirmed: bool = True
    consultation_ready_state: str = "ready"
    assigned_doctor_persona: str | None = None


class ConsultationTurnRequest(BaseModel):
    input_type: ConsultationInputType
    turn_id: str | None = None
    raw_input: str | None = None
    audio_uri: str | None = None
    transcript_text: str | None = None
    transcript_source: str | None = None
    response_started_at: datetime | None = None
    response_completed_at: datetime | None = None
