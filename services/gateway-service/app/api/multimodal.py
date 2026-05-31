from __future__ import annotations

from fastapi import APIRouter, Cookie, File, Form, Header, Request, UploadFile

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
    payload.pop("user_id", None)
    upstream = forward_multimodal_request(
        "POST",
        "/api/v1/multimodal/sessions",
        payload,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.post("/sessions/{session_id}/warmup")
async def warmup_multimodal_session(
    session_id: str,
    request: Request,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    payload = await request.json()
    upstream = forward_multimodal_request(
        "POST",
        f"/api/v1/multimodal/sessions/{session_id}/warmup",
        payload,
        acting_user_id=user["id"],
        timeout_seconds=60,
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


@router.get("/sessions/{session_id}/audio-turns/{audio_turn_id}")
async def get_audio_turn_status(
    session_id: str,
    audio_turn_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_multimodal_request(
        "GET",
        f"/api/v1/multimodal/sessions/{session_id}/audio-turns/{audio_turn_id}",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.post("/sessions/{session_id}/visual-captures")
async def upload_visual_capture(
    session_id: str,
    flow_run_id: str = Form(...),
    origin_flow_type: str | None = Form(default=None),
    question_key: str = Form(...),
    stage_id: str | None = Form(default=None),
    turn_id: str | None = Form(default=None),
    sample_started_at: str = Form(...),
    sample_ended_at: str = Form(...),
    sample_index: int = Form(...),
    mime_type: str = Form(...),
    image_file: UploadFile = File(...),
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    content_type = mime_type or image_file.content_type or "image/jpeg"
    file_bytes = await image_file.read()
    request_body, request_content_type = request_content_type_for_multipart(
        flow_run_id=flow_run_id,
        origin_flow_type=origin_flow_type,
        question_key=question_key,
        stage_id=stage_id,
        turn_id=turn_id,
        sample_started_at=sample_started_at,
        sample_ended_at=sample_ended_at,
        sample_index=sample_index,
        mime_type=content_type,
        filename=image_file.filename or f"visual-{sample_index}.jpg",
        file_bytes=file_bytes,
    )
    upstream = forward_multimodal_raw_request(
        "POST",
        f"/api/v1/multimodal/sessions/{session_id}/visual-captures",
        body=request_body,
        content_type=request_content_type,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


def request_content_type_for_multipart(
    *,
    flow_run_id: str,
    origin_flow_type: str | None,
    question_key: str,
    stage_id: str | None,
    turn_id: str | None,
    sample_started_at: str,
    sample_ended_at: str,
    sample_index: int,
    mime_type: str,
    filename: str,
    file_bytes: bytes,
) -> tuple[bytes, str]:
    boundary = "----MCSGatewayBoundary"
    chunks: list[bytes] = []
    fields = {
        "flow_run_id": flow_run_id,
        **({"origin_flow_type": origin_flow_type} if origin_flow_type else {}),
        "question_key": question_key,
        "sample_started_at": sample_started_at,
        "sample_ended_at": sample_ended_at,
        "sample_index": str(sample_index),
        "mime_type": mime_type,
        **({"stage_id": stage_id} if stage_id else {}),
        **({"turn_id": turn_id} if turn_id else {}),
    }
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="image_file"; filename="{filename}"\r\n'.encode("utf-8"),
            f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


@router.get("/sessions/{session_id}/live")
async def get_multimodal_live(
    session_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_multimodal_request(
        "GET",
        f"/api/v1/multimodal/sessions/{session_id}/live",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]


@router.get("/sessions/{session_id}/turns/{turn_id}/bundle")
async def get_multimodal_turn_bundle(
    session_id: str,
    turn_id: str,
    mcs_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    _, user = _require_current_user(mcs_session, authorization)
    upstream = forward_multimodal_request(
        "GET",
        f"/api/v1/multimodal/sessions/{session_id}/turns/{turn_id}/bundle",
        None,
        acting_user_id=user["id"],
    )
    if upstream["status"] >= 400:
        raise _proxy_error(upstream)
    return upstream["payload"]
