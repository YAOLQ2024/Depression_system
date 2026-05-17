from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateConsultationSessionRequest(BaseModel):
    user_id: str = Field(min_length=1)
    participant_profile_snapshot: dict[str, Any] = Field(default_factory=dict)
    device_status: dict[str, Any] = Field(default_factory=dict)
    assigned_doctor_persona: str | None = None
    audio_channel_ready: bool = True
    consent_confirmed: bool = True
    consultation_ready_state: str = "ready"


class ConsultationTurnRequest(BaseModel):
    input_type: Literal[
        "speech",
        "manual_input",
        "continue_button",
        "silence",
        "recognition_failure",
    ]
    raw_input: str | None = None
    transcript_text: str | None = None
    response_started_at: datetime | None = None
    response_completed_at: datetime | None = None
