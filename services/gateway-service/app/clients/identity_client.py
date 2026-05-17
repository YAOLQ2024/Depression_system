from __future__ import annotations

import json
from urllib import error, request

from app.config import get_settings


def _forward_json_request_to_base_url(
    base_url: str,
    method: str,
    path: str,
    payload: dict | None,
    session_token: str | None = None,
    extra_headers: dict[str, str] | None = None,
    service_name: str = "upstream service",
) -> dict:
    target_url = f"{base_url}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    if session_token:
        headers["Authorization"] = f"Bearer {session_token}"
    if extra_headers:
        headers.update(extra_headers)

    req = request.Request(
        target_url, data=data, headers=headers, method=method
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return {"status": response.status, "payload": json.loads(body)}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else "{}"
        try:
            payload_obj = json.loads(body)
        except json.JSONDecodeError:
            payload_obj = {"message": body or "upstream http error"}
        if "detail" in payload_obj and isinstance(payload_obj["detail"], dict):
            payload_obj = payload_obj["detail"]
        return {"status": exc.code, "payload": payload_obj}
    except error.URLError as exc:
        return {
            "status": 503,
            "payload": {
                "code": 5030,
                "message": f"{service_name} unavailable: {exc.reason}",
                "data": {},
            },
        }


def forward_json_request(
    method: str,
    path: str,
    payload: dict | None,
    session_token: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict:
    settings = get_settings()
    return _forward_json_request_to_base_url(
        base_url=settings["identity_service_url"],
        method=method,
        path=path,
        payload=payload,
        session_token=session_token,
        extra_headers=extra_headers,
        service_name="identity service",
    )
