from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models import AssessmentAnswer, AssessmentResult, AssessmentSession
from app.schemas.assessment import CreateAssessmentSessionRequest, SubmitAssessmentAnswerRequest
from app.services.assessment_multimodal_bridge import (
    ensure_multimodal_session_binding,
    finalize_assessment_turn_bundle,
    get_assessment_turn_multimodal_bundle as fetch_assessment_turn_multimodal_bundle,
    recover_assessment_turn_hot_state as recover_assessment_turn_hot_state_upstream,
    refresh_multimodal_live_snapshot,
    stream_assessment_multimodal_live as stream_assessment_multimodal_live_upstream,
)
from app.services.scale_loader import ScaleDefinition, ScaleLoaderError, get_scale_loader


class AssessmentServiceError(Exception):
    def __init__(self, message: str, code: int, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class NormalizedAssessmentAnswer:
    label: str
    score: int
    normalization_source: str


LETTER_ALIASES: tuple[str, ...] = ("a", "b", "c", "d", "e", "f")
POSITION_PATTERNS: dict[int, tuple[str, ...]] = {
    1: ("第一个", "第一项", "第一档", "选一", "选1", "一档", "第1个", "第1项"),
    2: ("第二个", "第二项", "第二档", "选二", "选2", "二档", "第2个", "第2项"),
    3: ("第三个", "第三项", "第三档", "选三", "选3", "三档", "第3个", "第3项"),
    4: ("第四个", "第四项", "第四档", "选四", "选4", "四档", "第4个", "第4项"),
    5: ("第五个", "第五项", "第五档", "选五", "选5", "五档", "第5个", "第5项"),
    6: ("第六个", "第六项", "第六档", "选六", "选6", "六档", "第6个", "第6项"),
}
VOICE_OPTION_SYNONYMS: dict[str, dict[int, tuple[str, ...]]] = {
    "phq9": {
        0: ("完全没有", "没有", "从来没有", "一点没有", "完全没", "0分"),
        1: ("几天", "有几天", "一两天", "两三天", "偶尔", "偶尔会", "有时候", "1分"),
        2: ("一半以上", "一半以上的日子", "大半时间", "很多天", "比较多", "三到六天", "3到6天", "2分"),
        3: ("几乎每天", "几乎天天", "每天", "天天", "基本每天", "一直都", "七到九天", "7到9天", "3分"),
    },
    "sds": {
        1: ("没有或很少时间", "没有", "很少", "几乎没有", "基本没有", "1分"),
        2: ("小部分时间", "少部分时间", "一小部分时间", "有一些时候", "有时", "偶尔", "2分"),
        3: ("相当多时间", "很多时候", "较多时间", "经常", "常常", "3分"),
        4: ("绝大部分或全部时间", "绝大部分时间", "全部时间", "大部分时间", "几乎总是", "一直都是", "总是", "4分"),
    },
}


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


def _validate_source_consultation_handoff(
    db_session: Session,
    payload: CreateAssessmentSessionRequest,
    *,
    acting_user_id: str,
) -> None:
    source_consultation_id = str(payload.source_consultation_flow_run_id or "").strip()
    if not source_consultation_id:
        return

    consultation_row = db_session.execute(
        text(
            """
            select id, encounter_session_id, status
            from consultation_sessions
            where id = :consultation_id and user_id = :user_id
            """
        ),
        {
            "consultation_id": source_consultation_id,
            "user_id": acting_user_id,
        },
    ).mappings().first()
    if not consultation_row:
        raise AssessmentServiceError(
            "source consultation session not found",
            code=4044,
            status_code=404,
        )

    expected_encounter_id = str(payload.encounter_session_id or "").strip()
    actual_encounter_id = str(consultation_row.get("encounter_session_id") or "").strip()
    if expected_encounter_id and actual_encounter_id != expected_encounter_id:
        raise AssessmentServiceError(
            "source consultation session does not belong to the requested encounter",
            code=4096,
            status_code=409,
        )

    if str(consultation_row.get("status") or "").strip() != "handoff_ready":
        raise AssessmentServiceError(
            "source consultation session is not ready for assessment handoff",
            code=4097,
            status_code=409,
        )


def _mark_encounter_completed(
    db_session: Session,
    *,
    encounter_session_id: str | None,
    acting_user_id: str,
    now: datetime,
) -> None:
    normalized_encounter_session_id = str(encounter_session_id or "").strip()
    if not normalized_encounter_session_id:
        return

    result = db_session.execute(
        text(
            """
            update encounter_sessions
            set current_flow_type = :current_flow_type,
                status = :status,
                completed_at = coalesce(completed_at, :completed_at),
                updated_at = :updated_at
            where id = :encounter_session_id and user_id = :user_id
            """
        ),
        {
            "current_flow_type": "assessment",
            "status": "completed",
            "completed_at": now,
            "updated_at": now,
            "encounter_session_id": normalized_encounter_session_id,
            "user_id": acting_user_id,
        },
    )
    if result.rowcount == 0:  # pyright: ignore[reportAttributeAccessIssue]
        raise AssessmentServiceError(
            "encounter session not found for assessment completion",
            code=4045,
            status_code=404,
        )


def _mark_multimodal_session_completed(
    db_session: Session,
    *,
    multimodal_session_id: str | None,
    encounter_session_id: str | None,
    now: datetime,
) -> None:
    normalized_multimodal_session_id = str(multimodal_session_id or "").strip()
    if normalized_multimodal_session_id:
        result = db_session.execute(
            text(
                """
                update multimodal_sessions
                set status = :status,
                    completed_at = coalesce(completed_at, :completed_at),
                    updated_at = :updated_at
                where id = :session_id
                """
            ),
            {
                "status": "completed",
                "completed_at": now,
                "updated_at": now,
                "session_id": normalized_multimodal_session_id,
            },
        )
        if result.rowcount > 0:  # pyright: ignore[reportAttributeAccessIssue]
            return

    normalized_encounter_session_id = str(encounter_session_id or "").strip()
    if not normalized_encounter_session_id:
        return

    result = db_session.execute(
        text(
            """
            update multimodal_sessions
            set status = :status,
                completed_at = coalesce(completed_at, :completed_at),
                updated_at = :updated_at
            where encounter_session_id = :encounter_session_id
            """
        ),
        {
            "status": "completed",
            "completed_at": now,
            "updated_at": now,
            "encounter_session_id": normalized_encounter_session_id,
        },
    )
    if result.rowcount == 0:  # pyright: ignore[reportAttributeAccessIssue]
        raise AssessmentServiceError(
            "multimodal session not found for assessment completion",
            code=4046,
            status_code=404,
        )


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


def _serialize_accepted_answer(
    answer_record: AssessmentAnswer,
    *,
    normalization_source: str,
) -> dict[str, Any]:
    return {
        "answer_id": answer_record.id,
        "session_id": answer_record.session_id,
        "scale_slug": answer_record.scale_slug,
        "item_id": answer_record.item_id,
        "item_index": answer_record.item_index,
        "question_key": answer_record.question_key,
        "turn_id": answer_record.turn_id,
        "answer_source": answer_record.answer_source,
        "selected_option_label": answer_record.selected_option_label or answer_record.normalized_option,
        "selected_option_score": answer_record.selected_option_score or answer_record.score_value,
        "transcript_text": answer_record.transcript_text,
        "transcript_source": answer_record.transcript_source,
        "audio_uri": answer_record.audio_uri,
        "original_audio_uri": answer_record.original_audio_uri,
        "normalized_wav_uri": answer_record.normalized_wav_uri,
        "response_started_at": (
            answer_record.response_started_at.isoformat() if answer_record.response_started_at else None
        ),
        "response_completed_at": (
            answer_record.response_completed_at.isoformat() if answer_record.response_completed_at else None
        ),
        "capture_timestamp": (
            answer_record.capture_timestamp.isoformat() if answer_record.capture_timestamp else None
        ),
        "normalization_source": normalization_source,
        "created_at": answer_record.created_at.isoformat(),
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
        "multimodal_session_id": session_record.multimodal_session_id,
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


def _normalize_text_fragment(value: str) -> str:
    normalized = str(value or "").strip().lower()
    normalized = normalized.replace("“", "").replace("”", "").replace("‘", "").replace("’", "")
    normalized = re.sub(r"[，。；：、,.!?？!（）()\[\]【】/\-—_]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _resolve_answer_source(payload: SubmitAssessmentAnswerRequest) -> str:
    explicit = (payload.answer_source or "").strip().lower()
    if explicit:
        return explicit
    if payload.transcript_text or payload.audio_uri or payload.original_audio_uri:
        return "voice"
    if payload.selected_option_label is not None or payload.selected_option_score is not None:
        return "click"
    return "unknown"


def _match_option_by_position(
    normalized_text: str,
    position_scores: dict[int, int],
) -> int | None:
    for position, phrases in POSITION_PATTERNS.items():
        if position in position_scores and any(phrase in normalized_text for phrase in phrases):
            return position_scores[position]
    return None


def _match_option_by_letter(
    normalized_text: str,
    letter_scores: dict[str, int],
) -> int | None:
    for letter, score in letter_scores.items():
        if re.search(rf"(?:^|\s|选项|选择|答案){re.escape(letter)}(?:$|\s)", normalized_text):
            return score
    return None


def _match_option_by_numeric_token(
    normalized_text: str,
    options_by_score: dict[int, str],
) -> int | None:
    matches = re.findall(r"\d+", normalized_text)
    for raw_match in matches:
        score = int(raw_match)
        if score in options_by_score:
            return score
    return None


def _match_option_by_label_text(
    raw_text: str,
    normalized_text: str,
    options_by_label: dict[str, int],
) -> int | None:
    normalized_label_to_score = {
        _normalize_text_fragment(label): score for label, score in options_by_label.items()
    }
    for label, score in options_by_label.items():
        if label and label in raw_text:
            return score
    for normalized_label, score in normalized_label_to_score.items():
        if normalized_label and normalized_label in normalized_text:
            return score
    return None


def _match_option_by_scale_synonyms(
    scale_slug: str,
    normalized_text: str,
    options_by_score: dict[int, str],
) -> int | None:
    synonym_groups = VOICE_OPTION_SYNONYMS.get(scale_slug, {})
    for score, phrases in synonym_groups.items():
        if score not in options_by_score:
            continue
        if any(_normalize_text_fragment(phrase) in normalized_text for phrase in phrases):
            return score
    return None


def _normalize_option(
    scale_definition: ScaleDefinition,
    payload: SubmitAssessmentAnswerRequest,
) -> NormalizedAssessmentAnswer:
    options_by_score = {option.score: option.label for option in scale_definition.answer_options}
    options_by_label = {option.label: option.score for option in scale_definition.answer_options}
    position_scores = {
        index + 1: option.score for index, option in enumerate(scale_definition.answer_options)
    }
    letter_scores = {
        LETTER_ALIASES[index]: option.score
        for index, option in enumerate(scale_definition.answer_options)
        if index < len(LETTER_ALIASES)
    }

    if payload.selected_option_score is not None:
        if payload.selected_option_score not in options_by_score:
            raise AssessmentServiceError("selected option score is invalid", code=4005)
        return NormalizedAssessmentAnswer(
            label=options_by_score[payload.selected_option_score],
            score=payload.selected_option_score,
            normalization_source="selected_option_score",
        )

    if payload.selected_option_label:
        if payload.selected_option_label not in options_by_label:
            raise AssessmentServiceError("selected option label is invalid", code=4006)
        score = options_by_label[payload.selected_option_label]
        return NormalizedAssessmentAnswer(
            label=payload.selected_option_label,
            score=score,
            normalization_source="selected_option_label",
        )

    raw_text = (payload.transcript_text or payload.raw_input or "").strip()
    if not raw_text:
        raise AssessmentServiceError("missing assessment answer input", code=4007)

    normalized_text = _normalize_text_fragment(raw_text)

    label_match = _match_option_by_label_text(raw_text, normalized_text, options_by_label)
    if label_match is not None:
        return NormalizedAssessmentAnswer(
            label=options_by_score[label_match],
            score=label_match,
            normalization_source="label_text_match",
        )

    position_match = _match_option_by_position(normalized_text, position_scores)
    if position_match is not None:
        return NormalizedAssessmentAnswer(
            label=options_by_score[position_match],
            score=position_match,
            normalization_source="position_match",
        )

    letter_match = _match_option_by_letter(normalized_text, letter_scores)
    if letter_match is not None:
        return NormalizedAssessmentAnswer(
            label=options_by_score[letter_match],
            score=letter_match,
            normalization_source="letter_match",
        )

    numeric_match = _match_option_by_numeric_token(normalized_text, options_by_score)
    if numeric_match is not None:
        return NormalizedAssessmentAnswer(
            label=options_by_score[numeric_match],
            score=numeric_match,
            normalization_source="numeric_match",
        )

    synonym_match = _match_option_by_scale_synonyms(
        scale_definition.slug,
        normalized_text,
        options_by_score,
    )
    if synonym_match is not None:
        return NormalizedAssessmentAnswer(
            label=options_by_score[synonym_match],
            score=synonym_match,
            normalization_source="scale_synonym_match",
        )

    raise AssessmentServiceError(
        "unable to normalize assessment answer",
        code=4008,
        status_code=422,
    )


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
        item_id = str(flag_definition.get("item_id") or "")
        answer = answers_by_item.get(item_id)
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

    resolved_answers = list(answers)
    raw_score, derived_score = _score_scale(scale_definition, resolved_answers)
    interpretation_level, interpretation_label = _resolve_interpretation(scale_definition, derived_score)
    risk_flags = _build_risk_flags(scale_definition, resolved_answers)
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
    if not payload.multimodal_session_id and not str(payload.encounter_session_id or "").strip():
        raise AssessmentServiceError(
            "encounter_session_id is required when multimodal_session_id is missing",
            code=4014,
            status_code=422,
        )

    selected_scales = _normalize_scale_sequence(payload)
    now = _now()
    with get_db_session() as db_session:
        _validate_source_consultation_handoff(
            db_session,
            payload,
            acting_user_id=acting_user_id,
        )
        session_record = AssessmentSession(
            id=str(uuid.uuid4()),
            user_id=payload.user_id,
            encounter_session_id=payload.encounter_session_id,
            source_consultation_flow_run_id=payload.source_consultation_flow_run_id,
            multimodal_session_id=payload.multimodal_session_id,
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
        if not session_record.multimodal_session_id:
            ensure_multimodal_session_binding(
                session_record,
                acting_user_id=acting_user_id,
            )
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

        normalized_answer = _normalize_option(scale_definition, payload)
        answer_source = _resolve_answer_source(payload)
        bound_multimodal_session_id = str(
            session_record.multimodal_session_id or ""
        ).strip() or None
        if not bound_multimodal_session_id:
            bound_multimodal_session_id = ensure_multimodal_session_binding(
                session_record,
                acting_user_id=acting_user_id,
            )
        if payload.multimodal_session_id:
            if str(payload.multimodal_session_id).strip() != bound_multimodal_session_id:
                raise AssessmentServiceError(
                    "assessment multimodal session mismatch",
                    code=4094,
                    status_code=409,
                )
        question_key = payload.question_key or f"{scale_definition.slug}-{current_item['index']:03d}"
        raw_input = payload.raw_input or payload.transcript_text
        multimodal_session_id = (
            payload.multimodal_session_id
            or bound_multimodal_session_id
            or None
        )
        answer_record = AssessmentAnswer(
            id=str(uuid.uuid4()),
            session_id=session_record.id,
            scale_slug=scale_definition.slug,
            item_id=current_item["item_id"],
            item_index=int(current_item.get("index") or (session_record.current_item_index + 1)),
            question_key=question_key,
            turn_id=payload.turn_id,
            answer_source=answer_source,
            raw_input=raw_input,
            transcript_text=payload.transcript_text,
            transcript_source=payload.transcript_source,
            audio_uri=payload.audio_uri,
            original_audio_uri=payload.original_audio_uri,
            normalized_wav_uri=payload.normalized_wav_uri,
            multimodal_session_id=multimodal_session_id,
            normalized_option=normalized_answer.label,
            selected_option_label=normalized_answer.label,
            score_value=normalized_answer.score,
            selected_option_score=normalized_answer.score,
            response_started_at=payload.response_started_at,
            response_completed_at=payload.response_completed_at,
            capture_timestamp=payload.capture_timestamp,
            created_at=_now(),
        )
        db_session.add(answer_record)
        db_session.flush()
        turn_bundle = finalize_assessment_turn_bundle(
            session_record,
            turn_id=payload.turn_id or question_key,
            acting_user_id=acting_user_id,
        )
        accepted_answer = _serialize_accepted_answer(
            answer_record,
            normalization_source=normalized_answer.normalization_source,
        )
        if turn_bundle is not None:
            accepted_answer["turn_bundle"] = turn_bundle

        session_record.updated_at = _now()
        next_item_index = session_record.current_item_index + 1
        if next_item_index < len(scale_definition.items):
            session_record.current_item_index = next_item_index
            db_session.flush()
            return {
                "assessment_session": _serialize_session(db_session, session_record),
                "accepted_answer": accepted_answer,
            }

        _store_scale_result(db_session, session_record, scale_definition)
        selected_scales = _ensure_json_list(session_record.selected_scales)
        current_scale_index = selected_scales.index(scale_definition.slug)
        if current_scale_index < len(selected_scales) - 1:
            session_record.current_scale_slug = selected_scales[current_scale_index + 1]
            session_record.current_item_index = 0
            db_session.flush()
            return {
                "assessment_session": _serialize_session(db_session, session_record),
                "accepted_answer": accepted_answer,
            }

        completion_time = _now()
        session_record.current_scale_slug = None
        session_record.current_item_index = 0
        session_record.status = "completed"
        session_record.completed_at = completion_time
        session_record.aggregate_payload = _build_aggregate_payload(db_session, session_record)
        _mark_encounter_completed(
            db_session,
            encounter_session_id=session_record.encounter_session_id,
            acting_user_id=acting_user_id,
            now=completion_time,
        )
        _mark_multimodal_session_completed(
            db_session,
            multimodal_session_id=session_record.multimodal_session_id,
            encounter_session_id=session_record.encounter_session_id,
            now=completion_time,
        )
        db_session.flush()
        return {
            "assessment_session": _serialize_session(db_session, session_record),
            "accepted_answer": accepted_answer,
        }


def get_assessment_multimodal_live(
    session_id: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        _require_session_owner(session_record, acting_user_id)
        return refresh_multimodal_live_snapshot(
            session_record,
            acting_user_id=acting_user_id,
        )


def stream_assessment_multimodal_live(
    session_id: str,
    acting_user_id: str | None,
):
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        _require_session_owner(session_record, acting_user_id)
        return stream_assessment_multimodal_live_upstream(
            session_record,
            acting_user_id=acting_user_id,
        )


def get_assessment_turn_multimodal_bundle(
    session_id: str,
    turn_id: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        _require_session_owner(session_record, acting_user_id)
        return fetch_assessment_turn_multimodal_bundle(
            session_record,
            turn_id=turn_id,
            acting_user_id=acting_user_id,
        )


def recover_assessment_turn_hot_state(
    session_id: str,
    turn_id: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        _require_session_owner(session_record, acting_user_id)
        return recover_assessment_turn_hot_state_upstream(
            session_record,
            turn_id=turn_id,
            acting_user_id=acting_user_id,
        )
