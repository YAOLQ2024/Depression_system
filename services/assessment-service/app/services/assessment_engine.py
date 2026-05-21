from __future__ import annotations

from datetime import datetime, timezone
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models import AssessmentAnswer, AssessmentResult, AssessmentSession
from app.schemas.assessment import CreateAssessmentSessionRequest, SubmitAssessmentAnswerRequest
from app.services.scale_loader import ScaleDefinition, ScaleLoaderError, get_scale_loader


class AssessmentServiceError(Exception):
    def __init__(self, message: str, code: int, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_json_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def _ensure_json_list(value: list[str] | None) -> list[str]:
    return list(value or [])


def _require_acting_user_id(acting_user_id: str | None) -> str:
    if not acting_user_id:
        raise AssessmentServiceError("missing acting user id", code=4013, status_code=401)
    return acting_user_id


def _translate_loader_error(exc: ScaleLoaderError) -> AssessmentServiceError:
    return AssessmentServiceError(str(exc), code=5001, status_code=500)


def _normalize_scale_sequence(payload: CreateAssessmentSessionRequest) -> list[str]:
    loader = get_scale_loader()
    active_slugs = loader.active_scale_slugs
    candidate = payload.selected_scales or payload.scale_handoff_payload.get("required_scales") or active_slugs
    normalized: list[str] = []
    seen: set[str] = set()
    for slug in candidate:
        if slug not in active_slugs:
            raise AssessmentServiceError(f"unsupported scale slug: {slug}", code=4002)
        if slug in seen:
            continue
        seen.add(slug)
        normalized.append(slug)
    if not normalized:
        raise AssessmentServiceError("no active scales selected", code=4003)
    return normalized


def _get_session_or_raise(db_session: Session, session_id: str) -> AssessmentSession:
    session_record = db_session.get(AssessmentSession, session_id)
    if not session_record:
        raise AssessmentServiceError("assessment session not found", code=4041, status_code=404)
    return session_record


def _require_session_owner(session_record: AssessmentSession, acting_user_id: str) -> None:
    if session_record.user_id != acting_user_id:
        raise AssessmentServiceError("assessment session forbidden", code=4031, status_code=403)


def _get_current_scale_or_raise(session_record: AssessmentSession) -> ScaleDefinition:
    if not session_record.current_scale_slug:
        raise AssessmentServiceError("assessment session has no active scale", code=4004)
    try:
        return get_scale_loader().load_scale(session_record.current_scale_slug)
    except ScaleLoaderError as exc:
        raise _translate_loader_error(exc) from exc


def _build_current_item(scale_definition: ScaleDefinition, item_index: int) -> dict[str, Any] | None:
    if item_index < 0 or item_index >= len(scale_definition.items):
        return None
    item = scale_definition.items[item_index]
    return {
        "scale_slug": scale_definition.slug,
        "item_id": item.id,
        "index": item.index,
        "text": item.text,
        "answer_options": [{"score": option.score, "label": option.label} for option in scale_definition.answer_options],
    }


def _serialize_result(result_record: AssessmentResult) -> dict[str, Any]:
    return {
        "scale_slug": result_record.scale_slug,
        "raw_score": result_record.raw_score,
        "derived_score": result_record.derived_score,
        "interpretation_level": result_record.interpretation_level,
        "interpretation_label": result_record.interpretation_label,
        "risk_flags": list(result_record.risk_flags or []),
        "completed_at": result_record.completed_at.isoformat(),
    }


def _serialize_session(db_session: Session, session_record: AssessmentSession) -> dict[str, Any]:
    results = db_session.scalars(
        select(AssessmentResult)
        .where(AssessmentResult.session_id == session_record.id)
        .order_by(AssessmentResult.completed_at.asc())
    ).all()

    current_item = None
    if session_record.current_scale_slug and session_record.status != "completed":
        current_scale = _get_current_scale_or_raise(session_record)
        current_item = _build_current_item(current_scale, session_record.current_item_index)

    return {
        "session_id": session_record.id,
        "user_id": session_record.user_id,
        "encounter_session_id": session_record.encounter_session_id,
        "source_consultation_flow_run_id": (
            session_record.source_consultation_flow_run_id
        ),
        "status": session_record.status,
        "required_scales": _ensure_json_list(session_record.required_scales),
        "selected_scales": _ensure_json_list(session_record.selected_scales),
        "current_scale_slug": session_record.current_scale_slug,
        "current_item_index": session_record.current_item_index,
        "current_item": current_item,
        "scale_handoff_payload": _ensure_json_dict(session_record.scale_handoff_payload),
        "capture_context": _ensure_json_dict(session_record.capture_context),
        "aggregate_payload": _ensure_json_dict(session_record.aggregate_payload),
        "results": [_serialize_result(result_record) for result_record in results],
        "created_at": session_record.created_at.isoformat(),
        "updated_at": session_record.updated_at.isoformat(),
        "started_at": session_record.started_at.isoformat() if session_record.started_at else None,
        "completed_at": session_record.completed_at.isoformat() if session_record.completed_at else None,
    }


def _normalize_option(scale_definition: ScaleDefinition, payload: SubmitAssessmentAnswerRequest) -> tuple[str, int]:
    options_by_score = {option.score: option.label for option in scale_definition.answer_options}
    options_by_label = {option.label: option.score for option in scale_definition.answer_options}

    if payload.selected_option_score is not None:
        if payload.selected_option_score not in options_by_score:
            raise AssessmentServiceError("selected option score is invalid", code=4005)
        return options_by_score[payload.selected_option_score], payload.selected_option_score

    if payload.selected_option_label:
        if payload.selected_option_label not in options_by_label:
            raise AssessmentServiceError("selected option label is invalid", code=4006)
        score = options_by_label[payload.selected_option_label]
        return payload.selected_option_label, score

    raw_text = (payload.raw_input or "").strip()
    if not raw_text:
        raise AssessmentServiceError("missing assessment answer input", code=4007)

    digit_match = re.search(r"\d+", raw_text)
    if digit_match:
        score = int(digit_match.group(0))
        if score in options_by_score:
            return options_by_score[score], score

    for label, score in options_by_label.items():
        if label in raw_text:
            return label, score

    raise AssessmentServiceError("unable to normalize assessment answer", code=4008)


def _resolve_interpretation(scale_definition: ScaleDefinition, derived_score: int) -> tuple[str | None, str | None]:
    for rule in scale_definition.scoring.get("severity_rules") or []:
        minimum = int(rule["min"])
        maximum = int(rule["max"])
        if minimum <= derived_score <= maximum:
            return str(rule.get("level")), str(rule.get("label"))
    return None, None


def _score_scale(scale_definition: ScaleDefinition, answers: list[AssessmentAnswer]) -> tuple[int, int]:
    score_method = scale_definition.scoring.get("method")
    raw_score = sum(answer.score_value for answer in answers)

    if score_method == "sum":
        return raw_score, raw_score

    if score_method == "standard_score":
        reverse_items = set(scale_definition.scoring.get("reverse_scored_items") or [])
        normalized_scores: list[int] = []
        option_scores = [option.score for option in scale_definition.answer_options]
        minimum_score = min(option_scores)
        maximum_score = max(option_scores)
        for answer in answers:
            if answer.item_id in reverse_items:
                normalized_scores.append(maximum_score + minimum_score - answer.score_value)
            else:
                normalized_scores.append(answer.score_value)
        raw_score = sum(normalized_scores)
        return raw_score, int(raw_score * 1.25)

    if score_method == "sum_excluding_not_applicable":
        na_value = int(scale_definition.scoring.get("na_value", 9))
        filtered_scores = [answer.score_value for answer in answers if answer.score_value != na_value]
        raw_score = sum(filtered_scores)
        return raw_score, raw_score

    raise AssessmentServiceError(f"unsupported scoring method: {score_method}", code=5002, status_code=500)


def _build_risk_flags(scale_definition: ScaleDefinition, answers: list[AssessmentAnswer]) -> list[dict[str, Any]]:
    answers_by_item = {answer.item_id: answer for answer in answers}
    flags: list[dict[str, Any]] = []
    for flag_definition in scale_definition.risk_flags:
        answer = answers_by_item.get(flag_definition.get("item_id"))
        if not answer:
            continue
        minimum_score = int(flag_definition.get("min_score", 0))
        if answer.score_value >= minimum_score:
            flags.append(
                {
                    "flag": flag_definition.get("flag"),
                    "label": flag_definition.get("label"),
                    "item_id": answer.item_id,
                    "score_value": answer.score_value,
                }
            )
    return flags


def _store_scale_result(db_session: Session, session_record: AssessmentSession, scale_definition: ScaleDefinition) -> AssessmentResult:
    answers = db_session.scalars(
        select(AssessmentAnswer)
        .where(
            AssessmentAnswer.session_id == session_record.id,
            AssessmentAnswer.scale_slug == scale_definition.slug,
        )
        .order_by(AssessmentAnswer.item_index.asc())
    ).all()
    if len(answers) != len(scale_definition.items):
        raise AssessmentServiceError("scale answers are incomplete", code=4009)

    raw_score, derived_score = _score_scale(scale_definition, answers)
    interpretation_level, interpretation_label = _resolve_interpretation(scale_definition, derived_score)
    risk_flags = _build_risk_flags(scale_definition, answers)
    now = _now()

    existing_result = db_session.scalar(
        select(AssessmentResult).where(
            AssessmentResult.session_id == session_record.id,
            AssessmentResult.scale_slug == scale_definition.slug,
        )
    )
    if existing_result:
        result_record = existing_result
        result_record.raw_score = raw_score
        result_record.derived_score = derived_score
        result_record.interpretation_level = interpretation_level
        result_record.interpretation_label = interpretation_label
        result_record.risk_flags = risk_flags
        result_record.completed_at = now
        result_record.updated_at = now
        return result_record

    result_record = AssessmentResult(
        id=str(uuid.uuid4()),
        session_id=session_record.id,
        scale_slug=scale_definition.slug,
        raw_score=raw_score,
        derived_score=derived_score,
        interpretation_level=interpretation_level,
        interpretation_label=interpretation_label,
        risk_flags=risk_flags,
        completed_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(result_record)
    return result_record


def _build_aggregate_payload(db_session: Session, session_record: AssessmentSession) -> dict[str, Any]:
    results = db_session.scalars(
        select(AssessmentResult)
        .where(AssessmentResult.session_id == session_record.id)
        .order_by(AssessmentResult.completed_at.asc())
    ).all()
    return {
        "assessment_session_id": session_record.id,
        "encounter_session_id": session_record.encounter_session_id,
        "source_consultation_flow_run_id": (
            session_record.source_consultation_flow_run_id
        ),
        "scale_count": len(results),
        "scale_results": [_serialize_result(result_record) for result_record in results],
        "source_handoff": _ensure_json_dict(session_record.scale_handoff_payload),
    }


def get_assessment_catalog() -> list[dict[str, Any]]:
    try:
        return get_scale_loader().build_catalog()
    except ScaleLoaderError as exc:
        raise _translate_loader_error(exc) from exc


def create_assessment_session(payload: CreateAssessmentSessionRequest, acting_user_id: str | None) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    if payload.user_id != acting_user_id:
        raise AssessmentServiceError("user mismatch for assessment creation", code=4032, status_code=403)

    selected_scales = _normalize_scale_sequence(payload)
    now = _now()
    with get_db_session() as db_session:
        session_record = AssessmentSession(
            id=str(uuid.uuid4()),
            user_id=payload.user_id,
            encounter_session_id=payload.encounter_session_id,
            source_consultation_flow_run_id=payload.source_consultation_flow_run_id,
            status="in_progress",
            required_scales=list(payload.scale_handoff_payload.get("required_scales") or selected_scales),
            selected_scales=selected_scales,
            current_scale_slug=selected_scales[0],
            current_item_index=0,
            scale_handoff_payload=_ensure_json_dict(payload.scale_handoff_payload),
            capture_context=_ensure_json_dict(payload.capture_context),
            aggregate_payload={},
            created_at=now,
            updated_at=now,
            started_at=now,
        )
        db_session.add(session_record)
        db_session.flush()
        return _serialize_session(db_session, session_record)


def get_assessment_session(session_id: str, acting_user_id: str | None) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        _require_session_owner(session_record, acting_user_id)
        return _serialize_session(db_session, session_record)


def submit_assessment_answer(
    session_id: str,
    payload: SubmitAssessmentAnswerRequest,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        _require_session_owner(session_record, acting_user_id)

        if session_record.status == "completed":
            raise AssessmentServiceError("assessment session already completed", code=4091, status_code=409)

        scale_definition = _get_current_scale_or_raise(session_record)
        current_item = _build_current_item(scale_definition, session_record.current_item_index)
        if not current_item:
            raise AssessmentServiceError("assessment session current item missing", code=5003, status_code=500)
        if payload.item_id and payload.item_id != current_item["item_id"]:
            raise AssessmentServiceError("assessment item mismatch", code=4092, status_code=409)

        existing_answer = db_session.scalar(
            select(AssessmentAnswer).where(
                AssessmentAnswer.session_id == session_record.id,
                AssessmentAnswer.scale_slug == scale_definition.slug,
                AssessmentAnswer.item_id == current_item["item_id"],
            )
        )
        if existing_answer:
            raise AssessmentServiceError("assessment item already answered", code=4093, status_code=409)

        option_label, option_score = _normalize_option(scale_definition, payload)
        answer_record = AssessmentAnswer(
            id=str(uuid.uuid4()),
            session_id=session_record.id,
            scale_slug=scale_definition.slug,
            item_id=current_item["item_id"],
            item_index=session_record.current_item_index,
            raw_input=payload.raw_input,
            normalized_option=option_label,
            score_value=option_score,
            capture_timestamp=payload.capture_timestamp,
            created_at=_now(),
        )
        db_session.add(answer_record)
        db_session.flush()

        session_record.updated_at = _now()
        next_item_index = session_record.current_item_index + 1
        if next_item_index < len(scale_definition.items):
            session_record.current_item_index = next_item_index
            db_session.flush()
            return _serialize_session(db_session, session_record)

        _store_scale_result(db_session, session_record, scale_definition)
        selected_scales = _ensure_json_list(session_record.selected_scales)
        current_scale_index = selected_scales.index(scale_definition.slug)
        if current_scale_index < len(selected_scales) - 1:
            session_record.current_scale_slug = selected_scales[current_scale_index + 1]
            session_record.current_item_index = 0
            db_session.flush()
            return _serialize_session(db_session, session_record)

        session_record.current_scale_slug = None
        session_record.current_item_index = 0
        session_record.status = "completed"
        session_record.completed_at = _now()
        session_record.aggregate_payload = _build_aggregate_payload(db_session, session_record)
        db_session.flush()
        return _serialize_session(db_session, session_record)
