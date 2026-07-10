"""Session Core (얇은 버전) — 통화/세션 단위 언어쌍·맥락 기억.

로드맵 #2. **추가형·feature-flag(`COMM_V2_SESSION_CORE`)·hot path 무접촉.**

핵심 객체:
- :class:`~backend.communication.session.models.SessionContext` — 세션 1건의 언어쌍/참가자/최근 턴.
- :class:`~backend.communication.session.store.SessionStore` — 저장 추상(인메모리 기본, Redis 승격 가능).
- :class:`~backend.communication.session.manager.SessionManager` — get_or_create / 언어쌍 갱신 / 턴 기록 / 만료.

기존 `nadotongryoksa_voip_router`·`voice-translate` hot path는 이 모듈을 **호출하지 않는다**.
오케스트레이터가 플래그 on일 때만 얇게 연결한다(향후 단계).
"""

from .config import SessionCoreConfig, get_session_core_config, is_session_core_enabled
from .manager import SessionManager
from .models import LanguagePair, Participant, SessionContext, TurnRecord
from .store import InMemorySessionStore, SessionStore

__all__ = [
    "SessionCoreConfig",
    "get_session_core_config",
    "is_session_core_enabled",
    "SessionManager",
    "LanguagePair",
    "Participant",
    "SessionContext",
    "TurnRecord",
    "InMemorySessionStore",
    "SessionStore",
]
