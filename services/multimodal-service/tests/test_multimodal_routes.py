from __future__ import annotations

import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

sys.modules.setdefault(
    "minio",
    SimpleNamespace(Minio=object),
)
sys.modules.setdefault(
    "minio.error",
    SimpleNamespace(S3Error=Exception),
)
sys.modules.setdefault(
    "onnxruntime",
    SimpleNamespace(get_available_providers=lambda: ["CPUExecutionProvider"]),
)
sys.modules.setdefault(
    "infer_text",
    SimpleNamespace(build_runtime_engine=lambda **_kwargs: object()),
)
sys.modules.setdefault(
    "infer_audio",
    SimpleNamespace(
        MODEL_SAMPLE_RATE=16000,
        build_runtime_engine=lambda **_kwargs: object(),
        predict_audio=lambda *_args, **_kwargs: {},
        resample_linear=lambda data, *_args, **_kwargs: data,
    ),
)
sys.modules.setdefault(
    "infer_face",
    SimpleNamespace(build_runtime_engine=lambda **_kwargs: object()),
)
sys.modules.setdefault(
    "infer_pose",
    SimpleNamespace(
        build_runtime_engine=lambda **_kwargs: object(),
        build_turn_state=lambda *_args, **_kwargs: SimpleNamespace(last_used_at=0.0),
        close_runtime_engine=lambda *_args, **_kwargs: None,
    ),
)
sys.modules.setdefault(
    "app.services.object_storage",
    SimpleNamespace(
        ensure_multimodal_bucket=lambda: None,
        upload_audio_object=lambda *_args, **_kwargs: "s3://bucket/key",
        upload_object_to_bucket=lambda **_kwargs: "s3://bucket/key",
        download_object_bytes=lambda *_args, **_kwargs: b"",
        parse_s3_uri=lambda uri: ("bucket", "key"),
        is_storage_ready=lambda: True,
    ),
)
sys.modules.setdefault(
    "python_multipart",
    SimpleNamespace(__version__="0.0.20"),
)
sys.modules.setdefault(
    "multipart",
    SimpleNamespace(__version__="0.0.20"),
)
sys.modules.setdefault(
    "multipart.multipart",
    SimpleNamespace(parse_options_header=lambda value: value),
)

def build_test_client(monkeypatch: object) -> TestClient:
    from app import main as main_module

    monkeypatch.setattr(main_module, "recover_incomplete_audio_turns", lambda: None)
    monkeypatch.setattr(main_module, "ensure_multimodal_bucket", lambda: None)
    monkeypatch.setattr(main_module, "shutdown_transcription_executor", lambda: None)
    monkeypatch.setattr(main_module.runtime_store, "shutdown", lambda: None)
    return TestClient(main_module.app)


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


def test_visual_capture_accepts_shared_frame_form(monkeypatch) -> None:
    from app.api import multimodal as api

    observed: dict[str, object] = {}

    def fake_submit_visual_capture(session_id, payload, acting_user_id=None):
        observed["session_id"] = session_id
        observed["payload"] = payload
        observed["acting_user_id"] = acting_user_id
        return {
            "visual_frame": {
                "visual_frame_id": "vf-001",
                "session_id": session_id,
                "storage_uri": "s3://mcs-multimodal/captures/visual/mm-session-1/turn-1/sample-9.jpg",
            },
            "face_result": {"capture_id": "face-cap-visual-001"},
            "pose_result": {"capture_id": "pose-cap-visual-001"},
            "turn_bundle": {"turn_id": "turn-1"},
            "multimodal_session": {"id": session_id},
        }

    monkeypatch.setattr(api, "submit_visual_capture", fake_submit_visual_capture)

    with build_test_client(monkeypatch) as client:
        response = client.post(
            "/api/v1/multimodal/sessions/mm-session-1/visual-captures",
            data={
                "flow_run_id": "consult-1",
                "question_key": "chief-complaint-001",
                "turn_id": "turn-1",
                "sample_started_at": "2026-05-17T10:01:11Z",
                "sample_ended_at": "2026-05-17T10:01:11Z",
                "sample_index": "9",
                "mime_type": "image/jpeg",
            },
            files={"image_file": ("frame.jpg", b"jpeg-bytes", "image/jpeg")},
            headers={"x-mcs-user-id": "user-1"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["visual_frame"]["visual_frame_id"] == "vf-001"
    assert payload["data"]["face_result"]["capture_id"] == "face-cap-visual-001"
    assert payload["data"]["pose_result"]["capture_id"] == "pose-cap-visual-001"
    req = observed["payload"]
    assert req.sample_index == 9
    assert req.image_format == "jpeg"
    assert req.image_bytes == b"jpeg-bytes"
    assert req.image_base64 is None


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
