"""Call Orchestrator 저장 추상 + 인메모리 구현.

Session Core store와 동일 패턴(thread-safe, TTL purge + LRU 캡). 운영 승격 시
동일 인터페이스로 Redis 백엔드로 교체(로드맵 #4 Redis Cluster 연계).
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Optional

from .models import CallLifecycle, CallStateV2


class LifecycleStore(ABC):
    @abstractmethod
    def get(self, call_id: str) -> Optional[CallLifecycle]:
        ...

    @abstractmethod
    def put(self, lifecycle: CallLifecycle) -> None:
        ...

    @abstractmethod
    def delete(self, call_id: str) -> None:
        ...

    @abstractmethod
    def purge_expired(self, ttl_sec: int) -> int:
        ...

    @abstractmethod
    def count(self) -> int:
        ...

    @abstractmethod
    def active_count(self) -> int:
        ...


class InMemoryLifecycleStore(LifecycleStore):
    """프로세스 로컬 인메모리 스토어 (thread-safe, TTL purge + 용량 캡)."""

    def __init__(self, *, max_calls: int = 10000) -> None:
        self._max_calls = max(1, max_calls)
        self._data: dict[str, CallLifecycle] = {}
        self._lock = threading.RLock()

    def get(self, call_id: str) -> Optional[CallLifecycle]:
        with self._lock:
            return self._data.get(call_id)

    def put(self, lifecycle: CallLifecycle) -> None:
        with self._lock:
            self._data[lifecycle.call_id] = lifecycle
            self._evict_if_needed()

    def delete(self, call_id: str) -> None:
        with self._lock:
            self._data.pop(call_id, None)

    def purge_expired(self, ttl_sec: int) -> int:
        with self._lock:
            stale = [cid for cid, lc in self._data.items() if lc.is_expired(ttl_sec)]
            for cid in stale:
                self._data.pop(cid, None)
            return len(stale)

    def count(self) -> int:
        with self._lock:
            return len(self._data)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for lc in self._data.values() if lc.state == CallStateV2.ACTIVE)

    def _evict_if_needed(self) -> None:
        overflow = len(self._data) - self._max_calls
        if overflow <= 0:
            return
        # 종료 상태 + 오래된 순으로 우선 evict(진행 중 통화 보존).
        victims = sorted(
            self._data.values(),
            key=lambda lc: (not lc.state.is_terminal(), lc.updated_at),
        )[:overflow]
        for lc in victims:
            self._data.pop(lc.call_id, None)
