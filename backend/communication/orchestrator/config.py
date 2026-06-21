"""Call Orchestrator feature flag + 설정 (COMM_V2_* env opt-in)."""

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
class CallOrchestratorConfig:
    """런타임 설정 스냅샷.

    Attributes:
        enabled: 마스터 스위치(``COMM_V2_CALL_ORCHESTRATOR``). 기본 off.
        ttl_sec: 종료/비활성 라이프사이클 보존 시간(초).
        max_calls: 인메모리 보호용 추적 통화 수 상한.
        max_events: 통화당 보존할 라이프사이클 이벤트 개수.
        max_concurrent_active: 동시 active 통화 admission 상한(0 = 무제한).
        enforce_policy: True면 admission 정책을 **강제**(거부 가능), False면 관찰만(항상 allow).
    """

    enabled: bool = False
    ttl_sec: int = 3600
    max_calls: int = 10000
    max_events: int = 64
    max_concurrent_active: int = 0
    enforce_policy: bool = False


def get_call_orchestrator_config() -> CallOrchestratorConfig:
    """현재 환경변수로부터 설정을 읽어온다(호출 시점 평가)."""

    return CallOrchestratorConfig(
        enabled=_env_bool("COMM_V2_CALL_ORCHESTRATOR", False),
        ttl_sec=_env_int("COMM_V2_CALL_ORCH_TTL_SEC", 3600),
        max_calls=_env_int("COMM_V2_CALL_ORCH_MAX_CALLS", 10000),
        max_events=_env_int("COMM_V2_CALL_ORCH_MAX_EVENTS", 64),
        max_concurrent_active=_env_int("COMM_V2_CALL_ORCH_MAX_CONCURRENT", 0),
        enforce_policy=_env_bool("COMM_V2_CALL_ORCH_ENFORCE", False),
    )


def is_call_orchestrator_enabled() -> bool:
    """Call Orchestrator가 켜져 있는지(기본 off)."""

    return _env_bool("COMM_V2_CALL_ORCHESTRATOR", False)
