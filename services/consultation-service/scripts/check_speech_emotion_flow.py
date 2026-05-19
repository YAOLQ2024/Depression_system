#!/usr/bin/env python
from __future__ import annotations

import argparse
import io
import json
import math
import subprocess
import sys
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None
    final_headers = {"accept": "application/json"}
    if headers:
        final_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        final_headers["content-type"] = "application/json"

    req = request.Request(url, data=body, headers=final_headers, method=method)
    try:
        with request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {detail}") from exc


def encode_multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for name, (filename, file_bytes, mime_type) in files.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode(),
                f"Content-Type: {mime_type}\r\n\r\n".encode(),
                file_bytes,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def multipart_request(url: str, *, headers: dict[str, str], fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> dict[str, Any]:
    body, boundary = encode_multipart(fields, files)
    final_headers = {
        "accept": "application/json",
        "content-type": f"multipart/form-data; boundary={boundary}",
        **headers,
    }
    req = request.Request(url, data=body, headers=final_headers, method="POST")
    try:
        with request.urlopen(req, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed: {exc.code} {detail}") from exc


def build_test_wav(*, rate: int = 16000, duration_s: float = 1.0, freq: float = 220.0) -> bytes:
    frames = bytearray()
    total = int(rate * duration_s)
    for i in range(total):
        sample = int(0.22 * 32767 * math.sin(2 * math.pi * freq * i / rate))
        frames += sample.to_bytes(2, "little", signed=True)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(frames)
    return buffer.getvalue()


def run_command(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return completed.stdout.strip()


def complete_until_waiting_user_input(base_api: str, session_id: str, headers: dict[str, str]) -> None:
    response = json_request(f"{base_api}/consultations/{session_id}/start", method="POST", headers=headers)
    while True:
        consultation = response["data"]["consultation"]
        status = consultation["status"]
        item = consultation.get("current_question_item") or {}
        if status == "waiting_user_input":
            return
        if status == "waiting_system_completion" and item and item.get("response_required") is False:
            question_key = item["question_key"]
            response = json_request(
                f"{base_api}/consultations/{session_id}/question-items/{parse.quote(question_key)}/complete",
                method="POST",
                headers=headers,
            )
            continue
        raise RuntimeError(f"Unexpected consultation status before audio upload: {status}")


def assert_equal(label: str, left: Any, right: Any) -> None:
    if left != right:
        raise AssertionError(f"{label} mismatch: {left!r} != {right!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end smoke check for speech emotion flow.")
    parser.add_argument("--base-api", default="http://127.0.0.1:8012/api/v1")
    parser.add_argument("--acting-user-id", default="integration-speech-smoke")
    parser.add_argument("--postgres-container", default="compose-postgres-1")
    parser.add_argument("--consultation-container", default="compose-consultation-service-1")
    parser.add_argument("--db-user", default="mcs")
    parser.add_argument("--db-name", default="mcs")
    args = parser.parse_args()

    headers = {"x-mcs-user-id": args.acting_user_id}
    create_payload = {"user_id": args.acting_user_id}
    created = json_request(f"{args.base_api}/consultations", method="POST", headers=headers, payload=create_payload)
    session_id = created["data"]["consultation"]["session_id"]
    complete_until_waiting_user_input(args.base_api, session_id, headers)

    audio_bytes = build_test_wav()
    audio_response = multipart_request(
        f"{args.base_api}/consultations/{session_id}/turns/audio",
        headers=headers,
        fields={
            "transcript_text": "我最近总觉得心情不太好，晚上也睡不好。",
            "response_started_at": iso_now(),
            "response_completed_at": iso_now(),
            "mime_type": "audio/wav",
        },
        files={"audio_file": ("integration.wav", audio_bytes, "audio/wav")},
    )

    data = audio_response["data"]
    consultation = data["consultation"]
    consultation_turn = data["consultation_turn"]
    speech_result = data["speech_emotion_result"]
    live_speech = consultation.get("multimodal_live", {}).get("speech", {})

    turn_id = consultation_turn["turn_id"]
    audio_uri = consultation_turn["audio_uri"]
    original_audio_uri = consultation_turn["original_audio_uri"]
    normalized_wav_uri = consultation_turn["normalized_wav_uri"]
    speech_result_id = speech_result["speech_emotion_result_id"]
    primary_label = speech_result["primary_label"]
    primary_score = speech_result["primary_score"]
    transcript_text = consultation_turn.get("transcript_text")

    db_result = run_command(
        [
            "docker",
            "exec",
            args.postgres_container,
            "psql",
            "-U",
            args.db_user,
            "-d",
            args.db_name,
            "-t",
            "-A",
            "-F",
            "|",
            "-c",
            (
                "select id, consultation_turn_id, consultation_session_id, primary_label, primary_score, inference_status "
                f"from speech_emotion_results where id='{speech_result_id}';"
            ),
        ]
    )
    db_turn = run_command(
        [
            "docker",
            "exec",
            args.postgres_container,
            "psql",
            "-U",
            args.db_user,
            "-d",
            args.db_name,
            "-t",
            "-A",
            "-F",
            "|",
            "-c",
            (
                "select id, session_id, audio_uri, original_audio_uri, normalized_wav_uri, transcript_text "
                f"from consultation_turns where id='{turn_id}';"
            ),
        ]
    )
    db_live = run_command(
        [
            "docker",
            "exec",
            args.postgres_container,
            "psql",
            "-U",
            args.db_user,
            "-d",
            args.db_name,
            "-t",
            "-A",
            "-c",
            f"select multimodal_live_payload::text from consultation_sessions where id='{session_id}';",
        ]
    )

    bucket_prefix = "s3://mcs-consultation/"
    if not original_audio_uri.startswith(bucket_prefix):
        raise AssertionError(f"Unexpected original_audio_uri format: {original_audio_uri}")
    if not normalized_wav_uri.startswith(bucket_prefix):
        raise AssertionError(f"Unexpected normalized_wav_uri format: {normalized_wav_uri}")
    original_object_key = original_audio_uri[len(bucket_prefix) :]
    normalized_object_key = normalized_wav_uri[len(bucket_prefix) :]
    original_object_stat = run_command(
        [
            "docker",
            "exec",
            args.consultation_container,
            "python",
            "-c",
            (
                "from app.services.object_storage import get_object_storage_client; "
                f"s=get_object_storage_client().stat_object('mcs-consultation','{original_object_key}'); "
                "print(f'{s.bucket_name}|{s.object_name}|{s.size}')"
            ),
        ]
    )
    normalized_object_stat = run_command(
        [
            "docker",
            "exec",
            args.consultation_container,
            "python",
            "-c",
            (
                "from app.services.object_storage import get_object_storage_client; "
                f"s=get_object_storage_client().stat_object('mcs-consultation','{normalized_object_key}'); "
                "print(f'{s.bucket_name}|{s.object_name}|{s.size}')"
            ),
        ]
    )

    db_result_parts = db_result.split("|")
    db_turn_parts = db_turn.split("|")
    original_object_parts = original_object_stat.split("|")
    normalized_object_parts = normalized_object_stat.split("|")
    live_payload = json.loads(db_live)

    assert_equal("speech_result.id", db_result_parts[0], speech_result_id)
    assert_equal("speech_result.turn_id", db_result_parts[1], turn_id)
    assert_equal("speech_result.session_id", db_result_parts[2], session_id)
    assert_equal("speech_result.primary_label", db_result_parts[3], primary_label)
    assert_equal("speech_result.primary_score", float(db_result_parts[4]), float(primary_score))
    assert_equal("speech_result.status", db_result_parts[5], "completed")

    assert_equal("consultation_turn.id", db_turn_parts[0], turn_id)
    assert_equal("consultation_turn.session_id", db_turn_parts[1], session_id)
    assert_equal("consultation_turn.audio_uri", db_turn_parts[2], audio_uri)
    assert_equal("consultation_turn.original_audio_uri", db_turn_parts[3], original_audio_uri)
    assert_equal("consultation_turn.normalized_wav_uri", db_turn_parts[4], normalized_wav_uri)
    if not transcript_text or not transcript_text.strip():
        raise AssertionError("consultation_turn.transcript_text is empty")
    assert_equal("consultation_turn.transcript_text", db_turn_parts[5], transcript_text)

    assert_equal("live.primary_label", live_payload["speech"]["primary_label"], primary_label)
    assert_equal("live.status", live_payload["speech"]["status"], live_speech["status"])
    assert_equal("response live.primary_label", live_speech["primary_label"], primary_label)

    assert_equal("minio.original.bucket", original_object_parts[0], "mcs-consultation")
    assert_equal("minio.original.object_key", original_object_parts[1], original_object_key)
    assert_equal("minio.normalized.bucket", normalized_object_parts[0], "mcs-consultation")
    assert_equal("minio.normalized.object_key", normalized_object_parts[1], normalized_object_key)

    report = {
        "session_id": session_id,
        "turn_id": turn_id,
        "speech_emotion_result_id": speech_result_id,
        "audio_uri": audio_uri,
        "original_audio_uri": original_audio_uri,
        "normalized_wav_uri": normalized_wav_uri,
        "primary_label": primary_label,
        "primary_score": primary_score,
        "transcript_text": transcript_text,
        "db_consistent": True,
        "minio_consistent": True,
        "live_consistent": True,
        "original_minio_object_size": int(original_object_parts[2]),
        "normalized_wav_object_size": int(normalized_object_parts[2]),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - smoke script
        print(f"[speech-emotion-flow-check] {exc}", file=sys.stderr)
        raise
