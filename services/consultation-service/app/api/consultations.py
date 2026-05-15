from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from app.schemas.consultations import ConsultationTurnRequest, CreateConsultationSessionRequest
from app.services.consultation_engine import (
    ConsultationServiceError,
    complete_system_question_item,
    create_consultation_session,
    get_consultation_session,
    start_consultation_session,
    submit_consultation_turn,
)
from app.services.responses import error_response, success_response

router = APIRouter(prefix="/api/v1", tags=["consultations"])


def _translate_error(exc: ConsultationServiceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=error_response(message=exc.message, code=exc.code),
    )


@router.post("/consultations")
def post_consultation(
    payload: CreateConsultationSessionRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = create_consultation_session(payload, acting_user_id=x_mcs_user_id)
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"consultation": session_payload}, message="consultation session created")


@router.get("/consultations/{session_id}")
def get_consultation(session_id: str, x_mcs_user_id: str | None = Header(default=None)):
    try:
        session_payload = get_consultation_session(session_id, acting_user_id=x_mcs_user_id)
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"consultation": session_payload})


@router.post("/consultations/{session_id}/start")
def post_consultation_start(session_id: str, x_mcs_user_id: str | None = Header(default=None)):
    try:
        session_payload = start_consultation_session(session_id, acting_user_id=x_mcs_user_id)
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"consultation": session_payload}, message="consultation started")


@router.post("/consultations/{session_id}/question-items/{question_key}/complete")
def post_system_question_item_complete(
    session_id: str,
    question_key: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = complete_system_question_item(
            session_id,
            question_key=question_key,
            acting_user_id=x_mcs_user_id,
        )
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"consultation": session_payload}, message="system question item completed")


@router.post("/consultations/{session_id}/turns")
def post_consultation_turn(
    session_id: str,
    payload: ConsultationTurnRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = submit_consultation_turn(session_id, payload, acting_user_id=x_mcs_user_id)
    except ConsultationServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"consultation": session_payload}, message="consultation turn accepted")
