"""B뇌 코더 에이전트 — 기존 generator facade를 통한 실제 코드 생성"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)


class CoderAgent(BaseAgent):
    agent_id = "coder"
    agent_role = "coding"
    brain = "B"

    async def _run(self, context: AgentContext) -> AgentResult:
        output_dir = context.output_dir
        if not output_dir:
            return AgentResult(
                agent=self.agent_id,
                status="error",
                output="출력 디렉터리가 설정되지 않았습니다.",
                errors=["output_dir is required"],
            )

        previous = self._format_previous_results(context)
        revision_hint = ""
        if context.user_feedback:
            revision_hint = f"\n\n[수정 요청]\n{context.user_feedback}\n위 피드백을 반영하여 코드를 수정하세요."

        try:
            written_files = await self._generate_code(context, previous, revision_hint)
        except Exception as exc:
            logger.exception("[coder] code generation failed")
            return AgentResult(
                agent=self.agent_id,
                status="error",
                output=f"코드 생성 실패: {exc}",
                errors=[str(exc)],
            )

        return AgentResult(
            agent=self.agent_id,
            status="success",
            output=f"B뇌 코드 생성 완료: {len(written_files)}개 파일 작성",
            next_agents=["validator"],
            artifacts={
                "written_files": written_files,
                "output_dir": str(output_dir),
                "file_count": len(written_files),
            },
        )

    async def _generate_code(self, context: AgentContext, previous: str, revision_hint: str) -> List[str]:
        from backend.llm.orchestrator import (
            _run_b_brain_multi_generator,
            _compat_manifest_for_request,
            _compat_write_manifest,
        )

        output_path = Path(context.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        enriched_task = context.task
        if previous:
            enriched_task = f"{context.task}\n\n{previous}"
        if revision_hint:
            enriched_task += revision_hint

        b_result = _run_b_brain_multi_generator(
            project_name=context.project_name,
            validation_profile=context.validation_profile,
            task=enriched_task,
            output_dir=output_path,
        )

        anchor_path, manifest, _ = _compat_manifest_for_request(
            project_name=context.project_name,
            validation_profile=context.validation_profile,
            task=enriched_task,
            output_dir=output_path,
            b_brain_result=b_result,
        )

        written_files = _compat_write_manifest(output_path, manifest)
        return written_files

    async def fix(self, context: AgentContext, errors: List[str]) -> AgentResult:
        context.user_feedback = f"검증 에이전트가 다음 오류를 발견했습니다:\n" + "\n".join(f"- {e}" for e in errors)
        return await self.execute(context)
