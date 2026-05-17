from __future__ import annotations

import json
import uuid
from urllib import error, request

from app.clients.identity_client import _forward_json_request_to_base_url
from app.config import get_settings


def forward_consultation_request(
    method: str,
    path: str,
    payload: dict | None,
    acting_user_id: str,
) -> dict:
    settings = get_settings()
    return _forward_json_request_to_base_url(
        base_url=settings["consultation_service_url"],
        method=method,
        path=path,
        payload=payload,
        extra_headers={"X-MCS-User-Id": acting_user_id},
        service_name="consultation service",
    )


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


def forward_consultation_multipart_request(
    path: str,
    *,
    fields: dict[str, str],
    filename: str,
    content_type: str,
    file_bytes: bytes,
    acting_user_id: str,
) -> dict:
    settings = get_settings()
    target_url = f"{settings['consultation_service_url']}{path}"
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
            payload_obj = {"message": body_text or "consultation service http error"}
        if "detail" in payload_obj and isinstance(payload_obj["detail"], dict):
            payload_obj = payload_obj["detail"]
        return {"status": exc.code, "payload": payload_obj}
    except error.URLError as exc:
        return {
            "status": 503,
            "payload": {
                "code": 5032,
                "message": f"consultation service unavailable: {exc.reason}",
                "data": {},
            },
        }
