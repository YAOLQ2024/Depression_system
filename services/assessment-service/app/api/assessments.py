from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.schemas.assessment import CreateAssessmentSessionRequest, SubmitAssessmentAnswerRequest
from app.services.assessment_engine import (
    AssessmentServiceError,
    create_assessment_session,
    get_assessment_catalog,
    get_assessment_session,
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


@router.post("/sessions/{session_id}/answers")
def post_assessment_answer(
    session_id: str,
    payload: SubmitAssessmentAnswerRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = submit_assessment_answer(session_id, payload, acting_user_id=x_mcs_user_id)
    except AssessmentServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"assessment_session": session_payload}, message="assessment answer accepted")
