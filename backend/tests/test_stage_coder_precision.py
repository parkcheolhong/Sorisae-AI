"""코더 단계 패치 + reviewer 자동 수정 루프 테스트."""
from __future__ import annotations

import pytest

from backend.orchestrator.autonomous.agents.base import AgentResult
from backend.orchestrator.autonomous.session import AutonomousSession, StageState
from backend.orchestrator.autonomous.stage_definitions import STAGE_DEFINITIONS
from backend.orchestrator.autonomous.turn_controller import TurnController


@pytest.mark.asyncio
async def test_stage_one_coder_writes_bounded_files(tmp_path, monkeypatch):
    session_dir = tmp_path / "autonomous_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
        str(session_dir),
    )

    session = AutonomousSession.create(owner_id="probe", mode="semi_auto")
    session.task = "FastAPI 헬스체크 API"
    session.stages = [
        StageState(stage_id=s["id"], stage_label=s["label"], status="pending")
        for s in STAGE_DEFINITIONS
    ]
    session.stages[0].status = "in_progress"
    session.current_stage_index = 0
    session.approval_state = "approved"
    session.execution_state = "executing"
    session.save()

    controller = TurnController(llm_call=None)
    results = await controller._execute_current_stage(session)

    coder = next(r for r in results if r.agent == "coder")
    file_count = int(coder.artifacts.get("file_count") or 0)
    assert file_count <= 15, f"expected stage patch, got {file_count} files"
    assert coder.artifacts.get("stage_patch_mode") is True


def test_extract_reviewer_issues_from_markdown():
    controller = TurnController()
    review = AgentResult(
        agent="reviewer",
        status="needs_revision",
        output=(
            "## 검토 결과\n- approved: false\n\n"
            "## 발견된 문제\n"
            "- tests 디렉터리 비어 있음\n"
            "- DB 연결 미구현\n\n"
            "## 개선 제안\n- test 추가"
        ),
    )
    issues = controller._extract_reviewer_issues(review)
    assert len(issues) == 2
    assert "tests" in issues[0]
