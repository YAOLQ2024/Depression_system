from __future__ import annotations

import math
import struct
from typing import Sequence

SYNC = b"\x06\x09"
PKT_TYPE_WAVE = 0x01
PKT_TYPE_FEAT = 0x02
WAVE_CHANNEL_COUNT = 3
FEATURE_COUNT = 57
WAVE_PACKET_BYTES = 19
FEATURE_PACKET_BYTES = 233


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


def generate_wave_channels(simulated_second: float, *, amplitude: float) -> tuple[float, float, float]:
    base = float(amplitude)
    t = float(simulated_second)
    t7 = base * (0.60 * math.sin(2 * math.pi * 9.8 * t) + 0.14 * math.sin(2 * math.pi * 1.2 * t))
    t8 = base * (0.48 * math.sin(2 * math.pi * 10.6 * t + 0.45) + 0.18 * math.cos(2 * math.pi * 0.8 * t))
    fpz = base * (0.32 * math.sin(2 * math.pi * 12.4 * t + 0.9) + 0.08 * math.sin(2 * math.pi * 0.35 * t))
    return (float(t7), float(t8), float(fpz))


def generate_feature_vector(simulated_second: float) -> tuple[float, ...]:
    t = float(simulated_second)
    values = []
    for index in range(FEATURE_COUNT):
        low = math.sin(t * 0.35 + index * 0.13) * 0.7
        mid = math.cos(t * 0.12 + index * 0.07) * 0.2
        drift = math.sin(t * 0.02 + index * 0.01) * 0.1
        values.append(float(low + mid + drift))
    return tuple(values)
