"""Session Core 저장 추상 + 인메모리 구현.

기본 구현은 thread-safe 인메모리(TTL·LRU 보호). 운영 승격 시 동일 인터페이스로
Redis 백엔드를 끼워 넣는다(로드맵 #4 Redis Cluster 연계).
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Optional

from .models import SessionContext


class SessionStore(ABC):
    """세션 저장 인터페이스 (Redis 승격 대비)."""

    @abstractmethod
    def get(self, session_id: str) -> Optional[SessionContext]:
        ...

    @abstractmethod
    def put(self, context: SessionContext) -> None:
        ...

    @abstractmethod
    def delete(self, session_id: str) -> None:
        ...

    @abstractmethod
    def purge_expired(self, ttl_sec: int) -> int:
        ...

    @abstractmethod
    def count(self) -> int:
        ...


class InMemorySessionStore(SessionStore):
    """프로세스 로컬 인메모리 스토어 (thread-safe, TTL purge + 용량 캡).

    단일 프로세스 한정(멀티 워커는 Redis 백엔드로 승격). 캡 초과 시 가장
    오래 갱신되지 않은 세션부터 evict 한다.
    """

    def __init__(self, *, max_sessions: int = 10000) -> None:
        self._max_sessions = max(1, max_sessions)
        self._data: dict[str, SessionContext] = {}
        self._lock = threading.RLock()

    def get(self, session_id: str) -> Optional[SessionContext]:
        with self._lock:
            return self._data.get(session_id)

    def put(self, context: SessionContext) -> None:
        with self._lock:
            self._data[context.session_id] = context
            self._evict_if_needed()

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._data.pop(session_id, None)

    def purge_expired(self, ttl_sec: int) -> int:
        with self._lock:
            stale = [sid for sid, ctx in self._data.items() if ctx.is_expired(ttl_sec)]
            for sid in stale:
                self._data.pop(sid, None)
            return len(stale)

    def count(self) -> int:
        with self._lock:
            return len(self._data)

    def _evict_if_needed(self) -> None:
        overflow = len(self._data) - self._max_sessions
        if overflow <= 0:
            return
        # 갱신 오래된 순으로 evict.
        victims = sorted(self._data.values(), key=lambda c: c.updated_at)[:overflow]
        for ctx in victims:
            self._data.pop(ctx.session_id, None)
