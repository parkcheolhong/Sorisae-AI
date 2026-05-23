# FILE-ID: FILE-TESTS-TEST-SECURITY-RUNTIME-PY
# SECTION-ID: SECTION-TESTS-TEST-SECURITY-RUNTIME-PY-MAIN
# FEATURE-ID: FEATURE-TESTS-TEST-SECURITY-RUNTIME-PY-RUNTIME
# CHUNK-ID: CHUNK-TESTS-TEST-SECURITY-RUNTIME-PY-001

from fastapi.testclient import TestClient
from app.main import app
from backend.core.auth import get_auth_settings
from backend.core.security import get_security_profile

client = TestClient(app)

def test_security_defaults():
    auth = get_auth_settings()
    profile = get_security_profile()
    assert auth['enabled'] is True
    assert profile['https_only'] is True
    assert profile['allowed_hosts']
    assert client.get('/auth/settings').status_code == 200
    assert client.get('/ops/status').status_code == 200
