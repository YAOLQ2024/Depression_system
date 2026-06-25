from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.clients.assessment_client import get_assessment_session as fetch_assessment_session_upstream
from app.clients.consultation_client import get_consultation_session as fetch_consultation_session_upstream
from app.clients.multimodal_client import get_multimodal_live as fetch_multimodal_live_upstream
from app.config import get_settings
from app.database import get_db_session
from app.models import RiskEvaluation, RiskTrigger
from app.schemas.risk import CreateRiskEvaluationRequest, OverrideRiskEvaluationRequest
from app.services.risk_resources import (
    RiskResourceError,
    load_intervention_catalog,
    load_risk_rule_set,
)


class RiskServiceError(Exception):
    def __init__(self, message: str, code: int, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class TriggerDecision:
    key: str
    source: str
    effect: str
    evidence_summary: str | None
    evidence_payload: dict[str, Any]


RISK_ORDER: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "urgent": 3,
}
DEFAULT_SCALE_WEIGHTS: dict[str, float] = {
    "phq9": 0.40,
    "sds": 0.30,
    "sas": 0.15,
    "social-function": 0.15,
}
DEFAULT_MULTIMODAL_WEIGHTS: dict[str, float] = {
    "eeg": 0.20,
    "text": 0.20,
    "speech": 0.20,
    "face": 0.30,
    "pose": 0.10,
}
DEFAULT_DEPRESSION_SEVERITY_BANDS: list[dict[str, Any]] = [
    {"min": 0.0, "max": 24.99, "level": "minimal", "label": "无或极轻度抑郁倾向"},
    {"min": 25.0, "max": 49.99, "level": "mild", "label": "轻度抑郁倾向"},
    {"min": 50.0, "max": 69.99, "level": "moderate", "label": "中度抑郁倾向"},
    {
        "min": 70.0,
        "max": 84.99,
        "level": "moderately_severe",
        "label": "中重度抑郁倾向",
    },
    {"min": 85.0, "max": 100.0, "level": "severe", "label": "重度抑郁倾向"},
]
DEFAULT_DEPRESSION_RISK_MAPPING: dict[str, str] = {
    "minimal": "low",
    "mild": "low",
    "moderate": "medium",
    "moderately_severe": "high",
    "severe": "high",
}
DEFAULT_RECOMMENDATION_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "referral": {
        "low": ["当前未见明确急性安全风险，如症状持续或加重，建议尽快完成精神心理专科评估。"],
        "medium": ["建议近期预约精神科或心理科门诊，结合量表结果与临床访谈做进一步评估。"],
        "high": ["建议尽快由精神科或心理危机干预团队进一步评估，并通知家属或可信支持者陪同。"],
        "urgent": ["建议立即停止普通流程，尽快转入急诊或危机干预通道，并安排现场或家属陪护。"],
    },
    "lifestyle": {
        "low": [
            "保持规律作息，避免连续熬夜和长期独处。",
            "记录近一周情绪、睡眠和食欲变化，便于后续复诊时对照。",
        ],
        "medium": [
            "先保证睡眠与进食节律，减少明显加重情绪波动的刺激因素。",
            "主动联系家人、朋友或老师，建立稳定支持联系。",
        ],
        "high": [
            "尽量避免独处，优先确保身边有可联系、可到场的支持者。",
            "暂时移除可能用于自伤的危险物品，并减少高压情境暴露。",
        ],
        "urgent": [
            "立即寻求线下陪伴与医疗支持，不建议单独停留。",
            "在专业人员接手前，优先保障环境安全与持续陪护。",
        ],
    },
}
DEFAULT_INTERVENTION_MAPPING: dict[str, dict[str, Any]] = {
    "low": {"intensity": "low", "allow_auto_intervention": True},
    "medium": {"intensity": "medium", "allow_auto_intervention": True},
    "high": {"intensity": "high", "allow_auto_intervention": False},
    "urgent": {"intensity": "high", "allow_auto_intervention": False},
}
DEFAULT_NEGATIVE_LABEL_SETS: dict[str, set[str]] = {
    "eeg": {"negative", "娑堟瀬"},
    "text": {"negative", "消极", "悲伤", "抑郁", "焦虑"},
    "speech": {"sad", "ang", "悲伤", "难过", "愤怒"},
    "face": {"sad", "angry", "disgust", "fear", "悲伤", "难过", "愤怒", "厌恶", "恐惧"},
    "pose": {"sad", "ang", "悲伤", "难过", "愤怒"},
}
DEFAULT_SELF_HARM_KEYWORDS: tuple[str, ...] = (
    "自杀",
    "想死",
    "不想活了",
    "结束生命",
    "轻生",
    "自残",
    "伤害自己",
    "活着没意思",
)
SCALE_ALIASES: dict[str, str] = {
    "phq9": "phq9",
    "phq-9": "phq9",
    "sds": "sds",
    "sas": "sas",
    "social-function": "social-function",
    "social_function": "social-function",
    "socialfunction": "social-function",
}
MODALITY_ALIASES: dict[str, str] = {
    "eeg": "eeg",
    "text": "text",
    "speech": "speech",
    "audio": "speech",
    "face": "face",
    "pose": "pose",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_json_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def _ensure_json_list(value: list[Any] | None) -> list[Any]:
    return list(value or [])


def _require_acting_user_id(acting_user_id: str | None) -> str:
    normalized = str(acting_user_id or "").strip()
    if normalized:
        return normalized
    raise RiskServiceError("missing acting user id", code=4013, status_code=401)


def _translate_resource_error(exc: RiskResourceError) -> RiskServiceError:
    return RiskServiceError(str(exc), code=5001, status_code=500)


def _extract_upstream_data(upstream: dict, *, error_code: int) -> dict[str, Any]:
    if int(upstream.get("status") or 500) >= 400:
        payload = upstream.get("payload") or {}
        raise RiskServiceError(
            str(payload.get("message") or "upstream service request failed"),
            code=int(payload.get("code") or error_code),
            status_code=int(upstream.get("status") or 502),
        )
    payload = upstream.get("payload") or {}
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        raise RiskServiceError(
            "upstream service returned invalid payload",
            code=error_code,
            status_code=502,
        )
    return data


def _normalize_identifier(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _normalize_search_text(value: Any) -> str:
    return "".join(str(value or "").lower().split())


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _risk_label(risk_level: str) -> str:
    return {
        "low": "低风险",
        "medium": "中风险",
        "high": "高风险",
        "urgent": "紧急风险",
    }.get(risk_level, risk_level)


def _canonical_scale_slug(slug: str | None) -> str | None:
    normalized = str(slug or "").strip().lower()
    if not normalized:
        return None
    return SCALE_ALIASES.get(normalized, normalized)


def _canonical_modality_name(modality: str | None) -> str | None:
    normalized = str(modality or "").strip().lower()
    if not normalized:
        return None
    return MODALITY_ALIASES.get(normalized, normalized)


def _coalesce_identifier(field_name: str, *values: str | None) -> str | None:
    normalized_values = []
    for value in values:
        normalized = _normalize_identifier(value)
        if normalized and normalized not in normalized_values:
            normalized_values.append(normalized)
    if len(normalized_values) <= 1:
        return normalized_values[0] if normalized_values else None
    raise RiskServiceError(
        f"mismatched {field_name}",
        code=4091,
        status_code=409,
    )


def _max_risk_level(*values: str | None) -> str:
    resolved = "low"
    for value in values:
        normalized = str(value or "").strip().lower() or "low"
        if RISK_ORDER.get(normalized, -1) > RISK_ORDER[resolved]:
            resolved = normalized
    return resolved


def _build_scale_result_map(scale_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result_map: dict[str, dict[str, Any]] = {}
    for result in scale_results:
        scale_slug = _canonical_scale_slug(result.get("scale_slug"))
        if not scale_slug:
            continue
        result_map[scale_slug] = dict(result)
    return result_map


def _flatten_risk_flags(scale_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for result in scale_results:
        scale_slug = _canonical_scale_slug(result.get("scale_slug"))
        for flag in _ensure_json_list(result.get("risk_flags")):
            if not isinstance(flag, dict):
                continue
            flattened.append(
                {
                    "scale_slug": scale_slug,
                    **dict(flag),
                }
            )
    return flattened


def _build_normalized_score_map(scale_results: list[dict[str, Any]]) -> dict[str, float]:
    normalized_scores: dict[str, float] = {}
    for result in scale_results:
        scale_slug = _canonical_scale_slug(result.get("scale_slug"))
        normalized_score = _safe_float(result.get("normalized_score"))
        if scale_slug and normalized_score is not None:
            normalized_scores[scale_slug] = round(normalized_score, 2)
    return normalized_scores


def _normalize_assessment_payload(
    raw_payload: dict[str, Any],
    *,
    assessment_session_id: str | None = None,
    status: str | None = None,
    source_consultation_flow_run_id: str | None = None,
    multimodal_session_id: str | None = None,
) -> dict[str, Any]:
    payload = _ensure_json_dict(raw_payload)
    scale_results = [
        dict(item)
        for item in _ensure_json_list(
            payload.get("scale_results") or payload.get("results")
        )
        if isinstance(item, dict)
    ]
    scale_result_map = payload.get("scale_result_map")
    if not isinstance(scale_result_map, dict):
        scale_result_map = _build_scale_result_map(scale_results)
    else:
        scale_result_map = {
            _canonical_scale_slug(key) or str(key): dict(value)
            for key, value in scale_result_map.items()
            if isinstance(value, dict)
        }
    normalized_scores = payload.get("normalized_scores")
    if not isinstance(normalized_scores, dict):
        normalized_scores = _build_normalized_score_map(scale_results)
    else:
        normalized_scores = {
            _canonical_scale_slug(key) or str(key): round(_safe_float(value) or 0.0, 2)
            for key, value in normalized_scores.items()
            if _safe_float(value) is not None
        }
    flattened_risk_flags = payload.get("flattened_risk_flags")
    if not isinstance(flattened_risk_flags, list):
        flattened_risk_flags = _flatten_risk_flags(scale_results)
    multimodal_feature_bundle = payload.get("multimodal_feature_bundle")
    if not isinstance(multimodal_feature_bundle, dict):
        multimodal_feature_bundle = {}
    eeg_turn_results = payload.get("eeg_turn_results")
    if not isinstance(eeg_turn_results, list):
        eeg_turn_results = []

    return {
        "assessment_session_id": _normalize_identifier(
            payload.get("assessment_session_id") or assessment_session_id
        ),
        "encounter_session_id": _normalize_identifier(payload.get("encounter_session_id")),
        "status": payload.get("status") or status,
        "source_consultation_flow_run_id": _normalize_identifier(
            payload.get("source_consultation_flow_run_id")
            or source_consultation_flow_run_id
        ),
        "multimodal_session_id": _normalize_identifier(
            payload.get("multimodal_session_id") or multimodal_session_id
        ),
        "scale_count": int(payload.get("scale_count") or len(scale_results)),
        "scale_results": scale_results,
        "scale_result_map": scale_result_map,
        "normalized_scores": normalized_scores,
        "flattened_risk_flags": [
            dict(item) for item in flattened_risk_flags if isinstance(item, dict)
        ],
        "eeg_turn_results": [
            dict(item) for item in eeg_turn_results if isinstance(item, dict)
        ],
        "multimodal_feature_bundle": dict(multimodal_feature_bundle),
        "source_handoff": _ensure_json_dict(
            payload.get("source_handoff") or payload.get("scale_handoff_payload")
        ),
    }


def _normalize_consultation_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    payload = _ensure_json_dict(raw_payload)
    handoff = _ensure_json_dict(payload.get("scale_handoff_payload"))
    return {
        "session_id": _normalize_identifier(
            payload.get("session_id") or handoff.get("session_id")
        ),
        "encounter_session_id": _normalize_identifier(payload.get("encounter_session_id")),
        "workflow_id": payload.get("workflow_id") or handoff.get("workflow_id"),
        "status": payload.get("status"),
        "multimodal_session_id": _normalize_identifier(payload.get("multimodal_session_id")),
        "chief_complaint_summary": payload.get("chief_complaint_summary")
        or handoff.get("chief_complaint_summary"),
        "chief_complaint_structured_result": _ensure_json_dict(
            payload.get("chief_complaint_structured_result")
            or handoff.get("chief_complaint_structured_result")
        ),
        "chief_complaint_stage_summary": payload.get("chief_complaint_stage_summary")
        or handoff.get("chief_complaint_stage_summary"),
        "current_history_structured_result": _ensure_json_dict(
            payload.get("current_history_structured_result")
            or handoff.get("current_history_structured_result")
        ),
        "symptom_screening_stage_summary": payload.get("symptom_screening_stage_summary")
        or handoff.get("symptom_screening_stage_summary"),
        "high_risk_screening_result": _ensure_json_dict(
            payload.get("high_risk_screening_result")
            or handoff.get("high_risk_screening_result")
        ),
        "high_risk_screening_stage_summary": payload.get("high_risk_screening_stage_summary")
        or handoff.get("high_risk_screening_stage_summary"),
        "digital_human_consultation_summary": payload.get("digital_human_consultation_summary")
        or handoff.get("digital_human_consultation_summary"),
        "scale_handoff_payload": handoff,
    }


def _normalize_multimodal_payload(
    raw_payload: dict[str, Any],
    *,
    multimodal_session_id: str | None = None,
    source_type: str,
) -> dict[str, Any]:
    payload = _ensure_json_dict(raw_payload)
    normalized = dict(payload)
    normalized["multimodal_session_id"] = _normalize_identifier(
        payload.get("multimodal_session_id")
        or payload.get("session_id")
        or multimodal_session_id
    )
    normalized["source_type"] = source_type
    return normalized


def _load_rule_set_or_raise(rule_set_id: str) -> dict[str, Any]:
    try:
        return load_risk_rule_set(rule_set_id)
    except RiskResourceError as exc:
        raise _translate_resource_error(exc) from exc


def _load_intervention_catalog_or_raise() -> dict[str, Any]:
    try:
        return load_intervention_catalog()
    except RiskResourceError as exc:
        raise _translate_resource_error(exc) from exc


def _resolve_assessment_payload(
    payload: CreateRiskEvaluationRequest,
    *,
    acting_user_id: str,
) -> tuple[dict[str, Any], str]:
    if payload.assessment_aggregate_payload:
        return (
            _normalize_assessment_payload(payload.assessment_aggregate_payload),
            "explicit_aggregate_payload",
        )

    assessment_session_id = _normalize_identifier(payload.assessment_session_id)
    if not assessment_session_id:
        return {}, "missing"

    upstream_data = _extract_upstream_data(
        fetch_assessment_session_upstream(
            assessment_session_id=assessment_session_id,
            acting_user_id=acting_user_id,
        ),
        error_code=5021,
    )
    session_payload = _ensure_json_dict(upstream_data.get("assessment_session"))
    aggregate_payload = _ensure_json_dict(session_payload.get("aggregate_payload"))
    if aggregate_payload:
        return (
            _normalize_assessment_payload(
                aggregate_payload,
                assessment_session_id=session_payload.get("session_id"),
                status=session_payload.get("status"),
                source_consultation_flow_run_id=session_payload.get(
                    "source_consultation_flow_run_id"
                ),
                multimodal_session_id=session_payload.get("multimodal_session_id"),
            ),
            "upstream_session_aggregate_payload",
        )

    return (
        _normalize_assessment_payload(
            {
                "assessment_session_id": session_payload.get("session_id"),
                "encounter_session_id": session_payload.get("encounter_session_id"),
                "status": session_payload.get("status"),
                "source_consultation_flow_run_id": session_payload.get(
                    "source_consultation_flow_run_id"
                ),
                "multimodal_session_id": session_payload.get("multimodal_session_id"),
                "scale_results": session_payload.get("results") or [],
                "scale_handoff_payload": session_payload.get("scale_handoff_payload")
                or {},
            },
            assessment_session_id=session_payload.get("session_id"),
            status=session_payload.get("status"),
            source_consultation_flow_run_id=session_payload.get(
                "source_consultation_flow_run_id"
            ),
            multimodal_session_id=session_payload.get("multimodal_session_id"),
        ),
        "upstream_session_partial_results",
    )


def _fetch_consultation_payload(
    consultation_session_id: str,
    *,
    acting_user_id: str,
) -> dict[str, Any]:
    upstream_data = _extract_upstream_data(
        fetch_consultation_session_upstream(
            consultation_session_id=consultation_session_id,
            acting_user_id=acting_user_id,
        ),
        error_code=5022,
    )
    return _normalize_consultation_payload(
        _ensure_json_dict(upstream_data.get("consultation"))
    )


def _resolve_consultation_payload(
    payload: CreateRiskEvaluationRequest,
    *,
    acting_user_id: str,
    assessment_payload: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    if payload.consultation_payload:
        return (
            _normalize_consultation_payload(payload.consultation_payload),
            "explicit_payload",
        )

    source_handoff = _ensure_json_dict(assessment_payload.get("source_handoff"))
    consultation_session_id = _coalesce_identifier(
        "consultation_session_id",
        payload.consultation_session_id,
        assessment_payload.get("source_consultation_flow_run_id"),
        source_handoff.get("session_id"),
    )
    if consultation_session_id:
        try:
            return (
                _fetch_consultation_payload(
                    consultation_session_id,
                    acting_user_id=acting_user_id,
                ),
                "upstream_session",
            )
        except RiskServiceError:
            if not source_handoff:
                raise

    if source_handoff:
        return (
            _normalize_consultation_payload(source_handoff),
            "assessment_source_handoff",
        )

    return {}, "missing"


def _resolve_multimodal_payload(
    payload: CreateRiskEvaluationRequest,
    *,
    acting_user_id: str,
    consultation_payload: dict[str, Any],
    assessment_payload: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    if payload.multimodal_feature_bundle:
        return (
            _normalize_multimodal_payload(
                payload.multimodal_feature_bundle,
                multimodal_session_id=payload.multimodal_session_id,
                source_type="explicit_bundle",
            ),
            "explicit_bundle",
        )

    assessment_bundle = _ensure_json_dict(
        assessment_payload.get("multimodal_feature_bundle")
    )
    if assessment_bundle:
        return (
            _normalize_multimodal_payload(
                assessment_bundle,
                multimodal_session_id=_coalesce_identifier(
                    "multimodal_session_id",
                    payload.multimodal_session_id,
                    assessment_bundle.get("multimodal_session_id"),
                    assessment_payload.get("multimodal_session_id"),
                    consultation_payload.get("multimodal_session_id"),
                ),
                source_type="assessment_aggregate_bundle",
            ),
            "assessment_aggregate_bundle",
        )

    multimodal_session_id = _coalesce_identifier(
        "multimodal_session_id",
        payload.multimodal_session_id,
        assessment_payload.get("multimodal_session_id"),
        consultation_payload.get("multimodal_session_id"),
    )
    if not multimodal_session_id:
        return {}, "missing"

    try:
        upstream_data = _extract_upstream_data(
            fetch_multimodal_live_upstream(
                multimodal_session_id=multimodal_session_id,
                acting_user_id=acting_user_id,
            ),
            error_code=5023,
        )
    except RiskServiceError:
        return {}, "unavailable"
    return (
        _normalize_multimodal_payload(
            {
                "multimodal_session_id": multimodal_session_id,
                "live_snapshot": upstream_data,
            },
            multimodal_session_id=multimodal_session_id,
            source_type="upstream_live_snapshot",
        ),
        "upstream_live_snapshot",
    )


def _get_rule_config(rule_set: dict[str, Any], key: str, fallback: Any) -> Any:
    value = rule_set.get(key)
    if value in (None, "", [], {}):
        return fallback
    return value


def _normalize_negative_label_sets(rule_set: dict[str, Any]) -> dict[str, set[str]]:
    raw_sets = _get_rule_config(rule_set, "negative_label_sets", {})
    if not isinstance(raw_sets, dict):
        raw_sets = {}
    normalized_sets = {key: set(value) for key, value in DEFAULT_NEGATIVE_LABEL_SETS.items()}
    for modality, labels in raw_sets.items():
        canonical = _canonical_modality_name(modality)
        if not canonical:
            continue
        normalized_sets[canonical] = {
            str(label).strip().lower()
            for label in _ensure_json_list(labels)
            if str(label).strip()
        }
    return normalized_sets


def _lookup_modality_section(container: dict[str, Any], modality: str) -> Any:
    keys = [
        modality,
        f"{modality}_features",
        f"{modality}_summary",
    ]
    if modality == "speech":
        keys.extend(["audio", "audio_features", "speech_result"])
    for key in keys:
        if key in container:
            return container.get(key)
    return None


def _resolve_multimodal_container(multimodal_payload: dict[str, Any]) -> dict[str, Any]:
    container = _ensure_json_dict(multimodal_payload.get("bundle"))
    if not container:
        container = _ensure_json_dict(multimodal_payload.get("live_snapshot"))
    if not container:
        container = _ensure_json_dict(multimodal_payload)
    return container


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clamp_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def _normalize_confidence_value(value: Any) -> float | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    if numeric > 1.0:
        numeric = numeric / 100.0
    return round(_clamp_01(numeric), 4)


def _normalize_score_value(value: Any) -> float | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    if numeric <= 1.0:
        numeric = numeric * 100.0
    return round(_clamp_100(numeric), 2)


def _extract_top_label_confidence(section: dict[str, Any]) -> float | None:
    for key in ("confidence", "primary_score", "primary_ratio", "score"):
        normalized = _normalize_confidence_value(section.get(key))
        if normalized is not None:
            return normalized

    top_labels = section.get("top_3_labels")
    if not isinstance(top_labels, list):
        return None
    for item in top_labels:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_confidence_value(item.get("score"))
        if normalized is not None:
            return normalized
    return None


def _extract_quality_ratio(value: Any) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    numeric = _safe_float(value)
    if numeric is None:
        return None
    if numeric > 1.0:
        numeric = numeric / 100.0
    return round(_clamp_01(numeric), 4)


def _extract_coverage_ratio(section: dict[str, Any]) -> float | None:
    sample_count = _safe_float(section.get("sample_count"))
    valid_sample_count = _safe_float(section.get("valid_sample_count"))
    if sample_count is None or sample_count <= 0 or valid_sample_count is None:
        return None
    return round(_clamp_01(valid_sample_count / sample_count), 4)


def _compute_quality_factor(section: dict[str, Any], *, modality: str) -> float | None:
    quality_flags = _ensure_json_dict(section.get("quality_flags"))
    if modality == "face":
        no_face_ratio = _extract_quality_ratio(
            quality_flags.get("no_face_ratio", quality_flags.get("no_face"))
        )
        blur_ratio = _extract_quality_ratio(
            quality_flags.get("blur_ratio", quality_flags.get("blur"))
        )
        low_light_ratio = _extract_quality_ratio(
            quality_flags.get("low_light_ratio", quality_flags.get("low_light"))
        )
        ratios = [item for item in (no_face_ratio, blur_ratio, low_light_ratio) if item is not None]
        if not ratios:
            return None
        penalty = (
            0.60 * (no_face_ratio or 0.0)
            + 0.25 * (blur_ratio or 0.0)
            + 0.15 * (low_light_ratio or 0.0)
        )
        return round(_clamp_01(1.0 - penalty), 4)

    if modality == "pose":
        no_pose_ratio = _extract_quality_ratio(
            quality_flags.get("no_pose_ratio", quality_flags.get("no_pose"))
        )
        body_cutoff_ratio = _extract_quality_ratio(
            quality_flags.get("body_cutoff_ratio", quality_flags.get("body_cutoff"))
        )
        motion_blur_ratio = _extract_quality_ratio(
            quality_flags.get("motion_blur_ratio", quality_flags.get("motion_blur"))
        )
        ratios = [item for item in (no_pose_ratio, body_cutoff_ratio, motion_blur_ratio) if item is not None]
        if not ratios:
            return None
        penalty = (
            0.60 * (no_pose_ratio or 0.0)
            + 0.25 * (body_cutoff_ratio or 0.0)
            + 0.15 * (motion_blur_ratio or 0.0)
        )
        return round(_clamp_01(1.0 - penalty), 4)

    return None


def _blend_confidence_components(
    weighted_components: list[tuple[str, float, float | None]],
    *,
    default_value: float = 0.5,
) -> tuple[float, dict[str, Any]]:
    weighted_sum = 0.0
    total_weight = 0.0
    used_components: dict[str, float] = {}
    for key, weight, value in weighted_components:
        if value is None:
            continue
        weighted_sum += weight * value
        total_weight += weight
        used_components[key] = round(value, 4)
    if total_weight <= 0:
        return round(default_value, 4), {
            "confidence_components": {},
            "confidence_formula": "default_fallback",
        }
    return round(weighted_sum / total_weight, 4), {
        "confidence_components": used_components,
        "confidence_formula": "weighted_average_over_available_components",
    }


def _extract_top_label_distribution_score(
    section: dict[str, Any],
    *,
    negative_labels: set[str],
) -> tuple[float | None, dict[str, Any]]:
    top_labels = section.get("top_3_labels")
    if not isinstance(top_labels, list):
        return None, {}

    negative_total = 0.0
    total_score = 0.0
    for item in top_labels:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip().lower()
        score = _safe_float(item.get("score"))
        if score is None or score < 0:
            continue
        total_score += score
        if label in negative_labels:
            negative_total += score
    if total_score <= 0:
        return None, {}
    return round(_clamp_100((negative_total / total_score) * 100.0), 2), {
        "score_source": "top_3_labels_ratio",
    }


def _extract_label_distribution_score(
    section: dict[str, Any],
    *,
    negative_labels: set[str],
) -> tuple[float | None, dict[str, Any]]:
    label_distribution = section.get("label_distribution")
    if not isinstance(label_distribution, list):
        return None, {}

    negative_total = 0.0
    total_ratio = 0.0
    total_count = 0.0
    negative_count = 0.0
    has_ratio = False
    has_count = False

    for row in label_distribution:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip().lower()
        ratio = _safe_float(row.get("ratio"))
        count = _safe_float(row.get("count"))
        if ratio is not None:
            has_ratio = True
            total_ratio += ratio
            if label in negative_labels:
                negative_total += ratio
        if count is not None:
            has_count = True
            total_count += count
            if label in negative_labels:
                negative_count += count

    if has_ratio and total_ratio > 0:
        return (
            round((negative_total / total_ratio) * 100.0, 2),
            {"score_source": "label_distribution_ratio"},
        )
    if has_count and total_count > 0:
        return (
            round((negative_count / total_count) * 100.0, 2),
            {"score_source": "label_distribution_count"},
        )
    return None, {}


def _extract_modality_score(
    multimodal_payload: dict[str, Any],
    *,
    modality: str,
    negative_labels: set[str],
) -> tuple[float | None, dict[str, Any]]:
    container = _resolve_multimodal_container(multimodal_payload)

    modality_scores = container.get("modality_scores")
    if isinstance(modality_scores, dict):
        for key in (modality, f"{modality}_score"):
            score = _normalize_score_value(modality_scores.get(key))
            if score is not None:
                return round(score, 2), {"score_source": "modality_scores"}

    direct_score = _normalize_score_value(container.get(f"{modality}_score"))
    if direct_score is not None:
        return round(direct_score, 2), {"score_source": "top_level_score"}

    section = _lookup_modality_section(container, modality)
    if isinstance(section, (int, float)):
        return round(_normalize_score_value(section) or 0.0, 2), {"score_source": "section_numeric"}
    if not isinstance(section, dict):
        return None, {}

    for key in ("modality_score", "score", "normalized_score"):
        score = _normalize_score_value(section.get(key))
        if score is not None:
            return round(score, 2), {"score_source": key}

    negative_count = _safe_float(section.get("negative_label_count"))
    total_valid_count = _safe_float(section.get("total_valid_label_count"))
    if negative_count is not None and total_valid_count and total_valid_count > 0:
        return (
            round((negative_count / total_valid_count) * 100.0, 2),
            {
                "score_source": "negative_label_count_ratio",
                "negative_label_count": negative_count,
                "total_valid_label_count": total_valid_count,
            },
        )

    negative_ratio = _safe_float(section.get("negative_ratio"))
    if negative_ratio is not None:
        ratio_value = negative_ratio * 100.0 if negative_ratio <= 1 else negative_ratio
        return round(_clamp_100(ratio_value), 2), {"score_source": "negative_ratio"}

    top_label_score, top_label_metadata = _extract_top_label_distribution_score(
        section,
        negative_labels=negative_labels,
    )
    if top_label_score is not None:
        return top_label_score, top_label_metadata

    return _extract_label_distribution_score(
        section,
        negative_labels=negative_labels,
    )


def _compute_modality_confidence(
    multimodal_payload: dict[str, Any],
    *,
    modality: str,
) -> tuple[float | None, dict[str, Any]]:
    container = _resolve_multimodal_container(multimodal_payload)
    section = _lookup_modality_section(container, modality)
    if not isinstance(section, dict):
        if modality == "eeg":
            score, _ = _extract_modality_score(multimodal_payload, modality=modality, negative_labels=set())
            if score is not None:
                return 0.6, {
                    "confidence_components": {"availability": 0.6},
                    "confidence_formula": "fixed_eeg_confidence",
                }
        return None, {}

    if modality == "text":
        model_confidence = _extract_top_label_confidence(section)
        transcript_confidence = _normalize_confidence_value(section.get("transcript_confidence"))
        if transcript_confidence is None:
            speech_section = _lookup_modality_section(container, "speech")
            if isinstance(speech_section, dict):
                transcript_confidence = _normalize_confidence_value(
                    speech_section.get("transcript_confidence")
                )
        transcript_text = str(section.get("transcript_text") or "").strip()
        text_length_factor = round(_clamp_01(len(transcript_text) / 20.0), 4) if transcript_text else None
        return _blend_confidence_components(
            [
                ("model_confidence", 0.5, model_confidence),
                ("transcript_confidence", 0.3, transcript_confidence),
                ("text_length_factor", 0.2, text_length_factor),
            ]
        )

    if modality == "speech":
        model_confidence = _extract_top_label_confidence(section)
        transcript_confidence = _normalize_confidence_value(section.get("transcript_confidence"))
        return _blend_confidence_components(
            [
                ("model_confidence", 0.7, model_confidence),
                ("transcript_confidence", 0.3, transcript_confidence),
            ]
        )

    if modality == "face":
        model_confidence = _extract_top_label_confidence(section)
        coverage_ratio = _extract_coverage_ratio(section)
        quality_factor = _compute_quality_factor(section, modality="face")
        return _blend_confidence_components(
            [
                ("model_confidence", 0.4, model_confidence),
                ("coverage_ratio", 0.3, coverage_ratio),
                ("quality_factor", 0.3, quality_factor),
            ]
        )

    if modality == "pose":
        coverage_ratio = _extract_coverage_ratio(section)
        quality_factor = _compute_quality_factor(section, modality="pose")
        return _blend_confidence_components(
            [
                ("coverage_ratio", 0.5, coverage_ratio),
                ("quality_factor", 0.5, quality_factor),
            ]
        )

    if modality == "eeg":
        score, _ = _extract_modality_score(multimodal_payload, modality=modality, negative_labels=set())
        if score is None:
            return None, {}
        return 0.6, {
            "confidence_components": {"availability": 0.6},
            "confidence_formula": "fixed_eeg_confidence",
        }

    return None, {}


def _adjust_score_with_confidence(score: float, confidence: float) -> float:
    adjusted = 50.0 + (score - 50.0) * confidence
    return round(_clamp_100(adjusted), 2)


def _compute_weighted_score(
    weights: dict[str, float],
    score_lookup: dict[str, float],
) -> tuple[float | None, list[dict[str, Any]], list[str]]:
    weighted_sum = 0.0
    total_weight = 0.0
    used_components: list[dict[str, Any]] = []
    missing_components: list[str] = []
    for key, weight in weights.items():
        score = score_lookup.get(key)
        if score is None:
            missing_components.append(key)
            continue
        weighted_sum += score * weight
        total_weight += weight
        used_components.append(
            {
                "key": key,
                "score": round(score, 2),
                "weight": round(weight, 4),
                "weighted_contribution": round(score * weight, 2),
            }
        )
    if total_weight <= 0:
        return None, used_components, missing_components
    return round(weighted_sum / total_weight, 2), used_components, missing_components


def _gather_text_fragments(consultation_payload: dict[str, Any]) -> list[str]:
    fragments: list[str] = []
    for key in (
        "chief_complaint_summary",
        "chief_complaint_stage_summary",
        "symptom_screening_stage_summary",
        "high_risk_screening_stage_summary",
        "digital_human_consultation_summary",
    ):
        value = consultation_payload.get(key)
        if value:
            fragments.append(str(value))

    for result_key in (
        "chief_complaint_structured_result",
        "current_history_structured_result",
        "high_risk_screening_result",
    ):
        result_payload = consultation_payload.get(result_key)
        if not isinstance(result_payload, dict):
            continue
        for value in result_payload.values():
            if value not in (None, ""):
                fragments.append(str(value))
    return fragments


def _append_trigger(
    triggers: list[TriggerDecision],
    seen: set[tuple[str, str, str]],
    *,
    key: str,
    source: str,
    effect: str,
    evidence_summary: str | None,
    evidence_payload: dict[str, Any],
) -> None:
    signature = (key, source, evidence_summary or "")
    if signature in seen:
        return
    seen.add(signature)
    triggers.append(
        TriggerDecision(
            key=key,
            source=source,
            effect=effect,
            evidence_summary=evidence_summary,
            evidence_payload=dict(evidence_payload),
        )
    )


def _evaluate_safety_risk(
    *,
    consultation_payload: dict[str, Any],
    assessment_payload: dict[str, Any],
    rule_set: dict[str, Any],
) -> tuple[str, list[TriggerDecision]]:
    triggers: list[TriggerDecision] = []
    seen: set[tuple[str, str, str]] = set()
    safety_risk_level = "low"

    high_risk_result = _ensure_json_dict(
        consultation_payload.get("high_risk_screening_result")
    )
    alert_level = str(high_risk_result.get("alert_level") or "").strip().lower()
    suicidal_ideation = str(high_risk_result.get("suicidal_ideation") or "").strip().lower()
    self_harm_behavior = str(high_risk_result.get("self_harm_behavior") or "").strip().lower()
    suicide_plan = str(high_risk_result.get("suicide_plan") or "").strip().lower()
    acute_support_state = str(high_risk_result.get("acute_support_state") or "").strip().lower()

    if alert_level in {"high", "urgent"}:
        safety_risk_level = _max_risk_level(safety_risk_level, alert_level)
        _append_trigger(
            triggers,
            seen,
            key="high_risk_screening_positive",
            source="high_risk_screening",
            effect="immediate_manual_review_or_urgent_escalation",
            evidence_summary=f"高风险筛查输出 alert_level={alert_level}",
            evidence_payload=high_risk_result,
        )

    if suicide_plan == "positive":
        safety_risk_level = _max_risk_level(safety_risk_level, "urgent")
        _append_trigger(
            triggers,
            seen,
            key="suicide_plan_positive",
            source="high_risk_screening",
            effect="urgent_escalation",
            evidence_summary="高风险筛查明确出现自杀计划",
            evidence_payload=high_risk_result,
        )

    if self_harm_behavior == "positive":
        safety_risk_level = _max_risk_level(safety_risk_level, "urgent")
        _append_trigger(
            triggers,
            seen,
            key="self_harm_behavior_positive",
            source="high_risk_screening",
            effect="urgent_escalation",
            evidence_summary="高风险筛查明确出现自伤行为",
            evidence_payload=high_risk_result,
        )

    if suicidal_ideation == "positive":
        safety_risk_level = _max_risk_level(safety_risk_level, "high")
        _append_trigger(
            triggers,
            seen,
            key="suicidal_ideation_positive",
            source="high_risk_screening",
            effect="escalate_to_high_or_urgent",
            evidence_summary="高风险筛查提示存在伤害自己或轻生想法",
            evidence_payload=high_risk_result,
        )
        if acute_support_state in {"none", "limited", "unclear"}:
            safety_risk_level = _max_risk_level(safety_risk_level, "high")

    negative_labels = _normalize_negative_label_sets(rule_set)
    del negative_labels  # silence unused during current hard-trigger phase
    safety_rules = _get_rule_config(rule_set, "safety_rules", {})
    raw_keywords = safety_rules.get("self_harm_keywords") if isinstance(safety_rules, dict) else None
    keywords = tuple(
        str(keyword).strip()
        for keyword in _ensure_json_list(raw_keywords)
        if str(keyword).strip()
    ) or DEFAULT_SELF_HARM_KEYWORDS

    normalized_text_blob = "\n".join(
        _normalize_search_text(text)
        for text in _gather_text_fragments(consultation_payload)
        if text
    )
    for keyword in keywords:
        normalized_keyword = _normalize_search_text(keyword)
        if normalized_keyword and normalized_keyword in normalized_text_blob:
            safety_risk_level = _max_risk_level(safety_risk_level, "high")
            _append_trigger(
                triggers,
                seen,
                key="self_harm_statement",
                source="interview_or_scale",
                effect="escalate_to_high_or_urgent",
                evidence_summary=f"问诊文本命中高风险表达：{keyword}",
                evidence_payload={"keyword": keyword},
            )
            break

    for risk_flag in _ensure_json_list(assessment_payload.get("flattened_risk_flags")):
        if not isinstance(risk_flag, dict):
            continue
        flag_name = str(risk_flag.get("flag") or "").strip().lower()
        item_id = str(risk_flag.get("item_id") or "").strip().lower()
        scale_slug = _canonical_scale_slug(risk_flag.get("scale_slug"))
        if scale_slug == "phq9" and (
            flag_name == "self_harm_positive" or item_id == "q9"
        ):
            safety_risk_level = _max_risk_level(safety_risk_level, "high")
            _append_trigger(
                triggers,
                seen,
                key="phq9_q9_positive",
                source="phq9_q9",
                effect="escalate_to_high_or_urgent",
                evidence_summary="PHQ-9 第 9 题触发自伤/轻生风险标记",
                evidence_payload=risk_flag,
            )

    return safety_risk_level, triggers


def _resolve_depression_severity(
    depression_score: float | None,
    *,
    rule_set: dict[str, Any],
) -> tuple[str | None, str | None]:
    if depression_score is None:
        return None, None
    aggregation = _get_rule_config(rule_set, "aggregation", {})
    bands = aggregation.get("depression_severity_bands")
    if not isinstance(bands, list):
        bands = DEFAULT_DEPRESSION_SEVERITY_BANDS
    for band in bands:
        if not isinstance(band, dict):
            continue
        minimum = _safe_float(band.get("min"))
        maximum = _safe_float(band.get("max"))
        if minimum is None or maximum is None:
            continue
        if minimum <= depression_score <= maximum:
            return str(band.get("level") or ""), str(band.get("label") or "")
    return None, None


def _resolve_depression_risk_level(
    depression_severity: str | None,
    *,
    rule_set: dict[str, Any],
) -> str:
    aggregation = _get_rule_config(rule_set, "aggregation", {})
    risk_mapping = aggregation.get("depression_risk_mapping")
    if not isinstance(risk_mapping, dict):
        risk_mapping = DEFAULT_DEPRESSION_RISK_MAPPING
    return str(risk_mapping.get(depression_severity or "", "low")).strip().lower() or "low"


def _evaluate_depression_axis(
    *,
    assessment_payload: dict[str, Any],
    multimodal_payload: dict[str, Any],
    multimodal_source: str,
    rule_set: dict[str, Any],
) -> dict[str, Any]:
    aggregation = _get_rule_config(rule_set, "aggregation", {})
    scale_weights = aggregation.get("scale_weights")
    if not isinstance(scale_weights, dict):
        scale_weights = DEFAULT_SCALE_WEIGHTS
    else:
        scale_weights = {
            _canonical_scale_slug(key) or str(key): float(value)
            for key, value in scale_weights.items()
        }

    scale_result_map = assessment_payload.get("scale_result_map")
    if not isinstance(scale_result_map, dict):
        scale_result_map = {}
    normalized_scores = assessment_payload.get("normalized_scores")
    if not isinstance(normalized_scores, dict):
        normalized_scores = {}

    scale_score_lookup: dict[str, float] = {}
    for scale_slug in scale_weights:
        normalized_score = _safe_float(normalized_scores.get(scale_slug))
        if normalized_score is None:
            result_payload = scale_result_map.get(scale_slug)
            if isinstance(result_payload, dict):
                normalized_score = _safe_float(result_payload.get("normalized_score"))
        if normalized_score is not None:
            scale_score_lookup[scale_slug] = round(normalized_score, 2)

    scale_score, used_scales, missing_scales = _compute_weighted_score(
        scale_weights,
        scale_score_lookup,
    )

    multimodal_weights = aggregation.get("multimodal_weights")
    if not isinstance(multimodal_weights, dict):
        multimodal_weights = DEFAULT_MULTIMODAL_WEIGHTS
    else:
        multimodal_weights = {
            _canonical_modality_name(key) or str(key): float(value)
            for key, value in multimodal_weights.items()
        }

    negative_label_sets = _normalize_negative_label_sets(rule_set)
    modality_score_lookup: dict[str, float] = {}
    modality_confidence_lookup: dict[str, float] = {}
    modality_components: list[dict[str, Any]] = []
    missing_modalities: list[str] = []
    for modality in multimodal_weights:
        raw_score, raw_score_metadata = _extract_modality_score(
            multimodal_payload,
            modality=modality,
            negative_labels=negative_label_sets.get(modality, set()),
        )
        if raw_score is None:
            missing_modalities.append(modality)
            continue
        confidence, confidence_metadata = _compute_modality_confidence(
            multimodal_payload,
            modality=modality,
        )
        if confidence is None:
            confidence = 0.5
            confidence_metadata = {
                "confidence_components": {},
                "confidence_formula": "default_fallback",
            }
        adjusted_score = _adjust_score_with_confidence(raw_score, confidence)
        modality_score_lookup[modality] = adjusted_score
        modality_confidence_lookup[modality] = confidence
        modality_components.append(
            {
                "key": modality,
                "raw_score": raw_score,
                "confidence": round(confidence, 4),
                "adjusted_score": adjusted_score,
                "score_metadata": raw_score_metadata,
                "confidence_metadata": confidence_metadata,
            }
        )

    multimodal_score, used_modalities, computed_missing_modalities = _compute_weighted_score(
        multimodal_weights,
        modality_score_lookup,
    )
    if not missing_modalities:
        missing_modalities = computed_missing_modalities

    multimodal_confidence_weighted_sum = 0.0
    multimodal_confidence_total_weight = 0.0
    for modality, weight in multimodal_weights.items():
        confidence = modality_confidence_lookup.get(modality, 0.0)
        multimodal_confidence_weighted_sum += confidence * weight
        multimodal_confidence_total_weight += weight
    multimodal_confidence = None
    if multimodal_confidence_total_weight > 0:
        multimodal_confidence = round(
            multimodal_confidence_weighted_sum / multimodal_confidence_total_weight,
            4,
        )
    multimodal_confidence_grade = None
    if multimodal_confidence is not None:
        if multimodal_confidence >= 0.75:
            multimodal_confidence_grade = "A"
        elif multimodal_confidence >= 0.55:
            multimodal_confidence_grade = "B"
        elif multimodal_confidence >= 0.30:
            multimodal_confidence_grade = "C"
        else:
            multimodal_confidence_grade = "insufficient"

    top_level_weights = {
        "scale_score": float(aggregation.get("assessment_weight", 0.80)),
        "multimodal_score": float(aggregation.get("multimodal_weight", 0.20)),
    }
    if scale_score is not None and multimodal_score is not None:
        depression_score = round(
            (top_level_weights["scale_score"] * scale_score)
            + (top_level_weights["multimodal_score"] * multimodal_score),
            2,
        )
        used_top_level = [
            {
                "key": "scale_score",
                "score": round(scale_score, 2),
                "weight": round(top_level_weights["scale_score"], 4),
                "weighted_contribution": round(
                    top_level_weights["scale_score"] * scale_score,
                    2,
                ),
            },
            {
                "key": "multimodal_score",
                "score": round(multimodal_score, 2),
                "weight": round(top_level_weights["multimodal_score"], 4),
                "weighted_contribution": round(
                    top_level_weights["multimodal_score"] * multimodal_score,
                    2,
                ),
            },
        ]
        missing_top_level: list[str] = []
        top_level_formula = "fixed_weighted_average"
    else:
        top_level_lookup: dict[str, float] = {}
        if scale_score is not None:
            top_level_lookup["scale_score"] = scale_score
        if multimodal_score is not None:
            top_level_lookup["multimodal_score"] = multimodal_score
        depression_score, used_top_level, missing_top_level = _compute_weighted_score(
            top_level_weights,
            top_level_lookup,
        )
        top_level_formula = "renormalized_weighted_average_over_available_components"
    depression_severity, depression_severity_label = _resolve_depression_severity(
        depression_score,
        rule_set=rule_set,
    )
    depression_risk_level = _resolve_depression_risk_level(
        depression_severity,
        rule_set=rule_set,
    )

    pending_integrations: list[str] = []
    if multimodal_source == "upstream_live_snapshot":
        pending_integrations.append("multimodal_final_feature_bundle")

    return {
        "scale_score": scale_score,
        "multimodal_score": multimodal_score,
        "multimodal_confidence": multimodal_confidence,
        "multimodal_confidence_grade": multimodal_confidence_grade,
        "depression_score": depression_score,
        "depression_severity": depression_severity,
        "depression_severity_label": depression_severity_label,
        "depression_risk_level": depression_risk_level,
        "score_breakdown": {
            "scale_score": {
                "value": scale_score,
                "used_scales": used_scales,
                "missing_scales": missing_scales,
                "source_scale_count": assessment_payload.get("scale_count"),
            },
            "multimodal_score": {
                "value": multimodal_score,
                "overall_confidence": multimodal_confidence,
                "overall_confidence_grade": multimodal_confidence_grade,
                "used_modalities": used_modalities,
                "detected_modality_scores": modality_components,
                "missing_modalities": missing_modalities,
                "source_type": multimodal_source,
                "formula": "weighted average over confidence-adjusted modality scores",
            },
            "depression_score": {
                "value": depression_score,
                "used_components": used_top_level,
                "missing_components": missing_top_level,
                "formula": top_level_formula,
            },
        },
        "pending_integrations": pending_integrations,
    }


def _select_intervention_program_ids(
    *,
    risk_level: str,
    intervention_catalog: dict[str, Any],
    rule_set: dict[str, Any],
) -> tuple[str | None, list[str], bool]:
    mapping = _get_rule_config(rule_set, "intervention_mapping", {})
    if not isinstance(mapping, dict):
        mapping = DEFAULT_INTERVENTION_MAPPING
    settings = mapping.get(risk_level) or DEFAULT_INTERVENTION_MAPPING.get(risk_level, {})
    intensity = str(settings.get("intensity") or "").strip().lower() or None
    allow_auto_intervention = bool(settings.get("allow_auto_intervention", False))
    if not intensity:
        return None, [], allow_auto_intervention

    selected_program_ids: list[str] = []
    for program in _ensure_json_list(intervention_catalog.get("programs")):
        if not isinstance(program, dict):
            continue
        intensity_levels = {
            str(level).strip().lower()
            for level in _ensure_json_list(program.get("intensity_levels"))
            if str(level).strip()
        }
        if intensity in intensity_levels:
            program_id = _normalize_identifier(program.get("id"))
            if program_id:
                selected_program_ids.append(program_id)
    return intensity, selected_program_ids, allow_auto_intervention


def _build_front_display_payload(
    *,
    risk_level: str,
    safety_risk_level: str,
    depression_score: float | None,
    depression_severity_label: str | None,
    requires_human_review: bool,
) -> dict[str, Any]:
    if safety_risk_level in {"high", "urgent"}:
        message = "当前结果以安全风险信号为主导，建议优先线下评估与人工介入。"
    elif depression_score is not None and depression_severity_label:
        message = f"综合抑郁得分约为 {depression_score:.2f} 分，当前判定为“{depression_severity_label}”。"
    else:
        message = "当前结果以已有结构化输入完成，后续可在补齐多模态接口后继续增强。"
    return {
        "risk_level": risk_level,
        "risk_level_label": _risk_label(risk_level),
        "title": f"当前评估结果：{_risk_label(risk_level)}",
        "message": message,
        "requires_human_review": requires_human_review,
    }


def _build_explanation_summary(
    *,
    risk_level: str,
    safety_risk_level: str,
    depression_score: float | None,
    depression_severity_label: str | None,
    triggers: list[TriggerDecision],
) -> str:
    if triggers:
        return (
            f"当前统一风险等级为“{_risk_label(risk_level)}”，主要由安全相关触发信号驱动，"
            f"当前安全风险轴为“{_risk_label(safety_risk_level)}”。"
        )
    if depression_score is not None and depression_severity_label:
        return (
            f"当前统一风险等级为“{_risk_label(risk_level)}”，综合抑郁得分约为 {depression_score:.2f} 分，"
            f"对应“{depression_severity_label}”。"
        )
    return f"当前统一风险等级为“{_risk_label(risk_level)}”，但输入仍存在待补齐项。"


def _build_result_payload(
    *,
    evaluation_id: str,
    rule_set_id: str,
    rule_set: dict[str, Any],
    workflow_id: str | None,
    risk_level: str,
    safety_risk_level: str,
    depression_axis: dict[str, Any],
    triggers: list[TriggerDecision],
    requires_human_review: bool,
    consultation_source: str,
    assessment_source: str,
    multimodal_source: str,
    missing_inputs: list[str],
    pending_integrations: list[str],
) -> dict[str, Any]:
    templates = _get_rule_config(rule_set, "recommendation_templates", {})
    if not isinstance(templates, dict):
        templates = DEFAULT_RECOMMENDATION_TEMPLATES
    referral_templates = templates.get("referral") or DEFAULT_RECOMMENDATION_TEMPLATES["referral"]
    lifestyle_templates = templates.get("lifestyle") or DEFAULT_RECOMMENDATION_TEMPLATES["lifestyle"]
    intervention_catalog = _load_intervention_catalog_or_raise()
    intervention_intensity, recommended_program_ids, allow_auto_intervention = _select_intervention_program_ids(
        risk_level=risk_level,
        intervention_catalog=intervention_catalog,
        rule_set=rule_set,
    )

    explanation_summary = _build_explanation_summary(
        risk_level=risk_level,
        safety_risk_level=safety_risk_level,
        depression_score=depression_axis.get("depression_score"),
        depression_severity_label=depression_axis.get("depression_severity_label"),
        triggers=triggers,
    )
    front_display = _build_front_display_payload(
        risk_level=risk_level,
        safety_risk_level=safety_risk_level,
        depression_score=depression_axis.get("depression_score"),
        depression_severity_label=depression_axis.get("depression_severity_label"),
        requires_human_review=requires_human_review,
    )

    trigger_summaries = [
        trigger.evidence_summary
        for trigger in triggers
        if trigger.evidence_summary
    ]
    result_pending_integrations = list(dict.fromkeys(
        list(pending_integrations) + list(depression_axis.get("pending_integrations") or [])
    ))
    return {
        "evaluation_id": evaluation_id,
        "workflow_id": workflow_id,
        "rule_set_id": rule_set_id,
        "risk_level": risk_level,
        "risk_level_label": _risk_label(risk_level),
        "safety_risk_level": safety_risk_level,
        "depression_score": depression_axis.get("depression_score"),
        "depression_severity": depression_axis.get("depression_severity"),
        "depression_severity_label": depression_axis.get("depression_severity_label"),
        "risk_explanation": {
            "summary": explanation_summary,
            "trigger_summaries": trigger_summaries,
            "score_breakdown": depression_axis.get("score_breakdown") or {},
            "missing_inputs": missing_inputs,
            "pending_integrations": result_pending_integrations,
            "input_sources": {
                "consultation": consultation_source,
                "assessment": assessment_source,
                "multimodal": multimodal_source,
            },
        },
        "referral_recommendations": list(referral_templates.get(risk_level) or []),
        "lifestyle_suggestions": list(lifestyle_templates.get(risk_level) or []),
        "intervention_entry_payload": {
            "evaluation_id": evaluation_id,
            "workflow_id": workflow_id,
            "rule_set_id": rule_set_id,
            "risk_level": risk_level,
            "safety_risk_level": safety_risk_level,
            "depression_score": depression_axis.get("depression_score"),
            "depression_severity": depression_axis.get("depression_severity"),
            "recommended_intensity": intervention_intensity,
            "recommended_program_ids": recommended_program_ids,
            "allow_auto_intervention": allow_auto_intervention and not requires_human_review,
            "requires_human_review": requires_human_review,
            "hard_trigger_keys": [trigger.key for trigger in triggers],
            "missing_inputs": missing_inputs,
            "pending_integrations": result_pending_integrations,
        },
        "front_display": front_display,
    }


def _serialize_trigger_record(trigger_record: RiskTrigger) -> dict[str, Any]:
    return {
        "trigger_id": trigger_record.id,
        "trigger_key": trigger_record.trigger_key,
        "trigger_source": trigger_record.trigger_source,
        "trigger_effect": trigger_record.trigger_effect,
        "evidence_summary": trigger_record.evidence_summary,
        "evidence_payload": _ensure_json_dict(trigger_record.evidence_payload),
        "created_at": trigger_record.created_at.isoformat(),
    }


def _serialize_evaluation(
    db_session,
    evaluation_record: RiskEvaluation,
) -> dict[str, Any]:
    trigger_records = db_session.scalars(
        select(RiskTrigger)
        .where(RiskTrigger.evaluation_id == evaluation_record.id)
        .order_by(RiskTrigger.created_at.asc(), RiskTrigger.id.asc())
    ).all()
    return {
        "evaluation_id": evaluation_record.id,
        "user_id": evaluation_record.user_id,
        "encounter_session_id": evaluation_record.encounter_session_id,
        "consultation_session_id": evaluation_record.consultation_session_id,
        "assessment_session_id": evaluation_record.assessment_session_id,
        "multimodal_session_id": evaluation_record.multimodal_session_id,
        "workflow_id": evaluation_record.workflow_id,
        "rule_set_id": evaluation_record.rule_set_id,
        "risk_level": evaluation_record.risk_level,
        "depression_score": round(evaluation_record.depression_score, 2)
        if evaluation_record.depression_score is not None
        else None,
        "depression_severity": evaluation_record.depression_severity,
        "safety_risk_level": evaluation_record.safety_risk_level,
        "requires_human_review": evaluation_record.requires_human_review,
        "status": evaluation_record.status,
        "consultation_payload": _ensure_json_dict(evaluation_record.consultation_payload),
        "assessment_payload": _ensure_json_dict(evaluation_record.assessment_payload),
        "multimodal_payload": _ensure_json_dict(evaluation_record.multimodal_payload),
        "input_summary": _ensure_json_dict(evaluation_record.input_summary_payload),
        "triggers": [_serialize_trigger_record(record) for record in trigger_records],
        "result": _ensure_json_dict(evaluation_record.result_payload),
        "created_at": evaluation_record.created_at.isoformat(),
        "updated_at": evaluation_record.updated_at.isoformat(),
        "completed_at": evaluation_record.completed_at.isoformat()
        if evaluation_record.completed_at
        else None,
    }


def _get_evaluation_or_raise(db_session, evaluation_id: str) -> RiskEvaluation:
    evaluation_record = db_session.get(RiskEvaluation, evaluation_id)
    if evaluation_record:
        return evaluation_record
    raise RiskServiceError("risk evaluation not found", code=4041, status_code=404)


def _require_evaluation_owner(
    evaluation_record: RiskEvaluation,
    *,
    acting_user_id: str,
) -> None:
    if evaluation_record.user_id != acting_user_id:
        raise RiskServiceError("risk evaluation forbidden", code=4031, status_code=403)


def create_risk_evaluation(
    payload: CreateRiskEvaluationRequest,
    *,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    if payload.user_id != acting_user_id:
        raise RiskServiceError(
            "user mismatch for risk evaluation creation",
            code=4032,
            status_code=403,
        )

    settings = get_settings()
    rule_set_id = (
        _normalize_identifier(payload.rule_set_id)
        or str(settings["default_risk_rule_set"])
    )
    rule_set = _load_rule_set_or_raise(rule_set_id)

    assessment_payload, assessment_source = _resolve_assessment_payload(
        payload,
        acting_user_id=acting_user_id,
    )
    consultation_payload, consultation_source = _resolve_consultation_payload(
        payload,
        acting_user_id=acting_user_id,
        assessment_payload=assessment_payload,
    )
    multimodal_payload, multimodal_source = _resolve_multimodal_payload(
        payload,
        acting_user_id=acting_user_id,
        consultation_payload=consultation_payload,
        assessment_payload=assessment_payload,
    )

    if not consultation_payload and not assessment_payload:
        raise RiskServiceError(
            "at least one of consultation payload or assessment payload is required",
            code=4002,
            status_code=422,
        )

    encounter_session_id = _coalesce_identifier(
        "encounter_session_id",
        payload.encounter_session_id,
        consultation_payload.get("encounter_session_id"),
        assessment_payload.get("encounter_session_id"),
    )
    consultation_session_id = _coalesce_identifier(
        "consultation_session_id",
        payload.consultation_session_id,
        consultation_payload.get("session_id"),
        assessment_payload.get("source_consultation_flow_run_id"),
        _ensure_json_dict(assessment_payload.get("source_handoff")).get("session_id"),
    )
    assessment_session_id = _coalesce_identifier(
        "assessment_session_id",
        payload.assessment_session_id,
        assessment_payload.get("assessment_session_id"),
    )
    multimodal_session_id = _coalesce_identifier(
        "multimodal_session_id",
        payload.multimodal_session_id,
        consultation_payload.get("multimodal_session_id"),
        assessment_payload.get("multimodal_session_id"),
        multimodal_payload.get("multimodal_session_id"),
    )
    workflow_id = _coalesce_identifier(
        "workflow_id",
        consultation_payload.get("workflow_id"),
        rule_set.get("workflow_id"),
        _ensure_json_dict(assessment_payload.get("source_handoff")).get("workflow_id"),
    )

    safety_risk_level, triggers = _evaluate_safety_risk(
        consultation_payload=consultation_payload,
        assessment_payload=assessment_payload,
        rule_set=rule_set,
    )
    depression_axis = _evaluate_depression_axis(
        assessment_payload=assessment_payload,
        multimodal_payload=multimodal_payload,
        multimodal_source=multimodal_source,
        rule_set=rule_set,
    )
    risk_level = _max_risk_level(
        safety_risk_level,
        depression_axis.get("depression_risk_level"),
    )
    requires_human_review = risk_level in {"high", "urgent"} or bool(
        triggers
    )

    missing_inputs: list[str] = []
    if not consultation_payload:
        missing_inputs.append("consultation_payload")
    if not assessment_payload:
        missing_inputs.append("assessment_aggregate_payload")
    if not multimodal_payload:
        missing_inputs.append("multimodal_feature_bundle")

    pending_integrations: list[str] = []
    if multimodal_source in {"missing", "unavailable"}:
        pending_integrations.append("multimodal_final_feature_bundle")
    if consultation_source == "assessment_source_handoff":
        pending_integrations.append("consultation_session_optional_refetch")

    now = _now()
    evaluation_record = RiskEvaluation(
        user_id=payload.user_id,
        encounter_session_id=encounter_session_id,
        consultation_session_id=consultation_session_id,
        assessment_session_id=assessment_session_id,
        multimodal_session_id=multimodal_session_id,
        workflow_id=workflow_id,
        rule_set_id=rule_set_id,
        risk_level=risk_level,
        depression_score=depression_axis.get("depression_score"),
        depression_severity=depression_axis.get("depression_severity"),
        safety_risk_level=safety_risk_level,
        requires_human_review=requires_human_review,
        status="completed",
        consultation_payload=consultation_payload or {},
        assessment_payload=assessment_payload or {},
        multimodal_payload=multimodal_payload or {},
        input_summary_payload={
            "consultation_source": consultation_source,
            "assessment_source": assessment_source,
            "multimodal_source": multimodal_source,
            "missing_inputs": missing_inputs,
            "pending_integrations": pending_integrations,
        },
        result_payload={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )

    with get_db_session() as db_session:
        db_session.add(evaluation_record)
        db_session.flush()

        result_payload = _build_result_payload(
            evaluation_id=evaluation_record.id,
            rule_set_id=rule_set_id,
            rule_set=rule_set,
            workflow_id=workflow_id,
            risk_level=risk_level,
            safety_risk_level=safety_risk_level,
            depression_axis=depression_axis,
            triggers=triggers,
            requires_human_review=requires_human_review,
            consultation_source=consultation_source,
            assessment_source=assessment_source,
            multimodal_source=multimodal_source,
            missing_inputs=missing_inputs,
            pending_integrations=pending_integrations,
        )
        evaluation_record.result_payload = result_payload
        evaluation_record.updated_at = _now()

        for trigger in triggers:
            db_session.add(
                RiskTrigger(
                    evaluation_id=evaluation_record.id,
                    trigger_key=trigger.key,
                    trigger_source=trigger.source,
                    trigger_effect=trigger.effect,
                    evidence_summary=trigger.evidence_summary,
                    evidence_payload=trigger.evidence_payload,
                    created_at=now,
                )
            )
        db_session.flush()
        return _serialize_evaluation(db_session, evaluation_record)


def get_risk_evaluation(
    evaluation_id: str,
    *,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        evaluation_record = _get_evaluation_or_raise(db_session, evaluation_id)
        _require_evaluation_owner(
            evaluation_record,
            acting_user_id=acting_user_id,
        )
        return _serialize_evaluation(db_session, evaluation_record)


def get_risk_explanation(
    evaluation_id: str,
    *,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        evaluation_record = _get_evaluation_or_raise(db_session, evaluation_id)
        _require_evaluation_owner(
            evaluation_record,
            acting_user_id=acting_user_id,
        )
        serialized = _serialize_evaluation(db_session, evaluation_record)
        return {
            "evaluation_id": serialized["evaluation_id"],
            "risk_level": serialized["risk_level"],
            "safety_risk_level": serialized["safety_risk_level"],
            "depression_score": serialized["depression_score"],
            "depression_severity": serialized["depression_severity"],
            "requires_human_review": serialized["requires_human_review"],
            "triggers": serialized["triggers"],
            "risk_explanation": _ensure_json_dict(serialized["result"]).get(
                "risk_explanation",
                {},
            ),
            "referral_recommendations": _ensure_json_dict(serialized["result"]).get(
                "referral_recommendations",
                [],
            ),
            "lifestyle_suggestions": _ensure_json_dict(serialized["result"]).get(
                "lifestyle_suggestions",
                [],
            ),
            "front_display": _ensure_json_dict(serialized["result"]).get(
                "front_display",
                {},
            ),
        }


def override_risk_evaluation(
    evaluation_id: str,
    payload: OverrideRiskEvaluationRequest,
    *,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    del payload

    raise RiskServiceError(
        (
            "risk override workflow is reserved but not implemented yet; "
            f"evaluation_id={evaluation_id}, acting_user_id={acting_user_id}"
        ),
        code=5011,
        status_code=501,
    )
