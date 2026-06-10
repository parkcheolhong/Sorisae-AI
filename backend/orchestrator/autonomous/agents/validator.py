"""검증 에이전트 — 생성된 코드의 품질/보안/구조 검증"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    agent_id = "validator"
    agent_role = "validator"
    brain = "A"

    async def _run(self, context: AgentContext) -> AgentResult:
        coder_result = None
        for r in context.previous_results:
            if r.agent == "coder" and r.artifacts.get("written_files"):
                coder_result = r
                break

        if not coder_result:
            return AgentResult(
                agent=self.agent_id,
                status="success",
                output="검증할 코드가 없습니다.",
                artifacts={"passed": True, "checks": []},
            )

        output_dir = Path(coder_result.artifacts.get("output_dir", context.output_dir or ""))
        written_files = coder_result.artifacts.get("written_files", [])
        checks: List[Dict[str, Any]] = []
        errors: List[str] = []

        for fpath in written_files:
            if not fpath.endswith(".py"):
                continue
            full = output_dir / fpath
            if not full.exists():
                continue
            result = self._compile_check(full)
            checks.append(result)
            if not result["passed"]:
                errors.append(f"{fpath}: {result['error']}")

        structure_check = self._structure_check(output_dir, written_files)
        checks.append(structure_check)
        if not structure_check["passed"]:
            errors.append(structure_check["error"])

        passed = len(errors) == 0
        score = max(0, 100 - len(errors) * 15)

        return AgentResult(
            agent=self.agent_id,
            status="success" if passed else "needs_revision",
            output=(
                f"검증 통과 ({score}점): {len(written_files)}개 파일 확인 완료"
                if passed
                else f"검증 실패 ({score}점): {len(errors)}개 오류 발견"
            ),
            next_agents=[] if passed else ["coder"],
            errors=errors,
            artifacts={
                "passed": passed,
                "score": score,
                "checks": checks,
                "file_count": len(written_files),
            },
        )

    def _compile_check(self, path: Path) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return {"check": "compile", "file": str(path.name), "passed": True, "error": None}
            return {"check": "compile", "file": str(path.name), "passed": False, "error": result.stderr.strip()[:200]}
        except Exception as exc:
            return {"check": "compile", "file": str(path.name), "passed": False, "error": str(exc)[:200]}

    def _structure_check(self, output_dir: Path, written_files: List[str]) -> Dict[str, Any]:
        if not written_files:
            return {"check": "structure", "passed": False, "error": "생성된 파일이 없습니다"}

        has_entry = any(
            f.endswith("main.py") or f.endswith("app.py") or f.endswith("__init__.py")
            for f in written_files
        )
        if not has_entry:
            return {"check": "structure", "passed": False, "error": "진입점 파일(main.py/app.py)이 없습니다"}

        return {"check": "structure", "passed": True, "error": None}
