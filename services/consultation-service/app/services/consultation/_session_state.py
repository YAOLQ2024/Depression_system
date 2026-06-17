from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.models import ConsultationSession
from app.schemas.consultations import ConsultationTurnRequest
from app.services.consultation import _ensure_json_dict, _ensure_json_list, _now
from app.services.consultation._subtitle_history import (
    _sync_doctor_subtitle_history,
)
from app.services.workflow_loader import QuestionItem, ScriptNode, WorkflowBundle


def _default_engine_state() -> dict[str, Any]:
    return {
        "current_prompt": None,
        "waiting_node_type": None,
        "completed_stages": [],
        "completed_question_keys": [],
        "last_branch_taken": None,
    }


CHIEF_COMPLAINT_NO_CLEAR_HINTS = (
    "说不上来",
    "一下子说不上来",
    "一下说不上来",
    "不太说得上来",
    "有点说不上来",
    "有点讲不清楚",
    "说不太清楚",
    "说不清楚",
    "讲不清楚",
    "不太清楚",
    "不清楚",
    "不知道该怎么说",
    "不知道怎么说",
    "不知道说什么",
    "不太知道怎么说",
    "也不知道怎么形容",
    "不太会形容",
    "不知道从哪说起",
    "不知道从哪里说起",
    "不知道该从哪说起",
    "不知道先说什么",
    "没什么特别的问题",
    "没什么特别不舒服",
    "没什么明显问题",
    "没有特别的问题",
    "没有明显的问题",
    "没有什么大问题",
    "也没啥问题",
    "没啥问题",
    "没什么问题",
    "好像没什么问题",
    "感觉没什么问题",
    "暂时没什么问题",
    "目前没什么问题",
    "就是来看看",
    "就想来看看",
    "就是来咨询一下",
    "就想咨询一下",
    "来了解一下",
    "想了解一下",
    "来评估一下",
    "想评估一下",
    "做个评估",
    "想做个评估",
    "想做个状态评估",
    "做个状态评估",
    "来测一下",
    "想测一下",
    "来筛查一下",
    "想筛查一下",
    "做个筛查",
    "想做个筛查",
    "看看心理状态",
    "看看自己的状态",
    "想看看状态",
    "看看最近状态",
    "来做检查",
    "想做检查",
    "来复查一下",
    "先来看看情况",
    "先来了解情况",
    "身边人建议我来",
    "家里人建议我来",
    "家人建议我来",
    "父母让我来",
    "老师建议我来",
    "老师让我来",
    "朋友建议我来",
    "同学建议我来",
    "同事建议我来",
    "被建议来看看",
    "别人建议我来",
)

CHIEF_COMPLAINT_CLEAR_SYMPTOM_HINTS = (
    "失眠",
    "睡不着",
    "睡不踏实",
    "早醒",
    "入睡困难",
    "睡眠不好",
    "焦虑",
    "紧张",
    "害怕",
    "恐慌",
    "心慌",
    "烦躁",
    "易怒",
    "脾气大",
    "情绪低落",
    "心情不好",
    "抑郁",
    "难受",
    "压抑",
    "没劲",
    "提不起精神",
    "不开心",
    "总想哭",
    "胸闷",
    "头痛",
    "头晕",
    "食欲不好",
    "不想吃饭",
    "注意力不集中",
    "学不进去",
    "上不下去班",
    "不想上学",
    "不想上班",
    "没法工作",
    "反复想",
    "控制不住",
    "强迫",
    "反复检查",
    "想很多",
    "胡思乱想",
    "高兴不起来",
    "没有兴趣",
    "不想社交",
    "不愿见人",
    "躯体不舒服",
    "心累",
    "压力大",
    "最近状态不对",
)


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


def _get_completed_question_keys(
    session_record: ConsultationSession,
) -> list[str]:
    engine_state = _ensure_json_dict(session_record.engine_state)
    completed_question_keys: list[str] = []
    for raw_value in _ensure_json_list(
        engine_state.get("completed_question_keys")
    ):
        value = str(raw_value or "").strip()
        if value and value not in completed_question_keys:
            completed_question_keys.append(value)
    return completed_question_keys


def _record_completed_question_key(
    session_record: ConsultationSession, question_key: str | None
) -> None:
    normalized_key = str(question_key or "").strip()
    if not normalized_key:
        return
    engine_state = _ensure_json_dict(session_record.engine_state)
    completed_question_keys = _get_completed_question_keys(session_record)
    if normalized_key not in completed_question_keys:
        completed_question_keys.append(normalized_key)
    engine_state["completed_question_keys"] = completed_question_keys
    session_record.engine_state = engine_state


def _advance_progress_cursor(
    stage_id: str, bundle: WorkflowBundle
) -> tuple[str | None, str | None]:
    if stage_id not in bundle.substeps:
        return None, None
    current_index = bundle.substeps.index(stage_id)
    if current_index >= len(bundle.substeps) - 1:
        return None, None
    next_stage_id = bundle.substeps[current_index + 1]
    next_stage = bundle.stage_scripts[next_stage_id]
    return next_stage_id, next_stage.entry_node


def _resolve_default_prompt_next_target(node: ScriptNode) -> str | None:
    branches = node.payload.get("branches", {})
    preferred = branches.get("normal")
    if isinstance(preferred, dict):
        return preferred.get("next")
    for branch_payload in branches.values():
        if isinstance(branch_payload, dict):
            next_target = branch_payload.get("next")
            if next_target:
                return next_target
    return None


def _count_remaining_prompt_items(
    session_record: ConsultationSession, bundle: WorkflowBundle
) -> int:
    stage_id = str(session_record.current_stage_id or "").strip() or None
    node_id = str(session_record.current_node_id or "").strip() or None
    if not stage_id or not node_id:
        return 0

    prompt_count = 0
    simulated_requires_human_review = bool(
        session_record.requires_human_review
    )
    visited: set[tuple[str, str, bool]] = set()

    while stage_id and node_id:
        visit_key = (stage_id, node_id, simulated_requires_human_review)
        if visit_key in visited:
            break
        visited.add(visit_key)

        stage = bundle.stage_scripts.get(stage_id)
        if not stage:
            break
        node = stage.nodes.get(node_id)
        if not node:
            break

        target: str | None = None
        if node.type in {"system_gate", "speak"}:
            target = node.payload.get("next")
        elif node.type == "route_by_rule":
            target = _resolve_route(session_record, node)
        elif node.type == "decision":
            branch_name = _evaluate_decision(session_record, node)
            if (
                stage_id == "stage-04-high-risk-screening"
                and branch_name == "human_intervention_required"
            ):
                simulated_requires_human_review = True
            target = node.payload.get("branches", {}).get(branch_name)
        elif node.type == "speak_then_wait":
            prompt_count += 1
            target = _resolve_default_prompt_next_target(node)
        elif node.type == "speak_then_complete":
            prompt_count += 1
            target = node.payload.get("next")
        else:
            break

        if target == "stage-complete":
            if (
                stage_id == "stage-04-high-risk-screening"
                and simulated_requires_human_review
            ):
                break
            stage_id, node_id = _advance_progress_cursor(stage_id, bundle)
            continue

        node_id = str(target or "").strip() or None

    return prompt_count


def _resolve_prompt_progress(
    session_record: ConsultationSession, bundle: WorkflowBundle
) -> tuple[int, int]:
    completed_prompt_count = len(_get_completed_question_keys(session_record))
    total_prompt_count = completed_prompt_count + _count_remaining_prompt_items(
        session_record, bundle
    )
    return completed_prompt_count, total_prompt_count


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


def _sync_playlist_state(
    session_record: ConsultationSession, bundle: WorkflowBundle
) -> None:
    completed_prompt_count, total_prompt_count = _resolve_prompt_progress(
        session_record, bundle
    )
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
        session_record.completed_prompt_count = completed_prompt_count
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
    session_record.completed_prompt_count = completed_prompt_count
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


def _normalize_chief_complaint_text(text: str) -> str:
    return re.sub(r"[\s，。！？、,.!?；;：:“”\"'（）()【】\[\]\-]+", "", text)


def _parse_chief_complaint_route(text: str) -> str:
    normalized = _normalize_chief_complaint_text(text)
    if not normalized:
        return "clear_problem"
    if any(token in normalized for token in CHIEF_COMPLAINT_CLEAR_SYMPTOM_HINTS):
        return "clear_problem"
    if any(token in normalized for token in CHIEF_COMPLAINT_NO_CLEAR_HINTS):
        return "no_clear_problem"
    return "clear_problem"


def _set_slot(
    session_record: ConsultationSession, slot_name: str, value: Any
) -> None:
    slot_values = _ensure_json_dict(session_record.slot_values)
    slot_values[slot_name] = value
    session_record.slot_values = slot_values


def _store_free_text_extraction(
    session_record: ConsultationSession,
    *,
    target_slot: str | None,
    target_slots: list[str],
    text: str,
    extracted: dict[str, Any],
) -> None:
    if target_slot:
        extracted[target_slot] = text
        _set_slot(session_record, target_slot, text)
    for slot_name in target_slots:
        extracted[slot_name] = text
        _set_slot(session_record, slot_name, text)

    if target_slot == "chief_complaint_text":
        session_record.chief_complaint_raw_text = text or None


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
        _store_free_text_extraction(
            session_record,
            target_slot=target_slot,
            target_slots=target_slots,
            text=text,
            extracted=extracted,
        )

    elif strategy == "chief_complaint_entry_parse":
        target_slot = extraction.get("target_slot")
        target_slots = extraction.get("target_slots", [])
        route_slot = extraction.get("route_slot")
        _store_free_text_extraction(
            session_record,
            target_slot=target_slot,
            target_slots=target_slots,
            text=text,
            extracted=extracted,
        )
        if route_slot:
            route_value = _parse_chief_complaint_route(text)
            extracted[route_slot] = route_value
            _set_slot(session_record, route_slot, route_value)

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
