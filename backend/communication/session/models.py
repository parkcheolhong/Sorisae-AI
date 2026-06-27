"""Session Core 도메인 모델 (순수 dataclass, FastAPI/DB 비의존)."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional


def _now() -> float:
    return time.time()


@dataclass(frozen=True)
class LanguagePair:
    """방향성 있는 통역 언어쌍 (BCP-47/ISO 코드 문자열)."""

    source: str
    target: str

    def normalized(self) -> "LanguagePair":
        return LanguagePair(source=self.source.strip().lower(), target=self.target.strip().lower())

    def reversed(self) -> "LanguagePair":
        return LanguagePair(source=self.target, target=self.source)

    def as_tuple(self) -> tuple[str, str]:
        return (self.source, self.target)


@dataclass
class Participant:
    """세션 참가자 + 선호 언어."""

    user_ref: str
    preferred_language: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class TurnRecord:
    """단일 통역 턴(맥락 기억 단위) — 원문/번역문/방향.

    오디오 바이트는 보관하지 않는다(프라이버시·메모리). 텍스트 요약만.
    """

    direction: LanguagePair
    source_text: str = ""
    translated_text: str = ""
    speaker_ref: Optional[str] = None
    created_at: float = field(default_factory=_now)


@dataclass
class SessionContext:
    """세션 1건의 살아있는 맥락.

    - ``language_pair``: 가장 최근 확정 언어쌍(언어 기억).
    - ``recent_turns``: 최근 N개 턴(맥락 기억, ``max_turns`` 캡).
    - ``participants``: user_ref → Participant.
    """

    session_id: str
    call_id: Optional[str] = None
    language_pair: Optional[LanguagePair] = None
    participants: dict[str, Participant] = field(default_factory=dict)
    recent_turns: Deque[TurnRecord] = field(default_factory=deque)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()

    def is_expired(self, ttl_sec: int, *, now: Optional[float] = None) -> bool:
        ref = _now() if now is None else now
        return (ref - self.updated_at) > ttl_sec

    def upsert_participant(self, participant: Participant) -> None:
        self.participants[participant.user_ref] = participant
        self.touch()

    def set_language_pair(self, pair: LanguagePair) -> None:
        self.language_pair = pair.normalized()
        self.touch()

    def add_turn(self, turn: TurnRecord, *, max_turns: int) -> None:
        self.recent_turns.append(turn)
        while len(self.recent_turns) > max(0, max_turns):
            self.recent_turns.popleft()
        # 턴 방향을 최신 언어쌍으로 반영(언어 기억).
        self.language_pair = turn.direction.normalized()
        self.touch()

    def context_snapshot(self, *, limit: Optional[int] = None) -> list[TurnRecord]:
        turns = list(self.recent_turns)
        if limit is not None and limit >= 0:
            return turns[-limit:]
        return turns
