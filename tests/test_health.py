# FILE-ID: FILE-TESTS-TEST-HEALTH-PY
# SECTION-ID: SECTION-TESTS-TEST-HEALTH-PY-MAIN
# FEATURE-ID: FEATURE-TESTS-TEST-HEALTH-PY-RUNTIME
# CHUNK-ID: CHUNK-TESTS-TEST-HEALTH-PY-001

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    assert response.json()['checks']['ai_contract_ready'] is True
