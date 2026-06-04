from __future__ import annotations

from fastapi import APIRouter, Cookie, Header
from fastapi.responses import StreamingResponse

from app.api.consultations import _proxy_error, _require_current_user
from app.clients.assessment_client import (
    forward_assessment_request,
    open_assessment_event_stream,
)
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
            "encounter_session_id": payload.encounter_session_id,
            "source_consultation_flow_run_id": (
                payload.source_consultation_flow_run_id
            ),
            "multimodal_session_id": payload.multimodal_session_id,
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


@router.get("/sessions/{session_id}/scales/{scale_slug}/detail")
def get_assessment_scale_detail(
    session_id: str,
    scale_slug: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> dict:
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_assessment_request(
        "GET",
        f"/api/v1/assessment/sessions/{session_id}/scales/{scale_slug}/detail",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.get("/sessions/{session_id}/multimodal/live")
def get_assessment_multimodal_live(
    session_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_assessment_request(
        "GET",
        f"/api/v1/assessment/sessions/{session_id}/multimodal/live",
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


@router.get("/sessions/{session_id}/multimodal/live/stream")
def get_assessment_multimodal_live_stream(
    session_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = open_assessment_event_stream(
        f"/api/v1/assessment/sessions/{session_id}/multimodal/live/stream",
        acting_user_id=user["id"],
    )
    if isinstance(upstream, dict):
        raise _proxy_error(upstream)
    return StreamingResponse(
        upstream.iter_bytes(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/turns/{turn_id}/multimodal/bundle")
def get_assessment_turn_multimodal_bundle(
    session_id: str,
    turn_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_assessment_request(
        "GET",
        f"/api/v1/assessment/sessions/{session_id}/turns/{turn_id}/multimodal/bundle",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.post("/sessions/{session_id}/turns/{turn_id}/multimodal/recover")
def recover_assessment_turn_multimodal_hot_state(
    session_id: str,
    turn_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_assessment_request(
        "POST",
        f"/api/v1/assessment/sessions/{session_id}/turns/{turn_id}/multimodal/recover",
        {},
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]
