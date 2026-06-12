from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from app.protocol import (
    build_feature_frame,
    build_wave_frame,
    generate_feature_vector,
    generate_wave_channels,
)
from app.redis_stream_writer import RedisStreamWriter

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
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
    numeric = float(normalized)
    if numeric > 10_000_000_000:
        numeric /= 1000.0
    return datetime.fromtimestamp(numeric, tz=timezone.utc)


def _decode_payload(record: dict[str, Any]) -> bytes:
    payload_hex = record.get("payload_hex")
    if payload_hex not in (None, ""):
        return bytes.fromhex(str(payload_hex).strip())
    payload_base64 = record.get("payload_base64")
    if payload_base64 not in (None, ""):
        return base64.b64decode(str(payload_base64).strip())
    payload = record.get("payload")
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    raise ValueError("missing_payload")


def compute_sleep_seconds(
    previous_at: datetime | None,
    current_at: datetime,
    *,
    respect_timing: bool,
    speed: float,
) -> float:
    if not respect_timing or previous_at is None:
        return 0.0
    delta = (current_at - previous_at).total_seconds()
    if delta <= 0:
        return 0.0
    return delta / max(0.0001, float(speed))


@dataclass(slots=True)
class ReplayRecord:
    received_at: datetime
    payload: bytes
    device_id: str | None
    source: str | None
    packet_count: int


@dataclass(slots=True)
class ReplaySummary:
    mode: str
    published_entries: int = 0
    published_packets: int = 0
    bytes_total: int = 0
    first_recorded_at: datetime | None = None
    last_recorded_at: datetime | None = None
    first_published_at: datetime | None = None
    last_published_at: datetime | None = None
    loop_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "published_entries": self.published_entries,
            "published_packets": self.published_packets,
            "bytes_total": self.bytes_total,
            "first_recorded_at": _isoformat(self.first_recorded_at),
            "last_recorded_at": _isoformat(self.last_recorded_at),
            "first_published_at": _isoformat(self.first_published_at),
            "last_published_at": _isoformat(self.last_published_at),
            "loop_count": self.loop_count,
        }


def iter_jsonl_records(path: Path, *, source_filter: str | None = None) -> Iterator[ReplayRecord]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            source = str(payload.get("source") or "").strip() or None
            if source_filter and source != source_filter:
                continue
            received_at = _parse_timestamp(payload.get("received_at") or payload.get("ts"))
            if received_at is None:
                raise ValueError(f"missing_received_at line={line_number}")
            packet_count = int(payload.get("packet_count") or 1)
            yield ReplayRecord(
                received_at=received_at,
                payload=_decode_payload(payload),
                device_id=str(payload.get("device_id") or "").strip() or None,
                source=source,
                packet_count=max(1, packet_count),
            )


class RawBytesReplayer:
    def __init__(
        self,
        *,
        replay_file: Path,
        writer: RedisStreamWriter,
        source_name: str,
        respect_timing: bool,
        speed: float,
        loop: bool,
        max_records: int,
        source_filter: str | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._replay_file = Path(replay_file)
        self._writer = writer
        self._source_name = source_name
        self._respect_timing = bool(respect_timing)
        self._speed = max(0.0001, float(speed))
        self._loop = bool(loop)
        self._max_records = max(0, int(max_records))
        self._source_filter = source_filter
        self._sleep_fn = sleep_fn

    def run(self) -> ReplaySummary:
        if not self._replay_file.exists():
            raise FileNotFoundError(f"replay file not found: {self._replay_file}")

        summary = ReplaySummary(mode="raw")
        logger.info(
            "EEG replay started mode=raw file=%s speed=%s respect_timing=%s loop=%s stream=%s",
            self._replay_file,
            self._speed,
            self._respect_timing,
            self._loop,
            self._writer.stream_key,
        )

        while True:
            previous_at: datetime | None = None
            published_this_loop = 0
            summary.loop_count += 1

            for record in iter_jsonl_records(self._replay_file, source_filter=self._source_filter):
                if self._max_records and summary.published_entries >= self._max_records:
                    logger.info("EEG replay reached max_records=%s", self._max_records)
                    return summary

                sleep_seconds = compute_sleep_seconds(
                    previous_at,
                    record.received_at,
                    respect_timing=self._respect_timing,
                    speed=self._speed,
                )
                if sleep_seconds > 0:
                    self._sleep_fn(sleep_seconds)

                publish_now = _utcnow()
                self._writer.publish(
                    payload=record.payload,
                    received_at=publish_now,
                    device_id=record.device_id,
                    packet_count=record.packet_count,
                    extra_fields={
                        "replay_mode": "raw",
                        "recorded_received_at": _isoformat(record.received_at),
                        "recorded_source": record.source,
                    },
                )
                summary.published_entries += 1
                summary.published_packets += record.packet_count
                summary.bytes_total += len(record.payload)
                summary.first_recorded_at = summary.first_recorded_at or record.received_at
                summary.last_recorded_at = record.received_at
                summary.first_published_at = summary.first_published_at or publish_now
                summary.last_published_at = publish_now

                previous_at = record.received_at
                published_this_loop += 1

            if published_this_loop == 0:
                logger.warning("EEG replay file produced no matching records file=%s", self._replay_file)
                return summary
            if not self._loop:
                return summary


@dataclass(slots=True)
class SimulationState:
    next_wave_at: float = 0.0
    next_feature_at: float = 0.0
    wave_seq: int = 1


def build_simulated_payload_window(
    state: SimulationState,
    *,
    window_start: float,
    window_end: float,
    wave_rate_hz: int,
    feature_rate_hz: int,
    amplitude: float,
) -> tuple[bytes, int, int, int]:
    wave_period = 1.0 / max(1, int(wave_rate_hz))
    feature_period = 1.0 / max(1, int(feature_rate_hz))
    cursor = max(0.0, float(window_start))
    if state.next_wave_at < cursor:
        state.next_wave_at = cursor
    if state.next_feature_at < cursor:
        state.next_feature_at = cursor

    parts: list[bytes] = []
    packet_count = 0
    wave_count = 0
    feature_count = 0
    inclusive_end = float(window_end) + 1e-12

    while state.next_wave_at < inclusive_end or state.next_feature_at < inclusive_end:
        if state.next_wave_at <= state.next_feature_at:
            event_at = state.next_wave_at
            if event_at >= inclusive_end:
                break
            channels = generate_wave_channels(event_at, amplitude=amplitude)
            parts.append(build_wave_frame(state.wave_seq, channels))
            state.wave_seq = (state.wave_seq + 1) & 0xFFFF
            if state.wave_seq == 0:
                state.wave_seq = 1
            state.next_wave_at += wave_period
            wave_count += 1
            packet_count += 1
            continue

        event_at = state.next_feature_at
        if event_at >= inclusive_end:
            break
        parts.append(build_feature_frame(generate_feature_vector(event_at)))
        state.next_feature_at += feature_period
        feature_count += 1
        packet_count += 1

    return (b"".join(parts), packet_count, wave_count, feature_count)


class SimulatedReplayer:
    def __init__(
        self,
        *,
        writer: RedisStreamWriter,
        source_name: str,
        speed: float,
        duration_seconds: float,
        wave_rate_hz: int,
        feature_rate_hz: int,
        publish_interval_ms: int,
        amplitude: float,
        device_id: str,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._writer = writer
        self._source_name = source_name
        self._speed = max(0.0001, float(speed))
        self._duration_seconds = max(0.001, float(duration_seconds))
        self._wave_rate_hz = max(1, int(wave_rate_hz))
        self._feature_rate_hz = max(1, int(feature_rate_hz))
        self._publish_interval_seconds = max(0.001, int(publish_interval_ms) / 1000.0)
        self._amplitude = max(0.001, float(amplitude))
        self._device_id = device_id
        self._sleep_fn = sleep_fn

    def run(self) -> ReplaySummary:
        summary = ReplaySummary(mode="simulate")
        logger.info(
            "EEG replay started mode=simulate duration_seconds=%s speed=%s wave_rate_hz=%s feature_rate_hz=%s stream=%s",
            self._duration_seconds,
            self._speed,
            self._wave_rate_hz,
            self._feature_rate_hz,
            self._writer.stream_key,
        )
        state = SimulationState()
        simulated_elapsed = 0.0

        while simulated_elapsed < self._duration_seconds:
            window_start = simulated_elapsed
            window_end = min(self._duration_seconds, window_start + self._publish_interval_seconds)
            payload, packet_count, wave_count, feature_count = build_simulated_payload_window(
                state,
                window_start=window_start,
                window_end=window_end,
                wave_rate_hz=self._wave_rate_hz,
                feature_rate_hz=self._feature_rate_hz,
                amplitude=self._amplitude,
            )
            if payload:
                publish_now = _utcnow()
                self._writer.publish(
                    payload=payload,
                    received_at=publish_now,
                    device_id=self._device_id,
                    packet_count=packet_count,
                    extra_fields={
                        "replay_mode": "simulate",
                        "sim_window_start": f"{window_start:.6f}",
                        "sim_window_end": f"{window_end:.6f}",
                        "sim_wave_count": wave_count,
                        "sim_feature_count": feature_count,
                    },
                )
                summary.published_entries += 1
                summary.published_packets += packet_count
                summary.bytes_total += len(payload)
                summary.first_published_at = summary.first_published_at or publish_now
                summary.last_published_at = publish_now
            simulated_elapsed = window_end
            if simulated_elapsed < self._duration_seconds:
                self._sleep_fn((window_end - window_start) / self._speed)

        summary.loop_count = 1
        return summary
