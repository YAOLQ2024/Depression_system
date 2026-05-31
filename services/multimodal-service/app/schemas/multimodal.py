from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from app.services.multimodal_session_scope import (
    is_encounter_scope,
    normalize_identifier,
    normalize_scope_pair,
)


class MultimodalStageContext(BaseModel):
    stage_id: str = Field(min_length=1)
    stage_label: str = Field(min_length=1)
    stage_order: int = Field(ge=1)


class CreateMultimodalSessionRequest(BaseModel):
    encounter_session_id: str | None = None
    scope_type: str | None = None
    scope_id: str | None = None
    flow_type: str | None = None
    flow_run_id: str | None = None
    user_id: str | None = None
    stage_context: MultimodalStageContext | None = None
    enabled_modalities: list[str] = Field(
        default_factory=lambda: ["text", "audio", "face", "pose"],
    )
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_scope(self) -> "CreateMultimodalSessionRequest":
        has_scope = bool(str(self.scope_type or "").strip()) or bool(
            str(self.scope_id or "").strip()
        )
        has_flow = bool(str(self.flow_type or "").strip()) or bool(
            str(self.flow_run_id or "").strip()
        )
        if has_scope:
            if not str(self.scope_type or "").strip() or not str(
                self.scope_id or ""
            ).strip():
                raise ValueError("scope_type and scope_id must be provided together")
        if has_flow:
            if not str(self.flow_type or "").strip() or not str(
                self.flow_run_id or ""
            ).strip():
                raise ValueError("flow_type and flow_run_id must be provided together")
        if not has_scope and not has_flow:
            raise ValueError(
                "either scope_type/scope_id or flow_type/flow_run_id is required"
            )
        normalized_scope_type, normalized_scope_id = normalize_scope_pair(
            self.scope_type,
            self.scope_id,
        )
        normalized_encounter_session_id = normalize_identifier(
            self.encounter_session_id
        )
        if is_encounter_scope(normalized_scope_type):
            encounter_scope_id = (
                normalized_encounter_session_id or normalized_scope_id
            )
            if not encounter_scope_id:
                raise ValueError(
                    "encounter scope requires encounter_session_id or scope_id"
                )
            if (
                normalized_encounter_session_id
                and normalized_scope_id
                and normalized_encounter_session_id != normalized_scope_id
            ):
                raise ValueError(
                    "encounter_session_id must match scope_id for encounter scope"
                )
            if not normalized_encounter_session_id and normalized_scope_id:
                self.encounter_session_id = normalized_scope_id
        return self


class WarmupMultimodalSessionRequest(BaseModel):
    modalities: list[str] = Field(default_factory=lambda: ["text", "audio", "face", "pose"])


class SubmitAudioTurnRequest(BaseModel):
    turn_id: str = Field(min_length=1)
    flow_run_id: str = Field(min_length=1)
    origin_flow_type: str | None = None
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
    origin_flow_type: str | None = None
    question_key: str = Field(min_length=1)
    stage_id: str | None = None
    image_bytes: bytes | None = Field(default=None, min_length=1)
    image_base64: str | None = None
    image_format: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    turn_id: str | None = None
    sample_started_at: datetime
    sample_ended_at: datetime
    sample_index: int = Field(ge=0)
    frame_id: str | None = None

    _image_bytes_cache: bytes | None = PrivateAttr(default=None)
    _image_base64_cache: str | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _ensure_image_source(self) -> "SubmitFrameCaptureRequest":
        normalized_base64 = str(self.image_base64 or "").strip()
        if self.image_bytes is None and not normalized_base64:
            raise ValueError("either image_bytes or image_base64 is required")
        if self.image_base64 is not None and not normalized_base64:
            self.image_base64 = None
        return self

    def require_image_bytes(self) -> bytes:
        if self.image_bytes is not None:
            return self.image_bytes
        if self._image_bytes_cache is None:
            self._image_bytes_cache = base64.b64decode(
                self.require_image_base64(),
                validate=True,
            )
        return self._image_bytes_cache

    def require_image_base64(self) -> str:
        normalized = str(self.image_base64 or "").strip()
        if normalized:
            return normalized
        if self._image_base64_cache is None:
            self._image_base64_cache = base64.b64encode(
                self.require_image_bytes()
            ).decode("ascii")
        return self._image_base64_cache

    def image_bytes_length(self) -> int:
        return len(self.require_image_bytes())


class MultimodalSessionSnapshot(BaseModel):
    id: str
    session_id: str | None = None
    user_id: str | None = None
    encounter_session_id: str | None = None
    scope_type: str
    scope_id: str
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
