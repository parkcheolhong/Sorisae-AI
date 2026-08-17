"""
회귀 테스트: 마켓플레이스 인증 경계 + 상태전이 3건 수정 검증
==========================================================
수정 항목:
  FIX-1 (HIGH)   : face/ml/search 라우터 noop-auth 중복 등록 제거 (AUTH-BYPASS-001)
  FIX-2 (MEDIUM) : feature_orchestrate_router final_enabled 조건 역전 수정
  FIX-3 (LOW)    : music_router theme Optional[str] → str 타입 수정
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch, patch as _patch_obj

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# FIX-1: noop-auth 중복 등록이 제거됐는지 정적으로 검증
# ---------------------------------------------------------------------------

def test_fix1_main_no_noop_face_recognition_router():
    """main.py 에서 face_recognition_router 를 /api 직접 등록하는 코드가 없어야 한다."""
    with open("backend/main.py", encoding="utf-8") as f:
        src = f.read()
    # 수정 후에는 include_router(face_recognition_router ... prefix="/api") 블록이 없어야 함
    assert 'app.include_router(face_recognition_router, prefix="/api")' not in src, (
        "AUTH-BYPASS-001: face_recognition_router noop-auth 직접 등록이 아직 남아 있습니다."
    )


def test_fix1_main_no_noop_ml_detectors_router():
    """main.py 에서 ml_detectors_router 를 /api 직접 등록하는 코드가 없어야 한다."""
    with open("backend/main.py", encoding="utf-8") as f:
        src = f.read()
    assert 'app.include_router(ml_detectors_router, prefix="/api")' not in src, (
        "AUTH-BYPASS-001: ml_detectors_router noop-auth 직접 등록이 아직 남아 있습니다."
    )


def test_fix1_main_no_noop_vector_search_router():
    """main.py 에서 vector_search_router 를 /api 직접 등록하는 코드가 없어야 한다."""
    with open("backend/main.py", encoding="utf-8") as f:
        src = f.read()
    assert 'app.include_router(vector_search_router, prefix="/api")' not in src, (
        "AUTH-BYPASS-001: vector_search_router noop-auth 직접 등록이 아직 남아 있습니다."
    )


def test_fix1_face_recognition_router_build_with_noop_still_works():
    """noop 계약 없이 빌드한 라우터는 _noop_auth 를 사용하지만,
    이 라우터는 main.py 에서 더 이상 /api 에 등록되지 않아야 한다.
    (라우터 빌드 자체는 깨지지 않음 확인)"""
    from backend.marketplace.face_recognition_router import build_face_recognition_router
    router = build_face_recognition_router()  # contract=None → noop
    routes = [r.path for r in router.routes]
    assert "/face-recognition/status" in routes
    assert "/face-recognition/compare" in routes


def test_fix1_ml_detectors_router_build_with_noop_still_works():
    from backend.marketplace.ml_detectors_router import build_ml_detectors_router
    router = build_ml_detectors_router()
    routes = [r.path for r in router.routes]
    assert "/ml-detectors/status" in routes
    assert "/ml-detectors/run" in routes


def test_fix1_search_router_build_with_noop_still_works():
    from backend.marketplace.search_router import build_search_router
    router = build_search_router()
    routes = [r.path for r in router.routes]
    assert "/search/semantic" in routes
    assert "/search/index-project" in routes
    assert "/search/stats" in routes


def test_fix1_face_compare_requires_auth_when_contract_provided():
    """contract 를 주입하면 compare 엔드포인트가 인증을 요구해야 한다."""
    from backend.marketplace.face_recognition_router import build_face_recognition_router

    fake_user = SimpleNamespace(id=1, email="user@test.com")

    class _FakeContract:
        def get_current_user(self):
            raise HTTPException(status_code=401, detail="unauthorized")

    contract = _FakeContract()
    # build 시 contract.get_current_user 를 Depends 에 전달
    router = build_face_recognition_router(contract=contract)
    app = FastAPI()
    app.include_router(router, prefix="/api")

    client = TestClient(app, raise_server_exceptions=False)
    # 인증 없이 호출 → 401
    resp = client.post("/api/face-recognition/compare", json={"image_a": "a.jpg", "image_b": "b.jpg"})
    assert resp.status_code in (401, 422), (
        f"인증 없이 compare 가 {resp.status_code} 를 반환했습니다 (401 또는 422 기대)."
    )


def test_fix1_search_index_project_requires_auth_when_contract_provided():
    """contract 를 주입하면 /search/index-project 가 인증을 요구해야 한다."""
    from backend.marketplace.search_router import build_search_router

    class _FakeContract:
        def get_current_user(self):
            raise HTTPException(status_code=401, detail="unauthorized")

    contract = _FakeContract()
    router = build_search_router(contract=contract)
    app = FastAPI()
    app.include_router(router, prefix="/api")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/search/index-project", json={"project_id": 1, "title": "test"})
    assert resp.status_code in (401, 422), (
        f"인증 없이 index-project 가 {resp.status_code} 를 반환했습니다 (401 또는 422 기대)."
    )


# ---------------------------------------------------------------------------
# FIX-2: feature_orchestrate final_enabled 조건 역전 수정 검증
# ---------------------------------------------------------------------------

def test_fix2_source_final_enabled_false_skips_final_phase():
    """feature_orchestrate_router.py 소스에서
    final_enabled=False 분기가 run_final_phase 를 호출하지 않아야 한다."""
    with open("backend/marketplace/feature_orchestrate_router.py", encoding="utf-8") as f:
        src = f.read()

    # FIX-2 적용 후: preview-only 분기(if not final_enabled 블록) 안에
    # run_final_phase 호출이 없어야 한다.
    # 가장 단순한 검증: preview-only 블록 직후 return 전에 run_final_phase 가 없는지 확인.
    preview_only_block_start = src.find("# preview-only path: skip final render and quality gate entirely")
    assert preview_only_block_start != -1, "preview-only 주석을 찾을 수 없습니다."

    # preview-only 블록 끝(return 이후 첫 blank line)까지 잘라서 검사
    return_pos = src.find("return", preview_only_block_start)
    assert return_pos != -1, "preview-only 블록에 return 이 없습니다."
    preview_only_section = src[preview_only_block_start:return_pos + len("return")]
    assert "run_final_phase" not in preview_only_section, (
        "FIX-2: preview-only 분기 안에 run_final_phase 호출이 남아 있습니다."
    )
    assert "run_quality_gate" not in preview_only_section, (
        "FIX-2: preview-only 분기 안에 run_quality_gate 호출이 남아 있습니다."
    )


def test_fix2_source_final_enabled_true_runs_final_phase():
    """final_enabled=True 경로(분기 바깥)에는 run_final_phase 가 반드시 있어야 한다."""
    with open("backend/marketplace/feature_orchestrate_router.py", encoding="utf-8") as f:
        src = f.read()
    # preview-only 분기를 벗어난 뒤에 run_final_phase 가 호출됨을 확인
    preview_return_pos = src.find("return", src.find("# preview-only path"))
    after_preview_only = src[preview_return_pos + len("return"):]
    assert "run_final_phase" in after_preview_only, (
        "FIX-2: final_enabled=True 경로에 run_final_phase 가 없습니다."
    )


def test_fix2_preview_only_manifest_has_none_final_artifact():
    """preview-only 경로에서 build_artifact_manifest 가 None 을 넘기는지 소스 확인."""
    with open("backend/marketplace/feature_orchestrate_router.py", encoding="utf-8") as f:
        src = f.read()
    preview_only_start = src.find("# preview-only path: skip final render and quality gate entirely")
    return_pos = src.find("return", preview_only_start)
    section = src[preview_only_start:return_pos]
    # build_artifact_manifest(preview_artifact, None, None) 호출 확인
    assert "build_artifact_manifest(preview_artifact, None, None)" in section, (
        "FIX-2: preview-only 분기에서 build_artifact_manifest 에 None 을 전달하지 않습니다."
    )


# ---------------------------------------------------------------------------
# FIX-3: music_router theme Optional[str] → str 타입 수정 검증
# ---------------------------------------------------------------------------

def test_fix3_music_router_theme_fallback_in_source():
    """music_router.py 에서 payload.theme or \"\" 패턴이 있어야 한다."""
    with open("backend/marketplace/music_router.py", encoding="utf-8") as f:
        src = f.read()
    assert 'theme=payload.theme or ""' in src, (
        "FIX-3: music_router.py 에서 theme=payload.theme or \"\" 패턴이 없습니다."
    )
    assert "theme=payload.theme)" not in src, (
        "FIX-3: music_router.py 에 Optional[str] 직접 전달 코드가 아직 남아 있습니다."
    )


def test_fix3_music_compose_theme_none_does_not_crash():
    """theme=None 으로 compose 를 호출해도 create_complete_song 이 빈 문자열을 받아야 한다."""
    captured: dict[str, Any] = {}

    class _FakeStudio:
        def create_complete_song(self, *, emotion: str, theme: str):
            captured["theme"] = theme
            return {
                "title": "test-song",
                "lyrics": {"title": "lyrics"},
                "composition": {"title": "comp"},
            }

    class _FakeGenerator:
        def create_musical_composition(self, emotion, intensity):
            return {
                "title": "mood",
                "musical_elements": {"tempo": 120, "melody": [1, 2, 3, 4, 5, 6, 7, 8, 9]},
            }

    import backend.marketplace.music_router as _music_mod

    class _FakeContract:
        def get_current_user(self):
            return SimpleNamespace(id=1)

    router = _music_mod.build_music_router(contract=_FakeContract())
    app = FastAPI()
    app.include_router(router)  # prefix /music 는 router 에 이미 있음
    app.dependency_overrides[_FakeContract.get_current_user] = lambda: SimpleNamespace(id=1)

    with patch.object(_music_mod, "_get_music_runtime",
                      return_value=(_FakeStudio(), _FakeGenerator(), None)):
        client = TestClient(app)
        resp = client.post(
            "/music/compose/emotion",
            json={"emotion": "happy", "intensity": 0.7, "theme": None},
        )

    # theme=None 이 "" 로 변환되어 create_complete_song 에 전달됐는지 확인
    assert captured.get("theme") == "", (
        f"FIX-3: theme=None 이 빈 문자열로 변환되지 않았습니다. 실제값: {captured.get('theme')!r}"
    )


def test_fix3_music_compose_theme_string_passes_through():
    """theme 이 문자열일 때는 그대로 전달돼야 한다."""
    captured: dict[str, Any] = {}

    class _FakeStudio:
        def create_complete_song(self, *, emotion: str, theme: str):
            captured["theme"] = theme
            return {
                "title": "t",
                "lyrics": {"title": "l"},
                "composition": {"title": "c"},
            }

    class _FakeGenerator:
        def create_musical_composition(self, emotion, intensity):
            return {
                "title": "m",
                "musical_elements": {"tempo": 90, "melody": list(range(10))},
            }

    import backend.marketplace.music_router as _music_mod

    class _FakeContract:
        def get_current_user(self):
            return SimpleNamespace(id=1)

    router = _music_mod.build_music_router(contract=_FakeContract())
    app = FastAPI()
    app.include_router(router)  # prefix /music 는 router 에 이미 있음

    with patch.object(_music_mod, "_get_music_runtime",
                      return_value=(_FakeStudio(), _FakeGenerator(), None)):
        client = TestClient(app)
        resp = client.post(
            "/music/compose/emotion",
            json={"emotion": "sad", "intensity": 0.5, "theme": "nature"},
        )

    assert captured.get("theme") == "nature", (
        f"FIX-3: theme='nature' 가 그대로 전달되지 않았습니다. 실제값: {captured.get('theme')!r}"
    )
