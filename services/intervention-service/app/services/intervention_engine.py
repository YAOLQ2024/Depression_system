from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

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


def _require_owner(session: InterventionSession, acting_user_id: str | None) -> None:
    if acting_user_id and session.user_id != acting_user_id:
        raise InterventionServiceError(
            message="intervention session not found",
            status_code=404,
            code=4041,
        )


def create_intervention_session(
    payload: CreateInterventionSessionRequest,
    *,
    acting_user_id: str | None,
) -> dict[str, Any]:
    if acting_user_id and acting_user_id != payload.user_id:
        raise InterventionServiceError(
            message="acting user does not match payload user",
            status_code=403,
            code=4031,
        )

    now = _utcnow()
    source = (payload.source or DEFAULT_SOURCE).strip() or DEFAULT_SOURCE
    metadata = dict(payload.metadata or {})

    intervention_session = InterventionSession(
        user_id=payload.user_id,
        encounter_session_id=payload.encounter_session_id,
        consultation_session_id=payload.consultation_session_id,
        assessment_session_id=payload.assessment_session_id,
        plan_id=payload.plan_id,
        risk_evaluation_id=payload.risk_evaluation_id,
        source=source,
        status=STATUS_ACTIVE,
        metadata_payload=metadata,
        created_at=now,
        updated_at=now,
        started_at=now,
    )

    with get_db_session() as db:
        db.add(intervention_session)
        db.flush()
        db.refresh(intervention_session)
        return _serialize_session(intervention_session)


def get_intervention_session(
    session_id: str,
    *,
    acting_user_id: str | None,
) -> dict[str, Any]:
    with get_db_session() as db:
        intervention_session = db.get(InterventionSession, session_id)
        if intervention_session is None:
            raise InterventionServiceError(
                message="intervention session not found",
                status_code=404,
                code=4040,
            )
        _require_owner(intervention_session, acting_user_id)
        return _serialize_session(intervention_session)


def record_intervention_event(
    session_id: str,
    payload: RecordInterventionEventRequest,
    *,
    acting_user_id: str | None,
) -> dict[str, Any]:
    now = _utcnow()

    with get_db_session() as db:
        intervention_session = db.get(InterventionSession, session_id)
        if intervention_session is None:
            raise InterventionServiceError(
                message="intervention session not found",
                status_code=404,
                code=4040,
            )
        _require_owner(intervention_session, acting_user_id)

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
            intervention_session.completed_at = now
        else:
            intervention_session.status = STATUS_ACTIVE

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
    with get_db_session() as db:
        intervention_session = db.get(InterventionSession, session_id)
        if intervention_session is None:
            raise InterventionServiceError(
                message="intervention session not found",
                status_code=404,
                code=4040,
            )
        _require_owner(intervention_session, acting_user_id)

        rows = db.scalars(
            select(InterventionEvent)
            .where(InterventionEvent.session_id == session_id)
            .order_by(InterventionEvent.created_at.asc())
        ).all()
        return [_serialize_event(row) for row in rows]
