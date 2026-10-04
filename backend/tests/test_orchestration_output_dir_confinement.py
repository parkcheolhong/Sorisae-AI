"""Client output_dir must not overwrite the live repository tree."""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from backend.llm.orchestrator import (
    REPO_ROOT,
    _compat_write_manifest,
    _trusted_orchestration_output_dir,
)
from backend.orchestrator.autonomous.agents.base import AgentContext
from backend.orchestrator.autonomous.agents.coder import CoderAgent


def test_upload_root_env_cannot_reopen_the_repository(monkeypatch, tmp_path: Path) -> None:
    repo = Path(REPO_ROOT).resolve()
    monkeypatch.setenv("MARKETPLACE_UPLOAD_ROOT", str(repo))
    assert _trusted_orchestration_output_dir(repo) != repo

    external = tmp_path / "external-uploads"
    project = external / "customer_1" / "runs" / "job"
    monkeypatch.setenv("MARKETPLACE_UPLOAD_ROOT", str(external))
    assert _trusted_orchestration_output_dir(project) == project.resolve()


def test_repository_root_is_not_a_trusted_output_dir() -> None:
    repo = Path(REPO_ROOT).resolve()
    trusted = _trusted_orchestration_output_dir(repo)
    uploads = (repo / "uploads").resolve()

    assert trusted != repo
    assert trusted.is_relative_to(uploads / "projects")
    assert _trusted_orchestration_output_dir(repo / "backend").is_relative_to(uploads / "projects")
    assert _trusted_orchestration_output_dir(uploads / "projects" / "customer_run") == (
        uploads / "projects" / "customer_run"
    ).resolve()


def test_manifest_write_does_not_overwrite_repository_tree(tmp_path: Path) -> None:
    repo = Path(REPO_ROOT).resolve()
    probe = repo / "_output_confine_probe"
    remapped = _trusted_orchestration_output_dir(probe)
    shutil.rmtree(probe, ignore_errors=True)
    shutil.rmtree(remapped, ignore_errors=True)
    probe.mkdir()
    sentinel = probe / "requirements.txt"
    sentinel.write_text("SENTINEL_DO_NOT_LOSE\n", encoding="utf-8")
    try:
        written = _compat_write_manifest(
            probe,
            [{"path": "requirements.txt", "content": "overwritten\n"}],
        )
        assert written == ["requirements.txt"]
        assert sentinel.read_text(encoding="utf-8") == "SENTINEL_DO_NOT_LOSE\n"
        assert (remapped / "requirements.txt").is_file()
        assert (repo / "requirements.txt").read_text(encoding="utf-8") != "overwritten\n"
    finally:
        shutil.rmtree(probe, ignore_errors=True)
        shutil.rmtree(remapped, ignore_errors=True)

    temp_target = _trusted_orchestration_output_dir(tmp_path)
    assert temp_target == tmp_path.resolve()


def test_stage_coder_does_not_overwrite_repository_files() -> None:
    repo = Path(REPO_ROOT).resolve()
    probe = repo / "_output_confine_probe_coder"
    remapped = _trusted_orchestration_output_dir(probe)
    shutil.rmtree(probe, ignore_errors=True)
    shutil.rmtree(remapped, ignore_errors=True)
    probe.mkdir()
    (probe / "requirements.txt").write_text("SENTINEL_DO_NOT_LOSE\n", encoding="utf-8")
    (probe / "README.md").write_text("SENTINEL_README\n", encoding="utf-8")
    app_main = probe / "app" / "main.py"
    app_main.parent.mkdir(parents=True)
    app_main.write_text("SENTINEL_APP\n", encoding="utf-8")
    try:
        ctx = AgentContext(
            run_id="probe",
            task="FastAPI 헬스체크 API 만들어줘",
            project_name="probe",
            validation_profile="python_fastapi",
            stage_id="STAGE-01",
            output_dir=str(probe),
        )
        result = asyncio.run(CoderAgent().execute(ctx))
        assert result.status == "success"
        assert (probe / "requirements.txt").read_text(encoding="utf-8") == "SENTINEL_DO_NOT_LOSE\n"
        assert (probe / "README.md").read_text(encoding="utf-8") == "SENTINEL_README\n"
        assert app_main.read_text(encoding="utf-8") == "SENTINEL_APP\n"
        assert Path(str(result.artifacts["output_dir"])).is_relative_to(repo / "uploads" / "projects")
        assert (remapped / "requirements.txt").is_file()
    finally:
        shutil.rmtree(probe, ignore_errors=True)
        shutil.rmtree(remapped, ignore_errors=True)
