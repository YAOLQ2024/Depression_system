from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from app.schemas.users import ProfileUpdateRequest
from app.services.auth import extract_bearer_token
from app.services.responses import error_response, success_response
from app.services.user_store import get_user_by_session_token, update_profile

router = APIRouter(prefix="/api/v1", tags=["users"])


def _require_user(authorization: str | None) -> tuple[str, dict]:
    session_token = extract_bearer_token(authorization)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response(message="missing session token", code=4011),
        )
    user = get_user_by_session_token(session_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response(message="session invalid or expired", code=4012),
        )
    return session_token, user


@router.get("/users/me")
def get_me(authorization: str | None = Header(default=None)):
    _, user = _require_user(authorization)
    return success_response({"user": user})


@router.put("/users/me/profile")
def put_profile(
    payload: ProfileUpdateRequest,
    authorization: str | None = Header(default=None),
):
    _, user = _require_user(authorization)
    updated = update_profile(user["id"], payload.model_dump(exclude_none=True))
    return success_response({"user": updated}, message="profile updated")
