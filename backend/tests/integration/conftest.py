"""
통합 테스트 conftest — FastAPI TestClient 픽스처 제공

사용법:
  pytest backend/tests/integration/ -v
"""
from __future__ import annotations

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_integration.db")
os.environ.setdefault("QDRANT_REST_ONLY", "true")
os.environ.setdefault("ENABLE_FIXED_ADMIN_BOOTSTRAP", "false")
os.environ.setdefault("ENABLE_AD_ORDER_WORKER_BOOTSTRAP", "false")
os.environ.setdefault("ENABLE_SELF_RUN_VIDEO_WORKER_BOOTSTRAP", "false")


@pytest.fixture(scope="session")
def test_client():
    """FastAPI TestClient 세션 스코프 픽스처"""
    from fastapi.testclient import TestClient

    try:
        from backend.main import app
    except Exception:
        pytest.skip("backend.main import 실패 — 의존성 미설치 환경")
        return

    with TestClient(app) as client:
        yield client
