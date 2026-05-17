from __future__ import annotations

from pydantic import BaseModel, Field


class TextEmotionInferRequest(BaseModel):
    text: str = Field(..., description="Input text content")
    session_id: str | None = Field(default=None)
    frame_id: str | None = Field(default=None)
    timestamp: str | None = Field(default=None, description="ISO 8601 timestamp")


class AudioEmotionInferRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded audio bytes")
    audio_format: str = Field(..., description="Audio format, e.g. wav/flac/ogg/pcm_f32le")
    sampling_rate: int | None = Field(default=None, description="Sampling rate for raw PCM")
    session_id: str | None = Field(default=None)
    frame_id: str | None = Field(default=None)
    timestamp: str | None = Field(default=None, description="ISO 8601 timestamp")


class FrameEmotionInferRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image bytes")
    image_format: str = Field(..., description="Image format, e.g. jpeg/png")
    session_id: str | None = Field(default=None)
    frame_id: str | None = Field(default=None)
    timestamp: str | None = Field(default=None, description="ISO 8601 timestamp")
