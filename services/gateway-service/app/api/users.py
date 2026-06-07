from __future__ import annotations

from fastapi import APIRouter, Cookie, Header, HTTPException, status

from app.clients.identity_client import forward_json_request
from app.api.consultations import _require_session_token
from app.schemas.users import PreparationStateUpdateRequest, ProfileUpdateRequest

router = APIRouter(prefix="/api/v1", tags=["users"])


@router.get("/users/me")
def get_me(
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    token = _require_session_token(mcs_session, authorization)
    upstream = forward_json_request("GET", "/api/v1/users/me", None, session_token=token)
    if upstream["status"] >= 400:
        raise HTTPException(status_code=upstream["status"], detail=upstream["payload"])
    return upstream["payload"]


@router.put("/users/me/profile")
def update_my_profile(
    payload: ProfileUpdateRequest,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    token = _require_session_token(mcs_session, authorization)
    upstream = forward_json_request(
        "PUT",
        "/api/v1/users/me/profile",
        payload.model_dump(exclude_none=True),
        session_token=token,
    )
    if upstream["status"] >= 400:
        raise HTTPException(status_code=upstream["status"], detail=upstream["payload"])
    return upstream["payload"]


@router.get("/users/me/preparation-state")
def get_my_preparation_state(
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    token = _require_session_token(mcs_session, authorization)
    upstream = forward_json_request("GET", "/api/v1/users/me/preparation-state", None, session_token=token)
    if upstream["status"] >= 400:
        raise HTTPException(status_code=upstream["status"], detail=upstream["payload"])
    return upstream["payload"]


@router.put("/users/me/preparation-state")
def update_my_preparation_state(
    payload: PreparationStateUpdateRequest,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    token = _require_session_token(mcs_session, authorization)
    upstream = forward_json_request(
        "PUT",
        "/api/v1/users/me/preparation-state",
        payload.model_dump(mode="json", exclude_unset=True),
        session_token=token,
    )
    if upstream["status"] >= 400:
        raise HTTPException(status_code=upstream["status"], detail=upstream["payload"])
    return upstream["payload"]
