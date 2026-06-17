from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.services.consultation._session_state import (
    _apply_extraction,
    _count_remaining_prompt_items,
    _record_completed_question_key,
    _resolve_prompt_progress,
)
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
        "completed_at": None,
        "requires_human_review": False,
        "chief_complaint_raw_text": None,
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
            "suicide_plan": "positive",
            "self_harm_behavior": "negative",
        },
        current_stage_id="stage-04-high-risk-screening",
        current_node_id="evaluate-after-plan-or-action",
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
    assert total_prompt_count == 12
