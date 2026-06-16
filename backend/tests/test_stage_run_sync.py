"""stage_run ↔ autonomous session 동기화 테스트."""
from __future__ import annotations

import json

import pytest

from backend.orchestration_stage_service import initialize_stage_run, load_stage_run
from backend.orchestrator.autonomous.session import AutonomousSession, StageState
from backend.orchestrator.autonomous.stage_run_sync import sync_stage_run_from_autonomous_session
from backend.orchestrator.autonomous.turn_controller import STAGE_DEFINITIONS


def test_sync_marks_arch001_passed_and_advances_to_arch002(tmp_path, monkeypatch):
    stage_run_dir = tmp_path / "stage_runs"
    stage_run_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "backend.orchestration_stage_service._STAGE_RUN_ROOT",
        stage_run_dir,
    )

    stage_run = initialize_stage_run(
        scope="marketplace",
        project_name="scanner",
        mode="full",
        requested_by={"id": "42"},
    )
    run_id = stage_run["run_id"]

    session = AutonomousSession.create(owner_id="42", mode="semi_auto")
    session.task = "project scanner"
    session.stages = [
        StageState(stage_id=s["id"], stage_label=s["label"], status="pending")
        for s in STAGE_DEFINITIONS
    ]
    session.stages[0].status = "completed"
    session.stages[1].status = "in_progress"
    session.current_stage_index = 1
    session.agent_results = []

    synced = sync_stage_run_from_autonomous_session(stage_run_id=run_id, session=session)
    assert synced is not None
    assert synced["current_stage_id"] == "ARCH-002"
    arch1 = next(stage for stage in synced["stages"] if stage["id"] == "ARCH-001")
    arch2 = next(stage for stage in synced["stages"] if stage["id"] == "ARCH-002")
    assert arch1["status"] == "passed"
    assert arch2["status"] == "running"


def test_sync_design_substeps_while_awaiting_approval(tmp_path, monkeypatch):
    stage_run_dir = tmp_path / "stage_runs"
    stage_run_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "backend.orchestration_stage_service._STAGE_RUN_ROOT",
        stage_run_dir,
    )

    stage_run = initialize_stage_run(
        scope="marketplace",
        project_name="scanner",
        mode="full",
        requested_by={"id": "42"},
    )
    run_id = stage_run["run_id"]

    session = AutonomousSession.create(owner_id="42", mode="semi_auto")
    session.execution_state = "awaiting_approval"
    session.approval_state = "pending"
    session.stages = [
        StageState(stage_id=s["id"], stage_label=s["label"], status="pending")
        for s in STAGE_DEFINITIONS
    ]
    session.stages[0].status = "in_progress"
    session.current_stage_index = 0

    from backend.orchestrator.autonomous.agents.base import AgentResult

    session.agent_results = [
        AgentResult(agent="reasoner", status="success", output="design"),
        AgentResult(agent="planner", status="success", output="plan"),
    ]

    synced = sync_stage_run_from_autonomous_session(stage_run_id=run_id, session=session)
    arch1 = next(stage for stage in synced["stages"] if stage["id"] == "ARCH-001")
    substeps = arch1["substeps"]
    assert substeps[0]["status"] == "passed"
    assert substeps[1]["status"] == "passed"
    assert substeps[2]["status"] == "running"
    assert synced["current_stage_id"] == "ARCH-001"
