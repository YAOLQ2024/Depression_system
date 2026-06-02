from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateRiskEvaluationRequest(BaseModel):
    user_id: str = Field(min_length=1)
    encounter_session_id: str | None = None
    consultation_session_id: str | None = None
    assessment_session_id: str | None = None
    multimodal_session_id: str | None = None
    rule_set_id: str | None = None
    consultation_payload: dict[str, Any] = Field(default_factory=dict)
    assessment_aggregate_payload: dict[str, Any] = Field(default_factory=dict)
    multimodal_feature_bundle: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class OverrideRiskEvaluationRequest(BaseModel):
    override_risk_level: str | None = None
    review_decision: str | None = None
    review_note: str | None = None
    reviewer_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
