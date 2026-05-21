from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MultimodalStageContext(BaseModel):
    stage_id: str = Field(min_length=1)
    stage_label: str = Field(min_length=1)
    stage_order: int = Field(ge=1)


class CreateMultimodalSessionRequest(BaseModel):
    encounter_session_id: str | None = None
    flow_type: str = Field(min_length=1)
    flow_run_id: str = Field(min_length=1)
    user_id: str | None = None
    stage_context: MultimodalStageContext | None = None
    enabled_modalities: list[str] = Field(
        default_factory=lambda: ["text", "audio", "face", "pose"],
    )
    notes: str | None = None


class WarmupMultimodalSessionRequest(BaseModel):
    modalities: list[str] = Field(default_factory=lambda: ["text", "audio", "face", "pose"])


class SubmitAudioTurnRequest(BaseModel):
    turn_id: str = Field(min_length=1)
    flow_run_id: str = Field(min_length=1)
    question_key: str | None = None
    stage_id: str | None = None
    audio_base64: str | None = None
    audio_format: str | None = None
    sampling_rate: int | None = None
    transcript_text: str | None = None
    original_audio_uri: str | None = None
    original_mime_type: str | None = None
    source_filename: str | None = None
    normalized_wav_uri: str | None = None
    captured_at: datetime | None = None
    frame_id: str | None = None


class SubmitFrameCaptureRequest(BaseModel):
    flow_run_id: str = Field(min_length=1)
    question_key: str = Field(min_length=1)
    stage_id: str | None = None
    image_base64: str = Field(min_length=1)
    image_format: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    turn_id: str | None = None
    sample_started_at: datetime
    sample_ended_at: datetime
    sample_index: int = Field(ge=0)
    frame_id: str | None = None


class MultimodalSessionSnapshot(BaseModel):
    id: str
    session_id: str | None = None
    user_id: str | None = None
    encounter_session_id: str | None = None
    flow_type: str | None = None
    flow_run_id: str | None = None
    status: str
    stage_context: dict[str, Any] = Field(default_factory=dict)
    enabled_modalities: list[str] = Field(default_factory=list)
    live_state_payload: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    started_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    warmed_up_at: datetime | None = None
    completed_at: datetime | None = None
