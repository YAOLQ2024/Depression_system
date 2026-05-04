from __future__ import annotations

from fastapi import APIRouter, Cookie, HTTPException, Response, status

from app.clients.identity_client import forward_json_request
from app.config import get_settings
from app.schemas.auth import LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/auth/register")
def register(payload: RegisterRequest):
    upstream = forward_json_request("POST", "/api/v1/auth/register", payload.model_dump())
    if upstream["status"] >= 400:
        raise HTTPException(status_code=upstream["status"], detail=upstream["payload"])
    return upstream["payload"]


@router.post("/auth/login")
def login(payload: LoginRequest, response: Response):
    settings = get_settings()
    upstream = forward_json_request("POST", "/api/v1/auth/login", payload.model_dump())
    if upstream["status"] >= 400:
        raise HTTPException(status_code=upstream["status"], detail=upstream["payload"])

    payload_body = upstream["payload"]
    data = dict(payload_body.get("data") or {})
    session_token = data.pop("session_token", None)
    if session_token:
        response.set_cookie(
            settings["session_cookie_name"],
            session_token,
            httponly=True,
            samesite="lax",
        )
    payload_body["data"] = data
    return payload_body


@router.post("/auth/logout")
def logout(response: Response, mcs_session: str | None = Cookie(default=None)):
    settings = get_settings()
    token = mcs_session
    if token:
        forward_json_request("POST", f"/api/v1/auth/logout?session_token={token}", None)
    response.delete_cookie(settings["session_cookie_name"])
    return {"code": 0, "message": "logged out", "data": {"logged_out": True}}
