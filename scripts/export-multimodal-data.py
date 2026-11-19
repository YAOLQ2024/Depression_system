#!/usr/bin/env python3
"""Read-only five-modality export using the running multimodal container.

Usage: python3 scripts/export-multimodal-data.py [--output /absolute/new/folder]
The host needs only Python and Docker; database/MinIO dependencies run in-container.
"""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

CONTAINER = "mcs-jetson-multimodal-service-1"
FOLDERS = {"eeg": "01_脑电_EEG", "audio": "02_语音_Audio", "text": "03_文本_Text",
           "face": "04_表情_Face", "pose": "05_姿态_Pose"}
TABLES = ["multimodal_sessions", "multimodal_captures", "multimodal_inference_results",
          "multimodal_audio_turns", "multimodal_visual_frames", "multimodal_turn_bundles",
          "multimodal_eeg_explanations", "consultation_sessions", "consultation_turns",
          "assessment_sessions", "assessment_answers", "assessment_results", "encounter_sessions",
          "risk_evaluations", "risk_triggers", "intervention_sessions", "intervention_events"]


def dump_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_rows(path, rows):
    """Exact JSONL plus Excel-friendly CSV; nested values remain JSON."""
    with path.with_suffix(".jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            # Neutralize spreadsheet formulas in user-provided text. JSONL is unmodified.
            cooked = {}
            for k, v in row.items():
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False, default=str)
                if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")):
                    v = "'" + v
                cooked[k] = v
            writer.writerow(cooked)


def collect_uris(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from collect_uris(v)
    elif isinstance(value, list):
        for v in value:
            yield from collect_uris(v)
    elif isinstance(value, str) and value.startswith("s3://"):
        yield value


def object_modes(key):
    if key.startswith("raw/eeg/") or key.endswith(".npz"):
        return ["eeg"]
    if key.startswith("captures/") or key.lower().endswith((".jpg", ".jpeg", ".png")):
        return ["face", "pose"]
    if key.startswith("consultation/") or key.lower().endswith((".wav", ".webm", ".mp3", ".ogg", ".m4a")):
        return ["audio"]
    return []


def worker(output, since=None, excluded_session=None):
    from sqlalchemy import text
    from app.database import get_engine
    from app.services.object_storage import get_object_storage_client
    from minio.error import S3Error
    import numpy as np

    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    snapshot = {}
    with get_engine().connect().execution_options(isolation_level="REPEATABLE READ") as conn:
        with conn.begin():
            conn.execute(text("SET TRANSACTION READ ONLY"))
            cutoff = str(conn.execute(text("SELECT transaction_timestamp()" )).scalar())
            for table in TABLES:
                snapshot[table] = [dict(r) for r in conn.execute(text(f'SELECT * FROM "{table}" ORDER BY id')).mappings()]
            session_index = [dict(r) for r in conn.execute(text("""
                SELECT m.id AS multimodal_session_id, m.encounter_session_id, m.user_id,
                  m.flow_type, m.flow_run_id, m.status, m.started_at, m.created_at,
                  COALESCE(u.email ~* '(smoke|synthetic|test|demo)' OR
                    u.full_name ~* '(smoke|synthetic|test|demo|测试)', false) AS possible_test_account
                FROM multimodal_sessions m LEFT JOIN users u ON u.id=m.user_id ORDER BY m.created_at
            """)).mappings()]

    selection = None
    excluded_flow = None
    if excluded_session:
        excluded_flow = next((r["flow_run_id"] for r in snapshot["multimodal_sessions"] if r["id"] == excluded_session), None)
    if since:
        snapshot, selection = select_since(snapshot, since, excluded_session)
        kept_ids = {r["id"] for r in snapshot["multimodal_sessions"]}
        session_index = [r for r in session_index if r["multimodal_session_id"] in kept_ids]
        dump_json(root / "date_selection.json", selection)
    # Do not include account credentials or demographic profile snapshots.
    for row in snapshot["consultation_sessions"]:
        row.pop("participant_profile_snapshot", None)
    # Complete clinical table snapshot, including scale, risk and intervention data.
    # Older exports did not include all auxiliary tables; preserve availability explicitly.
    database_dir = root / "database_snapshot"
    database_dir.mkdir()
    for table, rows in snapshot.items():
        write_rows(database_dir / table, rows)
    refs = {mode: set() for mode in FOLDERS}
    for mode, folder in FOLDERS.items():
        dest = root / folder
        dest.mkdir()
        write_rows(dest / "session_index", session_index)
        for table in ("multimodal_sessions", "encounter_sessions", "consultation_sessions",
                      "assessment_sessions", "multimodal_turn_bundles"):
            write_rows(dest / table, snapshot[table])
        selected = {
            "multimodal_captures": [r for r in snapshot["multimodal_captures"] if r["modality"] == mode],
            "multimodal_inference_results": [r for r in snapshot["multimodal_inference_results"]
                                              if r["modality"] == ("speech" if mode == "audio" else mode)],
        }
        if mode == "eeg":
            selected["multimodal_eeg_explanations"] = snapshot["multimodal_eeg_explanations"]
        if mode in ("audio", "text"):
            for table in ("multimodal_audio_turns", "consultation_turns", "assessment_answers"):
                selected[table] = snapshot[table]
        if mode == "text":
            selected["assessment_results"] = snapshot["assessment_results"]
        if mode in ("face", "pose"):
            selected["multimodal_visual_frames"] = snapshot["multimodal_visual_frames"]
        for table, rows in selected.items():
            write_rows(dest / table, rows)
            for uri in collect_uris(rows):
                if mode in object_modes(uri.split("/", 3)[-1]):
                    refs[mode].add(uri)

    client = get_object_storage_client()
    objects = []
    protected_uris = retained_uris(snapshot, collect_uris) if since else set()
    for bucket in client.list_buckets():
        for obj in client.list_objects(bucket.name, recursive=True):
            if excluded_session and (excluded_session in obj.object_name or (excluded_flow and excluded_flow in obj.object_name)):
                continue
            if since and obj.last_modified < datetime.fromisoformat(since) and f"s3://{bucket.name}/{obj.object_name}" not in protected_uris:
                continue
            objects.append((bucket.name, obj.object_name, obj.size, obj.etag))
    inventory = []
    manifests = {m: [] for m in FOLDERS}
    eeg_windows = []
    known = set()
    cache = root / "_download_cache"
    cache.mkdir()
    for bucket, key, size, etag in objects:
        uri = f"s3://{bucket}/{key}"
        parts = PurePosixPath(bucket + "/" + key).parts
        if any(p in ("..", "/") for p in parts):
            raise ValueError("Unsafe object path")
        modes = object_modes(key)
        if not modes:
            raise ValueError(f"Unclassified object; extend exporter before proceeding: {uri}")
        local = cache.joinpath(*parts)
        local.parent.mkdir(parents=True, exist_ok=True)
        base = {"uri": uri, "bytes": size, "etag": etag}
        try:
            client.fget_object(bucket, key, str(local))
        except S3Error as exc:
            base.update(status="download_error", error=exc.code)
            inventory.append(base)
            for mode in modes:
                manifests[mode].append(dict(base))
            known.add(uri)
            continue
        actual_size = local.stat().st_size
        if actual_size != size:
            raise RuntimeError(f"Object changed size during export: {uri}")
        # Recheck ETag against listing to detect concurrent overwrite.
        if client.stat_object(bucket, key).etag != etag:
            raise RuntimeError(f"Object changed during export: {uri}")
        digest = hashlib.sha256(local.read_bytes()).hexdigest()
        base.update(status="saved", sha256=digest)
        inventory.append(base)
        known.add(uri)
        for mode in modes:
            relative = Path("files").joinpath(*parts)
            target = root / FOLDERS[mode] / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(local, target)
            manifests[mode].append({**base, "local_path": str(relative), "referenced_in_database": uri in refs[mode]})
        if "eeg" in modes:
            with np.load(local, allow_pickle=False) as data:
                samples = data["samples"]
                rate = int(data["sampling_rate"])
                channels = data["channel_names"].tolist()
                times = data["sample_timestamps_ms"]
                seq = data["sequences"]
                if samples.shape != (len(times), len(channels)) or len(seq) != len(times):
                    raise ValueError(f"Unexpected EEG array shape: {uri}")
                wave_rel = Path("waveform_csv").joinpath(*parts).with_suffix(".csv")
                wave = root / FOLDERS["eeg"] / wave_rel
                wave.parent.mkdir(parents=True, exist_ok=True)
                with wave.open("w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["sample_timestamp_ms", "sequence", *channels])
                    writer.writerows((int(times[i]), int(seq[i]), *samples[i].tolist()) for i in range(len(samples)))
                eeg_windows.append({"uri": uri, "sample_count": len(samples), "sampling_rate_hz": rate,
                                    "sample_seconds": len(samples) / rate, "channels": channels,
                                    "feature_frame_count": len(data["feature_frames"]),
                                    "multimodal_session_id": key.split("/")[2], "turn_id": key.split("/")[3],
                                    "waveform_csv": str(wave_rel)})
        local.unlink()
    shutil.rmtree(cache)
    for mode in FOLDERS:
        for uri in sorted(refs[mode] - known):
            manifests[mode].append({"uri": uri, "status": "missing_in_minio"})
        write_rows(root / FOLDERS[mode] / "file_manifest", manifests[mode])
        write_rows(root / FOLDERS[mode] / "missing_files", [r for r in manifests[mode] if r["status"] != "saved"])
    write_rows(root / FOLDERS["eeg"] / "eeg_windows", eeg_windows)
    write_rows(root / "object_inventory", inventory)
    summary = {
        "date_selection": selection,
        "database_snapshot_at_utc": cutoff,
        "export_finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "database_rows": {table: len(rows) for table, rows in snapshot.items()},
        "consultation_status": dict(Counter(r["status"] for r in snapshot["consultation_sessions"])),
        "assessment_status": dict(Counter(r["status"] for r in snapshot["assessment_sessions"])),
        "possible_test_sessions": sum(r["possible_test_account"] for r in session_index),
        "raw_objects": len(inventory), "raw_bytes": sum(r["bytes"] for r in inventory),
        "modalities": {mode: {
            "saved_files": sum(r["status"] == "saved" for r in rows),
            "unavailable_files": sum(r["status"] != "saved" for r in rows),
            "saved_bytes": sum(r.get("bytes", 0) for r in rows if r["status"] == "saved"),
        } for mode, rows in manifests.items()},
        "eeg_sample_count": sum(r["sample_count"] for r in eeg_windows),
        "eeg_sample_seconds": sum(r["sample_seconds"] for r in eeg_windows),
        "eeg_sessions_with_raw_files": len({r["multimodal_session_id"] for r in eeg_windows}),
        "eeg_turns_with_raw_files": len({(r["multimodal_session_id"], r["turn_id"]) for r in eeg_windows}),
    }
    dump_json(root / "summary.json", summary)
    instructions = """五模态数据导出说明

01_脑电_EEG：原始 NPZ（包含波形、时间戳、通道、特征和模型输入）及 waveform_csv 波形表。
02_语音_Audio：原始录音、标准化 WAV、转写和语音推理记录。
03_文本_Text：问诊问题/回答、语音转写、量表答案/结果和文本推理记录。
04_表情_Face：采样图片、表情推理与关键帧记录。
05_姿态_Pose：采样图片、姿态推理与关键帧记录。
表情和姿态来自同一摄像头，故两份导出分别附上同一套图片；不是两套独立拍摄数据。

每份都包含 session_index（会话索引）、会话关联表、轮次汇总、file_manifest（文件路径与 SHA256）
和 missing_files（缺失或下载失败的文件）。CSV 可用 Excel 打开；JSONL 保留原始嵌套数据和文本。
CSV 对以公式字符开头的文本加了单引号，原始内容请以 JSONL 为准。
通过 multimodal_session_id/session_id、encounter_session_id、flow_run_id、turn_id、question_key、
sample_id 关联五模态；各表字段含义请结合表名，consultation_turns.session_id 是问诊会话 ID，
multimodal_captures.session_id 是多模态会话 ID。
时间以字段中的时区为准；数据库时间为 UTC（+00:00），北京时间需加 8 小时。

数据库采用只读一致性快照；MinIO 文件在随后逐个读取，采集可继续进行。
数据库中的旧记录可能指向已经被清理的文件。missing_files 仅表示数据库引用文件的可用性，
不能恢复已删除内容；无 URI 的失败采集记录仍保留在对应表中。
按指定时间范围导出原始对象，包括未被关键帧表引用的采样图片；推理结果只按实际数据库记录导出。
脑电按回答窗口分文件，原始 NPZ 无损保留；eeg_windows.csv 列出每窗样本数与采样率。
eeg_sample_seconds 是样本数/采样率的累计值，并不代表连续录制或实际问诊时长，可能存在间隙。
摄像头原始链路保存的是采样图片，不是完整视频。本次不包括此前独立保存的本地 MP4。
possible_test_account 是按账号名称特征推测的测试标记，无法保证准确，未自动删除任何测试记录。
未导出账号密码和用户档案快照；这些文件仍可能包含个人健康信息，请妥善保存。

保存方法：将整个导出目录复制到移动硬盘；也可分别复制五个 ZIP，每个 ZIP 都能独立解压查看。
ZIP_SHA256.csv 可用于核对归档在复制前后是否一致；切勿只保存 CSV 而丢弃 files 原始文件目录。
本脚本只读取数据，不会删除 MinIO 或修改采集配置。
"""
    (root / "导出说明.txt").write_text(instructions, encoding="utf-8")
    if selection:
        with (root / "导出说明.txt").open("a", encoding="utf-8") as f:
            f.write("\n本次范围：" + selection["since_inclusive"] + " 及之后。\n")
            f.write("整场排除的多模态会话：" + str(excluded_session) + "\n")
    for folder in FOLDERS.values():
        shutil.copyfile(root / "导出说明.txt", root / folder / "导出说明.txt")
        shutil.copyfile(root / "summary.json", root / folder / "summary.json")
        if selection:
            shutil.copyfile(root / "date_selection.json", root / folder / "date_selection.json")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    parser.add_argument("--since", help="起始时间，包含时区，例如 2026-11-12T14:00:00+08:00")
    parser.add_argument("--exclude-session", help="整场排除的多模态会话 ID")
    parser.add_argument("--cleanup-before", action="store_true", help="清理 --since 之前的数据，需要明确指定此参数")
    parser.add_argument("--no-archives", action="store_true", help="仅生成目录，供数据集整理使用")
    args = parser.parse_args()
    if args.worker:
        if args.cleanup_before:
            if not args.since:
                parser.error("清理必须提供 --since")
            cleanup(args.since, collect_uris, args.worker, TABLES, args.exclude_session)
        else:
            worker(args.worker, args.since, args.exclude_session)
        return
    if args.cleanup_before:
        parser.error("清理操作仅由维护流程在容器内执行")
    output = (args.output or Path.home() / "Desktop" / ("多模态数据导出_" + datetime.now().strftime("%Y%m%d_%H%M%S"))).resolve()
    if output.exists():
        parser.error("输出目录已存在，请选择新的目录以免覆盖数据")
    temporary = "/tmp/multimodal-export-" + uuid.uuid4().hex
    # Read our source locally, then execute with the container's installed SDKs.
    command = ["docker", "exec", "-i", CONTAINER, "python", "-", "--worker", temporary]
    if args.since:
        command += ["--since", args.since]
    if args.exclude_session:
        command += ["--exclude-session", args.exclude_session]
    module = Path(__file__).with_name("multimodal-retention.py").read_text(encoding="utf-8")
    payload = ("exec(" + repr(module) + ")\n").encode() + Path(__file__).read_bytes()
    subprocess.run(command, input=payload, check=True)
    # Stage the copy so an incomplete export is not mistaken for a finished one.
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".multimodal-export-", dir=output.parent) as staging:
        subprocess.run(["docker", "cp", f"{CONTAINER}:{temporary}/.", staging], check=True)
        staged = Path(staging)
        checksums = []
        for folder in ([] if args.no_archives else FOLDERS.values()):
            archive = staged / (folder + ".zip")
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
                for source in sorted((staged / folder).rglob("*")):
                    if source.is_file():
                        z.write(source, source.relative_to(staged))
            with zipfile.ZipFile(archive) as z:
                if z.testzip() is not None:
                    raise RuntimeError(f"归档校验失败：{archive.name}")
            checksums.append({"archive": archive.name, "bytes": archive.stat().st_size,
                              "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()})
        write_rows(staged / "ZIP_SHA256", checksums)
        # Verify every original against the checksum captured at download time.
        for folder in FOLDERS.values():
            for line in (staged / folder / "file_manifest.jsonl").read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if row["status"] == "saved":
                    local = staged / folder / row["local_path"]
                    if hashlib.sha256(local.read_bytes()).hexdigest() != row["sha256"]:
                        raise RuntimeError(f"文件校验失败：{local}")
        staged.rename(output)
        # TemporaryDirectory tolerates the staging path having been renamed.
    subprocess.run(["docker", "exec", CONTAINER, "rm", "-rf", temporary], check=True)
    print(f"导出完成并通过原始文件 SHA256 和 ZIP 完整性校验：{output}")


if __name__ == "__main__":
    main()
