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


class ConsultationTurnRequest(BaseModel):
    input_type: ConsultationInputType
    raw_input: str | None = None
    audio_uri: str | None = None
    transcript_text: str | None = None
    audio_base64: str | None = None
    audio_format: str | None = None
    sampling_rate: int | None = None
    audio_uri: str | None = None
    response_started_at: datetime | None = None
    response_completed_at: datetime | None = None


class ConsultationSubtitlePreviewRequest(BaseModel):
    prompt_key: str = Field(min_length=1)
    transcript_text: str = Field(min_length=1)
    source: Literal["dolphin_preview", "browser_fallback"]
