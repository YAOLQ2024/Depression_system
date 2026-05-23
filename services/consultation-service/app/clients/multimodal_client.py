from __future__ import annotations

import base64
import json
import uuid
from urllib import error, request

from app.config import get_settings


def _forward_multimodal_request(
    method: str,
    path: str,
    payload: dict | None,
    acting_user_id: str,
) -> dict:
    settings = get_settings()
    target_url = f"{settings['multimodal_service_url']}{path}"
    headers = {
        "Accept": "application/json",
        "X-MCS-User-Id": acting_user_id,
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = request.Request(target_url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=120) as response:
            body = response.read().decode("utf-8")
            return {"status": response.status, "payload": json.loads(body)}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else "{}"
        try:
            payload_obj = json.loads(body)
        except json.JSONDecodeError:
            payload_obj = {"message": body or "multimodal service http error"}
        if "detail" in payload_obj and isinstance(payload_obj["detail"], dict):
            payload_obj = payload_obj["detail"]
        return {"status": exc.code, "payload": payload_obj}
    except error.URLError as exc:
        return {
            "status": 503,
            "payload": {
                "code": 5031,
                "message": f"multimodal service unavailable: {exc.reason}",
                "data": {},
            },
        }


def _encode_multipart_formdata(fields: dict[str, str], file_field: str, filename: str, content_type: str, file_bytes: bytes) -> tuple[bytes, str]:
    boundary = f"----MCSBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []
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
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(chunks), boundary


def _forward_multimodal_multipart_request(
    path: str,
    *,
    fields: dict[str, str],
    filename: str,
    content_type: str,
    file_bytes: bytes,
    acting_user_id: str,
) -> dict:
    settings = get_settings()
    target_url = f"{settings['multimodal_service_url']}{path}"
    body, boundary = _encode_multipart_formdata(fields, "image_file", filename, content_type, file_bytes)
    headers = {
        "Accept": "application/json",
        "X-MCS-User-Id": acting_user_id,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = request.Request(target_url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=20) as response:
            body_text = response.read().decode("utf-8")
            return {"status": response.status, "payload": json.loads(body_text)}
    except error.HTTPError as exc:
        body_text = exc.read().decode("utf-8") if exc.fp else "{}"
        try:
            payload_obj = json.loads(body_text)
        except json.JSONDecodeError:
            payload_obj = {"message": body_text or "multimodal service http error"}
        if "detail" in payload_obj and isinstance(payload_obj["detail"], dict):
            payload_obj = payload_obj["detail"]
        return {"status": exc.code, "payload": payload_obj}
    except error.URLError as exc:
        return {
            "status": 503,
            "payload": {
                "code": 5031,
                "message": f"multimodal service unavailable: {exc.reason}",
                "data": {},
            },
        }


def create_multimodal_session(
    *,
    user_id: str,
    encounter_session_id: str | None = None,
    flow_type: str,
    flow_run_id: str,
) -> dict:
    return _forward_multimodal_request(
        "POST",
        "/api/v1/multimodal/sessions",
        {
            "user_id": user_id,
            "encounter_session_id": encounter_session_id,
            "flow_type": flow_type,
            "flow_run_id": flow_run_id,
            "enabled_modalities": ["text", "audio", "face", "pose"],
        },
        acting_user_id=user_id,
    )

def get_multimodal_live(*, multimodal_session_id: str, acting_user_id: str) -> dict:
    return _forward_multimodal_request(
        "GET",
        f"/api/v1/multimodal/sessions/{multimodal_session_id}/live",
        None,
        acting_user_id=acting_user_id,
    )


def get_multimodal_turn_bundle(
    *,
    multimodal_session_id: str,
    turn_id: str,
    acting_user_id: str,
) -> dict:
    return _forward_multimodal_request(
        "GET",
        f"/api/v1/multimodal/sessions/{multimodal_session_id}/turns/{turn_id}/bundle",
        None,
        acting_user_id=acting_user_id,
    )


def clear_pose_turn_runtime(
    *,
    multimodal_session_id: str,
    turn_id: str,
    acting_user_id: str,
) -> dict:
    return _forward_multimodal_request(
        "POST",
        f"/api/v1/multimodal/sessions/{multimodal_session_id}/turns/{turn_id}/pose-runtime/clear",
        {},
        acting_user_id=acting_user_id,
    )


def submit_visual_capture(
    *,
    multimodal_session_id: str,
    flow_run_id: str,
    question_key: str,
    stage_id: str | None,
    turn_id: str | None,
    sample_started_at: str,
    sample_ended_at: str,
    sample_index: int,
    mime_type: str,
    file_bytes: bytes,
    filename: str,
    acting_user_id: str,
) -> dict:
    return _forward_multimodal_multipart_request(
        f"/api/v1/multimodal/sessions/{multimodal_session_id}/visual-captures",
        fields={
            "flow_run_id": flow_run_id,
            "question_key": question_key,
            **({"stage_id": stage_id} if stage_id else {}),
            "sample_started_at": sample_started_at,
            "sample_ended_at": sample_ended_at,
            "sample_index": str(sample_index),
            "mime_type": mime_type,
            **({"turn_id": turn_id} if turn_id else {}),
        },
        filename=filename,
        content_type=mime_type,
        file_bytes=file_bytes,
        acting_user_id=acting_user_id,
    )
