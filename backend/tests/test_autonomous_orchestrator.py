"""멀티 에이전트 자율대화 오케스트레이터 테스트"""
import pytest

from backend.orchestrator.autonomous.turn_controller import TurnController, STAGE_DEFINITIONS
from backend.orchestrator.autonomous.session import AutonomousSession
from backend.orchestrator.autonomous.agent_bus import AgentMessageBus, AgentMessage
from backend.orchestrator.autonomous.agents.base import AgentContext, AgentResult


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

    def test_save_and_load_preserves_execution_state(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
            str(tmp_path),
        )
        from backend.orchestrator.autonomous.session import StageState

        session = AutonomousSession.create(owner_id="user1", project_name="test-project")
        session.task = "FastAPI로 블로그 만들어줘"
        session.execution_state = "awaiting_approval"
        session.approval_state = "pending"
        session.pending_approval_data = {
            "pipeline": ["reasoner", "planner"],
            "results_summary": [{"agent": "planner", "status": "success"}],
        }
        session.output_dir = str(tmp_path / "out")
        session.model_routes = {"default": "test-model"}
        session.extra = {"source": "regression-test"}
        session.stages = [
            StageState(
                stage_id="STAGE-01",
                stage_label="1단계",
                status="in_progress",
                agent_results=[{"agent": "planner", "status": "success"}],
                revision_count=1,
            )
        ]
        session.agent_results = [
            AgentResult(
                agent="planner",
                status="success",
                output="계획 완료",
                artifacts={"plan_type": "implementation_plan"},
                next_agents=["coder"],
                elapsed_ms=12.5,
                metadata={"route": "planner"},
            )
        ]
        session.save()

        loaded = AutonomousSession.load(session.session_id, "user1")
        assert loaded is not None
        assert loaded.execution_state == "awaiting_approval"
        assert loaded.approval_state == "pending"
        assert loaded.pending_approval_data == session.pending_approval_data
        assert loaded.output_dir == session.output_dir
        assert loaded.model_routes == {"default": "test-model"}
        assert loaded.extra == {"source": "regression-test"}
        assert len(loaded.stages) == 1
        assert loaded.stages[0].stage_id == "STAGE-01"
        assert loaded.stages[0].revision_count == 1
        assert loaded.stages[0].agent_results == [{"agent": "planner", "status": "success"}]
        assert len(loaded.agent_results) == 1
        assert loaded.agent_results[0].agent == "planner"
        assert loaded.agent_results[0].next_agents == ["coder"]
        assert loaded.agent_results[0].metadata == {"route": "planner"}

    def test_load_rejects_other_user(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.orchestrator.autonomous.session.AUTONOMOUS_SESSION_DIR",
            str(tmp_path),
        )
        session = AutonomousSession.create(owner_id="user1")
        session.save()

        loaded = AutonomousSession.load(session.session_id, "user2")
        assert loaded is None

    def test_stage_management(self):
        session = AutonomousSession.create(owner_id="user1")
        from backend.orchestrator.autonomous.session import StageState
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


class TestValidatorAgent:
    """ValidatorAgent 단위 테스트 — PR #67 버그 수정 회귀 검증"""

    @pytest.mark.asyncio
    async def test_uses_last_coder_result_not_first(self, tmp_path):
        """validator는 첫 번째가 아닌 가장 최근 코더 결과를 사용해야 한다."""
        from backend.orchestrator.autonomous.agents.validator import ValidatorAgent

        first_out = tmp_path / "first"
        first_out.mkdir()
        (first_out / "main.py").write_text("def bad(:\n    pass\n")  # 문법 오류

        second_out = tmp_path / "second"
        second_out.mkdir()
        (second_out / "main.py").write_text("def hello():\n    return 'world'\n")

        ctx = AgentContext(
            run_id="r",
            task="t",
            project_name="p",
            validation_profile="default",
            previous_results=[
                AgentResult(
                    agent="coder",
                    status="success",
                    output="1차",
                    artifacts={"written_files": ["main.py"], "output_dir": str(first_out)},
                ),
                AgentResult(
                    agent="coder",
                    status="success",
                    output="2차 수정",
                    artifacts={"written_files": ["main.py"], "output_dir": str(second_out)},
                ),
            ],
        )
        result = await ValidatorAgent()._run(ctx)
        assert result.artifacts["passed"] is True, (
            f"최신 코더 결과를 사용하지 않았습니다. errors={result.errors}"
        )

    @pytest.mark.asyncio
    async def test_no_coder_result_passes(self):
        from backend.orchestrator.autonomous.agents.validator import ValidatorAgent

        ctx = AgentContext(
            run_id="r", task="t", project_name="p", validation_profile="default"
        )
        result = await ValidatorAgent()._run(ctx)
        assert result.status == "success"
        assert result.artifacts["passed"] is True

    @pytest.mark.asyncio
    async def test_compile_error_triggers_revision(self, tmp_path):
        from backend.orchestrator.autonomous.agents.validator import ValidatorAgent

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        (out_dir / "main.py").write_text("def bad(:\n    pass\n")

        ctx = AgentContext(
            run_id="r",
            task="t",
            project_name="p",
            validation_profile="default",
            previous_results=[
                AgentResult(
                    agent="coder",
                    status="success",
                    output="코드",
                    artifacts={"written_files": ["main.py"], "output_dir": str(out_dir)},
                )
            ],
        )
        result = await ValidatorAgent()._run(ctx)
        assert result.artifacts["passed"] is False
        assert result.status == "needs_revision"
        assert "coder" in result.next_agents
