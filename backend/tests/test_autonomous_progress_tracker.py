from __future__ import annotations

import pytest

from backend.orchestrator.autonomous.progress_tracker import (
    build_autonomous_progress_snapshot,
    load_progress_for_run,
    persist_autonomous_progress,
)
from backend.orchestrator.autonomous.session import AutonomousSession


def test_build_autonomous_progress_snapshot_running():
    session = AutonomousSession.create(owner_id="owner-1", mode="semi_auto", project_name="demo")
    session.execution_state = "executing"
    session.task = "Redis cache discuss"
    snapshot = build_autonomous_progress_snapshot(session)
    assert snapshot["orchestrator_core"] == "autonomous_turn_controller"
    assert snapshot["status"] == "running"
    assert snapshot["execution_state"] == "executing"
    assert snapshot["session_id"] == session.session_id


def test_persist_and_load_progress_aliases(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_RUNTIME_ROOT", str(tmp_path / "runtime"))
    session = AutonomousSession.create(owner_id="owner-2", mode="semi_auto", project_name="demo")
    session.extra["stage_run_id"] = "stage_run_abc123"
    session.extra["progress_run_id"] = session.session_id
    session.execution_state = "executing"

    persist_autonomous_progress(
        session,
        stage_run_id="stage_run_abc123",
        event_message="discuss · executing",
    )

    by_session = load_progress_for_run(session.session_id)
    by_stage_run = load_progress_for_run("stage_run_abc123")
    assert by_session["session_id"] == session.session_id
    assert by_stage_run["session_id"] == session.session_id
    assert any("discuss" in str(item.get("message", "")) for item in by_session.get("events") or [])


def test_persist_records_substep_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_RUNTIME_ROOT", str(tmp_path / "runtime"))
    session = AutonomousSession.create(owner_id="owner-3", mode="semi_auto", project_name="demo")
    session.execution_state = "executing"

    persist_autonomous_progress(
        session,
        event_message="STAGE-04 · coder → success",
    )

    payload = load_progress_for_run(session.session_id)
    assert payload.get("active_substep") == "coder"
    assert payload.get("substeps")
    assert payload.get("orchestrator_core") == "autonomous_turn_controller"
