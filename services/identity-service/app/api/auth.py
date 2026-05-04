from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.responses import error_response, success_response
from app.services.user_store import (
    ROLE_CHOICES,
    authenticate_user,
    create_user,
    revoke_session,
)

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/auth/register")
def register(payload: RegisterRequest):
    try:
        user = create_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role="participant",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_response(message=str(exc), code=4090),
        ) from exc
    return success_response({"user": user}, message="registered")


@router.post("/auth/login")
def login(payload: LoginRequest):
    auth_result = authenticate_user(payload.email, payload.password)
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response(message="invalid credentials", code=4010),
        )
    return success_response(auth_result, message="logged in")


@router.post("/auth/logout")
def logout(session_token: str):
    revoke_session(session_token)
    return success_response({"logged_out": True}, message="logged out")


@router.get("/roles")
def list_roles():
    return success_response({"roles": ROLE_CHOICES})
