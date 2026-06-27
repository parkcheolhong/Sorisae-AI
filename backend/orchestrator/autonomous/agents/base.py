"""에이전트 기본 클래스 및 결과 모델"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    agent: str
    status: str  # success, stub, error, needs_review, needs_revision
    output: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    next_agents: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    run_id: str
    task: str
    project_name: str
    validation_profile: str
    stage_id: Optional[str] = None
    stage_label: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    previous_results: List[AgentResult] = field(default_factory=list)
    model_routes: Dict[str, str] = field(default_factory=dict)
    user_feedback: Optional[str] = None
    output_dir: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    """모든 에이전트의 기본 클래스"""

    agent_id: str = "base"
    agent_role: str = "base"
    brain: str = "A"  # A (추론/설계) 또는 B (실행/생성)

    def __init__(self, llm_call=None, bus=None):
        self._llm_call = llm_call
        self._bus = bus

    async def execute(self, context: AgentContext) -> AgentResult:
        started = time.perf_counter()
        try:
            result = await self._run(context)
            result.elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            return result
        except Exception as exc:
            elapsed = round((time.perf_counter() - started) * 1000, 1)
            logger.exception("[%s] agent execution failed", self.agent_id)
            return AgentResult(
                agent=self.agent_id,
                status="error",
                output="",
                errors=[str(exc)],
                elapsed_ms=elapsed,
            )

    async def _run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError

    async def revise(self, context: AgentContext, feedback: str) -> AgentResult:
        context.user_feedback = feedback
        return await self.execute(context)

    async def _call_llm_tracked(
        self,
        system_prompt: str,
        user_prompt: str,
        context: AgentContext,
    ) -> tuple[str, bool]:
        """Returns (output, llm_connected). GPU/Ollama 미연결 시 stub 텍스트와 False."""
        if self._llm_call is None:
            stub = (
                f"[{self.agent_id}] LLM 미연결 — GPU/Ollama 서버 연결 후 품질 검증 필요. "
                f"(프롬프트 미리보기: {system_prompt[:80]}...)"
            )
            return stub, False
        model = context.model_routes.get(self.agent_role, context.model_routes.get("default", ""))
        try:
            output = await self._llm_call(
                route_key=self.agent_role,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return output, True
        except Exception as exc:
            logger.warning("[%s] LLM call failed, using stub: %s", self.agent_id, exc)
            stub = (
                f"[{self.agent_id}] LLM 호출 실패 — {exc}. "
                f"(프롬프트 미리보기: {system_prompt[:80]}...)"
            )
            return stub, False

    async def _call_llm(self, system_prompt: str, user_prompt: str, context: AgentContext) -> str:
        output, _ = await self._call_llm_tracked(system_prompt, user_prompt, context)
        return output

    def _format_previous_results(self, context: AgentContext) -> str:
        if not context.previous_results:
            return ""
        lines = ["[이전 에이전트 결과]"]
        for r in context.previous_results:
            lines.append(f"- {r.agent} ({r.status}): {r.output[:300]}")
        return "\n".join(lines)
