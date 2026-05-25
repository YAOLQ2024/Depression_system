from __future__ import annotations

from typing import Any

from app.clients.multimodal_client import (
    create_multimodal_session as create_upstream_multimodal_session,
    get_multimodal_live as fetch_upstream_multimodal_live,
)
from app.models import ConsultationSession
from app.services.consultation import ConsultationServiceError, _now


def _extract_upstream_data(
    upstream: dict, *, error_code: int
) -> dict[str, Any]:
    if upstream["status"] >= 400:
        payload = upstream.get("payload") or {}
        raise ConsultationServiceError(
            str(payload.get("message") or "multimodal service request failed"),
            code=int(payload.get("code") or error_code),
            status_code=int(upstream["status"]),
        )
    data = (upstream.get("payload") or {}).get("data") or {}
    if not isinstance(data, dict):
        raise ConsultationServiceError(
            "multimodal service returned invalid payload",
            code=error_code,
            status_code=502,
        )
    return data


def _extract_optional_upstream_data(
    upstream: dict,
    *,
    error_code: int,
    allowed_statuses: set[int],
) -> dict[str, Any] | None:
    if int(upstream["status"]) in allowed_statuses:
        return None
    return _extract_upstream_data(upstream, error_code=error_code)


def _ensure_multimodal_session_binding(
    session_record: ConsultationSession,
    *,
    acting_user_id: str,
) -> str:
    if session_record.multimodal_session_id:
        return session_record.multimodal_session_id

    multimodal_data = _extract_upstream_data(
        create_upstream_multimodal_session(
            user_id=acting_user_id,
            encounter_session_id=session_record.encounter_session_id,
            flow_type="consultation",
            flow_run_id=session_record.id,
        ),
        error_code=5021,
    )
    multimodal_session = multimodal_data.get("multimodal_session") or {}
    multimodal_session_id = (
        multimodal_session.get("id") or multimodal_session.get("session_id")
    )
    if not multimodal_session_id:
        raise ConsultationServiceError(
            "multimodal session id missing",
            code=5022,
            status_code=502,
        )

    session_record.multimodal_session_id = str(multimodal_session_id)
    session_record.updated_at = _now()
    return str(multimodal_session_id)


def _refresh_multimodal_live_snapshot(
    session_record: ConsultationSession,
    *,
    acting_user_id: str,
) -> dict[str, Any]:
    multimodal_session_id = _ensure_multimodal_session_binding(
        session_record,
        acting_user_id=acting_user_id,
    )
    live_data = _extract_upstream_data(
        fetch_upstream_multimodal_live(
            multimodal_session_id=multimodal_session_id,
            acting_user_id=acting_user_id,
        ),
        error_code=5024,
    )
    session_record.multimodal_live_payload = live_data
    session_record.multimodal_live_updated_at = _now()
    return live_data
