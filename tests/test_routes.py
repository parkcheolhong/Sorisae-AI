# FILE-ID: FILE-TESTS-TEST-ROUTES-PY
# SECTION-ID: SECTION-TESTS-TEST-ROUTES-PY-MAIN
# FEATURE-ID: FEATURE-TESTS-TEST-ROUTES-PY-RUNTIME
# CHUNK-ID: CHUNK-TESTS-TEST-ROUTES-PY-001

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_order_profile_route():
    response = client.get('/order-profile')
    assert response.status_code == 200
    payload = response.json()
    assert payload['profile_id']
    report = client.get('/report')
    assert report.status_code == 200
    assert payload['mandatory_engine_contracts']

def test_ai_runtime_snapshot_marker():
    from backend.api.router import get_ai_runtime_snapshot
    payload = get_ai_runtime_snapshot({'records': []})
    assert payload['model_registry']
    assert payload['training_pipeline']
    assert payload['inference_runtime']
    assert payload['evaluation_report']

def test_ai_fastapi_endpoints():
    health = client.get('/ai/health')
    assert health.status_code == 200
    infer = client.post('/ai/inference', json={'signal_strength': 0.8, 'features': {'records': []}})
    assert infer.status_code == 200
    evaluate = client.post('/ai/evaluate', json={'predictions': [{'candidate_sets': [{'target': 'x', 'rank': 1, 'score': 0.8}], 'score': 0.8}]})
    assert evaluate.status_code == 200
