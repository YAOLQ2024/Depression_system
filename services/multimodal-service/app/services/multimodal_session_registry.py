from __future__ import annotations

from datetime import datetime
import uuid
from typing import Callable

from sqlalchemy.exc import IntegrityError

from app.models import MultimodalSession
from app.schemas.multimodal import CreateMultimodalSessionRequest
from app.services.multimodal_session_scope import (
    find_multimodal_session,
    resolve_session_scope,
)


def apply_session_updates(
    record: MultimodalSession,
    *,
    effective_user_id: str | None,
    encounter_session_id: str | None,
    scope_type: str | None,
    scope_id: str | None,
    flow_type: str | None,
    flow_run_id: str | None,
    stage_context: dict,
    enabled_modalities: list[str],
    notes: str | None,
    lookup_by_scope: bool,
    now: datetime,
    status_on_update: str | None,
) -> None:
    record.user_id = effective_user_id or record.user_id
    record.encounter_session_id = (
        encounter_session_id or record.encounter_session_id
    )
    record.scope_type = scope_type or record.scope_type
    record.scope_id = scope_id or record.scope_id
    resolved_scope_type = str(record.scope_type or "").strip().lower()
    if resolved_scope_type == "encounter" and str(record.scope_id or "").strip():
        record.encounter_session_id = str(record.scope_id).strip()
    if not lookup_by_scope or not resolved_scope_type:
        record.flow_type = flow_type or record.flow_type
        record.flow_run_id = flow_run_id or record.flow_run_id
    record.stage_context = stage_context or record.stage_context or {}
    record.enabled_modalities = enabled_modalities
    record.live_state_payload = record.live_state_payload or {}
    record.notes = notes if notes is not None else record.notes
    if status_on_update is not None:
        record.status = status_on_update
    record.started_at = record.started_at or record.created_at or now
    record.created_at = record.created_at or record.started_at or now
    record.updated_at = now


def create_or_reuse_session_record(
    db_session,
    *,
    payload: CreateMultimodalSessionRequest,
    effective_user_id: str | None,
    stage_context: dict,
    enabled_modalities: list[str],
    now_factory: Callable[[], datetime],
    create_status: str,
    status_on_update: str | None,
    fallback_flow_run_id_factory: Callable[[str], str],
    acting_user_id: str | None = None,
    access_validator: Callable[[MultimodalSession, str | None], None] | None = None,
) -> MultimodalSession:
    (
        resolved_encounter_session_id,
        scope_type,
        scope_id,
        flow_type,
        flow_run_id,
    ) = resolve_session_scope(
        encounter_session_id=payload.encounter_session_id,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        flow_type=payload.flow_type,
        flow_run_id=payload.flow_run_id,
    )
    payload.encounter_session_id = resolved_encounter_session_id
    lookup_by_scope = bool(scope_type and scope_id)

    def _validate_access(record: MultimodalSession) -> None:
        if access_validator is not None:
            access_validator(record, acting_user_id)

    existing = find_multimodal_session(
        db_session,
        scope_type=scope_type,
        scope_id=scope_id,
        flow_type=flow_type,
        flow_run_id=flow_run_id,
    )
    if existing is not None:
        _validate_access(existing)
        now = now_factory()
        apply_session_updates(
            existing,
            effective_user_id=effective_user_id,
            encounter_session_id=resolved_encounter_session_id,
            scope_type=scope_type,
            scope_id=scope_id,
            flow_type=flow_type,
            flow_run_id=flow_run_id,
            stage_context=stage_context,
            enabled_modalities=enabled_modalities,
            notes=payload.notes,
            lookup_by_scope=lookup_by_scope,
            now=now,
            status_on_update=status_on_update,
        )
        db_session.add(existing)
        db_session.flush()
        db_session.refresh(existing)
        return existing

    session_id = str(uuid.uuid4())
    now = now_factory()
    record = MultimodalSession(
        id=session_id,
        encounter_session_id=resolved_encounter_session_id,
        scope_type=scope_type or "flow",
        scope_id=scope_id or flow_run_id or session_id,
        flow_type=flow_type or "consultation",
        flow_run_id=flow_run_id or fallback_flow_run_id_factory(session_id),
        user_id=effective_user_id,
        stage_context=stage_context,
        status=create_status,
        enabled_modalities=enabled_modalities,
        live_state_payload={},
        notes=payload.notes,
        started_at=now,
        created_at=now,
        updated_at=now,
    )
    try:
        db_session.add(record)
        db_session.flush()
        db_session.refresh(record)
        return record
    except IntegrityError:
        db_session.rollback()
        existing = find_multimodal_session(
            db_session,
            scope_type=scope_type,
            scope_id=scope_id,
            flow_type=flow_type,
            flow_run_id=flow_run_id,
        )
        if existing is None:
            raise
        _validate_access(existing)
        now = now_factory()
        apply_session_updates(
            existing,
            effective_user_id=effective_user_id,
            encounter_session_id=resolved_encounter_session_id,
            scope_type=scope_type,
            scope_id=scope_id,
            flow_type=flow_type,
            flow_run_id=flow_run_id,
            stage_context=stage_context,
            enabled_modalities=enabled_modalities,
            notes=payload.notes,
            lookup_by_scope=lookup_by_scope,
            now=now,
            status_on_update=status_on_update,
        )
        db_session.add(existing)
        db_session.flush()
        db_session.refresh(existing)
        return existing
