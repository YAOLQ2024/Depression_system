from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateAssessmentSessionRequest(BaseModel):
    user_id: str = Field(min_length=1)
    consultation_session_id: str | None = None
    scale_handoff_payload: dict[str, Any] = Field(default_factory=dict)
    selected_scales: list[str] = Field(default_factory=list)
    capture_context: dict[str, Any] = Field(default_factory=dict)


class SubmitAssessmentAnswerRequest(BaseModel):
    item_id: str | None = None
    selected_option_score: int | None = None
    selected_option_label: str | None = None
    raw_input: str | None = None
    capture_timestamp: datetime | None = None
