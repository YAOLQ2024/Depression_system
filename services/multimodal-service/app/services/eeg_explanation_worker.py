"""Run with python -m app.services.eeg_explanation_worker (one CPU task at a time)."""
from __future__ import annotations

from datetime import timedelta
import json
import logging
import os
from pathlib import Path
import pickle
import signal
import subprocess
import sys
import tempfile
import time
import uuid

import numpy as np
from sqlalchemy import and_, or_, select

from app.config import get_settings
from app.database import get_db_session
from app.models import MultimodalEegExplanation, MultimodalInferenceResult
from app.services.eeg_explanation_math import aggregate_contributions, digest_json, feature_mapping
from app.services.eeg_explanation_service import file_hash, now_utc

logger = logging.getLogger(__name__)


def compute(payload: dict) -> dict:
    # Only a repository model, server-frozen input and verified reference asset enter this process.
    import shap
    if shap.__version__ != '0.46.0':
        raise ValueError('explainer_version_mismatch')
    settings = get_settings()
    config, snapshot = payload['config'], payload['snapshot']
    model_path = settings['eeg_model_path']
    background_path = settings['eeg_explanation_background_path']
    if file_hash(model_path) != config['model_sha256']:
        raise ValueError('model_version_unavailable')
    if (file_hash(background_path) != config['background_sha256']
            or file_hash(background_path.with_suffix('.json')) != config['background_manifest_sha256']):
        raise ValueError('background_version_unavailable')
    if snapshot.get('input_hash') != digest_json({k: v for k, v in snapshot.items() if k != 'input_hash'}):
        raise ValueError('input_snapshot_corrupt')
    model = pickle.loads(model_path.read_bytes())
    classifier = model['model']
    indices = list(map(int, model['selected_features']))
    names = [model['trial_feature_names'][i] for i in indices]
    if (names != snapshot['feature_names'] or indices != snapshot['selected_indices']
            or digest_json(names) != config['feature_names_hash']):
        raise ValueError('background_feature_mismatch')
    if classifier.decision_function_shape != 'ovr' or classifier.n_features_in_ != 110:
        raise ValueError('unsupported_model_output')
    with np.load(background_path, allow_pickle=False) as data:
        background = np.asarray(data['scaled_features'], dtype=float)
    if (background.ndim != 2 or background.shape[1] != 110
            or not 1 <= background.shape[0] <= config['max_background'] or not np.isfinite(background).all()):
        raise ValueError('invalid_background_shape')
    x = np.asarray(snapshot['scaled_vector'], dtype=float).reshape(1, -1)
    if x.shape != (1, 110) or not np.isfinite(x).all():
        raise ValueError('invalid_input_snapshot')
    classes = list(map(int, classifier.classes_))
    target_index = classes.index(config['target_class'])
    label_by_class = {0: '消极', 1: '中性', 2: '积极'}
    if label_by_class[int(classifier.predict(x)[0])] != payload['primary_label']:
        raise ValueError('prediction_replay_mismatch')
    def output(values):
        return classifier.decision_function(values)[:, target_index]
    np.random.seed(config['seed'])
    explainer = shap.KernelExplainer(output, background, link='identity')
    phi = explainer.shap_values(x, nsamples=config['nsamples'], l1_reg=0, silent=True)
    mapping = feature_mapping(model['trial_feature_names'], indices)
    return aggregate_contributions(phi, mapping, base_value=float(explainer.expected_value),
        target_output=float(output(x)[0]), influence_floor=float(config['influence_floor']))


def claim_task():
    settings = get_settings()
    with get_db_session() as db:
        now = now_utc()
        row = db.scalar(select(MultimodalEegExplanation).where(or_(
            MultimodalEegExplanation.status == 'queued',
            and_(MultimodalEegExplanation.status == 'running', MultimodalEegExplanation.lease_expires_at < now),
        )).order_by(MultimodalEegExplanation.created_at).with_for_update(skip_locked=True).limit(1))
        if row is None:
            return None
        if row.attempts >= 3:
            row.status, row.error_code, row.finished_at = 'failed', 'worker_retry_exhausted', now
            return None
        row.attempts += 1
        row.status, row.started_at, row.lease_token = 'running', now, str(uuid.uuid4())
        row.lease_expires_at = now + timedelta(seconds=settings['eeg_explanation_timeout_seconds'] + 60)
        inference = db.get(MultimodalInferenceResult, row.inference_id)
        return {'id': row.id, 'lease_token': row.lease_token, 'config': row.config_payload,
                'snapshot': inference.inference_payload.get('_explanation_input', {}),
                'primary_label': inference.inference_payload.get('primary_label')}


def process_task(task):
    started = time.monotonic()
    status, error, result = 'ready', None, None
    try:
        # Hard timeout applies to a disposable child; it cannot block acquisition or retain a DB lock.
        with tempfile.TemporaryDirectory(prefix='mcs-eeg-explain-') as folder:
            data_path = Path(folder) / 'task.json'
            data_path.write_text(json.dumps(task, allow_nan=False))
            env = {**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'NUMBA_NUM_THREADS': '1'}
            child = subprocess.run([sys.executable, '-m', 'app.services.eeg_explanation_worker', '--compute', str(data_path)],
                timeout=get_settings()['eeg_explanation_timeout_seconds'], capture_output=True, env=env)
            if child.returncode:
                raise RuntimeError('explanation_worker_failed')
            response = json.loads(data_path.read_text())
            result, error = response.get('values'), response.get('error_code')
            if error:
                status = 'invalid' if error in {'additivity_check_failed', 'invalid_attribution_shape', 'nonfinite_model_output', 'prediction_replay_mismatch', 'input_snapshot_corrupt'} else 'unavailable'
    except subprocess.TimeoutExpired:
        status, error = 'failed', 'explanation_timeout'
    except Exception:
        logger.exception('EEG explanation failed id=%s', task['id'])
        status, error = 'failed', 'explanation_worker_failed'
    with get_db_session() as db:
        row = db.scalar(select(MultimodalEegExplanation).where(
            MultimodalEegExplanation.id == task['id'],
            MultimodalEegExplanation.lease_token == task['lease_token'],
            MultimodalEegExplanation.status == 'running').with_for_update())
        if row is None:
            return
        row.status = 'queued' if status == 'failed' and row.attempts < 3 else status
        row.error_code, row.result_payload = error, result if status == 'ready' else None
        row.finished_at, row.lease_expires_at = now_utc(), None
        row.duration_ms = int((time.monotonic() - started) * 1000)
    # A small patch is sufficient; history/detail polling also recovers missed notifications.
    from app.services.multimodal_live_stream import publish_multimodal_live_snapshot
    with get_db_session() as db:
        row = db.get(MultimodalEegExplanation, task['id'])
        if row:
            publish_multimodal_live_snapshot(row.session_id, {'eeg_explanation_status': {
                'explanation_id': row.id, 'sample_id': row.sample_id, 'inference_id': row.inference_id,
                'target_class': row.target_class, 'status': row.status}})


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("shap").setLevel(logging.WARNING)
    if len(sys.argv) == 3 and sys.argv[1] == '--compute':
        path = Path(sys.argv[2])
        try:
            result = {'values': compute(json.loads(path.read_text())), 'error_code': None}
        except (ValueError, KeyError, ImportError, OSError) as exc:
            code = str(exc) if isinstance(exc, ValueError) else 'explanation_assets_unavailable'
            result = {'values': None, 'error_code': code}
        path.write_text(json.dumps(result, allow_nan=False))
        return
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not stopping:
        try:
            task = claim_task()
            if task:
                process_task(task)
            else:
                time.sleep(1)
        except Exception:
            logger.exception('EEG task polling failed')
            time.sleep(3)


if __name__ == '__main__':
    main()
