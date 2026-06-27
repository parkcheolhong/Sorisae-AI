from __future__ import annotations

import pytest

from backend.llm.orchestrator_progress_tracker import save_orchestration_progress
from backend.orchestrator.autonomous.progress_stream import (
    format_sse_frame,
    iter_orchestration_progress_sse,
)


@pytest.mark.asyncio
async def test_iter_orchestration_progress_sse_emits_progress_and_done(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_RUNTIME_ROOT", str(tmp_path / "runtime"))
    run_id = "session_sse_001"
    save_orchestration_progress(
        run_id,
        {
            "run_id": run_id,
            "status": "success",
            "execution_state": "completed",
            "active_substep": "coder",
            "substeps": [{"id": "coder", "status": "completed", "message": "STAGE-04 · coder → success"}],
            "events": [{"at": "2026-06-17T00:00:00Z", "level": "info", "message": "STAGE-04 · coder → success"}],
        },
    )

    frames = []
    async for frame in iter_orchestration_progress_sse(run_id, poll_interval_sec=0.01, heartbeat_interval_sec=999):
        frames.append(frame)
        if "event: done" in frame:
            break

    assert any("event: progress" in frame for frame in frames)
    assert frames[-1].startswith("event: done")
    progress_frame = next(frame for frame in frames if "event: progress" in frame)
    assert '"progress_source": "autonomous_sse"' in progress_frame


def test_format_sse_frame_json():
    frame = format_sse_frame("progress", {"run_id": "abc", "status": "running"})
    assert frame.startswith("event: progress\n")
    assert '"run_id": "abc"' in frame


@pytest.mark.asyncio
async def test_iter_orchestration_progress_sse_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_RUNTIME_ROOT", str(tmp_path / "runtime"))
    frames = []
    async for frame in iter_orchestration_progress_sse(
        "missing-run",
        poll_interval_sec=0.01,
        wait_for_start_sec=0.05,
    ):
        frames.append(frame)
    assert frames
    assert "event: error" in frames[-1]
