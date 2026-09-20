"""Extras engine experiment/launch must not import files outside engines120."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.marketplace import extras_router as extras_router_module
from backend.marketplace.extras_router import (
    _engines120_root,
    _is_safe_engine_basename,
    _resolve_engines120_target,
    _safe_recovery_engine_filename,
    build_extras_router,
)


class _FakeContract:
    def get_current_user(self):
        return SimpleNamespace(id=11, email="buyer@example.com")


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(build_extras_router(_FakeContract()), prefix="/api/marketplace")
    return TestClient(app)


def test_path_join_with_absolute_file_escapes_engines120():
    """Document the pre-fix Path join behavior that made RCE trivial."""
    root = _engines120_root()
    escaped = root / "/tmp/evil.py"
    assert escaped == Path("/tmp/evil.py")
    traversed = (root / "../../../auth.py").resolve()
    assert not traversed.is_relative_to(root)


@pytest.mark.parametrize(
    "name",
    [
        "/tmp/evil.py",
        "../auth.py",
        "../../auth.py",
        "../../../auth.py",
        "foo/../slot001_sorisae_voice_movie_server.py",
        "subdir/slot001.py",
        "..\\auth.py",
        "not_python.txt",
        "",
    ],
)
def test_unsafe_engine_basenames_are_rejected(name: str):
    assert _is_safe_engine_basename(name) is False


def test_safe_engine_basename_accepts_slot_file():
    assert _is_safe_engine_basename("slot001_sorisae_voice_movie_server.py") is True


def test_resolve_rejects_absolute_and_parent_paths():
    with pytest.raises(HTTPException) as absolute_exc:
        _resolve_engines120_target("/tmp/evil.py", 1)
    assert absolute_exc.value.status_code == 400

    with pytest.raises(HTTPException) as parent_exc:
        _resolve_engines120_target("../../../auth.py", 1)
    assert parent_exc.value.status_code == 400


def test_resolve_accepts_existing_slot_basename_inside_engines120():
    target = _resolve_engines120_target("slot001_sorisae_voice_movie_server.py", 1)
    assert target is not None
    assert target.name == "slot001_sorisae_voice_movie_server.py"
    assert target.is_relative_to(_engines120_root())


def test_resolve_falls_back_to_slot_glob_when_file_missing():
    target = _resolve_engines120_target("does-not-exist.py", 1)
    assert target is not None
    assert target.name.startswith("slot001_")
    assert target.is_relative_to(_engines120_root())


def test_recovery_filename_rejects_traversal():
    with pytest.raises(HTTPException) as exc:
        _safe_recovery_engine_filename("../../../backend/auth.py")
    assert exc.value.status_code == 400
    assert _safe_recovery_engine_filename("cyber_detective_ai") == "cyber_detective_ai.py"


def test_experiment_http_rejects_absolute_file_without_importing_it(monkeypatch):
    calls: list[Path] = []

    def _should_not_run(target_file: Path, user_input: str, timeout_sec: float):
        calls.append(target_file)
        raise AssertionError("outside engines120 must not be executed")

    monkeypatch.setattr(extras_router_module, "_run_module_experiment", _should_not_run)
    client = _build_client()
    response = client.post(
        "/api/marketplace/extras/engine/experiment",
        json={"slot": 1, "file": "/tmp/evil.py", "experiment_input": "ping"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "잘못된 엔진 파일명입니다."
    assert calls == []


def test_launch_http_rejects_parent_path(monkeypatch):
    def _fail_if_called(*_args, **_kwargs):
        raise AssertionError("escaped engine file must not be imported")

    monkeypatch.setattr("importlib.util.spec_from_file_location", _fail_if_called)
    client = _build_client()
    response = client.post(
        "/api/marketplace/extras/engine/launch",
        json={"slot": 1, "file": "../../../auth.py", "dry_run": True},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "잘못된 엔진 파일명입니다."


def test_recovery_http_rejects_traversal():
    client = _build_client()
    # Keep a single path segment so the route matches; ".." still fails the basename guard.
    response = client.post("/api/marketplace/extras/recovery/recover/..auth.py")
    assert response.status_code == 400
    assert response.json()["detail"] == "잘못된 엔진 파일명입니다."
