from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.clients.multimodal_client import (
    create_multimodal_session as create_upstream_multimodal_session,
    finalize_multimodal_turn as finalize_upstream_multimodal_turn,
    get_multimodal_live as fetch_upstream_multimodal_live,
    get_multimodal_turn_bundle as fetch_upstream_multimodal_turn_bundle,
    recover_multimodal_turn_hot_state as recover_upstream_multimodal_turn_hot_state,
    stream_multimodal_live as stream_upstream_multimodal_live,
)
from app.models import AssessmentSession


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _service_error(message: str, code: int, status_code: int = 400):
    from app.services.assessment_engine import AssessmentServiceError

    return AssessmentServiceError(message, code=code, status_code=status_code)


def _extract_upstream_data(upstream: dict, *, error_code: int) -> dict[str, Any]:
    if upstream["status"] >= 400:
        payload = upstream.get("payload") or {}
        raise _service_error(
            str(payload.get("message") or "multimodal service request failed"),
            code=int(payload.get("code") or error_code),
            status_code=int(upstream["status"]),
        )
    data = (upstream.get("payload") or {}).get("data") or {}
    if not isinstance(data, dict):
        raise _service_error(
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


def _build_stage_context(session_record: AssessmentSession) -> dict[str, Any] | None:
    scale_slug = str(session_record.current_scale_slug or "").strip()
    if not scale_slug:
        return None
    return {
        "stage_id": scale_slug,
        "stage_label": scale_slug.upper() if scale_slug != "social-function" else "SOCIAL-FUNCTION",
        "stage_order": max(1, int(session_record.current_item_index) + 1),
    }


def ensure_multimodal_session_binding(
    session_record: AssessmentSession,
    *,
    acting_user_id: str,
) -> str:
    if session_record.multimodal_session_id:
        return session_record.multimodal_session_id
    encounter_session_id = str(session_record.encounter_session_id or "").strip()
    if not encounter_session_id:
        raise _service_error(
            "assessment encounter_session_id is required before binding multimodal session",
            code=4095,
            status_code=409,
        )

    multimodal_data = _extract_upstream_data(
        create_upstream_multimodal_session(
            user_id=acting_user_id,
            encounter_session_id=encounter_session_id,
            scope_type="encounter",
            scope_id=encounter_session_id,
            flow_type="assessment",
            flow_run_id=session_record.id,
            stage_context=_build_stage_context(session_record),
        ),
        error_code=5021,
    )
    multimodal_session = multimodal_data.get("multimodal_session") or {}
    multimodal_session_id = multimodal_session.get("id") or multimodal_session.get("session_id")
    if not multimodal_session_id:
        raise _service_error(
            "multimodal session id missing",
            code=5022,
            status_code=502,
        )

    session_record.multimodal_session_id = str(multimodal_session_id)
    session_record.updated_at = _now()
    return str(multimodal_session_id)


def refresh_multimodal_live_snapshot(
    session_record: AssessmentSession,
    *,
    acting_user_id: str,
) -> dict[str, Any]:
    multimodal_session_id = ensure_multimodal_session_binding(
        session_record,
        acting_user_id=acting_user_id,
    )
    return _extract_upstream_data(
        fetch_upstream_multimodal_live(
            multimodal_session_id=multimodal_session_id,
            acting_user_id=acting_user_id,
        ),
        error_code=5024,
    )


def stream_assessment_multimodal_live(
    session_record: AssessmentSession,
    *,
    acting_user_id: str,
):
    multimodal_session_id = ensure_multimodal_session_binding(
        session_record,
        acting_user_id=acting_user_id,
    )
    upstream = stream_upstream_multimodal_live(
        multimodal_session_id=multimodal_session_id,
        acting_user_id=acting_user_id,
    )
    if isinstance(upstream, dict):
        payload = upstream.get("payload") or {}
        raise _service_error(
            str(payload.get("message") or "multimodal live stream unavailable"),
            code=int(payload.get("code") or 5024),
            status_code=int(upstream.get("status") or 502),
        )
    return upstream


def get_assessment_turn_multimodal_bundle(
    session_record: AssessmentSession,
    *,
    turn_id: str,
    acting_user_id: str,
) -> dict[str, Any]:
    multimodal_session_id = ensure_multimodal_session_binding(
        session_record,
        acting_user_id=acting_user_id,
    )
    return _extract_upstream_data(
        fetch_upstream_multimodal_turn_bundle(
            multimodal_session_id=multimodal_session_id,
            turn_id=turn_id,
            acting_user_id=acting_user_id,
        ),
        error_code=5026,
    )


def finalize_assessment_turn_bundle(
    session_record: AssessmentSession,
    *,
    turn_id: str | None,
    acting_user_id: str,
) -> dict[str, Any] | None:
    if not turn_id:
        return None
    multimodal_session_id = ensure_multimodal_session_binding(
        session_record,
        acting_user_id=acting_user_id,
    )
    finalize_data = _extract_optional_upstream_data(
        finalize_upstream_multimodal_turn(
            multimodal_session_id=multimodal_session_id,
            turn_id=turn_id,
            acting_user_id=acting_user_id,
        ),
        error_code=5025,
        allowed_statuses={404},
    )
    if not isinstance(finalize_data, dict):
        return None
    turn_bundle = finalize_data.get("turn_bundle")
    return turn_bundle if isinstance(turn_bundle, dict) else None


def recover_assessment_turn_hot_state(
    session_record: AssessmentSession,
    *,
    turn_id: str,
    acting_user_id: str,
) -> dict[str, Any]:
    multimodal_session_id = ensure_multimodal_session_binding(
        session_record,
        acting_user_id=acting_user_id,
    )
    return _extract_upstream_data(
        recover_upstream_multimodal_turn_hot_state(
            multimodal_session_id=multimodal_session_id,
            turn_id=turn_id,
            acting_user_id=acting_user_id,
        ),
        error_code=5027,
    )
