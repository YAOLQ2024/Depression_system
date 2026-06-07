from __future__ import annotations

from app.clients._http import forward_json_request
from app.config import get_settings


def create_risk_evaluation(*, payload: dict, acting_user_id: str) -> dict:
    settings = get_settings()
    return forward_json_request(
        base_url=settings["risk_service_url"],
        method="POST",
        path="/api/v1/risk/evaluations",
        payload=payload,
        acting_user_id=acting_user_id,
        service_name="risk service",
        timeout=120,
    )
