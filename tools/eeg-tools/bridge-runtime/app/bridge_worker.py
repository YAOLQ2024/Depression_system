from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.ble_client import BleTransportClient
from app.config import get_settings
from app.health import BridgeHealthStore
from app.recorder import JsonlRecorder
from app.redis_stream_writer import RedisStreamWriter

logger = logging.getLogger(__name__)


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class PacketEnvelope:
    payload: bytes
    device_id: str | None
    received_at: datetime


class EegHostBridgeWorker:
    def __init__(self, *, settings: dict[str, Any] | None = None) -> None:
        self._settings = dict(settings or get_settings())
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._publish_queue: queue.Queue[PacketEnvelope] = queue.Queue(
            maxsize=int(self._settings["queue_maxsize"])
        )
        self._health_store = BridgeHealthStore(self._settings["status_file"])
        self._writer = RedisStreamWriter(
            redis_url=str(self._settings["redis_url"]),
            stream_key=str(self._settings["stream_key"]),
            source_name=str(self._settings["source_name"]),
            payload_encoding=str(self._settings["payload_encoding"]),
            maxlen=int(self._settings["redis_maxlen"]),
            approximate_maxlen=bool(self._settings["redis_approx_maxlen"]),
            connect_timeout_seconds=float(self._settings["redis_connect_timeout_seconds"]),
            socket_timeout_seconds=float(self._settings["redis_socket_timeout_seconds"]),
        )
        self._recorder = JsonlRecorder(
            enabled=bool(self._settings["record_enabled"]),
            record_dir=self._settings["record_dir"],
            source_name=str(self._settings["source_name"]),
        )
        self._ble_client = BleTransportClient(
            device_name_hint=str(self._settings["ble_device_name_hint"]),
            notify_char_uuid=str(self._settings["ble_notify_char_uuid"]),
            scan_seconds=float(self._settings["ble_scan_seconds"]),
            reconnect_delay_seconds=float(self._settings["reconnect_delay_seconds"]),
        )
        self._publish_thread = threading.Thread(
            target=self._publisher_loop,
            name="eeg-host-bridge-publisher",
            daemon=True,
        )
        self._publish_batch_size = int(self._settings["publish_batch_size"])
        self._publish_batch_timeout_seconds = (
            int(self._settings["publish_batch_timeout_ms"]) / 1000.0
        )
        self._health_flush_interval_seconds = float(
            self._settings["health_flush_interval_seconds"]
        )
        self._queue_full_warning_interval_seconds = float(
            self._settings["queue_full_warning_interval_seconds"]
        )
        self._last_health_flush_monotonic = 0.0
        self._last_queue_full_warning_monotonic = 0.0
        self._last_health_write_warning_monotonic = 0.0
        self._status = "idle"
        self._device_id: str | None = None
        self._last_error: str | None = None
        self._packet_count = 0
        self._publish_count = 0
        self._published_packet_count = 0
        self._dropped_packet_count = 0
        self._last_packet_at: datetime | None = None
        self._last_publish_at: datetime | None = None
        self._last_stream_entry_id: str | None = None
        self._last_batch_packet_count = 0
        self._health_store.update(
            app_name=self._settings["app_name"],
            status=self._status,
            device_id=self._device_id,
            stream_key=self._settings["stream_key"],
            source=self._settings["source_name"],
            record_enabled=bool(self._settings["record_enabled"]),
            record_file=None,
            packet_count=0,
            publish_count=0,
            published_packet_count=0,
            dropped_packet_count=0,
            last_packet_at=None,
            last_publish_at=None,
            last_stream_entry_id=None,
            last_batch_packet_count=0,
            queue_capacity=int(self._settings["queue_maxsize"]),
            queue_size=0,
            last_error=None,
            updated_at=_isoformat(datetime.now(timezone.utc)),
        )

    def _refresh_health_locked(self) -> None:
        self._health_store.update(
            status=self._status,
            device_id=self._device_id,
            packet_count=self._packet_count,
            publish_count=self._publish_count,
            dropped_packet_count=self._dropped_packet_count,
            last_packet_at=_isoformat(self._last_packet_at),
            last_publish_at=_isoformat(self._last_publish_at),
            last_stream_entry_id=self._last_stream_entry_id,
            last_error=self._last_error,
            record_file=(
                str(self._recorder.record_file)
                if self._recorder.record_file is not None
                else None
            ),
            published_packet_count=self._published_packet_count,
            last_batch_packet_count=self._last_batch_packet_count,
            queue_capacity=int(self._settings["queue_maxsize"]),
            queue_size=self._publish_queue.qsize(),
            updated_at=_isoformat(datetime.now(timezone.utc)),
        )

    def _flush_health(self, *, force: bool) -> None:
        now = time.monotonic()
        if not force and (now - self._last_health_flush_monotonic) < self._health_flush_interval_seconds:
            return
        try:
            self._health_store.write()
            self._last_health_flush_monotonic = now
        except Exception:
            if now - self._last_health_write_warning_monotonic >= 1.0:
                logger.warning(
                    "EEG host bridge health status write failed path=%s",
                    self._settings["status_file"],
                    exc_info=True,
                )
                self._last_health_write_warning_monotonic = now

    def _update_status(self, status: str, device_id: str | None, error: str | None) -> None:
        with self._lock:
            self._status = status
            if device_id is not None:
                self._device_id = device_id
            if error:
                self._last_error = error
            elif status in {"idle", "scanning", "connecting", "connected", "streaming"}:
                self._last_error = None
            self._refresh_health_locked()
        self._flush_health(force=True)

    def _handle_packet(self, payload: bytes, device_id: str | None, received_at: datetime) -> None:
        with self._lock:
            self._packet_count += 1
            self._last_packet_at = received_at
            if device_id is not None:
                self._device_id = device_id
            self._refresh_health_locked()
        try:
            self._publish_queue.put_nowait(
                PacketEnvelope(
                    payload=payload,
                    device_id=device_id,
                    received_at=received_at,
                )
            )
        except queue.Full:
            now = time.monotonic()
            with self._lock:
                self._dropped_packet_count += 1
                self._last_error = "publish_queue_full"
                self._refresh_health_locked()
                dropped_total = self._dropped_packet_count
                queue_size = self._publish_queue.qsize()
            if now - self._last_queue_full_warning_monotonic >= self._queue_full_warning_interval_seconds:
                logger.warning(
                    "EEG host bridge publish queue is full; dropping packets "
                    "dropped_total=%s queue_size=%s queue_capacity=%s",
                    dropped_total,
                    queue_size,
                    int(self._settings["queue_maxsize"]),
                )
                self._last_queue_full_warning_monotonic = now
            self._flush_health(force=False)
            return
        self._flush_health(force=False)

    def _drain_publish_batch(self, first_envelope: PacketEnvelope) -> list[PacketEnvelope]:
        batch = [first_envelope]
        deadline = time.monotonic() + self._publish_batch_timeout_seconds
        while len(batch) < self._publish_batch_size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                batch.append(self._publish_queue.get(timeout=remaining))
            except queue.Empty:
                break
        return batch

    def _publisher_loop(self) -> None:
        while not self._stop_event.is_set() or not self._publish_queue.empty():
            try:
                envelope = self._publish_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            batch = self._drain_publish_batch(envelope)

            try:
                for item in batch:
                    self._recorder.record(
                        payload=item.payload,
                        received_at=item.received_at,
                        device_id=item.device_id,
                    )
            except Exception:
                logger.warning("EEG host bridge local recording failed", exc_info=True)

            try:
                last_envelope = batch[-1]
                combined_payload = b"".join(item.payload for item in batch)
                device_id = next(
                    (item.device_id for item in reversed(batch) if item.device_id),
                    None,
                )
                entry_id = self._writer.publish(
                    payload=combined_payload,
                    received_at=last_envelope.received_at,
                    first_received_at=batch[0].received_at,
                    device_id=device_id,
                    packet_count=len(batch),
                )
                with self._lock:
                    self._publish_count += 1
                    self._published_packet_count += len(batch)
                    self._last_publish_at = datetime.now(timezone.utc)
                    self._last_stream_entry_id = entry_id
                    self._last_batch_packet_count = len(batch)
                    self._refresh_health_locked()
            except Exception as exc:
                logger.warning("EEG host bridge Redis publish failed", exc_info=True)
                with self._lock:
                    self._last_error = str(exc)
                    self._refresh_health_locked()
                self._flush_health(force=True)
            finally:
                for _ in batch:
                    self._publish_queue.task_done()
                self._flush_health(force=False)

    def status_snapshot(self) -> dict[str, Any]:
        return self._health_store.snapshot()

    def run_forever(self) -> None:
        self._publish_thread.start()
        self._flush_health(force=True)
        try:
            asyncio.run(
                self._ble_client.run_forever(
                    stop_event=self._stop_event,
                    on_packet=self._handle_packet,
                    on_status=self._update_status,
                )
            )
        except KeyboardInterrupt:
            logger.info("EEG host bridge interrupted by user")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        self._publish_thread.join(timeout=5)
        self._recorder.close()
        self._writer.close()
        with self._lock:
            self._status = "stopped"
            self._refresh_health_locked()
        self._flush_health(force=True)
