"""감정 SER(E0) feature flag + 설정 (COMM_V2_* env opt-in)."""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUE = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class EmotionSerConfig:
    """런타임 설정 스냅샷.

    Attributes:
        enabled: SER 텔레메트리 스위치(``COMM_V2_EMOTION_SER``). 기본 off.
        confidence_threshold: 이 신뢰도 미만이면 **중립 폴백**(오인식 안전망, §6 가드레일).
        min_samples: SER 추정에 필요한 최소 샘플 수(짧으면 신뢰도↓).
        register_enabled: E1 감정→register(존댓말/어휘) 제어 스위치(``COMM_V2_EMOTION_REGISTER``).
            SER 텔레메트리와 **독립 opt-in** — register만 켜도 추정해 MT 힌트를 만든다.
        register_min_confidence: register 지시문을 낼 최소 신뢰도(약신호 과조정 방지, SER 임계보다 높게).
        probe_enabled: E2 ``VOIP_EMOTION_PROBE`` 텔레메트리 emit 스위치(``COMM_V2_EMOTION_PROBE``).
            원문(입력)↔출력(TTS) 감정을 추정해 응답에 동봉 → 클라가 로그캣 emit → 평가 하니스가
            감정 보존도(E2)를 실데이터로 산출. SER/register 와 **독립 opt-in**, 기본 off.
    """

    enabled: bool = False
    confidence_threshold: float = 0.35
    min_samples: int = 1600  # ~100ms @16kHz
    register_enabled: bool = False
    register_min_confidence: float = 0.5
    probe_enabled: bool = False
    expressive_tts_enabled: bool = False
    expressive_min_confidence: float = 0.55


def get_emotion_ser_config() -> EmotionSerConfig:
    return EmotionSerConfig(
        enabled=_env_bool("COMM_V2_EMOTION_SER", False),
        confidence_threshold=_env_float("COMM_V2_EMOTION_SER_CONF", 0.35),
        min_samples=int(_env_float("COMM_V2_EMOTION_SER_MIN_SAMPLES", 1600)),
        register_enabled=_env_bool("COMM_V2_EMOTION_REGISTER", False),
        register_min_confidence=_env_float("COMM_V2_EMOTION_REGISTER_CONF", 0.5),
        probe_enabled=_env_bool("COMM_V2_EMOTION_PROBE", False),
        expressive_tts_enabled=_env_bool("COMM_V2_EMOTION_EXPRESSIVE_TTS", False),
        expressive_min_confidence=_env_float("COMM_V2_EMOTION_EXPRESSIVE_TTS_CONF", 0.55),
    )


def is_emotion_ser_enabled() -> bool:
    return _env_bool("COMM_V2_EMOTION_SER", False)


def is_emotion_register_enabled() -> bool:
    """E1 감정→register 제어가 켜져 있는지(기본 off)."""

    return _env_bool("COMM_V2_EMOTION_REGISTER", False)


def is_emotion_probe_enabled() -> bool:
    """E2 EMOTION_PROBE 텔레메트리 emit 이 켜져 있는지(기본 off)."""

    return _env_bool("COMM_V2_EMOTION_PROBE", False)


def is_emotion_expressive_tts_enabled() -> bool:
    """E3 표현형 TTS(감정→운율) 카나리가 켜져 있는지(기본 off)."""

    return _env_bool("COMM_V2_EMOTION_EXPRESSIVE_TTS", False)
