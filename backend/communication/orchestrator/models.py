"""Call Orchestrator 도메인 모델 (순수 dataclass, FastAPI/DB 비의존)."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Optional


def _now() -> float:
    return time.time()


class CallStateV2(str, Enum):
    """오케스트레이터 정규화 통화 상태.

    라우터의 자유 문자열 status(``connecting``/``ringing``/``active``/``ended``/
    ``callee_offline``/``dialer_required``/``missed`` 등)를 정규 집합으로 매핑한다.
    """

    INITIATING = "initiating"
    RINGING = "ringing"
    CONNECTING = "connecting"
    ACTIVE = "active"
    ENDING = "ending"
    ENDED = "ended"
    MISSED = "missed"
    FAILED = "failed"

    @classmethod
    def from_router_status(cls, status: Optional[str]) -> "CallStateV2":
        s = (status or "").strip().lower()
        mapping = {
            "initiating": cls.INITIATING,
            "ringing": cls.RINGING,
            "connecting": cls.CONNECTING,
            "callee_offline": cls.RINGING,
            "dialer_required": cls.CONNECTING,
            "active": cls.ACTIVE,
            "ending": cls.ENDING,
            "ended": cls.ENDED,
            "completed": cls.ENDED,
            "missed": cls.MISSED,
            "failed": cls.FAILED,
            "error": cls.FAILED,
        }
        return mapping.get(s, cls.INITIATING)

    def is_terminal(self) -> bool:
        return self in {CallStateV2.ENDED, CallStateV2.MISSED, CallStateV2.FAILED}


# 허용 상태 전이(관찰 위주라 느슨함 — 위반은 거부가 아니라 경고 플래그로만 기록).
_ALLOWED_TRANSITIONS: dict[CallStateV2, set[CallStateV2]] = {
    CallStateV2.INITIATING: {CallStateV2.RINGING, CallStateV2.CONNECTING,
                             CallStateV2.ACTIVE, CallStateV2.ENDED,
                             CallStateV2.MISSED, CallStateV2.FAILED},
    CallStateV2.RINGING: {CallStateV2.CONNECTING, CallStateV2.ACTIVE,
                          CallStateV2.ENDED, CallStateV2.MISSED, CallStateV2.FAILED},
    CallStateV2.CONNECTING: {CallStateV2.ACTIVE, CallStateV2.ENDED,
                             CallStateV2.MISSED, CallStateV2.FAILED},
    CallStateV2.ACTIVE: {CallStateV2.ENDING, CallStateV2.ENDED, CallStateV2.FAILED},
    CallStateV2.ENDING: {CallStateV2.ENDED, CallStateV2.FAILED},
    CallStateV2.ENDED: set(),
    CallStateV2.MISSED: set(),
    CallStateV2.FAILED: set(),
}


def is_valid_transition(src: CallStateV2, dst: CallStateV2) -> bool:
    if src == dst:
        return True
    return dst in _ALLOWED_TRANSITIONS.get(src, set())


@dataclass
class LifecycleEvent:
    """단일 상태 전이 이벤트."""

    state: CallStateV2
    at: float = field(default_factory=_now)
    reason: Optional[str] = None
    out_of_order: bool = False  # 허용 전이 위반(관찰 플래그)

    def to_dict(self) -> dict[str, Any]:
        return {"state": self.state.value, "at": self.at,
                "reason": self.reason, "out_of_order": self.out_of_order}


@dataclass
class PolicyDecision:
    """admission/policy 결정 결과."""

    allow: bool
    code: str = "allow"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"allow": self.allow, "code": self.code, "reason": self.reason}


@dataclass
class CallLifecycle:
    """통화 1건의 라이프사이클 추적(상태·이벤트 이력·정책 결정)."""

    call_id: str
    session_id: Optional[str] = None
    state: CallStateV2 = CallStateV2.INITIATING
    route: Optional[str] = None
    events: Deque[LifecycleEvent] = field(default_factory=deque)
    policy_decisions: list[PolicyDecision] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()

    def is_expired(self, ttl_sec: int, *, now: Optional[float] = None) -> bool:
        # 종료 상태만 만료 대상(진행 중 통화는 보존).
        if not self.state.is_terminal():
            return False
        ref = _now() if now is None else now
        return (ref - self.updated_at) > ttl_sec

    def transition(self, new_state: CallStateV2, *, reason: Optional[str] = None,
                   max_events: int = 64) -> LifecycleEvent:
        out_of_order = not is_valid_transition(self.state, new_state)
        ev = LifecycleEvent(state=new_state, reason=reason, out_of_order=out_of_order)
        self.events.append(ev)
        while len(self.events) > max(1, max_events):
            self.events.popleft()
        self.state = new_state
        self.touch()
        return ev

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "session_id": self.session_id,
            "state": self.state.value,
            "route": self.route,
            "events": [e.to_dict() for e in self.events],
            "policy_decisions": [p.to_dict() for p in self.policy_decisions],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
