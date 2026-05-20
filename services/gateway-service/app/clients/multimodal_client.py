from __future__ import annotations

import json
import socket
from urllib import error, request

from app.config import get_settings


def _handle_upstream_response(response: request.addinfourl) -> dict:
    body = response.read().decode("utf-8")
    return {"status": response.status, "payload": json.loads(body)}


def _handle_upstream_error(exc: error.HTTPError) -> dict:
    body = exc.read().decode("utf-8") if exc.fp else "{}"
    try:
        payload_obj = json.loads(body)
    except json.JSONDecodeError:
        payload_obj = {"message": body or "upstream http error"}
    if "detail" in payload_obj and isinstance(payload_obj["detail"], dict):
        payload_obj = payload_obj["detail"]
    return {"status": exc.code, "payload": payload_obj}


def _handle_unavailable(exc: error.URLError) -> dict:
    return {
        "status": 503,
        "payload": {
            "code": 5030,
            "message": f"multimodal service unavailable: {exc.reason}",
            "data": {},
        },
    }


def _handle_timeout(timeout_seconds: int | float) -> dict:
    return {
        "status": 504,
        "payload": {
            "code": 5040,
            "message": (
                "multimodal service request timed out "
                f"after {timeout_seconds} seconds"
            ),
            "data": {},
        },
    }


def forward_multimodal_request(
    method: str,
    path: str,
    payload: dict | None,
    acting_user_id: str,
    timeout_seconds: int = 15,
) -> dict:
    settings = get_settings()
    target_url = f"{settings['multimodal_service_url']}{path}"
    data = None
    headers = {
        "Accept": "application/json",
        "X-MCS-User-Id": acting_user_id,
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    req = request.Request(target_url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return _handle_upstream_response(response)
    except error.HTTPError as exc:
        return _handle_upstream_error(exc)
    except (TimeoutError, socket.timeout):
        return _handle_timeout(timeout_seconds)
    except error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            return _handle_timeout(timeout_seconds)
        return _handle_unavailable(exc)


def forward_multimodal_raw_request(
    method: str,
    path: str,
    body: bytes,
    content_type: str,
    acting_user_id: str,
    timeout_seconds: int = 30,
) -> dict:
    settings = get_settings()
    target_url = f"{settings['multimodal_service_url']}{path}"
    headers = {
        "Accept": "application/json",
        "Content-Type": content_type,
        "X-MCS-User-Id": acting_user_id,
    }
    req = request.Request(target_url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return _handle_upstream_response(response)
    except error.HTTPError as exc:
        return _handle_upstream_error(exc)
    except (TimeoutError, socket.timeout):
        return _handle_timeout(timeout_seconds)
    except error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            return _handle_timeout(timeout_seconds)
        return _handle_unavailable(exc)
