# services/consultation-service/tests/test_encounter_service.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from app.services.encounter_service import (
    EncounterServiceError,
    get_encounter_detail,
    get_scale_score_history,
    list_encounters,
)


def _make_encounter(id, user_id="user-1", status="completed", created_at=None):
    enc = MagicMock()
    enc.id = id
    enc.user_id = user_id
    enc.status = status
    enc.current_flow_type = "consultation"
    enc.created_at = created_at or datetime(2026, 5, 20, 14, 30, tzinfo=timezone.utc)
    enc.completed_at = datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc) if status == "completed" else None
    return enc


def _make_consultation(id, encounter_id, summary="测试主诉"):
    c = MagicMock()
    c.id = id
    c.encounter_session_id = encounter_id
    c.chief_complaint_raw_text = summary
    c.chief_complaint_summary = summary
    c.created_at = datetime(2026, 5, 20, 14, 30, tzinfo=timezone.utc)
    c.started_at = datetime(2026, 5, 20, 14, 31, tzinfo=timezone.utc)
    c.completed_at = datetime(2026, 5, 20, 14, 55, tzinfo=timezone.utc)
    c.assigned_doctor_persona = "doctor-a-calm-female"
    c.slot_values = {
        "chief_complaint_stage_summary": summary,
        "symptom_screening_stage_summary": "近两周持续睡眠不佳并伴随兴趣下降。",
        "high_risk_screening_stage_summary": "当前未见明确急性安全风险信号。",
        "digital_human_consultation_summary": "问诊提示近期抑郁情绪与睡眠问题较突出。",
        "chief_complaint_structured_result": {"mood": "low"},
    }
    c.current_history_structured_result = {
        "sleep_quality": "poor",
        "interest_level": "decreased",
    }
    c.high_risk_screening_result = {
        "suicidal_ideation": "denied",
        "support_system": "available",
    }
    c.scale_handoff_payload = {
        "chief_complaint_stage_summary": summary,
        "symptom_screening_stage_summary": "近两周持续睡眠不佳并伴随兴趣下降。",
        "high_risk_screening_stage_summary": "当前未见明确急性安全风险信号。",
        "digital_human_consultation_summary": "问诊提示近期抑郁情绪与睡眠问题较突出。",
        "required_scales": ["phq9", "sds"],
    }
    c.subtitle_history_payload = [
        {
            "entry_key": "doctor-1",
            "speaker": "doctor",
            "text": "请描述最近两周的状态。",
            "status": "final",
            "sequence": 1,
        },
        {
            "entry_key": "user-1",
            "speaker": "user",
            "text": summary,
            "status": "final",
            "sequence": 2,
        },
    ]
    c.context_snapshot = {"consent_confirmed": True}
    return c


def _scalar_result(values):
    return MagicMock(
        scalars=MagicMock(
            return_value=MagicMock(
                all=MagicMock(return_value=values),
            )
        )
    )


def _mapping_all_result(values):
    mappings_result = MagicMock()
    mappings_result.all.return_value = values
    return MagicMock(mappings=MagicMock(return_value=mappings_result))


def _mapping_first_result(value):
    mappings_result = MagicMock()
    mappings_result.first.return_value = value
    return MagicMock(mappings=MagicMock(return_value=mappings_result))


def _scalar_one_or_none_result(value):
    return MagicMock(scalar_one_or_none=MagicMock(return_value=value))


class TestListEncounters:
    @patch("app.services.encounter_service.get_db_session")
    def test_empty_result(self, mock_db_ctx):
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        result = list_encounters("user-1")
        assert result == {"encounters": [], "next_cursor": None, "has_more": False}

    @patch("app.services.encounter_service.get_db_session")
    def test_single_page(self, mock_db_ctx):
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        enc = _make_encounter("enc-1")
        cons = _make_consultation("cons-1", "enc-1", "情绪低落")

        mock_session.execute.side_effect = [
            _scalar_result([enc]),
            _scalar_result([cons]),
            _mapping_all_result([]),
        ]

        result = list_encounters("user-1")
        assert len(result["encounters"]) == 1
        assert result["encounters"][0]["id"] == "enc-1"
        assert result["encounters"][0]["chief_complaint_summary"] == "情绪低落"
        assert result["has_more"] is False
        assert result["next_cursor"] is None

    @patch("app.services.encounter_service.get_db_session")
    def test_invalid_cursor_raises(self, mock_db_ctx):
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.one_or_none.return_value = None

        with pytest.raises(EncounterServiceError) as exc_info:
            list_encounters("user-1", cursor="nonexistent")
        assert exc_info.value.status_code == 400

    @patch("app.services.encounter_service.get_db_session")
    def test_has_more_with_cursor(self, mock_db_ctx):
        """When limit=1 and there are 2 encounters, has_more=True and next_cursor is set."""
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        enc1 = _make_encounter("enc-1", created_at=datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc))
        enc2 = _make_encounter("enc-2", created_at=datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc))

        # limit+1 = 2 rows returned -> has_more=True
        mock_session.execute.side_effect = [
            _scalar_result([enc1, enc2]),
            _scalar_result([]),
            _mapping_all_result([]),
        ]

        result = list_encounters("user-1", limit=1)
        assert len(result["encounters"]) == 1
        assert result["encounters"][0]["id"] == "enc-1"
        assert result["has_more"] is True
        assert result["next_cursor"] == "enc-1"

    @patch("app.services.encounter_service.get_db_session")
    def test_multiple_encounters_with_consultations(self, mock_db_ctx):
        """Multiple encounters each with their own consultation exercises the consultation map logic."""
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        enc1 = _make_encounter("enc-1", created_at=datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc))
        enc2 = _make_encounter("enc-2", created_at=datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc))
        cons1 = _make_consultation("cons-1", "enc-1", "情绪低落")
        cons2 = _make_consultation("cons-2", "enc-2", "失眠焦虑")

        mock_session.execute.side_effect = [
            _scalar_result([enc1, enc2]),
            _scalar_result([cons1, cons2]),
            _mapping_all_result([]),
        ]

        result = list_encounters("user-1")
        assert len(result["encounters"]) == 2

        by_id = {e["id"]: e for e in result["encounters"]}
        assert by_id["enc-1"]["chief_complaint_summary"] == "情绪低落"
        assert by_id["enc-2"]["chief_complaint_summary"] == "失眠焦虑"
        assert by_id["enc-1"]["consultation_session_id"] == "cons-1"
        assert by_id["enc-2"]["consultation_session_id"] == "cons-2"
        assert result["has_more"] is False

    @patch("app.services.encounter_service.get_db_session")
    def test_list_includes_assessment_resume_and_scores(self, mock_db_ctx):
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        enc = _make_encounter("enc-1", status="in_progress")
        enc.current_flow_type = "assessment"
        cons = _make_consultation("cons-1", "enc-1", "情绪低落")
        assessment_row = {
            "id": "assess-1",
            "encounter_session_id": "enc-1",
            "aggregate_payload": {
                "scale_result_map": {
                    "phq9": {
                        "raw_score": 15,
                        "interpretation_level": "moderate",
                    }
                },
                "risk_summary": {
                    "risk_level": "medium",
                },
            },
            "created_at": datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc),
            "started_at": datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc),
            "completed_at": None,
            "status": "in_progress",
        }

        mock_session.execute.side_effect = [
            _scalar_result([enc]),
            _scalar_result([cons]),
            _mapping_all_result([assessment_row]),
        ]

        result = list_encounters("user-1")
        assert result["encounters"][0]["assessment_session_id"] == "assess-1"
        assert result["encounters"][0]["phq9_score"] == 15
        assert result["encounters"][0]["phq9_risk_level"] == "moderate"
        assert result["encounters"][0]["overall_risk_level"] == "medium"


class TestGetEncounterDetail:
    @patch("app.services.encounter_service.get_db_session")
    def test_detail_includes_assessment_without_model_imports(self, mock_db_ctx):
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        enc = _make_encounter("enc-1")
        enc.started_at = datetime(2026, 5, 20, 14, 30, tzinfo=timezone.utc)
        cons = _make_consultation("cons-1", "enc-1", "情绪低落")
        assessment_row = {
            "id": "assess-1",
            "encounter_session_id": "enc-1",
            "status": "completed",
            "aggregate_payload": {
                "risk_summary": {
                    "risk_level": "medium",
                    "risk_level_label": "中风险",
                },
                "scale_result_map": {
                    "phq9": {
                        "scale_slug": "phq9",
                        "raw_score": 15,
                        "derived_score": 15,
                        "normalized_score": 56,
                        "interpretation_level": "moderate",
                        "interpretation_label": "中度抑郁",
                        "score_details": {
                            "normalization": {
                                "maximum": 27,
                            }
                        },
                    }
                },
            },
            "scale_handoff_payload": {
                "required_scales": ["phq9", "sds"],
            },
            "required_scales": ["phq9", "sds"],
            "selected_scales": ["phq9"],
            "source_consultation_flow_run_id": "cons-1",
            "multimodal_session_id": "mm-1",
            "created_at": datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc),
            "started_at": datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc),
            "completed_at": datetime(2026, 5, 20, 15, 10, tzinfo=timezone.utc),
        }
        assessment_result_row = {
            "scale_slug": "phq9",
            "raw_score": 15,
            "derived_score": 15,
            "interpretation_level": "moderate",
            "interpretation_label": "中度抑郁",
            "risk_flags": [{"flag": "moderate_depression"}],
            "completed_at": datetime(2026, 5, 20, 15, 10, tzinfo=timezone.utc),
            "created_at": datetime(2026, 5, 20, 15, 10, tzinfo=timezone.utc),
        }

        mock_session.execute.side_effect = [
            _scalar_one_or_none_result(enc),
            _scalar_one_or_none_result(cons),
            _mapping_first_result(assessment_row),
            _mapping_all_result([assessment_result_row]),
        ]

        result = get_encounter_detail("user-1", "enc-1")

        assert result["encounter"]["assessment"]["id"] == "assess-1"
        assert result["encounter"]["assessment"]["required_scales"] == ["phq9", "sds"]
        assert result["encounter"]["assessment"]["selected_scales"] == ["phq9"]
        assert result["encounter"]["assessment_results"][0]["scale_slug"] == "phq9"
        assert result["encounter"]["assessment_results"][0]["normalized_score"] == 56
        assert result["encounter"]["assessment_results"][0]["score_details"] == {
            "normalization": {"maximum": 27}
        }
        assert result["encounter"]["assessment_results"][0]["risk_flags"] == [{"flag": "moderate_depression"}]
        assert result["encounter"]["consultation"]["chief_complaint_stage_summary"] == "情绪低落"
        assert result["encounter"]["consultation"]["required_scales"] == ["phq9", "sds"]
        assert result["encounter"]["consultation"]["subtitle_history"][0]["speaker"] == "doctor"
        assert any(item["event"] == "assessment_started" for item in result["encounter"]["timeline"])


class TestGetScaleScoreHistory:
    @patch("app.services.encounter_service.get_db_session")
    def test_history_includes_completed_scale_from_incomplete_encounter_and_dedupes_visit(self, mock_db_ctx):
        mock_session = MagicMock()
        mock_db_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_ctx.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value = _mapping_all_result(
            [
                {
                    "scale_slug": "phq9",
                    "raw_score": 16,
                    "derived_score": 16,
                    "result_completed_at": datetime(2026, 5, 22, 10, 0, tzinfo=timezone.utc),
                    "result_created_at": datetime(2026, 5, 22, 10, 0, tzinfo=timezone.utc),
                    "assessment_session_id": "assess-2b",
                    "assessment_status": "completed",
                    "encounter_session_id": "enc-2",
                    "assessment_created_at": datetime(2026, 5, 22, 9, 50, tzinfo=timezone.utc),
                    "encounter_status": "completed",
                },
                {
                    "scale_slug": "phq9",
                    "raw_score": 14,
                    "derived_score": 14,
                    "result_completed_at": datetime(2026, 5, 22, 9, 30, tzinfo=timezone.utc),
                    "result_created_at": datetime(2026, 5, 22, 9, 30, tzinfo=timezone.utc),
                    "assessment_session_id": "assess-2a",
                    "assessment_status": "completed",
                    "encounter_session_id": "enc-2",
                    "assessment_created_at": datetime(2026, 5, 22, 9, 20, tzinfo=timezone.utc),
                    "encounter_status": "completed",
                },
                {
                    "scale_slug": "phq9",
                    "raw_score": 12,
                    "derived_score": 12,
                    "result_completed_at": datetime(2026, 5, 20, 15, 10, tzinfo=timezone.utc),
                    "result_created_at": datetime(2026, 5, 20, 15, 10, tzinfo=timezone.utc),
                    "assessment_session_id": "assess-1",
                    "assessment_status": "in_progress",
                    "encounter_session_id": "enc-1",
                    "assessment_created_at": datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc),
                    "encounter_status": "in_progress",
                },
            ]
        )

        result = get_scale_score_history("user-1", "phq9")

        assert result["scale_slug"] == "phq9"
        assert [item["encounter_id"] for item in result["history"]] == ["enc-1", "enc-2"]
        assert result["history"][0]["score"] == 12
        assert result["history"][0]["encounter_status"] == "in_progress"
        assert result["history"][1]["score"] == 16
        assert result["history"][1]["assessment_session_id"] == "assess-2b"
