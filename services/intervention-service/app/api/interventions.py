from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.schemas.intervention import (
    CreateInterventionSessionRequest,
    RecordInterventionEventRequest,
)
from app.services.intervention_engine import (
    InterventionServiceError,
    create_intervention_session,
    get_intervention_session,
    list_intervention_session_events,
    record_intervention_event,
)
from app.services.responses import error_response, success_response

router = APIRouter(prefix="/api/v1/interventions", tags=["interventions"])


def _translate_error(exc: InterventionServiceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=error_response(message=exc.message, code=exc.code),
    )


@router.post("/sessions")
def post_intervention_session(
    payload: CreateInterventionSessionRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = create_intervention_session(
            payload,
            acting_user_id=x_mcs_user_id,
        )
    except InterventionServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(
        {"intervention_session": session_payload},
        message="intervention session created",
    )


@router.get("/sessions/{session_id}")
def get_intervention_session_by_id(
    session_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        session_payload = get_intervention_session(
            session_id,
            acting_user_id=x_mcs_user_id,
        )
    except InterventionServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"intervention_session": session_payload})


@router.get("/sessions/{session_id}/events")
def get_intervention_session_events(
    session_id: str,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        events = list_intervention_session_events(
            session_id,
            acting_user_id=x_mcs_user_id,
        )
    except InterventionServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response({"events": events})


@router.post("/sessions/{session_id}/events")
def post_intervention_session_event(
    session_id: str,
    payload: RecordInterventionEventRequest,
    x_mcs_user_id: str | None = Header(default=None),
):
    try:
        event_payload = record_intervention_event(
            session_id,
            payload,
            acting_user_id=x_mcs_user_id,
        )
    except InterventionServiceError as exc:
        raise _translate_error(exc) from exc
    return success_response(
        event_payload,
        message="intervention event recorded",
    )
