"""M1 uses independent calibration, then disjoint four-frame windows.

All input frames in this suite are synthetic; numerical agreement does not
measure emotion classification accuracy on participants.
"""
import io
import pickle
from pathlib import Path

import numpy as np
import pytest

from app.config import get_settings
from app.services.eeg_model_runtime import ModelRuntime, normalize_bundle
from app.services.eeg_protocol import (
    FEATURE_COUNT,
    KEPT_FEATURE_INDICES,
    MODEL_FEATURE_COUNT,
    MODEL_FEATURE_NAMES,
    build_feature_frame,
    build_wave_frame,
)
from app.services.eeg_runtime import EEGRuntimeService


@pytest.fixture
def bundle():
    path = Path(__file__).resolve().parents[1] / "runtime-assets/eeg/EEG_model.pkl"
    return pickle.loads(path.read_bytes())


def packet(row):
    raw = np.full(FEATURE_COUNT, -999., dtype=np.float32)
    raw[list(KEPT_FEATURE_INDICES)] = row
    return build_feature_frame(raw)


def begin(runtime, session="participant-a", turn="turn-1"):
    return runtime.begin_turn(
        session_id=session, turn_id=turn, flow_run_id=None, stage_id=None, question_key=None,
    )


@pytest.fixture
def runtime(monkeypatch):
    settings = get_settings()
    monkeypatch.setitem(settings, "eeg_enabled", True)
    monkeypatch.setitem(settings, "eeg_require_transport_for_ready", False)
    monkeypatch.setitem(settings, "redis_enabled", False)
    service = EEGRuntimeService()
    monkeypatch.setattr(service, "_ensure_provider_started_locked", lambda: None)
    monkeypatch.setattr(service, "_upload_raw_window", lambda *a, **k: None)
    records = []
    monkeypatch.setattr(
        service, "_record_window_result_locked",
        lambda binding, **kwargs: records.append(kwargs["inference_payload"]),
    )
    assert service.warmup_model(), service._last_error
    return service, records


def test_m1_metadata_is_normalized_without_mutating_bundle(bundle):
    original = dict(bundle)
    # Also accept the training export before local runtime metadata was added.
    for key in ("trial_feature_names", "selected_features", "norm_mode", "runtime_window_frames"):
        bundle.pop(key, None)
    normalized = normalize_bundle(bundle)
    assert "norm_mode" not in bundle
    assert normalized["norm_mode"] == "independent_calibration"
    assert normalized["selected_features"] == list(range(156))
    assert normalized["runtime_window_frames"] == 4
    assert normalized["runtime_calibration_frames"] == 87
    assert normalized["window_feature_names"] == list(MODEL_FEATURE_NAMES)
    assert normalized["trial_feature_names"] == original["trial_feature_names"]
    assert len(MODEL_FEATURE_NAMES) == MODEL_FEATURE_COUNT == 52


def test_adapter_uses_sample_std_floor_and_fixed_independent_statistics(bundle):
    adapter = ModelRuntime(bundle)
    rng = np.random.RandomState(53)
    calibration = rng.normal(10., 3., size=(87, 52)).astype(np.float32)
    calibration[:, 0] = 2.  # Exercise the 1e-8 floor on a constant feature.
    window = rng.normal(11., 2., size=(4, 52)).astype(np.float32)
    window[:, 0] = 2.
    with pytest.raises(ValueError, match="eeg_calibration_required"):
        adapter.prepare(window)
    for index, row in enumerate(calibration):
        assert adapter.add_calibration(row) == (index == 86)
    values = calibration.astype(float)
    expected_mean = values.mean(axis=0)
    expected_std = np.maximum(values.std(axis=0, ddof=1), 1e-8)
    normalized = (window.astype(float) - expected_mean) / expected_std
    time_axis = np.arange(4, dtype=float)
    time_axis -= time_axis.mean()
    expected = np.concatenate([
        np.median(normalized, axis=0), normalized.std(axis=0),
        np.mean(normalized * (time_axis / time_axis.std())[:, None], axis=0),
    ])
    full, scaled = adapter.prepare(window)
    np.testing.assert_array_equal(adapter.mean, expected_mean)
    np.testing.assert_array_equal(adapter.std, expected_std)
    np.testing.assert_array_equal(full, expected)
    np.testing.assert_array_equal(scaled, bundle["scaler"].transform(expected.reshape(1, -1)))
    adapter.prepare(window + 5)
    assert adapter.add_calibration(np.zeros(52))
    np.testing.assert_array_equal(adapter.mean, expected_mean)
    assert len(adapter.calibration_rows) == 87
    for count in (0, 3, 5):
        with pytest.raises(ValueError):
            adapter.prepare(np.ones((count, 52)))


@pytest.mark.parametrize("bad_rows", [np.ones((1, 52)), np.ones((87, 51)), np.full((87, 52), np.nan)])
def test_adapter_rejects_invalid_calibration(bundle, bad_rows):
    adapter = ModelRuntime(bundle)
    with pytest.raises(ValueError, match="invalid_eeg_calibration_rows"):
        adapter.set_calibration(bad_rows)
    assert not adapter.calibrated


def test_calibration_npz_requires_explicit_calibration_array(bundle, tmp_path):
    adapter = ModelRuntime(bundle)
    path = tmp_path / "calibration.npz"
    np.savez(path, feature_frames=np.ones((87, 52)))
    with pytest.raises(ValueError, match="eeg_calibration_array_missing"):
        adapter.load_calibration(path)
    np.savez(path, calibration=np.arange(87 * 52).reshape(87, 52))
    adapter.load_calibration(path)
    assert adapter.calibrated
    adapter.reset_calibration()
    assert not adapter.calibrated and adapter.calibration_rows == []


def test_adapter_rejects_feature_order_or_dimension_mismatch(bundle):
    reordered = {**bundle, "window_feature_names": list(reversed(MODEL_FEATURE_NAMES))}
    with pytest.raises(ValueError, match="eeg_packet_feature_order_mismatch"):
        ModelRuntime(reordered)
    bundle["scaler"].n_features_in_ = 110
    with pytest.raises(ValueError, match="eeg_model_feature_dimension_mismatch"):
        ModelRuntime(bundle)


def test_service_calibrates_before_first_four_frame_prediction(runtime, bundle, monkeypatch):
    service, records = runtime
    snapshot = service.status_snapshot()
    assert snapshot["model_loaded"] and snapshot["ready"]
    assert not snapshot["classification_ready"]
    assert snapshot["calibration"]["status"] == "pending"
    assert service._window_feature_frames == service._min_feature_frames == 4
    rng = np.random.RandomState(17)
    calibration = rng.normal(size=(87, 52)).astype(np.float32)
    windows = rng.normal(2., 1., size=(8, 52)).astype(np.float32)
    # Frames arriving before a participant attaches must never seed calibration.
    service.ingest_transport_bytes(packet(calibration[0]))
    assert begin(service)["calibration"]["collected_frames"] == 0
    service.ingest_transport_bytes(packet(np.full(52, np.nan)))
    assert service.status_snapshot()["calibration"]["collected_frames"] == 0
    for i, row in enumerate(calibration):
        service.ingest_transport_bytes(build_wave_frame(i, [1, 2, 3]))
        service.ingest_transport_bytes(packet(row))
        live = service.get_session_live_payload("participant-a")["eeg_live"]
        assert live["latest_result"] is None
        assert live["calibration"]["collected_frames"] == i + 1
    assert records == []
    assert live["calibration"]["status"] == "ready"
    assert service.status_snapshot()["classification_ready"]
    assert not service._active_binding.current_window.feature_samples
    assert not service._active_binding.current_window.wave_samples
    for row in windows[:3]:
        service.ingest_transport_bytes(packet(row))
    assert records == []
    raw_windows = []
    monkeypatch.setattr(
        service, "_upload_raw_window",
        lambda binding, snapshot: raw_windows.append(service._serialize_window_npz_bytes(binding, snapshot)),
    )
    service.ingest_transport_bytes(packet(windows[3]))
    assert len(records) == 1
    assert records[0]["feature_frame_count"] == 4
    expected = ModelRuntime(bundle)
    expected.set_calibration(calibration)
    full, scaled = expected.prepare(windows[:4])
    frozen = records[0]["_explanation_input"]
    assert frozen["pipeline_version"] == "independent-calibration-mss-v1"
    np.testing.assert_array_equal(frozen["aggregate_vector"], full)
    np.testing.assert_array_equal(frozen["scaled_vector"], scaled[0])
    assert records[0]["primary_label"] == {0: "消极", 1: "中性", 2: "积极"}[int(bundle["model"].predict(scaled)[0])]
    with np.load(io.BytesIO(raw_windows[0]), allow_pickle=False) as raw:
        np.testing.assert_array_equal(raw["feature_frames"], windows[:4])
        np.testing.assert_array_equal(raw["aggregate_vector"], full)
        np.testing.assert_array_equal(raw["scaled_vector"], scaled[0])
    for row in windows[4:]:
        service.ingest_transport_bytes(packet(row))
    assert len(records) == 2
    np.testing.assert_array_equal(service._m1_runtime.mean, calibration.astype(float).mean(axis=0))


def test_session_calibration_survives_turns_but_never_crosses_participants(runtime):
    service, records = runtime
    row = np.arange(52, dtype=np.float32)
    begin(service)
    for i in range(40):
        service.ingest_transport_bytes(packet(row + i))
    # An idempotent begin and a gap between turns preserve partial calibration.
    assert begin(service)["calibration"]["collected_frames"] == 40
    service.finish_turn(session_id="participant-a", turn_id="turn-1")
    service.ingest_transport_bytes(packet(row + 999))
    assert begin(service, turn="turn-2")["calibration"]["collected_frames"] == 40
    for i in range(47):
        service.ingest_transport_bytes(packet(row + i + 40))
    assert service.status_snapshot()["calibration"]["status"] == "ready"
    mean = service._m1_runtime.mean.copy()
    # A forced turn finish must not classify an incomplete four-frame window.
    for i in range(3):
        service.ingest_transport_bytes(packet(row + i))
    service.finish_turn(session_id="participant-a", turn_id="turn-2")
    assert records == [None]
    assert begin(service, turn="turn-3")["calibration"]["status"] == "ready"
    np.testing.assert_array_equal(service._m1_runtime.mean, mean)
    for i in range(4):
        service.ingest_transport_bytes(packet(row + i))
    assert records[-1] is not None
    # Changing session also discards any partial packet from the previous one.
    encoded = packet(row)
    service.ingest_transport_bytes(encoded[:100])
    status = begin(service, session="participant-b")
    assert status["calibration"]["status"] == "collecting"
    assert status["calibration"]["collected_frames"] == 0
    service.ingest_transport_bytes(encoded[100:])
    assert service.status_snapshot()["calibration"]["collected_frames"] == 0
    assert service.get_session_live_payload("participant-b")["eeg_live"]["latest_result"] is None
    # Returning to an old session cannot reuse the intervening person's stats.
    service.ingest_transport_bytes(packet(row))
    assert begin(service)["calibration"]["collected_frames"] == 0
    service.shutdown()
    assert service.status_snapshot()["calibration"]["status"] == "pending"


def test_nonfinite_classification_window_is_not_predicted(runtime):
    service, records = runtime
    begin(service)
    for i in range(87):
        service.ingest_transport_bytes(packet(np.full(52, float(i))))
    for i in range(4):
        service.ingest_transport_bytes(packet(np.full(52, float(i) if i != 2 else np.inf)))
    assert records == [None]
    assert service.get_session_live_payload("participant-a")["eeg_live"]["latest_result"] is None
