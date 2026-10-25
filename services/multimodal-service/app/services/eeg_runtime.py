from __future__ import annotations

import asyncio
import base64
import binascii
import io
import hashlib
import uuid
import logging
import os
import pickle
import socket
import threading
from abc import ABC, abstractmethod
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
from app.redis import get_optional_redis_client
from app.services.eeg_live_state_store import (
    clear_eeg_turn_hot_state,
    read_eeg_live_payload,
    write_eeg_live_payload,
    write_eeg_turn_state_payload,
    write_eeg_turn_window_payload,
)
from app.services.eeg_explanation_math import freeze_input
from app.services.eeg_protocol import EEGPacketDecoder, FeaturePacket, MODEL_FEATURE_COUNT, WavePacket
from app.services.object_storage import upload_object_to_bucket

logger = logging.getLogger(__name__)
EEG_LIVE_FLUSH_INTERVAL_SECONDS = 0.12
EEG_LABELS = {
    0: "\u6d88\u6781",
    1: "\u4e2d\u6027",
    2: "\u79ef\u6781",
}
EEG_TRANSPORT_READY_STATUSES = {
    "scanning",
    "connecting",
    "connected",
    "streaming",
    "waiting_for_stream",
}
EEG_SUPPORTED_NORM_MODES = {"none", "session_zscore"}
EEG_DEFAULT_TRIAL_FEATURE_COMPONENTS = ("med", "std", "slope")
EEG_WAVE_SEQ_MODULO = 1 << 16
EEG_PREVIEW_SEQ_REORDER_TOLERANCE = 8
EEG_PREVIEW_SEQ_RESET_LOW_WATERMARK = 32


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime | None:
    if value in (None, "", b""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    try:
        numeric = float(normalized)
    except ValueError:
        return None
    if numeric > 10_000_000_000:
        numeric /= 1000.0
    return datetime.fromtimestamp(numeric, tz=timezone.utc)


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


def _softmax(scores: Sequence[float] | np.ndarray) -> np.ndarray:
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


def _normalize_feature_rows(rows: np.ndarray, norm_mode: str) -> np.ndarray:
    normalized_mode = str(norm_mode or "none").strip().lower() or "none"
    if normalized_mode == "none":
        return rows
    if normalized_mode != "session_zscore":
        raise ValueError(f"unsupported_eeg_norm_mode:{normalized_mode}")
    if rows.ndim != 2 or rows.shape[0] == 0:
        return rows
    mean = np.mean(rows, axis=0, keepdims=True)
    std = np.std(rows, axis=0, keepdims=True)
    std[std < 1e-12] = 1.0
    return (rows - mean) / std


def _compute_trial_slope(rows: np.ndarray) -> np.ndarray:
    if rows.ndim != 2 or rows.shape[0] <= 1:
        return np.zeros(rows.shape[1] if rows.ndim == 2 else 0, dtype=np.float32)
    time_axis = np.arange(rows.shape[0], dtype=np.float32)
    time_axis = time_axis - np.mean(time_axis)
    time_std = float(np.std(time_axis))
    if time_std < 1e-12:
        return np.zeros(rows.shape[1], dtype=np.float32)
    time_axis = time_axis / time_std
    return np.mean(rows * time_axis[:, None], axis=0, dtype=np.float32)


def _aggregate_trial_vectors(rows: np.ndarray, *, components: Sequence[str]) -> np.ndarray:
    if rows.ndim != 2 or rows.shape[0] == 0:
        return np.zeros(0, dtype=np.float32)

    parts: list[np.ndarray] = []
    for component in components:
        normalized_component = str(component or "").strip().lower()
        if normalized_component == "med":
            parts.append(np.median(rows, axis=0).astype(np.float32))
        elif normalized_component == "std":
            parts.append(np.std(rows, axis=0).astype(np.float32))
        elif normalized_component == "slope":
            parts.append(_compute_trial_slope(rows))
        else:
            raise ValueError(f"unsupported_eeg_trial_component:{normalized_component}")
    return np.concatenate(parts, axis=0).astype(np.float32)


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
    sample_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    quality_flags: dict[str, bool] = field(default_factory=dict)
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
    preview_last_bucket: int | None = None
    preview_last_raw_seq: int | None = None
    preview_last_unwrapped_seq: int | None = None
    preview_seq_offset: int = 0


class EEGTransportProvider(ABC):
    def __init__(self, *, on_bytes: Callable[[bytes], None], provider_name: str) -> None:
        self._on_bytes = on_bytes
        self._provider_name = provider_name
        self._status = "idle"
        self._device_id: str | None = None
        self._last_error: str | None = None
        self._last_packet_at: datetime | None = None
        self._last_source_at: datetime | None = None
        self._last_packet_seq: int | None = None
        self._status_callback: Callable[[str, str | None, str | None], None] | None = None
        self._status_details: dict[str, Any] = {}

    def set_status_callback(
        self,
        callback: Callable[[str, str | None, str | None], None],
    ) -> None:
        self._status_callback = callback

    def state_snapshot(self) -> dict[str, Any]:
        lag_source = self._last_source_at or self._last_packet_at
        lag_ms = None
        if lag_source is not None:
            lag_ms = max(0, int(round((_utcnow() - lag_source).total_seconds() * 1000)))
        return {
            "transport_provider": self._provider_name,
            "transport_status": self._status,
            "device_id": self._device_id,
            "last_error": self._last_error,
            "last_transport_at": self._last_packet_at,
            "last_packet_seq": self._last_packet_seq,
            "transport_lag_ms": lag_ms,
            **self._status_details,
        }

    def _emit_status(
        self,
        status: str,
        *,
        device_id: str | None = None,
        error: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._status = status
        if device_id is not None:
            self._device_id = device_id
        if error:
            self._last_error = error
        elif status in {"idle", "scanning", "connecting", "connected", "streaming", "waiting_for_stream"}:
            self._last_error = None
        if details:
            self._status_details.update(details)
        if self._status_callback is not None:
            self._status_callback(status, self._device_id, self._last_error)

    def _record_packet(
        self,
        *,
        device_id: str | None = None,
        seq: int | None = None,
        source_timestamp: datetime | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._last_packet_at = _utcnow()
        self._last_source_at = source_timestamp or self._last_packet_at
        if device_id is not None:
            self._device_id = device_id
        if seq is not None:
            self._last_packet_seq = int(seq)
        if details:
            self._status_details.update(details)

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError


class EEGRedisStreamProvider(EEGTransportProvider):
    def __init__(self, *, on_bytes: Callable[[bytes], None]) -> None:
        super().__init__(on_bytes=on_bytes, provider_name="redis_stream")
        settings = get_settings()
        configured_prefix = str(settings["eeg_stream_key_prefix"]).strip() or "mcs:eeg:transport"
        if configured_prefix.rsplit(":", 1)[-1] == "transport":
            configured_stream_key = f"{configured_prefix}:default"
        else:
            configured_stream_key = configured_prefix
        default_consumer_name = f"{socket.gethostname()}-{os.getpid()}"
        self._stream_key = configured_stream_key
        self._consumer_group = str(settings["eeg_stream_consumer_group"]).strip() or "multimodal-eeg"
        self._consumer_name = str(settings["eeg_stream_consumer_name"]).strip() or default_consumer_name
        self._block_ms = max(1, int(settings["eeg_stream_block_ms"]))
        self._batch_size = max(1, int(settings["eeg_stream_batch_size"]))
        self._reconnect_delay_seconds = float(settings["eeg_reconnect_delay_seconds"])
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._status_details.update(
            {
                "redis_stream_key": self._stream_key,
                "redis_consumer_group": self._consumer_group,
            }
        )

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="eeg-redis-stream-provider",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2)
        if thread is not None and thread.is_alive():
            logger.warning("EEG redis-stream provider thread did not exit cleanly before timeout")
            return
        self._thread = None

    @staticmethod
    def _field_value(fields: dict[Any, Any], name: str) -> bytes | str | None:
        return fields.get(name) or fields.get(name.encode("utf-8"))

    def _decode_payload_bytes(self, fields: dict[Any, Any]) -> bytes:
        payload_hex = self._field_value(fields, "payload_hex")
        if payload_hex not in (None, "", b""):
            if isinstance(payload_hex, bytes):
                payload_hex = payload_hex.decode("utf-8", errors="ignore")
            return binascii.unhexlify(str(payload_hex).strip())

        payload_base64 = self._field_value(fields, "payload_base64")
        if payload_base64 not in (None, "", b""):
            if isinstance(payload_base64, bytes):
                payload_base64 = payload_base64.decode("utf-8", errors="ignore")
            return base64.b64decode(str(payload_base64).strip())

        raw_payload = self._field_value(fields, "payload")
        if isinstance(raw_payload, bytes):
            return raw_payload
        if isinstance(raw_payload, str):
            return raw_payload.encode("utf-8")
        raise ValueError("missing_transport_payload")

    def _ensure_consumer_group(self, client: Any) -> None:
        try:
            client.xgroup_create(
                name=self._stream_key,
                groupname=self._consumer_group,
                id="$",
                mkstream=True,
            )
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def _ack_entry(self, client: Any, entry_id: Any) -> None:
        try:
            client.xack(self._stream_key, self._consumer_group, entry_id)
        except Exception:
            logger.warning(
                "EEG redis-stream ack failed stream=%s entry_id=%s",
                self._stream_key,
                entry_id,
                exc_info=True,
            )

    def _consume_entries(self, client: Any, entries: list[tuple[Any, dict[Any, Any]]]) -> None:
        for entry_id, fields in entries:
            device_id = self._field_value(fields, "device_id")
            if isinstance(device_id, bytes):
                device_id = device_id.decode("utf-8", errors="ignore")
            device_id = str(device_id or "").strip() or None

            seq_value = self._field_value(fields, "seq") or self._field_value(fields, "sample_index")
            if isinstance(seq_value, bytes):
                seq_value = seq_value.decode("utf-8", errors="ignore")
            seq = None
            if seq_value not in (None, "", b""):
                try:
                    seq = int(str(seq_value).strip())
                except ValueError:
                    seq = None

            source_timestamp = _parse_timestamp(
                self._field_value(fields, "received_at") or self._field_value(fields, "ts")
            )

            try:
                payload = self._decode_payload_bytes(fields)
            except Exception as exc:
                logger.warning(
                    "EEG redis-stream payload decode failed stream=%s entry_id=%s",
                    self._stream_key,
                    entry_id,
                    exc_info=True,
                )
                self._emit_status(
                    "streaming",
                    device_id=device_id,
                    error=str(exc),
                    details={
                        "redis_stream_key": self._stream_key,
                        "redis_consumer_group": self._consumer_group,
                    },
                )
                self._ack_entry(client, entry_id)
                continue

            self._record_packet(
                device_id=device_id,
                seq=seq,
                source_timestamp=source_timestamp,
                details={
                    "redis_stream_key": self._stream_key,
                    "redis_consumer_group": self._consumer_group,
                },
            )
            self._emit_status(
                "streaming",
                device_id=device_id,
                details={
                    "redis_stream_key": self._stream_key,
                    "redis_consumer_group": self._consumer_group,
                },
            )

            try:
                self._on_bytes(payload)
            except Exception as exc:
                logger.warning(
                    "EEG redis-stream ingest failed stream=%s entry_id=%s",
                    self._stream_key,
                    entry_id,
                    exc_info=True,
                )
                self._emit_status(
                    "streaming",
                    device_id=device_id,
                    error=str(exc),
                    details={
                        "redis_stream_key": self._stream_key,
                        "redis_consumer_group": self._consumer_group,
                    },
                )
            finally:
                self._ack_entry(client, entry_id)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            client = get_optional_redis_client()
            if client is None:
                self._emit_status(
                    "disconnected",
                    error="redis_disabled",
                    details={
                        "redis_stream_key": self._stream_key,
                        "redis_consumer_group": self._consumer_group,
                    },
                )
                self._stop_event.wait(self._reconnect_delay_seconds)
                continue
            try:
                self._ensure_consumer_group(client)
                self._emit_status(
                    "waiting_for_stream",
                    details={
                        "redis_stream_key": self._stream_key,
                        "redis_consumer_group": self._consumer_group,
                    },
                )
                while not self._stop_event.is_set():
                    records = client.xreadgroup(
                        groupname=self._consumer_group,
                        consumername=self._consumer_name,
                        streams={self._stream_key: ">"},
                        count=self._batch_size,
                        block=self._block_ms,
                    )
                    if not records:
                        continue
                    for _, entries in records:  # type: ignore[union-attr]
                        self._consume_entries(client, entries)
            except Exception as exc:
                logger.exception("EEG redis-stream provider loop failed")
                self._emit_status(
                    "disconnected",
                    error=str(exc),
                    details={
                        "redis_stream_key": self._stream_key,
                        "redis_consumer_group": self._consumer_group,
                    },
                )
                self._stop_event.wait(self._reconnect_delay_seconds)


class EEGBleProvider(EEGTransportProvider):
    def __init__(self, *, on_bytes: Callable[[bytes], None]) -> None:
        super().__init__(on_bytes=on_bytes, provider_name="ble")
        settings = get_settings()
        self._name_hint = str(settings["eeg_device_name_hint"])
        self._notify_uuid = str(settings["eeg_notify_char_uuid"])
        self._scan_seconds = float(settings["eeg_scan_seconds"])
        self._reconnect_delay_seconds = float(settings["eeg_reconnect_delay_seconds"])
        self._stop_event = threading.Event()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

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

    def _emit_status(self, status: str, *, device_id: str | None = None, error: str | None = None, details: dict[str, Any] | None = None) -> None:
        if self._stopping.is_set():
            return
        super()._emit_status(status, device_id=device_id, error=error, details=details)

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
                        self._record_packet(device_id=address)
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
        self._auto_start_transport = bool(settings["eeg_auto_start_transport"])
        self._require_transport_for_ready = bool(settings["eeg_require_transport_for_ready"])
        self._channel_names = list(settings["eeg_channel_names"])
        self._sampling_rate = int(settings["eeg_sampling_rate"])
        self._preview_sampling_rate = max(
            1,
            min(self._sampling_rate, int(settings["eeg_preview_sampling_rate"])),
        )
        self._preview_seconds = max(1, int(settings["eeg_preview_seconds"]))
        self._window_seconds = max(1, int(settings["eeg_window_seconds"]))
        self._window_feature_frames = self._window_seconds
        self._min_feature_frames = max(1, int(settings["eeg_min_feature_frames"]))
        self._latest_results_limit = max(1, int(settings["eeg_latest_results_limit"]))
        self._preview_sample_limit = max(1, self._preview_sampling_rate * self._preview_seconds)
        self._decoder = EEGPacketDecoder()
        self._lock = threading.RLock()
        self._last_error: str | None = None
        self._provider = self._create_transport_provider()
        if self._provider is not None:
            self._provider.set_status_callback(self._update_device_status)
        self._provider_started = False
        self._device_status = "disabled" if not self._enabled else "idle"
        self._device_id: str | None = None
        self._transport_provider = self._provider_mode
        self._transport_status = self._device_status
        self._last_transport_at: datetime | None = None
        self._last_packet_seq: int | None = None
        self._transport_lag_ms: int | None = None
        self._redis_stream_key: str | None = None
        self._redis_consumer_group: str | None = None
        self._active_binding: EegTurnBinding | None = None
        self._memory_live_payloads: dict[str, dict[str, Any]] = {}
        self._clf = None
        self._scaler = None
        self._selected_features: np.ndarray | None = None
        self._packet_feature_names: list[str] = []
        self._window_feature_names: list[str] = []
        self._trial_feature_names: list[str] = []
        self._trial_feature_components: tuple[str, ...] = ("med",)
        self._input_kind = "vector"
        self._norm_mode = "none"
        self._runtime_feature_source = "packet"
        self._all_feature_names: list[str] = []
        self._model_name = "eeg_3class"
        self._model_sha256: str | None = None
        self._model_version: str | None = None
        self._model_loaded = False
        self._live_update_callback: Callable[[str, dict[str, Any], dict[str, Any] | None], None] | None = None
        self._sync_transport_state_locked()

    def _is_model_ready_locked(self) -> bool:
        model_feature_names = self._all_feature_names or self._trial_feature_names or self._window_feature_names
        return bool(
            self._clf is not None
            and self._scaler is not None
            and self._selected_features is not None
            and self._selected_features.size > 0
            and model_feature_names
        )

    def _reset_model_artifacts_locked(self) -> None:
        self._clf = None
        self._scaler = None
        self._selected_features = None
        self._packet_feature_names = []
        self._window_feature_names = []
        self._trial_feature_names = []
        self._trial_feature_components = ("med",)
        self._input_kind = "vector"
        self._norm_mode = "none"
        self._runtime_feature_source = "packet"
        self._all_feature_names = []

    @staticmethod
    def _coerce_feature_name_list(values: Any) -> list[str]:
        if not isinstance(values, (list, tuple)):
            return []
        return [str(value) for value in values]

    def _create_transport_provider(self) -> EEGTransportProvider | None:
        if self._provider_mode == "ble":
            return EEGBleProvider(on_bytes=self.ingest_transport_bytes)
        if self._provider_mode == "redis_stream":
            return EEGRedisStreamProvider(on_bytes=self.ingest_transport_bytes)
        self._last_error = f"unsupported_eeg_provider:{self._provider_mode}"
        logger.warning("Unsupported EEG provider mode: %s", self._provider_mode)
        return None

    def warmup_model(self) -> bool:
        with self._lock:
            return self._load_model_locked()

    def ensure_transport_started(self) -> dict[str, Any]:
        with self._lock:
            self._ensure_provider_started_locked()
            return self._build_status_snapshot_locked()

    def warmup(self) -> dict[str, Any]:
        with self._lock:
            self._load_model_locked()
            return self._build_status_snapshot_locked()

    def status_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._build_status_snapshot_locked()

    def _sync_transport_state_locked(self) -> None:
        if self._provider is None:
            self._transport_provider = self._provider_mode
            self._transport_status = "disabled" if not self._enabled else "idle"
            self._device_status = self._transport_status
            self._device_id = None
            self._last_transport_at = None
            self._last_packet_seq = None
            self._transport_lag_ms = None
            self._redis_stream_key = None
            self._redis_consumer_group = None
            return

        state = self._provider.state_snapshot()
        self._transport_provider = str(state.get("transport_provider") or self._provider_mode)
        self._transport_status = str(state.get("transport_status") or ("disabled" if not self._enabled else "idle"))
        self._device_status = self._transport_status
        self._device_id = state.get("device_id")
        provider_last_error = state.get("last_error")
        if provider_last_error:
            self._last_error = str(provider_last_error)
        elif self._transport_status in {"idle", *EEG_TRANSPORT_READY_STATUSES}:
            self._last_error = None
        provider_last_transport_at = state.get("last_transport_at")
        if provider_last_transport_at is not None:
            self._last_transport_at = provider_last_transport_at
        provider_last_packet_seq = state.get("last_packet_seq")
        if provider_last_packet_seq is not None:
            self._last_packet_seq = provider_last_packet_seq
        provider_transport_lag_ms = state.get("transport_lag_ms")
        if provider_transport_lag_ms is not None:
            self._transport_lag_ms = provider_transport_lag_ms
        elif self._last_transport_at is None:
            self._transport_lag_ms = None
        self._redis_stream_key = state.get("redis_stream_key")
        self._redis_consumer_group = state.get("redis_consumer_group")

    def _transport_ready_locked(self) -> bool:
        if not self._enabled or self._provider is None or not self._provider_started:
            return False
        return self._transport_status in EEG_TRANSPORT_READY_STATUSES

    def _not_ready_reason_locked(self, *, model_loaded: bool, transport_ready: bool) -> str | None:
        if not self._enabled:
            return None
        if not model_loaded:
            return self._last_error or "eeg_model_not_loaded"
        if not self._require_transport_for_ready:
            return None
        if self._provider is None:
            return self._last_error or "transport_provider_unavailable"
        if not self._provider_started:
            return "transport_not_started"
        if not transport_ready:
            return f"transport_status:{self._transport_status}"
        return None

    def _build_status_snapshot_locked(self) -> dict[str, Any]:
        self._sync_transport_state_locked()
        model_loaded = self._is_model_ready_locked()
        transport_ready = self._transport_ready_locked()
        not_ready_reason = self._not_ready_reason_locked(
            model_loaded=model_loaded,
            transport_ready=transport_ready,
        )
        return {
            "enabled": self._enabled,
            "provider": self._provider_mode,
            "provider_started": self._provider_started,
            "device_status": self._device_status,
            "device_id": self._device_id,
            "last_error": self._last_error,
            "model_loaded": model_loaded,
            "model_name": self._model_name,
            "model_version": self._model_version,
            "channel_names": list(self._channel_names),
            "sampling_rate": self._sampling_rate,
            "transport_provider": self._transport_provider,
            "transport_status": self._transport_status,
            "last_transport_at": _isoformat(self._last_transport_at),
            "last_packet_seq": self._last_packet_seq,
            "transport_lag_ms": self._transport_lag_ms,
            "redis_stream_key": self._redis_stream_key,
            "redis_consumer_group": self._redis_consumer_group,
            "require_transport_for_ready": self._require_transport_for_ready,
            "auto_start_transport": self._auto_start_transport,
            "transport_ready": transport_ready,
            "ready": not self._enabled or not_ready_reason is None,
            "not_ready_reason": not_ready_reason,
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
            carryover_preview = self._load_preview_carryover_locked(session_id)
            carryover_results = self._load_result_carryover_locked(session_id)
            binding = EegTurnBinding(
                session_id=session_id,
                turn_id=turn_id,
                flow_run_id=flow_run_id,
                stage_id=stage_id,
                question_key=question_key,
                started_at=_utcnow(),
                preview_buffer=deque(carryover_preview, maxlen=self._preview_sample_limit),
                latest_results=deque(carryover_results, maxlen=self._latest_results_limit),
                live_stream_reset_pending=not bool(carryover_preview),
                preview_last_bucket=self._resolve_preview_bucket_from_payloads(carryover_preview),
                preview_last_raw_seq=self._resolve_last_preview_seq_from_payloads(carryover_preview),
                preview_last_unwrapped_seq=self._resolve_last_preview_seq_from_payloads(carryover_preview),
            )
            self._active_binding = binding
            self._write_binding_live_locked(binding)
            self._write_turn_state_locked(binding, status="active")
            return self._build_binding_status_payload_locked(binding)

    def finish_turn(self, *, session_id: str, turn_id: str, reason: str = "completed") -> dict[str, Any]:
        with self._lock:
            active = self._active_binding
            if active is None:
                # Transport provider keeps running so the next turn can attach
                # without a full reconnect / consumer restart.
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
            # Transport provider remains running and is only stopped on shutdown().
            return {
                "session_id": session_id,
                "turn_id": turn_id,
                "status": "finished",
                "device_status": self._device_status,
                "reason": reason,
            }

    def get_session_live_payload(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            active = self._active_binding
            if active and active.session_id == session_id:
                return self._build_live_payload_locked(active)
            payload = read_eeg_live_payload(session_id)
            if payload is not None:
                return payload
            cached = self._memory_live_payloads.get(session_id)
            if cached is not None:
                return cached
            return self._build_pending_live_payload()

    def ingest_transport_bytes(self, chunk: bytes) -> None:
        with self._lock:
            self._last_transport_at = _utcnow()
            self._transport_lag_ms = 0
            for packet in self._decoder.feed(chunk):
                if isinstance(packet, WavePacket):
                    self._last_packet_seq = int(packet.seq)
                    self._handle_wave_packet_locked(packet)
                elif isinstance(packet, FeaturePacket):
                    self._handle_feature_packet_locked(packet)

    def _ensure_provider_started_locked(self) -> None:
        if not self._enabled or self._provider is None or self._provider_started:
            return
        self._provider.start()
        self._provider_started = True
        self._sync_transport_state_locked()

    def _stop_provider_locked(self, *, clear_error: bool) -> None:
        if self._provider_started and self._provider is not None:
            self._provider.stop()
            self._provider_started = False
        self._device_status = "disabled" if not self._enabled else "idle"
        self._transport_status = self._device_status
        self._device_id = None
        self._last_transport_at = None
        self._last_packet_seq = None
        self._transport_lag_ms = None
        if clear_error:
            self._last_error = None

    def _load_model_locked(self) -> bool:
        if self._model_loaded:
            return self._is_model_ready_locked()

        self._model_loaded = True
        model_path = Path(get_settings()["eeg_model_path"])
        if not model_path.exists():
            self._last_error = f"eeg_model_missing:{model_path.name}"
            logger.warning("EEG model asset is missing at %s", model_path)
            return False

        try:
            model_bytes = model_path.read_bytes()
            self._model_sha256 = hashlib.sha256(model_bytes).hexdigest()
            model_obj = pickle.loads(model_bytes)
            self._clf = model_obj.get("model")
            self._scaler = model_obj.get("scaler")
            selected = model_obj.get("selected_features")
            if selected is None:
                selected = []
            self._selected_features = np.array(selected, dtype=int)
            self._input_kind = str(model_obj.get("input_kind") or "vector").strip() or "vector"
            self._norm_mode = str(model_obj.get("norm_mode") or "none").strip().lower() or "none"
            self._runtime_feature_source = (
                str(model_obj.get("runtime_feature_source") or "packet").strip().lower() or "packet"
            )
            packet_feature_names = self._coerce_feature_name_list(model_obj.get("packet_feature_names"))
            window_feature_names = self._coerce_feature_name_list(model_obj.get("window_feature_names"))
            trial_feature_names = self._coerce_feature_name_list(model_obj.get("trial_feature_names"))
            all_feature_names = self._coerce_feature_name_list(model_obj.get("all_feature_names"))
            if not packet_feature_names:
                packet_feature_names = list(window_feature_names) or list(all_feature_names)
            if not packet_feature_names:
                packet_feature_names = [f"feat_{index}" for index in range(MODEL_FEATURE_COUNT)]
            if not window_feature_names:
                window_feature_names = list(packet_feature_names)
            if not trial_feature_names:
                trial_feature_names = list(all_feature_names) or list(window_feature_names)

            raw_components = model_obj.get("trial_feature_components") or []
            trial_feature_components = tuple(
                str(component).strip().lower()
                for component in raw_components
                if str(component).strip()
            )
            if not trial_feature_components:
                trial_feature_components = (
                    ("med",)
                    if len(trial_feature_names) == len(window_feature_names)
                    else EEG_DEFAULT_TRIAL_FEATURE_COMPONENTS
                )

            self._packet_feature_names = list(packet_feature_names)
            self._window_feature_names = list(window_feature_names)
            self._trial_feature_names = list(trial_feature_names)
            self._trial_feature_components = tuple(trial_feature_components)
            self._all_feature_names = list(trial_feature_names)
            self._model_name = str(model_obj.get("classifier_name") or self._model_name)
            self._model_version = str(
                model_obj.get("version")
                or model_obj.get("version_tag")
                or model_obj.get("feature_set_desc")
                or "unknown"
            )

            if self._input_kind != "vector":
                raise ValueError(f"unsupported_eeg_input_kind:{self._input_kind}")
            if self._runtime_feature_source not in {"packet", ""}:
                raise ValueError(
                    f"unsupported_eeg_runtime_feature_source:{self._runtime_feature_source}"
                )
            if self._norm_mode not in EEG_SUPPORTED_NORM_MODES:
                raise ValueError(f"unsupported_eeg_norm_mode:{self._norm_mode}")

            expected_trial_feature_count = len(self._window_feature_names) * len(
                self._trial_feature_components
            )
            if len(self._trial_feature_names) != expected_trial_feature_count:
                raise ValueError(
                    "eeg_trial_feature_count_mismatch:"
                    f"trial={len(self._trial_feature_names)}"
                    f":expected={expected_trial_feature_count}"
                )
            if (
                self._selected_features.size > 0
                and np.max(self._selected_features) >= len(self._trial_feature_names)
            ):
                raise ValueError(
                    "eeg_selected_feature_index_out_of_range:"
                    f"selected_max={int(np.max(self._selected_features))}"
                    f":trial={len(self._trial_feature_names)}"
                )

            self._last_error = None
            return self._is_model_ready_locked()
        except Exception as exc:
            self._last_error = str(exc)
            logger.exception("Failed to load EEG model asset")
            self._reset_model_artifacts_locked()
            return False

    def _update_device_status(self, status: str, device_id: str | None, error: str | None) -> None:
        with self._lock:
            self._sync_transport_state_locked()
            if self._provider is None:
                self._device_status = status
                self._transport_status = status
                self._device_id = device_id
                if error:
                    self._last_error = error
                elif status in {"idle", "scanning", "connecting", "connected", "streaming", "waiting_for_stream"}:
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
            values=(float(packet.channels[0]), float(packet.channels[1]), float(packet.channels[2])),
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
        if self._should_capture_preview_sample(binding, sample.seq):
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
        expected_count = self._packet_feature_count()
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

    def _packet_feature_count(self) -> int:
        if self._window_feature_names:
            return len(self._window_feature_names)
        if self._packet_feature_names:
            return len(self._packet_feature_names)
        return MODEL_FEATURE_COUNT

    def _model_feature_count(self) -> int:
        if self._trial_feature_names:
            return len(self._trial_feature_names)
        if self._all_feature_names:
            return len(self._all_feature_names)
        return self._packet_feature_count()

    def _load_preview_carryover_locked(self, session_id: str) -> list[dict[str, Any]]:
        payload = self._memory_live_payloads.get(session_id) or read_eeg_live_payload(session_id)
        eeg_waves = dict(payload.get("eeg_waves") or {}) if isinstance(payload, dict) else {}
        samples = eeg_waves.get("samples")
        if not isinstance(samples, list):
            return []
        return [dict(sample) for sample in samples[-self._preview_sample_limit :] if isinstance(sample, dict)]

    def _load_result_carryover_locked(self, session_id: str) -> list[dict[str, Any]]:
        payload = self._memory_live_payloads.get(session_id) or read_eeg_live_payload(session_id)
        eeg_live = dict(payload.get("eeg_live") or {}) if isinstance(payload, dict) else {}
        latest_results = eeg_live.get("latest_results")
        if not isinstance(latest_results, list):
            return []
        return [
            dict(result)
            for result in latest_results[-self._latest_results_limit :]
            if isinstance(result, dict)
        ]

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
            "eeg_live": {
                **dict(base_payload.get("eeg_live") or {}),
                "turn_id": None,
            },
            "eeg_waves": {
                **dict(base_payload.get("eeg_waves") or {}),
            },
        }
        self._store_live_payload_locked(binding.session_id, final_payload)

    def _serialize_window_npz_bytes(self, binding: EegTurnBinding, snapshot: dict | None = None) -> bytes:
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
            else np.zeros((0, self._packet_feature_count()), dtype=np.float32)
        )
        feature_timestamps_ms = np.array(
            [int(sample.captured_at.timestamp() * 1000) for sample in feature_samples],
            dtype=np.int64,
        )
        buffer = io.BytesIO()
        np.savez_compressed(
            buffer,
            aggregate_vector=np.asarray((snapshot or {}).get("aggregate_vector", []), dtype=np.float32),
            scaled_vector=np.asarray((snapshot or {}).get("scaled_vector", []), dtype=np.float64),
            selected_indices=np.asarray((snapshot or {}).get("selected_indices", []), dtype=np.int32),
            model_sha256=np.array((snapshot or {}).get("model_sha256") or ""),
            input_hash=np.array((snapshot or {}).get("input_hash") or ""),
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

    def _upload_raw_window(self, binding: EegTurnBinding, snapshot: dict | None = None) -> str | None:
        object_key = (
            f"raw/eeg/{binding.session_id}/{binding.turn_id}/window-{binding.window_index}.npz"
        )
        try:
            return upload_object_to_bucket(
                bucket_name=str(get_settings()["multimodal_bucket"]),
                object_key=object_key,
                file_bytes=self._serialize_window_npz_bytes(binding, snapshot),
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
        if features_matrix.ndim != 2 or features_matrix.shape[1] != self._packet_feature_count():
            logger.warning(
                "EEG packet feature dimension mismatch: received=%s expected=%s",
                features_matrix.shape[1] if features_matrix.ndim == 2 else 0,
                self._packet_feature_count(),
            )
            return None
        if not np.isfinite(features_matrix).all():
            current_window.quality_flags["nonfinite_features"] = True
            return None
        try:
            normalized_matrix = _normalize_feature_rows(features_matrix, self._norm_mode).astype(
                np.float32
            )
            model_input_vector = _aggregate_trial_vectors(
                normalized_matrix,
                components=self._trial_feature_components,
            )
        except ValueError as exc:
            logger.warning("EEG feature aggregation failed: %s", exc)
            return None

        if model_input_vector.size != self._model_feature_count():
            logger.warning(
                "EEG aggregated feature dimension mismatch: received=%s expected=%s",
                model_input_vector.size,
                self._model_feature_count(),
            )
            return None
        if not np.isfinite(model_input_vector).all():
            current_window.quality_flags["nonfinite_features"] = True
            return None
        if np.any(self._selected_features < 0) or np.any(self._selected_features >= model_input_vector.size):
            logger.warning(
                "EEG selected feature indices exceed aggregated vector size=%s",
                model_input_vector.size,
            )
            return None
        selected = model_input_vector[self._selected_features].reshape(1, -1)
        scaled = self._scaler.transform(selected)
        if not np.isfinite(scaled).all():
            current_window.quality_flags["nonfinite_features"] = True
            logger.warning("EEG scaled input contains nonfinite values")
            return None
        prediction = int(self._clf.predict(scaled)[0])

        probabilities = _predict_probabilities(self._clf, scaled)

        score_map = {
            EEG_LABELS.get(index, str(index)): float(probabilities[index])
            for index in range(min(len(probabilities), len(EEG_LABELS)))
        }
        primary_label = EEG_LABELS.get(prediction, str(prediction))
        return {
            "modality": "eeg",
            "status": "ready",
            "sample_id": current_window.sample_id,
            "inference_id": str(uuid.uuid4()),
            "model_sha256": self._model_sha256,
            "score_kind": "softmax_decision_score" if "svc" in type(self._clf).__name__.lower() else "model_score",
            "_explanation_input": freeze_input(
                model_sha256=self._model_sha256, feature_names=self._all_feature_names,
                selected=self._selected_features.tolist(), aggregated=model_input_vector, scaled=scaled,
            ),
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
                id=current_window.sample_id,
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
                    "quality_flags": dict(current_window.quality_flags),
                    "prediction_status": "ready" if inference_payload else "invalid" if current_window.quality_flags else "insufficient_frames",
                },
                captured_at=current_window.sample_ended_at,
                created_at=now,
            )
            db_session.add(capture)
            db_session.flush()

            if inference_payload is not None:
                result_row = MultimodalInferenceResult(
                    id=inference_payload["inference_id"],
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
                            "sample_id": inference_payload.get("sample_id"),
                            "inference_id": inference_payload.get("inference_id"),
                            "model_sha256": inference_payload.get("model_sha256"),
                            "score_kind": inference_payload.get("score_kind"),
                            "sample_started_at": inference_payload.get("sample_started_at"),
                            "sample_ended_at": inference_payload.get("sample_ended_at"),
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
            "sample_id": current_window.sample_id,
            "inference_id": (inference_payload or {}).get("inference_id"),
            "model_sha256": self._model_sha256,
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
            "quality_flags": dict(current_window.quality_flags),
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
                "sampling_rate": self._preview_sampling_rate,
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
                "sampling_rate": self._preview_sampling_rate,
                "samples": [],
            },
        }

    def _build_live_wave_delta_locked(self, binding: EegTurnBinding) -> dict[str, Any] | None:
        if not binding.pending_live_samples and not binding.live_stream_reset_pending:
            return None
        return {
            "status": "ready" if binding.preview_buffer else "pending",
            "channel_names": list(self._channel_names),
            "sampling_rate": self._preview_sampling_rate,
            "append_samples": list(binding.pending_live_samples),
            "reset": bool(binding.live_stream_reset_pending),
        }

    @staticmethod
    def _coerce_wave_seq(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                return None
        return int(value) % EEG_WAVE_SEQ_MODULO

    def _resolve_last_preview_seq_from_payloads(self, payloads: list[dict[str, Any]]) -> int | None:
        if not payloads:
            return None
        return self._coerce_wave_seq(payloads[-1].get("seq"))

    def _resolve_preview_bucket_from_payloads(self, payloads: list[dict[str, Any]]) -> int | None:
        last_seq = self._resolve_last_preview_seq_from_payloads(payloads)
        if last_seq is None:
            return None
        return self._preview_bucket_for_seq(last_seq)

    def _preview_bucket_for_seq(self, seq: int) -> int:
        if self._preview_sampling_rate >= self._sampling_rate:
            return int(seq)
        return (int(seq) * self._preview_sampling_rate) // max(1, self._sampling_rate)

    def _advance_preview_seq_locked(self, binding: EegTurnBinding, seq: int) -> int | None:
        raw_seq = self._coerce_wave_seq(seq)
        if raw_seq is None:
            return None

        last_raw_seq = binding.preview_last_raw_seq
        last_unwrapped_seq = binding.preview_last_unwrapped_seq
        if last_raw_seq is None or last_unwrapped_seq is None:
            binding.preview_last_raw_seq = raw_seq
            binding.preview_last_unwrapped_seq = raw_seq
            return raw_seq

        seq_offset = binding.preview_seq_offset
        if raw_seq < last_raw_seq:
            backward_gap = last_raw_seq - raw_seq
            should_continue_from_new_cycle = (
                raw_seq <= EEG_PREVIEW_SEQ_RESET_LOW_WATERMARK
                or backward_gap > EEG_PREVIEW_SEQ_REORDER_TOLERANCE
            )
            if not should_continue_from_new_cycle:
                return None
            # Preserve monotonic preview bucketing across 16-bit wrap-around
            # and device reconnects that reset the transport sequence counter.
            seq_offset = last_unwrapped_seq + 1 - raw_seq
            binding.preview_seq_offset = seq_offset

        unwrapped_seq = raw_seq + seq_offset
        if unwrapped_seq <= last_unwrapped_seq:
            return None

        binding.preview_last_raw_seq = raw_seq
        binding.preview_last_unwrapped_seq = unwrapped_seq
        return unwrapped_seq

    def _should_capture_preview_sample(self, binding: EegTurnBinding, seq: int) -> bool:
        unwrapped_seq = self._advance_preview_seq_locked(binding, seq)
        if unwrapped_seq is None:
            return False
        bucket = self._preview_bucket_for_seq(unwrapped_seq)
        last_bucket = binding.preview_last_bucket
        if last_bucket is not None and bucket <= last_bucket:
            return False
        binding.preview_last_bucket = bucket
        return True

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
        self._sync_transport_state_locked()
        return {
            "session_id": binding.session_id,
            "turn_id": binding.turn_id,
            "device_status": self._device_status,
            "provider": self._provider_mode,
            "transport_provider": self._transport_provider,
            "transport_status": self._transport_status,
            "model_loaded": self._is_model_ready_locked(),
            "channel_names": list(self._channel_names),
            "sampling_rate": self._sampling_rate,
        }

    def _finalize_window_locked(self, binding: EegTurnBinding, *, reason: str, force: bool = False) -> None:
        current_window = binding.current_window
        if not current_window.wave_samples and not current_window.feature_samples:
            return
        if not force and len(current_window.feature_samples) < self._min_feature_frames:
            return

        inference_payload = self._infer_window_locked(binding, raw_eeg_uri=None)
        raw_eeg_uri = self._upload_raw_window(binding, (inference_payload or {}).get("_explanation_input"))
        if inference_payload is not None:
            inference_payload["raw_eeg_uri"] = raw_eeg_uri
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
                    "sample_id": inference_payload.get("sample_id"),
                    "inference_id": inference_payload.get("inference_id"),
                    "model_sha256": inference_payload.get("model_sha256"),
                    "score_kind": inference_payload.get("score_kind"),
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
