from __future__ import annotations

import uuid

from app.models import ConsultationSession
from app.services.consultation import (
    ConsultationServiceError,
    _ensure_json_dict,
    _ensure_json_list,
    _now,
)
from app.services.consultation._session_state import (
    _build_chief_complaint_result,
    _build_current_history_result,
    _build_digital_human_consultation_summary,
    _build_high_risk_result,
    _build_scale_handoff_payload,
    _evaluate_decision,
    _render_prompt,
    _resolve_current_question_item_object,
    _resolve_route,
    _set_current_prompt,
)
from app.services.workflow_loader import WorkflowBundle


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
        else session_record.current_question_key
        or session_record.current_node_id
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

    if completed_stage_id == "stage-02-chief-complaint":
        _build_chief_complaint_result(session_record)
    if completed_stage_id == "stage-03-symptom-screening":
        _build_current_history_result(session_record)
    if completed_stage_id == "stage-04-high-risk-screening":
        high_risk_branch = (
            "human_intervention_required"
            if session_record.requires_human_review
            else "safe_to_continue"
        )
        _build_high_risk_result(session_record, high_risk_branch)
        _build_digital_human_consultation_summary(session_record)

    encounter_session = session_record.encounter_session
    if (
        completed_stage_id == "stage-04-high-risk-screening"
        and session_record.requires_human_review
    ):
        session_record.workflow_stage_id = "clinical-decision"
        session_record.status = "paused_for_human_review"
        if encounter_session is not None:
            encounter_session.current_flow_type = "consultation"
            encounter_session.status = "completed"
            encounter_session.completed_at = _now()
            encounter_session.updated_at = _now()
        session_record.current_stage_id = None
        session_record.current_node_id = None
        session_record.completed_at = _now()
        return

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
        if encounter_session is not None:
            encounter_session.current_flow_type = "consultation"
            encounter_session.status = "completed"
            encounter_session.completed_at = _now()
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
