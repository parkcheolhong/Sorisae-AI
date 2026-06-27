"""TurnController intent routing — 승인/상태 오분류 회귀 테스트."""
from __future__ import annotations

import pytest

from backend.orchestrator.autonomous.session import AutonomousSession
from backend.orchestrator.autonomous.turn_controller import TurnController


@pytest.fixture
def pending_session() -> AutonomousSession:
    session = AutonomousSession.create(owner_id="customer-1", mode="semi_auto")
    session.task = "ai 엔진 구현"
    session.execution_state = "awaiting_approval"
    session.approval_state = "pending"
    return session


def test_pending_approval_does_not_classify_progress_as_status(pending_session):
    controller = TurnController()

    assert controller.classify_intent("진행해", pending_session) == "approval"
    assert controller.classify_intent("승인합니다 진행해주세요", pending_session) == "approval"
    assert controller.classify_intent("승인", pending_session) == "approval"


def test_stage_question_is_status_not_reasoner(pending_session):
    controller = TurnController()

    assert controller.classify_intent("현재 몇단계입니까?", pending_session) == "status"
    assert controller.classify_intent("진행 상황 알려줘", pending_session) == "status"


def test_progress_keyword_without_approval_pending_is_not_status():
    controller = TurnController()

    assert controller.classify_intent("진행해") == "approval"
    assert controller.classify_intent("진행해주세요") == "approval"


def test_execution_request_after_design_is_code_generation():
    controller = TurnController()
    session = AutonomousSession.create(owner_id="admin-1", mode="semi_auto")
    session.agent_results.append(
        type("R", (), {"agent": "reasoner", "status": "success", "output": "design"})()
    )

    assert controller.classify_intent("지금 설계대로 실해해줘", session) == "code_generation"


def test_pending_implementation_request_forces_approval(pending_session):
    controller = TurnController()

    assert controller._should_force_approval(
        pending_session,
        "최신 기술 반영해서 구현 만들어줘",
        "code_generation",
    )
    assert controller._should_force_approval(
        pending_session,
        "지금 설계대로 실해해줘",
        "code_generation",
    )


@pytest.mark.asyncio
async def test_stage_design_command_sets_pending_approval(tmp_path, monkeypatch):
    session_dir = tmp_path / "autonomous_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
        str(session_dir),
    )

    session = AutonomousSession.create(owner_id="admin-1", mode="semi_auto")
    session.task = "FastAPI 블로그 API"
    session.save()

    controller = TurnController(llm_call=None)
    payload = await controller.process_turn("설계해줘", session)

    assert payload["intent"] == "stage_design"
    assert session.approval_state == "pending"
    assert session.execution_state == "awaiting_approval"
    assert session.current_stage_index == 0
    assert session.stages[0].status == "in_progress"
    assert "진행해" in payload["content"] or "단계" in payload["content"]


@pytest.mark.asyncio
async def test_stage_execute_blocked_without_prior_completion(tmp_path, monkeypatch):
    session_dir = tmp_path / "autonomous_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
        str(session_dir),
    )

    from backend.orchestrator.autonomous.session import StageState
    from backend.orchestrator.autonomous.stage_definitions import STAGE_DEFINITIONS

    session = AutonomousSession.create(owner_id="admin-1", mode="semi_auto")
    session.task = "블로그 API"
    session.stages = [
        StageState(stage_id=s["id"], stage_label=s["label"], status="pending")
        for s in STAGE_DEFINITIONS
    ]
    session.stages[0].status = "in_progress"
    session.current_stage_index = 0
    session.save()

    controller = TurnController(llm_call=None)
    payload = await controller.process_turn("2단계 진행해줘", session)

    assert payload["intent"] == "stage_execute"
    assert "이전 단계" in payload["content"]
    assert session.stages[1].status != "completed"


@pytest.mark.asyncio
async def test_semi_auto_reopens_approval_for_next_stage(tmp_path, monkeypatch):
    session_dir = tmp_path / "autonomous_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
        str(session_dir),
    )

    from backend.orchestrator.autonomous.session import StageState
    from backend.orchestrator.autonomous.stage_definitions import STAGE_DEFINITIONS

    session = AutonomousSession.create(owner_id="admin-1", mode="semi_auto")
    session.task = "단타주식 매매프로그램"
    session.execution_state = "awaiting_approval"
    session.approval_state = "pending"
    session.stages = [
        StageState(stage_id=s["id"], stage_label=s["label"], status="pending")
        for s in STAGE_DEFINITIONS
    ]
    session.stages[0].status = "in_progress"
    session.current_stage_index = 0
    session.save()

    controller = TurnController(llm_call=None)
    payload = await controller.process_turn("진행해", session)

    assert payload["intent"] == "approval"
    assert session.stages[0].status == "completed"
    assert session.get_current_stage() is not None
    assert session.get_current_stage().stage_id == "STAGE-02"
    assert session.approval_state == "pending"
    assert session.execution_state == "awaiting_approval"
    assert "2단계" in payload["content"]

    controller = TurnController()
    message = (
        "ai 주식 자동매매 프로그램을 최신 기준으로 예측 할수 있는 "
        "기술 검토해서 설계 구현해줘"
    )

    assert controller.classify_intent(message) == "code_generation"


def test_stage_continue_while_pending_is_approval(pending_session):
    controller = TurnController()

    assert controller.classify_intent("1단계 구조설계 진행해줘", pending_session) == "approval"
    assert controller.classify_intent("승인합니다 진행해 주세요", pending_session) == "approval"


@pytest.mark.asyncio
async def test_approval_persists_across_saved_session(tmp_path, monkeypatch):
    session_dir = tmp_path / "autonomous_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
        str(session_dir),
    )
    import backend.orchestrator.autonomous.router as autonomous_router_module

    monkeypatch.setattr(
        autonomous_router_module,
        "_build_llm_call",
        lambda: (None, {}),
    )

    from backend.orchestrator.autonomous.surface_adapter import run_autonomous_surface_chat

    first = await run_autonomous_surface_chat(
        message="ai엔진 채팅봇 만들어줘",
        owner_id="42",
        surface="marketplace",
        mode="manual_10step",
        manual_mode=True,
    )
    assert first.diagnostics["autonomous_intent"] == "task_registered"
    session_id = first.session_id

    design = await run_autonomous_surface_chat(
        message="설계해줘",
        owner_id="42",
        surface="marketplace",
        session_id=session_id,
        mode="manual_10step",
        manual_mode=True,
    )
    assert design.conversation_stage == "approval_pending"

    second = await run_autonomous_surface_chat(
        message="승인합니다 진행해 주세요",
        owner_id="42",
        surface="marketplace",
        session_id=session_id,
        mode="manual_10step",
        manual_mode=True,
    )

    assert second.diagnostics["autonomous_intent"] == "approval"
    assert second.diagnostics["stages_completed"] == 1
    assert "2단계" in second.reply.content


@pytest.mark.asyncio
async def test_review_only_on_idle_session_routes_to_reasoner(tmp_path, monkeypatch):
    session_dir = tmp_path / "autonomous_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
        str(session_dir),
    )
    import backend.orchestrator.autonomous.router as autonomous_router_module

    monkeypatch.setattr(
        autonomous_router_module,
        "_build_llm_call",
        lambda: (None, {}),
    )

    from backend.orchestrator.autonomous.surface_adapter import run_autonomous_surface_chat

    response = await run_autonomous_surface_chat(
        message="코드 검토해줘",
        owner_id="admin-1",
        surface="admin",
        mode="manual_9step",
        manual_mode=True,
    )

    assert response.diagnostics["autonomous_intent"] == "review"
    assert "리뷰할 에이전트 결과가 없습니다" not in response.reply.content


@pytest.mark.asyncio
async def test_handle_approval_advances_semi_auto_session(tmp_path, monkeypatch):
    session_dir = tmp_path / "autonomous_sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
        str(session_dir),
    )

    session = AutonomousSession.create(owner_id="customer-1", mode="semi_auto")
    session.task = "FastAPI 헬스 API"
    session.execution_state = "awaiting_approval"
    session.approval_state = "pending"
    session.stages = []
    from backend.orchestrator.autonomous.stage_definitions import STAGE_DEFINITIONS
    from backend.orchestrator.autonomous.session import StageState

    session.stages = [
        StageState(stage_id=s["id"], stage_label=s["label"], status="pending")
        for s in STAGE_DEFINITIONS
    ]
    session.stages[0].status = "in_progress"
    session.current_stage_index = 0
    session.save()

    controller = TurnController(llm_call=None)
    payload = await controller.process_turn("진행해", session)

    assert payload["intent"] == "approval"
    assert session.stages[0].status == "completed"
    assert session.approval_state == "pending"
    assert session.execution_state == "awaiting_approval"
    assert payload["requires_approval"] is True
