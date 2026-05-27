from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np

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
    SimpleNamespace(build_runtime_engine=lambda **_kwargs: object()),
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
    "app.services.non_eeg_runtime",
    SimpleNamespace(runtime_store=SimpleNamespace()),
)
sys.modules.setdefault(
    "app.services.non_eeg_inference",
    SimpleNamespace(
        infer_audio_emotion=lambda *_args, **_kwargs: None,
        infer_audio_emotion_from_wav_path=lambda *_args, **_kwargs: None,
        infer_face_emotion=lambda *_args, **_kwargs: None,
        infer_pose_emotion=lambda *_args, **_kwargs: None,
        infer_text_emotion=lambda *_args, **_kwargs: None,
    ),
)
sys.modules.setdefault(
    "app.services.object_storage",
    SimpleNamespace(
        ensure_multimodal_bucket=lambda: None,
        upload_audio_object=lambda *_args, **_kwargs: "s3://bucket/key",
        download_object_bytes=lambda *_args, **_kwargs: b"",
        parse_s3_uri=lambda uri: ("bucket", "key"),
        upload_object_to_bucket=lambda **_kwargs: "s3://bucket/key",
    ),
)

from app.schemas.multimodal import SubmitFrameCaptureRequest
from app.services.multimodal_session_service import (
    MultimodalServiceError,
    _build_failed_face_result,
    _compute_face_quality_flags,
    _normalize_face_result,
    _refresh_live_payload,
    submit_face_capture,
)


def _build_face_payload() -> SubmitFrameCaptureRequest:
    now = datetime(2026, 5, 21, 12, 0, 0, tzinfo=timezone.utc)
    return SubmitFrameCaptureRequest(
        flow_run_id="consult-1",
        question_key="chief-complaint-001",
        stage_id="stage-02-chief-complaint",
        image_base64="ZmFrZQ==",
        image_format="jpeg",
        mime_type="image/jpeg",
        turn_id="turn-1",
        sample_started_at=now,
        sample_ended_at=now,
        sample_index=3,
        frame_id="face-3",
    )


def test_normalize_face_result_keeps_quality_flags_and_completed_status() -> None:
    payload = _build_face_payload()

    result = _normalize_face_result(
        {
            "status": "ok",
            "dominant_emotion_zh": "平静",
            "confidence": 0.82,
            "scores": {
                "neutral": 0.82,
                "sad": 0.11,
                "happy": 0.07,
            },
            "quality_flags": {
                "blur": True,
                "low_light": False,
            },
        },
        payload,
    )

    assert result["status"] == "ready"
    assert result["processing_status"] == "completed"
    assert result["primary_label"] == "平静"
    assert result["primary_score"] == 0.82
    assert result["quality_flags"] == {
        "no_face": False,
        "blur": True,
        "low_light": False,
    }
    assert result["error_message"] is None
    assert result["sample_index"] == 3


def test_normalize_face_result_marks_failed_when_runtime_returns_error() -> None:
    payload = _build_face_payload()

    result = _normalize_face_result(
        {
            "status": "model_inference_failed",
            "dominant_emotion_zh": None,
            "confidence": 0.0,
            "scores": {},
        },
        payload,
    )

    assert result["status"] == "failed"
    assert result["processing_status"] == "failed"
    assert result["primary_label"] is None
    assert result["error_message"] == "model_inference_failed"
    assert result["quality_flags"]["no_face"] is False


def test_build_failed_face_result_returns_standardized_payload() -> None:
    payload = _build_face_payload()

    result = _build_failed_face_result(payload, error_message="object storage unavailable")

    assert result["modality"] == "face"
    assert result["status"] == "failed"
    assert result["processing_status"] == "failed"
    assert result["top_3_labels"] == []
    assert result["quality_flags"] == {
        "no_face": False,
        "blur": False,
        "low_light": False,
    }
    assert result["error_message"] == "object storage unavailable"


def test_compute_face_quality_flags_handles_invalid_image_bytes() -> None:
    flags = _compute_face_quality_flags(b"not-an-image")
    assert flags == {"blur": False, "low_light": False}


def test_compute_face_quality_flags_detects_dark_blurry_frame(monkeypatch) -> None:
    dark_frame = np.zeros((64, 64, 3), dtype=np.uint8)
    fake_cv2 = SimpleNamespace(
        IMREAD_COLOR=1,
        COLOR_BGR2GRAY=2,
        CV_64F=3,
        imdecode=lambda *_args, **_kwargs: dark_frame,
        cvtColor=lambda frame, _code: frame[:, :, 0],
        Laplacian=lambda frame, _depth: frame,
    )
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    flags = _compute_face_quality_flags(b"unused")

    assert flags == {"blur": True, "low_light": True}


def test_compute_face_quality_flags_detects_bright_detailed_frame(monkeypatch) -> None:
    checker = np.indices((64, 64)).sum(axis=0) % 2
    checker = (checker * 255).astype(np.uint8)
    bright_frame = np.stack([checker, checker, checker], axis=-1)
    fake_cv2 = SimpleNamespace(
        IMREAD_COLOR=1,
        COLOR_BGR2GRAY=2,
        CV_64F=3,
        imdecode=lambda *_args, **_kwargs: bright_frame,
        cvtColor=lambda frame, _code: frame[:, :, 0],
        Laplacian=lambda frame, _depth: frame,
    )
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    flags = _compute_face_quality_flags(b"unused")

    assert flags == {"blur": False, "low_light": False}


def test_refresh_live_payload_copies_face_runtime_fields() -> None:
    session = SimpleNamespace(
        live_state_payload={},
        updated_at=None,
        status="created",
    )

    _refresh_live_payload(
        session,
        {
            "modality": "face",
            "status": "failed",
            "processing_status": "failed",
            "primary_label": None,
            "primary_score": None,
            "top_3_labels": [],
            "quality_flags": {"no_face": False, "blur": True, "low_light": False},
            "sample_ended_at": "2026-05-21T12:00:00+00:00",
            "sample_count": 6,
            "valid_sample_count": 4,
            "error_message": "model_inference_failed",
        },
    )

    face_live = session.live_state_payload["face"]
    assert face_live["status"] == "failed"
    assert face_live["processing_status"] == "failed"
    assert face_live["latest_capture_at"] == "2026-05-21T12:00:00+00:00"
    assert face_live["sample_count"] == 6
    assert face_live["valid_sample_count"] == 4
    assert face_live["error_message"] == "model_inference_failed"
    assert session.status == "active"


class _FakeDbSession:
    def __init__(self, session_obj) -> None:
        self._session_obj = session_obj
        self.added: list[object] = []
        self.flush_count = 0

    def get(self, model, session_id: str):
        if session_id == self._session_obj.id:
            return self._session_obj
        return None

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flush_count += 1


class _FakeDbContext:
    def __init__(self, db_session: _FakeDbSession) -> None:
        self._db_session = db_session

    def __enter__(self) -> _FakeDbSession:
        return self._db_session

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_submit_face_capture_success_updates_live_and_uses_bundle_counts(monkeypatch) -> None:
    payload = _build_face_payload()
    now = datetime(2026, 5, 21, 12, 0, 0, tzinfo=timezone.utc)
    session = SimpleNamespace(
        id="mm-session-1",
        user_id="user-1",
        live_state_payload={},
        updated_at=now,
        status="created",
    )
    db_session = _FakeDbSession(session)
    inference_rows: list[dict[str, object]] = []

    monkeypatch.setattr(
        "app.services.multimodal_session_service.get_db_session",
        lambda: _FakeDbContext(db_session),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._build_frame_storage_uri",
        lambda **kwargs: "s3://mcs-multimodal/captures/face/mm-session-1/turn-1/sample-3.jpg",
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._record_capture",
        lambda *args, **kwargs: SimpleNamespace(
            id="face-cap-003",
            created_at=now,
            storage_uri=None,
        ),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service.infer_face_emotion",
        lambda request: {
            "code": 0,
            "message": "ok",
            "data": {
                "result": {
                    "status": "ok",
                    "dominant_emotion_zh": "平静",
                    "confidence": 0.77,
                    "scores": {"neutral": 0.77, "sad": 0.12, "happy": 0.11},
                }
            },
        },
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._compute_face_quality_flags",
        lambda image_bytes: {"blur": True, "low_light": False},
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._record_inference_result",
        lambda *args, **kwargs: inference_rows.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._upsert_turn_bundle",
        lambda *args, **kwargs: {
            "turn_id": payload.turn_id,
            "face_features": {
                "summary_type": "turn_window",
                "primary_label": "平静",
                "primary_score": 0.5,
                "primary_ratio": 0.5,
                "sample_count": 9,
                "valid_sample_count": 7,
                "label_distribution": [],
                "quality_distribution": {},
                "quality_flags": {},
            },
        },
    )

    result = submit_face_capture("mm-session-1", payload, acting_user_id="user-1")

    assert result["capture_id"] == "face-cap-003"
    assert result["storage_uri"].startswith("s3://")
    assert result["processing_status"] == "completed"
    assert result["sample_count"] == 9
    assert result["valid_sample_count"] == 7
    assert result["turn_bundle"]["face_features"]["sample_count"] == 9
    assert inference_rows[0]["inference_payload"]["quality_flags"] == {
        "no_face": False,
        "blur": True,
        "low_light": False,
    }
    face_live = session.live_state_payload["face"]
    assert face_live["status"] == "ready"
    assert face_live["sample_count"] == 9
    assert face_live["valid_sample_count"] == 7
    assert face_live["error_message"] is None
    assert db_session.flush_count >= 1


def test_submit_face_capture_failure_returns_standardized_failed_payload(monkeypatch) -> None:
    payload = _build_face_payload()
    now = datetime(2026, 5, 21, 12, 0, 0, tzinfo=timezone.utc)
    session = SimpleNamespace(
        id="mm-session-2",
        user_id="user-2",
        live_state_payload={},
        updated_at=now,
        status="created",
    )
    db_session = _FakeDbSession(session)
    inference_rows: list[dict[str, object]] = []

    monkeypatch.setattr(
        "app.services.multimodal_session_service.get_db_session",
        lambda: _FakeDbContext(db_session),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._build_frame_storage_uri",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._record_capture",
        lambda *args, **kwargs: SimpleNamespace(
            id="face-cap-failed",
            created_at=now,
            storage_uri=None,
        ),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service.infer_face_emotion",
        lambda request: {"code": 5001, "message": "model_inference_failed", "data": {}},
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._extract_result_or_raise",
        lambda response: (_ for _ in ()).throw(
            MultimodalServiceError("model_inference_failed", 5001, 500)
        ),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._record_inference_result",
        lambda *args, **kwargs: inference_rows.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._upsert_turn_bundle",
        lambda *args, **kwargs: None,
    )

    result = submit_face_capture("mm-session-2", payload, acting_user_id="user-2")

    assert result["capture_id"] == "face-cap-failed"
    assert result["processing_status"] == "failed"
    assert result["error_message"] == "model_inference_failed"
    assert result["sample_count"] == payload.sample_index
    assert result["valid_sample_count"] is None
    assert result["storage_uri"] is None
    assert inference_rows[0]["inference_payload"]["status"] == "failed"
    assert session.live_state_payload["face"]["status"] == "failed"
    assert session.live_state_payload["face"]["error_message"] == "model_inference_failed"
