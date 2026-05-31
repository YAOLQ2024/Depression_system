from __future__ import annotations

import json
from urllib import error, request

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


def _open_multimodal_stream_request(
    method: str,
    path: str,
    *,
    acting_user_id: str,
    timeout: int = 120,
) -> UpstreamEventStream | dict:
    settings = get_settings()
    target_url = f"{settings['multimodal_service_url']}{path}"
    headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-MCS-User-Id": acting_user_id,
    }
    req = request.Request(target_url, headers=headers, method=method)
    try:
        response = request.urlopen(req, timeout=timeout)
        return UpstreamEventStream(response)
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


def create_multimodal_session(
    *,
    user_id: str,
    encounter_session_id: str | None = None,
    flow_type: str,
    flow_run_id: str,
    scope_type: str | None = None,
    scope_id: str | None = None,
    stage_context: dict | None = None,
) -> dict:
    return _forward_multimodal_request(
        "POST",
        "/api/v1/multimodal/sessions",
        {
            "user_id": user_id,
            "encounter_session_id": encounter_session_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "flow_type": flow_type,
            "flow_run_id": flow_run_id,
            "enabled_modalities": ["text", "audio", "face", "pose"],
            **({"stage_context": stage_context} if stage_context else {}),
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


def stream_multimodal_live(
    *,
    multimodal_session_id: str,
    acting_user_id: str,
) -> UpstreamEventStream | dict:
    return _open_multimodal_stream_request(
        "GET",
        f"/api/v1/multimodal/sessions/{multimodal_session_id}/live/stream",
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


def finalize_multimodal_turn(
    *,
    multimodal_session_id: str,
    turn_id: str,
    acting_user_id: str,
) -> dict:
    return _forward_multimodal_request(
        "POST",
        f"/api/v1/multimodal/sessions/{multimodal_session_id}/turns/{turn_id}/finalize",
        {},
        acting_user_id=acting_user_id,
    )


def recover_multimodal_turn_hot_state(
    *,
    multimodal_session_id: str,
    turn_id: str,
    acting_user_id: str,
) -> dict:
    return _forward_multimodal_request(
        "POST",
        f"/api/v1/multimodal/sessions/{multimodal_session_id}/turns/{turn_id}/recover",
        {},
        acting_user_id=acting_user_id,
    )
