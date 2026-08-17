"""Session Core feature flag + 설정 (COMM_V2_* env opt-in)."""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUE = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class SessionCoreConfig:
    """런타임 설정 스냅샷.

    Attributes:
        enabled: 마스터 스위치(``COMM_V2_SESSION_CORE``). 기본 off.
        ttl_sec: 비활성 세션 만료 시간(초).
        max_turns: 세션당 보존할 최근 턴 개수(맥락 기억 상한).
        max_sessions: 인메모리 스토어 보호용 세션 수 상한.
    """

    enabled: bool = False
    ttl_sec: int = 3600
    max_turns: int = 50
    max_sessions: int = 10000


def get_session_core_config() -> SessionCoreConfig:
    """현재 환경변수로부터 설정을 읽어온다(호출 시점 평가)."""

    return SessionCoreConfig(
        enabled=_env_bool("COMM_V2_SESSION_CORE", False),
        ttl_sec=_env_int("COMM_V2_SESSION_TTL_SEC", 3600),
        max_turns=_env_int("COMM_V2_SESSION_MAX_TURNS", 50),
        max_sessions=_env_int("COMM_V2_SESSION_MAX_SESSIONS", 10000),
    )


def is_session_core_enabled() -> bool:
    """Session Core가 켜져 있는지(기본 off)."""

    return _env_bool("COMM_V2_SESSION_CORE", False)
