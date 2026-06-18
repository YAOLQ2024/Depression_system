from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.intervention_event import InterventionEvent
from app.models.intervention_session import InterventionSession
from app.schemas.intervention import (
    CreateInterventionSessionRequest,
    RecordInterventionEventRequest,
)

DEFAULT_SOURCE = "standalone"
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
EVENT_TYPES_MARK_COMPLETED = {"module_completed", "module_exited"}


@dataclass(slots=True)
class InterventionServiceError(Exception):
    message: str
    status_code: int
    code: int


@dataclass(slots=True)
class ResolvedInterventionScope:
    encounter_session_id: str | None
    consultation_session_id: str | None
    assessment_session_id: str | None
    risk_evaluation_id: str | None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_session(session: InterventionSession) -> dict[str, Any]:
    return {
        "session_id": session.id,
        "user_id": session.user_id,
        "encounter_session_id": session.encounter_session_id,
        "consultation_session_id": session.consultation_session_id,
        "assessment_session_id": session.assessment_session_id,
        "plan_id": session.plan_id,
        "risk_evaluation_id": session.risk_evaluation_id,
        "source": session.source,
        "status": session.status,
        "current_program_id": session.current_program_id,
        "current_program_title": session.current_program_title,
        "current_delivery_mode": session.current_delivery_mode,
        "metadata": session.metadata_payload or {},
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "started_at": session.started_at.isoformat(),
        "last_event_at": session.last_event_at.isoformat() if session.last_event_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


def _serialize_event(event: InterventionEvent) -> dict[str, Any]:
    return {
        "event_id": event.id,
        "session_id": event.session_id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "program_id": event.program_id,
        "program_title": event.program_title,
        "delivery_mode": event.delivery_mode,
        "payload": event.payload or {},
        "created_at": event.created_at.isoformat(),
    }


def _normalize_identifier(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _require_acting_user_id(acting_user_id: str | None) -> str:
    normalized = _normalize_identifier(acting_user_id)
    if normalized:
        return normalized
    raise InterventionServiceError(
        message="missing acting user id",
        status_code=401,
        code=4011,
    )


def _require_owner(session: InterventionSession, acting_user_id: str) -> None:
    if session.user_id != acting_user_id:
        raise InterventionServiceError(
            message="intervention session not found",
            status_code=404,
            code=4041,
        )


def _get_owned_encounter_scope(
    db: Session,
    encounter_session_id: str,
    *,
    acting_user_id: str,
) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            select id
            from encounter_sessions
            where id = :encounter_session_id and user_id = :user_id
            """
        ),
        {
            "encounter_session_id": encounter_session_id,
            "user_id": acting_user_id,
        },
    ).mappings().first()
    if row:
        return dict(row)
    raise InterventionServiceError(
        message="encounter session not found",
        status_code=404,
        code=4042,
    )


def _get_owned_consultation_scope(
    db: Session,
    consultation_session_id: str,
    *,
    acting_user_id: str,
) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            select id, encounter_session_id
            from consultation_sessions
            where id = :consultation_session_id and user_id = :user_id
            """
        ),
        {
            "consultation_session_id": consultation_session_id,
            "user_id": acting_user_id,
        },
    ).mappings().first()
    if row:
        return dict(row)
    raise InterventionServiceError(
        message="consultation session not found",
        status_code=404,
        code=4043,
    )


def _get_owned_assessment_scope(
    db: Session,
    assessment_session_id: str,
    *,
    acting_user_id: str,
) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            select id, encounter_session_id, source_consultation_flow_run_id
            from assessment_sessions
            where id = :assessment_session_id and user_id = :user_id
            """
        ),
        {
            "assessment_session_id": assessment_session_id,
            "user_id": acting_user_id,
        },
    ).mappings().first()
    if row:
        return dict(row)
    raise InterventionServiceError(
        message="assessment session not found",
        status_code=404,
        code=4044,
    )


def _get_owned_risk_scope(
    db: Session,
    risk_evaluation_id: str,
    *,
    acting_user_id: str,
) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            select id, encounter_session_id, consultation_session_id, assessment_session_id
            from risk_evaluations
            where id = :risk_evaluation_id and user_id = :user_id
            """
        ),
        {
            "risk_evaluation_id": risk_evaluation_id,
            "user_id": acting_user_id,
        },
    ).mappings().first()
    if row:
        return dict(row)
    raise InterventionServiceError(
        message="risk evaluation not found",
        status_code=404,
        code=4045,
    )


def _merge_related_scope_id(
    current_id: str | None,
    related_id: str | None,
    *,
    owner_label: str,
    target_label: str,
    code: int,
) -> str | None:
    normalized_related_id = _normalize_identifier(related_id)
    if not normalized_related_id:
        return current_id
    if current_id and current_id != normalized_related_id:
        raise InterventionServiceError(
            message=f"{owner_label} does not belong to the requested {target_label}",
            status_code=409,
            code=code,
        )
    return current_id or normalized_related_id


def _resolve_intervention_scope(
    db: Session,
    payload: CreateInterventionSessionRequest,
    *,
    acting_user_id: str,
) -> ResolvedInterventionScope:
    encounter_session_id = _normalize_identifier(payload.encounter_session_id)
    consultation_session_id = _normalize_identifier(payload.consultation_session_id)
    assessment_session_id = _normalize_identifier(payload.assessment_session_id)
    risk_evaluation_id = _normalize_identifier(payload.risk_evaluation_id)

    encounter_validated = False
    consultation_scope: dict[str, Any] | None = None
    assessment_scope: dict[str, Any] | None = None

    if encounter_session_id:
        _get_owned_encounter_scope(
            db,
            encounter_session_id,
            acting_user_id=acting_user_id,
        )
        encounter_validated = True

    if consultation_session_id:
        consultation_scope = _get_owned_consultation_scope(
            db,
            consultation_session_id,
            acting_user_id=acting_user_id,
        )
        encounter_session_id = _merge_related_scope_id(
            encounter_session_id,
            consultation_scope.get("encounter_session_id"),
            owner_label="consultation session",
            target_label="encounter session",
            code=4091,
        )

    if assessment_session_id:
        assessment_scope = _get_owned_assessment_scope(
            db,
            assessment_session_id,
            acting_user_id=acting_user_id,
        )
        encounter_session_id = _merge_related_scope_id(
            encounter_session_id,
            assessment_scope.get("encounter_session_id"),
            owner_label="assessment session",
            target_label="encounter session",
            code=4092,
        )
        consultation_session_id = _merge_related_scope_id(
            consultation_session_id,
            assessment_scope.get("source_consultation_flow_run_id"),
            owner_label="assessment session",
            target_label="consultation session",
            code=4093,
        )

    if risk_evaluation_id:
        risk_scope = _get_owned_risk_scope(
            db,
            risk_evaluation_id,
            acting_user_id=acting_user_id,
        )
        encounter_session_id = _merge_related_scope_id(
            encounter_session_id,
            risk_scope.get("encounter_session_id"),
            owner_label="risk evaluation",
            target_label="encounter session",
            code=4094,
        )
        consultation_session_id = _merge_related_scope_id(
            consultation_session_id,
            risk_scope.get("consultation_session_id"),
            owner_label="risk evaluation",
            target_label="consultation session",
            code=4095,
        )
        assessment_session_id = _merge_related_scope_id(
            assessment_session_id,
            risk_scope.get("assessment_session_id"),
            owner_label="risk evaluation",
            target_label="assessment session",
            code=4096,
        )

    if assessment_session_id and assessment_scope is None:
        assessment_scope = _get_owned_assessment_scope(
            db,
            assessment_session_id,
            acting_user_id=acting_user_id,
        )
        encounter_session_id = _merge_related_scope_id(
            encounter_session_id,
            assessment_scope.get("encounter_session_id"),
            owner_label="assessment session",
            target_label="encounter session",
            code=4092,
        )
        consultation_session_id = _merge_related_scope_id(
            consultation_session_id,
            assessment_scope.get("source_consultation_flow_run_id"),
            owner_label="assessment session",
            target_label="consultation session",
            code=4093,
        )

    if consultation_session_id and consultation_scope is None:
        consultation_scope = _get_owned_consultation_scope(
            db,
            consultation_session_id,
            acting_user_id=acting_user_id,
        )
        encounter_session_id = _merge_related_scope_id(
            encounter_session_id,
            consultation_scope.get("encounter_session_id"),
            owner_label="consultation session",
            target_label="encounter session",
            code=4091,
        )

    if encounter_session_id and not encounter_validated:
        _get_owned_encounter_scope(
            db,
            encounter_session_id,
            acting_user_id=acting_user_id,
        )

    return ResolvedInterventionScope(
        encounter_session_id=encounter_session_id,
        consultation_session_id=consultation_session_id,
        assessment_session_id=assessment_session_id,
        risk_evaluation_id=risk_evaluation_id,
    )


def create_intervention_session(
    payload: CreateInterventionSessionRequest,
    *,
    acting_user_id: str | None,
) -> dict[str, Any]:
    normalized_acting_user_id = _require_acting_user_id(acting_user_id)
    normalized_payload_user_id = _normalize_identifier(payload.user_id)
    if normalized_payload_user_id != normalized_acting_user_id:
        raise InterventionServiceError(
            message="acting user does not match payload user",
            status_code=403,
            code=4031,
        )

    now = _utcnow()
    source = (payload.source or DEFAULT_SOURCE).strip() or DEFAULT_SOURCE
    metadata = dict(payload.metadata or {})

    with get_db_session() as db:
        resolved_scope = _resolve_intervention_scope(
            db,
            payload,
            acting_user_id=normalized_acting_user_id,
        )
        intervention_session = InterventionSession(
            user_id=normalized_acting_user_id,
            encounter_session_id=resolved_scope.encounter_session_id,
            consultation_session_id=resolved_scope.consultation_session_id,
            assessment_session_id=resolved_scope.assessment_session_id,
            plan_id=payload.plan_id,
            risk_evaluation_id=resolved_scope.risk_evaluation_id,
            source=source,
            status=STATUS_ACTIVE,
            metadata_payload=metadata,
            created_at=now,
            updated_at=now,
            started_at=now,
        )
        db.add(intervention_session)
        db.flush()
        db.refresh(intervention_session)
        return _serialize_session(intervention_session)


def get_intervention_session(
    session_id: str,
    *,
    acting_user_id: str | None,
) -> dict[str, Any]:
    normalized_acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db:
        intervention_session = db.get(InterventionSession, session_id)
        if intervention_session is None:
            raise InterventionServiceError(
                message="intervention session not found",
                status_code=404,
                code=4040,
            )
        _require_owner(intervention_session, normalized_acting_user_id)
        return _serialize_session(intervention_session)


def record_intervention_event(
    session_id: str,
    payload: RecordInterventionEventRequest,
    *,
    acting_user_id: str | None,
) -> dict[str, Any]:
    normalized_acting_user_id = _require_acting_user_id(acting_user_id)
    now = _utcnow()

    with get_db_session() as db:
        intervention_session = db.get(InterventionSession, session_id)
        if intervention_session is None:
            raise InterventionServiceError(
                message="intervention session not found",
                status_code=404,
                code=4040,
            )
        _require_owner(intervention_session, normalized_acting_user_id)

        event = InterventionEvent(
            session_id=intervention_session.id,
            user_id=intervention_session.user_id,
            event_type=payload.event_type,
            program_id=payload.program_id,
            program_title=payload.program_title,
            delivery_mode=payload.delivery_mode,
            payload=dict(payload.payload or {}),
            created_at=now,
        )
        db.add(event)

        intervention_session.last_event_at = now
        intervention_session.updated_at = now
        if payload.program_id:
            intervention_session.current_program_id = payload.program_id
        if payload.program_title:
            intervention_session.current_program_title = payload.program_title
        if payload.delivery_mode:
            intervention_session.current_delivery_mode = payload.delivery_mode
        if payload.event_type in EVENT_TYPES_MARK_COMPLETED:
            intervention_session.status = STATUS_COMPLETED
            intervention_session.completed_at = intervention_session.completed_at or now
        elif intervention_session.status != STATUS_COMPLETED:
            intervention_session.status = STATUS_ACTIVE
            intervention_session.completed_at = None

        db.flush()
        db.refresh(intervention_session)
        db.refresh(event)
        return {
            "event": _serialize_event(event),
            "session": _serialize_session(intervention_session),
        }


def list_intervention_session_events(
    session_id: str,
    *,
    acting_user_id: str | None,
) -> list[dict[str, Any]]:
    normalized_acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db:
        intervention_session = db.get(InterventionSession, session_id)
        if intervention_session is None:
            raise InterventionServiceError(
                message="intervention session not found",
                status_code=404,
                code=4040,
            )
        _require_owner(intervention_session, normalized_acting_user_id)

        rows = db.scalars(
            select(InterventionEvent)
            .where(InterventionEvent.session_id == session_id)
            .order_by(InterventionEvent.created_at.asc())
        ).all()
        return [_serialize_event(row) for row in rows]
