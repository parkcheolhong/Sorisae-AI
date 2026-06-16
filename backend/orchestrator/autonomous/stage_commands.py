"""단계별 자연어 명령 — 설계 / 진행 / 협업 대화."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from .stage_definitions import (
    COLLABORATION_STAGE_INDEX_MIN,
    STAGE_DEFINITIONS,
    STAGE_NUMBER_BY_INDEX,
)

_DESIGN_ONLY = re.compile(r"설계\s*해", re.IGNORECASE)
_EXECUTE_VERBS = re.compile(
    r"(진행|실행|실해|구현|만들|적용|코드\s*생성|시작\s*해|반영\s*해|배포)",
    re.IGNORECASE,
)
_DISCUSS_MARKERS = re.compile(
    r"(\?|질문|아이디어|신기술|최신\s*기술|검색|제안|추천|어떻게|왜|설명|"
    r"what|how|why|idea|suggest|recommend|search)",
    re.IGNORECASE,
)
_STAGE_NUMBER = re.compile(r"(\d+(?:\.\d+)?)\s*단계", re.IGNORECASE)


@dataclass(frozen=True)
class StageCommand:
    action: str  # design | execute | discuss
    stage_index: int
    stage_id: str
    stage_label: str
    stage_number: float


def stage_index_from_number(stage_number: float) -> Optional[int]:
    normalized = float(stage_number)
    if normalized == int(normalized) and normalized != 4.5:
        normalized = int(normalized)
    for index, mapped in enumerate(STAGE_NUMBER_BY_INDEX):
        if mapped == normalized:
            return index
    return None


def parse_stage_number(message: str) -> Optional[int]:
    match = _STAGE_NUMBER.search(message.strip())
    if not match:
        return None
    try:
        return stage_index_from_number(float(match.group(1)))
    except ValueError:
        return None


def stage_number_for_index(stage_index: int) -> float:
    if 0 <= stage_index < len(STAGE_NUMBER_BY_INDEX):
        return STAGE_NUMBER_BY_INDEX[stage_index]
    return float(stage_index + 1)


def format_stage_progress_hint(stage_index: int) -> str:
    current = stage_number_for_index(stage_index)
    if stage_index + 1 < len(STAGE_DEFINITIONS):
        nxt = stage_number_for_index(stage_index + 1)
        return f"'{nxt:g}단계 진행해줘'로 다음 단계를 실행하세요."
    return "11단계 파이프라인이 모두 완료되었습니다."


def format_stage_execute_hint(stage_index: int) -> str:
    number = stage_number_for_index(stage_index)
    return f"'{number:g}단계 진행해줘' 또는 '진행해'라고 입력하면 해당 단계 코드 생성을 시작합니다."


def is_collaboration_stage_index(stage_index: int) -> bool:
    return stage_index >= COLLABORATION_STAGE_INDEX_MIN


def parse_stage_command(message: str, session: Optional[Any] = None) -> Optional[StageCommand]:
    """자연어 → 단계 명령. 예: 설계해줘 / 2단계 진행해줘 / 4단계에서 Redis 캐시 아이디어?"""
    text = message.strip()
    if not text:
        return None

    stage_index = parse_stage_number(text)
    has_execute = bool(_EXECUTE_VERBS.search(text))
    has_discuss = bool(_DISCUSS_MARKERS.search(text))
    design_only = bool(_DESIGN_ONLY.search(text)) and not has_execute

    if design_only:
        target_index = stage_index if stage_index is not None else 0
        stage = STAGE_DEFINITIONS[target_index]
        return StageCommand(
            action="design",
            stage_index=target_index,
            stage_id=stage["id"],
            stage_label=stage["label"],
            stage_number=stage_number_for_index(target_index),
        )

    if stage_index is not None and has_execute:
        stage = STAGE_DEFINITIONS[stage_index]
        return StageCommand(
            action="execute",
            stage_index=stage_index,
            stage_id=stage["id"],
            stage_label=stage["label"],
            stage_number=stage_number_for_index(stage_index),
        )

    if stage_index is not None and has_discuss and is_collaboration_stage_index(stage_index):
        stage = STAGE_DEFINITIONS[stage_index]
        return StageCommand(
            action="discuss",
            stage_index=stage_index,
            stage_id=stage["id"],
            stage_label=stage["label"],
            stage_number=stage_number_for_index(stage_index),
        )

    # 4단계+ 협업: 단계 번호 없이 질문/아이디어만 입력
    if (
        session is not None
        and stage_index is None
        and has_discuss
        and not has_execute
        and not design_only
    ):
        current_index = int(getattr(session, "current_stage_index", 0) or 0)
        if is_collaboration_stage_index(current_index):
            stage = STAGE_DEFINITIONS[current_index]
            return StageCommand(
                action="discuss",
                stage_index=current_index,
                stage_id=stage["id"],
                stage_label=stage["label"],
                stage_number=stage_number_for_index(current_index),
            )

    # 승인 대기 중 「진행해」 — 현재 단계 execute
    if session is not None and stage_index is None and has_execute:
        execution_state = str(getattr(session, "execution_state", "") or "")
        approval_state = str(getattr(session, "approval_state", "") or "")
        if execution_state == "awaiting_approval" or approval_state == "pending":
            current_index = int(getattr(session, "current_stage_index", 0) or 0)
            if 0 <= current_index < len(STAGE_DEFINITIONS):
                stage = STAGE_DEFINITIONS[current_index]
                return StageCommand(
                    action="execute",
                    stage_index=current_index,
                    stage_id=stage["id"],
                    stage_label=stage["label"],
                    stage_number=stage_number_for_index(current_index),
                )

    return None
