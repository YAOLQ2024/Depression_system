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


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def get_encounter_detail(
    user_id: str,
    encounter_id: str,
) -> dict[str, Any]:
    """查询单次就诊的完整详情，包含问诊、评估和时间线。"""
    with get_db_session() as db_session:
        encounter = db_session.execute(
            select(EncounterSession).where(
                EncounterSession.id == encounter_id,
                EncounterSession.user_id == user_id,
            )
        ).scalar_one_or_none()

        if encounter is None:
            raise EncounterServiceError(
                f"encounter not found: {encounter_id}",
                status_code=404,
                code="encounter_not_found",
            )

        # 查询关联的 consultation
        consultation = db_session.execute(
            select(ConsultationSession)
            .where(ConsultationSession.encounter_session_id == encounter_id)
            .order_by(ConsultationSession.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        # 查询关联的 assessment（当前所有 service 共享同一个 PostgreSQL）
        from app.models.assessment_session import AssessmentSession
        from app.models.assessment_result import AssessmentResult

        assessment = db_session.execute(
            select(AssessmentSession)
            .where(AssessmentSession.encounter_session_id == encounter_id)
            .order_by(AssessmentSession.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        assessment_results: list[dict[str, Any]] = []
        assessment_payload: dict[str, Any] | None = None
        if assessment is not None:
            assessment_payload = {
                "id": assessment.id,
                "status": assessment.status,
                "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
                "completed_at": assessment.completed_at.isoformat() if assessment.completed_at else None,
                "aggregate_payload": assessment.aggregate_payload,
            }
            results = db_session.execute(
                select(AssessmentResult)
                .where(AssessmentResult.session_id == assessment.id)
                .order_by(AssessmentResult.created_at.asc())
            ).scalars().all()
            for r in results:
                assessment_results.append({
                    "scale_slug": r.scale_slug,
                    "raw_score": r.raw_score,
                    "derived_score": r.derived_score,
                    "interpretation_level": r.interpretation_level,
                    "interpretation_label": r.interpretation_label,
                    "risk_flags": r.risk_flags,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                })

        # 组装问诊摘要
        consultation_payload: dict[str, Any] | None = None
        if consultation is not None:
            consultation_payload = {
                "id": consultation.id,
                "status": consultation.status,
                "chief_complaint_summary": consultation.chief_complaint_summary,
                "assigned_doctor_persona": consultation.assigned_doctor_persona,
                "created_at": consultation.created_at.isoformat() if consultation.created_at else None,
                "completed_at": consultation.completed_at.isoformat() if consultation.completed_at else None,
                "started_at": consultation.started_at.isoformat() if consultation.started_at else None,
            }

        # 组装时间线
        timeline: list[dict[str, Any]] = []
        timeline.append({"event": "encounter_created", "at": _isoformat(encounter.created_at)})
        if encounter.started_at:
            timeline.append({"event": "encounter_started", "at": _isoformat(encounter.started_at)})
        if consultation:
            if consultation.created_at:
                timeline.append({"event": "consultation_created", "at": _isoformat(consultation.created_at)})
            if consultation.started_at:
                timeline.append({"event": "consultation_started", "at": _isoformat(consultation.started_at)})
            if consultation.completed_at:
                timeline.append({"event": "consultation_completed", "at": _isoformat(consultation.completed_at)})
        if assessment:
            if assessment.created_at:
                timeline.append({"event": "assessment_created", "at": _isoformat(assessment.created_at)})
            if assessment.started_at:
                timeline.append({"event": "assessment_started", "at": _isoformat(assessment.started_at)})
            if assessment.completed_at:
                timeline.append({"event": "assessment_completed", "at": _isoformat(assessment.completed_at)})
        if encounter.completed_at:
            timeline.append({"event": "encounter_completed", "at": _isoformat(encounter.completed_at)})

        timeline.sort(key=lambda item: item["at"] or "")

        return {
            "encounter": {
                "id": encounter.id,
                "status": encounter.status,
                "current_flow_type": encounter.current_flow_type,
                "created_at": _isoformat(encounter.created_at),
                "completed_at": _isoformat(encounter.completed_at),
                "started_at": _isoformat(encounter.started_at),
                "consultation": consultation_payload,
                "assessment": assessment_payload,
                "assessment_results": assessment_results,
                "timeline": timeline,
            }
        }
