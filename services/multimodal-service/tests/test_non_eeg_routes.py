from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_ready() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["status"] == "ready"


def test_text_emotion_new_route(monkeypatch) -> None:
    from app.api import non_eeg_inference as api

    monkeypatch.setattr(
        api,
        "infer_text_emotion",
        lambda request: {"code": 0, "message": "ok", "data": {"result": {"label": "positive"}}},
    )

    response = client.post("/api/v1/non-eeg/text-emotion/infer", json={"text": "今天感觉不错"})
    assert response.status_code == 200
    assert response.json()["data"]["result"]["label"] == "positive"


def test_text_emotion_legacy_route(monkeypatch) -> None:
    from app.api import non_eeg_inference as api

    monkeypatch.setattr(
        api,
        "infer_text_emotion",
        lambda request: {"code": 0, "message": "ok", "data": {"result": {"label": "negative"}}},
    )

    response = client.post("/api/v1/text/infer", json={"text": "我有点难受"})
    assert response.status_code == 200
    assert response.json()["data"]["result"]["label"] == "negative"
