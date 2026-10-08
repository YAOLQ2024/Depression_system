import pytest

from app.services.risk_engine import (
    _extract_label_distribution_score,
    _extract_top_label_distribution_score,
    _normalize_negative_label_sets,
)


@pytest.mark.parametrize("configured", [None, ["ang", "sad"], ["angry", "sad"]])
@pytest.mark.parametrize("label", ["ang", "angry"])
def test_audio_anger_alias_matches_existing_rule(configured, label):
    rules = {} if configured is None else {"negative_label_sets": {"speech": configured}}
    negative = _normalize_negative_label_sets(rules)["speech"]
    score, _ = _extract_top_label_distribution_score(
        {"top_3_labels": [{"label": label, "score": 0.7}, {"label": "neutral", "score": 0.3}]},
        negative_labels=negative,
    )
    assert score == 70


@pytest.mark.parametrize("label", ["fear", "恐惧", "disgust", "厌恶", "angry", "愤怒"])
def test_face_english_and_chinese_labels_preserve_rule(label):
    negative = _normalize_negative_label_sets({})["face"]
    score, _ = _extract_label_distribution_score(
        {"label_distribution": [{"label": label, "ratio": 1}]}, negative_labels=negative,
    )
    assert score == 100


def test_empty_custom_rule_does_not_add_anger():
    assert not _normalize_negative_label_sets({"negative_label_sets": {"speech": ["sad"]}})["speech"].intersection({"ang", "angry"})
