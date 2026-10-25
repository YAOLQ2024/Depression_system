"""Numerical / access / persistence regression tests. All reference data here are synthetic."""
from datetime import timedelta
import json
import os
import pickle
from pathlib import Path
import uuid

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Base, MultimodalCapture, MultimodalEegExplanation, MultimodalInferenceResult, MultimodalSession
from app.services import eeg_explanation_service as service
from app.services.eeg_explanation_math import aggregate_contributions, digest_json, feature_mapping, freeze_input, PIPELINE_VERSION


def test_signed_influence_and_coupled_channel_weights_are_conserved():
    mapping = feature_mapping(['med_DE_T7_delta', 'std_PAC_T7_T8_delta_theta', 'slope_PPC_Fpz_Fpz_delta_theta'], [0, 1, 2])
    result = aggregate_contributions(np.array([1., -2., 3.]), mapping, base_value=.5, target_output=2.5)
    assert sum(result['group_net'].values()) == 2
    assert sum(result['channel_net'].values()) == 2
    assert sum(result['channel_abs'].values()) == 6
    assert result['channel_abs']['T7'] == 2  # abs before sum, rather than abs(1 - 1)
    assert result['channel_abs']['Fpz'] == 3  # repeated channel does not double count
    assert sum(result['channel_percent'].values()) == 100
    low = aggregate_contributions(np.zeros(3), mapping, base_value=.5, target_output=.5)
    assert low['channel_percent'] is None
    with pytest.raises(ValueError, match='additivity'):
        aggregate_contributions(np.ones(3), mapping, base_value=0, target_output=20)
    with pytest.raises(ValueError, match='shape'):
        aggregate_contributions(np.array([float('nan')]), mapping, base_value=0, target_output=0)


@pytest.fixture
def synthetic_assets(tmp_path, monkeypatch):
    from sklearn.svm import SVC
    from sklearn.preprocessing import StandardScaler
    # The real feature vocabulary / selection order, paired with a newly trained synthetic classifier.
    baseline_path = Path(__file__).resolve().parents[1] / 'runtime-assets/eeg/EEG_model.pkl'
    baseline = pickle.loads(baseline_path.read_bytes())
    indices = list(map(int, baseline['selected_features']))
    names = baseline['trial_feature_names']
    rng = np.random.RandomState(29)
    train = rng.normal(size=(30, 110))
    labels = np.tile([0, 1, 2], 10)
    classifier = SVC(C=1.5, kernel='rbf', decision_function_shape='ovr').fit(train, labels)
    scaler = StandardScaler().fit(train)
    model_path = tmp_path / 'test_model.pkl'
    model_path.write_bytes(pickle.dumps({'model': classifier, 'scaler': scaler, 'selected_features': indices, 'trial_feature_names': names}))
    background_path = tmp_path / 'test_background.npz'
    np.savez_compressed(background_path, scaled_features=train[3:7])
    sha = service.file_hash(model_path)
    feature_names = [names[i] for i in indices]
    background_path.with_suffix('.json').write_text(json.dumps({'background_id': 'synthetic-test-only',
        'background_sha256': service.file_hash(background_path), 'model_sha256': sha,
        'pipeline_version': PIPELINE_VERSION, 'input_kind': 'selected_scaled',
        'feature_names': feature_names, 'color_limit': 1.0}))
    settings = {**get_settings(), 'eeg_model_path': model_path, 'eeg_explanation_background_path': background_path,
                'eeg_explanations_enabled': True, 'eeg_explanation_nsamples': 256, 'redis_enabled': False}
    monkeypatch.setattr(service, 'get_settings', lambda: settings)
    from app.services import eeg_explanation_worker as worker
    monkeypatch.setattr(worker, 'get_settings', lambda: settings)
    # Original model-input values are frozen; no reinterpretation through a new scaler.
    snapshot = freeze_input(model_sha256=sha, feature_names=names, selected=indices,
                            aggregated=np.zeros(156), scaled=train[0:1])
    label = {0: '消极', 1: '中性', 2: '积极'}[int(classifier.predict(train[0:1])[0])]
    return settings, snapshot, label


def test_real_kernel_shap_on_synthetic_reference_and_corrupt_snapshot(synthetic_assets):
    pytest.importorskip('shap')
    from app.services.eeg_explanation_worker import compute
    _, snapshot, label = synthetic_assets
    config, error = service.current_configuration(2)
    assert error is None
    result = compute({'config': config, 'snapshot': snapshot, 'primary_label': label})
    assert len(result['phi']) == 110
    assert abs(result['base_value'] + sum(result['phi']) - result['target_output']) < 1e-6
    assert abs(sum(result['channel_abs'].values()) - sum(map(abs, result['phi']))) < 1e-9
    assert any(abs(x) > 1e-7 for x in result['phi'])
    corrupted = {**snapshot, 'scaled_vector': [99.] * 110}
    with pytest.raises(ValueError, match='snapshot_corrupt'):
        compute({'config': config, 'snapshot': corrupted, 'primary_label': label})


@pytest.fixture
def database(monkeypatch):
    dsn = os.getenv('MCS_EEG_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Set MCS_EEG_TEST_DATABASE_URL to a disposable PostgreSQL database')
    url = make_url(dsn)
    assert url.database and url.database.startswith('mcs_eeg_test_'), 'Refusing to run against a non-test database'
    engine = create_engine(url.set(drivername='postgresql+psycopg'))
    # Migration tests run before this suite; never create a SQLite substitute.
    connection = engine.connect()
    transaction = connection.begin()
    from app import database as db_module
    monkeypatch.setattr(db_module, 'get_session_factory', lambda: lambda: Session(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint'))
    try:
        yield connection
    finally:
        transaction.rollback(); connection.close(); engine.dispose()


def seed_record(connection, *, session_id=None, user='alice', offset=0, snapshot=None, label='中性'):
    now = service.now_utc() + timedelta(seconds=offset)
    session_id = session_id or str(uuid.uuid4())
    with Session(bind=connection, join_transaction_mode='create_savepoint') as db:
        if not db.get(MultimodalSession, session_id):
            db.add(MultimodalSession(id=session_id, scope_type='flow', scope_id=session_id,
                flow_type='consultation', flow_run_id=session_id, user_id=user,
                stage_context={}, enabled_modalities=['eeg'], status='active', started_at=now, created_at=now, updated_at=now))
            db.flush()
        capture_id, inference_id = str(uuid.uuid4()), str(uuid.uuid4())
        db.add(MultimodalCapture(id=capture_id, session_id=session_id, turn_id=f'turn-{offset}',
            sample_index=1, modality='eeg', capture_kind='window',
            sample_started_at=now-timedelta(seconds=10), sample_ended_at=now, created_at=now))
        db.flush()
        payload = {'primary_label': label, 'status': 'ready', 'sample_started_at': (now-timedelta(seconds=10)).isoformat(),
            'sample_ended_at': now.isoformat(), 'model_sha256': (snapshot or {}).get('model_sha256')}
        if snapshot: payload['_explanation_input'] = snapshot
        db.add(MultimodalInferenceResult(id=inference_id, session_id=session_id, sample_id=capture_id,
            modality='eeg', source_kind='eeg_window', turn_id=f'turn-{offset}', inference_payload=payload, created_at=now))
        db.commit()
    return session_id, capture_id, inference_id


def test_history_across_turns_pagination_and_access(database):
    session_id, _, _ = seed_record(database)
    for i in range(1, 24): seed_record(database, session_id=session_id, offset=i)
    first = service.list_windows(session_id, 'alice', limit=20)
    second = service.list_windows(session_id, 'alice', limit=20, cursor=first['next_cursor'])
    assert len(first['items']) == 20 and len(second['items']) == 4
    assert {i['sample_id'] for i in first['items']}.isdisjoint(i['sample_id'] for i in second['items'])
    assert all(i['window_index'] == 1 for i in first['items'])  # Same window_index in different turns is safe.
    assert '_explanation_input' not in first['items'][0]
    with pytest.raises(service.EegExplanationError) as denied:
        service.list_windows(session_id, 'bob')
    assert denied.value.status_code == 403
    with pytest.raises(service.EegExplanationError):
        service.list_windows(session_id, 'alice', cursor='invalid cursor')


def test_task_idempotency_target_partition_and_cross_session_denial(database, synthetic_assets):
    _, snapshot, label = synthetic_assets
    session_id, sample_id, inference_id = seed_record(database, snapshot=snapshot, label=label)
    one = service.request_explanation(session_id, 'alice', inference_id=inference_id, target_class=2)
    repeated = service.request_explanation(session_id, 'alice', inference_id=inference_id, target_class=2)
    another = service.request_explanation(session_id, 'alice', inference_id=inference_id, target_class=0)
    assert one['explanation_id'] == repeated['explanation_id'] != another['explanation_id']
    assert one['sample_id'] == sample_id and one['status'] == 'queued' and one['values'] is None
    assert service.list_explanations(session_id, 'alice', target_class=2)['items'][0]['explanation_id'] == one['explanation_id']
    with pytest.raises(service.EegExplanationError):
        service.get_explanation(session_id, 'bob', one['explanation_id'])
    other_session, _, _ = seed_record(database)
    with pytest.raises(service.EegExplanationError):
        service.request_explanation(other_session, 'alice', inference_id=inference_id, target_class=2)
    with pytest.raises(service.EegExplanationError):
        service.get_explanation(other_session, 'alice', one['explanation_id'])
    # A cursor pins the full configuration, including the explanation target.
    for i in range(2): seed_record(database, session_id=session_id, offset=i+2)
    page = service.list_explanations(session_id, 'alice', target_class=2, limit=1)
    with pytest.raises(service.EegExplanationError):
        service.list_explanations(session_id, 'alice', target_class=0, limit=1, cursor=page['next_cursor'])


def test_missing_background_is_explicit_and_never_zero_filled(database, synthetic_assets):
    settings, snapshot, label = synthetic_assets
    settings['eeg_explanation_background_path'].unlink()
    session_id, _, inference_id = seed_record(database, snapshot=snapshot, label=label)
    result = service.request_explanation(session_id, 'alice', inference_id=inference_id, target_class=2)
    assert result['status'] == 'unavailable' and result['error_code'] == 'background_missing' and result['values'] is None
    history = service.list_explanations(session_id, 'alice', target_class=2)
    assert history['items'][0]['group_net'] is None
    assert history['color_scale']['max'] is None


def test_api_validation_and_worker_lease_recovery(database, synthetic_assets):
    _, snapshot, label = synthetic_assets
    from app.api.eeg_explanations import router
    from app.services.eeg_explanation_worker import claim_task
    app = FastAPI(); app.include_router(router)
    client = TestClient(app)
    session_id, _, inference_id = seed_record(database, snapshot=snapshot, label=label)
    base = f'/api/v1/multimodal/sessions/{session_id}/eeg'
    assert client.get(base+'/windows').status_code == 401
    headers = {'X-MCS-User-Id': 'alice'}
    assert client.get(base+'/explanations?target_class=2', headers=headers).status_code == 200
    assert client.post(base+'/explanations', headers=headers, json={'inference_id': inference_id, 'target_class': 8}).status_code == 422
    assert client.post(base+'/explanations', headers=headers, json={'inference_id': inference_id, 'target_class': 2, 'scaled_vector': [1]}).status_code == 422
    response = client.post(base+'/explanations', headers=headers, json={'inference_id': inference_id, 'target_class': 2})
    assert response.status_code == 202
    task = claim_task()
    assert task and task['snapshot']['input_hash'] == snapshot['input_hash']
    assert claim_task() is None
    with Session(bind=database, join_transaction_mode='create_savepoint') as db:
        row = db.get(MultimodalEegExplanation, task['id'])
        row.lease_expires_at = service.now_utc() - timedelta(seconds=1)
        db.commit()
    recovered = claim_task()
    assert recovered['id'] == task['id'] and recovered['lease_token'] != task['lease_token']


def test_worker_subprocess_completes_a_persistent_task(database, synthetic_assets, monkeypatch):
    from app.services.eeg_explanation_worker import claim_task, process_task
    settings, snapshot, label = synthetic_assets
    monkeypatch.setenv('EEG_MODEL_PATH', str(settings['eeg_model_path']))
    monkeypatch.setenv('EEG_EXPLANATION_BACKGROUND_PATH', str(settings['eeg_explanation_background_path']))
    monkeypatch.setenv('EEG_EXPLANATIONS_ENABLED', 'true')
    session_id, _, inference_id = seed_record(database, snapshot=snapshot, label=label)
    request = service.request_explanation(session_id, 'alice', inference_id=inference_id, target_class=2)
    task = claim_task()
    process_task(task)
    result = service.get_explanation(session_id, 'alice', request['explanation_id'])
    assert result['status'] == 'ready', result['error_code']
    assert len(result['values']['phi']) == 110
    assert service.list_explanations(session_id, 'alice', target_class=2)['items'][0]['group_net'] == result['values']['group_net']
    # Disabling new computations must not hide or overwrite an existing valid explanation.
    settings['eeg_explanations_enabled'] = False
    repeated = service.request_explanation(session_id, 'alice', inference_id=inference_id, target_class=2)
    assert repeated['explanation_id'] == result['explanation_id']
    assert repeated['status'] == 'ready'
    history = service.list_explanations(session_id, 'alice', target_class=2)
    assert history['items'][0]['status'] == 'ready'


def test_runtime_window_persists_the_same_ids_and_scaled_input(database, monkeypatch):
    from app.services.eeg_protocol import build_feature_frame
    from app.services.eeg_runtime import EEGRuntimeService
    session_id, _, _ = seed_record(database)
    runtime = EEGRuntimeService()
    runtime._enabled = True
    runtime._require_transport_for_ready = False
    assert runtime.warmup_model()
    monkeypatch.setattr(runtime, '_ensure_provider_started_locked', lambda: None)
    monkeypatch.setattr(runtime, '_upload_raw_window', lambda *a, **k: None)
    runtime.begin_turn(session_id=session_id, turn_id='new-turn', flow_run_id=session_id, stage_id='test', question_key='test')
    for i in range(10):
        runtime.ingest_transport_bytes(build_feature_frame([float(np.sin(j*.17+i*.37)) for j in range(57)]))
    live = runtime.get_session_live_payload(session_id)['eeg_live']['latest_result']
    assert live['sample_id'] and live['inference_id'] and live['model_sha256']
    with Session(bind=database, join_transaction_mode='create_savepoint') as db:
        record = db.get(MultimodalInferenceResult, live['inference_id'])
        assert record.sample_id == live['sample_id']
        snapshot = record.inference_payload['_explanation_input']
        assert len(snapshot['aggregate_vector']) == 156 and len(snapshot['scaled_vector']) == 110
        model = pickle.loads(Path(get_settings()['eeg_model_path']).read_bytes())
        vector = np.asarray(snapshot['aggregate_vector'], dtype=np.float32)[model['selected_features']].reshape(1, -1)
        np.testing.assert_array_equal(model['scaler'].transform(vector).reshape(-1), snapshot['scaled_vector'])
    window = next(w for w in service.list_windows(session_id, 'alice')['items'] if w['inference_id'] == live['inference_id'])
    assert window['sample_id'] == live['sample_id'] and window['model_sha256'] == live['model_sha256']


def test_following_live_windows_cannot_create_an_unbounded_queue(database, synthetic_assets):
    _, snapshot, label = synthetic_assets
    session_id, _, first_id = seed_record(database, snapshot=snapshot, label=label)
    ids = [first_id]
    for i in range(1, 4):
        _, _, identity = seed_record(database, session_id=session_id, offset=i, snapshot=snapshot, label=label)
        ids.append(identity)
    requested = [service.request_explanation(session_id, 'alice', inference_id=identity, target_class=2) for identity in ids]
    assert [r['status'] for r in requested] == ['queued', 'queued', 'queued', 'unavailable']
    assert requested[-1]['error_code'] == 'queue_busy' and requested[-1]['values'] is None
    with Session(bind=database, join_transaction_mode='create_savepoint') as db:
        db.get(MultimodalEegExplanation, requested[0]['explanation_id']).status = 'failed'
        db.commit()
    later = service.request_explanation(session_id, 'alice', inference_id=ids[-1], target_class=2)
    assert later['status'] == 'queued' and later['explanation_id'] != requested[-1]['explanation_id']
