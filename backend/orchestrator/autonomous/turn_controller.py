"""멀티 에이전트 자율대화 턴 컨트롤러

대화 흐름을 관리하고, 적절한 에이전트를 선택하며,
실행 여부를 결정하는 핵심 컨트롤러.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from typing import Any, Callable, Dict, List, Optional

from .agent_bus import AgentMessageBus, AgentMessage
from .agents.base import AgentContext, AgentResult, BaseAgent
from .agents.reasoner import ReasonerAgent
from .agents.planner import PlannerAgent
from .agents.reviewer import ReviewerAgent
from .agents.coder import CoderAgent
from .agents.validator import ValidatorAgent
from .session import AutonomousSession, StageState
from .stage_commands import (
    StageCommand,
    format_stage_execute_hint,
    format_stage_progress_hint,
    parse_stage_command,
    stage_number_for_index,
)
from .stage_definitions import STAGE_DEFINITIONS

logger = logging.getLogger(__name__)

MAX_REVISION_ATTEMPTS = 3


def _max_full_auto_stages_per_turn() -> int:
    """full_auto 턴당 STAGE 순회 상한 (기본: 11단계 전체)."""
    default = str(len(STAGE_DEFINITIONS))
    raw = os.getenv("AUTONOMOUS_MAX_STAGES_PER_TURN", default).strip()
    try:
        parsed = int(raw)
    except ValueError:
        parsed = len(STAGE_DEFINITIONS)
    return max(1, min(parsed, len(STAGE_DEFINITIONS)))

APPROVAL_PATTERNS = [
    r"승인",
    r"진행\s*해",
    r"진행\s*해\s*주",
    r"진행\s*부탁",
    r"^네[\s,.]",
    r"^좋아\b",
    r"^approve\b",
    r"^proceed\b",
    r"^ok\b",
    r"^go\b",
]

STAGE_APPROVAL_PATTERNS = [
    r"\d+\s*단계",
    r"단계.*진행",
]

REJECTION_PATTERNS = [
    r"^거절",
    r"^반려",
    r"^취소",
    r"^reject\b",
    r"^cancel\b",
    r"^no\b",
    r"^아니\b",
]

CODE_GENERATION_PATTERNS = [
    r"(만들어|생성|구현|개발|빌드|build|create|generate|implement)",
    r"설계\s*구현",
    r"설계\s*해",
    r"프로그램",
    r"자동매매|트레이딩|bot|봇|채팅봇",
    r"매매\s*프로그램",
]

EXECUTION_REQUEST_PATTERNS = [
    r"실행",
    r"실해",
    r"설계\s*대로",
    r"그대로",
    r"바로\s*(만들|구현|진행|실행)",
    r"진행\s*해",
    r"시작\s*해",
    r"적용\s*해",
    r"반영\s*해",
]

INTENT_PATTERNS_ORDERED = [
    ("greeting", r"^(안녕|반갑|hello|hi[ !]|hi$)"),
    ("rejection", r"^(거절|반려|취소|reject|cancel|no$|아니)"),
    ("approval", r"^(승인|좋아|진행해|approve|ok$|proceed|go$)"),
    (
        "status",
        r"(진행\s*(상황|현황|상태)|현재\s*(상태|단계|몇\s*단계)|몇\s*단계|단계\s*(가\s*)?(어디|몇)|status|progress)",
    ),
    ("revision", r"(수정|변경|고쳐|바꿔|fix|change|modify|revise)"),
    ("code_generation", r"(만들어|생성|구현|개발|빌드|build|create|generate|implement)"),
    ("review", r"(검토|리뷰|review|점검)"),
    ("question", r"(\?|무엇|어떻게|왜|뭐|알려|설명|what|how|why|explain)"),
]


class TurnController:
    """멀티 에이전트 자율대화 턴 컨트롤러"""

    def __init__(self, llm_call: Optional[Callable] = None) -> None:
        self.bus = AgentMessageBus()
        self._llm_call = llm_call

        self.agents: Dict[str, BaseAgent] = {
            "reasoner": ReasonerAgent(llm_call=llm_call, bus=self.bus),
            "planner": PlannerAgent(llm_call=llm_call, bus=self.bus),
            "reviewer": ReviewerAgent(llm_call=llm_call, bus=self.bus),
            "coder": CoderAgent(llm_call=llm_call, bus=self.bus),
            "validator": ValidatorAgent(llm_call=llm_call, bus=self.bus),
        }
        self._bus_inbox: Dict[str, List[AgentMessage]] = {agent_id: [] for agent_id in self.agents}
        self._wire_agent_bus_subscriptions()

    def _wire_agent_bus_subscriptions(self) -> None:
        for agent_id in self.agents:
            def _make_handler(aid: str):
                def _handler(message: AgentMessage) -> None:
                    self._bus_inbox.setdefault(aid, []).append(message)
                return _handler
            self.bus.subscribe(agent_id, _make_handler(agent_id))

    async def _run_agent_with_bus(
        self,
        agent_id: str,
        context: AgentContext,
        session: AutonomousSession,
        task_message: str,
    ) -> AgentResult:
        await self.bus.send(AgentMessage(
            from_agent="controller",
            to_agent=agent_id,
            msg_type="request",
            content=task_message[:500],
            run_id=session.session_id,
        ))
        context.extra["bus_inbox"] = [
            message.to_dict() for message in self._bus_inbox.get(agent_id, [])
        ]
        agent = self.agents.get(agent_id)
        if not agent:
            return AgentResult(agent=agent_id, status="error", output="", errors=["agent not found"])
        result = await agent.execute(context)
        await self.bus.send(AgentMessage(
            from_agent=agent_id,
            to_agent="controller",
            msg_type="response",
            content=result.output[:500],
            run_id=session.session_id,
            artifacts=result.artifacts,
        ))
        for next_id in result.next_agents:
            await self.bus.send(AgentMessage(
                from_agent=agent_id,
                to_agent=next_id,
                msg_type="handoff",
                content=result.output[:300],
                run_id=session.session_id,
                artifacts={"from_status": result.status},
            ))
        return result

    def _matches_any(self, message: str, patterns: List[str]) -> bool:
        text = message.strip()
        if not text:
            return False
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _awaiting_user_approval(self, session: AutonomousSession) -> bool:
        return (
            session.approval_state == "pending"
            or session.execution_state == "awaiting_approval"
        )

    def _looks_like_execution_request(self, message: str) -> bool:
        return self._matches_any(message, EXECUTION_REQUEST_PATTERNS)

    def _has_design_baseline(self, session: AutonomousSession) -> bool:
        return any(result.agent == "reasoner" and result.status in {"success", "stub"} for result in session.agent_results)

    def _resolve_approval_intent(self, message: str, session: AutonomousSession) -> Optional[str]:
        text = message.strip()
        if not text or not self._awaiting_user_approval(session):
            return None
        if self._matches_any(text, APPROVAL_PATTERNS):
            return "approval"
        if self._looks_like_execution_request(text):
            return "approval"
        if self._matches_any(text, STAGE_APPROVAL_PATTERNS) and re.search(r"진행", text, re.IGNORECASE):
            return "approval"
        return None

    def _ensure_build_session(self, session: AutonomousSession, message: str) -> None:
        if not session.task:
            session.task = message
        if not session.stages:
            session.execution_state = "planning"
            self._initialize_stages(session)
        elif session.execution_state == "idle":
            session.execution_state = "planning"

    def _prepare_next_semi_auto_stage_gate(self, session: AutonomousSession) -> None:
        if session.mode != "semi_auto" or session.execution_state == "failed":
            return
        if session.current_stage_index >= len(session.stages):
            session.execution_state = "completed"
            session.approval_state = "approved"
            session.pending_approval_data = None
            session.extra["stage_command_hint"] = "11단계 파이프라인이 모두 완료되었습니다."
            session.add_system_message("✅ 11단계 파이프라인이 모두 완료되었습니다.")
            return
        next_stage = session.get_current_stage()
        if next_stage and session.execution_state != "completed":
            session.approval_state = "pending"
            session.execution_state = "awaiting_approval"
            session.add_system_message(
                f"{next_stage.stage_label} 코드 생성 승인 대기 중입니다. "
                f"'승인' 또는 '진행해'라고 입력하세요."
            )
        elif session.execution_state == "completed":
            session.approval_state = "approved"

    def _should_force_approval(self, session: AutonomousSession, message: str, intent: str) -> bool:
        if not self._awaiting_user_approval(session):
            return False
        if intent == "approval" or self._resolve_approval_intent(message, session):
            return True
        if intent == "code_generation" or self._looks_like_execution_request(message):
            return True
        return False

    def classify_intent(self, message: str, session: Optional[AutonomousSession] = None) -> str:
        text = message.strip()
        lowered = text.lower()

        if session:
            forced = self._resolve_approval_intent(text, session)
            if forced:
                return forced
            if session.approval_state == "pending" and self._matches_any(text, REJECTION_PATTERNS):
                return "rejection"

        if self._matches_any(text, CODE_GENERATION_PATTERNS):
            return "code_generation"

        if session and self._looks_like_execution_request(text):
            if self._awaiting_user_approval(session) or self._has_design_baseline(session) or session.task:
                return "code_generation"

        for intent, pattern in INTENT_PATTERNS_ORDERED:
            if re.search(pattern, lowered, re.IGNORECASE):
                return intent
        if len(text) > 50:
            return "code_generation"
        return "question"

    def route_to_agents(self, intent: str, session: AutonomousSession) -> List[str]:
        if intent == "greeting":
            return []
        if intent == "question":
            return ["reasoner"]
        if intent == "review":
            if not session.agent_results:
                return ["reasoner"]
            return ["reviewer"]
        if intent == "status":
            return []
        if intent == "approval":
            return []
        if intent == "revision":
            revision_target = self._find_revision_target(session)
            return [revision_target] if revision_target else ["reasoner"]

        if intent == "code_generation":
            if session.execution_state == "idle" and self._has_design_baseline(session) and not session.stages:
                return ["planner"]
            if session.execution_state == "idle":
                return ["reasoner", "planner"]
            stage = session.get_current_stage()
            if stage:
                stage_def = next((s for s in STAGE_DEFINITIONS if s["id"] == stage.stage_id), None)
                if stage_def:
                    return stage_def["agents"]
            return ["reasoner", "planner", "coder", "validator"]

        return ["reasoner"]

    def _focus_stage(self, session: AutonomousSession, stage_index: int) -> None:
        """현재 단계 포커스 — 이전 단계를 임의로 completed로 표시하지 않음."""
        if not session.stages:
            self._initialize_stages(session)
        bounded = max(0, min(stage_index, len(session.stages) - 1))
        for index, stage in enumerate(session.stages):
            if index == bounded:
                if stage.status != "completed":
                    stage.status = "in_progress"
            elif index > bounded and stage.status == "in_progress":
                stage.status = "pending"
        session.current_stage_index = bounded
        session.execution_state = "planning"

    def _can_execute_stage(self, session: AutonomousSession, stage_index: int) -> bool:
        if stage_index <= 0:
            return True
        if not session.stages:
            return stage_index == 0
        previous = session.stages[stage_index - 1]
        return previous.status == "completed"

    def _planning_agents_for_stage(self, stage_index: int) -> List[str]:
        stage_def = STAGE_DEFINITIONS[stage_index]
        if stage_index == 0:
            return ["reasoner", "planner"]
        return [
            agent
            for agent in stage_def["agents"]
            if agent not in {"coder", "validator", "reviewer"}
        ]

    async def _run_planning_for_stage(
        self,
        session: AutonomousSession,
        message: str,
        agent_ids: List[str],
    ) -> List[AgentResult]:
        results: List[AgentResult] = []
        context = self._build_context(session, message)
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if not agent:
                continue
            context.previous_results = list(session.agent_results)
            result = await self._run_agent_with_bus(agent_id, context, session, message)
            results.append(result)
            session.agent_results.append(result)
            session.add_agent_message(agent_id, result.output, result.artifacts)
            if result.status == "error":
                break
        return results

    async def _handle_stage_command(
        self,
        command: StageCommand,
        message: str,
        session: AutonomousSession,
    ) -> Dict[str, Any]:
        self._ensure_build_session(session, session.task or message)
        if command.action != "discuss":
            self._focus_stage(session, command.stage_index)
        session.extra["active_stage_command"] = command.action
        session.extra["active_stage_number"] = command.stage_number

        if command.action == "design":
            agents = self._planning_agents_for_stage(command.stage_index)
            results = await self._run_planning_for_stage(session, message, agents)
            session.approval_state = "pending"
            session.execution_state = "awaiting_approval"
            session.pending_approval_data = {
                "pipeline": agents,
                "stage_command": "design",
                "stage_index": command.stage_index,
            }
            session.extra["stage_command_hint"] = format_stage_execute_hint(command.stage_index)
            combined = self._combine_results(results, session)
            session.save()
            return self._build_response(
                session,
                combined,
                intent="stage_design",
                agent_results=results,
            )

        if command.action == "discuss":
            context = self._build_context(session, message)
            context.stage_id = command.stage_id
            context.stage_label = command.stage_label
            context.extra["collaboration_mode"] = True
            enriched = (
                f"{message}\n\n"
                f"[협업 모드 · {command.stage_label}]\n"
                "프로젝트 맥락을 유지한 채 질문에 답하고, 아이디어·신기술·개선안을 제안하세요. "
                "구현이 필요하면 어떤 파일/모듈을 바꿀지 구체적으로 적어 주세요."
            )
            results: List[AgentResult] = []
            for agent_id in ("reasoner", "planner"):
                context.previous_results = list(session.agent_results)
                result = await self._run_agent_with_bus(agent_id, context, session, enriched)
                results.append(result)
                session.agent_results.append(result)
                session.add_agent_message(agent_id, result.output, result.artifacts)
                if result.status == "error":
                    break
            session.execution_state = "executing"
            session.approval_state = "none"
            session.extra["stage_command_hint"] = (
                f"구현까지 진행하려면 '{command.stage_number:g}단계 진행해줘'라고 입력하세요. "
                f"추가 질문은 그대로 대화하시면 됩니다."
            )
            combined = self._combine_results(results, session)
            session.save()
            return self._build_response(
                session,
                combined,
                intent="stage_discuss",
                agent_results=results,
            )

        # execute
        if not self._can_execute_stage(session, command.stage_index):
            reply = (
                f"{command.stage_label} 실행 전에 이전 단계를 먼저 완료해야 합니다. "
                f"'{stage_number_for_index(command.stage_index - 1):g}단계 진행해줘'를 먼저 실행하세요."
            )
            session.add_system_message(reply)
            session.save()
            return self._build_response(session, reply, intent="stage_execute")

        if session.approval_state == "pending" and session.current_stage_index == command.stage_index:
            session.approval_state = "approved"
            session.execution_state = "executing"
            session.pending_approval_data = None
            session.add_system_message(f"{command.stage_label} 코드 생성을 시작합니다.")
            exec_results = await self._execute_current_stage(session)
            self._prepare_next_semi_auto_stage_gate(session)
            session.extra["stage_command_hint"] = format_stage_progress_hint(command.stage_index)
            combined = self._combine_results(exec_results, session)
            session.save()
            return self._build_response(
                session,
                combined,
                intent="approval",
                agent_results=exec_results,
            )

        target = (
            session.stages[command.stage_index]
            if session.stages and 0 <= command.stage_index < len(session.stages)
            else None
        )
        if target and target.status == "completed":
            hint = format_stage_progress_hint(command.stage_index)
            reply = f"{command.stage_label}는 이미 완료되었습니다. {hint}"
            session.extra["stage_command_hint"] = hint
            session.add_system_message(reply)
            session.save()
            return self._build_response(session, reply, intent="stage_execute")

        planning_agents = self._planning_agents_for_stage(command.stage_index)
        results: List[AgentResult] = []
        if planning_agents:
            results = await self._run_planning_for_stage(session, message, planning_agents)

        session.approval_state = "approved"
        session.execution_state = "executing"
        session.pending_approval_data = None
        session.add_system_message(f"{command.stage_label} 코드 생성을 시작합니다.")

        exec_results = await self._execute_current_stage(session)
        results.extend(exec_results)
        self._prepare_next_semi_auto_stage_gate(session)
        session.extra["stage_command_hint"] = format_stage_progress_hint(command.stage_index)
        combined = self._combine_results(results, session)
        session.save()
        return self._build_response(
            session,
            combined,
            intent="stage_execute",
            agent_results=results,
        )

    async def process_turn(self, message: str, session: AutonomousSession) -> Dict[str, Any]:
        session.extra["llm_connected"] = self._llm_call is not None
        session.add_user_message(message)

        stage_command = parse_stage_command(message, session)
        if stage_command:
            return await self._handle_stage_command(stage_command, message, session)

        intent = self.classify_intent(message, session)
        if intent == "status" and self._resolve_approval_intent(message, session):
            intent = "approval"

        if self._should_force_approval(session, message, intent):
            return await self._handle_approval(session)

        if intent == "greeting":
            reply = self._build_greeting(session)
            session.add_system_message(reply)
            return self._build_response(session, reply, intent=intent)

        if intent == "status":
            reply = self._build_status(session)
            session.add_system_message(reply)
            session.save()
            return self._build_response(session, reply, intent=intent)

        if intent == "approval":
            return await self._handle_approval(session)

        if intent == "rejection":
            return await self._handle_rejection(session)

        if (
            intent == "code_generation"
            and session.mode == "semi_auto"
            and session.execution_state == "idle"
            and not session.agent_results
        ):
            return await self._register_task_only(message, session)

        if not session.task and intent == "code_generation":
            self._ensure_build_session(session, message)
        elif intent == "code_generation":
            self._ensure_build_session(session, message)

        agent_pipeline = self.route_to_agents(intent, session)
        if not agent_pipeline:
            reply = "요청을 처리할 수 있는 에이전트를 결정하지 못했습니다. 더 구체적으로 말씀해 주세요."
            session.add_system_message(reply)
            return self._build_response(session, reply, intent=intent)

        context = self._build_context(session, message)
        results: List[AgentResult] = []

        for agent_id in agent_pipeline:
            context.previous_results = results.copy()
            result = await self._run_agent_with_bus(agent_id, context, session, message)
            results.append(result)
            session.agent_results.append(result)
            session.add_agent_message(agent_id, result.output, result.artifacts)

            if result.status == "needs_revision" and agent_id != "coder":
                revision_result = await self._handle_auto_revision(agent_id, result, context, session)
                if revision_result:
                    results.append(revision_result)

            if result.status == "error":
                break

        if session.mode != "advisory" and intent == "code_generation":
            if session.requires_approval():
                session.approval_state = "pending"
                session.execution_state = "awaiting_approval"
                session.pending_approval_data = {
                    "pipeline": agent_pipeline,
                    "results_summary": [{"agent": r.agent, "status": r.status} for r in results],
                }
            else:
                session.approval_state = "approved"
                session.execution_state = "executing"
                session.add_system_message("full_auto 모드: 승인 없이 코드 생성을 시작합니다.")
                exec_results = await self._execute_code_pipeline(session, continue_stages=True)
                results.extend(exec_results)

        combined_output = self._combine_results(results, session)
        session.save()
        return self._build_response(session, combined_output, intent=intent, agent_results=results)

    async def _handle_auto_revision(
        self,
        reviewing_agent_id: str,
        review_result: AgentResult,
        context: AgentContext,
        session: AutonomousSession,
    ) -> Optional[AgentResult]:
        stage = session.get_current_stage()
        if stage and stage.revision_count >= MAX_REVISION_ATTEMPTS:
            session.add_system_message(f"최대 수정 횟수({MAX_REVISION_ATTEMPTS})에 도달했습니다. 사용자 개입이 필요합니다.")
            return None

        target_agents = review_result.next_agents
        if not target_agents:
            return None

        target_id = target_agents[0]
        target_agent = self.agents.get(target_id)
        if not target_agent:
            return None

        feedback = review_result.output
        revised = await target_agent.revise(context, feedback)
        session.agent_results.append(revised)
        session.add_agent_message(target_id, f"[수정됨] {revised.output}", revised.artifacts)

        if stage:
            stage.revision_count += 1

        await self.bus.send(AgentMessage(
            from_agent=target_id,
            to_agent="controller",
            msg_type="revision",
            content=f"Revision by {target_id} after {reviewing_agent_id} review",
            run_id=session.session_id,
        ))

        return revised

    async def _handle_approval(self, session: AutonomousSession) -> Dict[str, Any]:
        if session.approval_state != "pending":
            reply = "현재 승인 대기 중인 작업이 없습니다."
            session.add_system_message(reply)
            return self._build_response(session, reply, intent="approval")

        session.approval_state = "approved"
        session.execution_state = "executing"
        session.pending_approval_data = None
        session.add_system_message("승인되었습니다. 코드 생성을 시작합니다.")

        exec_results = await self._execute_code_pipeline(
            session,
            continue_stages=session.mode == "full_auto",
        )
        self._prepare_next_semi_auto_stage_gate(session)
        combined = self._combine_results(session.agent_results[-max(5, len(exec_results)):], session)
        session.save()
        return self._build_response(
            session,
            combined,
            intent="approval",
            agent_results=exec_results or session.agent_results[-5:],
        )

    async def _handle_rejection(self, session: AutonomousSession) -> Dict[str, Any]:
        if session.approval_state != "pending":
            reply = "현재 거절할 승인 대기 작업이 없습니다."
            session.add_system_message(reply)
            return self._build_response(session, reply, intent="rejection")

        session.approval_state = "rejected"
        session.execution_state = "planning"
        session.pending_approval_data = None
        session.add_system_message("승인이 거절되었습니다. 설계를 다시 검토합니다.")

        context = self._build_context(session, session.task)
        context.previous_results = list(session.agent_results)
        replan_results: List[AgentResult] = []

        for agent_id in ("reasoner", "planner"):
            agent = self.agents.get(agent_id)
            if not agent:
                continue
            context.previous_results = list(session.agent_results)
            result = await agent.execute(context)
            replan_results.append(result)
            session.agent_results.append(result)
            session.add_agent_message(agent_id, result.output, result.artifacts)
            if result.status == "error":
                break

        if session.mode == "semi_auto" and replan_results and replan_results[-1].status != "error":
            session.approval_state = "pending"
            session.execution_state = "awaiting_approval"
            session.pending_approval_data = {
                "pipeline": ["reasoner", "planner"],
                "results_summary": [{"agent": r.agent, "status": r.status} for r in replan_results],
                "replan": True,
            }
        elif session.mode == "full_auto" and replan_results and replan_results[-1].status != "error":
            session.approval_state = "approved"
            session.execution_state = "executing"
            exec_results = await self._execute_code_pipeline(session, continue_stages=True)
            replan_results.extend(exec_results)

        combined = self._combine_results(replan_results, session)
        session.save()
        return self._build_response(session, combined, intent="rejection", agent_results=replan_results)

    async def _execute_code_pipeline(
        self,
        session: AutonomousSession,
        *,
        continue_stages: bool = False,
    ) -> List[AgentResult]:
        """현재 스테이지 coder→validator 실행. full_auto면 다음 스테이지까지 순회."""
        collected: List[AgentResult] = []
        stage_cycles = 0

        while True:
            stage_results = await self._execute_current_stage(session)
            collected.extend(stage_results)
            stage_cycles += 1

            if session.execution_state == "failed":
                break

            if not continue_stages or session.mode != "full_auto":
                break

            if stage_cycles >= _max_full_auto_stages_per_turn():
                if session.get_current_stage() is not None:
                    session.execution_state = "executing"
                break

            next_stage = session.get_current_stage()
            if not next_stage:
                session.execution_state = "completed"
                break

            next_stage.status = "in_progress"
            stage_def = self._get_stage_definition(next_stage.stage_id)
            if not stage_def:
                break

            planning_results = await self._run_stage_planning_agents(session, stage_def["agents"])
            collected.extend(planning_results)
            if planning_results and planning_results[-1].status == "error":
                session.execution_state = "failed"
                break

        return collected

    def _get_stage_definition(self, stage_id: str) -> Optional[Dict[str, Any]]:
        return next((s for s in STAGE_DEFINITIONS if s["id"] == stage_id), None)

    async def _run_stage_planning_agents(
        self,
        session: AutonomousSession,
        agent_ids: List[str],
    ) -> List[AgentResult]:
        """스테이지 정의 중 coder/validator 제외 에이전트 실행."""
        results: List[AgentResult] = []
        context = self._build_context(session, session.task)
        for agent_id in agent_ids:
            if agent_id in ("coder", "validator"):
                continue
            agent = self.agents.get(agent_id)
            if not agent:
                continue
            context.previous_results = list(session.agent_results)
            result = await self._run_agent_with_bus(agent_id, context, session, session.task)
            results.append(result)
            session.agent_results.append(result)
            session.add_agent_message(agent_id, result.output, result.artifacts)
            if result.status == "error":
                break
        return results

    async def _register_task_only(self, message: str, session: AutonomousSession) -> Dict[str, Any]:
        """프로젝트 목표만 저장 — reasoner 중복 실행 방지, 설계해줘로 1단계 시작."""
        session.task = message.strip()
        if not session.stages:
            self._initialize_stages(session)
        session.approval_state = "none"
        session.execution_state = "idle"
        session.extra["stage_command_hint"] = "'설계해줘'를 입력하면 1단계 구조 설계를 시작합니다."
        reply = (
            f"프로젝트 목표를 저장했습니다.\n\n"
            f"**요청**: {session.task[:300]}\n\n"
            f"1단계 구조 설계를 시작하려면 **`설계해줘`**를 입력하세요."
        )
        session.add_system_message(reply)
        session.save()
        return self._build_response(session, reply, intent="task_registered")

    def _extract_reviewer_issues(self, review_result: AgentResult) -> List[str]:
        issues: List[str] = []
        in_issues = False
        for line in str(review_result.output or "").splitlines():
            stripped = line.strip()
            if stripped.startswith("## 발견된 문제"):
                in_issues = True
                continue
            if in_issues and stripped.startswith("## "):
                break
            if in_issues and stripped.startswith("- "):
                issues.append(stripped[2:].strip())
        if issues:
            return issues
        if review_result.errors:
            return list(review_result.errors)
        return [str(review_result.output or "")[:800]]

    async def _run_reviewer_coder_fix_loop(
        self,
        session: AutonomousSession,
        context: AgentContext,
        review_result: AgentResult,
        results: List[AgentResult],
    ) -> AgentResult:
        """4.5단계 등 reviewer needs_revision → coder 자동 수정 루프."""
        coder = self.agents.get("coder")
        reviewer = self.agents.get("reviewer")
        if not coder or not reviewer:
            return review_result

        current_review = review_result
        for attempt in range(MAX_REVISION_ATTEMPTS):
            if current_review.status != "needs_revision":
                break

            issues = self._extract_reviewer_issues(current_review)
            session.add_system_message(
                f"리뷰어 지적 {len(issues)}건 → 코더 자동 수정 ({attempt + 1}/{MAX_REVISION_ATTEMPTS})"
            )
            fix_result = await coder.fix(context, issues)
            results.append(fix_result)
            session.agent_results.append(fix_result)
            session.add_agent_message("coder", f"[리뷰 반영 {attempt + 1}] {fix_result.output}", fix_result.artifacts)
            context.previous_results = list(session.agent_results)

            if fix_result.status != "success":
                break

            current_review = await self._run_agent_with_bus("reviewer", context, session, session.task)
            results.append(current_review)
            session.agent_results.append(current_review)
            session.add_agent_message("reviewer", current_review.output, current_review.artifacts)
            context.previous_results = list(session.agent_results)

            stage = session.get_current_stage()
            if stage:
                stage.revision_count += 1

        return current_review

    def _finalize_stage_execution(
        self,
        session: AutonomousSession,
        *,
        passed: bool,
    ) -> None:
        if passed:
            stage = session.get_current_stage()
            if stage:
                stage.status = "completed"
                session.advance_stage()
            if session.get_current_stage() is None:
                session.execution_state = "completed"
            else:
                session.execution_state = "executing"
        else:
            session.execution_state = "failed"

    async def _execute_current_stage(self, session: AutonomousSession) -> List[AgentResult]:
        stage = session.get_current_stage()
        stage_def = self._get_stage_definition(stage.stage_id) if stage else None
        agent_ids = list(stage_def["agents"]) if stage_def else ["coder", "validator"]
        stage_id = str(stage.stage_id if stage else "")

        context = self._build_context(session, session.task)
        context.previous_results = list(session.agent_results)
        results: List[AgentResult] = []

        verification_only = stage_id == "STAGE-10"

        if not verification_only:
            for agent_id in [a for a in agent_ids if a == "reviewer"]:
                result = await self._run_agent_with_bus(agent_id, context, session, session.task)
                results.append(result)
                session.agent_results.append(result)
                session.add_agent_message(agent_id, result.output, result.artifacts)
                context.previous_results = list(session.agent_results)
                if result.status == "error":
                    session.add_system_message(
                        "리뷰어 호출 오류 — 코더/검증 단계로 계속 진행합니다."
                    )
                    continue
                if result.status == "needs_revision":
                    await self._run_reviewer_coder_fix_loop(session, context, result, results)

        if verification_only:
            val_passed = True
            for agent_id in [a for a in agent_ids if a in ("validator", "reviewer")]:
                result = await self._run_agent_with_bus(agent_id, context, session, session.task)
                results.append(result)
                session.agent_results.append(result)
                session.add_agent_message(agent_id, result.output, result.artifacts)
                context.previous_results = list(session.agent_results)
                if agent_id == "validator" and not result.artifacts.get("passed"):
                    val_passed = False
            self._finalize_stage_execution(session, passed=val_passed)
            return results

        coder_result = await self._run_agent_with_bus("coder", context, session, session.task)
        results.append(coder_result)
        session.agent_results.append(coder_result)
        session.add_agent_message("coder", coder_result.output, coder_result.artifacts)

        if coder_result.status != "success":
            session.execution_state = "failed"
            return results

        context.previous_results.append(coder_result)
        val_result = await self._run_agent_with_bus("validator", context, session, session.task)
        results.append(val_result)
        session.agent_results.append(val_result)
        session.add_agent_message("validator", val_result.output, val_result.artifacts)

        if val_result.status == "needs_revision" and val_result.errors:
            coder = self.agents["coder"]
            validator = self.agents["validator"]
            for attempt in range(MAX_REVISION_ATTEMPTS):
                fix_result = await coder.fix(context, val_result.errors)
                results.append(fix_result)
                session.agent_results.append(fix_result)
                session.add_agent_message("coder", f"[자동수정 {attempt + 1}] {fix_result.output}")

                context.previous_results.append(fix_result)
                val_result = await validator.execute(context)
                results.append(val_result)
                session.agent_results.append(val_result)
                if val_result.artifacts.get("passed"):
                    break

        self._finalize_stage_execution(
            session,
            passed=bool(val_result.artifacts.get("passed")),
        )

        return results

    def _initialize_stages(self, session: AutonomousSession) -> None:
        session.stages = [
            StageState(stage_id=s["id"], stage_label=s["label"], status="pending")
            for s in STAGE_DEFINITIONS
        ]
        if session.stages:
            session.stages[0].status = "in_progress"
        session.current_stage_index = 0

    def _build_context(self, session: AutonomousSession, message: str) -> AgentContext:
        output_dir = session.output_dir
        if not output_dir:
            import tempfile
            output_dir = os.path.join(
                tempfile.gettempdir(),
                "codeai_autonomous_output",
                session.session_id,
            )
            session.output_dir = output_dir

        stage = session.get_current_stage()
        return AgentContext(
            run_id=session.session_id,
            task=session.task or message,
            project_name=session.project_name or "autonomous-project",
            validation_profile=session.validation_profile,
            stage_id=stage.stage_id if stage else None,
            stage_label=stage.stage_label if stage else None,
            conversation_history=[
                {"role": t.role, "content": t.content}
                for t in session.conversation[-10:]
            ],
            previous_results=list(session.agent_results[-5:]),
            model_routes=session.model_routes,
            output_dir=output_dir,
        )

    def _find_revision_target(self, session: AutonomousSession) -> Optional[str]:
        for r in reversed(session.agent_results):
            if r.status in ("success", "error"):
                return r.agent
        return None

    def _combine_results(self, results: List[AgentResult], session: AutonomousSession) -> str:
        if not results:
            return "처리 결과가 없습니다."

        parts = []
        for r in results:
            role_label = {"reasoner": "🧠 추론자", "planner": "📋 설계자", "reviewer": "🔍 리뷰어", "coder": "⚡ 코더", "validator": "✅ 검증"}.get(r.agent, r.agent)
            status_icon = {"success": "✅", "stub": "⚡", "error": "❌", "needs_revision": "🔄", "needs_review": "📝"}.get(r.status, "❓")
            parts.append(f"### {role_label} {status_icon}\n{r.output}")

        if session.approval_state == "pending":
            stage = session.get_current_stage()
            stage_label = stage.stage_label if stage else "다음 단계"
            hint = str(session.extra.get("stage_command_hint") or "").strip()
            parts.append(
                f"\n---\n⏳ **승인 대기 중** ({stage_label}): "
                f"'승인' 또는 '진행해'라고 말씀하시면 코드 생성을 시작합니다."
            )
            if hint:
                parts.append(f"💡 {hint}")
        elif session.extra.get("stage_command_hint"):
            parts.append(f"\n---\n💡 {session.extra['stage_command_hint']}")

        return "\n\n".join(parts)

    def _build_greeting(self, session: AutonomousSession) -> str:
        mode_label = {"advisory": "조언", "semi_auto": "반자동", "full_auto": "완전자동"}.get(session.mode, session.mode)
        return (
            f"안녕하세요! 멀티 에이전트 자율대화 오케스트레이터입니다.\n\n"
            f"**현재 모드**: {mode_label}\n"
            f"**단계 명령 예시**:\n"
            f"- `설계해줘` → 1단계 구조 설계\n"
            f"- `2단계 진행해줘` → 2단계 코드 생성\n"
            f"- `4단계 Redis 캐시 아이디어 제안해줘` → 4단계 협업 대화\n"
            f"- `진행해` / `승인` → 현재 단계 코드 생성\n\n"
            f"프로젝트를 만들고 싶으시면 '~만들어줘'라고 말씀하세요."
        )

    def _build_status(self, session: AutonomousSession) -> str:
        mode_label = {"advisory": "조언", "semi_auto": "반자동", "full_auto": "완전자동"}.get(session.mode, session.mode)
        lines = [
            f"**세션**: {session.session_id}",
            f"**모드**: {mode_label}",
            f"**실행 상태**: {session.execution_state}",
            f"**승인 상태**: {session.approval_state}",
            f"**에이전트 결과**: {len(session.agent_results)}건",
        ]
        if session.stages:
            stage = session.get_current_stage()
            completed = sum(1 for s in session.stages if s.status == "completed")
            lines.append(f"**진행**: {completed}/{len(session.stages)} 단계 완료")
            if stage:
                lines.append(f"**현재 단계**: {stage.stage_label} ({stage.status})")
        return "\n".join(lines)

    def _build_response(
        self,
        session: AutonomousSession,
        content: str,
        *,
        intent: str = "",
        agent_results: Optional[List[AgentResult]] = None,
    ) -> Dict[str, Any]:
        return {
            "session_id": session.session_id,
            "mode": session.mode,
            "intent": intent,
            "content": content,
            "execution_state": session.execution_state,
            "approval_state": session.approval_state,
            "current_stage": session.get_current_stage().stage_label if session.get_current_stage() else None,
            "stages_completed": sum(1 for s in session.stages if s.status == "completed"),
            "stages_total": len(session.stages),
            "agent_results": [
                {"agent": r.agent, "status": r.status, "elapsed_ms": r.elapsed_ms}
                for r in (agent_results or [])
            ],
            "message_log": self.bus.get_message_log(session.session_id)[-10:],
            "requires_approval": session.approval_state == "pending",
            "llm_connected": bool(session.extra.get("llm_connected")),
            "stages_remaining": max(0, len(session.stages) - sum(1 for s in session.stages if s.status == "completed")),
            "stage_command": session.extra.get("active_stage_command"),
            "stage_number": session.extra.get("active_stage_number"),
            "stage_command_hint": session.extra.get("stage_command_hint"),
        }
