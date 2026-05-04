from __future__ import annotations

from fastapi import APIRouter, Cookie, HTTPException, status

from app.clients.identity_client import forward_json_request
from app.config import get_settings
from app.schemas.users import ProfileUpdateRequest

router = APIRouter(prefix="/api/v1", tags=["users"])


def _require_session_token(cookie_value: str | None) -> str:
    if cookie_value:
        return cookie_value
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": 4010, "message": "missing session cookie", "data": {}},
    )


@router.get("/users/me")
def get_me(mcs_session: str | None = Cookie(default=None)):
    token = _require_session_token(mcs_session)
    upstream = forward_json_request("GET", "/api/v1/users/me", None, session_token=token)
    if upstream["status"] >= 400:
        raise HTTPException(status_code=upstream["status"], detail=upstream["payload"])
    return upstream["payload"]


@router.put("/users/me/profile")
def update_my_profile(
    payload: ProfileUpdateRequest,
    mcs_session: str | None = Cookie(default=None),
):
    token = _require_session_token(mcs_session)
    upstream = forward_json_request(
        "PUT",
        "/api/v1/users/me/profile",
        payload.model_dump(exclude_none=True),
        session_token=token,
    )
    if upstream["status"] >= 400:
        raise HTTPException(status_code=upstream["status"], detail=upstream["payload"])
    return upstream["payload"]
