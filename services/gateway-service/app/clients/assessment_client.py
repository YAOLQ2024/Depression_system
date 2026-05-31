from __future__ import annotations

import json
from urllib import error, request

from app.clients.identity_client import _forward_json_request_to_base_url
from app.config import get_settings


class UpstreamEventStream:
    def __init__(self, response) -> None:
        self._response = response

    def iter_bytes(self, chunk_size: int = 1024):
        try:
            while True:
                chunk = self._response.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            self.close()

    def close(self) -> None:
        try:
            self._response.close()
        except Exception:
            return


def forward_assessment_request(
    method: str,
    path: str,
    payload: dict | None,
    acting_user_id: str,
) -> dict:
    settings = get_settings()
    return _forward_json_request_to_base_url(
        base_url=settings["assessment_service_url"],
        method=method,
        path=path,
        payload=payload,
        extra_headers={"X-MCS-User-Id": acting_user_id},
        service_name="assessment service",
    )


def open_assessment_event_stream(
    path: str,
    *,
    acting_user_id: str,
    timeout: int = 120,
) -> UpstreamEventStream | dict:
    settings = get_settings()
    target_url = f"{settings['assessment_service_url']}{path}"
    headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-MCS-User-Id": acting_user_id,
    }
    req = request.Request(target_url, headers=headers, method="GET")
    try:
        response = request.urlopen(req, timeout=timeout)
        return UpstreamEventStream(response)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else "{}"
        try:
            payload_obj = json.loads(body)
        except json.JSONDecodeError:
            payload_obj = {"message": body or "assessment service http error"}
        if "detail" in payload_obj and isinstance(payload_obj["detail"], dict):
            payload_obj = payload_obj["detail"]
        return {"status": exc.code, "payload": payload_obj}
    except error.URLError as exc:
        return {
            "status": 503,
            "payload": {
                "code": 5032,
                "message": f"assessment service unavailable: {exc.reason}",
                "data": {},
            },
        }
