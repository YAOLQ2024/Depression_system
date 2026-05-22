from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.schemas.multimodal import SubmitFrameCaptureRequest
from app.services.non_eeg_runtime import NonEegRuntimeStore
from app.services.multimodal_session_service import (
    MultimodalServiceError,
    _build_failed_pose_result,
    _normalize_pose_result,
    _refresh_live_payload,
    submit_pose_capture,
)


def _build_pose_payload() -> SubmitFrameCaptureRequest:
    now = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)
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
        sample_index=4,
        frame_id="pose-4",
    )


def test_normalize_pose_result_collecting_stays_processing() -> None:
    payload = _build_pose_payload()

    result = _normalize_pose_result(
        {
            "status": "ok",
            "label": "collecting",
            "score": 0.0,
            "extra": {"confidences": {}},
        },
        payload,
    )

    assert result["status"] == "pending"
    assert result["processing_status"] == "processing"
    assert result["primary_label"] is None
    assert result["top_3_labels"] == []
    assert result["error_message"] is None


def test_normalize_pose_result_no_pose_keeps_quality_flag() -> None:
    payload = _build_pose_payload()

    result = _normalize_pose_result(
        {
            "status": "no_pose",
            "label": "no_pose",
            "score": 0.0,
            "extra": {"confidences": {}},
        },
        payload,
    )

    assert result["status"] == "ready"
    assert result["processing_status"] == "completed"
    assert result["quality_flags"]["no_pose"] is True
    assert result["error_message"] is None


def test_build_failed_pose_result_returns_standardized_payload() -> None:
    payload = _build_pose_payload()

    result = _build_failed_pose_result(payload, error_message="pose_inference_failed")

    assert result["modality"] == "pose"
    assert result["status"] == "failed"
    assert result["processing_status"] == "failed"
    assert result["quality_flags"] == {
        "no_pose": False,
        "body_cutoff": False,
        "motion_blur": False,
    }
    assert result["error_message"] == "pose_inference_failed"


def test_refresh_live_payload_copies_pose_runtime_fields() -> None:
    session = SimpleNamespace(
        live_state_payload={},
        updated_at=None,
        status="created",
    )

    _refresh_live_payload(
        session,
        {
            "modality": "pose",
            "status": "failed",
            "processing_status": "failed",
            "primary_label": None,
            "primary_score": None,
            "top_3_labels": [],
            "quality_flags": {"no_pose": False, "body_cutoff": True, "motion_blur": False},
            "sample_ended_at": "2026-05-22T12:00:00+00:00",
            "sample_count": 5,
            "valid_sample_count": 3,
            "error_message": "pose_inference_failed",
        },
    )

    pose_live = session.live_state_payload["pose"]
    assert pose_live["status"] == "failed"
    assert pose_live["processing_status"] == "failed"
    assert pose_live["sample_count"] == 5
    assert pose_live["valid_sample_count"] == 3
    assert pose_live["error_message"] == "pose_inference_failed"
    assert session.status == "active"


def test_pose_runtime_store_reuses_engine_but_isolates_turn_state(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.non_eeg_runtime.build_pose_runtime_engine",
        lambda **kwargs: SimpleNamespace(engine_id="shared-engine"),
    )
    monkeypatch.setattr(
        "app.services.non_eeg_runtime.build_pose_turn_state",
        lambda pose_window: SimpleNamespace(
            pose_window=pose_window,
            pose_buffer=[],
            last_used_at=0.0,
        ),
    )

    store = NonEegRuntimeStore()

    engine_a = store.get_pose_engine()
    engine_b = store.get_pose_engine()
    turn_state_a = store.get_pose_turn_state("session-1", "turn-1")
    turn_state_b = store.get_pose_turn_state("session-1", "turn-2")
    turn_state_a_again = store.get_pose_turn_state("session-1", "turn-1")

    assert engine_a is engine_b
    assert turn_state_a is turn_state_a_again
    assert turn_state_a is not turn_state_b


def test_pose_runtime_store_can_clear_and_prune_turn_state(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.non_eeg_runtime.build_pose_runtime_engine",
        lambda **kwargs: SimpleNamespace(engine_id="shared-engine"),
    )
    monkeypatch.setattr(
        "app.services.non_eeg_runtime.build_pose_turn_state",
        lambda pose_window: SimpleNamespace(
            pose_window=pose_window,
            pose_buffer=[],
            last_used_at=0.0,
        ),
    )

    store = NonEegRuntimeStore()
    turn_state = store.get_pose_turn_state("session-1", "turn-1")
    turn_state.last_used_at = 1.0

    assert store.clear_pose_turn_state("session-1", "turn-1") is True
    assert store.clear_pose_turn_state("session-1", "turn-1") is False

    stale_state = SimpleNamespace(pose_window=96, pose_buffer=[], last_used_at=1.0)
    active_state = SimpleNamespace(pose_window=96, pose_buffer=[], last_used_at=10_080.0)
    store._pose_turn_states["session-1:turn-2"] = stale_state
    store._pose_turn_states["session-1:turn-3"] = active_state

    monkeypatch.setattr("app.services.non_eeg_runtime.time.time", lambda: 10_100.0)
    removed = store.prune_pose_turn_states(60)

    assert removed == 1
    assert store._pose_turn_states["session-1:turn-3"] is active_state


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


def test_submit_pose_capture_success_updates_live_and_bundle_counts(monkeypatch) -> None:
    payload = _build_pose_payload()
    now = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)
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
        lambda **kwargs: "s3://mcs-multimodal/captures/pose/mm-session-1/turn-1/sample-4.jpg",
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._record_capture",
        lambda *args, **kwargs: SimpleNamespace(
            id="pose-cap-004",
            created_at=now,
            storage_uri=None,
        ),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service.infer_pose_emotion",
        lambda request: (
            {
                "code": 0,
                "message": "ok",
                "data": {
                    "result": {
                        "status": "ok",
                        "label": "轻微前倾",
                        "score": 0.62,
                        "extra": {"confidences": {"轻微前倾": 0.62, "中性": 0.38}},
                    }
                },
            }
            if request.turn_id == payload.turn_id
            else (_ for _ in ()).throw(AssertionError("turn_id not forwarded"))
        ),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._record_inference_result",
        lambda *args, **kwargs: inference_rows.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._upsert_turn_bundle",
        lambda *args, **kwargs: {
            "turn_id": payload.turn_id,
            "pose_features": {
                "summary_type": "turn_window",
                "primary_label": "轻微前倾",
                "primary_score": 0.625,
                "primary_ratio": 0.625,
                "sample_count": 8,
                "valid_sample_count": 8,
                "label_distribution": [],
                "quality_distribution": {},
                "quality_flags": {},
            },
        },
    )

    result = submit_pose_capture("mm-session-1", payload, acting_user_id="user-1")

    assert result["capture_id"] == "pose-cap-004"
    assert result["processing_status"] == "completed"
    assert result["sample_count"] == 8
    assert result["valid_sample_count"] == 8
    assert result["storage_uri"].startswith("s3://")
    assert inference_rows[0]["inference_payload"]["primary_label"] == "轻微前倾"
    pose_live = session.live_state_payload["pose"]
    assert pose_live["status"] == "ready"
    assert pose_live["sample_count"] == 8
    assert pose_live["valid_sample_count"] == 8
    assert pose_live["error_message"] is None


def test_submit_pose_capture_failure_returns_standardized_failed_payload(monkeypatch) -> None:
    payload = _build_pose_payload()
    now = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)
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
            id="pose-cap-failed",
            created_at=now,
            storage_uri=None,
        ),
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service.infer_pose_emotion",
        lambda request: {"code": 5001, "message": "pose_inference_failed", "data": {}},
    )
    monkeypatch.setattr(
        "app.services.multimodal_session_service._extract_result_or_raise",
        lambda response: (_ for _ in ()).throw(
            MultimodalServiceError("pose_inference_failed", 5001, 500)
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

    result = submit_pose_capture("mm-session-2", payload, acting_user_id="user-2")

    assert result["capture_id"] == "pose-cap-failed"
    assert result["processing_status"] == "failed"
    assert result["error_message"] == "pose_inference_failed"
    assert result["sample_count"] == payload.sample_index
    assert result["valid_sample_count"] is None
    assert result["storage_uri"] is None
    assert inference_rows[0]["inference_payload"]["status"] == "failed"
    assert session.live_state_payload["pose"]["status"] == "failed"
