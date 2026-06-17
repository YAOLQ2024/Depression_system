from __future__ import annotations

from app.clients.identity_client import _forward_json_request_to_base_url
from app.config import get_settings


def forward_intervention_request(
    method: str,
    path: str,
    payload: dict | None,
    *,
    acting_user_id: str,
) -> dict:
    settings = get_settings()
    return _forward_json_request_to_base_url(
        base_url=settings["intervention_service_url"],
        method=method,
        path=path,
        payload=payload,
        extra_headers={"X-MCS-User-Id": acting_user_id},
        service_name="intervention service",
    )
