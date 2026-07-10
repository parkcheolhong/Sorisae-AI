"""전화 브리지(T1) feature flag + 설정 (COMM_V2_* env opt-in)."""

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
class TelephonyBridgeConfig:
    """런타임 설정 스냅샷.

    Attributes:
        enabled: 마스터 스위치(``COMM_V2_TELEPHONY_BRIDGE``). 기본 off(PoC 전용).
        sample_rate: 레그 PCM 샘플레이트(Hz).
        frame_ms: 프레임 길이(ms) — RTP 페이로드 모사(20ms 기본).
        segment_max_ms: 세그먼트 자동 종단 상한(ms). 초과 시 강제 flush.
        segment_silence_ms: 무음 누적이 이 길이면 세그먼트 종단(엔드포인팅).
    """

    enabled: bool = False
    sample_rate: int = 16000
    frame_ms: int = 20
    segment_max_ms: int = 7000
    segment_silence_ms: int = 700


def get_telephony_bridge_config() -> TelephonyBridgeConfig:
    return TelephonyBridgeConfig(
        enabled=_env_bool("COMM_V2_TELEPHONY_BRIDGE", False),
        sample_rate=_env_int("COMM_V2_TELEPHONY_SAMPLE_RATE", 16000),
        frame_ms=_env_int("COMM_V2_TELEPHONY_FRAME_MS", 20),
        segment_max_ms=_env_int("COMM_V2_TELEPHONY_SEGMENT_MAX_MS", 7000),
        segment_silence_ms=_env_int("COMM_V2_TELEPHONY_SEGMENT_SILENCE_MS", 700),
    )


def is_telephony_bridge_enabled() -> bool:
    return _env_bool("COMM_V2_TELEPHONY_BRIDGE", False)
