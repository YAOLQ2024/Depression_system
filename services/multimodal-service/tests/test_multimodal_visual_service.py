from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import SimpleNamespace

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
from app.services.multimodal_session_service import submit_visual_capture


def _build_visual_payload() -> SubmitFrameCaptureRequest:
    now = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
    return SubmitFrameCaptureRequest(
        flow_run_id="consult-1",
        question_key="chief-complaint-001",
        stage_id="stage-02-chief-complaint",
        image_bytes=b"jpeg-bytes",
        image_format="jpeg",
        mime_type="image/jpeg",
        turn_id="turn-1",
        sample_started_at=now,
        sample_ended_at=now,
        sample_index=3,
        frame_id="visual-3",
    )


class _FakeDbSession:
    def __init__(self, session_obj) -> None:
        self._session_obj = session_obj
        self.flush_count = 0
        self.refreshed: list[object] = []

    def get(self, _model, session_id: str):
        if session_id == self._session_obj.id:
            return self._session_obj
        return None

    def add(self, _value: object) -> None:
        return None

    def flush(self) -> None:
        self.flush_count += 1

    def refresh(self, value: object) -> None:
        self.refreshed.append(value)


class _FakeDbContext:
    def __init__(self, db_session: _FakeDbSession) -> None:
        self._db_session = db_session

    def __enter__(self) -> _FakeDbSession:
        return self._db_session

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_submit_visual_capture_overlaps_upload_and_aggregates_once(monkeypatch) -> None:
    payload = _build_visual_payload()
    now = payload.sample_ended_at
    session = SimpleNamespace(
        id="mm-session-1",
        user_id="user-1",
        live_state_payload={},
        updated_at=now,
        status="created",
    )
    db_session = _FakeDbSession(session)
    order: list[str] = []
    capture_rows = {
        "face": SimpleNamespace(id="face-cap-1", created_at=now, storage_uri=None),
        "pose": SimpleNamespace(id="pose-cap-1", created_at=now, storage_uri=None),
    }

    class _FakeFuture:
        def result(self) -> str:
            order.append("upload_result")
            return "s3://mcs-multimodal/captures/visual/mm-session-1/turn-1/sample-3.jpg"

    class _FakeExecutor:
        def submit(self, fn, *args, **kwargs):
            order.append("upload_submit")
            return _FakeFuture()

    def fake_face_infer(session_id: str, frame_payload: SubmitFrameCaptureRequest):
        assert session_id == session.id
        assert order == ["upload_submit"]
        order.append("face_infer")
        return {
            "modality": "face",
            "status": "ready",
            "processing_status": "completed",
            "primary_label": "平静",
            "primary_score": 0.82,
            "top_3_labels": [{"label": "平静", "score": 0.82}],
            "quality_flags": {"no_face": False, "blur": False, "low_light": False},
            "sample_started_at": frame_payload.sample_started_at.isoformat(),
            "sample_ended_at": frame_payload.sample_ended_at.isoformat(),
            "error_message": None,
        }

    def fake_pose_infer(session_id: str, frame_payload: SubmitFrameCaptureRequest):
        assert session_id == session.id
        assert order == ["upload_submit", "face_infer"]
        order.append("pose_infer")
        return {
            "modality": "pose",
            "status": "ready",
            "processing_status": "completed",
            "primary_label": "中性姿态",
            "primary_score": 0.74,
            "top_3_labels": [{"label": "中性姿态", "score": 0.74}],
            "quality_flags": {
                "no_pose": False,
                "body_cutoff": False,
                "motion_blur": False,
            },
            "sample_started_at": frame_payload.sample_started_at.isoformat(),
            "sample_ended_at": frame_payload.sample_ended_at.isoformat(),
            "error_message": None,
        }

    def fake_record_visual_frame(*_args, **kwargs):
        assert kwargs["storage_uri"].startswith("s3://")
        order.append("record_visual_frame")
        return SimpleNamespace(id="vf-1", created_at=now)

    def fake_record_capture(*_args, **kwargs):
        modality = kwargs["modality"]
        order.append(f"record_capture_{modality}")
        return capture_rows[modality]

    upsert_calls: list[dict[str, object]] = []
    refresh_calls: list[tuple[dict[str, object], ...]] = []

    monkeypatch.setattr(
        "app.services.multimodal_session_service.get_db_session",
        lambda: _FakeDbContext(db_session),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._VISUAL_STORAGE_EXECUTOR",
        _FakeExecutor(),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._infer_face_capture_result",
        fake_face_infer,
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._infer_pose_capture_result",
        fake_pose_infer,
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._record_visual_frame",
        fake_record_visual_frame,
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._record_capture",
        fake_record_capture,
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._record_inference_result",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._upsert_turn_bundle",
        lambda *_args, **kwargs: upsert_calls.append(kwargs)
        or {
            "turn_id": payload.turn_id,
            "face_features": {"sample_count": 5, "valid_sample_count": 4},
            "pose_features": {"sample_count": 5, "valid_sample_count": 5},
        },
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._refresh_live_payload",
        lambda _session, *results: refresh_calls.append(results),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._snapshot",
        lambda current_session: {"id": current_session.id},
    )

    result = submit_visual_capture("mm-session-1", payload, acting_user_id="user-1")

    assert order[:4] == ["upload_submit", "face_infer", "pose_infer", "upload_result"]
    assert upsert_calls == [
        {
            "flow_run_id": payload.flow_run_id,
            "stage_id": payload.stage_id,
            "question_key": payload.question_key,
        }
    ]
    assert len(refresh_calls) == 1
    assert len(refresh_calls[0]) == 2
    assert result["visual_frame"]["visual_frame_id"] == "vf-1"
    assert result["visual_frame"]["storage_uri"].startswith("s3://")
    assert result["face_result"]["capture_id"] == "face-cap-1"
    assert result["face_result"]["sample_count"] == 5
    assert result["face_result"]["valid_sample_count"] == 4
    assert result["pose_result"]["capture_id"] == "pose-cap-1"
    assert result["pose_result"]["sample_count"] == 5
    assert result["pose_result"]["valid_sample_count"] == 5
    assert result["turn_bundle"]["turn_id"] == payload.turn_id
    assert db_session.refreshed == [session]
