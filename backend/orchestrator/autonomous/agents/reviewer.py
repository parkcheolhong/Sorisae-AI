"""A뇌 리뷰어 에이전트 — 코드 검토, 품질 평가, 개선 제안"""
from __future__ import annotations

from .base import BaseAgent, AgentContext, AgentResult


class ReviewerAgent(BaseAgent):
    agent_id = "reviewer"
    agent_role = "reviewer"
    brain = "A"

    async def _run(self, context: AgentContext) -> AgentResult:
        previous = self._format_previous_results(context)
        if not previous:
            return AgentResult(
                agent=self.agent_id,
                status="success",
                output="리뷰할 에이전트 결과가 없습니다.",
                next_agents=[],
            )

        system_prompt = (
            "당신은 시니어 코드 리뷰어(A뇌 리뷰어)입니다.\n"
            "이전 에이전트들의 결과를 검토하고 품질을 평가합니다.\n\n"
            "반드시 아래 형식으로 답변하세요:\n"
            "## 검토 결과\n- approved: true/false\n\n"
            "## 품질 점수\n- score: 0-100\n\n"
            "## 발견된 문제\n- 보안 취약점, 로직 오류, 성능 문제 등\n\n"
            "## 개선 제안\n- 구체적인 수정 방향\n\n"
            "한국어로 답변하세요."
        )
        user_prompt = (
            f"프로젝트: {context.project_name}\n"
            f"검증 프로필: {context.validation_profile}\n"
            f"요청 작업:\n{context.task}\n"
            f"\n{previous}"
        )

        output = await self._call_llm(system_prompt, user_prompt, context)

        output_lower = output.lower()
        normalized_output = "".join(output_lower.split())
        approved = "approved: true" in output_lower or "approved:true" in output_lower
        no_issue = any(
            phrase in normalized_output
            for phrase in ("문제없음", "문제없습니다", "문제가없", "문제는없")
        )
        has_issue = "문제" in output and not no_issue
        needs_revision = not approved and ("approved: false" in output_lower or has_issue)

        return AgentResult(
            agent=self.agent_id,
            status="needs_revision" if needs_revision else "success",
            output=output,
            next_agents=["coder"] if needs_revision else [],
            artifacts={
                "approved": approved,
                "needs_revision": needs_revision,
            },
        )
