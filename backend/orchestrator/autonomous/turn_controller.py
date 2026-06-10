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

logger = logging.getLogger(__name__)

STAGE_DEFINITIONS = [
    {"id": "STAGE-01", "label": "1단계: 구조 설계", "agents": ["reasoner"]},
    {"id": "STAGE-02", "label": "2단계: 폴더 및 기초 구현", "agents": ["planner"]},
    {"id": "STAGE-03", "label": "3단계: 설계 반영 골조 구현", "agents": ["planner", "coder"]},
    {"id": "STAGE-04", "label": "4단계: 핵심 엔진 구성", "agents": ["coder"]},
    {"id": "STAGE-045", "label": "4.5단계: Refiner/Fixer", "agents": ["reviewer", "coder"]},
    {"id": "STAGE-05", "label": "5단계: 로직 (ID 식별)", "agents": ["coder"]},
    {"id": "STAGE-06", "label": "6단계: 데이터", "agents": ["coder"]},
    {"id": "STAGE-07", "label": "7단계: 서비스", "agents": ["coder"]},
    {"id": "STAGE-08", "label": "8단계: API", "agents": ["coder"]},
    {"id": "STAGE-09", "label": "9단계: 프론트", "agents": ["coder"]},
    {"id": "STAGE-10", "label": "10단계: 운영 검증", "agents": ["validator", "reviewer"]},
]

MAX_REVISION_ATTEMPTS = 3

INTENT_PATTERNS_ORDERED = [
    ("greeting", r"^(안녕|반갑|hello|hi[ !]|hi$)"),
    ("status", r"(상태|진행|현황|status|progress)"),
    ("approval", r"^(승인|좋아|진행해|approve|ok$|proceed|go$)"),
    ("revision", r"(수정|변경|고쳐|바꿔|fix|change|modify|revise)"),
    ("review", r"(검토|리뷰|review|점검)"),
    ("code_generation", r"(만들어|생성|구현|개발|빌드|build|create|generate|implement)"),
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

    def classify_intent(self, message: str) -> str:
        text = message.strip().lower()
        for intent, pattern in INTENT_PATTERNS_ORDERED:
            if re.search(pattern, text, re.IGNORECASE):
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
            return ["reviewer"]
        if intent == "status":
            return []
        if intent == "approval":
            return []
        if intent == "revision":
            revision_target = self._find_revision_target(session)
            return [revision_target] if revision_target else ["reasoner"]

        if intent == "code_generation":
            if session.execution_state == "idle":
                return ["reasoner", "planner"]
            stage = session.get_current_stage()
            if stage:
                stage_def = next((s for s in STAGE_DEFINITIONS if s["id"] == stage.stage_id), None)
                if stage_def:
                    return stage_def["agents"]
            return ["reasoner", "planner", "coder", "validator"]

        return ["reasoner"]

    async def process_turn(self, message: str, session: AutonomousSession) -> Dict[str, Any]:
        session.add_user_message(message)
        intent = self.classify_intent(message)

        if intent == "greeting":
            reply = self._build_greeting(session)
            session.add_system_message(reply)
            session.save()
            return self._build_response(session, reply, intent=intent)

        if intent == "status":
            reply = self._build_status(session)
            session.add_system_message(reply)
            session.save()
            return self._build_response(session, reply, intent=intent)

        if intent == "approval":
            return await self._handle_approval(session)

        if not session.task and intent == "code_generation":
            session.task = message
            session.execution_state = "planning"
            self._initialize_stages(session)

        agent_pipeline = self.route_to_agents(intent, session)
        if not agent_pipeline:
            reply = "요청을 처리할 수 있는 에이전트를 결정하지 못했습니다. 더 구체적으로 말씀해 주세요."
            session.add_system_message(reply)
            session.save()
            return self._build_response(session, reply, intent=intent)

        context = self._build_context(session, message)
        results: List[AgentResult] = []

        for agent_id in agent_pipeline:
            agent = self.agents.get(agent_id)
            if not agent:
                continue

            context.previous_results = results.copy()
            result = await agent.execute(context)
            results.append(result)
            session.agent_results.append(result)

            await self.bus.send(AgentMessage(
                from_agent=agent_id,
                to_agent="controller",
                msg_type="response",
                content=result.output[:500],
                run_id=session.session_id,
                artifacts=result.artifacts,
            ))

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
            elif (
                session.mode == "full_auto"
                and not any(r.agent == "coder" for r in results)
                and all(r.status != "error" for r in results)
            ):
                execution_results = await self._execute_coder_pipeline(session)
                results.extend(execution_results)

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
            session.save()
            return self._build_response(session, reply, intent="approval")

        session.approval_state = "approved"
        session.add_system_message("승인되었습니다. 코드 생성을 시작합니다.")

        execution_results = await self._execute_coder_pipeline(session)

        combined = self._combine_results(execution_results, session)
        session.save()
        return self._build_response(session, combined, intent="approval", agent_results=execution_results)

    async def _execute_coder_pipeline(self, session: AutonomousSession) -> List[AgentResult]:
        session.execution_state = "executing"

        context = self._build_context(session, session.task)
        context.previous_results = list(session.agent_results)
        results: List[AgentResult] = []

        coder = self.agents["coder"]
        coder_result = await coder.execute(context)
        session.agent_results.append(coder_result)
        session.add_agent_message("coder", coder_result.output, coder_result.artifacts)
        results.append(coder_result)

        if coder_result.status == "success":
            context.previous_results.append(coder_result)
            validator = self.agents["validator"]
            val_result = await validator.execute(context)
            session.agent_results.append(val_result)
            session.add_agent_message("validator", val_result.output, val_result.artifacts)
            results.append(val_result)

            if val_result.status == "needs_revision" and val_result.errors:
                for attempt in range(MAX_REVISION_ATTEMPTS):
                    fix_result = await coder.fix(context, val_result.errors)
                    session.agent_results.append(fix_result)
                    session.add_agent_message("coder", f"[자동수정 {attempt+1}] {fix_result.output}")
                    results.append(fix_result)

                    context.previous_results.append(fix_result)
                    val_result = await validator.execute(context)
                    session.agent_results.append(val_result)
                    session.add_agent_message("validator", val_result.output, val_result.artifacts)
                    results.append(val_result)
                    if val_result.artifacts.get("passed"):
                        break

            if val_result.artifacts.get("passed"):
                session.execution_state = "completed"
                stage = session.get_current_stage()
                if stage:
                    stage.status = "completed"
                    session.advance_stage()
            else:
                session.execution_state = "failed"
        else:
            session.execution_state = "failed"

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
            status_icon = {"success": "✅", "error": "❌", "needs_revision": "🔄", "needs_review": "📝"}.get(r.status, "❓")
            parts.append(f"### {role_label} {status_icon}\n{r.output}")

        if session.approval_state == "pending":
            parts.append("\n---\n⏳ **승인 대기 중**: '승인' 또는 '진행해'라고 말씀하시면 코드 생성을 시작합니다.")

        return "\n\n".join(parts)

    def _build_greeting(self, session: AutonomousSession) -> str:
        mode_label = {"advisory": "조언", "semi_auto": "반자동", "full_auto": "완전자동"}.get(session.mode, session.mode)
        return (
            f"안녕하세요! 멀티 에이전트 자율대화 오케스트레이터입니다.\n\n"
            f"**현재 모드**: {mode_label}\n"
            f"**사용 가능한 에이전트**: 추론자, 설계자, 코더, 리뷰어, 검증기\n\n"
            f"프로젝트를 만들고 싶으시면 '~만들어줘'라고 말씀하세요.\n"
            f"예: 'FastAPI로 블로그 API 만들어줘'"
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
        }
