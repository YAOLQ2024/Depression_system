from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models import ConsultationSession, ConsultationTurn
from app.schemas.consultations import ConsultationTurnRequest, CreateConsultationSessionRequest
from app.services.workflow_loader import ScriptNode, WorkflowBundle, get_workflow_loader


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


def _default_engine_state() -> dict[str, Any]:
    return {
        "current_prompt": None,
        "waiting_node_type": None,
        "completed_stages": [],
        "last_branch_taken": None,
    }


def _render_prompt(node: ScriptNode, slot_values: dict[str, Any]) -> str:
    template = node.payload.get("template_prompt") or node.payload.get("prompt") or ""

    def replace_token(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        value = slot_values.get(key)
        if isinstance(value, list):
            return "、".join(str(item) for item in value)
        if value is None:
            return "暂未明确"
        return str(value)

    return re.sub(r"\{\{\s*([^}]+)\s*\}\}", replace_token, template)


def _normalize_text(raw_input: str | None, transcript_text: str | None, input_type: str) -> str:
    if transcript_text and transcript_text.strip():
        return transcript_text.strip()
    if raw_input and raw_input.strip():
        return raw_input.strip()
    if input_type == "continue_button":
        return "继续"
    return ""


def _extract_chief_complaint_keywords(text: str) -> list[str]:
    normalized = text.lower()
    keywords: list[str] = []
    if any(token in normalized for token in ["睡", "失眠", "早醒", "入睡", "夜醒"]):
        keywords.append("sleep")
    if any(token in normalized for token in ["情绪", "低落", "难过", "抑郁", "没兴趣", "提不起劲", "累", "空"]):
        keywords.append("mood")
    if any(token in normalized for token in ["紧张", "焦虑", "害怕", "心慌", "担心", "放松不下来"]):
        keywords.append("anxiety")
    return keywords or ["general"]


def _build_summary(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= 80:
        return compact
    return f"{compact[:77]}..."


def _parse_positive_negative(text: str) -> str:
    if any(token in text for token in ["没有", "没", "不会", "不是", "无", "从未"]):
        return "negative"
    if any(token in text for token in ["有", "想过", "出现过", "是", "会", "差点", "真的"]):
        return "positive"
    return "unclear"


def _parse_support_state(text: str) -> str:
    if any(token in text for token in ["没有", "无人", "一个人", "没人", "无"]):
        return "none"
    if any(token in text for token in ["有限", "不太方便", "有时候", "不一定", "不稳定"]):
        return "limited"
    if any(token in text for token in ["有", "可以", "能", "有人", "家人", "朋友", "老师", "同事"]):
        return "available"
    return "unclear"


def _extract_risk_value(slot_name: str, text: str) -> str:
    if slot_name == "acute_support_state":
        return _parse_support_state(text)
    return _parse_positive_negative(text)


def _set_slot(session_record: ConsultationSession, slot_name: str, value: Any) -> None:
    slot_values = _ensure_json_dict(session_record.slot_values)
    slot_values[slot_name] = value
    session_record.slot_values = slot_values


def _apply_extraction(session_record: ConsultationSession, node: ScriptNode, text: str) -> dict[str, Any]:
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


def _resolve_route(session_record: ConsultationSession, node: ScriptNode) -> str:
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
        return all(_evaluate_condition(slot_values, part) for part in expression.split(" and "))
    if " in [" in expression:
        left, right = expression.split(" in [", 1)
        slot_name = left.strip()
        candidates = [item.strip() for item in right.rstrip("]").split(",")]
        return str(slot_values.get(slot_name)) in candidates
    if "==" in expression:
        left, right = expression.split("==", 1)
        return str(slot_values.get(left.strip())) == right.strip()
    return False


def _evaluate_decision(session_record: ConsultationSession, node: ScriptNode) -> str:
    slot_values = _ensure_json_dict(session_record.slot_values)
    rules = node.payload.get("decision_rules", {})
    for branch_name, rule_payload in rules.items():
        if branch_name == "safe_to_continue" and rule_payload.get("default") is True:
            continue
        any_conditions = rule_payload.get("any", [])
        if any(_evaluate_condition(slot_values, expression) for expression in any_conditions):
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


def _build_high_risk_result(session_record: ConsultationSession, branch_name: str) -> None:
    slot_values = _ensure_json_dict(session_record.slot_values)
    alert_level = "high" if branch_name == "human_intervention_required" else "low"
    session_record.high_risk_screening_result = {
        "suicidal_ideation": slot_values.get("suicidal_ideation", "unclear"),
        "self_harm_behavior": slot_values.get("self_harm_behavior", "unclear"),
        "suicide_plan": slot_values.get("suicide_plan", "unclear"),
        "acute_support_state": slot_values.get("acute_support_state", "unclear"),
        "alert_level": alert_level,
        "outcome": branch_name,
    }
    session_record.requires_human_review = branch_name == "human_intervention_required"


def _build_scale_handoff_payload(session_record: ConsultationSession, bundle: WorkflowBundle) -> dict[str, Any]:
    return {
        "workflow_id": bundle.workflow_id,
        "session_id": session_record.id,
        "chief_complaint_summary": session_record.chief_complaint_summary,
        "current_history_structured_result": session_record.current_history_structured_result or {},
        "high_risk_screening_result": session_record.high_risk_screening_result or {},
        "required_scales": bundle.required_scales,
    }


def _set_current_prompt(session_record: ConsultationSession, prompt: str | None, waiting_node_type: str | None) -> None:
    engine_state = _ensure_json_dict(session_record.engine_state)
    engine_state["current_prompt"] = prompt
    engine_state["waiting_node_type"] = waiting_node_type
    session_record.engine_state = engine_state


def _mark_stage_completed(session_record: ConsultationSession, stage_id: str) -> None:
    engine_state = _ensure_json_dict(session_record.engine_state)
    completed = _ensure_json_list(engine_state.get("completed_stages"))
    if stage_id not in completed:
        completed.append(stage_id)
    engine_state["completed_stages"] = completed
    session_record.engine_state = engine_state


def _move_to_target(session_record: ConsultationSession, target: str | None, bundle: WorkflowBundle) -> None:
    if target == "stage-complete":
        _advance_stage(session_record, bundle)
        return
    session_record.current_node_id = target


def _advance_stage(session_record: ConsultationSession, bundle: WorkflowBundle) -> None:
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

    if session_record.requires_human_review:
        session_record.workflow_stage_id = "clinical-decision"
        session_record.status = "paused_for_human_review"
    else:
        session_record.workflow_stage_id = bundle.scale_stage_id
        session_record.status = "handoff_ready"
        session_record.scale_handoff_payload = _build_scale_handoff_payload(session_record, bundle)

    session_record.current_stage_id = None
    session_record.current_node_id = None
    session_record.completed_at = _now()


def _auto_advance(session_record: ConsultationSession, bundle: WorkflowBundle) -> None:
    while session_record.current_stage_id and session_record.current_node_id:
        stage = bundle.stage_scripts[session_record.current_stage_id]
        node = stage.nodes[session_record.current_node_id]

        if node.type == "system_gate":
            checks = node.payload.get("checks", [])
            context_snapshot = _ensure_json_dict(session_record.context_snapshot)
            missing = [check for check in checks if not context_snapshot.get(check)]
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
                raise ConsultationServiceError("consultation route target missing", code=5002, status_code=500)
            _move_to_target(session_record, target, bundle)
            continue

        if node.type == "decision":
            branch_name = _evaluate_decision(session_record, node)
            if node.id == "evaluate-high-risk":
                _build_high_risk_result(session_record, branch_name)
            target = node.payload.get("branches", {}).get(branch_name)
            if not target:
                raise ConsultationServiceError("consultation decision branch missing", code=5003, status_code=500)
            engine_state = _ensure_json_dict(session_record.engine_state)
            engine_state["last_branch_taken"] = branch_name
            session_record.engine_state = engine_state
            _move_to_target(session_record, target, bundle)
            continue

        if node.type == "speak_then_wait":
            prompt = _render_prompt(node, _ensure_json_dict(session_record.slot_values))
            session_record.status = "waiting_user_input"
            _set_current_prompt(session_record, prompt, node.type)
            return

        raise ConsultationServiceError(f"unsupported node type: {node.type}", code=5001, status_code=500)


def _infer_branch(payload: ConsultationTurnRequest) -> str:
    if payload.input_type == "silence":
        return "silence"
    if payload.input_type == "recognition_failure":
        return "recognition_failure"
    return "normal"


def _serialize_session(session_record: ConsultationSession, bundle: WorkflowBundle) -> dict[str, Any]:
    engine_state = _ensure_json_dict(session_record.engine_state)
    current_prompt = engine_state.get("current_prompt")
    return {
        "session_id": session_record.id,
        "user_id": session_record.user_id,
        "workflow_id": session_record.workflow_id,
        "script_bundle": session_record.script_bundle,
        "workflow_stage_id": session_record.workflow_stage_id,
        "current_stage_id": session_record.current_stage_id,
        "current_node_id": session_record.current_node_id,
        "status": session_record.status,
        "assigned_doctor_persona": session_record.assigned_doctor_persona,
        "requires_human_review": session_record.requires_human_review,
        "current_prompt": current_prompt,
        "participant_profile_snapshot": _ensure_json_dict(session_record.participant_profile_snapshot),
        "slot_values": _ensure_json_dict(session_record.slot_values),
        "chief_complaint_summary": session_record.chief_complaint_summary,
        "current_history_structured_result": session_record.current_history_structured_result or {},
        "high_risk_screening_result": session_record.high_risk_screening_result or {},
        "scale_handoff_payload": session_record.scale_handoff_payload or {},
        "required_scales": bundle.required_scales,
        "created_at": session_record.created_at.isoformat(),
        "updated_at": session_record.updated_at.isoformat(),
        "started_at": session_record.started_at.isoformat() if session_record.started_at else None,
        "completed_at": session_record.completed_at.isoformat() if session_record.completed_at else None,
    }


def _get_session_or_raise(db_session: Session, session_id: str) -> ConsultationSession:
    session_record = db_session.get(ConsultationSession, session_id)
    if not session_record:
        raise ConsultationServiceError("consultation session not found", code=4041, status_code=404)
    return session_record


def _require_acting_user_id(acting_user_id: str | None) -> str:
    if not acting_user_id:
        raise ConsultationServiceError("missing acting user id", code=4013, status_code=401)
    return acting_user_id


def create_consultation_session(payload: CreateConsultationSessionRequest, acting_user_id: str | None) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    if payload.user_id != acting_user_id:
        raise ConsultationServiceError("user mismatch for consultation creation", code=4031, status_code=403)
    bundle = get_workflow_loader().load_bundle()
    persona_id = payload.assigned_doctor_persona or get_workflow_loader().default_persona
    if persona_id not in bundle.doctor_personas:
        raise ConsultationServiceError("doctor persona not found", code=4006, status_code=404)

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
    session_record = ConsultationSession(
        id=str(uuid.uuid4()),
        user_id=payload.user_id,
        workflow_id=bundle.workflow_id,
        script_bundle=bundle.script_bundle,
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
        created_at=now,
        updated_at=now,
    )

    with get_db_session() as db_session:
        db_session.add(session_record)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)


def get_consultation_session(session_id: str, acting_user_id: str | None) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError("consultation session forbidden", code=4032, status_code=403)
        return _serialize_session(session_record, bundle)


def start_consultation_session(session_id: str, acting_user_id: str | None) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError("consultation session forbidden", code=4032, status_code=403)
        if session_record.status not in {"draft", "running"}:
            raise ConsultationServiceError("consultation session cannot be started in current status", code=4091, status_code=409)
        if not session_record.started_at:
            session_record.started_at = _now()
        session_record.status = "running"
        session_record.updated_at = _now()
        _auto_advance(session_record, bundle)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)


def submit_consultation_turn(session_id: str, payload: ConsultationTurnRequest, acting_user_id: str | None) -> dict[str, Any]:
    acting_user_id = _require_acting_user_id(acting_user_id)
    bundle = get_workflow_loader().load_bundle()
    with get_db_session() as db_session:
        session_record = _get_session_or_raise(db_session, session_id)
        if session_record.user_id != acting_user_id:
            raise ConsultationServiceError("consultation session forbidden", code=4032, status_code=403)
        if session_record.status != "waiting_user_input" or not session_record.current_stage_id or not session_record.current_node_id:
            raise ConsultationServiceError("consultation session is not waiting for user input", code=4092, status_code=409)

        stage = bundle.stage_scripts[session_record.current_stage_id]
        node = stage.nodes[session_record.current_node_id]
        branch_name = _infer_branch(payload)
        branch_payload = node.payload.get("branches", {}).get(branch_name)
        if not branch_payload:
            raise ConsultationServiceError("consultation branch missing", code=4007)

        normalized_text = _normalize_text(payload.raw_input, payload.transcript_text, payload.input_type)
        extracted_fields = _apply_extraction(session_record, node, normalized_text)

        db_session.add(
            ConsultationTurn(
                id=str(uuid.uuid4()),
                session_id=session_record.id,
                workflow_stage_id=session_record.workflow_stage_id,
                stage_id=session_record.current_stage_id,
                node_id=session_record.current_node_id,
                input_type=payload.input_type,
                prompt_text=_ensure_json_dict(session_record.engine_state).get("current_prompt"),
                raw_input=payload.raw_input,
                transcript_text=payload.transcript_text,
                structured_fields=extracted_fields or None,
                branch_taken=branch_name,
                created_at=_now(),
            )
        )

        session_record.status = "running"
        session_record.updated_at = _now()
        engine_state = _ensure_json_dict(session_record.engine_state)
        engine_state["last_branch_taken"] = branch_name
        session_record.engine_state = engine_state

        _move_to_target(session_record, branch_payload.get("next"), bundle)
        _auto_advance(session_record, bundle)
        db_session.flush()
        db_session.refresh(session_record)
        return _serialize_session(session_record, bundle)
