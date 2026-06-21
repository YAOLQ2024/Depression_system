# services/consultation-service/app/services/encounter_service.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import bindparam, select, text

from app.database import get_db_session
from app.models.consultation_session import ConsultationSession
from app.models.encounter_session import EncounterSession


class EncounterServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "encounter_error"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


def _safe_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.min.replace(tzinfo=timezone.utc)


def _ensure_json_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _ensure_json_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _ensure_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            normalized.append(text)
    return normalized


def _read_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coalesce_text(*values: Any) -> str | None:
    for value in values:
        text = _read_text(value)
        if text:
            return text
    return None


def _coalesce_numeric(*values: Any) -> float | int | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return value
    return None


def _load_latest_assessments_by_encounter(
    db_session: Any,
    encounter_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not encounter_ids:
        return {}

    rows = db_session.execute(
        text(
            """
            select
                id,
                encounter_session_id,
                status,
                aggregate_payload,
                scale_handoff_payload,
                required_scales,
                selected_scales,
                created_at,
                started_at,
                completed_at
            from assessment_sessions
            where encounter_session_id in :encounter_ids
            order by created_at desc, id desc
            """
        ).bindparams(bindparam("encounter_ids", expanding=True)),
        {"encounter_ids": encounter_ids},
    ).mappings().all()

    assessment_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        encounter_id = str(row.get("encounter_session_id") or "").strip()
        if encounter_id and encounter_id not in assessment_map:
            assessment_map[encounter_id] = dict(row)
    return assessment_map


def _extract_assessment_summary(assessment_row: dict[str, Any] | None) -> dict[str, Any]:
    if not assessment_row:
        return {
            "assessment_session_id": None,
            "phq9_score": None,
            "phq9_risk_level": None,
            "overall_risk_level": None,
        }

    aggregate_payload = _ensure_json_dict(assessment_row.get("aggregate_payload"))
    scale_result_map = _ensure_json_dict(aggregate_payload.get("scale_result_map"))
    phq9_result = _ensure_json_dict(scale_result_map.get("phq9"))
    risk_summary = _ensure_json_dict(aggregate_payload.get("risk_summary"))
    return {
        "assessment_session_id": assessment_row.get("id"),
        "phq9_score": phq9_result.get("raw_score"),
        "phq9_risk_level": phq9_result.get("interpretation_level"),
        "overall_risk_level": risk_summary.get("risk_level"),
    }


def _load_latest_assessment_for_encounter(
    db_session: Any,
    encounter_id: str,
) -> dict[str, Any] | None:
    row = db_session.execute(
        text(
            """
            select
                id,
                encounter_session_id,
                status,
                aggregate_payload,
                scale_handoff_payload,
                required_scales,
                selected_scales,
                source_consultation_flow_run_id,
                multimodal_session_id,
                created_at,
                started_at,
                completed_at
            from assessment_sessions
            where encounter_session_id = :encounter_id
            order by created_at desc, id desc
            limit 1
            """
        ),
        {"encounter_id": encounter_id},
    ).mappings().first()
    return dict(row) if row else None


def _load_assessment_results(
    db_session: Any,
    assessment_session_id: str,
) -> list[dict[str, Any]]:
    rows = db_session.execute(
        text(
            """
            select
                scale_slug,
                raw_score,
                derived_score,
                interpretation_level,
                interpretation_label,
                risk_flags,
                completed_at,
                created_at
            from assessment_results
            where session_id = :session_id
            order by created_at asc, scale_slug asc
            """
        ),
        {"session_id": assessment_session_id},
    ).mappings().all()
    return [dict(row) for row in rows]


def get_scale_score_history(
    user_id: str,
    scale_slug: str,
) -> dict[str, Any]:
    normalized_scale_slug = str(scale_slug or "").strip()
    if not normalized_scale_slug:
        raise EncounterServiceError(
            "scale slug is required",
            status_code=400,
            code="invalid_scale_slug",
        )

    with get_db_session() as db_session:
        rows = db_session.execute(
            text(
                """
                select
                    ar.scale_slug,
                    ar.raw_score,
                    ar.derived_score,
                    ar.completed_at as result_completed_at,
                    ar.created_at as result_created_at,
                    asess.id as assessment_session_id,
                    asess.status as assessment_status,
                    asess.encounter_session_id,
                    asess.created_at as assessment_created_at,
                    enc.status as encounter_status
                from assessment_results ar
                join assessment_sessions asess on asess.id = ar.session_id
                left join encounter_sessions enc on enc.id = asess.encounter_session_id
                where asess.user_id = :user_id
                  and ar.scale_slug = :scale_slug
                order by
                    coalesce(ar.completed_at, ar.created_at, asess.created_at) desc,
                    ar.created_at desc,
                    asess.created_at desc,
                    asess.id desc
                """
            ),
            {
                "user_id": user_id,
                "scale_slug": normalized_scale_slug,
            },
        ).mappings().all()

    latest_rows_by_visit: dict[str, dict[str, Any]] = {}
    for raw_row in rows:
        row = dict(raw_row)
        visit_key = _coalesce_text(
            row.get("encounter_session_id"),
            row.get("assessment_session_id"),
        )
        if not visit_key or visit_key in latest_rows_by_visit:
            continue
        latest_rows_by_visit[visit_key] = row

    ordered_rows = sorted(
        latest_rows_by_visit.values(),
        key=lambda item: _safe_datetime(
            item.get("result_completed_at")
            or item.get("result_created_at")
            or item.get("assessment_created_at")
        ),
    )

    history: list[dict[str, Any]] = []
    for row in ordered_rows:
        score = _coalesce_numeric(row.get("derived_score"), row.get("raw_score"))
        completed_at = _coalesce_text(
            _isoformat(row.get("result_completed_at")),
            _isoformat(row.get("result_created_at")),
            _isoformat(row.get("assessment_created_at")),
        )
        if score is None or not completed_at:
            continue

        history.append(
            {
                "encounter_id": row.get("encounter_session_id"),
                "encounter_status": row.get("encounter_status"),
                "assessment_session_id": row.get("assessment_session_id"),
                "assessment_status": row.get("assessment_status"),
                "completed_at": completed_at,
                "raw_score": row.get("raw_score"),
                "derived_score": row.get("derived_score"),
                "score": score,
            }
        )

    return {
        "scale_slug": normalized_scale_slug,
        "history": history,
    }


def _build_consultation_payload(
    consultation: ConsultationSession | None,
) -> dict[str, Any] | None:
    if consultation is None:
        return None

    slot_values = _ensure_json_dict(consultation.slot_values)
    scale_handoff_payload = _ensure_json_dict(consultation.scale_handoff_payload)

    return {
        "id": consultation.id,
        "status": consultation.status,
        "chief_complaint_raw_text": consultation.chief_complaint_raw_text,
        "chief_complaint_summary": consultation.chief_complaint_summary,
        "assigned_doctor_persona": consultation.assigned_doctor_persona,
        "slot_values": slot_values,
        "chief_complaint_structured_result": _ensure_json_dict(
            slot_values.get("chief_complaint_structured_result")
        ),
        "chief_complaint_stage_summary": _coalesce_text(
            slot_values.get("chief_complaint_stage_summary"),
            scale_handoff_payload.get("chief_complaint_stage_summary"),
            consultation.chief_complaint_summary,
        ),
        "current_history_structured_result": _ensure_json_dict(
            consultation.current_history_structured_result
        ),
        "symptom_screening_stage_summary": _coalesce_text(
            slot_values.get("symptom_screening_stage_summary"),
            scale_handoff_payload.get("symptom_screening_stage_summary"),
        ),
        "high_risk_screening_result": _ensure_json_dict(
            consultation.high_risk_screening_result
        ),
        "high_risk_screening_stage_summary": _coalesce_text(
            slot_values.get("high_risk_screening_stage_summary"),
            scale_handoff_payload.get("high_risk_screening_stage_summary"),
        ),
        "digital_human_consultation_summary": _coalesce_text(
            slot_values.get("digital_human_consultation_summary"),
            scale_handoff_payload.get("digital_human_consultation_summary"),
        ),
        "scale_handoff_payload": scale_handoff_payload,
        "required_scales": _ensure_string_list(
            scale_handoff_payload.get("required_scales")
        ),
        "subtitle_history": _ensure_json_list(consultation.subtitle_history_payload),
        "context_snapshot": _ensure_json_dict(consultation.context_snapshot),
        "created_at": consultation.created_at.isoformat()
        if consultation.created_at
        else None,
        "completed_at": consultation.completed_at.isoformat()
        if consultation.completed_at
        else None,
        "started_at": consultation.started_at.isoformat()
        if consultation.started_at
        else None,
    }


def _build_assessment_payload(
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if assessment is None:
        return None

    aggregate_payload = _ensure_json_dict(assessment.get("aggregate_payload"))
    scale_handoff_payload = _ensure_json_dict(
        assessment.get("scale_handoff_payload")
    )
    if not scale_handoff_payload:
        scale_handoff_payload = _ensure_json_dict(aggregate_payload.get("source_handoff"))

    return {
        "id": assessment.get("id"),
        "status": assessment.get("status"),
        "created_at": _isoformat(assessment.get("created_at")),
        "completed_at": _isoformat(assessment.get("completed_at")),
        "aggregate_payload": aggregate_payload,
        "scale_handoff_payload": scale_handoff_payload,
        "required_scales": _ensure_string_list(
            assessment.get("required_scales") or scale_handoff_payload.get("required_scales")
        ),
        "selected_scales": _ensure_string_list(
            assessment.get("selected_scales") or scale_handoff_payload.get("required_scales")
        ),
        "source_consultation_flow_run_id": assessment.get(
            "source_consultation_flow_run_id"
        ),
        "multimodal_session_id": assessment.get("multimodal_session_id"),
    }


def _merge_assessment_result_payload(
    assessment: dict[str, Any] | None,
    result_row: dict[str, Any],
) -> dict[str, Any]:
    aggregate_payload = _ensure_json_dict((assessment or {}).get("aggregate_payload"))
    scale_result_map = _ensure_json_dict(aggregate_payload.get("scale_result_map"))
    scale_slug = str(result_row.get("scale_slug") or "").strip()
    aggregate_result = _ensure_json_dict(scale_result_map.get(scale_slug))

    return {
        "scale_slug": scale_slug,
        "raw_score": result_row.get("raw_score", aggregate_result.get("raw_score")),
        "derived_score": result_row.get(
            "derived_score", aggregate_result.get("derived_score")
        ),
        "normalized_score": aggregate_result.get("normalized_score"),
        "interpretation_level": result_row.get(
            "interpretation_level", aggregate_result.get("interpretation_level")
        ),
        "interpretation_label": result_row.get(
            "interpretation_label", aggregate_result.get("interpretation_label")
        ),
        "score_details": _ensure_json_dict(aggregate_result.get("score_details")),
        "risk_flags": _ensure_json_list(
            result_row.get("risk_flags") or aggregate_result.get("risk_flags")
        ),
        "completed_at": _isoformat(
            result_row.get("completed_at") or aggregate_result.get("completed_at")
        ),
    }


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
        assessments_by_encounter = _load_latest_assessments_by_encounter(
            db_session, encounter_ids
        )

        consultation_map: dict[str, ConsultationSession] = {}
        for c in consultations:
            eid = c.encounter_session_id
            if eid and (
                eid not in consultation_map
                or _safe_datetime(c.created_at)
                > _safe_datetime(consultation_map[eid].created_at)
            ):
                consultation_map[eid] = c

        result: list[dict[str, Any]] = []
        for encounter in encounters:
            consultation = consultation_map.get(encounter.id)
            assessment_summary = _extract_assessment_summary(
                assessments_by_encounter.get(encounter.id)
            )
            result.append({
                "id": encounter.id,
                "status": encounter.status,
                "current_flow_type": encounter.current_flow_type,
                "created_at": encounter.created_at.isoformat() if encounter.created_at else None,
                "completed_at": encounter.completed_at.isoformat() if encounter.completed_at else None,
                "consultation_session_id": consultation.id if consultation else None,
                "assessment_session_id": assessment_summary["assessment_session_id"],
                "chief_complaint_summary": consultation.chief_complaint_summary if consultation else None,
                "phq9_score": assessment_summary["phq9_score"],
                "phq9_risk_level": assessment_summary["phq9_risk_level"],
                "overall_risk_level": assessment_summary["overall_risk_level"],
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

        assessment = _load_latest_assessment_for_encounter(db_session, encounter_id)

        assessment_results: list[dict[str, Any]] = []
        assessment_payload = _build_assessment_payload(assessment)
        if assessment is not None:
            results = _load_assessment_results(db_session, str(assessment.get("id")))
            for result_row in results:
                assessment_results.append(
                    _merge_assessment_result_payload(assessment, result_row)
                )

        # 组装问诊摘要
        consultation_payload = _build_consultation_payload(consultation)

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
            if assessment.get("created_at"):
                timeline.append({"event": "assessment_created", "at": _isoformat(assessment.get("created_at"))})
            if assessment.get("started_at"):
                timeline.append({"event": "assessment_started", "at": _isoformat(assessment.get("started_at"))})
            if assessment.get("completed_at"):
                timeline.append({"event": "assessment_completed", "at": _isoformat(assessment.get("completed_at"))})
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
