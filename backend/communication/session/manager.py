"""SessionManager — Session Core 진입점.

get_or_create / 언어쌍 갱신 / 턴 기록 / 컨텍스트 조회 / 만료를 캡슐화한다.
**플래그 off(기본)일 때는 어떤 메서드도 무해한 no-op/None 을 반환**해, 호출부가
플래그를 일일이 확인하지 않아도 hot path에 영향을 주지 않는다.
"""

from __future__ import annotations

from typing import Optional

from .config import SessionCoreConfig, get_session_core_config
from .models import LanguagePair, Participant, SessionContext, TurnRecord
from .store import InMemorySessionStore, SessionStore


class SessionManager:
    def __init__(
        self,
        store: Optional[SessionStore] = None,
        config: Optional[SessionCoreConfig] = None,
    ) -> None:
        self._config = config or get_session_core_config()
        self._store = store or InMemorySessionStore(max_sessions=self._config.max_sessions)

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def store(self) -> SessionStore:
        return self._store

    def get_or_create(
        self,
        session_id: str,
        *,
        call_id: Optional[str] = None,
    ) -> Optional[SessionContext]:
        """세션을 조회하거나 생성한다. 플래그 off면 ``None``."""

        if not self._config.enabled or not session_id:
            return None
        ctx = self._store.get(session_id)
        if ctx is None:
            ctx = SessionContext(session_id=session_id, call_id=call_id)
            self._store.put(ctx)
        elif call_id and not ctx.call_id:
            ctx.call_id = call_id
            ctx.touch()
            self._store.put(ctx)
        return ctx

    def get(self, session_id: str) -> Optional[SessionContext]:
        if not self._config.enabled or not session_id:
            return None
        return self._store.get(session_id)

    def update_language_pair(
        self,
        session_id: str,
        source: str,
        target: str,
        *,
        call_id: Optional[str] = None,
    ) -> Optional[SessionContext]:
        if not self._config.enabled or not session_id:
            return None
        ctx = self.get_or_create(session_id, call_id=call_id)
        if ctx is None:
            return None
        ctx.set_language_pair(LanguagePair(source=source, target=target))
        self._store.put(ctx)
        return ctx

    def upsert_participant(
        self,
        session_id: str,
        participant: Participant,
        *,
        call_id: Optional[str] = None,
    ) -> Optional[SessionContext]:
        if not self._config.enabled or not session_id:
            return None
        ctx = self.get_or_create(session_id, call_id=call_id)
        if ctx is None:
            return None
        ctx.upsert_participant(participant)
        self._store.put(ctx)
        return ctx

    def record_turn(
        self,
        session_id: str,
        turn: TurnRecord,
        *,
        call_id: Optional[str] = None,
    ) -> Optional[SessionContext]:
        if not self._config.enabled or not session_id:
            return None
        ctx = self.get_or_create(session_id, call_id=call_id)
        if ctx is None:
            return None
        ctx.add_turn(turn, max_turns=self._config.max_turns)
        self._store.put(ctx)
        return ctx

    def language_pair(self, session_id: str) -> Optional[LanguagePair]:
        ctx = self.get(session_id)
        return ctx.language_pair if ctx else None

    def recent_turns(self, session_id: str, *, limit: Optional[int] = None) -> list[TurnRecord]:
        ctx = self.get(session_id)
        if ctx is None:
            return []
        return ctx.context_snapshot(limit=limit)

    def end_session(self, session_id: str) -> None:
        if not session_id:
            return
        self._store.delete(session_id)

    def purge_expired(self) -> int:
        if not self._config.enabled:
            return 0
        return self._store.purge_expired(self._config.ttl_sec)
