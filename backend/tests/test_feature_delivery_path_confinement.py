"""feature-delivery 다운로드 경로 보안 회귀 테스트.

run_id 는 파일 경로에 직접 결합되므로(_stage_run_path) 토큰 화이트리스트로 트래버설을 막고,
제공 파일은 산출물 루트(시스템 temp/codeai-marketplace-*) 안으로 confine 한다(임의 파일 노출 방지).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.marketplace import router as mp_router


def test_run_id_regex_accepts_token_urlsafe_form() -> None:
    assert mp_router._FEATURE_RUN_ID_RE.match("stage_run_AbC-123_xyz")
    assert mp_router._FEATURE_RUN_ID_RE.match("abc123")


@pytest.mark.parametrize(
    "bad",
    [
        "../../etc/passwd",
        "..\\..\\secrets",
        "stage/run",
        "run id",
        "run.id.json",
        "",
        "x" * 200,
    ],
)
def test_run_id_regex_rejects_traversal_and_separators(bad: str) -> None:
    assert not mp_router._FEATURE_RUN_ID_RE.match(bad)


def test_resolver_rejects_malformed_run_id() -> None:
    with pytest.raises(HTTPException) as excinfo:
        mp_router._resolve_feature_delivery_asset_or_404("../../etc/passwd", "pdf")
    assert excinfo.value.status_code == 400


def test_path_confinement_allows_generated_artifact_root() -> None:
    allowed = Path(tempfile.gettempdir()) / "codeai-marketplace-image" / "seed" / "out.png"
    # 존재하지 않아도 confine 검사 자체는 통과해야 한다(파일 존재 검사는 별도 단계).
    mp_router._assert_delivery_path_confined(allowed)


@pytest.mark.parametrize(
    "outside",
    [
        Path(tempfile.gettempdir()) / "totally-unrelated" / "secret.bin",
        Path(tempfile.gettempdir()) / "codeai-marketplace-image" / ".." / ".." / "secret.bin",
    ],
)
def test_path_confinement_blocks_outside_roots(outside: Path) -> None:
    with pytest.raises(HTTPException) as excinfo:
        mp_router._assert_delivery_path_confined(outside)
    assert excinfo.value.status_code == 404
