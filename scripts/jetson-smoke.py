#!/usr/bin/env python3
"""Validate a running Jetson stack with a clearly labelled synthetic test account."""
from __future__ import annotations

import argparse
import http.cookiejar
import json
from pathlib import Path
import secrets
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import uuid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://127.0.0.1")
    parser.add_argument("--audio-fixture", type=Path, help="Prerecorded test audio; never a real patient recording")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    context = ssl.create_default_context(cafile=str(root / "infra/certs/jetson-local-ca.pem"))
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=context),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    )

    def request(path: str, payload=None, method="GET", *, absolute=False, raw=False, content_type=None):
        url = path if absolute else args.url.rstrip("/") + path
        body = payload if isinstance(payload, bytes) else None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body, method=method)
        if body is not None:
            req.add_header("Content-Type", content_type or "application/json")
        try:
            with opener.open(req, timeout=90) as response:
                content = response.read(1024) if raw else response.read()
                if raw:
                    return content
                result = json.loads(content)
                if "code" in result and result["code"] != 0:
                    raise RuntimeError(f"{path}: {result}")
                return result
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{method} {path}: HTTP {exc.code}: {exc.read().decode()}") from exc

    services = {
        "identity": 8011, "consultation": 8012, "assessment": 8013,
        "risk": 8014, "intervention": 8015, "followup": 8016,
        "multimodal": 18017, "gateway": 18080,
    }
    for name, port in services.items():
        request(f"http://127.0.0.1:{port}/health/ready", absolute=True)
        print(f"PASS readiness: {name}", flush=True)
    hostname = urlsplit(args.url).hostname
    if not hostname:
        parser.error("--url must include a hostname")
    if ":" in hostname:
        hostname = f"[{hostname}]"
    for name, url in {
        "consultation-web": args.url.rstrip("/"),
        "operations-web": f"https://{hostname}:8443",
    }.items():
        request(f"{url}/health/ready", absolute=True)
        print(f"PASS readiness: {name}", flush=True)
    assert b"<html" in request("/", raw=True).lower()
    assert request("/digital-human/consultation-v1/greeting-001.webm", raw=True)[:4] == bytes.fromhex("1a45dfa3")
    print("PASS trusted HTTPS, frontend and WebM asset", flush=True)

    account = f"jetson-deployment-smoke-{uuid.uuid4().hex[:8]}@mcs.local"
    password = secrets.token_urlsafe(24)
    request("/api/v1/auth/register", {
        "account": account, "password": password,
        "full_name": "部署验收测试账号（非真实患者）",
    }, "POST")
    request("/api/v1/auth/login", {"account": account, "password": password}, "POST")
    request("/api/v1/users/me")
    request("/api/v1/system/bootstrap")
    request("/api/v1/catalog/doctor-personas")
    request("/api/v1/users/me/profile", {
        "gender": "male", "age": 30, "height_cm": 170, "weight_kg": 65,
        "marital_status": "single", "parents_marital_status": "married",
        "parents_occupation": "部署测试", "prior_psychiatric_visit": "no",
    }, "PUT")
    print("PASS registration, cookie login, bootstrap and profile", flush=True)

    consultation = request("/api/v1/consultations", {
        "device_status": {"source": "deployment-test-fixture", "physical_devices_tested": False},
        "audio_channel_ready": True, "consent_confirmed": True,
    }, "POST")["data"]["consultation"]
    cid = consultation["session_id"]
    started = request(f"/api/v1/consultations/{cid}/start", {}, "POST")["data"]["consultation"]
    assert started["status"] != "draft"
    mid = consultation["multimodal_session_id"]
    request(f"/api/v1/multimodal/sessions/{mid}/warmup", {
        "modalities": ["text", "audio", "face", "pose", "eeg"],
    }, "POST")
    request(f"/api/v1/consultations/{cid}/multimodal/live")
    print("PASS consultation start, multimodal binding and five-modality warmup", flush=True)

    result = request("http://127.0.0.1:18017/api/v1/non-eeg/text-emotion/infer", {
        "text": "这是系统部署功能验收的测试语句。",
    }, "POST", absolute=True)
    assert result
    print("PASS text model inference", flush=True)
    if args.audio_fixture:
        boundary = "mcs-deployment-" + uuid.uuid4().hex
        fields = {
            "flow_run_id": cid, "origin_flow_type": "consultation",
            "question_key": "deployment-audio-fixture",
            "stage_id": started.get("current_stage_id") or "deployment-test",
            "node_id": started.get("current_node_id") or "deployment-test",
            "duration_ms": "4000", "mime_type": "audio/wav", "turn_id": uuid.uuid4().hex,
        }
        parts = []
        for key, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.extend([
            f'--{boundary}\r\nContent-Disposition: form-data; name="audio_file"; filename="deployment-fixture.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode(),
            args.audio_fixture.read_bytes(), f'\r\n--{boundary}--\r\n'.encode(),
        ])
        turn = request(f"/api/v1/multimodal/sessions/{mid}/audio-turns", b"".join(parts), "POST",
                       content_type=f"multipart/form-data; boundary={boundary}")["data"]["audio_turn"]
        deadline = time.monotonic() + 180
        while turn["processing_status"] not in {"completed", "failed"} and time.monotonic() < deadline:
            time.sleep(2)
            turn = request(f'/api/v1/multimodal/sessions/{mid}/audio-turns/{turn["audio_turn_id"]}')["data"]["audio_turn"]
        assert turn["processing_status"] == "completed", turn
        assert turn["transcript_text"].strip(), turn
        assert turn["audio_uri"] and turn["normalized_wav_uri"], turn
        print("PASS prerecorded audio upload, MinIO storage, CUDA ASR and emotion analysis", flush=True)
    request("/api/v1/auth/logout", {}, "POST")
    print(json.dumps({
        "result": "passed", "synthetic_test_account": account,
        "consultation_session_id": cid, "multimodal_session_id": mid,
        "physical_devices_tested": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
