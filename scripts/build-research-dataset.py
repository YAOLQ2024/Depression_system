#!/usr/bin/env python3
"""Merge immutable exports into a dated, auditable research dataset (offline only)."""
import argparse
import csv
import hashlib
import html
import json
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape

TZ = ZoneInfo("Asia/Shanghai")
MODES = {"eeg": "01_脑电_EEG", "audio": "02_语音_Audio", "text": "03_文本_Text",
         "face": "04_表情_Face", "pose": "05_姿态_Pose"}
PARENT = {
    "consultation_turns": ("consultation_sessions", "session_id"),
    "assessment_answers": ("assessment_sessions", "session_id"),
    "assessment_results": ("assessment_sessions", "session_id"),
    "multimodal_captures": ("multimodal_sessions", "session_id"),
    "multimodal_inference_results": ("multimodal_sessions", "session_id"),
    "multimodal_visual_frames": ("multimodal_sessions", "session_id"),
    "multimodal_turn_bundles": ("multimodal_sessions", "session_id"),
    "multimodal_eeg_explanations": ("multimodal_sessions", "session_id"),
    "multimodal_audio_turns": ("multimodal_sessions", "multimodal_session_id"),
    "risk_triggers": ("risk_evaluations", "evaluation_id"),
    "intervention_events": ("intervention_sessions", "session_id"),
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def read_rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()] if path.exists() else []


def json_file(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def table(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    names = fields or list(dict.fromkeys(k for r in rows for k in r)) or ["no_records"]
    with path.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = {}
            for k, v in r.items():
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")):
                    v = "'" + v
                out[k] = v
            w.writerow(out)


def local_time(value):
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamp missing timezone: " + str(value))
    return dt.astimezone(TZ).isoformat()


def uris(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from uris(v)
    elif isinstance(value, list):
        for v in value:
            yield from uris(v)
    elif isinstance(value, str) and value.startswith("s3://"):
        yield value


def load_batch(path, name):
    tables = defaultdict(dict)
    available = set()
    candidates = sorted((path / "database_snapshot").glob("*.jsonl"))
    if not candidates:
        candidates = [p for folder in MODES.values() for p in sorted((path / folder).glob("*.jsonl"))]
    ignored = {"session_index", "file_manifest", "missing_files", "eeg_windows"}
    for source in candidates:
        if source.stem in ignored:
            continue
        available.add(source.stem)
        for r in read_rows(source):
            rid = r["id"]
            previous = tables[source.stem].get(rid)
            if previous is not None and previous != r:
                raise ValueError(f"Conflicting records inside source: {name}/{source.stem}/{rid}")
            tables[source.stem][rid] = r
    assets = {}
    unavailable = []
    for mode, folder in MODES.items():
        for r in read_rows(path / folder / "file_manifest.jsonl"):
            if r["status"] != "saved":
                unavailable.append({"batch": name, "mode": mode, **r})
                continue
            source = path / folder / r["local_path"]
            if not source.is_file() or source.stat().st_size != r["bytes"] or digest(source) != r["sha256"]:
                raise ValueError(f"Source file checksum mismatch: {source}")
            if r["uri"] in assets and assets[r["uri"]]["sha256"] != r["sha256"]:
                raise ValueError("Conflicting copies of object: " + r["uri"])
            assets.setdefault(r["uri"], {**r, "source": source, "batch": name, "mode": mode})
    return {"name": name, "path": path, "tables": tables, "assets": assets,
            "available_tables": sorted(available), "unavailable": unavailable,
            "summary": json.loads((path / "summary.json").read_text())}


def workbook(path, sheets):
    """Small standards-based XLSX writer; inline strings never become formulas."""
    def cell(col, row, value, style=0):
        letters = ""
        while col:
            col, rem = divmod(col - 1, 26)
            letters = chr(65 + rem) + letters
        ref = f"{letters}{row}"
        if isinstance(value, bool):
            return f'<c r="{ref}" s="{style}" t="b"><v>{int(value)}</v></c>'
        if isinstance(value, (int, float)):
            return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
        value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value or "")
        value = "".join(ch for ch in value if ch >= " " or ch in "\t\n\r")[:32767]
        return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>'
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        types = ['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
                 '<Default Extension="xml" ContentType="application/xml"/>',
                 '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
                 '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
        for i in range(1, len(sheets) + 1):
            types.append(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'+"".join(types)+'</Types>')
        z.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/styles.xml", f'<styleSheet {ns}><fonts count="2"><font><sz val="11"/><name val="等线"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="等线"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF133B47"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        definitions = []
        relationships = []
        for i, (name, rows) in enumerate(sheets.items(), 1):
            definitions.append(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>')
            relationships.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
            fields = list(dict.fromkeys(k for r in rows for k in r)) or ["无记录"]
            sheet = [f'<worksheet {ns}><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>',
                     '<cols>'+''.join(f'<col min="{c}" max="{c}" width="24" customWidth="1"/>' for c in range(1,len(fields)+1))+'</cols><sheetData>']
            sheet.append('<row r="1">'+''.join(cell(c,1,f,1) for c,f in enumerate(fields,1))+'</row>')
            for n, row in enumerate(rows, 2):
                sheet.append(f'<row r="{n}">'+''.join(cell(c,n,row.get(f)) for c,f in enumerate(fields,1))+'</row>')
            sheet.append('</sheetData></worksheet>')
            z.writestr(f"xl/worksheets/sheet{i}.xml", ''.join(sheet))
        relationships.append(f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
        z.writestr("xl/workbook.xml", f'<workbook {ns} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(definitions)+'</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(relationships)+'</Relationships>')


def build(old, new, output):
    import numpy as np
    if output.exists():
        raise ValueError("Refusing to overwrite dataset: " + str(output))
    batches = [load_batch(old, "B01_历史导出"), load_batch(new, "B02_新增采集")]
    print("来源文件 SHA256 校验通过", flush=True)
    output.mkdir(parents=True)
    raw_dir = output / "01_原始总数据集"
    mode_dir = output / "02_各模态数据集"
    scale_dir = output / "03_量表结果数据集"
    audit_dir = output / "04_来源与质量核验"
    for directory in (raw_dir, mode_dir, scale_dir, audit_dir):
        directory.mkdir()
    merged = defaultdict(dict)
    provenance = defaultdict(set)
    assets = {}
    for batch in batches:
        for name, records in batch["tables"].items():
            for rid, row in records.items():
                if rid in merged[name] and merged[name][rid] != row:
                    raise ValueError(f"Record conflict, requires review: {name}/{rid}")
                merged[name][rid] = row
                provenance[(name, rid)].add(batch["name"])
        for uri, asset in batch["assets"].items():
            if uri in assets and assets[uri]["sha256"] != asset["sha256"]:
                raise ValueError("Object changed between batches: " + uri)
            assets.setdefault(uri, asset)
        folder = audit_dir / batch["name"]
        folder.mkdir()
        json_file(folder / "source_summary.json", batch["summary"])
        json_file(folder / "source_availability.json", {"source_path": str(batch["path"]),
                  "available_tables": batch["available_tables"],
                  "notes": "仅保存临床业务表；账号凭据未导出。历史批次未导出的辅助表不能恢复。"})
        for name, records in batch["tables"].items():
            table(folder / "数据库原始表" / name, list(records.values()))

    def case_for(name, row, depth=0):
        if depth > 8 or row is None:
            return None
        if name == "encounter_sessions":
            return row["id"]
        if row.get("encounter_session_id") in merged["encounter_sessions"]:
            return row["encounter_session_id"]
        if name in PARENT:
            target, field = PARENT[name]
            return case_for(target, merged.get(target,{}).get(row.get(field)), depth+1)
        if name == "multimodal_sessions":
            target = str(row.get("flow_type")) + "_sessions"
            return case_for(target, merged.get(target,{}).get(row.get("flow_run_id")), depth+1)
        for field, target in (("source_consultation_flow_run_id", "consultation_sessions"),
                              ("consultation_session_id", "consultation_sessions"),
                              ("assessment_session_id", "assessment_sessions")):
            if row.get(field) in merged.get(target,{}):
                return case_for(target, merged[target][row[field]], depth+1)
        return None

    cases = {}
    for rid, row in sorted(merged["encounter_sessions"].items(), key=lambda x: x[1]["created_at"]):
        start = local_time(row.get("started_at") or row["created_at"])
        day = start[:10]
        case_id = "CASE_"+day.replace("-", "")+"_"+rid.replace("-", "")[:12]
        cases[rid] = {"case_id": case_id, "encounter_session_id": rid, "collection_date_bj": day,
                      "started_at_bj": start, "source_batches": sorted(provenance[("encounter_sessions", rid)]),
                      "account_key": "|".join(sorted(provenance[("encounter_sessions", rid)]))+":"+str(row.get("user_id")),
                      "person_id_verified": False, "suspected_test_account": False}
    if len({r["case_id"] for r in cases.values()}) != len(cases):
        raise ValueError("Case ID collision")
    for batch in batches:
        for r in read_rows(batch["path"] / MODES["eeg"] / "session_index.jsonl"):
            enc = case_for("multimodal_sessions", merged["multimodal_sessions"].get(r["multimodal_session_id"]))
            if enc in cases and r.get("possible_test_account"):
                cases[enc]["suspected_test_account"] = True
    groups = defaultdict(lambda: defaultdict(list))
    orphans = []
    for name, records in merged.items():
        for row in records.values():
            enc = case_for(name, row)
            if enc in cases:
                groups[enc][name].append(row)
            else:
                orphans.append({"table": name, "id": row["id"], "reason": "no_verified_encounter_link"})
    table(audit_dir / "未关联业务记录", orphans)
    if orphans:
        # Preserve everything, but never guess a case association.
        for name, rows in merged.items():
            selected = [r for r in rows.values() if case_for(name, r) not in cases]
            if selected:
                table(raw_dir / "未关联记录" / name, selected)
    record_metadata = defaultdict(list)
    for name, records in merged.items():
        if name.endswith("sessions"):
            continue
        for row in records.values():
            for uri in set(uris(row)):
                record_metadata[uri].append((name, row, case_for(name, row)))

    def path_owner(uri):
        parts = urlparse(uri).path.lstrip("/").split("/")
        if parts[:2] in (["raw", "eeg"], ["captures", "visual"], ["captures", "face"], ["captures", "pose"]) and len(parts)>2:
            return case_for("multimodal_sessions", merged["multimodal_sessions"].get(parts[2]))
        if len(parts)>1 and parts[0] == "consultation":
            for name in ("consultation_sessions", "assessment_sessions"):
                if parts[1] in merged[name]:
                    return case_for(name, merged[name][parts[1]])
        owners = {enc for _, _, enc in record_metadata[uri] if enc in cases}
        if len(owners) == 1:
            return owners.pop()
        return None

    def case_subdir(enc):
        return Path(cases[enc]["collection_date_bj"]) / cases[enc]["case_id"] if enc in cases else Path("未知日期/未关联文件")

    object_rows = []
    mode_samples = defaultdict(list)
    eeg_vectors = []
    eeg_flat = []
    duplicate_refs = []
    all_uris = set(assets)
    missing_refs = []
    for uri, rows in record_metadata.items():
        if uri not in all_uris:
            missing_refs.append({"uri": uri, "referenced_records": [{"table": t,"id":r["id"]} for t,r,_ in rows]})
    for i, (uri, asset) in enumerate(sorted(assets.items()), 1):
        enc = path_owner(uri)
        case = cases.get(enc, {})
        parsed = urlparse(uri)
        key = Path(parsed.netloc) / parsed.path.lstrip("/")
        if ".." in key.parts:
            raise ValueError("Unsafe storage path")
        relative = Path("按日期") / case_subdir(enc) / "files" / key
        original = raw_dir / relative
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(asset["source"], original)
        if digest(original) != asset["sha256"]:
            raise ValueError("Copy checksum failed")
        references = record_metadata[uri]
        capture_rows = [(t,r) for t,r,_ in references if t in ("multimodal_captures", "multimodal_audio_turns", "multimodal_visual_frames")]
        event_times = [local_time(r.get("sample_started_at") or r.get("captured_at") or r.get("response_started_at") or r.get("created_at")) for _,r in capture_rows]
        event_times = [t for t in event_times if t]
        acquired_at = min(event_times) if event_times else case.get("started_at_bj")
        row = {"asset_id": "A_"+hashlib.sha256(uri.encode()).hexdigest()[:20],
               "case_id": case.get("case_id"), "encounter_session_id": enc,
               "case_date_bj": case.get("collection_date_bj"), "acquired_at_bj": acquired_at,
               "acquired_date_bj": acquired_at[:10] if acquired_at else None,
               "time_source": "capture_record" if event_times else "session_start_fallback",
               "source_batch": asset["batch"], "uri": uri, "bytes": asset["bytes"],
               "sha256": asset["sha256"], "original_path": str(original.relative_to(output)),
               "storage_kind": "eeg" if parsed.path.startswith("/raw/eeg/") else "visual" if parsed.path.startswith("/captures/") else "audio",
               "associated_record_ids": sorted({r["id"] for _,r in capture_rows})}
        object_rows.append(row)
        modes = ["face", "pose"] if row["storage_kind"]=="visual" else [row["storage_kind"]]
        turn_id = parsed.path.split("/")[4] if row["storage_kind"] in ("eeg", "visual") and len(parsed.path.split("/"))>4 else None
        capture = [r for t,r in capture_rows if t=="multimodal_captures" and r.get("modality")==modes[0]]
        if len(capture)>1:
            duplicate_refs.append({"uri":uri,"capture_record_ids":[r["id"] for r in capture],"note":"多个采集记录引用同一对象；物理文件只按一个样本计数，旧版本内容无法据此恢复"})
        for mode in modes:
            target = mode_dir / MODES[mode] / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
            sample = {**row, "turn_id": turn_id or next((r.get("turn_id") for _,r in capture_rows if r.get("turn_id")),None),
                      "input_path": str(target.relative_to(mode_dir/MODES[mode])),
                      "label_scope": "encounter_scale_result", "diagnosis_label_available": False}
            sample.update(question_key=next((r.get("question_key") for _,r in capture_rows if r.get("question_key")),None))
            mode_samples[mode].append(sample)
        if row["storage_kind"]=="eeg":
            sample=mode_samples["eeg"][-1]
            with np.load(original,allow_pickle=False) as data:
                count=len(data["samples"])
                rate=int(data["sampling_rate"])
                vector=data["aggregate_vector"].tolist() if "aggregate_vector" in data else []
                scaled=data["scaled_vector"].tolist() if "scaled_vector" in data else []
                sample.update(sample_count=count,sampling_rate_hz=rate,sample_seconds=count/rate,
                              channels=data["channel_names"].tolist(), feature_frame_count=len(data["feature_frames"]),
                              has_model_vector_156=len(vector)==156 and len(scaled)==156)
                eeg_vectors.append({"asset_id":row["asset_id"],"case_id":row["case_id"],"turn_id":sample["turn_id"],
                                    "input_path":sample["input_path"],"aggregate_vector":vector,"scaled_vector":scaled,
                                    "selected_indices":data["selected_indices"].tolist() if "selected_indices" in data else [],
                                    "model_sha256":str(data["model_sha256"].item()) if "model_sha256" in data else None})
                if sample["has_model_vector_156"]:
                    eeg_flat.append({"asset_id":row["asset_id"],"case_id":row["case_id"],**{f"f{j:03}":v for j,v in enumerate(scaled)}})
            source_wave=asset["source"].parents[len(Path(asset["local_path"]).parts)-1] / "waveform_csv" / key.with_suffix(".csv")
            if not source_wave.is_file():
                raise ValueError("EEG waveform export absent: "+str(source_wave))
            wave_target=mode_dir/MODES["eeg"]/"按日期"/case_subdir(enc)/"waveform_csv"/key.with_suffix(".csv")
            wave_target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source_wave,wave_target)
            sample["waveform_csv_path"]=str(wave_target.relative_to(mode_dir/MODES["eeg"]))
        if i%1000==0:
            print(f"已整理 {i}/{len(assets)} 个原始对象",flush=True)

    # Text inputs: keep source text, deduplicate matching ASR copies by audio URI.
    consumed_audio=set()
    text_seen=set()
    for name in ("consultation_turns","assessment_answers","multimodal_audio_turns"):
        for r in merged[name].values():
            text=r.get("transcript_text") or r.get("raw_input")
            enc=case_for(name,r)
            audio_uris={r.get(k) for k in ("audio_uri","original_audio_uri","normalized_wav_uri") if r.get(k)}
            if not text or (name=="multimodal_audio_turns" and audio_uris & consumed_audio):
                continue
            turn=r.get("turn_id") or (r["id"] if name=="consultation_turns" else None)
            identity=(enc,turn,r.get("question_key"),text)
            if identity in text_seen:
                continue
            text_seen.add(identity)
            consumed_audio.update(audio_uris)
            case=cases.get(enc,{})
            asset_id="T_"+hashlib.sha256((name+":"+r["id"]).encode()).hexdigest()[:20]
            relative=Path("按日期")/case_subdir(enc)/"texts"/(asset_id+".txt")
            target=mode_dir/MODES["text"]/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(text,encoding="utf-8")
            mode_samples["text"].append({"asset_id":asset_id,"case_id":case.get("case_id"),"encounter_session_id":enc,
                 "case_date_bj":case.get("collection_date_bj"),"source_table":name,"source_record_id":r["id"],
                 "turn_id":turn,"question_key":r.get("question_key"),"question_text":r.get("question_text"),
                 "acquired_at_bj":local_time(r.get("response_completed_at") or r["created_at"]),
                 "text":text,"input_path":str(relative),"sha256":digest(target),
                 "label_scope":"encounter_scale_result","diagnosis_label_available":False})

    labels=[]
    for r in merged["assessment_results"].values():
        enc=case_for("assessment_results",r)
        case=cases.get(enc,{})
        labels.append({"case_id":case.get("case_id"),"encounter_session_id":enc,
                       "assessment_session_id":r["session_id"],"case_date_bj":case.get("collection_date_bj"),
                       "result_date_bj":local_time(r["completed_at"])[:10],"scale_slug":r["scale_slug"],
                       "raw_score":r["raw_score"],"derived_score":r["derived_score"],
                       "interpretation_level":r.get("interpretation_level"),"interpretation_label":r.get("interpretation_label"),
                       "risk_flags":r.get("risk_flags"),"completed_at_bj":local_time(r["completed_at"]),
                       "label_source":"stored_scale_result","label_scope":"encounter",
                       "is_clinician_diagnosis":False,"source_record_id":r["id"]})
    table(scale_dir/"量表分数与标签",labels)
    answers=[]
    for r in merged["assessment_answers"].values():
        case=cases.get(case_for("assessment_answers",r),{})
        answers.append({"case_id":case.get("case_id"),"case_date_bj":case.get("collection_date_bj"),**r})
    table(scale_dir/"逐题答案",answers)

    for enc,case in cases.items():
        g=groups[enc]
        scale_sessions=g["assessment_sessions"]
        case.update(consultation_status="|".join(sorted({r["status"] for r in g["consultation_sessions"]})),
                    assessment_status="|".join(sorted({r["status"] for r in scale_sessions})) or "not_started",
                    assessment_completed=any(r["status"]=="completed" for r in scale_sessions),
                    scale_result_count=len(g["assessment_results"]),scale_slugs=sorted({r["scale_slug"] for r in g["assessment_results"]}),
                    consultation_turn_count=len(g["consultation_turns"]),scale_answer_count=len(g["assessment_answers"]),
                    raw_case_path=str((raw_dir/"按日期"/case_subdir(enc)).relative_to(output)))
        for mode in MODES:
            case[mode+"_input_count"]=sum(s["case_id"]==case["case_id"] for s in mode_samples[mode])
        case["all_five_modalities_available"]=all(case[m+"_input_count"]>0 for m in MODES)
        case["eeg_model_vector_count"]=sum(s["case_id"]==case["case_id"] and s.get("has_model_vector_156",False) for s in mode_samples["eeg"])
        json_file(raw_dir/"按日期"/case_subdir(enc)/"会话信息.json",case)
        for name,rows in g.items():
            if rows:
                table(raw_dir/"按日期"/case_subdir(enc)/"数据库记录"/name,rows)
        sd=scale_dir/"按日期"/case_subdir(enc)
        if scale_sessions:
            table(sd/"量表会话",scale_sessions)
            table(sd/"量表结果",[r for r in labels if r["case_id"]==case["case_id"]])
            table(sd/"逐题答案",[r for r in answers if r["case_id"]==case["case_id"]])

    cases_list=list(cases.values())
    for mode,folder in MODES.items():
        directory=mode_dir/folder
        directory.mkdir(exist_ok=True)
        table(directory/"样本索引",mode_samples[mode])
        table(directory/"会话与量表标签",[c for c in cases_list if c[mode+"_input_count"]])
        relevant_cases={s["case_id"] for s in mode_samples[mode]}
        table(directory/"量表标签",[r for r in labels if r["case_id"] in relevant_cases])
        inference_mode="speech" if mode=="audio" else mode
        inferences=[{ "case_id":cases.get(case_for("multimodal_inference_results",r),{}).get("case_id"),**r}
                    for r in merged["multimodal_inference_results"].values() if r["modality"]==inference_mode]
        table(directory/"模型预测_非人工标签",inferences)
        captures=[r for r in merged["multimodal_captures"].values() if r["modality"]==mode]
        table(directory/"采集记录",captures)
    table(mode_dir/MODES["eeg"]/"模型输入向量",eeg_vectors)
    table(mode_dir/MODES["eeg"]/"模型输入_标准化156维",eeg_flat)
    table(raw_dir/"原始文件索引",object_rows)
    table(audit_dir/"缺失原始文件",missing_refs)
    table(audit_dir/"同一对象多记录引用",duplicate_refs)
    aligned=defaultdict(lambda:{m:[] for m in MODES})
    for mode, samples in mode_samples.items():
        for sample in samples:
            if sample.get("turn_id") and sample.get("case_id"):
                aligned[(sample["case_id"],sample["turn_id"])][mode].append(sample["asset_id"])
    for r in merged["multimodal_turn_bundles"].values():
        case=cases.get(case_for("multimodal_turn_bundles",r),{})
        if case.get("case_id"):
            aligned[(case["case_id"],r["turn_id"])]
    alignment=[]
    by_id={c["case_id"]:c for c in cases_list}
    for (case_id,turn_id),values in sorted(aligned.items()):
        alignment.append({"case_id":case_id,"case_date_bj":by_id[case_id]["collection_date_bj"],"turn_id":turn_id,
                          "asset_ids_by_modality":values,"missing_modalities":[m for m,ids in values.items() if not ids],
                          **{m+"_count":len(ids) for m,ids in values.items()}})
    table(raw_dir/"轮次对齐索引",alignment)
    feature_names=[]
    for r in merged["multimodal_inference_results"].values():
        p=r.get("inference_payload",{}).get("_explanation_input",{})
        if p.get("feature_names"):
            feature_names=p["feature_names"]
            break
    json_file(mode_dir/MODES["eeg"]/"特征说明.json",{
        "standardized_vector_columns":[f"f{i:03}" for i in range(156)],
        "source_feature_names_as_stored":feature_names,
        "note":"f000-f155 的顺序为每个 NPZ 的 scaled_vector 顺序。selected_indices 和模型哈希见模型输入向量；请按模型版本核对，不能假定不同版本可直接混用。"})

    daily=[]
    for day in sorted({c["collection_date_bj"] for c in cases_list}):
        cc=[c for c in cases_list if c["collection_date_bj"]==day]
        daily.append({"采集日期_北京时间":day,"问诊会话例数":len(cc),"新增批次例数":sum("B02_新增采集" in c["source_batches"] for c in cc),
                      "完成量表例数":sum(c["assessment_completed"] for c in cc),"量表结果条数":sum(c["scale_result_count"] for c in cc),
                      "五模态均有输入例数":sum(c["all_five_modalities_available"] for c in cc),
                      **{m+"_输入数":sum(c[m+"_input_count"] for c in cc) for m in MODES}})
    overview={"generated_at_bj":datetime.now(TZ).isoformat(),"timezone":"Asia/Shanghai",
              "case_count":len(cases_list),"old_case_count":sum("B01_历史导出" in c["source_batches"] for c in cases_list),
              "new_case_count":sum("B02_新增采集" in c["source_batches"] for c in cases_list),
              "completed_assessment_case_count":sum(c["assessment_completed"] for c in cases_list),
              "scale_result_count":len(labels),"scale_types":dict(Counter(r["scale_slug"] for r in labels)),
              "all_five_case_count":sum(c["all_five_modalities_available"] for c in cases_list),
              "modality_input_counts":{m:len(mode_samples[m]) for m in MODES},
              "modality_case_counts":{m:sum(c[m+"_input_count"]>0 for c in cases_list) for m in MODES},
              "raw_unique_objects":len(object_rows),"raw_unique_bytes":sum(r["bytes"] for r in object_rows),
              "eeg_sample_seconds":sum(s.get("sample_seconds",0) for s in mode_samples["eeg"]),
              "eeg_model_vector_count":len(eeg_flat),"missing_object_uris":len(missing_refs),
              "unassociated_records":len(orphans),"unassociated_objects":sum(r["case_id"] is None for r in object_rows),
              "duplicate_capture_uri_groups":len(duplicate_refs),"verified_distinct_person_count":None,
              "daily":daily,"source_snapshot_times":{b["name"]:b["summary"]["database_snapshot_at_utc"] for b in batches}}
    table(output/"病例总索引",cases_list)
    table(output/"按日统计",daily)
    json_file(output/"dataset_summary.json",overview)
    write_docs(output,overview,cases_list,labels)
    workbook(output/"数据集统计总表.xlsx",{
        "数据集概览":[{"指标":k,"数值":v} for k,v in overview.items() if not isinstance(v,(dict,list))],
        "按日统计":daily,"病例总索引":cases_list,"量表结果":labels,
        "模态统计":[{"模态":m,"输入样本数":len(mode_samples[m]),"有输入的会话数":overview["modality_case_counts"][m]} for m in MODES]})
    # Every raw object appears once in the original set; modes have standalone copies.
    assert len({r["uri"] for r in object_rows})==len(assets)
    assert all((output/r["original_path"]).is_file() for r in object_rows)
    for mode,rows in mode_samples.items():
        assert all((mode_dir/MODES[mode]/r["input_path"]).is_file() for r in rows)
        if mode!="text":
            assert all(digest(mode_dir/MODES[mode]/r["input_path"])==r["sha256"] for r in rows)
    json_file(audit_dir/"核验结果.json",{"original_and_modality_sha256_verified":True,"case_primary_keys_unique":True,
              "original_objects":len(object_rows),"per_day_counts_match_total":sum(d["问诊会话例数"] for d in daily)==len(cases_list),
              "source_data_modified":False,"database_modified":False,"scale_results_preserved":len(labels)})
    checksums=[]
    for f in sorted(output.rglob("*")):
        if f.is_file():
            checksums.append({"path":str(f.relative_to(output)),"bytes":f.stat().st_size,"sha256":digest(f)})
    table(audit_dir/"全部文件_SHA256",checksums)
    print(json.dumps(overview,ensure_ascii=False),flush=True)


def write_docs(output,overview,cases,labels):
    readme=f"""# 情绪识别多模态科研数据集

版本：{overview['generated_at_bj']}（北京时间）  
统计单位：一次 encounter 问诊会话，不是已核实的独立受试者。

## 从这里开始

双击根目录 `数据集总览.html` 查看总量、每日统计和可筛选的病例索引；
`数据集统计总表.xlsx` 包含概览、按日统计、病例索引、量表结果、模态统计五张工作表。
CSV 使用 UTF-8 BOM，可用 Excel 打开；JSONL 保留嵌套原始值。

## 目录

```
01_原始总数据集/
  按日期/YYYY-MM-DD/CASE_日期_编号/
    会话信息.json
    数据库记录/              # 精确保存该会话的临床业务表行
    files/                   # NPZ、原始录音、标准 WAV、采样 JPEG
  原始文件索引.csv           # URI、SHA256、病例、日期、原始文件路径
  轮次对齐索引.csv           # case_id + turn_id 连接五个模态
02_各模态数据集/
  01_脑电_EEG/ 02_语音_Audio/ 03_文本_Text/ 04_表情_Face/ 05_姿态_Pose/
    按日期/YYYY-MM-DD/CASE_日期_编号/
    样本索引.csv             # input_path 相对此模态目录，可独立复制使用
    采集记录.jsonl           # 原始采集元信息
    模型预测_非人工标签.jsonl
    量表标签.csv             # 此模态涉及会话的量表自评结果
03_量表结果数据集/
  按日期/YYYY-MM-DD/CASE_日期_编号/
  量表分数与标签.csv         # 每个会话、每种量表一行结果
  逐题答案.csv               # 逐项选择、原始文本、时间与分值
04_来源与质量核验/
  B01_历史导出/ B02_新增采集/ # 分批数据库原始表与来源说明
  缺失原始文件.csv
  同一对象多记录引用.csv
  全部文件_SHA256.csv
```

## 本次清点

历史 {overview['old_case_count']} 例 + 新增 {overview['new_case_count']} 例 = **{overview['case_count']} 次会话**。
完成量表的会话 {overview['completed_assessment_case_count']} 次，量表结果 {overview['scale_result_count']} 条。
五模态均有至少一个输入的会话 {overview['all_five_case_count']} 次，这不代表全程连续同步采集或全部数据质量合格。
全部原始对象共 {overview['raw_unique_objects']} 个，按物理文件 URI 去重。
模型预测不是医生诊断或人工真值；量表记录保留数据库原有分数和解释，不重新计算阈值或分级。

## 日期与“例”的定义

目录按问诊会话开始日期（北京时间 Asia/Shanghai）归档。同一会话全部资料放在同一目录。
原始文件索引另外列出 acquired_at_bj / acquired_date_bj：有采集记录时采用采集时间；
未入选关键帧的 JPEG 可能没有逐张时间记录，采用会话开始时间回退，time_source 明确标记。
这种回退不能用来推断逐帧时间或精确同步。量表另有 result_date_bj，可按实际提交日期检索。
原始数据库字段保留 UTC 时区。case_id 稳定关联各模态，encounter_session_id 保留原始会话 ID。
按日期索引不能使用系统文件复制时间；复制时间不是采集时间。

新增会话共用账号，account_key 只表示来源批次内的账号，不能作为可靠受试者编号。
数据库曾被清空重建，跨批次账号也不能直接认定同一个人；person_id_verified 均为 false。
本数据集没有声称有 {overview['case_count']} 名独立患者，也未擅自生成受试者级训练/验证/测试划分。

## AI 数据集的使用边界

五个模态均包含各自独立的输入文件、样本索引、模型预测和可用的会话级量表标签。
各模态目录中的 input_path 是相对此模态目录的路径，不依赖项目、MinIO 或原始总数据集。
先通过 case_id 连接量表，再按研究任务决定是否使用量表分数作为会话级监督信号。
不把模型自身 primary_label 当作人工标签，也不把一次量表分级直接当作每个脑电窗口或图片的情绪真值。
需要逐帧表情类别、人体关键点等监督任务时，还须另行核验或标注。
临床诊断真值未提供，is_clinician_diagnosis 为 false。

脑电：原始 NPZ 无损保留，另附波形 CSV、模型输入向量 JSONL 和有效 156 维标准化输入表。
模型输入顺序、selected_indices、model_sha256 都保留；不同版本的输入需核对后使用。
样本不足的窗口仍保留，has_model_vector_156=false 的窗口不会放入 156 维表。
eeg_sample_seconds 是样本数/采样率累加，不能等同于连续录制时长。

语音：原始 WebM 与标准化 WAV 分开保留；两者可能是同一次回答的不同编码，并非两例。
文本：从问诊回答、量表答案、音频转写提取，优先保留问诊/量表原始记录，去除已匹配音频的重复 ASR 副本。
不同问题的相同答案不会被当作同一例。结构化总表中原始文本仍完整保留。
表情、姿态：来自同一套摄像头 JPEG，全画面采样图片分别复制到两个独立数据集中。
图片数量不得相加当作两倍独立拍摄数据；没有完整 MP4 或逐帧连续视频。
既有推理结果多为窗口/轮次汇总，不能假定每张非关键帧都有独立推理标注。

## 质量和来源

缺失对象 URI：{overview['missing_object_uris']}；未关联记录：{overview['unassociated_records']}；
未关联文件：{overview['unassociated_objects']}；多个采集记录共用同一个 URI 的组数：{overview['duplicate_capture_uri_groups']}。
同 URI 只保存一个实际文件，全部采集记录仍在数据库快照中，不将多次引用虚报为多个原始文件。
如同一个路径曾被覆盖，当前导出无法恢复其过去版本，也不会伪造缺失窗口。
来源 B01 是此前保留下来的桌面导出：部分辅助表当时没有导出，现已清库，不能恢复。
来源 B02 是此次只读一致性数据库快照，时间见 dataset_summary.json；MinIO 对象随后逐个读取。
没有读取账号密码；既有文本和声音/图片仍可能识别个人，本次整理不等同于完成匿名化。

所有可用对象先验证来源 SHA256，再验证原始总数据集和独立模态副本。
全部文件_SHA256 清单不包含自身；复制或下载后可再次核验。
本次只导出和整理，不删除或修改项目数据库、MinIO，也不覆盖旧导出。
"""
    (output/"README_数据集说明.md").write_text(readme,encoding="utf-8")
    for mode,folder in MODES.items():
        note=f"# {folder} 数据集\n\n输入 {overview['modality_input_counts'][mode]} 个，涉及 {overview['modality_case_counts'][mode]} 次问诊会话。\n\n"
        note+="从 样本索引.csv 开始；input_path 相对此目录。case_id 连接 量表标签.csv，标签为会话级量表结果。\n模型预测_非人工标签 是历史模型输出，不是人工标注。原始采集表和 JSONL 保留完整结构。\n"
        if mode in ("face","pose"):
            note+="\n图片与另一视觉模态同源；不是逐帧人工表情/关键点标注，也不是连续视频。\n"
        if mode=="eeg":
            note+="\nNPZ 保留所有数组。waveform_csv_path 是波形表；模型输入_标准化156维.csv 只收录存在有效维数向量的文件，仍需结合质量信息筛选。\n"
        (output/"02_各模态数据集"/folder/"README.md").write_text(note,encoding="utf-8")
    fields=[
        {"field":"case_id","含义":"基于开始日期和原始 encounter ID 的稳定会话编号；不是独立受试者编号"},
        {"field":"collection_date_bj / case_date_bj","含义":"问诊开始日期，北京时间；用于目录归档"},
        {"field":"acquired_at_bj / time_source","含义":"实际采集记录时间或明确标记的会话时间回退"},
        {"field":"input_path","含义":"相对此模态数据集目录的输入文件路径"},
        {"field":"sha256","含义":"文件字节级 SHA256，用于检查完整性"},
        {"field":"turn_id","含义":"轮次关联 ID；须与 case_id 一同使用"},
        {"field":"sample_id","含义":"原始采集记录 ID，可关联推理；不能与物理文件数量混算"},
        {"field":"asset_id","含义":"按对象 URI 或文本记录生成的稳定输入样本编号"},
        {"field":"primary_label / primary_score","含义":"历史模型预测类别和分数，不是人工真值"},
        {"field":"raw_score / derived_score","含义":"数据库已存量表原始分/衍生分，不进行重新分级"},
        {"field":"has_model_vector_156","含义":"文件含 156 维 aggregate_vector 与 scaled_vector；不等于所有质量条件合格"},
        {"field":"person_id_verified","含义":"是否已核实独立受试者身份；本次均为 false"}]
    table(output/"字段字典",fields)
    loader='''# 在数据集根目录运行：python3 读取示例.py
import csv
from pathlib import Path
root=Path(__file__).resolve().parent
with (root/'病例总索引.csv').open(encoding='utf-8-sig',newline='') as f:
    cases=list(csv.DictReader(f))
print('会话数：',len(cases))
# 查看某一天：修改此日期即可。
print('2026-11-19 会话数：',sum(c['collection_date_bj']=='2026-11-19' for c in cases))
mode=root/'02_各模态数据集'/'01_脑电_EEG'
with (mode/'样本索引.csv').open(encoding='utf-8-sig',newline='') as f:
    samples=list(csv.DictReader(f))
print('脑电文件数：',len(samples))
if samples:
    print('第一份脑电：',mode/samples[0]['input_path'])
    # 需要 numpy：data = numpy.load(mode/samples[0]['input_path'], allow_pickle=False)
    # 波形 data['samples']；通道 data['channel_names']；时间 data['sample_timestamps_ms']。
'''
    (output/"读取示例.py").write_text(loader,encoding="utf-8")
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>情绪识别 · 科研数据集</title>
<style>:root{--ink:#173944;--muted:#69808a;--green:#187b72;--line:#d9e4e6}*{box-sizing:border-box}body{margin:0;background:#f1f5f5;color:var(--ink);font:15px/1.6 system-ui,"Noto Sans CJK SC",sans-serif}header{background:#123640;color:white;padding:44px max(5vw,24px) 35px}header small{color:#a9d1ce;letter-spacing:3px}h1{font-size:36px;margin:10px 0}header p{color:#c6d9dd;max-width:930px}main{max-width:1320px;margin:auto;padding:28px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.metric,section,.dataset{background:white;border:1px solid var(--line);border-radius:14px}.metric{padding:20px}.metric b{display:block;font-size:36px;color:var(--green)}.metric span{color:var(--muted)}section{padding:25px;margin-top:24px}h2{font-size:21px;margin:0 0 14px}h3{margin:0 0 8px}.hint{color:var(--muted);font-size:13px}.datasets{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.dataset{padding:18px}.dataset b{color:var(--green)}a{color:var(--green);text-decoration:none}a:hover{text-decoration:underline}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:13px}th{text-align:left;background:#eff5f5;color:#526b75;font-weight:600}th,td{padding:12px 13px;border-bottom:1px solid #e6eded}tbody tr:hover{background:#f7fbfa}.pill{display:inline-block;border-radius:20px;padding:2px 9px;background:#e6f3ef;color:#167065;font-size:12px}.warn{background:#fff4dd;color:#886626}select,input{font:inherit;border:1px solid var(--line);padding:9px 12px;border-radius:8px;background:white;margin:0 8px 12px 0}.notice{border-left:4px solid #c69b4b;background:#fff9eb;padding:15px 18px;margin-top:24px;border-radius:6px}footer{padding:24px 0;color:var(--muted);font-size:12px}.legend{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px}.bar{height:5px;background:#e4eeec;border-radius:4px;margin-top:12px}.bar i{display:block;height:5px;background:var(--green);border-radius:4px}@media(max-width:800px){.metrics,.datasets{grid-template-columns:repeat(2,1fr)}h1{font-size:27px}main{padding:16px}}@media print{body{background:white}header{padding:20px;color:#123640;background:white}.notice{break-inside:avoid}select,input{display:none}section{break-inside:avoid}}</style>
<header><small>RESEARCH DATA COLLECTION · V2026.11</small><h1>情绪识别 · 多模态科研数据集</h1><p>原始总数据集 / 五个模态输入数据集 / 量表结果集。旧导出与新增采集统一归档，保留病例、轮次、来源与完整性索引。</p><div id="range"></div></header>
<main><div class="metrics" id="metrics"></div><div class="notice">统计口径：一例指一次问诊会话。共用账号不能证明独立受试者人数。量表结果与模型预测分别存放；模型预测不作为人工真值。</div>
<section><h2>数据集入口</h2><div class="datasets" id="datasets"></div><p class="hint">各模态均有独立输入文件和相对路径索引。表情与姿态图片同源；文件数不能相加当作独立拍摄量。</p></section>
<section><h2>按日采集统计</h2><div class="scroll"><table><thead><tr><th>北京时间</th><th>会话</th><th>新增</th><th>完成量表</th><th>五模态有输入</th><th>脑电文件</th><th>音频文件</th><th>文本输入</th><th>采样图片</th></tr></thead><tbody id="daily"></tbody></table></div></section>
<section><h2>病例索引</h2><select id="date"><option value="">全部采集日期</option></select><select id="filter"><option value="all">全部会话</option><option value="complete">已完成量表</option><option value="five">五模态均有输入</option><option value="new">仅新增批次</option></select><input id="search" placeholder="按病例编号查找"><span class="hint" id="shown"></span>
<div class="scroll"><table><thead><tr><th>日期 / 病例编号</th><th>来源</th><th>脑电</th><th>语音</th><th>文本</th><th>表情</th><th>姿态</th><th>量表</th><th>原始资料</th></tr></thead><tbody id="cases"></tbody></table></div></section>
<section><h2>质量与可追溯性</h2><div id="quality"></div><p class="hint">“有输入”只表示存在该模态样本，不表示全程同步或质量已全部合格。未入选关键帧的图片可能仅能确定所属会话日期。原始数据与模态副本均核对 SHA256。</p><div class="legend"><a href="数据集统计总表.xlsx">Excel 统计总表 ↗</a><a href="病例总索引.csv">病例 CSV ↗</a><a href="README_数据集说明.md">数据集说明 ↗</a><a href="04_来源与质量核验/核验结果.json">核验结果 ↗</a></div></section>
<footer id="footer"></footer></main><script>const data=__DATA__, cases=data.cases, s=data.summary;
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
document.getElementById('range').textContent=s.daily[0]['采集日期_北京时间']+' — '+s.daily.at(-1)['采集日期_北京时间']+' · Asia/Shanghai';
document.getElementById('metrics').innerHTML=[[s.case_count,'问诊会话 · 历史 '+s.old_case_count+' + 新增 '+s.new_case_count],[s.completed_assessment_case_count,'完成量表的会话'],[s.scale_result_count,'量表结果 · 多种量表'],[s.all_five_case_count,'五模态均有输入的会话']].map(([v,t])=>'<div class="metric"><b>'+v+'</b><span>'+esc(t)+'</span></div>').join('');
const modes=[['eeg','脑电 EEG','01_脑电_EEG','窗口文件'],['audio','语音 Audio','02_语音_Audio','编码文件'],['text','文本 Text','03_文本_Text','文本输入'],['face','表情 Face','04_表情_Face','采样图片'],['pose','姿态 Pose','05_姿态_Pose','同源图片']];
document.getElementById('datasets').innerHTML='<div class="dataset"><h3><a href="01_原始总数据集/">原始总数据集 ↗</a></h3><b>'+s.raw_unique_objects.toLocaleString()+'</b> 个原始对象<p class="hint">保留原始文件和临床业务表，按日期 / 会话组织。</p></div>'+modes.map(([m,n,f,u])=>'<div class="dataset"><h3><a href="02_各模态数据集/'+f+'/">'+n+' ↗</a></h3><b>'+s.modality_input_counts[m].toLocaleString()+'</b> '+u+' · '+s.modality_case_counts[m]+' 次会话<div class="bar"><i style="width:'+(s.modality_case_counts[m]/s.case_count*100)+'%"></i></div><p class="hint">输入文件 / 样本索引 / 历史预测 / 量表标签</p></div>').join('')+'<div class="dataset"><h3><a href="03_量表结果数据集/">量表结果集 ↗</a></h3><b>'+s.scale_result_count+'</b> 条结果<p class="hint">'+Object.entries(s.scale_types).map(([k,v])=>esc(k)+' × '+v).join(' · ')+'</p></div>';
document.getElementById('daily').innerHTML=s.daily.map(d=>'<tr>'+['采集日期_北京时间','问诊会话例数','新增批次例数','完成量表例数','五模态均有输入例数','eeg_输入数','audio_输入数','text_输入数','face_输入数'].map(k=>'<td>'+esc(d[k])+'</td>').join('')+'</tr>').join('');
document.getElementById('date').innerHTML+=s.daily.map(d=>'<option>'+d['采集日期_北京时间']+'</option>').join('');
function render(){const day=document.getElementById('date').value,f=document.getElementById('filter').value,q=document.getElementById('search').value.toLowerCase();const rows=cases.filter(c=>(!day||c.collection_date_bj===day)&&(!q||c.case_id.toLowerCase().includes(q))&&(f==='all'||f==='complete'&&c.assessment_completed||f==='five'&&c.all_five_modalities_available||f==='new'&&c.source_batches.includes('B02_新增采集')));document.getElementById('shown').textContent=rows.length+' 次会话';document.getElementById('cases').innerHTML=rows.map(c=>'<tr><td>'+c.collection_date_bj+'<br><small>'+esc(c.case_id)+'</small></td><td>'+ (c.source_batches.includes('B02_新增采集')?'新增':'历史')+'</td>'+modes.map(([m])=>'<td>'+c[m+'_input_count']+'</td>').join('')+'<td><span class="pill '+(c.assessment_completed?'':'warn')+'">'+(c.assessment_completed?'已完成':'未完成 / 未开始')+'</span><br><small>'+esc(c.scale_slugs.join(' / '))+'</small></td><td><a href="'+esc(c.raw_case_path)+'/">查看 ↗</a></td></tr>').join('')}
for(const id of ['date','filter','search'])document.getElementById(id).addEventListener('input',render);render();
document.getElementById('quality').textContent='缺失对象 '+s.missing_object_uris+' · 未关联文件 '+s.unassociated_objects+' · 未关联记录 '+s.unassociated_records+' · 同一对象多记录引用 '+s.duplicate_capture_uri_groups+' 组 · 可用 156 维脑电向量 '+s.eeg_model_vector_count+' 份';
document.getElementById('footer').textContent='生成于 '+s.generated_at_bj+' · 本地静态报告，无外部网络依赖。未确认独立受试者人数，未自动划分训练/验证/测试集。';
</script></html>'''
    payload=json.dumps({"summary":overview,"cases":cases},ensure_ascii=False).replace("<","\\u003c")
    (output/"数据集总览.html").write_text(page.replace("__DATA__",payload),encoding="utf-8")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old",type=Path,required=True)
    parser.add_argument("--new",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    build(args.old.resolve(),args.new.resolve(),args.output.resolve())
