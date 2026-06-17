from __future__ import annotations

from fastapi import APIRouter, Cookie, Header

from app.api.consultations import _proxy_error, _require_current_user
from app.clients.intervention_client import forward_intervention_request
from app.schemas.interventions import (
    CreateInterventionSessionRequest,
    RecordInterventionEventRequest,
)

router = APIRouter(prefix="/api/v1/interventions", tags=["interventions"])


@router.post("/sessions")
def create_intervention_session(
    payload: CreateInterventionSessionRequest,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_intervention_request(
        "POST",
        "/api/v1/interventions/sessions",
        {
            "user_id": user["id"],
            "encounter_session_id": payload.encounter_session_id,
            "consultation_session_id": payload.consultation_session_id,
            "assessment_session_id": payload.assessment_session_id,
            "plan_id": payload.plan_id,
            "risk_evaluation_id": payload.risk_evaluation_id,
            "source": payload.source,
            "metadata": payload.metadata,
        },
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.get("/sessions/{session_id}")
def get_intervention_session(
    session_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_intervention_request(
        "GET",
        f"/api/v1/interventions/sessions/{session_id}",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.get("/sessions/{session_id}/events")
def get_intervention_session_events(
    session_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_intervention_request(
        "GET",
        f"/api/v1/interventions/sessions/{session_id}/events",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.post("/sessions/{session_id}/events")
def record_intervention_event(
    session_id: str,
    payload: RecordInterventionEventRequest,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_intervention_request(
        "POST",
        f"/api/v1/interventions/sessions/{session_id}/events",
        payload.model_dump(exclude_none=True),
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]
