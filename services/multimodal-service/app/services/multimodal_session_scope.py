from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import MultimodalSession

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def normalize_identifier(value: str | None) -> str | None:
    return str(value or "").strip() or None


def normalize_scope_pair(
    scope_type: str | None,
    scope_id: str | None,
) -> tuple[str | None, str | None]:
    return normalize_identifier(scope_type), normalize_identifier(scope_id)


def is_encounter_scope(scope_type: str | None) -> bool:
    return str(normalize_identifier(scope_type) or "").lower() == "encounter"


def resolve_session_scope(
    *,
    encounter_session_id: str | None,
    scope_type: str | None,
    scope_id: str | None,
    flow_type: str | None,
    flow_run_id: str | None,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    normalized_encounter_session_id = normalize_identifier(encounter_session_id)
    normalized_scope_type, normalized_scope_id = normalize_scope_pair(
        scope_type,
        scope_id,
    )
    normalized_flow_type = normalize_identifier(flow_type)
    normalized_flow_run_id = normalize_identifier(flow_run_id)

    if is_encounter_scope(normalized_scope_type):
        canonical_encounter_session_id = (
            normalized_encounter_session_id or normalized_scope_id
        )
        return (
            canonical_encounter_session_id,
            "encounter",
            canonical_encounter_session_id,
            normalized_flow_type,
            normalized_flow_run_id,
        )

    if not normalized_scope_type and not normalized_scope_id:
        if normalized_encounter_session_id:
            return (
                normalized_encounter_session_id,
                "encounter",
                normalized_encounter_session_id,
                normalized_flow_type,
                normalized_flow_run_id,
            )
        if normalized_flow_run_id:
            return (
                normalized_encounter_session_id,
                "flow",
                normalized_flow_run_id,
                normalized_flow_type,
                normalized_flow_run_id,
            )

    return (
        normalized_encounter_session_id,
        normalized_scope_type,
        normalized_scope_id,
        normalized_flow_type,
        normalized_flow_run_id,
    )


def session_allows_flow_run(
    session_record: MultimodalSession,
    flow_run_id: str,
) -> bool:
    if is_encounter_scope(getattr(session_record, "scope_type", None)):
        return True
    session_flow_run_id = normalize_identifier(
        getattr(session_record, "flow_run_id", None)
    )
    if not session_flow_run_id:
        return True
    return session_flow_run_id == normalize_identifier(flow_run_id)


def find_multimodal_session(
    db_session: Session,
    *,
    scope_type: str | None,
    scope_id: str | None,
    flow_type: str | None,
    flow_run_id: str | None,
) -> MultimodalSession | None:
    if scope_type and scope_id:
        return db_session.execute(
            select(MultimodalSession).where(
                MultimodalSession.scope_type == scope_type,
                MultimodalSession.scope_id == scope_id,
            )
        ).scalar_one_or_none()
    return db_session.execute(
        select(MultimodalSession).where(
            MultimodalSession.flow_type == flow_type,
            MultimodalSession.flow_run_id == flow_run_id,
        )
    ).scalar_one_or_none()
