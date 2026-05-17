from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateMultimodalSessionRequest(BaseModel):
    user_id: str = Field(min_length=1)
    owner_session_id: str = Field(min_length=1, description="Consultation session id")
    enabled_modalities: list[str] = Field(
        default_factory=lambda: ["text", "audio", "face", "pose"],
    )
    notes: str | None = None


class WarmupMultimodalSessionRequest(BaseModel):
    modalities: list[str] = Field(default_factory=lambda: ["text", "audio", "face", "pose"])


class SubmitAudioTurnRequest(BaseModel):
    consultation_turn_id: str = Field(min_length=1)
    audio_base64: str = Field(min_length=1)
    audio_format: str = Field(min_length=1)
    sampling_rate: int | None = None
    transcript_text: str | None = None
    captured_at: datetime | None = None
    frame_id: str | None = None


class SubmitFrameCaptureRequest(BaseModel):
    image_base64: str = Field(min_length=1)
    image_format: str = Field(min_length=1)
    consultation_turn_id: str | None = None
    captured_at: datetime | None = None
    frame_id: str | None = None


class MultimodalSessionSnapshot(BaseModel):
    id: str
    user_id: str
    owner_session_id: str
    status: str
    enabled_modalities: list[str]
    latest_live_payload: dict[str, Any]
    session_summary_payload: dict[str, Any] | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    warmed_up_at: datetime | None = None
    completed_at: datetime | None = None
