"""A뇌 추론 에이전트 — 요구사항 분석, 구조 설계, 의존성 추론"""
from __future__ import annotations

from .base import BaseAgent, AgentContext, AgentResult


class ReasonerAgent(BaseAgent):
    agent_id = "reasoner"
    agent_role = "reasoning"
    brain = "A"

    async def _run(self, context: AgentContext) -> AgentResult:
        previous = self._format_previous_results(context)
        revision_hint = ""
        if context.user_feedback:
            revision_hint = f"\n\n[사용자 피드백]\n{context.user_feedback}\n위 피드백을 반영하여 설계를 수정하세요."

        system_prompt = (
            "당신은 소프트웨어 아키텍처 추론 전문가(A뇌 추론자)입니다.\n"
            "사용자의 요구사항을 분석하고, 프로젝트의 구조를 설계합니다.\n\n"
            "반드시 아래 형식으로 답변하세요:\n"
            "## 요구사항 분석\n- 핵심 기능 목록\n\n"
            "## 기술 스택 제안\n- 사용할 기술/프레임워크\n\n"
            "## 모델 설계\n- 필요한 데이터 모델\n\n"
            "## API 엔드포인트\n- 필요한 API 목록\n\n"
            "## 의존성 및 위험\n- 고려해야 할 사항\n\n"
            "한국어로 답변하세요."
        )
        user_prompt = (
            f"프로젝트: {context.project_name}\n"
            f"검증 프로필: {context.validation_profile}\n"
            f"요청 작업:\n{context.task}\n"
            f"{previous}{revision_hint}"
        )
        if context.stage_id:
            user_prompt += f"\n현재 단계: {context.stage_label or context.stage_id}"

        output = await self._call_llm(system_prompt, user_prompt, context)

        return AgentResult(
            agent=self.agent_id,
            status="success",
            output=output,
            next_agents=["planner"],
            artifacts={
                "analysis_type": "requirements_and_architecture",
                "stage_id": context.stage_id,
            },
        )
