from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.clients.multimodal_client import (
    clear_pose_turn_runtime as clear_upstream_pose_turn_runtime,
    create_multimodal_session as create_upstream_multimodal_session,
    get_multimodal_live as fetch_upstream_multimodal_live,
    get_multimodal_turn_bundle as fetch_upstream_multimodal_turn_bundle,
    submit_visual_capture as submit_upstream_visual_capture,
)
from app.database import get_db_session
from app.models import ConsultationSession, ConsultationTurn, EncounterSession
from app.schemas.consultations import (
    ConsultationTurnRequest,
    CreateConsultationSessionRequest,
)
from app.services.workflow_loader import (
    QuestionItem,
    ScriptNode,
    WorkflowBundle,
    get_workflow_loader,
)


class ConsultationServiceError(Exception):
    def __init__(self, message: str, code: int, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_json_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def _ensure_json_list(value: list[Any] | None) -> list[Any]:
    return list(value or [])


def _ensure_subtitle_history(
    value: list[Any] | None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(_ensure_json_list(value), start=1):
        if not isinstance(raw_entry, dict):
            continue
        speaker = str(raw_entry.get("speaker") or "").strip().lower()
        text = str(raw_entry.get("text") or "").strip()
        if speaker not in {"doctor", "user"} or not text:
            continue
        sequence = raw_entry.get("sequence")
        try:
            normalized_sequence = int(sequence)
        except (TypeError, ValueError):
            normalized_sequence = index
        created_at = raw_entry.get("created_at")
        updated_at = raw_entry.get("updated_at") or created_at
        entries.append(
            {
                "entry_key": str(
                    raw_entry.get("entry_key")
                    or f"{speaker}:{normalized_sequence}:{raw_entry.get('prompt_key') or 'entry'}"
                ),
                "speaker": speaker,
                "text": text,
                "status": str(raw_entry.get("status") or "final"),
                "source": str(raw_entry.get("source") or ""),
                "prompt_key": raw_entry.get("prompt_key"),
                "stage_id": raw_entry.get("stage_id"),
                "node_id": raw_entry.get("node_id"),
                "turn_id": raw_entry.get("turn_id"),
                "sequence": normalized_sequence,
                "created_at": str(created_at) if created_at else None,
                "updated_at": str(updated_at) if updated_at else None,
            }
        )
    entries.sort(
        key=lambda item: (
            int(item.get("sequence") or 0),
            str(item.get("created_at") or ""),
        )
    )
    return entries


def _next_subtitle_sequence(history: list[dict[str, Any]]) -> int:
    if not history:
        return 1
    return max(int(entry.get("sequence") or 0) for entry in history) + 1


def _split_subtitle_segments(text: str | None) -> list[str]:
    normalized = (text or "").strip()
    if not normalized:
        return []

    segments: list[str] = []
    for line in normalized.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        compact_line = line.strip()
        if not compact_line:
            continue
        parts = re.findall(r"[^。！？!?]+[。！？!?]?", compact_line)
        cleaned_parts = [part.strip() for part in parts if part.strip()]
        if cleaned_parts:
            segments.extend(cleaned_parts)
        else:
            segments.append(compact_line)
    return segments


def _upsert_subtitle_history_entry(
    history: list[dict[str, Any]],
    *,
    entry_key: str,
    speaker: str,
    text: str,
    status: str,
    source: str,
    prompt_key: str | None,
    stage_id: str | None,
    node_id: str | None,
    turn_id: str | None = None,
) -> bool:
    normalized_text = text.strip()
    if not normalized_text:
        return False

    timestamp = _now().isoformat()
    for entry in history:
        if entry.get("entry_key") != entry_key:
            continue
        changed = False
        for key, value in {
            "speaker": speaker,
            "text": normalized_text,
            "status": status,
            "source": source,
            "prompt_key": prompt_key,
            "stage_id": stage_id,
            "node_id": node_id,
            "turn_id": turn_id,
        }.items():
            if entry.get(key) != value:
                entry[key] = value
                changed = True
        if changed:
            entry["updated_at"] = timestamp
        return changed

    history.append(
        {
            "entry_key": entry_key,
            "speaker": speaker,
            "text": normalized_text,
            "status": status,
            "source": source,
            "prompt_key": prompt_key,
            "stage_id": stage_id,
            "node_id": node_id,
            "turn_id": turn_id,
            "sequence": _next_subtitle_sequence(history),
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )
    return True


def _sync_doctor_subtitle_history(
    session_record: ConsultationSession,
    question_item: QuestionItem | None,
) -> None:
    if not question_item:
        return

    prompt_text = _ensure_json_dict(session_record.engine_state).get(
        "current_prompt"
    )
    subtitle_source = (
        question_item.subtitle_text
        or prompt_text
        or question_item.question_text
        or ""
    )
    segments = _split_subtitle_segments(subtitle_source)
    if not segments:
        return

    history = _ensure_subtitle_history(session_record.subtitle_history_payload)
    changed = False
    for index, segment in enumerate(segments):
        changed = _upsert_subtitle_history_entry(
            history,
            entry_key=f"doctor:{question_item.question_key}:{index}",
            speaker="doctor",
            text=segment,
            status="final",
            source="doctor_prompt",
            prompt_key=question_item.question_key,
            stage_id=question_item.stage_id,
            node_id=question_item.node_id,
        ) or changed
    if changed:
        session_record.subtitle_history_payload = history


def _finalize_user_subtitle_entry(
    session_record: ConsultationSession,
    *,
    prompt_key: str | None,
    transcript_text: str,
    turn_id: str,
    source: str,
) -> None:
    normalized_text = transcript_text.strip()
    if not normalized_text:
        return

    resolved_prompt_key = (
        prompt_key or session_record.current_question_key or turn_id
    )
    history = _ensure_subtitle_history(session_record.subtitle_history_payload)
    changed = _upsert_subtitle_history_entry(
        history,
        entry_key=f"user:draft:{resolved_prompt_key}",
        speaker="user",
        text=normalized_text,
        status="final",
        source=source,
        prompt_key=prompt_key,
        stage_id=session_record.current_stage_id,
        node_id=session_record.current_node_id,
        turn_id=turn_id,
    )
    if changed:
        session_record.subtitle_history_payload = history


def _extract_upstream_data(upstream: dict, *, error_code: int) -> dict[str, Any]:
    if upstream["status"] >= 400:
        payload = upstream.get("payload") or {}
        raise ConsultationServiceError(
            str(payload.get("message") or "multimodal service request failed"),
            code=int(payload.get("code") or error_code),
            status_code=int(upstream["status"]),
        )
    data = (upstream.get("payload") or {}).get("data") or {}
    if not isinstance(data, dict):
        raise ConsultationServiceError(
            "multimodal service returned invalid payload",
            code=error_code,
            status_code=502,
        )
    return data


def _extract_optional_upstream_data(
    upstream: dict,
    *,
    error_code: int,
    allowed_statuses: set[int],
) -> dict[str, Any] | None:
    if int(upstream["status"]) in allowed_statuses:
        return None
    return _extract_upstream_data(upstream, error_code=error_code)


def _clear_pose_turn_runtime_best_effort(
    *,
    multimodal_session_id: str | None,
    turn_id: str | None,
    acting_user_id: str,
) -> None:
    if not multimodal_session_id or not turn_id:
        return
    try:
        clear_upstream_pose_turn_runtime(
            multimodal_session_id=multimodal_session_id,
            turn_id=turn_id,
            acting_user_id=acting_user_id,
        )
    except Exception:
        return


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


def _extract_chief_complaint_keywords(text: str) -> list[str]:
    normalized = text.lower()
    keywords: list[str] = []
    if any(
        token in normalized for token in ["睡", "失眠", "早醒", "入睡", "夜醒"]
    ):
        keywords.append("sleep")
    if any(
        token in normalized
        for token in [
            "情绪",
            "低落",
            "难过",
            "抑郁",
            "没兴趣",
            "提不起劲",
            "累",
            "空",
        ]
    ):
        keywords.append("mood")
    if any(
        token in normalized
        for token in ["紧张", "焦虑", "害怕", "心慌", "担心", "放松不下来"]
    ):
        keywords.append("anxiety")
    return keywords or ["general"]


def _build_summary(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= 80:
        return compact
    return f"{compact[:77]}..."


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

        derived_slots = extraction.get("derived_slots", [])
        if target_slot == "chief_complaint_text":
            session_record.chief_complaint_raw_text = text or None
            keywords = _extract_chief_complaint_keywords(text)
            summary = _build_summary(text) if text else "暂未明确"
            if "chief_complaint_keywords" in derived_slots:
                extracted["chief_complaint_keywords"] = keywords
                _set_slot(session_record, "chief_complaint_keywords", keywords)
            if "chief_complaint_summary" in derived_slots:
                extracted["chief_complaint_summary"] = summary
                _set_slot(session_record, "chief_complaint_summary", summary)
                session_record.chief_complaint_summary = summary

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
    keys = [
        "dominant_followup_track",
        "symptom_duration",
        "symptom_frequency",
        "symptom_intensity",
        "functional_impact",
        "recent_stressor",
        "prior_psychiatric_visit",
        "family_history",
    ]
    session_record.current_history_structured_result = {
        key: slot_values.get(key)
        for key in keys
        if slot_values.get(key) not in (None, "")
    }


def _build_high_risk_result(
    session_record: ConsultationSession, branch_name: str
) -> None:
    slot_values = _ensure_json_dict(session_record.slot_values)
    alert_level = (
        "high" if branch_name == "human_intervention_required" else "low"
    )
    session_record.high_risk_screening_result = {
        "suicidal_ideation": slot_values.get("suicidal_ideation", "unclear"),
        "self_harm_behavior": slot_values.get("self_harm_behavior", "unclear"),
        "suicide_plan": slot_values.get("suicide_plan", "unclear"),
        "acute_support_state": slot_values.get(
            "acute_support_state", "unclear"
        ),
        "alert_level": alert_level,
        "outcome": branch_name,
    }
    session_record.requires_human_review = (
        branch_name == "human_intervention_required"
    )


def _build_scale_handoff_payload(
    session_record: ConsultationSession, bundle: WorkflowBundle
) -> dict[str, Any]:
    return {
        "workflow_id": bundle.workflow_id,
        "session_id": session_record.id,
        "chief_complaint_summary": session_record.chief_complaint_summary,
        "current_history_structured_result": (
            session_record.current_history_structured_result or {}
        ),
        "high_risk_screening_result": (
            session_record.high_risk_screening_result or {}
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


def _get_active_turn_id(session_record: ConsultationSession) -> str | None:
    engine_state = _ensure_json_dict(session_record.engine_state)
    active_turn_id = str(engine_state.get("active_turn_id") or "").strip()
    return active_turn_id or None


def _clear_active_turn(session_record: ConsultationSession) -> None:
    engine_state = _ensure_json_dict(session_record.engine_state)
    engine_state.pop("active_turn_id", None)
    engine_state.pop("active_turn_question_key", None)
    session_record.engine_state = engine_state


def _ensure_active_turn(
    session_record: ConsultationSession,
    bundle: WorkflowBundle,
) -> str:
    engine_state = _ensure_json_dict(session_record.engine_state)
    current_question_item = _resolve_current_question_item_object(
        session_record,
        bundle,
    )
    active_turn_question_key = (
        current_question_item.question_key
        if current_question_item
        else session_record.current_question_key or session_record.current_node_id
    )
    active_turn_id = str(engine_state.get("active_turn_id") or "").strip()
    if (
        not active_turn_id
        or engine_state.get("active_turn_question_key")
        != active_turn_question_key
    ):
        active_turn_id = str(uuid.uuid4())
        engine_state["active_turn_id"] = active_turn_id
        engine_state["active_turn_question_key"] = active_turn_question_key
        session_record.engine_state = engine_state
    return active_turn_id


def _mark_stage_completed(
    session_record: ConsultationSession, stage_id: str
) -> None:
    engine_state = _ensure_json_dict(session_record.engine_state)
    completed = _ensure_json_list(engine_state.get("completed_stages"))
    if stage_id not in completed:
        completed.append(stage_id)
    engine_state["completed_stages"] = completed
    session_record.engine_state = engine_state


def _move_to_target(
    session_record: ConsultationSession,
    target: str | None,
    bundle: WorkflowBundle,
) -> None:
    if target == "stage-complete":
        _advance_stage(session_record, bundle)
        return
    session_record.current_node_id = target


def _advance_stage(
    session_record: ConsultationSession, bundle: WorkflowBundle
) -> None:
    if not session_record.current_stage_id:
        return

    completed_stage_id = session_record.current_stage_id
    _mark_stage_completed(session_record, completed_stage_id)
    _set_current_prompt(session_record, None, None)

    if completed_stage_id == "stage-03-current-history-followup":
        _build_current_history_result(session_record)

    current_index = bundle.substeps.index(completed_stage_id)
    if current_index < len(bundle.substeps) - 1:
        next_stage_id = bundle.substeps[current_index + 1]
        next_stage = bundle.stage_scripts[next_stage_id]
        session_record.current_stage_id = next_stage_id
        session_record.current_node_id = next_stage.entry_node
        session_record.status = "running"
        return

    encounter_session = session_record.encounter_session

    if session_record.requires_human_review:
        session_record.workflow_stage_id = "clinical-decision"
        session_record.status = "paused_for_human_review"
        if encounter_session is not None:
            encounter_session.current_flow_type = "consultation"
            encounter_session.status = "paused"
            encounter_session.updated_at = _now()
    else:
        session_record.workflow_stage_id = bundle.scale_stage_id
        session_record.status = "handoff_ready"
        session_record.scale_handoff_payload = _build_scale_handoff_payload(
            session_record, bundle
        )
        if encounter_session is not None:
            encounter_session.current_flow_type = "assessment"
            encounter_session.status = "in_progress"
            encounter_session.updated_at = _now()

    session_record.current_stage_id = None
    session_record.current_node_id = None
    session_record.completed_at = _now()


def _auto_advance(
    session_record: ConsultationSession, bundle: WorkflowBundle
) -> None:
    while session_record.current_stage_id and session_record.current_node_id:
        stage = bundle.stage_scripts[session_record.current_stage_id]
        node = stage.nodes[session_record.current_node_id]

        if node.type == "system_gate":
            checks = node.payload.get("checks", [])
            context_snapshot = _ensure_json_dict(
                session_record.context_snapshot
            )
            missing = [
                check for check in checks if not context_snapshot.get(check)
            ]
            if missing:
                raise ConsultationServiceError(
                    f"consultation context incomplete: {', '.join(missing)}",
                    code=4005,
                )
            _move_to_target(session_record, node.payload.get("next"), bundle)
            continue

        if node.type == "speak":
            _render_prompt(node, _ensure_json_dict(session_record.slot_values))
            _move_to_target(session_record, node.payload.get("next"), bundle)
            continue

        if node.type == "route_by_rule":
            target = _resolve_route(session_record, node)
            if not target:
                raise ConsultationServiceError(
                    "consultation route target missing",
                    code=5002,
                    status_code=500,
                )
            _move_to_target(session_record, target, bundle)
            continue

        if node.type == "decision":
            branch_name = _evaluate_decision(session_record, node)
            if node.id == "evaluate-high-risk":
                _build_high_risk_result(session_record, branch_name)
            target = node.payload.get("branches", {}).get(branch_name)
            if not target:
                raise ConsultationServiceError(
                    "consultation decision branch missing",
                    code=5003,
                    status_code=500,
                )
            engine_state = _ensure_json_dict(session_record.engine_state)
            engine_state["last_branch_taken"] = branch_name
            session_record.engine_state = engine_state
            _move_to_target(session_record, target, bundle)
            continue

        if node.type == "speak_then_wait":
            prompt = _render_prompt(
                node, _ensure_json_dict(session_record.slot_values)
            )
            session_record.status = "waiting_user_input"
            _set_current_prompt(session_record, prompt, node.type)
            _ensure_active_turn(session_record, bundle)
            return

        if node.type == "speak_then_complete":
            prompt = _render_prompt(
                node, _ensure_json_dict(session_record.slot_values)
            )
            session_record.status = "waiting_system_completion"
            _set_current_prompt(session_record, prompt, node.type)
            return

        raise ConsultationServiceError(
            f"unsupported node type: {node.type}", code=5001, status_code=500
        )


def _infer_branch(payload: ConsultationTurnRequest) -> str:
    if payload.input_type == "silence":
        return "silence"
    if payload.input_type == "recognition_failure":
        return "recognition_failure"
    return "normal"


def _serialize_session(
    session_record: ConsultationSession, bundle: WorkflowBundle
) -> dict[str, Any]:
    engine_state = _ensure_json_dict(session_record.engine_state)
    current_prompt = engine_state.get("current_prompt")
    current_question_item = _resolve_current_question_item(
        session_record, bundle
    )
    current_stage_progress = _resolve_current_stage_progress(
        session_record, bundle
    )
    return {
        "session_id": session_record.id,
        "encounter_session_id": session_record.encounter_session_id,
        "user_id": session_record.user_id,
        "workflow_id": session_record.workflow_id,
        "script_bundle": session_record.script_bundle,
        "playlist_version": session_record.playlist_version
        or bundle.digital_human_playlist.playlist_version,
        "playlist_manifest_status": (
            bundle.digital_human_playlist.manifest_status
        ),
        "delivery_mode": bundle.digital_human_playlist.delivery_mode,
        "total_prompt_count": session_record.total_prompt_count,
        "completed_prompt_count": session_record.completed_prompt_count,
        "workflow_stage_id": session_record.workflow_stage_id,
        "current_stage_id": session_record.current_stage_id,
        "current_node_id": session_record.current_node_id,
        "current_question_key": session_record.current_question_key,
        "current_question_order": session_record.current_question_order,
        "current_question_video_asset_id": (
            session_record.current_question_video_asset_id
        ),
        "current_question_video_uri": session_record.current_question_video_uri,
        "current_question_text": (
            session_record.current_question_text
        ),
        "current_question_subtitle_text": (
            session_record.current_question_subtitle_text
        ),
        "current_stage": current_stage_progress,
        "status": session_record.status,
        "current_turn_id": _get_active_turn_id(session_record),
        "assigned_doctor_persona": session_record.assigned_doctor_persona,
        "requires_human_review": session_record.requires_human_review,
        "current_prompt": current_prompt,
        "current_question_item": current_question_item,
        "participant_profile_snapshot": _ensure_json_dict(
            session_record.participant_profile_snapshot
        ),
        "slot_values": _ensure_json_dict(session_record.slot_values),
        "chief_complaint_summary": session_record.chief_complaint_summary,
        "current_history_structured_result": (
            session_record.current_history_structured_result or {}
        ),
        "high_risk_screening_result": (
            session_record.high_risk_screening_result or {}
        ),
        "multimodal_session_id": session_record.multimodal_session_id,
        "multimodal_live": session_record.multimodal_live_payload or {},
        "multimodal_live_updated_at": (
            session_record.multimodal_live_updated_at.isoformat()
            if session_record.multimodal_live_updated_at
            else None
        ),
        "subtitle_history": _ensure_subtitle_history(
            session_record.subtitle_history_payload
        ),
        "scale_handoff_payload": session_record.scale_handoff_payload or {},
        "required_scales": bundle.required_scales,
        "created_at": session_record.created_at.isoformat(),
        "updated_at": session_record.updated_at.isoformat(),
        "started_at": session_record.started_at.isoformat()
        if session_record.started_at
        else None,
        "completed_at": session_record.completed_at.isoformat()
        if session_record.completed_at
        else None,
    }


def _get_session_or_raise(
    db_session: Session, session_id: str
) -> ConsultationSession:
    session_record = db_session.get(ConsultationSession, session_id)
    if not session_record:
        raise ConsultationServiceError(
            "consultation session not found", code=4041, status_code=404
        )
    return session_record


def _require_acting_user_id(acting_user_id: str | None) -> str:
    if not acting_user_id:
        raise ConsultationServiceError(
            "missing acting user id", code=4013, status_code=401
        )
    return acting_user_id


def _ensure_multimodal_session_binding(
    session_record: ConsultationSession,
    *,
    acting_user_id: str,
) -> str:
    if session_record.multimodal_session_id:
        return session_record.multimodal_session_id

    multimodal_data = _extract_upstream_data(
        create_upstream_multimodal_session(
            user_id=acting_user_id,
            encounter_session_id=session_record.encounter_session_id,
            flow_type="consultation",
            flow_run_id=session_record.id,
        ),
        error_code=5021,
    )
    multimodal_session = multimodal_data.get("multimodal_session") or {}
    multimodal_session_id = (
        multimodal_session.get("id") or multimodal_session.get("session_id")
    )
    if not multimodal_session_id:
        raise ConsultationServiceError(
            "multimodal session id missing",
            code=5022,
            status_code=502,
        )

    session_record.multimodal_session_id = str(multimodal_session_id)
    session_record.updated_at = _now()
    return session_record.multimodal_session_id


def _refresh_multimodal_live_snapshot(
    session_record: ConsultationSession,
    *,
    acting_user_id: str,
) -> dict[str, Any]:
    multimodal_session_id = _ensure_multimodal_session_binding(
        session_record,
        acting_user_id=acting_user_id,
    )
    live_data = _extract_upstream_data(
        fetch_upstream_multimodal_live(
            multimodal_session_id=multimodal_session_id,
            acting_user_id=acting_user_id,
        ),
        error_code=5024,
    )
    session_record.multimodal_live_payload = live_data
    session_record.multimodal_live_updated_at = _now()
    return live_data


def create_consultation_session(
    payload: CreateConsultationSessionRequest, acting_user_id: str | None
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    if payload.user_id != acting_user_id:
        raise ConsultationServiceError(
            "user mismatch for consultation creation",
            code=4031,
            status_code=403,
        )
    bundle = get_workflow_loader().load_bundle()
    persona_id = (
        payload.assigned_doctor_persona
        or get_workflow_loader().default_persona
    )
    if persona_id not in bundle.doctor_personas:
        raise ConsultationServiceError(
            "doctor persona not found", code=4006, status_code=404
        )

    encounter_session_id = str(uuid.uuid4())
    consultation_session_id = str(uuid.uuid4())
    multimodal_data = _extract_upstream_data(
        create_upstream_multimodal_session(
            user_id=payload.user_id,
            encounter_session_id=encounter_session_id,
            flow_type="consultation",
            flow_run_id=consultation_session_id,
        ),
        error_code=5021,
    )
    multimodal_session = multimodal_data.get("multimodal_session") or {}
    multimodal_session_id = multimodal_session.get("id")
    if not multimodal_session_id:
        raise ConsultationServiceError(
            "multimodal session id missing",
            code=5022,
            status_code=502,
        )

    first_stage_id = bundle.substeps[0]
    first_stage = bundle.stage_scripts[first_stage_id]
    now = _now()
    context_snapshot = {
        "participant_profile_snapshot_loaded": True,
        "assigned_doctor_persona_loaded": True,
        "audio_channel_ready": payload.audio_channel_ready,
        "consent_confirmed": payload.consent_confirmed,
        "participant_profile_snapshot": payload.participant_profile_snapshot,
        "assigned_doctor_persona": persona_id,
        "device_status": payload.device_status,
        "consultation_ready_state": payload.consultation_ready_state,
    }
    encounter_record = EncounterSession(
        id=encounter_session_id,
        user_id=payload.user_id,
        entry_flow_type="consultation",
        current_flow_type="consultation",
        status="draft",
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    session_record = ConsultationSession(
        id=consultation_session_id,
        encounter_session_id=encounter_session_id,
        user_id=payload.user_id,
        workflow_id=bundle.workflow_id,
        script_bundle=bundle.script_bundle,
        playlist_version=bundle.digital_human_playlist.playlist_version
        or None,
        workflow_stage_id=bundle.consultation_stage_id,
        current_stage_id=first_stage_id,
        current_node_id=first_stage.entry_node,
        status="draft",
        assigned_doctor_persona=persona_id,
        requires_human_review=False,
        participant_profile_snapshot=payload.participant_profile_snapshot,
        context_snapshot=context_snapshot,
        slot_values={},
        engine_state=_default_engine_state(),
        multimodal_session_id=multimodal_session_id,
        multimodal_live_payload={},
        multimodal_live_updated_at=None,
        subtitle_history_payload=[],
        created_at=now,
        updated_at=now,
    )
    _sync_playlist_state(session_record, bundle)

    with get_db_session() as db_session:
        db_session.add(encounter_record)
        db_session.add(session_record)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)


def get_consultation_session(
    session_id: str, acting_user_id: str | None
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        _sync_playlist_state(session_record, bundle)
        db_session.flush()
        return _serialize_session(session_record, bundle)


def start_consultation_session(
    session_id: str, acting_user_id: str | None
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        if session_record.status not in {"draft", "running"}:
            raise ConsultationServiceError(
                "consultation session cannot be started in current status",
                code=4091,
                status_code=409,
            )
        if not session_record.started_at:
            session_record.started_at = _now()
        session_record.status = "running"
        session_record.updated_at = _now()
        if session_record.encounter_session is not None:
            session_record.encounter_session.status = "in_progress"
            session_record.encounter_session.started_at = (
                session_record.encounter_session.started_at or session_record.started_at
            )
            session_record.encounter_session.updated_at = _now()
        _auto_advance(session_record, bundle)
        _sync_playlist_state(session_record, bundle)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)


def complete_system_question_item(
    session_id: str,
    question_key: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        if (
            session_record.status != "waiting_system_completion"
            or not session_record.current_stage_id
            or not session_record.current_node_id
        ):
            raise ConsultationServiceError(
                "consultation session is not waiting for system completion",
                code=4093,
                status_code=409,
            )

        stage = bundle.stage_scripts[session_record.current_stage_id]
        node = stage.nodes[session_record.current_node_id]
        current_question_item = _resolve_current_question_item_object(
            session_record, bundle
        )
        if (
            not current_question_item
            or current_question_item.question_key != question_key
        ):
            raise ConsultationServiceError(
                "system question item mismatch", code=4008, status_code=409
            )
        if current_question_item.response_required:
            raise ConsultationServiceError(
                "question item requires user response and cannot be "
                "auto-completed",
                code=4094,
                status_code=409,
            )
        if node.type != "speak_then_complete":
            raise ConsultationServiceError(
                "current node does not support system completion",
                code=4095,
                status_code=409,
            )

        session_record.status = "running"
        session_record.updated_at = _now()
        engine_state = _ensure_json_dict(session_record.engine_state)
        engine_state["last_branch_taken"] = "system_complete"
        session_record.engine_state = engine_state

        _move_to_target(session_record, node.payload.get("next"), bundle)
        _auto_advance(session_record, bundle)
        _sync_playlist_state(session_record, bundle)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)


def submit_consultation_turn(
    session_id: str,
    payload: ConsultationTurnRequest,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        if (
            session_record.status != "waiting_user_input"
            or not session_record.current_stage_id
            or not session_record.current_node_id
        ):
            raise ConsultationServiceError(
                "consultation session is not waiting for user input",
                code=4092,
                status_code=409,
            )

        stage = bundle.stage_scripts[session_record.current_stage_id]
        node = stage.nodes[session_record.current_node_id]
        branch_name = _infer_branch(payload)
        branch_payload = node.payload.get("branches", {}).get(branch_name)
        if not branch_payload:
            raise ConsultationServiceError(
                "consultation branch missing", code=4007
            )

        normalized_text = _normalize_text(
            payload.raw_input, payload.transcript_text, payload.input_type
        )
        transcript_source = _resolve_transcript_source(payload)
        extracted_fields = _apply_extraction(
            session_record, node, normalized_text
        )
        current_question_item = _resolve_current_question_item_object(
            session_record, bundle
        )
        turn_timestamp = _now()
        response_started_at, response_completed_at = _resolve_response_window(
            payload
        )
        active_prompt_text = _ensure_json_dict(
            session_record.engine_state
        ).get("current_prompt")
        turn_index = (
            db_session.query(ConsultationTurn)
            .filter(ConsultationTurn.session_id == session_record.id)
            .count()
            + 1
        )
        active_turn_id = _get_active_turn_id(session_record)
        requested_turn_id = (payload.turn_id or "").strip() or None
        if (
            active_turn_id
            and requested_turn_id
            and requested_turn_id != active_turn_id
        ):
            raise ConsultationServiceError(
                "consultation turn id mismatch",
                code=4096,
                status_code=409,
            )
        turn_id = requested_turn_id or active_turn_id or str(uuid.uuid4())

        consultation_turn = ConsultationTurn(
            id=turn_id,
            encounter_session_id=session_record.encounter_session_id,
            consultation_flow_run_id=session_record.id,
            session_id=session_record.id,
            stage_id=session_record.current_stage_id,
            node_id=session_record.current_node_id,
            turn_index=turn_index,
            question_key=current_question_item.question_key
            if current_question_item
            else None,
            question_order=current_question_item.order
            if current_question_item
            else None,
            question_video_asset_id=current_question_item.video_asset_id
            if current_question_item
            else None,
            question_video_uri=current_question_item.video_uri
            if current_question_item
            else None,
            question_text=current_question_item.question_text
            if current_question_item
            else active_prompt_text,
            question_subtitle_text=(
                (
                    current_question_item.subtitle_text
                    or current_question_item.question_text
                )
                if current_question_item
                else active_prompt_text
            ),
            input_type=payload.input_type,
            prompt_text=active_prompt_text,
            raw_input=payload.raw_input,
            audio_uri=payload.audio_uri,
            transcript_text=payload.transcript_text,
            transcript_source=transcript_source,
            structured_fields=extracted_fields or None,
            turn_summary_payload=None,
            branch_taken=branch_name,
            turn_window_started_at=response_started_at,
            turn_window_completed_at=response_completed_at,
            response_started_at=response_started_at,
            response_completed_at=response_completed_at,
            created_at=turn_timestamp,
        )
        db_session.add(consultation_turn)
        _finalize_user_subtitle_entry(
            session_record,
            prompt_key=current_question_item.question_key
            if current_question_item
            else session_record.current_question_key,
            transcript_text=normalized_text,
            turn_id=turn_id,
            source=transcript_source,
        )

        multimodal_session_id = (
            str(session_record.multimodal_session_id or "").strip() or None
        )
        if payload.input_type == "speech" and not multimodal_session_id:
            multimodal_session_id = _ensure_multimodal_session_binding(
                session_record,
                acting_user_id=acting_user_id,
            )

        if multimodal_session_id:
            _refresh_multimodal_live_snapshot(
                session_record,
                acting_user_id=acting_user_id,
            )
            turn_bundle_payload = _extract_optional_upstream_data(
                fetch_upstream_multimodal_turn_bundle(
                    multimodal_session_id=multimodal_session_id,
                    turn_id=turn_id,
                    acting_user_id=acting_user_id,
                ),
                error_code=5025,
                allowed_statuses={404},
            )
            consultation_turn.turn_summary_payload = turn_bundle_payload
            _clear_pose_turn_runtime_best_effort(
                multimodal_session_id=multimodal_session_id,
                turn_id=turn_id,
                acting_user_id=acting_user_id,
            )

        _clear_active_turn(session_record)
        session_record.status = "running"
        session_record.updated_at = _now()
        engine_state = _ensure_json_dict(session_record.engine_state)
        engine_state["last_branch_taken"] = branch_name
        session_record.engine_state = engine_state

        _move_to_target(session_record, branch_payload.get("next"), bundle)
        _auto_advance(session_record, bundle)
        _sync_playlist_state(session_record, bundle)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)


def get_consultation_multimodal_live(
    session_id: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        live_data = _refresh_multimodal_live_snapshot(
            session_record,
            acting_user_id=acting_user_id,
        )
        db_session.flush()
        return live_data


def get_consultation_turn_multimodal_bundle(
    session_id: str,
    turn_id: str,
    acting_user_id: str | None,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        consultation_turn = db_session.get(ConsultationTurn, turn_id)
        if not consultation_turn or consultation_turn.session_id != session_record.id:
            raise ConsultationServiceError(
                "consultation turn not found", code=4043, status_code=404
            )
        if consultation_turn.turn_summary_payload:
            return consultation_turn.turn_summary_payload
        multimodal_session_id = _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        bundle_data = _extract_upstream_data(
            fetch_upstream_multimodal_turn_bundle(
                multimodal_session_id=multimodal_session_id,
                turn_id=consultation_turn.id,
                acting_user_id=acting_user_id,
            ),
            error_code=5025,
        )
        consultation_turn.turn_summary_payload = bundle_data
        db_session.add(consultation_turn)
        db_session.flush()
        return bundle_data


def submit_consultation_visual_capture(
    session_id: str,
    *,
    question_key: str,
    turn_id: str | None,
    sample_started_at: str,
    sample_ended_at: str,
    sample_index: int,
    mime_type: str,
    filename: str,
    file_bytes: bytes,
    acting_user_id: str | None,
) -> dict[str, Any]:
    return _submit_consultation_frame_capture(
        session_id,
        question_key=question_key,
        turn_id=turn_id,
        sample_started_at=sample_started_at,
        sample_ended_at=sample_ended_at,
        sample_index=sample_index,
        mime_type=mime_type,
        filename=filename,
        file_bytes=file_bytes,
        acting_user_id=acting_user_id,
        submit_upstream_capture=submit_upstream_visual_capture,
        error_code=5028,
    )


def _submit_consultation_frame_capture(
    session_id: str,
    *,
    question_key: str,
    turn_id: str | None,
    sample_started_at: str,
    sample_ended_at: str,
    sample_index: int,
    mime_type: str,
    filename: str,
    file_bytes: bytes,
    acting_user_id: str | None,
    submit_upstream_capture: Callable[..., dict[str, Any]],
    error_code: int,
) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError(
                "consultation session forbidden", code=4032, status_code=403
            )
        multimodal_session_id = _ensure_multimodal_session_binding(
            session_record,
            acting_user_id=acting_user_id,
        )
        capture_data = _extract_upstream_data(
            submit_upstream_capture(
                multimodal_session_id=multimodal_session_id,
                flow_run_id=session_record.id,
                question_key=question_key,
                stage_id=session_record.current_stage_id,
                turn_id=turn_id,
                sample_started_at=sample_started_at,
                sample_ended_at=sample_ended_at,
                sample_index=sample_index,
                mime_type=mime_type,
                file_bytes=file_bytes,
                filename=filename,
                acting_user_id=acting_user_id,
            ),
            error_code=error_code,
        )
        if turn_id:
            consultation_turn = db_session.get(ConsultationTurn, turn_id)
            if consultation_turn and consultation_turn.session_id == session_record.id:
                consultation_turn.turn_summary_payload = capture_data.get("turn_bundle")
                db_session.add(consultation_turn)
        db_session.flush()
        return capture_data
