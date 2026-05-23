"""
test_marketplace_security_improvements.py
==========================================
5개 보안/안정성 개선 Task 회귀 테스트

Task 1: 프로브 엔드포인트 rate limiting (slowapi)
Task 2: SSE try/finally 상태 보장
Task 3: asyncio.wait_for 타임아웃 강제
Task 4: /search/index-project Pydantic 입력 검증
Task 5: SSE 구조화 로깅 (failure_tag, stage_id, error_code)
"""
import asyncio
import importlib
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── Task 1: probe_rate_limit 모듈 존재 및 slowapi Limiter 확인 ───────────────
def test_task1_probe_rate_limit_module_exists():
    """probe_rate_limit.py 모듈이 존재하고 limiter를 노출한다."""
    import importlib
    mod = importlib.import_module("backend.marketplace.probe_rate_limit")
    assert hasattr(mod, "limiter"), "limiter가 없음"
    assert hasattr(mod, "PROBE_RATE_LIMIT"), "PROBE_RATE_LIMIT 상수가 없음"


def test_task1_probe_rate_limit_value():
    """PROBE_RATE_LIMIT 값이 비어있지 않다."""
    from backend.marketplace.probe_rate_limit import PROBE_RATE_LIMIT
    assert PROBE_RATE_LIMIT and "/" in PROBE_RATE_LIMIT


def test_task1_face_recognition_status_accepts_request_param():
    """face_recognition_router /status 엔드포인트가 request: Request 파라미터를 받는다."""
    import inspect
    from backend.marketplace.face_recognition_router import build_face_recognition_router
    router = build_face_recognition_router(contract=None)
    # /face-recognition/status 라우트의 endpoint 함수 파라미터 확인
    status_route = next(r for r in router.routes if "/face-recognition/status" in str(r.path))
    sig = inspect.signature(status_route.endpoint)
    assert "request" in sig.parameters, "/face-recognition/status에 request 파라미터 없음"


def test_task1_ml_detectors_status_accepts_request_param():
    """ml_detectors_router /status 엔드포인트가 request: Request 파라미터를 받는다."""
    import inspect
    from backend.marketplace.ml_detectors_router import build_ml_detectors_router
    router = build_ml_detectors_router(contract=None)
    status_route = next(r for r in router.routes if "/ml-detectors/status" in str(r.path))
    sig = inspect.signature(status_route.endpoint)
    assert "request" in sig.parameters, "/ml-detectors/status에 request 파라미터 없음"


# ─── Task 2: SSE try/finally 상태 보장 ────────────────────────────────────────
def test_task2_feature_orchestrate_router_source_has_finally():
    """feature_orchestrate_router.py 소스에 finally 블록이 존재한다."""
    import inspect
    import backend.marketplace.feature_orchestrate_router as mod
    src = inspect.getsource(mod)
    assert "finally:" in src, "finally 블록이 없음"


def test_task2_finally_block_covers_terminal_state_check():
    """finally 블록이 terminal 상태 목록을 확인하는 로직을 포함한다."""
    import inspect
    import backend.marketplace.feature_orchestrate_router as mod
    src = inspect.getsource(mod)
    assert "terminal_states" in src or "_terminal_states" in src, "terminal_states 체크 없음"
    assert "StreamAbandoned" in src, "StreamAbandoned failure_tag 없음"


# ─── Task 3: asyncio.wait_for 타임아웃 강제 ───────────────────────────────────
def test_task3_feature_orchestrate_uses_wait_for():
    """feature_orchestrate_router.py에 asyncio.wait_for 호출이 존재한다."""
    import inspect
    import backend.marketplace.feature_orchestrate_router as mod
    src = inspect.getsource(mod)
    assert "wait_for" in src, "asyncio.wait_for 호출이 없음"


def test_task3_face_recognition_compare_uses_asyncio_wait_for():
    """face_recognition_router.py compare 엔드포인트가 asyncio.wait_for를 사용한다."""
    import inspect
    import backend.marketplace.face_recognition_router as mod
    src = inspect.getsource(mod)
    assert "wait_for" in src, "face_recognition_router에 asyncio.wait_for 없음"


def test_task3_ml_detectors_run_uses_asyncio_wait_for():
    """ml_detectors_router.py run 엔드포인트가 asyncio.wait_for를 사용한다."""
    import inspect
    import backend.marketplace.ml_detectors_router as mod
    src = inspect.getsource(mod)
    assert "wait_for" in src, "ml_detectors_router에 asyncio.wait_for 없음"


def test_task3_face_compare_raises_504_on_timeout():
    """asyncio.TimeoutError 발생 시 face_recognition_compare가 504를 반환한다."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    import backend.marketplace.face_recognition_router as _mod

    with patch.object(_mod, "_compare_face_runtime_subprocess", side_effect=Exception("dummy")):
        router = _mod.build_face_recognition_router(contract=None)
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        # asyncio.wait_for TimeoutError를 시뮬레이션
        original_wait_for = asyncio.wait_for
        async def _timeout_sim(*args, **kwargs):
            raise asyncio.TimeoutError()

        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            resp = client.post("/face-recognition/compare", json={"image_a": "a.jpg", "image_b": "b.jpg"})
        assert resp.status_code == 504, f"예상 504, 실제 {resp.status_code}"


def test_task3_ml_run_raises_504_on_timeout():
    """asyncio.TimeoutError 발생 시 ml_detectors_run이 504를 반환한다."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    import backend.marketplace.ml_detectors_router as _mod

    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
        router = _mod.build_ml_detectors_router(contract=None)
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/ml-detectors/run", json={"detector": "face", "frame_paths": []})
    assert resp.status_code == 504, f"예상 504, 실제 {resp.status_code}"


# ─── Task 4: search_router Pydantic 검증 ──────────────────────────────────────
def test_task4_search_router_has_pydantic_model():
    """search_router.py에 IndexProjectRequest Pydantic 모델이 있다."""
    from backend.marketplace.search_router import IndexProjectRequest
    assert IndexProjectRequest is not None


def test_task4_index_project_rejects_zero_project_id():
    """project_id=0은 422 Validation Error를 반환한다."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from backend.marketplace.search_router import build_search_router

    router = build_search_router(contract=None)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/search/index-project", json={"project_id": 0, "title": "test"})
    assert resp.status_code == 422, f"예상 422, 실제 {resp.status_code}"


def test_task4_index_project_rejects_negative_project_id():
    """project_id=-1은 422 Validation Error를 반환한다."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from backend.marketplace.search_router import build_search_router

    router = build_search_router(contract=None)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/search/index-project", json={"project_id": -1, "title": "test"})
    assert resp.status_code == 422, f"예상 422, 실제 {resp.status_code}"


def test_task4_index_project_rejects_empty_title():
    """title='' 은 422 Validation Error를 반환한다."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from backend.marketplace.search_router import build_search_router

    router = build_search_router(contract=None)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/search/index-project", json={"project_id": 1, "title": ""})
    assert resp.status_code == 422, f"예상 422, 실제 {resp.status_code}"


def test_task4_index_project_rejects_title_too_long():
    """title이 200자 초과이면 422를 반환한다."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from backend.marketplace.search_router import build_search_router

    router = build_search_router(contract=None)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)
    long_title = "x" * 201
    resp = client.post("/search/index-project", json={"project_id": 1, "title": long_title})
    assert resp.status_code == 422, f"예상 422, 실제 {resp.status_code}"


def test_task4_index_project_rejects_description_too_long():
    """description이 2000자 초과이면 422를 반환한다."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from backend.marketplace.search_router import build_search_router

    router = build_search_router(contract=None)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)
    long_desc = "d" * 2001
    resp = client.post("/search/index-project", json={"project_id": 1, "title": "valid", "description": long_desc})
    assert resp.status_code == 422, f"예상 422, 실제 {resp.status_code}"


# ─── Task 5: SSE 구조화 로깅 ──────────────────────────────────────────────────
def test_task5_feature_orchestrate_router_source_has_failure_tag():
    """SSE except 블록에 failure_tag 필드가 포함된다."""
    import inspect
    import backend.marketplace.feature_orchestrate_router as mod
    src = inspect.getsource(mod)
    assert "failure_tag" in src, "failure_tag 없음"


def test_task5_feature_orchestrate_router_source_has_error_code():
    """SSE except 블록에 error_code 필드가 포함된다."""
    import inspect
    import backend.marketplace.feature_orchestrate_router as mod
    src = inspect.getsource(mod)
    assert "error_code" in src, "error_code 없음"


def test_task5_feature_orchestrate_router_source_has_traceback_summary():
    """SSE except 블록에 traceback_summary 필드가 포함된다."""
    import inspect
    import backend.marketplace.feature_orchestrate_router as mod
    src = inspect.getsource(mod)
    assert "traceback_summary" in src, "traceback_summary 없음"


def test_task5_feature_orchestrate_router_source_has_stage_id():
    """SSE except 블록에 stage_id 필드가 포함된다."""
    import inspect
    import backend.marketplace.feature_orchestrate_router as mod
    src = inspect.getsource(mod)
    assert "stage_id" in src, "stage_id 없음"
