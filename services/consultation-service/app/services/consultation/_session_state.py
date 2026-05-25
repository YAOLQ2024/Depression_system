from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.models import ConsultationSession
from app.schemas.consultations import ConsultationTurnRequest
from app.services.consultation import _ensure_json_dict, _now
from app.services.consultation._subtitle_history import (
    _ensure_subtitle_history,
    _sync_doctor_subtitle_history,
)
from app.services.workflow_loader import QuestionItem, ScriptNode, WorkflowBundle


def _default_engine_state() -> dict[str, Any]:
    return {
        "current_prompt": None,
        "waiting_node_type": None,
        "completed_stages": [],
        "last_branch_taken": None,
    }


def _serialize_question_item(question_item: QuestionItem) -> dict[str, Any]:
    return {
        "question_key": question_item.question_key,
        "stage_id": question_item.stage_id,
        "stage_label": question_item.stage_label,
        "stage_order": question_item.stage_order,
        "order": question_item.order,
        "node_id": question_item.node_id,
        "video_asset_id": question_item.video_asset_id,
        "video_uri": question_item.video_uri,
        "question_text": question_item.question_text,
        "subtitle_text": question_item.subtitle_text
        or question_item.question_text,
        "response_required": question_item.response_required,
    }


def _get_total_prompt_count(bundle: WorkflowBundle) -> int:
    return sum(
        len(stage.question_items)
        for stage in bundle.digital_human_playlist.stages_in_order
    )


def _resolve_current_question_item_object(
    session_record: ConsultationSession,
    bundle: WorkflowBundle,
) -> QuestionItem | None:
    if not session_record.current_stage_id:
        return None
    playlist_stage = bundle.digital_human_playlist.stages_by_id.get(
        session_record.current_stage_id
    )
    if not playlist_stage:
        return None

    if session_record.current_node_id:
        direct_match = playlist_stage.question_items_by_node_id.get(
            session_record.current_node_id
        )
        if direct_match:
            return direct_match

    if playlist_stage.question_items:
        return playlist_stage.question_items[0]
    return None


def _resolve_current_question_item(
    session_record: ConsultationSession,
    bundle: WorkflowBundle,
) -> dict[str, Any] | None:
    question_item = _resolve_current_question_item_object(
        session_record, bundle
    )
    return _serialize_question_item(question_item) if question_item else None


def _count_prompt_items_before(
    question_item: QuestionItem, bundle: WorkflowBundle
) -> int:
    completed = 0
    for stage in bundle.digital_human_playlist.stages_in_order:
        if stage.stage_order < question_item.stage_order:
            completed += len(stage.question_items)
            continue
        if stage.stage_order == question_item.stage_order:
            completed += sum(
                1
                for item in stage.question_items
                if item.order < question_item.order
            )
            break
    return completed


def _sync_playlist_state(
    session_record: ConsultationSession, bundle: WorkflowBundle
) -> None:
    total_prompt_count = _get_total_prompt_count(bundle)
    session_record.playlist_version = (
        bundle.digital_human_playlist.playlist_version or None
    )
    session_record.total_prompt_count = total_prompt_count

    current_question_item = _resolve_current_question_item_object(
        session_record, bundle
    )
    if not current_question_item:
        session_record.current_question_key = None
        session_record.current_question_order = None
        session_record.current_question_video_asset_id = None
        session_record.current_question_video_uri = None
        session_record.current_question_text = None
        session_record.current_question_subtitle_text = None
        session_record.completed_prompt_count = (
            total_prompt_count
            if session_record.status
            in {"handoff_ready", "paused_for_human_review"}
            or session_record.completed_at
            else 0
        )
        return

    session_record.current_question_key = current_question_item.question_key
    session_record.current_question_order = current_question_item.order
    session_record.current_question_video_asset_id = (
        current_question_item.video_asset_id
    )
    session_record.current_question_video_uri = current_question_item.video_uri
    session_record.current_question_text = (
        current_question_item.question_text
    )
    session_record.current_question_subtitle_text = (
        current_question_item.subtitle_text
        or current_question_item.question_text
    )
    session_record.completed_prompt_count = _count_prompt_items_before(
        current_question_item, bundle
    )
    _sync_doctor_subtitle_history(session_record, current_question_item)


def _resolve_current_stage_progress(
    session_record: ConsultationSession,
    bundle: WorkflowBundle,
) -> dict[str, Any] | None:
    if not session_record.current_stage_id:
        return None
    playlist_stage = bundle.digital_human_playlist.stages_by_id.get(
        session_record.current_stage_id
    )
    if not playlist_stage:
        return None
    return {
        "stage_id": playlist_stage.stage_id,
        "stage_label": playlist_stage.stage_label,
        "stage_order": playlist_stage.stage_order,
        "total_stages": len(bundle.digital_human_playlist.stages_in_order),
    }


def _render_prompt(node: ScriptNode, slot_values: dict[str, Any]) -> str:
    template = (
        node.payload.get("template_prompt") or node.payload.get("prompt") or ""
    )

    def replace_token(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        value = slot_values.get(key)
        if isinstance(value, list):
            return "、".join(str(item) for item in value)
        if value is None:
            return "暂未明确"
        return str(value)

    return re.sub(r"\{\{\s*([^}]+)\s*\}\}", replace_token, template)


def _normalize_text(
    raw_input: str | None, transcript_text: str | None, input_type: str
) -> str:
    if transcript_text and transcript_text.strip():
        return transcript_text.strip()
    if raw_input and raw_input.strip():
        return raw_input.strip()
    if input_type == "continue_button":
        return "继续"
    return ""


def _resolve_transcript_source(
    payload: ConsultationTurnRequest,
) -> str:
    if payload.transcript_source:
        return payload.transcript_source
    if payload.input_type == "speech":
        return "dolphin_final"
    return payload.input_type


def _resolve_response_window(
    payload: ConsultationTurnRequest,
) -> tuple[datetime, datetime]:
    started_at = payload.response_started_at or _now()
    completed_at = payload.response_completed_at or started_at
    if completed_at < started_at:
        completed_at = started_at
    return started_at, completed_at


def _build_summary(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= 80:
        return compact
    return f"{compact[:77]}..."


def _normalize_slot_text(value: Any) -> str | None:
    if value is None:
        return None
    compact = re.sub(r"\s+", " ", str(value)).strip()
    return compact or None


def _join_summary_lines(lines: list[str | None]) -> str:
    normalized = [
        text
        for raw in lines
        if (text := _normalize_slot_text(raw)) is not None
    ]
    return "；".join(normalized) if normalized else "暂未明确"


def _describe_risk_value(value: Any) -> str:
    mapping = {
        "positive": "有",
        "negative": "无",
        "unclear": "未明确",
        "available": "有稳定支持",
        "limited": "支持有限",
        "none": "暂无支持",
    }
    normalized = _normalize_slot_text(value)
    if not normalized:
        return "未明确"
    return mapping.get(normalized, normalized)


def _parse_positive_negative(text: str) -> str:
    if any(
        token in text for token in ["没有", "没", "不会", "不是", "无", "从未"]
    ):
        return "negative"
    if any(
        token in text
        for token in ["有", "想过", "出现过", "是", "会", "差点", "真的"]
    ):
        return "positive"
    return "unclear"


def _parse_support_state(text: str) -> str:
    if any(
        token in text for token in ["没有", "无人", "一个人", "没人", "无"]
    ):
        return "none"
    if any(
        token in text
        for token in ["有限", "不太方便", "有时候", "不一定", "不稳定"]
    ):
        return "limited"
    if any(
        token in text
        for token in [
            "有",
            "可以",
            "能",
            "有人",
            "家人",
            "朋友",
            "老师",
            "同事",
        ]
    ):
        return "available"
    return "unclear"


def _extract_risk_value(slot_name: str, text: str) -> str:
    if slot_name == "acute_support_state":
        return _parse_support_state(text)
    return _parse_positive_negative(text)


def _set_slot(
    session_record: ConsultationSession, slot_name: str, value: Any
) -> None:
    slot_values = _ensure_json_dict(session_record.slot_values)
    slot_values[slot_name] = value
    session_record.slot_values = slot_values


def _apply_extraction(
    session_record: ConsultationSession, node: ScriptNode, text: str
) -> dict[str, Any]:
    extraction = node.payload.get("extraction") or {}
    if not extraction:
        return {}

    extracted: dict[str, Any] = {}
    strategy = extraction.get("strategy")

    if strategy == "free_text":
        target_slot = extraction.get("target_slot")
        target_slots = extraction.get("target_slots", [])
        if target_slot:
            extracted[target_slot] = text
            _set_slot(session_record, target_slot, text)
        for slot_name in target_slots:
            extracted[slot_name] = text
            _set_slot(session_record, slot_name, text)

        if target_slot == "chief_complaint_text":
            session_record.chief_complaint_raw_text = text or None

    elif strategy == "risk_enum_parse":
        target_slot = extraction.get("target_slot")
        target_slots = extraction.get("target_slots", [])
        if target_slot:
            value = _extract_risk_value(target_slot, text)
            extracted[target_slot] = value
            _set_slot(session_record, target_slot, value)
        for slot_name in target_slots:
            value = _extract_risk_value(slot_name, text)
            extracted[slot_name] = value
            _set_slot(session_record, slot_name, value)

    return extracted


def _resolve_route(
    session_record: ConsultationSession, node: ScriptNode
) -> str:
    slot_values = _ensure_json_dict(session_record.slot_values)
    keywords = slot_values.get(node.payload.get("rule_source", ""), [])
    if isinstance(keywords, str):
        keywords = [keywords]
    branches = node.payload.get("branches", {})
    for candidate in ["sleep", "mood", "anxiety"]:
        if candidate in keywords and candidate in branches:
            return branches[candidate]
    return branches.get("default")


def _evaluate_condition(slot_values: dict[str, Any], expression: str) -> bool:
    expression = expression.strip()
    if " and " in expression:
        return all(
            _evaluate_condition(slot_values, part)
            for part in expression.split(" and ")
        )
    if " in [" in expression:
        left, right = expression.split(" in [", 1)
        slot_name = left.strip()
        candidates = [item.strip() for item in right.rstrip("]").split(",")]
        return str(slot_values.get(slot_name)) in candidates
    if "==" in expression:
        left, right = expression.split("==", 1)
        return str(slot_values.get(left.strip())) == right.strip()
    return False


def _evaluate_decision(
    session_record: ConsultationSession, node: ScriptNode
) -> str:
    slot_values = _ensure_json_dict(session_record.slot_values)
    rules = node.payload.get("decision_rules", {})
    for branch_name, rule_payload in rules.items():
        if (
            branch_name == "safe_to_continue"
            and rule_payload.get("default") is True
        ):
            continue
        any_conditions = rule_payload.get("any", [])
        if any(
            _evaluate_condition(slot_values, expression)
            for expression in any_conditions
        ):
            return branch_name
    return "safe_to_continue"


def _build_current_history_result(session_record: ConsultationSession) -> None:
    slot_values = _ensure_json_dict(session_record.slot_values)
    recent_stressor = _normalize_slot_text(slot_values.get("recent_stressor"))
    compulsive_behavior = _normalize_slot_text(
        slot_values.get("compulsive_behavior")
    )
    manic_episode_indicator = _normalize_slot_text(
        slot_values.get("manic_episode_indicator")
    )
    structured_result = {
        key: value
        for key, value in {
            "recent_stressor": recent_stressor,
            "compulsive_behavior": compulsive_behavior,
            "manic_episode_indicator": manic_episode_indicator,
        }.items()
        if value
    }
    session_record.current_history_structured_result = structured_result
    _set_slot(
        session_record,
        "symptom_screening_structured_result",
        structured_result,
    )
    _set_slot(
        session_record,
        "symptom_screening_stage_summary",
        _join_summary_lines(
            [
                (
                    f"近期压力事件：{recent_stressor}"
                    if recent_stressor
                    else ""
                ),
                (
                    f"反复思维或控制不住的行为：{compulsive_behavior}"
                    if compulsive_behavior
                    else ""
                ),
                (
                    f"情绪高涨与精力异常表现：{manic_episode_indicator}"
                    if manic_episode_indicator
                    else ""
                ),
            ]
        ),
    )


def _build_chief_complaint_result(
    session_record: ConsultationSession,
) -> None:
    slot_values = _ensure_json_dict(session_record.slot_values)
    chief_complaint_text = _normalize_slot_text(
        slot_values.get("chief_complaint_text")
    )
    symptom_duration = _normalize_slot_text(
        slot_values.get("symptom_duration")
    )
    symptom_first_occurrence = _normalize_slot_text(
        slot_values.get("symptom_first_occurrence")
    )
    structured_result = {
        key: value
        for key, value in {
            "chief_complaint_text": chief_complaint_text,
            "symptom_duration": symptom_duration,
            "symptom_first_occurrence": symptom_first_occurrence,
        }.items()
        if value not in (None, "", [])
    }
    summary = _join_summary_lines(
        [
            f"主要困扰：{chief_complaint_text}" if chief_complaint_text else "",
            f"起病与持续时间：{symptom_duration}" if symptom_duration else "",
            (
                f"当前核心症状与既往情况：{symptom_first_occurrence}"
                if symptom_first_occurrence
                else ""
            ),
        ]
    )
    _set_slot(
        session_record,
        "chief_complaint_structured_result",
        structured_result,
    )
    _set_slot(session_record, "chief_complaint_stage_summary", summary)
    _set_slot(session_record, "chief_complaint_summary", summary)
    session_record.chief_complaint_summary = summary


def _build_high_risk_result(
    session_record: ConsultationSession, branch_name: str
) -> None:
    slot_values = _ensure_json_dict(session_record.slot_values)
    suicidal_ideation = slot_values.get("suicidal_ideation", "unclear")
    self_harm_behavior = slot_values.get("self_harm_behavior", "unclear")
    suicide_plan = slot_values.get("suicide_plan", "unclear")
    acute_support_state = slot_values.get("acute_support_state", "unclear")
    primary_concern = _normalize_slot_text(slot_values.get("primary_concern"))
    alert_level = (
        "high" if branch_name == "human_intervention_required" else "low"
    )
    session_record.high_risk_screening_result = {
        "suicidal_ideation": suicidal_ideation,
        "self_harm_behavior": self_harm_behavior,
        "suicide_plan": suicide_plan,
        "acute_support_state": acute_support_state,
        "primary_concern": primary_concern,
        "alert_level": alert_level,
        "outcome": branch_name,
    }
    _set_slot(
        session_record,
        "high_risk_screening_stage_summary",
        _join_summary_lines(
            [
                f"自伤或轻生想法：{_describe_risk_value(suicidal_ideation)}",
                (
                    f"具体计划或实际行为："
                    f"{_describe_risk_value(suicide_plan)}/"
                    f"{_describe_risk_value(self_harm_behavior)}"
                ),
                (
                    f"当前支持系统："
                    f"{_describe_risk_value(acute_support_state)}"
                ),
                f"本次主要诉求：{primary_concern}" if primary_concern else "",
                f"风险判定：{alert_level}",
            ]
        ),
    )
    session_record.requires_human_review = (
        branch_name == "human_intervention_required"
    )


def _build_digital_human_consultation_summary(
    session_record: ConsultationSession,
) -> str:
    slot_values = _ensure_json_dict(session_record.slot_values)
    summary = _join_summary_lines(
        [
            _normalize_slot_text(
                slot_values.get("chief_complaint_stage_summary")
            )
            or _normalize_slot_text(session_record.chief_complaint_summary),
            _normalize_slot_text(
                slot_values.get("symptom_screening_stage_summary")
            ),
            _normalize_slot_text(
                slot_values.get("high_risk_screening_stage_summary")
            ),
        ]
    )
    _set_slot(session_record, "digital_human_consultation_summary", summary)
    return summary


def _build_scale_handoff_payload(
    session_record: ConsultationSession, bundle: WorkflowBundle
) -> dict[str, Any]:
    slot_values = _ensure_json_dict(session_record.slot_values)
    digital_human_consultation_summary = (
        _normalize_slot_text(
            slot_values.get("digital_human_consultation_summary")
        )
        or _build_digital_human_consultation_summary(session_record)
    )
    return {
        "workflow_id": bundle.workflow_id,
        "session_id": session_record.id,
        "chief_complaint_summary": session_record.chief_complaint_summary,
        "chief_complaint_structured_result": (
            slot_values.get("chief_complaint_structured_result") or {}
        ),
        "chief_complaint_stage_summary": (
            slot_values.get("chief_complaint_stage_summary")
            or session_record.chief_complaint_summary
        ),
        "current_history_structured_result": (
            session_record.current_history_structured_result or {}
        ),
        "symptom_screening_stage_summary": (
            slot_values.get("symptom_screening_stage_summary") or ""
        ),
        "high_risk_screening_result": (
            session_record.high_risk_screening_result or {}
        ),
        "high_risk_screening_stage_summary": (
            slot_values.get("high_risk_screening_stage_summary") or ""
        ),
        "digital_human_consultation_summary": (
            digital_human_consultation_summary
        ),
        "required_scales": bundle.required_scales,
    }


def _set_current_prompt(
    session_record: ConsultationSession,
    prompt: str | None,
    waiting_node_type: str | None,
) -> None:
    engine_state = _ensure_json_dict(session_record.engine_state)
    engine_state["current_prompt"] = prompt
    engine_state["waiting_node_type"] = waiting_node_type
    if waiting_node_type != "speak_then_wait":
        engine_state.pop("active_turn_id", None)
        engine_state.pop("active_turn_question_key", None)
    session_record.engine_state = engine_state
