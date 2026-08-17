import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_production_requires_configured_secret_key():
    env = os.environ.copy()
    env['APP_ENV'] = 'production'
    env['PYTHONPATH'] = str(ROOT_DIR)
    env.pop('SECRET_KEY', None)
    env.pop('JWT_SECRET', None)

    result = subprocess.run(
        [sys.executable, '-c', 'import backend.auth'],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert 'SECRET_KEY or JWT_SECRET must be configured' in output


def test_llm_and_image_mutation_routes_require_auth(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///./tmp/pytest_r1r8_routes.db')
    monkeypatch.setenv('SECRET_KEY', 'pytest-r1-r8-route-secret-000000000001')

    from backend.image.router import router as image_router
    from backend.llm.orchestrator import router as llm_router

    app = FastAPI()
    app.include_router(llm_router)
    app.include_router(image_router)
    client = TestClient(app)

    checks = [
        ('GET', '/api/llm/runtime-config', None),
        ('POST', '/api/llm/runtime-config', {}),
        ('POST', '/api/llm/orchestrate', {'task': 'r1r8 pytest probe', 'auto_apply': False, 'run_postcheck': False}),
        ('POST', '/api/llm/orchestrate/accepted', {'task': 'r1r8 pytest probe', 'auto_apply': False, 'run_postcheck': False}),
        ('POST', '/api/llm/orchestrate/chat', {'message': 'r1r8 pytest probe'}),
        ('POST', '/api/v1/image/generate', {'prompt': 'r1r8 pytest probe'}),
        ('POST', '/api/v1/image/stylize-reference', {'prompt': 'r1r8 pytest probe', 'source_image_base64': 'x'}),
        ('POST', '/api/v1/image/generate-keyframes', {'base_prompt': 'r1r8 pytest probe', 'scenes': ['scene'], 'source_image_base64': 'x'}),
    ]

    for method, path, payload in checks:
        response = client.request(method, path, json=payload) if payload is not None else client.request(method, path)
        assert response.status_code == 401


def test_admin_runtime_config_quota_returns_429(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///./tmp/pytest_r1r8_quota.db')
    monkeypatch.setenv('SECRET_KEY', 'pytest-r1-r8-quota-secret-000000000001')
    monkeypatch.setenv('ADMIN_MUTATION_QUOTA_MAX_REQUESTS', '1')
    monkeypatch.setenv('ADMIN_MUTATION_QUOTA_WINDOW_SEC', '60')

    from backend.auth import get_current_user
    from backend.llm.orchestrator import router as llm_router

    app = FastAPI()
    app.include_router(llm_router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=8901,
        email='r1r8-pytest-admin@example.com',
        username='r1r8-pytest-admin',
        is_admin=True,
        is_superuser=False,
        is_active=True,
    )
    client = TestClient(app)

    first = client.get('/api/llm/runtime-config')
    second = client.get('/api/llm/runtime-config')

    assert first.status_code == 200
    assert second.status_code == 429
    assert 'Retry-After' in second.headers