from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class CreateAssessmentSessionRequest(BaseModel):
    encounter_session_id: str | None = None
    source_consultation_flow_run_id: str | None = None
    multimodal_session_id: str | None = None
    scale_handoff_payload: dict[str, Any] = Field(default_factory=dict)
    selected_scales: list[str] = Field(default_factory=list)
    capture_context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_multimodal_binding(self) -> "CreateAssessmentSessionRequest":
        if str(self.multimodal_session_id or "").strip():
            return self
        if not str(self.encounter_session_id or "").strip():
            raise ValueError(
                "encounter_session_id is required when multimodal_session_id is missing"
            )
        return self


class SubmitAssessmentAnswerRequest(BaseModel):
    item_id: str | None = None
    selected_option_score: int | None = None
    selected_option_label: str | None = None
    question_key: str | None = None
    turn_id: str | None = None
    answer_source: str | None = None
    raw_input: str | None = None
    transcript_text: str | None = None
    transcript_source: str | None = None
    audio_uri: str | None = None
    original_audio_uri: str | None = None
    normalized_wav_uri: str | None = None
    multimodal_session_id: str | None = None
    response_started_at: datetime | None = None
    response_completed_at: datetime | None = None
    capture_timestamp: datetime | None = None
