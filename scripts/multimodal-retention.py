"""Shared date selection and explicit, transaction-protected clinical data cleanup.

Loaded by export-multimodal-data.py inside the running container. No account,
authentication, or migration table is read or modified here.
"""
from datetime import datetime, timezone
import json

EXTRA_TABLES = ["risk_evaluations", "risk_triggers", "intervention_sessions", "intervention_events"]
LINKS = {
    "consultation_sessions": {"encounter_session_id": "encounter_sessions", "multimodal_session_id": "multimodal_sessions"},
    "consultation_turns": {"session_id": "consultation_sessions", "encounter_session_id": "encounter_sessions"},
    "assessment_sessions": {"encounter_session_id": "encounter_sessions", "source_consultation_flow_run_id": "consultation_sessions", "multimodal_session_id": "multimodal_sessions"},
    "assessment_answers": {"session_id": "assessment_sessions", "multimodal_session_id": "multimodal_sessions"},
    "assessment_results": {"session_id": "assessment_sessions"},
    "multimodal_sessions": {"encounter_session_id": "encounter_sessions"},
    "multimodal_audio_turns": {"multimodal_session_id": "multimodal_sessions"},
    "multimodal_captures": {"session_id": "multimodal_sessions"},
    "multimodal_inference_results": {"session_id": "multimodal_sessions", "sample_id": "multimodal_captures"},
    "multimodal_visual_frames": {"session_id": "multimodal_sessions"},
    "multimodal_turn_bundles": {"session_id": "multimodal_sessions"},
    "multimodal_eeg_explanations": {"session_id": "multimodal_sessions", "sample_id": "multimodal_captures", "inference_id": "multimodal_inference_results"},
    "risk_evaluations": {"encounter_session_id": "encounter_sessions", "consultation_session_id": "consultation_sessions", "assessment_session_id": "assessment_sessions", "multimodal_session_id": "multimodal_sessions"},
    "risk_triggers": {"evaluation_id": "risk_evaluations"},
    "intervention_sessions": {"encounter_session_id": "encounter_sessions", "consultation_session_id": "consultation_sessions", "assessment_session_id": "assessment_sessions", "risk_evaluation_id": "risk_evaluations"},
    "intervention_events": {"session_id": "intervention_sessions"},
}
DELETE_ORDER = ["multimodal_eeg_explanations", "multimodal_inference_results", "multimodal_captures",
                "multimodal_audio_turns", "multimodal_visual_frames", "multimodal_turn_bundles",
                "risk_triggers", "intervention_events", "intervention_sessions", "risk_evaluations",
                "assessment_results", "assessment_answers", "assessment_sessions", "consultation_turns",
                "consultation_sessions", "multimodal_sessions", "encounter_sessions"]
SESSION_TABLES = {"encounter_sessions", "consultation_sessions", "assessment_sessions", "multimodal_sessions", "intervention_sessions"}


def timestamp(row, table):
    # Aggregates may be updated as a turn continues across the boundary.
    if table in ("multimodal_turn_bundles", "risk_evaluations"):
        return row.get("updated_at") or row["created_at"]
    if table in SESSION_TABLES:
        return row.get("started_at") or row["created_at"]
    return (row.get("sample_ended_at") or row.get("captured_at") or
            row.get("response_completed_at") or row.get("completed_at") or row["created_at"])


def select_since(snapshot, since, excluded_session=None):
    cutoff = datetime.fromisoformat(since)
    if cutoff.tzinfo is None:
        raise ValueError("--since 必须包含时区，例如 2026-11-12T14:00:00+08:00")
    indexed = {t: {r["id"]: r for r in rows} for t, rows in snapshot.items()}
    excluded = {t: set() for t in snapshot}
    if excluded_session:
        excluded["multimodal_sessions"].add(excluded_session)
        session = indexed["multimodal_sessions"].get(excluded_session)
        if session:
            if session.get("encounter_session_id"):
                excluded["encounter_sessions"].add(session["encounter_session_id"])
            if session.get("flow_type") in ("consultation", "assessment"):
                excluded[session["flow_type"] + "_sessions"].add(session["flow_run_id"])
        changed = True
        while changed:
            changed = False
            for table, rows in snapshot.items():
                for row in rows:
                    if row["id"] in excluded[table]:
                        continue
                    if any(row.get(col) in excluded.get(target, set()) for col, target in LINKS.get(table, {}).items()):
                        excluded[table].add(row["id"])
                        changed = True
    keep = {t: {r["id"] for r in rows if timestamp(r, t) >= cutoff and r["id"] not in excluded[t]}
            for t, rows in snapshot.items()}
    direct = {t: set(ids) for t, ids in keep.items()}
    changed = True
    while changed:
        changed = False
        for table, ids in keep.items():
            for rid in tuple(ids):
                row = indexed[table][rid]
                links = dict(LINKS.get(table, {}))
                if row.get("flow_type") in ("consultation", "assessment"):
                    links["flow_run_id"] = row["flow_type"] + "_sessions"
                if row.get("origin_flow_type") in ("consultation", "assessment"):
                    links["flow_run_id"] = row["origin_flow_type"] + "_sessions"
                for column, target in links.items():
                    value = row.get(column)
                    if value in excluded.get(target, set()):
                        raise RuntimeError(f"保留记录引用了被整场排除的会话：{table}.{column}")
                    if value in indexed.get(target, {}) and value not in keep[target]:
                        keep[target].add(value)
                        changed = True
    filtered = {t: [r for r in rows if r["id"] in keep[t]] for t, rows in snapshot.items()}
    plan = {
        "since_inclusive": cutoff.isoformat(), "since_utc": cutoff.astimezone(timezone.utc).isoformat(),
        "excluded_multimodal_session_id": excluded_session,
        "time_rule": "采集/回答结束时间优先，缺省使用记录创建时间；跨界窗口整体保留；跨界会话仅保留必要上下文",
        "tables": {t: {"total": len(snapshot[t]), "keep": len(keep[t]), "delete": len(snapshot[t])-len(keep[t]),
                        "context_only_ids": sorted(keep[t] - direct[t])} for t in snapshot},
    }
    return filtered, plan


def retained_uris(snapshot, collect_uris):
    # Include actual capture/inference links, not stale live-state caches on parents.
    uris = set()
    for table, rows in snapshot.items():
        if table not in SESSION_TABLES:
            uris.update(collect_uris(rows))
    return uris


def cleanup(since, collect_uris, report_path, tables, excluded_session=None):
    from sqlalchemy import text, bindparam
    from app.database import get_engine
    from app.services.object_storage import get_object_storage_client
    from pathlib import Path
    cutoff = datetime.fromisoformat(since)
    client = get_object_storage_client()
    candidates = []
    for bucket in client.list_buckets():
        for obj in client.list_objects(bucket.name, recursive=True):
            if obj.last_modified < cutoff or (excluded_session and excluded_session in obj.object_name):
                candidates.append((bucket.name, obj.object_name, obj.etag))
    with get_engine().begin() as conn:
        conn.execute(text("SET LOCAL lock_timeout = '5s'"))
        conn.execute(text("LOCK TABLE " + ",".join('"'+t+'"' for t in tables) + " IN SHARE ROW EXCLUSIVE MODE"))
        snapshot = {t: [dict(r) for r in conn.execute(text(f'SELECT * FROM "{t}"')).mappings()] for t in tables}
        filtered, plan = select_since(snapshot, since, excluded_session)
        # Audio paths contain flow IDs rather than multimodal IDs.
        excluded_row = next((r for r in snapshot["multimodal_sessions"] if r["id"] == excluded_session), None)
        if excluded_row:
            flow_id = excluded_row["flow_run_id"]
            existing = {(b, k) for b, k, _ in candidates}
            for bucket in client.list_buckets():
                for obj in client.list_objects(bucket.name, prefix=f"consultation/{flow_id}/", recursive=True):
                    if (bucket.name, obj.object_name) not in existing:
                        candidates.append((bucket.name, obj.object_name, obj.etag))
        protected = retained_uris(filtered, collect_uris)
        # Fingerprint the retained data to verify no retained row was cascaded away.
        expected = {t: {r["id"] for r in rows} for t, rows in filtered.items()}
        deleted = {}
        for table in DELETE_ORDER:
            old_ids = [r["id"] for r in snapshot[table] if r["id"] not in expected[table]]
            if old_ids:
                stmt = text(f'DELETE FROM "{table}" WHERE id IN :ids').bindparams(bindparam("ids", expanding=True))
                deleted[table] = conn.execute(stmt, {"ids": old_ids}).rowcount
            else:
                deleted[table] = 0
        for table in tables:
            actual = set(conn.execute(text(f'SELECT id FROM "{table}"')).scalars())
            if actual != expected[table]:
                raise RuntimeError(f"保留记录核对失败，事务回滚：{table}")
    removed = []
    protected_old = []
    for bucket, key, etag in candidates:
        uri = f"s3://{bucket}/{key}"
        if uri in protected:
            protected_old.append(uri)
            continue
        current = client.stat_object(bucket, key)
        explicitly_excluded = bool(excluded_session and excluded_session in key) or bool(excluded_row and excluded_row["flow_run_id"] in key)
        if current.etag != etag or (current.last_modified >= cutoff and not explicitly_excluded):
            raise RuntimeError(f"文件在清理期间被更新，已保留：{uri}")
        client.remove_object(bucket, key)
        removed.append(uri)
    report = {"selection": plan, "deleted_rows": deleted, "deleted_objects": removed,
              "protected_cross_boundary_objects": protected_old,
              "completed_at_utc": datetime.now(timezone.utc).isoformat()}
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"deleted_rows": deleted, "deleted_object_count": len(removed),
                      "protected_cross_boundary_object_count": len(protected_old)}, ensure_ascii=False))
