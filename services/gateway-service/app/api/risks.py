from __future__ import annotations

from fastapi import APIRouter, Cookie, Header

from app.api.consultations import _proxy_error, _require_current_user
from app.clients.risk_client import forward_risk_request
from app.schemas.risks import (
    CreateRiskEvaluationRequest,
    OverrideRiskEvaluationRequest,
)

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.post("/evaluations")
def create_risk_evaluation(
    payload: CreateRiskEvaluationRequest,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_risk_request(
        "POST",
        "/api/v1/risk/evaluations",
        {
            "user_id": user["id"],
            "encounter_session_id": payload.encounter_session_id,
            "consultation_session_id": payload.consultation_session_id,
            "assessment_session_id": payload.assessment_session_id,
            "multimodal_session_id": payload.multimodal_session_id,
            "rule_set_id": payload.rule_set_id,
            "consultation_payload": payload.consultation_payload,
            "assessment_aggregate_payload": payload.assessment_aggregate_payload,
            "multimodal_feature_bundle": payload.multimodal_feature_bundle,
            "options": payload.options,
        },
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.get("/evaluations/{evaluation_id}")
def get_risk_evaluation(
    evaluation_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_risk_request(
        "GET",
        f"/api/v1/risk/evaluations/{evaluation_id}",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.get("/evaluations/{evaluation_id}/explanations")
def get_risk_explanation(
    evaluation_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_risk_request(
        "GET",
        f"/api/v1/risk/evaluations/{evaluation_id}/explanations",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.post("/evaluations/{evaluation_id}/override")
def override_risk_evaluation(
    evaluation_id: str,
    payload: OverrideRiskEvaluationRequest,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_risk_request(
        "POST",
        f"/api/v1/risk/evaluations/{evaluation_id}/override",
        payload.model_dump(),
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]
