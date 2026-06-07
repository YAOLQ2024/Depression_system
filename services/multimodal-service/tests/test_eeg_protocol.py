from __future__ import annotations

from app.services.eeg_protocol import (
    EEGPacketDecoder,
    FeaturePacket,
    WavePacket,
    build_feature_frame,
    build_wave_frame,
)


def test_decoder_parses_wave_frame_across_chunks() -> None:
    decoder = EEGPacketDecoder()
    frame = build_wave_frame(42, [0.1, -0.2, 0.3])

    first = decoder.feed(frame[:7])
    second = decoder.feed(frame[7:])

    assert first == []
    assert len(second) == 1
    packet = second[0]
    assert isinstance(packet, WavePacket)
    assert packet.seq == 42
    assert len(packet.channels) == 3


def test_decoder_parses_feature_frame_with_noise_prefix() -> None:
    decoder = EEGPacketDecoder()
    frame = build_feature_frame([float(index) for index in range(57)])

    packets = decoder.feed(b"\x00\x01garbage" + frame)

    assert len(packets) == 1
    packet = packets[0]
    assert isinstance(packet, FeaturePacket)
    assert len(packet.features) == 57
    assert packet.features[0] == 0.0
    assert packet.features[-1] == 56.0
    model_vector = packet.to_model_vector()
    assert len(model_vector) == 52
    assert 26.0 not in model_vector
    assert 41.0 not in model_vector
    assert 46.0 not in model_vector
    assert 54.0 not in model_vector
    assert 55.0 not in model_vector


def test_decoder_drops_invalid_crc_frame() -> None:
    decoder = EEGPacketDecoder()
    frame = bytearray(build_wave_frame(7, [1.0, 2.0, 3.0]))
    frame[-1] ^= 0x01

    packets = decoder.feed(bytes(frame))

    assert packets == []
