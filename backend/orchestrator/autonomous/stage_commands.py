"""단계별 자연어 명령 — 설계 / 진행 / 협업 대화."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List, Optional

from .stage_definitions import (
    COLLABORATION_STAGE_INDEX_MIN,
    STAGE_DEFINITIONS,
    STAGE_NUMBER_BY_INDEX,
)

DEFAULT_STAGE_COMMAND_MODES: List[str] = [
    "/run",
    "/pass",
    "/fix",
    "/fail",
    "/verify",
    "/search",
    "/news",
    "/ask",
    "/revise",
    "/resume",
]

_SLASH_DISCUSS_PREFIXES = (
    "/ask",
    "/search",
    "/news",
    "/revise",
    "/resume",
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


def format_discuss_locked_hint() -> str:
    return "4단계부터 협업 Q&A·기술 제안이 가능합니다. 지금은 「설계해줘」·「N단계 진행해줘」를 사용하세요."


def build_stage_command_rules(
    *,
    stage_command: Optional[str] = None,
    stage_index: Optional[int] = None,
    stage_command_hint: Optional[str] = None,
    requires_approval: bool = False,
    command_modes: Optional[List[str]] = None,
) -> List[str]:
    """`format_stage_progress_hint` 등 백엔드 힌트를 stage 카드 commandRules와 mirror."""
    modes = command_modes or DEFAULT_STAGE_COMMAND_MODES
    rules: List[str] = [
        "일반 질문/명령은 지시 입력창에 적고 Enter로 전송합니다.",
        f"슬래시 명령: {', '.join(modes)}",
    ]
    if requires_approval:
        rules.append("승인 대기 중 — 「승인」·「진행해」로 코드 생성을 시작하거나 수정 요청을 입력하세요.")
    if stage_command == "design" and stage_index is not None:
        rules.append(format_stage_execute_hint(stage_index))
    elif stage_command == "discuss" and stage_command_hint:
        rules.append(stage_command_hint)
    elif stage_command == "execute" and stage_index is not None:
        rules.append(format_stage_progress_hint(stage_index))
    elif stage_command_hint:
        rules.append(stage_command_hint)
    elif stage_index is not None:
        rules.append(format_stage_progress_hint(stage_index))
    return rules


def collaboration_discuss_locked_message(message: str, session: Optional[Any] = None) -> Optional[str]:
    """4단계 미만 discuss/slash 협업 시도 → 고정 안내."""
    if session is None:
        return None
    text = message.strip()
    if not text:
        return None
    current_index = int(getattr(session, "current_stage_index", 0) or 0)
    if current_index >= COLLABORATION_STAGE_INDEX_MIN:
        return None
    lowered = text.lower()
    if lowered.startswith(_SLASH_DISCUSS_PREFIXES):
        return format_discuss_locked_hint()
    if bool(_DISCUSS_MARKERS.search(text)) and not bool(_EXECUTE_VERBS.search(text)):
        return format_discuss_locked_hint()
    return None


def _parse_slash_discuss_command(message: str, session: Optional[Any] = None) -> Optional["StageCommand"]:
    if session is None:
        return None
    text = message.strip()
    lowered = text.lower()
    matched_prefix = next((prefix for prefix in _SLASH_DISCUSS_PREFIXES if lowered.startswith(prefix)), None)
    if not matched_prefix:
        return None
    current_index = int(getattr(session, "current_stage_index", 0) or 0)
    if not is_collaboration_stage_index(current_index):
        return None
    stage = STAGE_DEFINITIONS[current_index]
    return StageCommand(
        action="discuss",
        stage_index=current_index,
        stage_id=stage["id"],
        stage_label=stage["label"],
        stage_number=stage_number_for_index(current_index),
    )


def is_collaboration_stage_index(stage_index: int) -> bool:
    return stage_index >= COLLABORATION_STAGE_INDEX_MIN


def parse_stage_command(message: str, session: Optional[Any] = None) -> Optional[StageCommand]:
    """자연어 → 단계 명령. 예: 설계해줘 / 2단계 진행해줘 / 4단계에서 Redis 캐시 아이디어?"""
    slash_cmd = _parse_slash_discuss_command(message, session)
    if slash_cmd:
        return slash_cmd

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
