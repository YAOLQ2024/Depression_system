from __future__ import annotations

from datetime import datetime, timezone

import pytest


pytest.importorskip("reportlab")

from app.services.pdf_report import FONT_NAME, generate_encounter_pdf


def test_pdf_report_uses_cjk_capable_font():
    assert FONT_NAME != "Helvetica"


def test_generate_encounter_pdf_returns_pdf_bytes():
    encounter_payload = {
        "encounter": {
            "id": "enc-1",
            "status": "completed",
            "current_flow_type": "assessment",
            "created_at": datetime(2026, 5, 20, 14, 30, tzinfo=timezone.utc).isoformat(),
            "consultation": {
                "chief_complaint_raw_text": "最近两周一直情绪低落，睡眠很差，还总是提不起劲。",
                "chief_complaint_summary": "最近情绪低落，伴随失眠与注意力下降。",
                "assigned_doctor_persona": "doctor-a-calm-female",
                "chief_complaint_stage_summary": "近期情绪持续低落，并伴随睡眠和注意力问题。",
                "symptom_screening_stage_summary": "问诊提示兴趣下降、精力不足与失眠较明显。",
                "high_risk_screening_stage_summary": "当前未见急性自伤风险，但仍建议持续观察。",
                "digital_human_consultation_summary": "整体问诊提示抑郁相关症状中度活跃，需结合量表综合判断。",
                "current_history_structured_result": {
                    "sleep_quality": "poor",
                    "interest_level": "decreased",
                },
                "high_risk_screening_result": {
                    "suicidal_ideation": "denied",
                },
                "required_scales": ["phq9", "sds"],
            },
            "assessment": {
                "aggregate_payload": {
                    "risk_summary": {
                        "risk_level": "medium",
                        "risk_level_label": "中风险",
                        "depression_score": 61.4,
                        "depression_severity_label": "中度抑郁",
                        "requires_human_review": False,
                        "front_display": {
                            "title": "当前评估结果：中风险",
                            "message": "综合抑郁得分约为 61.40 分，建议尽快完成进一步评估。",
                        },
                        "risk_explanation": {
                            "summary": "当前统一风险等级为中风险，主要由抑郁症状活跃度驱动。",
                        },
                        "referral_recommendations": ["建议 1-2 周内完成线下心理/精神专科评估。"],
                        "lifestyle_suggestions": ["保持规律作息并记录近两周情绪与睡眠变化。"],
                    }
                }
            },
            "assessment_results": [
                {
                    "scale_slug": "phq9",
                    "raw_score": 15,
                    "derived_score": 15,
                    "normalized_score": 56,
                    "interpretation_label": "中度抑郁",
                    "score_details": {
                        "normalization": {"maximum": 27}
                    },
                    "risk_flags": [{"flag": "moderate_depression"}],
                },
                {
                    "scale_slug": "sds",
                    "raw_score": 48,
                    "derived_score": 60,
                    "normalized_score": 60,
                    "interpretation_label": "轻中度抑郁",
                    "score_details": {
                        "normalization": {"maximum": 100}
                    },
                    "risk_flags": [],
                }
            ],
            "timeline": [
                {
                    "event": "encounter_created",
                    "at": datetime(2026, 5, 20, 14, 30, tzinfo=timezone.utc).isoformat(),
                },
                {
                    "event": "assessment_completed",
                    "at": datetime(2026, 5, 20, 15, 5, tzinfo=timezone.utc).isoformat(),
                },
            ],
        }
    }

    pdf_bytes = generate_encounter_pdf(encounter_payload)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 2000
