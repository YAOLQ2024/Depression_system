from __future__ import annotations

import json
from urllib import error, request

from fastapi.encoders import jsonable_encoder


def forward_json_request(
    *,
    base_url: str,
    method: str,
    path: str,
    payload: dict | None,
    acting_user_id: str,
    service_name: str,
    timeout: int = 60,
) -> dict:
    target_url = f"{base_url}{path}"
    headers = {
        "Accept": "application/json",
        "X-MCS-User-Id": acting_user_id,
    }
    data = None
    if payload is not None:
        data = json.dumps(
            jsonable_encoder(payload),
            ensure_ascii=False,
        ).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    req = request.Request(target_url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return {"status": response.status, "payload": json.loads(body)}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else "{}"
        try:
            payload_obj = json.loads(body)
        except json.JSONDecodeError:
            payload_obj = {"message": body or f"{service_name} http error"}
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
    except TimeoutError:
        return {
            "status": 504,
            "payload": {
                "code": 5040,
                "message": f"{service_name} timed out after {timeout} seconds",
                "data": {},
            },
        }
