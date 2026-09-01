from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import re
import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.clients.risk_client import create_risk_evaluation as create_risk_evaluation_upstream
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
# Spoken answers from ASR are much more varied than the four labels shown on
# screen. Keep the vocabulary grouped by scale/score so matching remains
# deterministic and auditable. There are more than 300 phrase entries here;
# score-like and ordinal expressions are additionally handled by the generic
# numeric/position rules below.
FOUR_LEVEL_FREQUENCY_SYNONYMS: dict[int, tuple[str, ...]] = {
    1: (
        "没有或很少时间", "没有", "基本没有", "几乎没有", "很少", "很少时间",
        "无此情况", "从不", "从未", "不怎么", "不太有", "不常", "极少",
        "极少时间", "仅有很少时间", "仅极少数时候", "几乎不", "基本不", "不曾",
        "未出现", "很难得", "难得", "罕见", "少之又少", "出现得很少", "发生得很少",
        "只有一点点", "几乎没出现", "没有多少", "很少发生", "很少会有", "基本没发生",
    ),
    2: (
        "小部分时间", "少部分时间", "一小部分时间", "少量时间", "少数时间",
        "有一些时候", "有时", "有时候", "偶尔", "偶尔会", "偶尔有", "偶发", "间或",
        "时不时", "不时", "偶然", "少许", "略有", "轻微", "不多", "不太多",
        "短时间", "短暂时候", "少部分日子", "个别时候", "零星出现", "偶有", "偶见",
        "有一点", "一点点", "少量出现", "偶尔出现",
    ),
    3: (
        "相当多时间", "很多时候", "较多时间", "比较多时间", "经常", "常常", "时常",
        "往往", "频繁", "较为频繁", "比较频繁", "经常出现", "常有", "多有",
        "不少时间", "相当一部分时间", "一半左右", "一半时间", "半数时间", "挺多时候",
        "出现得比较多", "发生得比较多", "多数时间", "多数时候", "经常会有", "常常会有",
        "反复出现", "经常发生", "频率较高", "比较常见", "不少时候", "较常发生",
    ),
    4: (
        "绝大部分或全部时间", "绝大部分时间", "全部时间", "大部分时间", "几乎总是",
        "一直都是", "总是", "始终", "一直", "每时每刻", "全程", "全部时候",
        "几乎所有时间", "几乎一直", "基本一直", "大多数时候", "大半时间", "长时间持续",
        "一整天", "整天", "全天", "无时无刻", "时刻如此", "总会", "一贯如此",
        "持续存在", "从早到晚", "几乎每次", "常态", "大部分日子", "绝大多数日子",
        "一直存在", "几乎整天",
    ),
}

VOICE_OPTION_SYNONYMS: dict[str, dict[int, tuple[str, ...]]] = {
    "phq9": {
        0: (
            "完全没有", "完全没", "从来没有", "从未有过", "一次也没有", "一点没有",
            "一点都没有", "没有过", "没有出现", "没发生过", "不曾有过", "从不", "从未",
            "零次", "0次", "零天", "0天", "没有任何一天", "一天也没有", "这两周都没有",
            "最近两周没有", "整整两周没有", "基本没有", "几乎没有", "没感觉到", "不存在",
            "没这回事", "没有这种情况", "无此情况", "没有", "完全不存在", "从没出现过",
        ),
        1: (
            "几天", "有几天", "只有几天", "就几天", "一两天", "两三天", "一到两天",
            "两到三天", "一两次", "两三次", "偶尔", "偶尔会", "偶尔有", "有时候", "有时",
            "时不时", "间或", "间歇性", "偶发", "不常", "不太经常", "很少几天", "少数几天",
            "个别几天", "大概两天", "大约三天", "一周不到", "偶尔出现", "零星几天",
            "偶然", "发生过几天", "只有一两天",
        ),
        2: (
            "一半以上", "一半以上的日子", "超过一半", "超过半数", "大半时间", "大半日子",
            "很多天", "比较多", "较多", "不少天", "一半时间", "半数日子", "一周多",
            "一周左右", "大概一周", "六七天", "七八天", "八九天", "九十天", "十来天",
            "十天左右", "十一天左右", "频率过半", "多数日子", "多半时间", "有一半时间",
            "相对频繁", "比较频繁", "出现得比较多", "发生得比较多", "超过七天", "大约十天",
        ),
        3: (
            "几乎每天", "几乎天天", "每天", "天天", "基本每天", "几乎每一天", "差不多每天",
            "每日", "每一日", "天天都有", "一直都", "一直有", "持续每天", "连着每天",
            "整整两周", "天天如此", "十三四天", "十二三天", "十四天", "两周每天", "两周都这样",
            "基本天天", "几乎全程", "近乎每天", "每日都有", "每天都会", "一天不落", "无一天例外",
            "一直如此", "连续十四天", "天天发生", "每天发生",
        ),
    },
    "sds": FOUR_LEVEL_FREQUENCY_SYNONYMS,
    "sas": FOUR_LEVEL_FREQUENCY_SYNONYMS,
    "social-function": {
        0: (
            "无缺陷", "没有缺陷", "无明显缺陷", "完全正常", "功能正常", "社会功能正常",
            "不受影响", "没有影响", "无障碍", "无问题", "无困难", "没有困难", "一切正常",
            "表现正常", "适应良好", "能正常工作", "能正常学习", "能正常社交", "交流正常",
            "生活正常", "不影响生活", "没有受损", "无功能受损", "完好", "无异常", "没有障碍",
            "功能完好", "社交没问题", "工作没问题", "学习没问题", "无任何影响", "没有功能问题",
        ),
        1: (
            "有些缺陷", "轻微缺陷", "轻度缺陷", "一点缺陷", "有一点影响", "略有影响",
            "少许影响", "有些影响", "轻微受损", "轻度受损", "不太严重", "偶有困难", "有点困难",
            "略有困难", "有些困难", "个别方面受影响", "部分受影响", "小问题", "有点问题",
            "轻微障碍", "轻度障碍", "基本能应对", "尚可应对", "影响不大", "有所下降",
            "有一点受损", "稍有缺陷", "略微受影响", "问题不大", "轻微影响生活", "有些不适应",
        ),
        2: (
            "严重缺陷", "明显缺陷", "重度缺陷", "严重受损", "明显受损", "功能严重受损",
            "影响很大", "严重影响", "很大困难", "明显困难", "难以应对", "基本不能应对",
            "社交困难严重", "工作受影响严重", "学习受影响严重", "生活受影响严重", "明显障碍",
            "重度障碍", "功能下降明显", "严重问题", "很不适应", "无法正常社交", "无法正常工作",
            "无法正常学习", "需要大量帮助", "问题很严重", "受影响很大", "功能明显下降", "难以正常生活",
            "严重影响工作", "严重影响社交",
        ),
        9: (
            "不适合", "不适用", "不适宜", "不适于评价", "无法判断", "不能判断", "难以判断",
            "不好判断", "不便回答", "不方便回答", "不想回答", "拒绝回答", "没有相关场景",
            "没有工作", "不在上学", "无社交场景", "题目不适用", "情况不适用", "不涉及", "不相关",
            "无法作答", "不确定是否适用", "暂不适用", "无从判断", "不予评价", "不方便作答",
            "没有这个情况", "目前不适用", "不适合回答", "无法评价", "跳过此题", "不作评价",
        ),
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


def _normalize_active_scale_slugs(
    candidate: Any,
    *,
    allow_empty: bool,
    empty_message: str,
    unsupported_message_prefix: str = "unsupported scale slug",
) -> list[str]:
    loader = get_scale_loader()
    active_slugs = loader.active_scale_slugs

    raw_slugs = candidate if isinstance(candidate, (list, tuple, set)) else []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_slug in raw_slugs:
        slug = str(raw_slug or "").strip()
        if not slug:
            continue
        if slug not in active_slugs:
            raise AssessmentServiceError(
                f"{unsupported_message_prefix}: {slug}",
                code=4002,
            )
        if slug in seen:
            continue
        seen.add(slug)
        normalized.append(slug)

    if not allow_empty and not normalized:
        raise AssessmentServiceError(empty_message, code=4003)
    return normalized


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    candidate = (
        payload.selected_scales
        or payload.scale_handoff_payload.get("required_scales")
        or active_slugs
    )
    return _normalize_active_scale_slugs(
        candidate,
        allow_empty=False,
        empty_message="no active scales selected",
    )


def _normalize_required_scales(
    payload: CreateAssessmentSessionRequest,
) -> list[str]:
    # Distinguish "explicitly passed []" from "field omitted" so callers can
    # intentionally clear required scales without falling back to handoff data.
    if "required_scales" in payload.model_fields_set:
        candidate = payload.required_scales
    else:
        candidate = payload.scale_handoff_payload.get("required_scales") or []
    return _normalize_active_scale_slugs(
        candidate,
        allow_empty=True,
        empty_message="",
        unsupported_message_prefix="unsupported required scale slug",
    )


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
        db_session.flush()
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
    db_session.flush()
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
        "multimodal_session_id": session_record.multimodal_session_id,
        "status": session_record.status,
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


def _extract_primary_label(feature_payload: dict[str, Any]) -> str | None:
    primary_label = str(feature_payload.get("primary_label") or "").strip()
    if primary_label:
        return primary_label

    for item in list(feature_payload.get("top_3_labels") or []):
        if not isinstance(item, dict):
            continue
        candidate = str(item.get("label") or "").strip()
        if candidate:
            return candidate
    return None


def _merge_label_counts(
    counter: Counter[str],
    *,
    feature_payload: dict[str, Any],
) -> tuple[int, int]:
    label_distribution = feature_payload.get("label_distribution")
    if isinstance(label_distribution, list):
        distribution_total = 0.0
        for row in label_distribution:
            if not isinstance(row, dict):
                continue
            label = str(row.get("label") or "").strip()
            count = _safe_float(row.get("count"))
            if not label or count is None or count <= 0:
                continue
            counter[label] += count
            distribution_total += count
        if distribution_total > 0:
            sample_count = int(round(_safe_float(feature_payload.get("sample_count")) or distribution_total))
            valid_sample_count = int(
                round(_safe_float(feature_payload.get("valid_sample_count")) or distribution_total)
            )
            return sample_count, valid_sample_count

    primary_label = _extract_primary_label(feature_payload)
    if not primary_label:
        return 0, 0
    counter[primary_label] += 1.0
    return 1, 1


def _build_label_distribution_summary(
    counter: Counter[str],
    *,
    sample_count: int,
    valid_sample_count: int,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total_count = float(sum(counter.values()))
    if valid_sample_count <= 0 and total_count > 0:
        valid_sample_count = int(round(total_count))
    if sample_count <= 0 and valid_sample_count > 0:
        sample_count = valid_sample_count

    label_distribution = [
        {
            "label": label,
            "count": int(round(count)) if abs(count - round(count)) < 1e-6 else round(count, 4),
            "ratio": round((count / total_count), 4) if total_count > 0 else 0.0,
        }
        for label, count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    primary_label = label_distribution[0]["label"] if label_distribution else None
    primary_ratio = label_distribution[0]["ratio"] if label_distribution else None

    payload = {
        "primary_label": primary_label,
        "primary_score": primary_ratio,
        "primary_ratio": primary_ratio,
        "sample_count": sample_count,
        "valid_sample_count": valid_sample_count,
        "label_distribution": label_distribution,
    }
    if extra_payload:
        payload.update(extra_payload)
    return payload


def _summarize_turn_feature_sections(
    sections: list[dict[str, Any]],
    *,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    sample_count = 0
    valid_sample_count = 0
    for section in sections:
        current_sample_count, current_valid_count = _merge_label_counts(
            counter,
            feature_payload=section,
        )
        sample_count += current_sample_count
        valid_sample_count += current_valid_count
    return _build_label_distribution_summary(
        counter,
        sample_count=sample_count,
        valid_sample_count=valid_sample_count,
        extra_payload=extra_payload,
    )


def _load_turn_multimodal_bundle_best_effort(
    session_record: AssessmentSession,
    *,
    turn_id: str,
    acting_user_id: str,
) -> dict[str, Any] | None:
    try:
        payload = fetch_assessment_turn_multimodal_bundle(
            session_record,
            turn_id=turn_id,
            acting_user_id=acting_user_id,
        )
    except Exception:
        return None
    return dict(payload) if isinstance(payload, dict) else None


def _build_eeg_feature_summary(session_record: AssessmentSession) -> dict[str, Any]:
    capture_context = _ensure_json_dict(session_record.capture_context)
    counter: Counter[str] = Counter()
    sample_count = 0
    valid_sample_count = 0
    latest_result: dict[str, Any] | None = None

    for entry in list(capture_context.get("eeg_turn_results") or []):
        if not isinstance(entry, dict):
            continue
        window_results = [
            dict(item)
            for item in list(entry.get("window_results") or [])
            if isinstance(item, dict)
        ]
        if not window_results and isinstance(entry.get("latest_result"), dict):
            window_results = [dict(entry["latest_result"])]

        for window_result in window_results:
            label = _extract_primary_label(window_result)
            sample_count += 1
            latest_result = window_result
            if not label:
                continue
            counter[label] += 1.0
            valid_sample_count += 1

    extra_payload = {
        "latest_result": dict(latest_result) if isinstance(latest_result, dict) else None,
        "result_count": sample_count,
    }
    return _build_label_distribution_summary(
        counter,
        sample_count=sample_count,
        valid_sample_count=valid_sample_count,
        extra_payload=extra_payload,
    )


def _build_multimodal_feature_bundle(
    db_session: Session,
    session_record: AssessmentSession,
    *,
    acting_user_id: str,
) -> dict[str, Any]:
    answers = db_session.scalars(
        select(AssessmentAnswer)
        .where(AssessmentAnswer.session_id == session_record.id)
        .order_by(AssessmentAnswer.created_at.asc(), AssessmentAnswer.item_index.asc())
    ).all()
    turn_ids: list[str] = []
    seen_turn_ids: set[str] = set()
    for answer in answers:
        turn_id = str(answer.turn_id or "").strip()
        if not turn_id or turn_id in seen_turn_ids:
            continue
        seen_turn_ids.add(turn_id)
        turn_ids.append(turn_id)

    turn_bundles: list[dict[str, Any]] = []
    for turn_id in turn_ids:
        bundle = _load_turn_multimodal_bundle_best_effort(
            session_record,
            turn_id=turn_id,
            acting_user_id=acting_user_id,
        )
        if bundle:
            turn_bundles.append(bundle)

    speech_sections: list[dict[str, Any]] = []
    text_sections: list[dict[str, Any]] = []
    face_sections: list[dict[str, Any]] = []
    pose_sections: list[dict[str, Any]] = []
    text_negative_terms: set[str] = set()

    for bundle in turn_bundles:
        speech_features = bundle.get("speech_features")
        if isinstance(speech_features, dict):
            speech_sections.append(dict(speech_features))

        text_features = bundle.get("text_features")
        if isinstance(text_features, dict):
            text_sections.append(dict(text_features))
            for term in list(text_features.get("negative_terms") or []):
                normalized_term = str(term or "").strip()
                if normalized_term:
                    text_negative_terms.add(normalized_term)

        face_features = bundle.get("face_features")
        if isinstance(face_features, dict):
            face_sections.append(dict(face_features))

        pose_features = bundle.get("pose_features")
        if isinstance(pose_features, dict):
            pose_sections.append(dict(pose_features))

    return {
        "multimodal_session_id": session_record.multimodal_session_id,
        "origin_flow_type": "assessment",
        "generated_at": _now().isoformat(),
        "turn_count": len(turn_ids),
        "bundle_count": len(turn_bundles),
        "speech_features": _summarize_turn_feature_sections(
            speech_sections,
            extra_payload={"summary_type": "assessment_session"},
        ),
        "text_features": _summarize_turn_feature_sections(
            text_sections,
            extra_payload={
                "summary_type": "assessment_session",
                "negative_terms": sorted(text_negative_terms),
            },
        ),
        "face_features": _summarize_turn_feature_sections(
            face_sections,
            extra_payload={"summary_type": "assessment_session"},
        ),
        "pose_features": _summarize_turn_feature_sections(
            pose_sections,
            extra_payload={"summary_type": "assessment_session"},
        ),
        "eeg_features": _build_eeg_feature_summary(session_record),
    }


def _build_risk_summary_payload(risk_evaluation: dict[str, Any]) -> dict[str, Any]:
    result_payload = _ensure_json_dict(risk_evaluation.get("result"))
    front_display = _ensure_json_dict(result_payload.get("front_display"))
    return {
        "evaluation_id": risk_evaluation.get("evaluation_id"),
        "risk_level": risk_evaluation.get("risk_level"),
        "risk_level_label": front_display.get("risk_level_label"),
        "depression_score": risk_evaluation.get("depression_score"),
        "depression_severity": risk_evaluation.get("depression_severity"),
        "depression_severity_label": result_payload.get("depression_severity_label"),
        "requires_human_review": risk_evaluation.get("requires_human_review"),
        "front_display": front_display,
        "risk_explanation": _ensure_json_dict(result_payload.get("risk_explanation")),
        "referral_recommendations": list(result_payload.get("referral_recommendations") or []),
        "lifestyle_suggestions": list(result_payload.get("lifestyle_suggestions") or []),
    }


def _create_final_risk_evaluation_best_effort(
    session_record: AssessmentSession,
    *,
    acting_user_id: str,
    assessment_aggregate_payload: dict[str, Any],
    multimodal_feature_bundle: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        upstream = create_risk_evaluation_upstream(
            payload={
                "user_id": session_record.user_id,
                "encounter_session_id": session_record.encounter_session_id,
                "consultation_session_id": session_record.source_consultation_flow_run_id,
                "assessment_session_id": session_record.id,
                "multimodal_session_id": session_record.multimodal_session_id,
                "assessment_aggregate_payload": assessment_aggregate_payload,
                "multimodal_feature_bundle": multimodal_feature_bundle,
            },
            acting_user_id=acting_user_id,
        )
    except AssessmentServiceError as exc:
        return None, {
            "code": exc.code,
            "message": exc.message,
            "status_code": exc.status_code,
        }
    except Exception as exc:
        return None, {
            "code": 5028,
            "message": str(exc) or "risk evaluation failed",
            "status_code": 502,
        }

    status_code = int(upstream.get("status") or 500)
    payload = upstream.get("payload") or {}
    if status_code >= 400:
        return None, {
            "code": int(payload.get("code") or 5028),
            "message": str(payload.get("message") or "risk service request failed"),
            "status_code": status_code,
        }

    data = payload.get("data") or {}
    if not isinstance(data, dict):
        return None, {
            "code": 5028,
            "message": "risk service returned invalid payload",
            "status_code": 502,
        }

    risk_evaluation = data.get("risk_evaluation")
    if not isinstance(risk_evaluation, dict):
        return None, {
            "code": 5028,
            "message": "risk service returned invalid payload",
            "status_code": 502,
        }
    return dict(risk_evaluation), None


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
                int(current_item["index"]),
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
    required_scales = _normalize_required_scales(payload)
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
            required_scales=required_scales,
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
        aggregate_payload = _build_aggregate_payload(db_session, session_record)
        multimodal_feature_bundle = _build_multimodal_feature_bundle(
            db_session,
            session_record,
            acting_user_id=acting_user_id,
        )
        aggregate_payload["multimodal_feature_bundle"] = multimodal_feature_bundle
        risk_evaluation, risk_error = _create_final_risk_evaluation_best_effort(
            session_record,
            acting_user_id=acting_user_id,
            assessment_aggregate_payload=aggregate_payload,
            multimodal_feature_bundle=multimodal_feature_bundle,
        )
        if risk_evaluation:
            aggregate_payload["risk_evaluation_id"] = risk_evaluation.get("evaluation_id")
            aggregate_payload["risk_evaluation"] = risk_evaluation
            aggregate_payload["risk_summary"] = _build_risk_summary_payload(
                risk_evaluation
            )
        if risk_error:
            aggregate_payload["risk_evaluation_error"] = risk_error
        session_record.aggregate_payload = aggregate_payload
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
