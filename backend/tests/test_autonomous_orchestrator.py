"""멀티 에이전트 자율대화 오케스트레이터 테스트"""
import json

import pytest

from backend.orchestrator.autonomous.turn_controller import TurnController, STAGE_DEFINITIONS
from backend.orchestrator.autonomous.session import AutonomousSession, StageState
from backend.orchestrator.autonomous.agent_bus import AgentMessageBus, AgentMessage
from backend.orchestrator.autonomous.agents.base import AgentContext, AgentResult
from backend.orchestrator.autonomous.agents.reviewer import ReviewerAgent


class TestAgentMessageBus:
    @pytest.mark.asyncio
    async def test_send_and_log(self):
        bus = AgentMessageBus()
        msg = AgentMessage(
            from_agent="reasoner",
            to_agent="planner",
            msg_type="response",
            content="분석 완료",
            run_id="test-run-1",
        )
        await bus.send(msg)
        log = bus.get_message_log("test-run-1")
        assert len(log) == 1
        assert log[0]["from_agent"] == "reasoner"
        assert log[0]["content"] == "분석 완료"

    @pytest.mark.asyncio
    async def test_listener_receives_messages(self):
        bus = AgentMessageBus()
        received = []
        bus.subscribe("planner", lambda m: received.append(m))

        await bus.send(AgentMessage(
            from_agent="reasoner",
            to_agent="planner",
            msg_type="response",
            content="테스트",
            run_id="test-run-2",
        ))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_broadcast_reaches_all_listeners(self):
        bus = AgentMessageBus()
        received = []
        bus.subscribe("*", lambda m: received.append(m))
        await bus.broadcast("controller", "전체 알림", "test-run-3")
        assert len(received) == 1
        assert received[0].msg_type == "broadcast"

    def test_clear_run(self):
        bus = AgentMessageBus()
        bus._message_log.append(AgentMessage(
            from_agent="a", to_agent="b", msg_type="x", content="1", run_id="r1",
        ))
        bus._message_log.append(AgentMessage(
            from_agent="a", to_agent="b", msg_type="x", content="2", run_id="r2",
        ))
        bus.clear_run("r1")
        assert len(bus.get_message_log("r1")) == 0
        assert len(bus.get_message_log("r2")) == 1


class TestAutonomousSession:
    def test_create_and_defaults(self):
        session = AutonomousSession.create(owner_id="user1", mode="semi_auto")
        assert session.owner_id == "user1"
        assert session.mode == "semi_auto"
        assert session.execution_state == "idle"

    def test_add_messages(self):
        session = AutonomousSession.create(owner_id="user1")
        session.add_user_message("안녕하세요")
        session.add_agent_message("reasoner", "분석 시작합니다")
        session.add_system_message("시스템 알림")
        assert len(session.conversation) == 3
        assert session.conversation[0].role == "user"
        assert session.conversation[1].agent_id == "reasoner"

    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
            str(tmp_path),
        )
        session = AutonomousSession.create(owner_id="user1", project_name="test-project")
        session.add_user_message("테스트")
        session.save()

        loaded = AutonomousSession.load(session.session_id, "user1")
        assert loaded is not None
        assert loaded.project_name == "test-project"
        assert len(loaded.conversation) == 1

    def test_save_and_load_restores_execution_state(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
            str(tmp_path),
        )
        session = AutonomousSession.create(owner_id="user1")
        session.agent_results.append(AgentResult(agent="planner", status="success", output="계획"))
        session.stages = [
            StageState(stage_id="S1", stage_label="1단계", status="completed"),
            StageState(stage_id="S2", stage_label="2단계", status="in_progress", revision_count=1),
        ]
        session.current_stage_index = 1
        session.execution_state = "awaiting_approval"
        session.approval_state = "pending"
        session.pending_approval_data = {"pipeline": ["planner"]}
        session.save()

        loaded = AutonomousSession.load(session.session_id, "user1")
        assert loaded is not None
        assert loaded.agent_results[0].agent == "planner"
        assert loaded.stages[1].stage_id == "S2"
        assert loaded.stages[1].revision_count == 1
        assert loaded.current_stage_index == 1
        assert loaded.execution_state == "awaiting_approval"
        assert loaded.pending_approval_data == {"pipeline": ["planner"]}

    def test_load_rejects_other_user(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
            str(tmp_path),
        )
        session = AutonomousSession.create(owner_id="user1")
        session.save()

        loaded = AutonomousSession.load(session.session_id, "user2")
        assert loaded is None

    def test_load_rejects_path_traversal(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
            str(tmp_path / "sessions"),
        )
        outside = tmp_path / "escape.json"
        outside.write_text(
            json.dumps({
                "session_id": "escape",
                "owner_id": "user1",
                "mode": "semi_auto",
            }),
            encoding="utf-8",
        )

        loaded = AutonomousSession.load("../escape", "user1")
        assert loaded is None

    def test_stage_management(self):
        session = AutonomousSession.create(owner_id="user1")
        session.stages = [
            StageState(stage_id="S1", stage_label="1단계", status="in_progress"),
            StageState(stage_id="S2", stage_label="2단계", status="pending"),
        ]
        assert session.get_current_stage().stage_id == "S1"
        next_stage = session.advance_stage()
        assert next_stage.stage_id == "S2"

    def test_requires_approval(self):
        session = AutonomousSession.create(owner_id="u", mode="advisory")
        assert session.requires_approval() is False
        session.mode = "semi_auto"
        assert session.requires_approval() is True
        session.mode = "full_auto"
        assert session.requires_approval() is False


class TestTurnController:
    def test_classify_intent(self):
        controller = TurnController()
        assert controller.classify_intent("안녕하세요") == "greeting"
        assert controller.classify_intent("FastAPI로 블로그 만들어줘") == "code_generation"
        assert controller.classify_intent("현재 상태 알려줘") == "status"
        assert controller.classify_intent("승인합니다") == "approval"
        assert controller.classify_intent("코드 리뷰해줘") == "review"
        assert controller.classify_intent("함수 이름을 수정해줘") == "revision"

    def test_route_to_agents_greeting(self):
        controller = TurnController()
        session = AutonomousSession.create(owner_id="u")
        agents = controller.route_to_agents("greeting", session)
        assert agents == []

    def test_route_to_agents_code_generation_idle(self):
        controller = TurnController()
        session = AutonomousSession.create(owner_id="u")
        agents = controller.route_to_agents("code_generation", session)
        assert "reasoner" in agents
        assert "planner" in agents

    def test_route_to_agents_question(self):
        controller = TurnController()
        session = AutonomousSession.create(owner_id="u")
        agents = controller.route_to_agents("question", session)
        assert agents == ["reasoner"]

    @pytest.mark.asyncio
    async def test_process_greeting(self):
        controller = TurnController()
        session = AutonomousSession.create(owner_id="user1", mode="semi_auto")
        result = await controller.process_turn("안녕하세요", session)
        assert result["intent"] == "greeting"
        assert "멀티 에이전트" in result["content"]
        assert result["session_id"] == session.session_id

    @pytest.mark.asyncio
    async def test_process_greeting_persists_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
            str(tmp_path),
        )
        controller = TurnController()
        session = AutonomousSession.create(owner_id="user1", mode="semi_auto")

        await controller.process_turn("안녕하세요", session)

        loaded = AutonomousSession.load(session.session_id, "user1")
        assert loaded is not None
        assert loaded.conversation[-1].content.startswith("안녕하세요")

    @pytest.mark.asyncio
    async def test_process_status(self):
        controller = TurnController()
        session = AutonomousSession.create(owner_id="user1")
        result = await controller.process_turn("현재 상태 알려줘", session)
        assert result["intent"] == "status"
        assert "세션" in result["content"]

    @pytest.mark.asyncio
    async def test_process_code_generation_creates_stages(self):
        controller = TurnController()
        session = AutonomousSession.create(owner_id="user1", mode="advisory")
        result = await controller.process_turn("FastAPI로 블로그 만들어줘", session)
        assert result["intent"] == "code_generation"
        assert session.execution_state == "planning"
        assert len(session.stages) == len(STAGE_DEFINITIONS)
        assert session.task == "FastAPI로 블로그 만들어줘"

    @pytest.mark.asyncio
    async def test_process_code_generation_semi_auto_requires_approval(self):
        controller = TurnController()
        session = AutonomousSession.create(owner_id="user1", mode="semi_auto")
        result = await controller.process_turn("FastAPI로 블로그 만들어줘", session)
        assert result["requires_approval"] is True
        assert session.approval_state == "pending"

    @pytest.mark.asyncio
    async def test_process_code_generation_full_auto_executes_coder(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
            str(tmp_path),
        )
        controller = TurnController()
        session = AutonomousSession.create(owner_id="user1", mode="full_auto")
        called = False

        async def fake_execute_coder_pipeline(active_session):
            nonlocal called
            called = True
            active_session.execution_state = "completed"
            result = AgentResult(agent="coder", status="success", output="생성 완료")
            active_session.agent_results.append(result)
            return [result]

        controller._execute_coder_pipeline = fake_execute_coder_pipeline

        result = await controller.process_turn("FastAPI로 블로그 만들어줘", session)
        assert called is True
        assert result["requires_approval"] is False
        assert any(r["agent"] == "coder" for r in result["agent_results"])
        assert session.execution_state == "completed"

    @pytest.mark.asyncio
    async def test_process_approval_without_pending(self):
        controller = TurnController()
        session = AutonomousSession.create(owner_id="user1")
        result = await controller.process_turn("승인", session)
        assert "승인 대기 중인 작업이 없습니다" in result["content"]

    @pytest.mark.asyncio
    async def test_agent_results_in_conversation(self):
        controller = TurnController()
        session = AutonomousSession.create(owner_id="user1", mode="advisory")
        await controller.process_turn("이 프로젝트 구조를 분석해줘", session)
        agent_turns = [t for t in session.conversation if t.role == "agent"]
        assert len(agent_turns) >= 1

    @pytest.mark.asyncio
    async def test_message_bus_records_activity(self):
        controller = TurnController()
        session = AutonomousSession.create(owner_id="user1", mode="advisory")
        await controller.process_turn("블로그 API를 만들어줘", session)
        log = controller.bus.get_message_log(session.session_id)
        assert len(log) >= 1

    def test_stage_definitions_complete(self):
        assert len(STAGE_DEFINITIONS) == 11
        assert STAGE_DEFINITIONS[0]["id"] == "STAGE-01"
        assert STAGE_DEFINITIONS[-1]["id"] == "STAGE-10"
        for stage in STAGE_DEFINITIONS:
            assert "id" in stage
            assert "label" in stage
            assert "agents" in stage
            assert len(stage["agents"]) >= 1


class TestReviewerAgent:
    @pytest.mark.asyncio
    async def test_korean_no_issue_review_does_not_request_revision(self):
        async def llm_call(**kwargs):
            return "## 검토 결과\n- 발견된 문제 없음\n\n## 개선 제안\n- 없습니다."

        reviewer = ReviewerAgent(llm_call=llm_call)
        context = AgentContext(
            run_id="run1",
            task="테스트",
            project_name="project",
            validation_profile="python_fastapi",
            previous_results=[AgentResult(agent="coder", status="success", output="완료")],
        )

        result = await reviewer.execute(context)
        assert result.status == "success"
        assert result.artifacts["needs_revision"] is False
