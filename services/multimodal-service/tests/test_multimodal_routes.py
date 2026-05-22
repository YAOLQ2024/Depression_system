from __future__ import annotations

from fastapi.testclient import TestClient

def build_test_client(monkeypatch: object) -> TestClient:
    from app import main as main_module

    monkeypatch.setattr(main_module, "recover_incomplete_audio_turns", lambda: None)
    monkeypatch.setattr(main_module, "ensure_multimodal_bucket", lambda: None)
    monkeypatch.setattr(main_module, "shutdown_transcription_executor", lambda: None)
    monkeypatch.setattr(main_module.runtime_store, "shutdown", lambda: None)
    return TestClient(main_module.app)


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
            "sample_started_at": "2026-05-17T10:01:11Z",
            "sample_ended_at": "2026-05-17T10:01:11Z",
            "sample_count": 7,
            "valid_sample_count": 7,
            "storage_uri": "s3://mcs-multimodal/captures/face/mm-session-1/turn-1/sample-7.jpg",
            "error_message": None,
            "created_at": "2026-05-17T10:01:11Z",
        }

    monkeypatch.setattr(api, "submit_face_capture", fake_submit_face_capture)

    with build_test_client(monkeypatch) as client:
        response = client.post(
            "/api/v1/multimodal/sessions/mm-session-1/captures/face",
            data={
                "flow_run_id": "consult-1",
                "question_key": "chief-complaint-001",
                "turn_id": "turn-1",
                "sample_started_at": "2026-05-17T10:01:11Z",
                "sample_ended_at": "2026-05-17T10:01:11Z",
                "sample_index": "7",
                "mime_type": "image/jpeg",
            },
            files={"image_file": ("frame.jpg", b"jpeg-bytes", "image/jpeg")},
            headers={"x-mcs-user-id": "user-1"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["capture_id"] == "face-cap-001"
    assert payload["data"]["sample_count"] == 7
    assert payload["data"]["storage_uri"].startswith("s3://")
    assert observed["session_id"] == "mm-session-1"
    req = observed["payload"]
    assert req.flow_run_id == "consult-1"
    assert req.question_key == "chief-complaint-001"
    assert req.turn_id == "turn-1"
    assert req.sample_index == 7
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
            "face": {
                "status": "ready",
                "processing_status": "completed",
                "primary_label": "平静",
                "primary_score": 0.76,
                "latest_capture_at": "2026-05-17T10:01:19Z",
                "sample_count": 6,
                "valid_sample_count": 6,
                "error_message": None,
            },
            "pose": {"status": "pending", "primary_label": None, "primary_score": None, "latest_capture_at": None},
        },
    )

    with build_test_client(monkeypatch) as client:
        response = client.get("/api/v1/multimodal/sessions/mm-session-1/live")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "live" not in data
    assert data["speech"]["status"] == "ready"
    assert data["face"]["latest_capture_at"] == "2026-05-17T10:01:19Z"
    assert data["face"]["sample_count"] == 6


def test_pose_capture_accepts_step4d_form(monkeypatch) -> None:
    from app.api import multimodal as api

    observed: dict[str, object] = {}

    def fake_submit_pose_capture(session_id, payload, acting_user_id=None):
        observed["session_id"] = session_id
        observed["payload"] = payload
        observed["acting_user_id"] = acting_user_id
        return {
            "capture_id": "pose-cap-001",
            "session_id": session_id,
            "question_key": payload.question_key,
            "modality": "pose",
            "processing_status": "completed",
            "primary_label": "轻微前倾",
            "primary_score": 0.63,
            "top_3_labels": [{"label": "轻微前倾", "score": 0.63}],
            "quality_flags": {"no_pose": False, "body_cutoff": False, "motion_blur": False},
            "sample_started_at": "2026-05-17T10:01:11Z",
            "sample_ended_at": "2026-05-17T10:01:11Z",
            "sample_count": 8,
            "valid_sample_count": 8,
            "storage_uri": "s3://mcs-multimodal/captures/pose/mm-session-1/turn-1/sample-8.jpg",
            "error_message": None,
            "created_at": "2026-05-17T10:01:11Z",
        }

    monkeypatch.setattr(api, "submit_pose_capture", fake_submit_pose_capture)

    with build_test_client(monkeypatch) as client:
        response = client.post(
            "/api/v1/multimodal/sessions/mm-session-1/captures/pose",
            data={
                "flow_run_id": "consult-1",
                "question_key": "chief-complaint-001",
                "turn_id": "turn-1",
                "sample_started_at": "2026-05-17T10:01:11Z",
                "sample_ended_at": "2026-05-17T10:01:11Z",
                "sample_index": "8",
                "mime_type": "image/jpeg",
            },
            files={"image_file": ("frame.jpg", b"jpeg-bytes", "image/jpeg")},
            headers={"x-mcs-user-id": "user-1"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["capture_id"] == "pose-cap-001"
    assert payload["data"]["sample_count"] == 8
    assert payload["data"]["storage_uri"].startswith("s3://")
    assert observed["session_id"] == "mm-session-1"
    req = observed["payload"]
    assert req.sample_index == 8
    assert req.image_format == "jpeg"


def test_bundle_route_returns_direct_bundle(monkeypatch) -> None:
    from app.api import multimodal as api

    monkeypatch.setattr(
        api,
        "get_multimodal_turn_bundle",
        lambda session_id, turn_id, acting_user_id=None: {
            "turn_id": turn_id,
            "session_id": session_id,
            "flow_run_id": "consult-1",
            "stage_id": "stage-02-chief-complaint",
            "question_key": "chief-complaint-001",
            "generated_at": "2026-05-17T10:01:25Z",
            "speech_features": {"primary_label": "语音平稳", "primary_score": 0.88, "top_3_labels": []},
            "text_features": {"primary_label": "中性", "primary_score": 0.79, "top_3_labels": [], "negative_terms": []},
            "face_features": {
                "summary_type": "turn_window",
                "primary_label": "平静",
                "primary_score": 0.5,
                "primary_ratio": 0.5,
                "sample_count": 6,
                "valid_sample_count": 6,
                "label_distribution": [
                    {"label": "平静", "count": 3, "ratio": 0.5},
                    {"label": "低落", "count": 2, "ratio": 0.3333},
                    {"label": "焦虑", "count": 1, "ratio": 0.1667},
                ],
                "quality_distribution": {
                    "no_face": {"count": 0, "ratio": 0.0},
                    "blur": {"count": 0, "ratio": 0.0},
                    "low_light": {"count": 0, "ratio": 0.0},
                },
                "quality_flags": {"no_face_ratio": 0.0, "blur_ratio": 0.0, "low_light_ratio": 0.0},
            },
            "pose_features": {
                "summary_type": "turn_window",
                "primary_label": "轻微前倾",
                "primary_score": 0.625,
                "primary_ratio": 0.625,
                "sample_count": 8,
                "valid_sample_count": 8,
                "label_distribution": [
                    {"label": "轻微前倾", "count": 5, "ratio": 0.625},
                    {"label": "中性", "count": 3, "ratio": 0.375},
                ],
                "quality_distribution": {
                    "no_pose": {"count": 0, "ratio": 0.0},
                    "body_cutoff": {"count": 0, "ratio": 0.0},
                    "motion_blur": {"count": 0, "ratio": 0.0},
                },
                "quality_flags": {"no_pose_ratio": 0.0, "body_cutoff_ratio": 0.0, "motion_blur_ratio": 0.0},
            },
        },
    )

    with build_test_client(monkeypatch) as client:
        response = client.get("/api/v1/multimodal/sessions/mm-session-1/turns/turn-1/bundle")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["turn_id"] == "turn-1"
    assert "turn_bundle" not in data
    assert data["face_features"]["summary_type"] == "turn_window"
    assert data["face_features"]["label_distribution"][0]["label"] == "平静"


def test_clear_pose_turn_runtime_route(monkeypatch) -> None:
    from app.api import multimodal as api

    monkeypatch.setattr(
        api,
        "clear_pose_turn_runtime_state",
        lambda session_id, turn_id, acting_user_id=None: {
            "session_id": session_id,
            "turn_id": turn_id,
            "modality": "pose",
            "cleared": True,
        },
    )

    with build_test_client(monkeypatch) as client:
        response = client.post(
            "/api/v1/multimodal/sessions/mm-session-1/turns/turn-1/pose-runtime/clear",
            headers={"x-mcs-user-id": "user-1"},
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["session_id"] == "mm-session-1"
    assert data["turn_id"] == "turn-1"
    assert data["cleared"] is True
