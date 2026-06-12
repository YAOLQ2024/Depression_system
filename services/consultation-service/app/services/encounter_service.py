# services/consultation-service/app/services/encounter_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.database import get_db_session
from app.models.consultation_session import ConsultationSession
from app.models.encounter_session import EncounterSession


class EncounterServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "encounter_error"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


def list_encounters(
    user_id: str,
    *,
    cursor: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """查询用户的就诊记录列表，返回游标分页结果。"""
    if limit < 1:
        limit = 1
    if limit > 50:
        limit = 50

    with get_db_session() as db_session:
        query = (
            select(EncounterSession)
            .where(EncounterSession.user_id == user_id)
            .order_by(EncounterSession.created_at.desc())
        )

        if cursor:
            cursor_row = db_session.execute(
                select(EncounterSession.created_at, EncounterSession.id)
                .where(EncounterSession.id == cursor)
            ).one_or_none()
            if cursor_row is None:
                raise EncounterServiceError(
                    f"cursor encounter not found: {cursor}",
                    status_code=400,
                    code="invalid_cursor",
                )
            cursor_created_at, cursor_id = cursor_row
            query = query.where(
                (EncounterSession.created_at < cursor_created_at)
                | ((EncounterSession.created_at == cursor_created_at) & (EncounterSession.id < cursor_id))
            )

        rows = db_session.execute(query.limit(limit + 1)).scalars().all()
        has_more = len(rows) > limit
        encounters = rows[:limit]

        if not encounters:
            return {"encounters": [], "next_cursor": None, "has_more": False}

        encounter_ids = [e.id for e in encounters]

        consultations = db_session.execute(
            select(ConsultationSession).where(
                ConsultationSession.encounter_session_id.in_(encounter_ids)
            )
        ).scalars().all()

        consultation_map: dict[str, ConsultationSession] = {}
        for c in consultations:
            eid = c.encounter_session_id
            if eid and (eid not in consultation_map or (c.created_at or datetime.min.replace(tzinfo=timezone.utc)) > (consultation_map[eid].created_at or datetime.min.replace(tzinfo=timezone.utc))):
                consultation_map[eid] = c

        result: list[dict[str, Any]] = []
        for encounter in encounters:
            consultation = consultation_map.get(encounter.id)
            result.append({
                "id": encounter.id,
                "status": encounter.status,
                "current_flow_type": encounter.current_flow_type,
                "created_at": encounter.created_at.isoformat() if encounter.created_at else None,
                "completed_at": encounter.completed_at.isoformat() if encounter.completed_at else None,
                "consultation_session_id": consultation.id if consultation else None,
                "assessment_session_id": None,
                "chief_complaint_summary": consultation.chief_complaint_summary if consultation else None,
                "phq9_score": None,
                "phq9_risk_level": None,
                "overall_risk_level": None,
            })

        next_cursor = encounters[-1].id if has_more else None
        return {"encounters": result, "next_cursor": next_cursor, "has_more": has_more}
