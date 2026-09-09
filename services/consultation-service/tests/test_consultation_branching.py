from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.services.consultation._session_state import (
    _apply_extraction,
    _build_high_risk_result,
    _count_remaining_prompt_items,
    _evaluate_decision,
    _record_completed_question_key,
    _resolve_prompt_progress,
)
from app.services.consultation._workflow_runtime import _advance_stage
from app.services.workflow_loader import WorkflowLoader


RESOURCE_ROOT = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "workflow-resources"
)


def _load_bundle():
    loader = WorkflowLoader(
        resources_dir=RESOURCE_ROOT,
        workflow_id="consultation-v1",
        script_bundle="rule-v1",
        default_persona="doctor-a-calm-female",
    )
    return loader.load_bundle()


def _build_session(**overrides):
    payload = {
        "slot_values": {},
        "engine_state": {},
        "subtitle_history_payload": [],
        "current_stage_id": "stage-02-chief-complaint",
        "current_node_id": "ask-chief-complaint-001",
        "current_question_key": None,
        "current_question_order": None,
        "current_question_video_asset_id": None,
        "current_question_video_uri": None,
        "current_question_text": None,
        "current_question_subtitle_text": None,
        "playlist_version": None,
        "total_prompt_count": 0,
        "completed_prompt_count": 0,
        "status": "running",
        "workflow_stage_id": None,
        "scale_handoff_payload": None,
        "completed_at": None,
        "requires_human_review": False,
        "chief_complaint_raw_text": None,
        "chief_complaint_summary": None,
        "current_history_structured_result": {},
        "high_risk_screening_result": {},
        "encounter_session": None,
        "id": "test-consultation-session",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_chief_complaint_entry_parse_marks_no_clear_problem() -> None:
    bundle = _load_bundle()
    node = bundle.stage_scripts["stage-02-chief-complaint"].nodes[
        "ask-chief-complaint-001"
    ]
    session_record = _build_session()
    transcript = "我一下子说不上来，就是想做个状态评估，家里人建议我来看看。"

    extracted = _apply_extraction(session_record, node, transcript)

    assert extracted["chief_complaint_text"] == transcript
    assert extracted["chief_complaint_route"] == "no_clear_problem"
    assert session_record.slot_values["chief_complaint_text"] == transcript
    assert session_record.slot_values["chief_complaint_route"] == "no_clear_problem"
    assert session_record.chief_complaint_raw_text == transcript


def test_chief_complaint_entry_parse_keeps_clear_problem_when_symptoms_present() -> None:
    bundle = _load_bundle()
    node = bundle.stage_scripts["stage-02-chief-complaint"].nodes[
        "ask-chief-complaint-001"
    ]
    session_record = _build_session()
    transcript = "没什么大问题，就是最近一直失眠、焦虑，晚上总是睡不好。"

    extracted = _apply_extraction(session_record, node, transcript)

    assert extracted["chief_complaint_route"] == "clear_problem"


def test_remaining_prompt_count_skips_to_primary_concern_when_risk_is_negative() -> None:
    bundle = _load_bundle()
    session_record = _build_session(
        slot_values={"suicidal_ideation": "negative"},
        current_stage_id="stage-04-high-risk-screening",
        current_node_id="evaluate-after-suicidal-ideation",
    )

    remaining_prompt_count = _count_remaining_prompt_items(session_record, bundle)

    assert remaining_prompt_count == 2


def test_remaining_prompt_count_stops_after_high_risk_alert() -> None:
    bundle = _load_bundle()
    session_record = _build_session(
        slot_values={
            "suicidal_ideation": "positive",
            "suicide_means_preparation": "positive",
            "suicide_plan": "positive",
            "self_harm_behavior": "negative",
            "high_risk_confirmation_outcome": "confirmed",
        },
        current_stage_id="stage-04-high-risk-screening",
        current_node_id="evaluate-high-risk",
    )

    remaining_prompt_count = _count_remaining_prompt_items(session_record, bundle)

    assert remaining_prompt_count == 1


def test_prompt_progress_uses_actual_path_with_branch_video() -> None:
    bundle = _load_bundle()
    session_record = _build_session(
        slot_values={"chief_complaint_route": "no_clear_problem"},
        current_stage_id="stage-02-chief-complaint",
        current_node_id="ask-chief-complaint-no-clear-problem",
    )
    _record_completed_question_key(session_record, "greeting-001")
    _record_completed_question_key(session_record, "chief-complaint-001")

    completed_prompt_count, total_prompt_count = _resolve_prompt_progress(
        session_record, bundle
    )

    assert completed_prompt_count == 2
    assert total_prompt_count == 10


def test_high_risk_review_requires_two_positive_answers() -> None:
    bundle = _load_bundle()
    node = bundle.stage_scripts["stage-04-high-risk-screening"].nodes[
        "evaluate-high-risk"
    ]
    session_record = _build_session(
        slot_values={
            "suicidal_ideation": "positive",
            "suicide_means_preparation": "negative",
            "suicide_farewell_behavior": "positive",
            "suicide_plan": "negative",
            "high_risk_confirmation_outcome": "confirmed",
        },
        current_stage_id="stage-04-high-risk-screening",
        current_node_id="evaluate-high-risk",
    )

    branch_name = _evaluate_decision(session_record, node)

    assert branch_name == "human_intervention_required"


def test_direct_suicidal_statement_enters_review_branch() -> None:
    bundle = _load_bundle()
    question_node = bundle.stage_scripts[
        "stage-04-high-risk-screening"
    ].nodes["ask-suicidal-ideation"]
    decision_node = bundle.stage_scripts[
        "stage-04-high-risk-screening"
    ].nodes["evaluate-after-suicidal-ideation"]
    session_record = _build_session(
        current_stage_id="stage-04-high-risk-screening",
        current_node_id="ask-suicidal-ideation",
    )

    extracted = _apply_extraction(session_record, question_node, "我想自杀")
    branch_name = _evaluate_decision(session_record, decision_node)

    assert extracted["suicidal_ideation"] == "positive"
    assert branch_name == "enter-review-branch"


def test_negated_suicidal_statement_stays_negative() -> None:
    bundle = _load_bundle()
    question_node = bundle.stage_scripts[
        "stage-04-high-risk-screening"
    ].nodes["ask-suicidal-ideation"]
    session_record = _build_session(
        current_stage_id="stage-04-high-risk-screening",
        current_node_id="ask-suicidal-ideation",
    )

    extracted = _apply_extraction(session_record, question_node, "我不想自杀")

    assert extracted["suicidal_ideation"] == "negative"


def test_high_risk_false_positive_is_downgraded_after_review() -> None:
    session_record = _build_session(
        slot_values={
            "suicidal_ideation": "positive",
            "suicide_means_preparation": "negative",
            "suicide_farewell_behavior": "negative",
            "suicide_plan": "negative",
        }
    )

    _build_high_risk_result(session_record, "safe_to_continue")

    assert session_record.high_risk_screening_result["positive_count"] == 1
    assert (
        session_record.high_risk_screening_result["confirmation_outcome"]
        == "not_confirmed"
    )
    assert (
        session_record.high_risk_screening_result["suicidal_ideation"]
        == "negative"
    )


def test_high_risk_human_review_marks_encounter_completed() -> None:
    bundle = _load_bundle()
    encounter_session = SimpleNamespace(
        current_flow_type="consultation",
        status="in_progress",
        completed_at=None,
        updated_at=None,
    )
    session_record = _build_session(
        slot_values={
            "suicidal_ideation": "positive",
            "suicide_means_preparation": "positive",
            "suicide_farewell_behavior": "negative",
            "suicide_plan": "negative",
        },
        current_stage_id="stage-04-high-risk-screening",
        current_node_id="high-risk-alert",
        workflow_stage_id="high-risk-screening",
        requires_human_review=True,
        encounter_session=encounter_session,
    )

    _advance_stage(session_record, bundle)

    assert session_record.status == "paused_for_human_review"
    assert session_record.workflow_stage_id == "clinical-decision"
    assert session_record.completed_at is not None
    assert session_record.current_stage_id is None
    assert session_record.current_node_id is None
    assert encounter_session.current_flow_type == "consultation"
    assert encounter_session.status == "completed"
    assert encounter_session.completed_at is not None
