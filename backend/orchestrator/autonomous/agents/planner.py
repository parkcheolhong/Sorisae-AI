"""A뇌 설계자 에이전트 — 파일 구조, 구현 계획, 단계별 작업 분해"""
from __future__ import annotations

from .base import BaseAgent, AgentContext, AgentResult


class PlannerAgent(BaseAgent):
    agent_id = "planner"
    agent_role = "planner"
    brain = "A"

    async def _run(self, context: AgentContext) -> AgentResult:
        previous = self._format_previous_results(context)
        revision_hint = ""
        if context.user_feedback:
            revision_hint = f"\n\n[사용자 피드백]\n{context.user_feedback}\n위 피드백을 반영하여 계획을 수정하세요."

        system_prompt = (
            "당신은 프로젝트 구현 설계자(A뇌 설계자)입니다.\n"
            "추론자의 분석 결과를 바탕으로 구체적인 파일 구조와 구현 계획을 수립합니다.\n\n"
            "반드시 아래 형식으로 답변하세요:\n"
            "## 디렉터리 구조\n```\nproject/\n├── ...\n```\n\n"
            "## 파일별 구현 계획\n- 각 파일의 역할과 핵심 함수/클래스\n\n"
            "## 구현 순서\n- 어떤 파일부터 어떤 순서로 구현할지\n\n"
            "## 단계별 작업 분해\n- 각 단계에서 수행할 작업 목록\n\n"
            "한국어로 답변하세요."
        )
        user_prompt = (
            f"프로젝트: {context.project_name}\n"
            f"검증 프로필: {context.validation_profile}\n"
            f"요청 작업:\n{context.task}\n"
            f"{previous}{revision_hint}"
        )

        output = await self._call_llm(system_prompt, user_prompt, context)

        return AgentResult(
            agent=self.agent_id,
            status="success",
            output=output,
            next_agents=["coder"],
            artifacts={
                "plan_type": "implementation_plan",
                "stage_id": context.stage_id,
            },
        )
