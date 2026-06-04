from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Sequence

SYNC = b"\x06\x09"
PKT_TYPE_WAVE = 0x01
PKT_TYPE_FEAT = 0x02
WAVE_CHANNEL_COUNT = 3
FEATURE_COUNT = 57
WAVE_PACKET_BYTES = 19
FEATURE_PACKET_BYTES = 233


@dataclass(frozen=True, slots=True)
class WavePacket:
    seq: int
    channels: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class FeaturePacket:
    features: tuple[float, ...]


def crc16_ccitt(data: bytes, *, init: int = 0xFFFF) -> int:
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _validate_crc(frame: bytes) -> bool:
    if len(frame) < 4:
        return False
    crc_calc = crc16_ccitt(frame[:-2])
    crc_recv = (frame[-2] << 8) | frame[-1]
    return crc_calc == crc_recv


def parse_wave_frame(frame: bytes) -> WavePacket | None:
    if len(frame) != WAVE_PACKET_BYTES:
        return None
    if frame[:2] != SYNC or frame[2] != PKT_TYPE_WAVE or not _validate_crc(frame):
        return None
    seq = struct.unpack("<H", frame[3:5])[0]
    channels = struct.unpack("<3f", frame[5:17])
    return WavePacket(
        seq=seq,
        channels=(float(channels[0]), float(channels[1]), float(channels[2])),
    )


def parse_feature_frame(frame: bytes) -> FeaturePacket | None:
    if len(frame) != FEATURE_PACKET_BYTES:
        return None
    if frame[:2] != SYNC or frame[2] != PKT_TYPE_FEAT or not _validate_crc(frame):
        return None
    values = struct.unpack("<57f", frame[3:231])
    return FeaturePacket(features=tuple(float(value) for value in values))


class EEGPacketDecoder:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def reset(self) -> None:
        self._buffer.clear()

    def feed(self, chunk: bytes | bytearray | memoryview) -> list[WavePacket | FeaturePacket]:
        if not chunk:
            return []

        self._buffer.extend(bytes(chunk))
        packets: list[WavePacket | FeaturePacket] = []

        while len(self._buffer) >= 3:
            sync_index = self._buffer.find(SYNC)
            if sync_index < 0:
                self._buffer[:] = self._buffer[-1:]
                break
            if sync_index > 0:
                del self._buffer[:sync_index]

            if len(self._buffer) < 3:
                break

            packet_type = self._buffer[2]
            if packet_type == PKT_TYPE_WAVE:
                packet_length = WAVE_PACKET_BYTES
            elif packet_type == PKT_TYPE_FEAT:
                packet_length = FEATURE_PACKET_BYTES
            else:
                del self._buffer[0]
                continue

            if len(self._buffer) < packet_length:
                break

            frame = bytes(self._buffer[:packet_length])
            del self._buffer[:packet_length]

            packet = (
                parse_wave_frame(frame)
                if packet_type == PKT_TYPE_WAVE
                else parse_feature_frame(frame)
            )
            if packet is not None:
                packets.append(packet)

        return packets


def build_wave_frame(seq: int, channels: Sequence[float]) -> bytes:
    if len(channels) != WAVE_CHANNEL_COUNT:
        raise ValueError("wave_channel_count_mismatch")
    payload = bytearray(SYNC)
    payload.append(PKT_TYPE_WAVE)
    payload.extend(struct.pack("<H", int(seq) & 0xFFFF))
    payload.extend(struct.pack("<3f", *[float(value) for value in channels]))
    crc = crc16_ccitt(bytes(payload))
    payload.extend(struct.pack(">H", crc))
    return bytes(payload)


def build_feature_frame(features: Sequence[float]) -> bytes:
    if len(features) != FEATURE_COUNT:
        raise ValueError("feature_count_mismatch")
    payload = bytearray(SYNC)
    payload.append(PKT_TYPE_FEAT)
    payload.extend(struct.pack("<57f", *[float(value) for value in features]))
    crc = crc16_ccitt(bytes(payload))
    payload.extend(struct.pack(">H", crc))
    return bytes(payload)
