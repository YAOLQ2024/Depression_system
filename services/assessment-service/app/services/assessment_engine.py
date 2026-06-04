from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.clients.multimodal_client import (
    finish_eeg_turn as finish_upstream_eeg_turn,
    get_eeg_turn_results as fetch_upstream_eeg_turn_results,
    start_eeg_turn as start_upstream_eeg_turn,
)
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
from app.services.scale_scoring import (
    ScaleScoringError,
    build_normalized_score,
    build_score_details,
    compute_scale_scoring,
)
from app.services.scale_loader import ScaleDefinition, ScaleLoaderError, get_scale_loader


ASSESSMENT_STAGE_ID = "assessment"


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
DETAIL_QUESTION_PREFIXES: dict[str, tuple[str, ...]] = {
    "sds": (
        "接下来进入SDS量表问诊环节，请根据您最近一星期的实际情况回答。",
    ),
    "sas": (
        "接下来进入SAS量表问诊环节，我会问您20个问题，请根据您最近一星期的实际感受，按照选项作答。",
    ),
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


def _translate_scoring_error(exc: ScaleScoringError) -> AssessmentServiceError:
    return AssessmentServiceError(str(exc), code=5002, status_code=500)


def _extract_upstream_data(upstream: dict, *, error_code: int) -> dict[str, Any]:
    if upstream["status"] >= 400:
        payload = upstream.get("payload") or {}
        raise AssessmentServiceError(
            str(payload.get("message") or "multimodal service request failed"),
            code=int(payload.get("code") or error_code),
            status_code=int(upstream["status"]),
        )
    data = (upstream.get("payload") or {}).get("data") or {}
    if not isinstance(data, dict):
        raise AssessmentServiceError(
            "multimodal service returned invalid payload",
            code=error_code,
            status_code=502,
        )
    return data


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


def _build_assessment_question_key(scale_slug: str, item_index: int) -> str:
    return f"{scale_slug}-{int(item_index):03d}"


def _build_assessment_turn_id(
    session_record: AssessmentSession,
    *,
    scale_slug: str,
    item_id: str,
) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"assessment:{session_record.id}:{scale_slug}:{item_id}",
        )
    )


def _build_current_turn_context(session_record: AssessmentSession) -> dict[str, Any] | None:
    if session_record.status == "completed" or not session_record.current_scale_slug:
        return None
    scale_definition = _get_current_scale_or_raise(session_record)
    current_item = _build_current_item(scale_definition, session_record.current_item_index)
    if not current_item:
        return None
    return {
        "turn_id": _build_assessment_turn_id(
            session_record,
            scale_slug=scale_definition.slug,
            item_id=str(current_item["item_id"]),
        ),
        "question_key": _build_assessment_question_key(
            scale_definition.slug,
            int(current_item["index"]),
        ),
        "scale_definition": scale_definition,
        "current_item": current_item,
    }


def _serialize_result(
    scale_definition: ScaleDefinition,
    answers: list[AssessmentAnswer],
    result_record: AssessmentResult,
) -> dict[str, Any]:
    normalized_score = build_normalized_score(
        scale_definition,
        answers,
        raw_score=result_record.raw_score,
        derived_score=result_record.derived_score,
    )
    score_details = build_score_details(
        scale_definition,
        answers,
        raw_score=result_record.raw_score,
        derived_score=result_record.derived_score,
        normalized_score=normalized_score,
    )
    return {
        "scale_slug": result_record.scale_slug,
        "raw_score": result_record.raw_score,
        "derived_score": result_record.derived_score,
        "normalized_score": normalized_score,
        "interpretation_level": result_record.interpretation_level,
        "interpretation_label": result_record.interpretation_label,
        "risk_flags": list(result_record.risk_flags or []),
        "score_details": score_details,
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


def _serialize_scale_detail_item(
    scale_definition: ScaleDefinition,
    item: dict[str, Any],
    answer_record: AssessmentAnswer | None,
) -> dict[str, Any]:
    item_index = int(item.get("index") or 0)
    question_text = _sanitize_scale_detail_question_text(
        scale_definition.slug,
        item_index,
        str(item.get("question_text") or item.get("text") or "").strip(),
    )
    fallback_question_key = f"{scale_definition.slug}-{item_index:03d}" if item_index > 0 else None

    return {
        "item_id": str(item.get("id") or ""),
        "item_index": item_index,
        "question_key": (
            answer_record.question_key if answer_record and answer_record.question_key else fallback_question_key
        ),
        "question_text": question_text,
        "selected_option_label": (
            answer_record.selected_option_label or answer_record.normalized_option if answer_record else None
        ),
        "selected_option_score": (
            answer_record.selected_option_score or answer_record.score_value if answer_record else None
        ),
        "answer_source": answer_record.answer_source if answer_record else None,
        "transcript_text": answer_record.transcript_text if answer_record else None,
        "transcript_source": answer_record.transcript_source if answer_record else None,
        "response_started_at": (
            answer_record.response_started_at.isoformat()
            if answer_record and answer_record.response_started_at
            else None
        ),
        "response_completed_at": (
            answer_record.response_completed_at.isoformat()
            if answer_record and answer_record.response_completed_at
            else None
        ),
        "capture_timestamp": (
            answer_record.capture_timestamp.isoformat()
            if answer_record and answer_record.capture_timestamp
            else None
        ),
        "answered_at": answer_record.created_at.isoformat() if answer_record else None,
    }


def _serialize_scale_detail(
    db_session: Session,
    session_record: AssessmentSession,
    *,
    scale_slug: str,
) -> dict[str, Any]:
    known_scale_slugs = {
        *(_ensure_json_list(session_record.selected_scales)),
        *(_ensure_json_list(session_record.required_scales)),
    }
    if scale_slug != session_record.current_scale_slug and scale_slug not in known_scale_slugs:
        raise AssessmentServiceError("assessment scale detail not found", code=4047, status_code=404)

    try:
        scale_definition = get_scale_loader().load_scale(scale_slug)
    except ScaleLoaderError as exc:
        raise _translate_loader_error(exc) from exc

    result_record = db_session.scalar(
        select(AssessmentResult).where(
            AssessmentResult.session_id == session_record.id,
            AssessmentResult.scale_slug == scale_slug,
        )
    )
    answers = db_session.scalars(
        select(AssessmentAnswer)
        .where(
            AssessmentAnswer.session_id == session_record.id,
            AssessmentAnswer.scale_slug == scale_slug,
        )
        .order_by(AssessmentAnswer.item_index.asc(), AssessmentAnswer.created_at.asc())
    ).all()
    answers_by_item_id = {
        answer.item_id: answer for answer in answers
    }

    items = [
        _serialize_scale_detail_item(
            scale_definition,
            {
                "id": item.id,
                "index": item.index,
                "text": item.text,
                "question_text": item.question_text,
            },
            answers_by_item_id.get(item.id),
        )
        for item in scale_definition.items
    ]
    answered_item_count = sum(1 for item in items if item["selected_option_label"])

    return {
        "session_id": session_record.id,
        "scale_slug": scale_definition.slug,
        "scale_code": scale_definition.code,
        "scale_name": scale_definition.name,
        "scale_short_name": scale_definition.short_name,
        "status": (
            "completed"
            if result_record
            else "in_progress"
            if session_record.current_scale_slug == scale_definition.slug
            else "pending"
        ),
        "configured_item_count": scale_definition.item_count,
        "answered_item_count": answered_item_count,
        "raw_score": result_record.raw_score if result_record else None,
        "derived_score": result_record.derived_score if result_record else None,
        "normalized_score": (
            build_normalized_score(
                scale_definition,
                answers,
                raw_score=result_record.raw_score,
                derived_score=result_record.derived_score,
            )
            if result_record
            else None
        ),
        "interpretation_level": result_record.interpretation_level if result_record else None,
        "interpretation_label": result_record.interpretation_label if result_record else None,
        "risk_flags": list(result_record.risk_flags or []) if result_record else [],
        "completed_at": result_record.completed_at.isoformat() if result_record else None,
        "answer_options": [
            {"score": option.score, "label": option.label}
            for option in scale_definition.answer_options
        ],
        "items": items,
    }


def _serialize_session(db_session: Session, session_record: AssessmentSession) -> dict[str, Any]:
    scale_loader = get_scale_loader()
    results = db_session.scalars(
        select(AssessmentResult)
        .where(AssessmentResult.session_id == session_record.id)
        .order_by(AssessmentResult.completed_at.asc())
    ).all()
    answers = db_session.scalars(
        select(AssessmentAnswer)
        .where(AssessmentAnswer.session_id == session_record.id)
        .order_by(AssessmentAnswer.scale_slug.asc(), AssessmentAnswer.item_index.asc())
    ).all()
    answers_by_scale: dict[str, list[AssessmentAnswer]] = {}
    for answer in answers:
        answers_by_scale.setdefault(answer.scale_slug, []).append(answer)

    turn_context = _build_current_turn_context(session_record)
    current_item = turn_context["current_item"] if turn_context else None

    try:
        serialized_results = [
            _serialize_result(
                scale_loader.load_scale(result_record.scale_slug),
                answers_by_scale.get(result_record.scale_slug, []),
                result_record,
            )
            for result_record in results
        ]
    except ScaleLoaderError as exc:
        raise _translate_loader_error(exc) from exc
    except ScaleScoringError as exc:
        raise _translate_scoring_error(exc) from exc

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
        "current_turn_id": turn_context["turn_id"] if turn_context else None,
        "scale_handoff_payload": _ensure_json_dict(session_record.scale_handoff_payload),
        "capture_context": _ensure_json_dict(session_record.capture_context),
        "aggregate_payload": _ensure_json_dict(session_record.aggregate_payload),
        "multimodal_live": _ensure_json_dict(session_record.multimodal_live_payload),
        "multimodal_live_updated_at": (
            session_record.multimodal_live_updated_at.isoformat()
            if session_record.multimodal_live_updated_at
            else None
        ),
        "results": serialized_results,
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
    try:
        scoring = compute_scale_scoring(scale_definition, resolved_answers)
    except ScaleScoringError as exc:
        raise _translate_scoring_error(exc) from exc
    now = _now()

    existing_result = db_session.scalar(
        select(AssessmentResult).where(
            AssessmentResult.session_id == session_record.id,
            AssessmentResult.scale_slug == scale_definition.slug,
        )
    )
    if existing_result:
        result_record = existing_result
        result_record.raw_score = scoring.raw_score
        result_record.derived_score = scoring.derived_score
        result_record.interpretation_level = scoring.interpretation_level
        result_record.interpretation_label = scoring.interpretation_label
        result_record.risk_flags = scoring.risk_flags
        result_record.completed_at = now
        result_record.updated_at = now
        return result_record

    result_record = AssessmentResult(
        id=str(uuid.uuid4()),
        session_id=session_record.id,
        scale_slug=scale_definition.slug,
        raw_score=scoring.raw_score,
        derived_score=scoring.derived_score,
        interpretation_level=scoring.interpretation_level,
        interpretation_label=scoring.interpretation_label,
        risk_flags=scoring.risk_flags,
        completed_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(result_record)
    return result_record


def _sanitize_scale_detail_question_text(
    scale_slug: str,
    item_index: int,
    question_text: str,
) -> str:
    normalized_text = str(question_text or "").strip()
    if item_index != 1 or not normalized_text:
        return normalized_text

    for prefix in DETAIL_QUESTION_PREFIXES.get(scale_slug, ()):
        if normalized_text.startswith(prefix):
            return normalized_text[len(prefix):].strip()

    return normalized_text


def _build_aggregate_payload(db_session: Session, session_record: AssessmentSession) -> dict[str, Any]:
    scale_loader = get_scale_loader()
    results = db_session.scalars(
        select(AssessmentResult)
        .where(AssessmentResult.session_id == session_record.id)
        .order_by(AssessmentResult.completed_at.asc())
    ).all()
    answers = db_session.scalars(
        select(AssessmentAnswer)
        .where(AssessmentAnswer.session_id == session_record.id)
        .order_by(AssessmentAnswer.scale_slug.asc(), AssessmentAnswer.item_index.asc())
    ).all()
    answers_by_scale: dict[str, list[AssessmentAnswer]] = {}
    for answer in answers:
        answers_by_scale.setdefault(answer.scale_slug, []).append(answer)
    try:
        serialized_results = [
            _serialize_result(
                scale_loader.load_scale(result_record.scale_slug),
                answers_by_scale.get(result_record.scale_slug, []),
                result_record,
            )
            for result_record in results
        ]
    except ScaleLoaderError as exc:
        raise _translate_loader_error(exc) from exc
    except ScaleScoringError as exc:
        raise _translate_scoring_error(exc) from exc
    scale_result_map = {
        result_payload["scale_slug"]: result_payload for result_payload in serialized_results
    }
    normalized_scores = {
        result_payload["scale_slug"]: result_payload.get("normalized_score")
        for result_payload in serialized_results
    }
    flattened_risk_flags: list[dict[str, Any]] = []
    for result_payload in serialized_results:
        for flag_payload in result_payload.get("risk_flags") or []:
            flattened_risk_flags.append(
                {
                    "scale_slug": result_payload["scale_slug"],
                    **dict(flag_payload),
                }
            )
    capture_context = _ensure_json_dict(session_record.capture_context)
    return {
        "assessment_session_id": session_record.id,
        "encounter_session_id": session_record.encounter_session_id,
        "source_consultation_flow_run_id": (
            session_record.source_consultation_flow_run_id
        ),
        "scale_count": len(results),
        "scale_results": serialized_results,
        "scale_result_map": scale_result_map,
        "normalized_scores": normalized_scores,
        "flattened_risk_flags": flattened_risk_flags,
        "eeg_turn_results": list(capture_context.get("eeg_turn_results") or []),
        "source_handoff": _ensure_json_dict(session_record.scale_handoff_payload),
    }


def _ensure_multimodal_session_binding(
    session_record: AssessmentSession,
    *,
    acting_user_id: str,
) -> str:
    multimodal_session_id = ensure_multimodal_session_binding(
        session_record,
        acting_user_id=acting_user_id,
    )
    session_record.updated_at = _now()
    return str(multimodal_session_id)


def _refresh_multimodal_live_snapshot(
    session_record: AssessmentSession,
    *,
    acting_user_id: str,
) -> dict[str, Any]:
    _ensure_multimodal_session_binding(
        session_record,
        acting_user_id=acting_user_id,
    )
    live_data = refresh_multimodal_live_snapshot(
        session_record,
        acting_user_id=acting_user_id,
    )
    session_record.multimodal_live_payload = live_data
    session_record.multimodal_live_updated_at = _now()
    return live_data


def _start_eeg_turn_best_effort(
    *,
    multimodal_session_id: str | None,
    session_record: AssessmentSession,
    acting_user_id: str,
) -> None:
    turn_context = _build_current_turn_context(session_record)
    if not multimodal_session_id or turn_context is None:
        return
    try:
        start_upstream_eeg_turn(
            multimodal_session_id=multimodal_session_id,
            turn_id=str(turn_context["turn_id"]),
            flow_run_id=session_record.id,
            stage_id=ASSESSMENT_STAGE_ID,
            question_key=str(turn_context["question_key"]),
            acting_user_id=acting_user_id,
        )
    except Exception:
        return


def _finish_eeg_turn_best_effort(
    *,
    multimodal_session_id: str | None,
    turn_id: str | None,
    acting_user_id: str,
    reason: str,
) -> None:
    if not multimodal_session_id or not turn_id:
        return
    try:
        finish_upstream_eeg_turn(
            multimodal_session_id=multimodal_session_id,
            turn_id=turn_id,
            reason=reason,
            acting_user_id=acting_user_id,
        )
    except Exception:
        return


def _load_eeg_turn_results_best_effort(
    *,
    multimodal_session_id: str | None,
    turn_id: str | None,
    acting_user_id: str,
) -> list[dict[str, Any]]:
    if not multimodal_session_id or not turn_id:
        return []
    try:
        data = _extract_upstream_data(
            fetch_upstream_eeg_turn_results(
                multimodal_session_id=multimodal_session_id,
                turn_id=turn_id,
                acting_user_id=acting_user_id,
            ),
            error_code=5026,
        )
    except Exception:
        return []

    results = data.get("results") or []
    normalized: list[dict[str, Any]] = []
    for item in results:
        if isinstance(item, dict):
            normalized.append(dict(item))
    return normalized


def _append_eeg_turn_results(
    session_record: AssessmentSession,
    *,
    scale_definition: ScaleDefinition,
    current_item: dict[str, Any],
    turn_id: str,
    window_results: list[dict[str, Any]],
) -> None:
    capture_context = _ensure_json_dict(session_record.capture_context)
    existing_entries = [
        entry
        for entry in list(capture_context.get("eeg_turn_results") or [])
        if isinstance(entry, dict) and entry.get("turn_id") != turn_id
    ]
    copied_results = [dict(item) for item in window_results if isinstance(item, dict)]
    existing_entries.append(
        {
            "turn_id": turn_id,
            "scale_slug": scale_definition.slug,
            "item_id": current_item["item_id"],
            "item_index": current_item["index"],
            "question_key": _build_assessment_question_key(
                scale_definition.slug,
                str(current_item["item_id"]),
            ),
            "result_count": len(copied_results),
            "latest_result": dict(copied_results[-1]) if copied_results else None,
            "window_results": copied_results,
            "captured_at": _now().isoformat(),
        }
    )
    capture_context["eeg_turn_results"] = existing_entries
    session_record.capture_context = capture_context
    session_record.updated_at = _now()


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
    assessment_session_id = str(uuid.uuid4())

    with get_db_session() as db_session:
        _validate_source_consultation_handoff(
            db_session,
            payload,
            acting_user_id=acting_user_id,
        )
        session_record = AssessmentSession(
            id=assessment_session_id,
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
            multimodal_live_payload={},
            multimodal_live_updated_at=None,
            created_at=now,
            updated_at=now,
            started_at=now,
        )
        db_session.add(session_record)
        db_session.flush()
        multimodal_session_id = _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        _start_eeg_turn_best_effort(
            multimodal_session_id=multimodal_session_id,
            session_record=session_record,
            acting_user_id=acting_user_id,
        )
        db_session.flush()
        return _serialize_session(db_session, session_record)


def get_assessment_session(session_id: str, acting_user_id: str | None) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        _require_session_owner(session_record, acting_user_id)
        multimodal_session_id = _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        if session_record.status != "completed":
            _start_eeg_turn_best_effort(
                multimodal_session_id=multimodal_session_id,
                session_record=session_record,
                acting_user_id=acting_user_id,
            )
        return _serialize_session(db_session, session_record)


def get_assessment_scale_detail(
    session_id: str,
    scale_slug: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        _require_session_owner(session_record, acting_user_id)
        return _serialize_scale_detail(
            db_session,
            session_record,
            scale_slug=scale_slug,
        )


def get_assessment_multimodal_live(
    session_id: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        _require_session_owner(session_record, acting_user_id)
        multimodal_session_id = _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        if session_record.status != "completed":
            _start_eeg_turn_best_effort(
                multimodal_session_id=multimodal_session_id,
                session_record=session_record,
                acting_user_id=acting_user_id,
            )
        return _refresh_multimodal_live_snapshot(
            session_record,
            acting_user_id=acting_user_id,
        )


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

        multimodal_session_id = _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        turn_context = _build_current_turn_context(session_record)
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
        question_key = payload.question_key or _build_assessment_question_key(
            scale_definition.slug,
            int(current_item["index"]),
        )
        raw_input = payload.raw_input or payload.transcript_text
        multimodal_session_id = (
            payload.multimodal_session_id
            or bound_multimodal_session_id
            or None
        )
        resolved_turn_id = payload.turn_id or (str(turn_context["turn_id"]) if turn_context else None) or question_key
        answer_record = AssessmentAnswer(
            id=str(uuid.uuid4()),
            session_id=session_record.id,
            scale_slug=scale_definition.slug,
            item_id=current_item["item_id"],
            item_index=int(current_item.get("index") or (session_record.current_item_index + 1)),
            question_key=question_key,
            turn_id=resolved_turn_id,
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
            turn_id=resolved_turn_id,
            acting_user_id=acting_user_id,
        )
        accepted_answer = _serialize_accepted_answer(
            answer_record,
            normalization_source=normalized_answer.normalization_source,
        )
        if turn_bundle is not None:
            accepted_answer["turn_bundle"] = turn_bundle

        _finish_eeg_turn_best_effort(
            multimodal_session_id=multimodal_session_id,
            turn_id=resolved_turn_id,
            acting_user_id=acting_user_id,
            reason="assessment_item_submitted",
        )
        eeg_window_results = _load_eeg_turn_results_best_effort(
            multimodal_session_id=multimodal_session_id,
            turn_id=resolved_turn_id,
            acting_user_id=acting_user_id,
        )
        if resolved_turn_id:
            _append_eeg_turn_results(
                session_record,
                scale_definition=scale_definition,
                current_item=current_item,
                turn_id=resolved_turn_id,
                window_results=eeg_window_results,
            )

        session_record.updated_at = _now()
        next_item_index = session_record.current_item_index + 1
        if next_item_index < len(scale_definition.items):
            session_record.current_item_index = next_item_index
            db_session.flush()
            _start_eeg_turn_best_effort(
                multimodal_session_id=multimodal_session_id,
                session_record=session_record,
                acting_user_id=acting_user_id,
            )
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
            _start_eeg_turn_best_effort(
                multimodal_session_id=multimodal_session_id,
                session_record=session_record,
                acting_user_id=acting_user_id,
            )
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


def stream_assessment_multimodal_live(
    session_id: str,
    acting_user_id: str | None,
):
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        _require_session_owner(session_record, acting_user_id)
        multimodal_session_id = _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        if session_record.status != "completed":
            _start_eeg_turn_best_effort(
                multimodal_session_id=multimodal_session_id,
                session_record=session_record,
                acting_user_id=acting_user_id,
            )
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
