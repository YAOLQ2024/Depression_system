from __future__ import annotations

from fastapi import APIRouter, Cookie, Header, Request

from app.api.consultations import _proxy_error, _require_current_user
from app.clients.multimodal_client import (
    forward_multimodal_raw_request,
    forward_multimodal_request,
)

router = APIRouter(prefix="/api/v1/multimodal", tags=["multimodal"])


@router.post("/sessions")
async def create_multimodal_session(
    request: Request,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    payload = await request.json()
    upstream = forward_multimodal_request(
        "POST",
        "/api/v1/multimodal/sessions",
        payload,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.post("/sessions/{session_id}/audio-turns")
async def upload_audio_turn(
    session_id: str,
    request: Request,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    content_type = request.headers.get("content-type") or ""
    body = await request.body()
    upstream = forward_multimodal_raw_request(
        "POST",
        f"/api/v1/multimodal/sessions/{session_id}/audio-turns",
        body=body,
        content_type=content_type,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]
