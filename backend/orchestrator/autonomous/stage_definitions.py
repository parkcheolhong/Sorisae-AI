"""11단계 STAGE 정의 — TurnController·stage_commands SSOT."""
from __future__ import annotations

from typing import Any, Dict, List

STAGE_DEFINITIONS: List[Dict[str, Any]] = [
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

STAGE_NUMBER_BY_INDEX: List[float] = [1, 2, 3, 4, 4.5, 5, 6, 7, 8, 9, 10]

COLLABORATION_STAGE_INDEX_MIN = 3  # 4단계(STAGE-04)부터 협업 Q&A
