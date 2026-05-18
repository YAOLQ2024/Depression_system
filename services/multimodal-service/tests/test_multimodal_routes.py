from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_face_capture_accepts_step4d_form(monkeypatch) -> None:
    from app.api import multimodal as api

    observed: dict[str, object] = {}

    def fake_submit_face_capture(session_id, payload, acting_user_id=None):
        observed["session_id"] = session_id
        observed["payload"] = payload
        observed["acting_user_id"] = acting_user_id
        return {
            "capture_id": "face-cap-001",
            "session_id": session_id,
            "question_key": payload.question_key,
            "modality": "face",
            "processing_status": "completed",
            "primary_label": "平静",
            "primary_score": 0.76,
            "top_3_labels": [{"label": "平静", "score": 0.76}],
            "quality_flags": {"no_face": False, "blur": False, "low_light": False},
            "capture_started_at": "2026-05-17T10:01:11Z",
            "capture_ended_at": "2026-05-17T10:01:11Z",
            "created_at": "2026-05-17T10:01:11Z",
        }

    monkeypatch.setattr(api, "submit_face_capture", fake_submit_face_capture)

    response = client.post(
        "/api/v1/multimodal/sessions/mm-session-1/captures/face",
        data={
            "consultation_session_id": "consult-1",
            "question_key": "chief-complaint-001",
            "turn_id": "turn-1",
            "capture_started_at": "2026-05-17T10:01:11Z",
            "capture_ended_at": "2026-05-17T10:01:11Z",
            "frame_index": "7",
            "mime_type": "image/jpeg",
        },
        files={"image_file": ("frame.jpg", b"jpeg-bytes", "image/jpeg")},
        headers={"x-mcs-user-id": "user-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["capture_id"] == "face-cap-001"
    assert observed["session_id"] == "mm-session-1"
    req = observed["payload"]
    assert req.consultation_session_id == "consult-1"
    assert req.question_key == "chief-complaint-001"
    assert req.consultation_turn_id == "turn-1"
    assert req.frame_index == 7
    assert req.mime_type == "image/jpeg"
    assert req.image_format == "jpeg"
    assert isinstance(req.image_base64, str) and len(req.image_base64) > 0


def test_live_route_returns_step4d_shape(monkeypatch) -> None:
    from app.api import multimodal as api

    monkeypatch.setattr(
        api,
        "get_multimodal_live",
        lambda session_id, acting_user_id=None: {
            "session_id": session_id,
            "updated_at": "2026-05-17T10:01:20Z",
            "speech": {"status": "ready", "primary_label": "语音平稳", "primary_score": 0.88, "top_3_labels": []},
            "text": {"status": "pending", "primary_label": None, "primary_score": None, "top_3_labels": [], "negative_terms": []},
            "face": {"status": "ready", "primary_label": "平静", "primary_score": 0.76, "latest_capture_at": "2026-05-17T10:01:19Z"},
            "pose": {"status": "pending", "primary_label": None, "primary_score": None, "latest_capture_at": None},
        },
    )

    response = client.get("/api/v1/multimodal/sessions/mm-session-1/live")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "live" not in data
    assert data["speech"]["status"] == "ready"
    assert data["face"]["latest_capture_at"] == "2026-05-17T10:01:19Z"


def test_bundle_route_returns_direct_bundle(monkeypatch) -> None:
    from app.api import multimodal as api

    monkeypatch.setattr(
        api,
        "get_multimodal_turn_bundle",
        lambda session_id, consultation_turn_id, acting_user_id=None: {
            "turn_id": consultation_turn_id,
            "session_id": session_id,
            "question_key": "chief-complaint-001",
            "generated_at": "2026-05-17T10:01:25Z",
            "speech_features": {"primary_label": "语音平稳", "primary_score": 0.88, "top_3_labels": []},
            "text_features": {"primary_label": "中性", "primary_score": 0.79, "top_3_labels": [], "negative_terms": []},
            "face_features": {"summary_type": "turn_window", "primary_label": "平静", "primary_score": 0.72, "top_3_labels": [], "sample_count": 6, "quality_flags": {"no_face_ratio": 0.0, "blur_ratio": 0.0, "low_light_ratio": 0.0}},
            "pose_features": {"summary_type": "turn_window", "primary_label": "轻微前倾", "primary_score": 0.81, "top_3_labels": [], "sample_count": 8, "quality_flags": {"no_pose_ratio": 0.0, "body_cutoff_ratio": 0.0, "motion_blur_ratio": 0.0}},
        },
    )

    response = client.get("/api/v1/multimodal/sessions/mm-session-1/turns/turn-1/bundle")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["turn_id"] == "turn-1"
    assert "turn_bundle" not in data
    assert data["face_features"]["summary_type"] == "turn_window"
