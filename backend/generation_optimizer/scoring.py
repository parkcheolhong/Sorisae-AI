from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class GenerationScore:
    score: int
    checklist: List[str]
    ok: bool


def score_generation_artifacts(paths: Iterable[str]) -> GenerationScore:
    normalized = {str(path).replace('\\', '/').strip() for path in paths if str(path).strip()}
    checklist: List[str] = []
    required = [
        'README.md',
        'docs/architecture.md',
        'docs/auto_link_map.json',
        'docs/generator_checklist.md',
        'docs/multi_role_contract.json',
        'docs/operational_readiness.md',
        'docs/traceability_map.json',
        '.codeai-template.json',
    ]
    for path in required:
        if path not in normalized:
            checklist.append(f'missing required artifact: {path}')
    score = max(0, 100 - (len(checklist) * 12))
    return GenerationScore(score=score, checklist=checklist, ok=len(checklist) == 0)
