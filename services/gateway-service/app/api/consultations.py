from __future__ import annotations

from fastapi import APIRouter, Cookie, HTTPException, status

from app.clients.consultation_client import forward_consultation_request
from app.clients.identity_client import forward_json_request
from app.schemas.consultations import ConsultationTurnRequest, CreateConsultationRequest

router = APIRouter(prefix="/api/v1", tags=["consultations"])


def _require_session_token(cookie_value: str | None) -> str:
    if cookie_value:
        return cookie_value
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": 4010, "message": "missing session cookie", "data": {}},
    )


def _require_current_user(mcs_session: str | None) -> tuple[str, dict]:
    token = _require_session_token(mcs_session)
    upstream = forward_json_request("GET", "/api/v1/users/me", None, session_token=token)
    if upstream["status"] >= 400:
        raise HTTPException(status_code=upstream["status"], detail=upstream["payload"])
    user = (upstream["payload"].get("data") or {}).get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4012, "message": "session invalid or expired", "data": {}},
        )
    return token, user


def _proxy_error(upstream: dict) -> HTTPException:
    return HTTPException(status_code=upstream["status"], detail=upstream["payload"])


@router.post("/consultations")
def create_consultation(
    payload: CreateConsultationRequest,
    mcs_session: str | None = Cookie(default=None),
):
    _, user = _require_current_user(mcs_session)
    consultation_payload = {
        "user_id": user["id"],
        "participant_profile_snapshot": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "profile_status": user["profile_status"],
            **(user.get("profile") or {}),
        },
        "device_status": payload.device_status,
        "audio_channel_ready": payload.audio_channel_ready,
        "consent_confirmed": payload.consent_confirmed,
        "consultation_ready_state": payload.consultation_ready_state,
    }
    upstream = forward_consultation_request(
        "POST",
        "/api/v1/consultations",
        consultation_payload,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.get("/consultations/{session_id}")
def get_consultation(
    session_id: str,
    mcs_session: str | None = Cookie(default=None),
):
    _, user = _require_current_user(mcs_session)
    upstream = forward_consultation_request(
        "GET",
        f"/api/v1/consultations/{session_id}",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.post("/consultations/{session_id}/start")
def start_consultation(
    session_id: str,
    mcs_session: str | None = Cookie(default=None),
):
    _, user = _require_current_user(mcs_session)
    upstream = forward_consultation_request(
        "POST",
        f"/api/v1/consultations/{session_id}/start",
        {},
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.post("/consultations/{session_id}/turns")
def submit_consultation_turn(
    session_id: str,
    payload: ConsultationTurnRequest,
    mcs_session: str | None = Cookie(default=None),
):
    _, user = _require_current_user(mcs_session)
    upstream = forward_consultation_request(
        "POST",
        f"/api/v1/consultations/{session_id}/turns",
        payload.model_dump(exclude_none=True),
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]
