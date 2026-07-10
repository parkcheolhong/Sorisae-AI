#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_LINES: Dict[str, List[str]] = {
    ".github/copilot-instructions.md": [
        "- 헌법 최우선 고정 규칙: 사용자가 지시한 목표를 단순·직진 경로로 수행하며, 불필요한 구조 확장/우회/복잡화/헛작업을 금지한다.",
        "- 헌법 최우선 고정 규칙: 합의되지 않은 설계 변경·단계 추가·범위 확장은 금지하며, 필요한 최소 변경과 근거 검증만 허용한다.",
    ],
    "AGENTS.md": [
        "- 사용자가 지시한 목표는 단순·직진 경로로 수행하며, 불필요한 구조 확장/우회/복잡화/헛작업을 금지한다.",
        "- 합의되지 않은 설계 변경·단계 추가·범위 확장은 금지하며, 필요한 최소 변경과 근거 검증만 허용한다.",
    ],
}


def _read_lines(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return text.splitlines()


def main() -> int:
    violations: List[str] = []

    for rel_path, required in REQUIRED_LINES.items():
        abs_path = REPO_ROOT / rel_path
        if not abs_path.exists():
            violations.append(f"{rel_path}: 파일이 없습니다.")
            continue

        lines = _read_lines(abs_path)
        for rule in required:
            if rule not in lines:
                violations.append(
                    f"{rel_path}: 필수 헌법 규칙 누락 -> {rule}"
                )

    if violations:
        print("[constitution-hard-gate] 차단: 헌법 고정 규칙 위반")
        for item in violations:
            print(f"- {item}")
        return 1

    print("[constitution-hard-gate] 통과: 헌법 고정 규칙 보존 확인")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
