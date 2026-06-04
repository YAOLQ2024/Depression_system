from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.assessment import CreateAssessmentSessionRequest, SubmitAssessmentAnswerRequest
from app.services.assessment_engine import (
    AssessmentServiceError,
    create_assessment_session,
    get_assessment_multimodal_live,
    get_assessment_catalog,
    get_assessment_scale_detail,
    get_assessment_session,
    get_assessment_turn_multimodal_bundle,
    recover_assessment_turn_hot_state,
    stream_assessment_multimodal_live,
    submit_assessment_answer,
)
from app.services.responses import error_response, success_response

router = APIRouter(prefix="/api/v1/assessment", tags=["assessment"])


def _translate_error(exc: AssessmentServiceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=error_response(message=exc.message, code=exc.code),
    )


@router.get("/catalog")
def get_catalog():
    try:
        catalog = get_assessment_catalog()
    except AssessmentServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"catalog": catalog})


@router.post("/sessions")
def post_assessment_session(
    payload: CreateAssessmentSessionRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = create_assessment_session(payload, acting_user_id=x_mcs_user_id)
    except AssessmentServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"assessment_session": session_payload}, message="assessment session created")


@router.get("/sessions/{session_id}")
def get_assessment(session_id: str, x_mcs_user_id: str | None = Header(default=None)):
    try:
        session_payload = get_assessment_session(session_id, acting_user_id=x_mcs_user_id)
    except AssessmentServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"assessment_session": session_payload})


@router.get("/sessions/{session_id}/scales/{scale_slug}/detail")
def get_assessment_scale_detail_route(
    session_id: str,
    scale_slug: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        scale_detail_payload = get_assessment_scale_detail(
            session_id,
            scale_slug,
            acting_user_id=x_mcs_user_id,
        )
    except AssessmentServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"scale_detail": scale_detail_payload})

@router.get("/sessions/{session_id}/multimodal/live")
def get_assessment_live(session_id: str, x_mcs_user_id: str | None = Header(default=None)):
    try:
        live_payload = get_assessment_multimodal_live(session_id, acting_user_id=x_mcs_user_id)
    except AssessmentServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(live_payload)


@router.post("/sessions/{session_id}/answers")
def post_assessment_answer(
    session_id: str,
    payload: SubmitAssessmentAnswerRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        response_payload = submit_assessment_answer(session_id, payload, acting_user_id=x_mcs_user_id)
    except AssessmentServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(response_payload, message="assessment answer accepted")


@router.get("/sessions/{session_id}/multimodal/live/stream")
def get_assessment_live_stream(
    session_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        upstream_stream = stream_assessment_multimodal_live(
            session_id,
            acting_user_id=x_mcs_user_id,
        )
    except AssessmentServiceError as exc:
        raise _translate_error(exc) from exc
    return StreamingResponse(
        upstream_stream.iter_bytes(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/turns/{turn_id}/multimodal/bundle")
def get_assessment_turn_bundle(
    session_id: str,
    turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        bundle_payload = get_assessment_turn_multimodal_bundle(
            session_id,
            turn_id,
            acting_user_id=x_mcs_user_id,
        )
    except AssessmentServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(bundle_payload)


@router.post("/sessions/{session_id}/turns/{turn_id}/multimodal/recover")
def post_assessment_turn_recover(
    session_id: str,
    turn_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        payload = recover_assessment_turn_hot_state(
            session_id,
            turn_id,
            acting_user_id=x_mcs_user_id,
        )
    except AssessmentServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(payload, message="assessment multimodal turn recovered")
