from __future__ import annotations

import asyncio
import io
import logging
import pickle
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
from sqlalchemy.orm.attributes import flag_modified

from app.config import get_settings
from app.database import get_db_session
from app.models import MultimodalCapture, MultimodalInferenceResult, MultimodalSession
from app.services.eeg_live_state_store import (
    clear_eeg_turn_hot_state,
    read_eeg_live_payload,
    write_eeg_live_payload,
    write_eeg_turn_state_payload,
    write_eeg_turn_window_payload,
)
from app.services.eeg_protocol import EEGPacketDecoder, FeaturePacket, MODEL_FEATURE_COUNT, WavePacket
from app.services.object_storage import upload_object_to_bucket

logger = logging.getLogger(__name__)
EEG_LIVE_FLUSH_INTERVAL_SECONDS = 0.12
EEG_LABELS = {
    0: "\u6d88\u6781",
    1: "\u4e2d\u6027",
    2: "\u79ef\u6781",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _top_labels_from_scores(scores: dict[str, float], *, limit: int = 3) -> list[dict[str, Any]]:
    return [
        {"label": label, "score": float(score)}
        for label, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def _copy_labels(labels: list[dict[str, Any]] | None, *, limit: int = 3) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for item in labels or []:
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        copied.append({"label": label, "score": float(item.get("score") or 0.0)})
        if len(copied) >= limit:
            break
    return copied


def _softmax(scores: Sequence[float]) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float32)
    values = values - np.max(values)
    exp_values = np.exp(values)
    total = np.sum(exp_values)
    if total <= 0:
        return np.full_like(exp_values, 1.0 / max(1, exp_values.size), dtype=np.float32)
    return exp_values / total


def _predict_probabilities(clf: Any, scaled_vector: np.ndarray) -> np.ndarray:
    classes = list(getattr(clf, "classes_", [0, 1, 2]))
    probabilities = np.zeros(3, dtype=np.float32)
    clf_name = type(clf).__name__.lower()

    if hasattr(clf, "decision_function") and "svc" in clf_name:
        decision = np.asarray(clf.decision_function(scaled_vector), dtype=np.float32)
        if decision.ndim == 1:
            raw = _softmax(np.array([-decision[0], decision[0]], dtype=np.float32)) if len(classes) == 2 else _softmax(decision)
        else:
            raw = _softmax(decision[0])
    elif hasattr(clf, "predict_proba"):
        raw = np.asarray(clf.predict_proba(scaled_vector)[0], dtype=np.float32)
    elif hasattr(clf, "decision_function"):
        decision = np.asarray(clf.decision_function(scaled_vector), dtype=np.float32)
        if decision.ndim == 1:
            raw = _softmax(np.array([-decision[0], decision[0]], dtype=np.float32)) if len(classes) == 2 else _softmax(decision)
        else:
            raw = _softmax(decision[0])
    else:
        predicted = int(clf.predict(scaled_vector)[0])
        raw = np.zeros(len(classes), dtype=np.float32)
        if predicted in classes:
            raw[classes.index(predicted)] = 1.0

    for cls, prob in zip(classes, raw):
        cls_index = int(cls)
        if 0 <= cls_index < probabilities.size:
            probabilities[cls_index] = float(prob)

    total = float(probabilities.sum())
    if total <= 0:
        probabilities[:] = [1 / 3, 1 / 3, 1 / 3]
    else:
        probabilities /= total
    return probabilities


@dataclass(slots=True)
class EegWaveSample:
    seq: int
    captured_at: datetime
    values: tuple[float, float, float]


@dataclass(slots=True)
class EegFeatureSample:
    captured_at: datetime
    values: tuple[float, ...]


@dataclass(slots=True)
class EegWindowBuffer:
    sample_started_at: datetime | None = None
    sample_ended_at: datetime | None = None
    wave_samples: list[EegWaveSample] = field(default_factory=list)
    feature_samples: list[EegFeatureSample] = field(default_factory=list)


@dataclass(slots=True)
class EegTurnBinding:
    session_id: str
    turn_id: str
    flow_run_id: str | None
    stage_id: str | None
    question_key: str | None
    started_at: datetime
    preview_buffer: deque[dict[str, Any]]
    latest_results: deque[dict[str, Any]]
    pending_live_samples: list[dict[str, Any]] = field(default_factory=list)
    live_stream_reset_pending: bool = True
    window_index: int = 1
    window_indexes: list[int] = field(default_factory=list)
    last_live_flush_at: datetime | None = None
    last_sample_at: datetime | None = None
    current_window: EegWindowBuffer = field(default_factory=EegWindowBuffer)


class EEGBleProvider:
    def __init__(self, *, on_bytes: Callable[[bytes], None]) -> None:
        settings = get_settings()
        self._on_bytes = on_bytes
        self._name_hint = str(settings["eeg_device_name_hint"])
        self._notify_uuid = str(settings["eeg_notify_char_uuid"])
        self._scan_seconds = float(settings["eeg_scan_seconds"])
        self._reconnect_delay_seconds = float(settings["eeg_reconnect_delay_seconds"])
        self._stop_event = threading.Event()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._status_callback: Callable[[str, str | None, str | None], None] | None = None

    def set_status_callback(
        self,
        callback: Callable[[str, str | None, str | None], None],
    ) -> None:
        self._status_callback = callback

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._stopping.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="eeg-ble-provider",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._stopping.set()
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(lambda: None)
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2)
        if thread is not None and thread.is_alive():
            logger.warning("EEG BLE provider thread did not exit cleanly before timeout")
            return
        self._thread = None
        self._loop = None

    def _emit_status(self, status: str, *, device_id: str | None = None, error: str | None = None) -> None:
        if self._stopping.is_set():
            return
        if self._status_callback is not None:
            self._status_callback(status, device_id, error)

    @staticmethod
    def _device_name(device: Any) -> str:
        return str(getattr(device, "name", "") or "").strip()

    @staticmethod
    def _device_address(device: Any) -> str:
        return str(getattr(device, "address", "") or "").strip()

    def _matches_device_hint(self, device: Any, *, local_name: str | None = None) -> bool:
        hint = self._name_hint.strip()
        if not hint:
            return True
        normalized_hint = hint.upper()
        candidates = [
            self._device_name(device),
            str(local_name or "").strip(),
            self._device_address(device),
        ]
        return any(candidate and normalized_hint in candidate.upper() for candidate in candidates)

    async def _discover_devices(self, scanner_cls: Any) -> list[tuple[Any, str | None]]:
        try:
            discovered = await scanner_cls.discover(timeout=self._scan_seconds, return_adv=True)
        except TypeError:
            devices = await scanner_cls.discover(timeout=self._scan_seconds)
            return [(device, None) for device in devices]

        devices_with_names: list[tuple[Any, str | None]] = []
        for item in discovered.values():
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            device, advertisement = item
            local_name = str(getattr(advertisement, "local_name", "") or "").strip() or None
            devices_with_names.append((device, local_name))
        return devices_with_names

    def _build_not_found_error(self, scanned_devices: Sequence[tuple[Any, str | None]]) -> str:
        scan_count = len(scanned_devices)
        hint = self._name_hint.strip()
        unnamed_count = sum(
            1
            for device, local_name in scanned_devices
            if not self._device_name(device) and not str(local_name or "").strip()
        )
        if hint and scan_count > 0 and unnamed_count == scan_count:
            return (
                f"device_not_found: scan_count={scan_count}; "
                "all advertisements are unnamed; set EEG_DEVICE_NAME_HINT to the BLE address"
            )
        if hint:
            return f"device_not_found: hint={hint}; scan_count={scan_count}"
        return f"device_not_found: scan_count={scan_count}"

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_forever())
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    async def _run_forever(self) -> None:
        try:
            from bleak import BleakClient, BleakScanner
        except Exception as exc:
            self._emit_status("dependency_missing", error=str(exc))
            return

        while not self._stop_event.is_set():
            try:
                self._emit_status("scanning")
                devices = await self._discover_devices(BleakScanner)
                target_device = None
                for device, local_name in devices:
                    if self._matches_device_hint(device, local_name=local_name):
                        target_device = device
                        break
                if target_device is None:
                    self._emit_status("disconnected", error=self._build_not_found_error(devices))
                    await asyncio.sleep(self._reconnect_delay_seconds)
                    continue

                address = self._device_address(target_device)
                self._emit_status("connecting", device_id=address)

                def _handle_disconnect(_: Any) -> None:
                    self._emit_status("disconnected", device_id=address, error="device_disconnected")

                async with BleakClient(target_device, disconnected_callback=_handle_disconnect, timeout=15.0) as client:
                    self._emit_status("connected", device_id=address)

                    def _handle_notification(_: Any, data: bytearray) -> None:
                        self._on_bytes(bytes(data))

                    await client.start_notify(self._notify_uuid, _handle_notification)
                    self._emit_status("streaming", device_id=address)
                    while not self._stop_event.is_set() and client.is_connected:
                        await asyncio.sleep(0.5)
                    await client.stop_notify(self._notify_uuid)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("EEG BLE provider loop failed")
                self._emit_status("disconnected", error=str(exc))
                await asyncio.sleep(self._reconnect_delay_seconds)


class EEGRuntimeService:
    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = bool(settings["eeg_enabled"])
        self._provider_mode = str(settings["eeg_provider"])
        self._channel_names = list(settings["eeg_channel_names"])
        self._sampling_rate = int(settings["eeg_sampling_rate"])
        self._preview_seconds = max(1, int(settings["eeg_preview_seconds"]))
        self._window_seconds = max(1, int(settings["eeg_window_seconds"]))
        self._window_feature_frames = self._window_seconds
        self._min_feature_frames = max(1, int(settings["eeg_min_feature_frames"]))
        self._latest_results_limit = max(1, int(settings["eeg_latest_results_limit"]))
        self._preview_sample_limit = max(1, self._sampling_rate * self._preview_seconds)
        self._decoder = EEGPacketDecoder()
        self._lock = threading.RLock()
        self._provider = EEGBleProvider(on_bytes=self.ingest_transport_bytes)
        self._provider.set_status_callback(self._update_device_status)
        self._provider_started = False
        self._device_status = "disabled" if not self._enabled else "idle"
        self._device_id: str | None = None
        self._last_error: str | None = None
        self._active_binding: EegTurnBinding | None = None
        self._memory_live_payloads: dict[str, dict[str, Any]] = {}
        self._clf = None
        self._scaler = None
        self._selected_features: np.ndarray | None = None
        self._all_feature_names: list[str] = []
        self._model_name = "eeg_3class"
        self._model_version: str | None = None
        self._model_loaded = False
        self._live_update_callback: Callable[[str, dict[str, Any], dict[str, Any] | None], None] | None = None

    def warmup(self) -> dict[str, Any]:
        with self._lock:
            model_loaded = self._load_model_locked()
            # 服务启动时自动开始 BLE 扫描，无需等待 begin_turn
            self._ensure_provider_started_locked()
            return {
                "enabled": self._enabled,
                "provider": self._provider_mode,
                "device_status": self._device_status,
                "model_loaded": model_loaded,
                "model_version": self._model_version,
                "channel_names": list(self._channel_names),
                "sampling_rate": self._sampling_rate,
            }

    def status_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self._enabled,
                "provider": self._provider_mode,
                "provider_started": self._provider_started,
                "device_status": self._device_status,
                "device_id": self._device_id,
                "last_error": self._last_error,
                "model_loaded": bool(
                    self._clf is not None
                    and self._scaler is not None
                    and self._selected_features is not None
                    and self._selected_features.size > 0
                    and bool(self._all_feature_names)
                ),
                "model_name": self._model_name,
                "model_version": self._model_version,
                "channel_names": list(self._channel_names),
                "sampling_rate": self._sampling_rate,
            }

    def shutdown(self) -> None:
        with self._lock:
            self._active_binding = None
            self._stop_provider_locked(clear_error=False)

    def set_live_update_callback(
        self,
        callback: Callable[[str, dict[str, Any], dict[str, Any] | None], None] | None,
    ) -> None:
        with self._lock:
            self._live_update_callback = callback

    def begin_turn(
        self,
        *,
        session_id: str,
        turn_id: str,
        flow_run_id: str | None,
        stage_id: str | None,
        question_key: str | None,
    ) -> dict[str, Any]:
        with self._lock:
            self._load_model_locked()
            self._ensure_provider_started_locked()
            active = self._active_binding
            if active and active.session_id == session_id and active.turn_id == turn_id:
                self._write_binding_live_locked(active)
                return self._build_binding_status_payload_locked(active)
            if active is not None:
                self._finish_binding_locked(active, reason="rebound")
            binding = EegTurnBinding(
                session_id=session_id,
                turn_id=turn_id,
                flow_run_id=flow_run_id,
                stage_id=stage_id,
                question_key=question_key,
                started_at=_utcnow(),
                preview_buffer=deque(maxlen=self._preview_sample_limit),
                latest_results=deque(maxlen=self._latest_results_limit),
            )
            self._active_binding = binding
            self._write_binding_live_locked(binding)
            self._write_turn_state_locked(binding, status="active")
            return self._build_binding_status_payload_locked(binding)

    def finish_turn(self, *, session_id: str, turn_id: str, reason: str = "completed") -> dict[str, Any]:
        with self._lock:
            active = self._active_binding
            if active is None:
                # BLE provider 保持运行，下次 turn 无需重新扫描
                clear_eeg_turn_hot_state(session_id, turn_id, window_indexes=[])
                return {
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "status": "not_active",
                    "device_status": self._device_status,
                    "reason": reason,
                }
            if active.session_id != session_id or active.turn_id != turn_id:
                clear_eeg_turn_hot_state(session_id, turn_id, window_indexes=[])
                return {
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "status": "not_active",
                    "device_status": self._device_status,
                    "reason": reason,
                }
            self._finish_binding_locked(active, reason=reason)
            self._active_binding = None
            # BLE provider 保持运行，断连后自动重连，下次 turn 即刻就绪
            # 仅在 shutdown() 时才真正停止
            return {
                "session_id": session_id,
                "turn_id": turn_id,
                "status": "finished",
                "device_status": self._device_status,
                "reason": reason,
            }

    def get_session_live_payload(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            payload = read_eeg_live_payload(session_id)
            if payload is not None:
                return payload
            cached = self._memory_live_payloads.get(session_id)
            if cached is not None:
                return cached
            active = self._active_binding
            if active and active.session_id == session_id:
                return self._build_live_payload_locked(active)
            return self._build_pending_live_payload()

    def ingest_transport_bytes(self, chunk: bytes) -> None:
        with self._lock:
            for packet in self._decoder.feed(chunk):
                if isinstance(packet, WavePacket):
                    self._handle_wave_packet_locked(packet)
                elif isinstance(packet, FeaturePacket):
                    self._handle_feature_packet_locked(packet)

    def _ensure_provider_started_locked(self) -> None:
        if not self._enabled or self._provider_mode != "ble" or self._provider_started:
            return
        self._provider.start()
        self._provider_started = True

    def _stop_provider_locked(self, *, clear_error: bool) -> None:
        if self._provider_started:
            self._provider.stop()
            self._provider_started = False
        self._device_status = "disabled" if not self._enabled else "idle"
        self._device_id = None
        if clear_error:
            self._last_error = None

    def _load_model_locked(self) -> bool:
        if self._model_loaded:
            return (
                self._clf is not None
                and self._scaler is not None
                and self._selected_features is not None
                and bool(self._all_feature_names)
            )

        self._model_loaded = True
        model_path = Path(get_settings()["eeg_model_path"])
        if not model_path.exists():
            self._last_error = f"eeg_model_missing:{model_path.name}"
            logger.warning("EEG model asset is missing at %s", model_path)
            return False

        try:
            with model_path.open("rb") as fp:
                model_obj = pickle.load(fp)
            self._clf = model_obj.get("model")
            self._scaler = model_obj.get("scaler")
            selected = model_obj.get("selected_features")
            if selected is None:
                selected = []
            self._selected_features = np.array(selected, dtype=int)
            all_feature_names = model_obj.get("all_feature_names") or []
            self._all_feature_names = [str(name) for name in all_feature_names]
            if not self._all_feature_names:
                self._all_feature_names = [f"feat_{index}" for index in range(MODEL_FEATURE_COUNT)]
            self._model_name = str(model_obj.get("classifier_name") or self._model_name)
            self._model_version = str(
                model_obj.get("version")
                or model_obj.get("version_tag")
                or model_obj.get("feature_set_desc")
                or "unknown"
            )
            self._last_error = None
            return (
                self._clf is not None
                and self._scaler is not None
                and self._selected_features.size > 0
                and bool(self._all_feature_names)
            )
        except Exception as exc:
            self._last_error = str(exc)
            logger.exception("Failed to load EEG model asset")
            self._clf = None
            self._scaler = None
            self._selected_features = None
            self._all_feature_names = []
            return False

    def _update_device_status(self, status: str, device_id: str | None, error: str | None) -> None:
        with self._lock:
            self._device_status = status
            self._device_id = device_id
            if error:
                self._last_error = error
            elif status in {"idle", "scanning", "connecting", "connected", "streaming"}:
                self._last_error = None
            active = self._active_binding
            if active is not None:
                self._write_binding_live_locked(active)

    def _handle_wave_packet_locked(self, packet: WavePacket) -> None:
        binding = self._active_binding
        if binding is None:
            return
        captured_at = _utcnow()
        sample = EegWaveSample(
            seq=int(packet.seq),
            captured_at=captured_at,
            values=tuple(packet.channels),
        )
        current_window = binding.current_window
        current_window.sample_started_at = current_window.sample_started_at or captured_at
        current_window.sample_ended_at = captured_at
        current_window.wave_samples.append(sample)
        binding.last_sample_at = captured_at
        sample_payload = {
            "seq": sample.seq,
            "captured_at": _isoformat(sample.captured_at),
            "values": [float(value) for value in sample.values],
        }
        binding.preview_buffer.append(sample_payload)
        binding.pending_live_samples.append(sample_payload)
        if (
            binding.last_live_flush_at is None
            or (captured_at - binding.last_live_flush_at).total_seconds() >= EEG_LIVE_FLUSH_INTERVAL_SECONDS
        ):
            self._write_binding_live_locked(binding)
            binding.last_live_flush_at = captured_at

    def _handle_feature_packet_locked(self, packet: FeaturePacket) -> None:
        binding = self._active_binding
        if binding is None:
            return
        captured_at = _utcnow()
        vector = np.asarray(packet.to_model_vector(), dtype=np.float32)
        expected_count = self._expected_feature_count()
        if vector.size != expected_count:
            logger.warning(
                "EEG feature dimension mismatch after filtering: received=%s expected=%s",
                vector.size,
                expected_count,
            )
            return
        feature_sample = EegFeatureSample(
            captured_at=captured_at,
            values=tuple(float(value) for value in vector),
        )
        current_window = binding.current_window
        current_window.sample_started_at = current_window.sample_started_at or captured_at
        current_window.sample_ended_at = captured_at
        current_window.feature_samples.append(feature_sample)
        binding.last_sample_at = captured_at
        if len(current_window.feature_samples) >= self._window_feature_frames:
            self._finalize_window_locked(binding, reason="window_complete")

    def _expected_feature_count(self) -> int:
        if self._all_feature_names:
            return len(self._all_feature_names)
        return MODEL_FEATURE_COUNT

    def _finish_binding_locked(self, binding: EegTurnBinding, *, reason: str) -> None:
        self._finalize_window_locked(binding, reason=reason, force=True)
        clear_eeg_turn_hot_state(
            binding.session_id,
            binding.turn_id,
            window_indexes=binding.window_indexes,
        )
        base_payload = self._build_live_payload_locked(binding)
        final_payload = {
            **base_payload,
            "eeg_waves": {
                **dict(base_payload.get("eeg_waves") or {}),
                "samples": [],
                "status": "pending",
            },
        }
        self._store_live_payload_locked(binding.session_id, final_payload)

    def _serialize_window_npz_bytes(self, binding: EegTurnBinding) -> bytes:
        wave_samples = binding.current_window.wave_samples
        feature_samples = binding.current_window.feature_samples
        sample_values = (
            np.array([sample.values for sample in wave_samples], dtype=np.float32)
            if wave_samples
            else np.zeros((0, len(self._channel_names)), dtype=np.float32)
        )
        sample_sequences = np.array([sample.seq for sample in wave_samples], dtype=np.int32)
        sample_timestamps_ms = np.array(
            [int(sample.captured_at.timestamp() * 1000) for sample in wave_samples],
            dtype=np.int64,
        )
        feature_values = (
            np.array([sample.values for sample in feature_samples], dtype=np.float32)
            if feature_samples
            else np.zeros((0, self._expected_feature_count()), dtype=np.float32)
        )
        feature_timestamps_ms = np.array(
            [int(sample.captured_at.timestamp() * 1000) for sample in feature_samples],
            dtype=np.int64,
        )
        buffer = io.BytesIO()
        np.savez_compressed(
            buffer,
            samples=sample_values,
            sequences=sample_sequences,
            sample_timestamps_ms=sample_timestamps_ms,
            feature_frames=feature_values,
            feature_timestamps_ms=feature_timestamps_ms,
            channel_names=np.array(self._channel_names),
            sampling_rate=np.array(self._sampling_rate, dtype=np.int32),
            window_index=np.array(binding.window_index, dtype=np.int32),
        )
        return buffer.getvalue()

    def _upload_raw_window(self, binding: EegTurnBinding) -> str | None:
        object_key = (
            f"raw/eeg/{binding.session_id}/{binding.turn_id}/window-{binding.window_index}.npz"
        )
        try:
            return upload_object_to_bucket(
                bucket_name=str(get_settings()["multimodal_bucket"]),
                object_key=object_key,
                file_bytes=self._serialize_window_npz_bytes(binding),
                content_type="application/octet-stream",
            )
        except Exception:
            logger.warning(
                "EEG raw window upload failed session_id=%s turn_id=%s window_index=%s",
                binding.session_id,
                binding.turn_id,
                binding.window_index,
                exc_info=True,
            )
            return None

    def _infer_window_locked(
        self,
        binding: EegTurnBinding,
        *,
        raw_eeg_uri: str | None,
    ) -> dict[str, Any] | None:
        current_window = binding.current_window
        if len(current_window.feature_samples) < self._min_feature_frames:
            return None
        if self._clf is None or self._scaler is None or self._selected_features is None:
            return None

        features_matrix = np.array(
            [sample.values for sample in current_window.feature_samples],
            dtype=np.float32,
        )
        median_vector = np.median(features_matrix, axis=0)
        if median_vector.size != self._expected_feature_count():
            logger.warning(
                "EEG median feature dimension mismatch: received=%s expected=%s",
                median_vector.size,
                self._expected_feature_count(),
            )
            return None
        if np.any(self._selected_features < 0) or np.any(self._selected_features >= median_vector.size):
            logger.warning("EEG selected feature indices exceed median vector size=%s", median_vector.size)
            return None
        selected = median_vector[self._selected_features].reshape(1, -1)
        scaled = self._scaler.transform(selected)
        prediction = int(self._clf.predict(scaled)[0])

        probabilities = _predict_probabilities(self._clf, scaled)

        label_map = {0: "消极", 1: "中性", 2: "积极"}
        score_map = {
            EEG_LABELS.get(index, str(index)): float(probabilities[index])
            for index in range(min(len(probabilities), len(EEG_LABELS)))
        }
        primary_label = EEG_LABELS.get(prediction, str(prediction))
        return {
            "modality": "eeg",
            "status": "ready",
            "device_status": self._device_status,
            "window_index": binding.window_index,
            "question_key": binding.question_key,
            "flow_run_id": binding.flow_run_id,
            "turn_id": binding.turn_id,
            "primary_label": primary_label,
            "primary_score": float(score_map.get(primary_label, 0.0)),
            "top_3_labels": _top_labels_from_scores(score_map, limit=3),
            "sample_started_at": _isoformat(current_window.sample_started_at),
            "sample_ended_at": _isoformat(current_window.sample_ended_at),
            "feature_frame_count": len(current_window.feature_samples),
            "channel_names": list(self._channel_names),
            "sampling_rate": self._sampling_rate,
            "model_name": self._model_name,
            "model_version": self._model_version,
            "raw_eeg_uri": raw_eeg_uri,
            "quality_flags": {},
        }

    def _record_window_result_locked(
        self,
        binding: EegTurnBinding,
        *,
        raw_eeg_uri: str | None,
        inference_payload: dict[str, Any] | None,
    ) -> None:
        current_window = binding.current_window
        now = _utcnow()
        with get_db_session() as db_session:
            capture = MultimodalCapture(
                session_id=binding.session_id,
                turn_id=binding.turn_id,
                flow_run_id=binding.flow_run_id,
                stage_id=binding.stage_id,
                question_key=binding.question_key,
                sample_index=binding.window_index,
                sample_started_at=current_window.sample_started_at,
                sample_ended_at=current_window.sample_ended_at,
                modality="eeg",
                capture_kind="window",
                source_ref_id=str(binding.window_index),
                storage_uri=raw_eeg_uri,
                capture_payload={
                    "window_index": binding.window_index,
                    "sampling_rate": self._sampling_rate,
                    "channel_names": list(self._channel_names),
                    "wave_sample_count": len(current_window.wave_samples),
                    "feature_frame_count": len(current_window.feature_samples),
                    "raw_eeg_uri": raw_eeg_uri,
                },
                captured_at=current_window.sample_ended_at,
                created_at=now,
            )
            db_session.add(capture)
            db_session.flush()

            if inference_payload is not None:
                result_row = MultimodalInferenceResult(
                    session_id=binding.session_id,
                    turn_id=binding.turn_id,
                    flow_run_id=binding.flow_run_id,
                    stage_id=binding.stage_id,
                    question_key=binding.question_key,
                    sample_id=capture.id,
                    modality="eeg",
                    source_kind="eeg_window",
                    source_ref_id=str(binding.window_index),
                    inference_payload=inference_payload,
                    captured_at=current_window.sample_ended_at,
                    created_at=now,
                )
                db_session.add(result_row)

                session = db_session.get(MultimodalSession, binding.session_id)
                if session is not None:
                    live_state_payload = dict(session.live_state_payload or {})
                    live_state_payload["eeg_live"] = {
                        "status": inference_payload.get("status", "ready"),
                        "device_status": self._device_status,
                        "channel_names": list(self._channel_names),
                        "sampling_rate": self._sampling_rate,
                        "updated_at": inference_payload.get("sample_ended_at"),
                        "latest_result": {
                            "window_index": inference_payload.get("window_index"),
                            "primary_label": inference_payload.get("primary_label"),
                            "primary_score": inference_payload.get("primary_score"),
                            "top_3_labels": _copy_labels(inference_payload.get("top_3_labels")),
                            "feature_frame_count": inference_payload.get("feature_frame_count"),
                        },
                    }
                    session.live_state_payload = live_state_payload
                    session.updated_at = now
                    flag_modified(session, "live_state_payload")
                    db_session.add(session)

    def _build_window_payload(
        self,
        binding: EegTurnBinding,
        *,
        raw_eeg_uri: str | None,
        inference_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        current_window = binding.current_window
        payload = {
            "session_id": binding.session_id,
            "turn_id": binding.turn_id,
            "flow_run_id": binding.flow_run_id,
            "stage_id": binding.stage_id,
            "question_key": binding.question_key,
            "window_index": binding.window_index,
            "sample_started_at": _isoformat(current_window.sample_started_at),
            "sample_ended_at": _isoformat(current_window.sample_ended_at),
            "raw_eeg_uri": raw_eeg_uri,
            "wave_sample_count": len(current_window.wave_samples),
            "feature_frame_count": len(current_window.feature_samples),
            "channel_names": list(self._channel_names),
            "sampling_rate": self._sampling_rate,
            "model_version": self._model_version,
            "quality_flags": {},
        }
        if inference_payload is not None:
            payload["primary_label"] = inference_payload.get("primary_label")
            payload["primary_score"] = inference_payload.get("primary_score")
            payload["top_3_labels"] = _copy_labels(inference_payload.get("top_3_labels"))
        else:
            payload["primary_label"] = None
            payload["primary_score"] = None
            payload["top_3_labels"] = []
        return payload

    def _write_turn_state_locked(self, binding: EegTurnBinding, *, status: str) -> None:
        current_window = binding.current_window
        write_eeg_turn_state_payload(
            binding.session_id,
            binding.turn_id,
            {
                "session_id": binding.session_id,
                "turn_id": binding.turn_id,
                "status": status,
                "started_at": _isoformat(binding.started_at),
                "last_updated_at": _isoformat(binding.last_sample_at or binding.started_at),
                "window_count": max(0, binding.window_index - 1),
                "last_window_index": binding.window_indexes[-1] if binding.window_indexes else None,
                "last_window_started_at": _isoformat(current_window.sample_started_at),
                "last_window_ended_at": _isoformat(current_window.sample_ended_at),
            },
        )

    def _build_live_payload_locked(self, binding: EegTurnBinding) -> dict[str, Any]:
        latest_results = list(binding.latest_results)
        return {
            "eeg_live": {
                "status": "ready" if binding.preview_buffer or latest_results else "pending",
                "device_status": self._device_status,
                "device_id": self._device_id,
                "channel_names": list(self._channel_names),
                "sampling_rate": self._sampling_rate,
                "updated_at": _isoformat(binding.last_sample_at or binding.started_at),
                "turn_id": binding.turn_id,
                "model_name": self._model_name,
                "model_version": self._model_version,
                "latest_result": latest_results[-1] if latest_results else None,
                "latest_results": latest_results,
                "error_message": self._last_error,
            },
            "eeg_waves": {
                "status": "ready" if binding.preview_buffer else "pending",
                "channel_names": list(self._channel_names),
                "sampling_rate": self._sampling_rate,
                "samples": list(binding.preview_buffer),
            },
        }

    def _build_pending_live_payload(self) -> dict[str, Any]:
        return {
            "eeg_live": {
                "status": "pending" if self._enabled else "disabled",
                "device_status": self._device_status,
                "device_id": self._device_id,
                "channel_names": list(self._channel_names),
                "sampling_rate": self._sampling_rate,
                "updated_at": None,
                "turn_id": None,
                "model_name": self._model_name,
                "model_version": self._model_version,
                "latest_result": None,
                "latest_results": [],
                "error_message": self._last_error,
            },
            "eeg_waves": {
                "status": "pending" if self._enabled else "disabled",
                "channel_names": list(self._channel_names),
                "sampling_rate": self._sampling_rate,
                "samples": [],
            },
        }

    def _build_live_wave_delta_locked(self, binding: EegTurnBinding) -> dict[str, Any] | None:
        if not binding.pending_live_samples and not binding.live_stream_reset_pending:
            return None
        return {
            "status": "ready" if binding.preview_buffer else "pending",
            "channel_names": list(self._channel_names),
            "sampling_rate": self._sampling_rate,
            "append_samples": list(binding.pending_live_samples),
            "reset": bool(binding.live_stream_reset_pending),
        }

    def _store_live_payload_locked(
        self,
        session_id: str,
        payload: dict[str, Any],
        wave_delta: dict[str, Any] | None = None,
    ) -> None:
        self._memory_live_payloads[session_id] = payload
        write_eeg_live_payload(session_id, payload)
        callback = self._live_update_callback
        if callback is None:
            return
        try:
            callback(session_id, payload, wave_delta)
        except Exception:
            logger.warning(
                "EEG live update callback failed session_id=%s",
                session_id,
                exc_info=True,
            )

    def _write_binding_live_locked(self, binding: EegTurnBinding) -> None:
        payload = self._build_live_payload_locked(binding)
        wave_delta = self._build_live_wave_delta_locked(binding)
        self._store_live_payload_locked(binding.session_id, payload, wave_delta)
        binding.pending_live_samples.clear()
        binding.live_stream_reset_pending = False

    def _build_binding_status_payload_locked(self, binding: EegTurnBinding) -> dict[str, Any]:
        return {
            "session_id": binding.session_id,
            "turn_id": binding.turn_id,
            "device_status": self._device_status,
            "provider": self._provider_mode,
            "model_loaded": (
                self._clf is not None
                and self._scaler is not None
                and self._selected_features is not None
                and bool(self._all_feature_names)
            ),
            "channel_names": list(self._channel_names),
            "sampling_rate": self._sampling_rate,
        }

    def _finalize_window_locked(self, binding: EegTurnBinding, *, reason: str, force: bool = False) -> None:
        current_window = binding.current_window
        if not current_window.wave_samples and not current_window.feature_samples:
            return
        if not force and len(current_window.feature_samples) < self._min_feature_frames:
            return

        raw_eeg_uri = self._upload_raw_window(binding)
        inference_payload = self._infer_window_locked(binding, raw_eeg_uri=raw_eeg_uri)
        window_payload = self._build_window_payload(
            binding,
            raw_eeg_uri=raw_eeg_uri,
            inference_payload=inference_payload,
        )
        self._record_window_result_locked(
            binding,
            raw_eeg_uri=raw_eeg_uri,
            inference_payload=inference_payload,
        )
        if inference_payload is not None:
            binding.latest_results.append(
                {
                    "window_index": inference_payload.get("window_index"),
                    "primary_label": inference_payload.get("primary_label"),
                    "primary_score": inference_payload.get("primary_score"),
                    "top_3_labels": _copy_labels(inference_payload.get("top_3_labels")),
                    "feature_frame_count": inference_payload.get("feature_frame_count"),
                    "sample_started_at": inference_payload.get("sample_started_at"),
                    "sample_ended_at": inference_payload.get("sample_ended_at"),
                    "raw_eeg_uri": inference_payload.get("raw_eeg_uri"),
                    "model_version": inference_payload.get("model_version"),
                    "quality_flags": dict(inference_payload.get("quality_flags") or {}),
                }
            )
        write_eeg_turn_window_payload(
            binding.session_id,
            binding.turn_id,
            binding.window_index,
            window_payload,
        )
        binding.window_indexes.append(binding.window_index)
        binding.window_index += 1
        binding.current_window = EegWindowBuffer()
        self._write_binding_live_locked(binding)
        self._write_turn_state_locked(binding, status="active" if reason == "window_complete" else "finished")


eeg_runtime_service = EEGRuntimeService()
