from __future__ import annotations

from fastapi import APIRouter, Cookie, Header

from app.api.consultations import _proxy_error, _require_current_user
from app.clients.assessment_client import forward_assessment_request
from app.schemas.assessments import CreateAssessmentSessionRequest, SubmitAssessmentAnswerRequest

router = APIRouter(prefix="/api/v1/assessment", tags=["assessment"])


@router.get("/catalog")
def get_assessment_catalog(
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_assessment_request(
        "GET",
        "/api/v1/assessment/catalog",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.post("/sessions")
def create_assessment_session(
    payload: CreateAssessmentSessionRequest,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_assessment_request(
        "POST",
        "/api/v1/assessment/sessions",
        {
            "user_id": user["id"],
            "consultation_session_id": payload.consultation_session_id,
            "scale_handoff_payload": payload.scale_handoff_payload,
            "selected_scales": payload.selected_scales,
            "capture_context": payload.capture_context,
        },
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.get("/sessions/{session_id}")
def get_assessment_session(
    session_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_assessment_request(
        "GET",
        f"/api/v1/assessment/sessions/{session_id}",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.post("/sessions/{session_id}/answers")
def submit_assessment_answer(
    session_id: str,
    payload: SubmitAssessmentAnswerRequest,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    upstream_user = _require_current_user(mcs_session, authorization)
    _, user = upstream_user
    upstream = forward_assessment_request(
        "POST",
        f"/api/v1/assessment/sessions/{session_id}/answers",
        payload.model_dump(exclude_none=True),
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]
