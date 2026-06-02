from __future__ import annotations

from app.clients._http import forward_json_request
from app.config import get_settings


def get_multimodal_live(*, multimodal_session_id: str, acting_user_id: str) -> dict:
    settings = get_settings()
    return forward_json_request(
        base_url=settings["multimodal_service_url"],
        method="GET",
        path=f"/api/v1/multimodal/sessions/{multimodal_session_id}/live",
        payload=None,
        acting_user_id=acting_user_id,
        service_name="multimodal service",
    )
