"""Session-scoped persistent EEG windows and on-demand explanation tasks."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import uuid

from sqlalchemy import and_, case, func, or_, select

from app.config import get_settings
from app.database import get_db_session
from app.models import MultimodalCapture, MultimodalEegExplanation, MultimodalInferenceResult, MultimodalSession
from app.services.eeg_explanation_math import MAPPING_VERSION, OUTPUT_KIND, PIPELINE_VERSION, digest_json
class EegExplanationError(Exception):
    def __init__(self, message: str, code: int, status_code: int):
        self.message, self.code, self.status_code = message, code, status_code
        super().__init__(message)


def now_utc():
    return datetime.now(timezone.utc)


def iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


@lru_cache(maxsize=8)
def _hash_file(path: str, mtime_ns: int, size: int) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_hash(path: Path) -> str | None:
    try:
        stat = path.stat()
        return _hash_file(str(path), stat.st_mtime_ns, stat.st_size)
    except OSError:
        return None


def current_configuration(target_class: int) -> tuple[dict, str | None]:
    settings = get_settings()
    background = settings['eeg_explanation_background_path']
    manifest_path = background.with_suffix('.json')
    model_hash = file_hash(settings['eeg_model_path'])
    background_hash = file_hash(background)
    manifest_hash = file_hash(manifest_path)
    manifest = {}
    error = None
    if not model_hash:
        error = 'model_missing'
    elif not background_hash or not manifest_hash:
        error = 'background_missing'
    else:
        try:
            manifest = json.loads(manifest_path.read_text())
            limit = float(manifest['color_limit'])
            floor = float(manifest.get('influence_floor', 1e-8))
            if (manifest['model_sha256'] != model_hash
                    or manifest['background_sha256'] != background_hash
                    or manifest['pipeline_version'] != PIPELINE_VERSION
                    or manifest['input_kind'] != 'selected_scaled'
                    or not isinstance(manifest['feature_names'], list)
                    or not manifest['background_id']
                    or not 0 < limit < float('inf') or not 0 <= floor < float('inf')):
                raise ValueError('background_manifest_mismatch')
            manifest['color_limit'] = limit
            manifest['influence_floor'] = floor
        except (OSError, ValueError, KeyError, TypeError):
            error = 'background_manifest_mismatch'
            manifest = {}
    if not error and not settings['eeg_explanations_enabled']:
        error = 'worker_disabled'
    config = {'model_sha256': model_hash, 'pipeline_version': PIPELINE_VERSION,
              'target_class': target_class, 'output_kind': OUTPUT_KIND,
              'background_id': manifest.get('background_id'), 'background_sha256': background_hash,
              'background_manifest_sha256': manifest_hash, 'mapping_version': MAPPING_VERSION,
              'explainer_version': 'shap-kernel-0.46.0', 'seed': 42,
              'nsamples': settings['eeg_explanation_nsamples'],
              'max_background': settings['eeg_explanation_max_background'],
              'influence_floor': manifest.get('influence_floor', 1e-8),
              'color_limit': manifest.get('color_limit'),
              'feature_names_hash': digest_json(manifest.get('feature_names', [])),
              'availability': error}
    return config, error


def configuration_hash(config):
    # Availability is operational state, not a new definition of model attribution.
    return digest_json({k: v for k, v in config.items() if k != 'availability'})


def _session(db, session_id, user_id, *, lock=False):
    query = select(MultimodalSession).where(MultimodalSession.id == session_id)
    if lock:
        query = query.with_for_update()
    session = db.scalar(query)
    if session is None:
        raise EegExplanationError('multimodal session not found', 4041, 404)
    if not user_id or not session.user_id or session.user_id != user_id:
        raise EegExplanationError('multimodal session access denied', 4031, 403)
    return session


def _encode_cursor(row, config_hash):
    return base64.urlsafe_b64encode(json.dumps([iso(row.created_at), row.id, config_hash]).encode()).decode()


def _decode_cursor(cursor, config_hash):
    if not cursor:
        return None
    try:
        if len(cursor) > 1024:
            raise ValueError()
        time, identity, configuration = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        if configuration != config_hash or not isinstance(identity, str):
            raise ValueError()
        timestamp = datetime.fromisoformat(time)
        if timestamp.tzinfo is None:
            raise ValueError()
        return timestamp, identity
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise EegExplanationError('invalid or outdated EEG history cursor', 4221, 422) from exc


def _windows(db, session_id, cursor, limit, config_hash='windows-v1'):
    query = select(MultimodalCapture, MultimodalInferenceResult).outerjoin(
        MultimodalInferenceResult,
        and_(MultimodalInferenceResult.sample_id == MultimodalCapture.id,
             MultimodalInferenceResult.modality == 'eeg'),
    ).where(MultimodalCapture.session_id == session_id, MultimodalCapture.modality == 'eeg',
            MultimodalCapture.capture_kind == 'window')
    decoded = _decode_cursor(cursor, config_hash)
    if decoded:
        at, identity = decoded
        query = query.where(or_(MultimodalCapture.created_at < at,
                                and_(MultimodalCapture.created_at == at, MultimodalCapture.id < identity)))
    records = list(db.execute(query.order_by(MultimodalCapture.created_at.desc(), MultimodalCapture.id.desc()).limit(limit + 1)))
    next_cursor = _encode_cursor(records[limit - 1][0], config_hash) if len(records) > limit else None
    return records[:limit], next_cursor


def _window(capture, inference):
    data = inference.inference_payload if inference else {}
    return {'sample_id': capture.id, 'inference_id': inference.id if inference else None,
            'multimodal_session_id': capture.session_id, 'flow_run_id': capture.flow_run_id,
            'turn_id': capture.turn_id, 'window_index': capture.sample_index,
            'sample_started_at': iso(capture.sample_started_at), 'sample_ended_at': iso(capture.sample_ended_at),
            'prediction_status': data.get('status', (capture.capture_payload or {}).get('prediction_status', 'insufficient_frames')),
            'primary_label': data.get('primary_label'), 'primary_score': data.get('primary_score'),
            'score_kind': data.get('score_kind', 'legacy_model_score'),
            'model_version': data.get('model_version'), 'model_sha256': data.get('model_sha256'),
            'quality_flags': data.get('quality_flags', (capture.capture_payload or {}).get('quality_flags', {})),
            'input_hash': data.get('_explanation_input', {}).get('input_hash')}


def serialize_explanation(row, inference):
    payload = inference.inference_payload
    return {'explanation_id': row.id, 'sample_id': row.sample_id, 'inference_id': row.inference_id,
            'multimodal_session_id': row.session_id, 'status': row.status,
            'config': row.config_payload, 'config_hash': row.config_hash,
            'input_hash': payload.get('_explanation_input', {}).get('input_hash'),
            'sample_started_at': payload.get('sample_started_at'), 'sample_ended_at': payload.get('sample_ended_at'),
            'values': row.result_payload if row.status == 'ready' else None,
            'error_code': row.error_code, 'created_at': iso(row.created_at),
            'computed_at': iso(row.finished_at), 'duration_ms': row.duration_ms, 'stale_reason': None}


def list_windows(session_id, user_id, *, cursor=None, limit=20):
    with get_db_session() as db:
        _session(db, session_id, user_id)
        rows, next_cursor = _windows(db, session_id, cursor, limit)
        return {'items': [_window(*r) for r in rows], 'next_cursor': next_cursor}


def request_explanation(session_id, user_id, *, inference_id, target_class):
    config, error = current_configuration(target_class)
    with get_db_session() as db:
        # Serialize duplicate submissions even when they arrive via different API processes.
        _session(db, session_id, user_id, lock=True)
        inference = db.scalar(select(MultimodalInferenceResult).where(
            MultimodalInferenceResult.id == inference_id,
            MultimodalInferenceResult.session_id == session_id,
            MultimodalInferenceResult.modality == 'eeg'))
        if inference is None or not inference.sample_id:
            raise EegExplanationError('EEG prediction not found', 4041, 404)
        capture = db.get(MultimodalCapture, inference.sample_id)
        if not capture or capture.session_id != session_id:
            raise EegExplanationError('EEG sample not found', 4041, 404)
        snapshot = inference.inference_payload.get('_explanation_input', {})
        if not snapshot:
            error = 'input_snapshot_missing'
        elif len(snapshot.get('scaled_vector', [])) != 110:
            error = 'unsupported_model_input'
        elif snapshot.get('model_sha256') != config['model_sha256']:
            error = 'model_version_unavailable'
        elif not error and digest_json(snapshot.get('feature_names')) != config['feature_names_hash']:
            error = 'background_feature_mismatch'
        config = {**config, 'availability': error}
        config_hash = configuration_hash(config)
        canonical_key = digest_json([inference.id, snapshot.get('input_hash'), config_hash])
        row = db.scalar(select(MultimodalEegExplanation).where(MultimodalEegExplanation.cache_key == canonical_key))
        if row is not None:
            return serialize_explanation(row, inference)
        if not error:
            pending = db.scalar(select(func.count()).select_from(MultimodalEegExplanation).where(
                MultimodalEegExplanation.session_id == session_id,
                MultimodalEegExplanation.status.in_(['queued', 'running'])))
            if pending >= get_settings()['eeg_explanation_max_pending']:
                error = 'queue_busy'
        key = digest_json([canonical_key, error]) if error else canonical_key
        row = db.scalar(select(MultimodalEegExplanation).where(MultimodalEegExplanation.cache_key == key))
        if row is None:
            row = MultimodalEegExplanation(id=str(uuid.uuid4()), session_id=session_id,
                sample_id=inference.sample_id, inference_id=inference.id, cache_key=key,
                config_hash=config_hash, config_payload=config, target_class=target_class,
                status='unavailable' if error else 'queued', error_code=error,
                attempts=0, created_at=now_utc())
            db.add(row)
            db.flush()
        return serialize_explanation(row, inference)


def get_explanation(session_id, user_id, explanation_id):
    with get_db_session() as db:
        _session(db, session_id, user_id)
        row = db.scalar(select(MultimodalEegExplanation).where(
            MultimodalEegExplanation.id == explanation_id, MultimodalEegExplanation.session_id == session_id))
        if row is None:
            raise EegExplanationError('EEG explanation not found', 4041, 404)
        inference = db.get(MultimodalInferenceResult, row.inference_id)
        return serialize_explanation(row, inference)


def list_explanations(session_id, user_id, *, target_class, cursor=None, limit=20):
    config, error = current_configuration(target_class)
    config_hash = configuration_hash(config)
    with get_db_session() as db:
        _session(db, session_id, user_id)
        windows, next_cursor = _windows(db, session_id, cursor, limit, config_hash)
        ids = [i.id for _, i in windows if i]
        explanations = {r.inference_id: r for r in db.scalars(select(MultimodalEegExplanation).where(
            MultimodalEegExplanation.session_id == session_id,
            MultimodalEegExplanation.config_hash == config_hash,
            MultimodalEegExplanation.inference_id.in_(ids)).order_by(
                case((MultimodalEegExplanation.status == 'ready', 1), else_=0),
                MultimodalEegExplanation.created_at, MultimodalEegExplanation.id))} if ids else {}
        items = []
        for capture, inference in windows:
            row = explanations.get(inference.id) if inference else None
            item = _window(capture, inference)
            item.update({'explanation_id': row.id if row else None,
                         'status': row.status if row else 'not_requested',
                         'error_code': row.error_code if row else error,
                         'group_net': row.result_payload['group_net'] if row and row.status == 'ready' else None})
            items.append(item)
        color = config['color_limit']
        return {'config': config, 'config_hash': config_hash, 'items': items, 'next_cursor': next_cursor,
                'availability_error': error, 'color_scale': {'min': -color if color else None, 'max': color,
                    'unit': OUTPUT_KIND, 'policy_id': config.get('background_manifest_sha256')}}
