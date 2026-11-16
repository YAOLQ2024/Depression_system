import pytest

from app.services.risk_engine import _evaluate_safety_risk


def evaluate(consultation, assessment=None, rules=None):
    return _evaluate_safety_risk(
        consultation_payload=consultation,
        assessment_payload=assessment or {},
        rule_set=rules or {},
    )


def test_negative_screening_summary_does_not_trigger_keyword_risk():
    summary = (
        "首问自伤或轻生想法：无；危险物品准备或查找信息：未明确；"
        "具体计划或实际行为：未明确/未明确；复核阳性次数：0；"
        "复核结论：未见明确高风险；风险判定：low"
    )
    assert evaluate({
        "high_risk_screening_result": {
            "suicidal_ideation": "negative",
            "suicidal_ideation_initial": "negative",
            "suicide_plan": "unclear",
            "self_harm_behavior": "unclear",
            "alert_level": "low",
            "primary_concern": "改善我睡眠的问题",
        },
        "high_risk_screening_stage_summary": summary,
        "digital_human_consultation_summary": "睡眠不好；" + summary,
    }) == ("low", [])


@pytest.mark.parametrize("text", [
    "我不想轻生", "我不想死", "不是想死，只是睡不好",
    "没有轻生的想法", "我从未想过自杀", "我不会伤害自己",
    "我并无自残行为", "我没有伤害自己或轻生的想法", "轻生想法：无",
    "自杀的念头都没有", "没有想死的想法", "没有不想活了的念头",
    "没有轻生想法，但最近睡眠不好", "不想轻生，也没有伤害自己",
])
def test_explicit_denials_are_not_positive_statements(text):
    assert evaluate({"chief_complaint_structured_result": {
        "chief_complaint_text": text,
    }}) == ("low", [])


@pytest.mark.parametrize("text", [
    "我想轻生", "我想死", "我不想活了", "活着没意思", "想结束生命",
    "我想伤害自己", "我不是没有轻生的想法", "并非没有想死的念头",
    "我没有失眠但想死", "我不想轻生，但是有时候想伤害自己",
    "没有轻生念头。最近又想轻生", "不想轻生但现在又想轻生",
    "我想死怎么办？", "我控制不住想伤害自己",
])
def test_positive_disclosures_remain_high_risk(text):
    level, triggers = evaluate({"chief_complaint_structured_result": {
        "chief_complaint_text": text,
    }, "high_risk_screening_result": {"suicidal_ideation": "negative"}})
    assert level == "high"
    assert triggers[0].key == "self_harm_statement"
    assert triggers[0].evidence_payload["field"] == (
        "chief_complaint_structured_result.chief_complaint_text"
    )
    assert triggers[0].evidence_payload["statement"] in text


@pytest.mark.parametrize("field, value, expected", [
    ("alert_level", "high", "high"),
    ("alert_level", "urgent", "urgent"),
    ("suicidal_ideation", "positive", "high"),
    ("suicide_plan", "positive", "urgent"),
    ("self_harm_behavior", "positive", "urgent"),
])
def test_structured_screening_triggers_remain_effective(field, value, expected):
    level, triggers = evaluate({"high_risk_screening_result": {field: value}})
    assert level == expected
    assert triggers


def test_phq9_positive_flag_remains_effective():
    level, triggers = evaluate({}, {"flattened_risk_flags": [{
        "scale_slug": "phq9", "item_id": "q9",
        "flag": "self_harm_positive", "score_value": 1,
    }]})
    assert level == "high"
    assert triggers[0].key == "phq9_q9_positive"


@pytest.mark.parametrize("consultation", [
    {"chief_complaint_summary": "我想死"},
    {"symptom_screening_stage_summary": "想伤害自己"},
    {"high_risk_screening_result": {"primary_concern": "想解决轻生的想法"}},
])
def test_patient_text_fallbacks_and_primary_concern_remain_effective(consultation):
    assert evaluate(consultation)[0] == "high"


def test_custom_keyword_rule_is_respected():
    level, triggers = evaluate(
        {"chief_complaint_summary": "我想跳楼"},
        rules={"safety_rules": {"self_harm_keywords": ["跳楼"]}},
    )
    assert level == "high"
    assert triggers[0].evidence_payload["keyword"] == "跳楼"
