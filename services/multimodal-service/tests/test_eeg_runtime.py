from __future__ import annotations

import numpy as np

from app.config import get_settings
from app.services.eeg_protocol import build_feature_frame
from app.services.eeg_runtime import EEGBleProvider, EEGRuntimeService


class RecordingScaler:
    def __init__(self) -> None:
        self.last_input: np.ndarray | None = None

    def transform(self, values: np.ndarray) -> np.ndarray:
        self.last_input = np.asarray(values, dtype=np.float32)
        return self.last_input


class ConstantClassifier:
    classes_ = np.array([0, 1, 2], dtype=int)

    def predict(self, values: np.ndarray) -> np.ndarray:
        return np.array([1], dtype=int)

    def predict_proba(self, values: np.ndarray) -> np.ndarray:
        return np.array([[0.2, 0.6, 0.2]], dtype=np.float32)


class FakeBleDevice:
    def __init__(self, *, name: str | None = None, address: str = "") -> None:
        self.name = name
        self.address = address


def test_runtime_emits_result_only_after_ten_filtered_feature_frames(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setitem(settings, "eeg_enabled", True)
    monkeypatch.setitem(settings, "eeg_window_seconds", 10)
    monkeypatch.setitem(settings, "eeg_min_feature_frames", 10)

    runtime = EEGRuntimeService()
    scaler = RecordingScaler()

    runtime._clf = ConstantClassifier()
    runtime._scaler = scaler
    runtime._selected_features = np.arange(52, dtype=int)
    runtime._all_feature_names = [f"feat_{index}" for index in range(52)]
    runtime._model_name = "RF_n200_maxd8"
    runtime._model_version = "test-version"
    runtime._model_loaded = True

    monkeypatch.setattr(runtime, "_load_model_locked", lambda: True)
    monkeypatch.setattr(runtime, "_ensure_provider_started_locked", lambda: None)
    monkeypatch.setattr(runtime, "_upload_raw_window", lambda *args, **kwargs: None)
    monkeypatch.setattr(runtime, "_record_window_result_locked", lambda *args, **kwargs: None)

    runtime.begin_turn(
        session_id="session-1",
        turn_id="turn-1",
        flow_run_id="flow-1",
        stage_id="stage-1",
        question_key="question-1",
    )

    frame = build_feature_frame([float(index) for index in range(57)])
    expected_vector = [float(index) for index in range(57) if index not in (26, 41, 46, 54, 55)]

    for _ in range(9):
        runtime.ingest_transport_bytes(frame)

    payload = runtime.get_session_live_payload("session-1")
    assert payload["eeg_live"]["latest_result"] is None
    assert runtime._active_binding is not None
    assert runtime._active_binding.window_index == 1

    runtime.ingest_transport_bytes(frame)

    payload = runtime.get_session_live_payload("session-1")
    latest_result = payload["eeg_live"]["latest_result"]
    assert latest_result is not None
    assert latest_result["window_index"] == 1
    assert latest_result["feature_frame_count"] == 10
    assert latest_result["primary_label"] == "\u4e2d\u6027"
    assert runtime._active_binding is not None
    assert runtime._active_binding.window_index == 2
    assert scaler.last_input is not None
    assert scaler.last_input.shape == (1, 52)
    assert scaler.last_input[0].tolist() == expected_vector


def test_runtime_clears_stale_device_error_when_scan_restarts(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setitem(settings, "eeg_enabled", True)

    runtime = EEGRuntimeService()
    runtime._last_error = "[Errno 2] No such file or directory"

    runtime._update_device_status("scanning", None, None)

    assert runtime._device_status == "scanning"
    assert runtime._last_error is None


def test_runtime_warmup_does_not_auto_start_ble_provider(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setitem(settings, "eeg_enabled", True)

    runtime = EEGRuntimeService()
    starts: list[str] = []

    monkeypatch.setattr(runtime, "_load_model_locked", lambda: True)
    monkeypatch.setattr(runtime._provider, "start", lambda: starts.append("start"))

    snapshot = runtime.warmup()

    assert snapshot["model_loaded"] is True
    assert starts == []
    assert runtime._provider_started is False
    assert runtime._device_status == "idle"


def test_runtime_releases_ble_provider_after_turn_finishes(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setitem(settings, "eeg_enabled", True)

    runtime = EEGRuntimeService()
    events: list[str] = []

    monkeypatch.setattr(runtime, "_load_model_locked", lambda: True)
    monkeypatch.setattr(runtime._provider, "start", lambda: events.append("start"))
    monkeypatch.setattr(runtime._provider, "stop", lambda: events.append("stop"))

    runtime._last_error = "device_busy"
    runtime.begin_turn(
        session_id="session-1",
        turn_id="turn-1",
        flow_run_id="flow-1",
        stage_id="stage-1",
        question_key="question-1",
    )

    result = runtime.finish_turn(
        session_id="session-1",
        turn_id="turn-1",
        reason="completed",
    )

    assert result["status"] == "finished"
    assert events == ["start", "stop"]
    assert runtime._provider_started is False
    assert runtime._device_status == "idle"
    assert runtime._device_id is None
    assert runtime._last_error is None


def test_ble_provider_matches_hint_against_ble_address(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setitem(settings, "eeg_device_name_hint", "77:E3:66")

    provider = EEGBleProvider(on_bytes=lambda _: None)
    device = FakeBleDevice(name=None, address="77:E3:66:67:9E:F3")

    assert provider._matches_device_hint(device, local_name=None) is True


def test_ble_provider_reports_actionable_error_for_unnamed_devices(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setitem(settings, "eeg_device_name_hint", "EEG")

    provider = EEGBleProvider(on_bytes=lambda _: None)
    scanned_devices = [(FakeBleDevice(name=None, address="77:E3:66:67:9E:F3"), None)]

    error = provider._build_not_found_error(scanned_devices)

    assert "all advertisements are unnamed" in error
    assert "EEG_DEVICE_NAME_HINT" in error
