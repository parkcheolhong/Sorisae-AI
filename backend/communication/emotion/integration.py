"""감정 SER(E0) ↔ 텔레메트리 얇은 연결 (best-effort, 완전 가드, off-path).

설계 불변식(Session/Orchestrator integration과 동일):

1. **flag off(기본) = 완전 no-op** (`COMM_V2_EMOTION_SER`).
2. **절대 throw 금지** — 예외는 흡수(debug 로그).
3. **hot path 무영향** — E0는 텔레메트리 부착 전용. 번역/통화 결과를 변경하지 않는다.

E0 범위에서는 **라이브 오디오 hot path에 직접 배선하지 않는다.** off-path 분석기/텔레메트리
소비자(예: 향후 통화 오디오 telemetry)가 이 진입점을 호출해 감정 라벨을 부착한다.
실제 hot path 오디오 연결은 E1 이후 플래그 하에 신중히 진행한다.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional, Sequence

from .audio import decode_audio_to_pcm16, pcm16_samples_from_bytes
from .config import (
    get_emotion_ser_config,
    is_emotion_expressive_tts_enabled,
    is_emotion_probe_enabled,
    is_emotion_register_enabled,
    is_emotion_ser_enabled,
)
from .estimator import AcousticHeuristicSER, EmotionEstimator
from .expressive_tts import ExpressiveTTSParams, expressive_params_from_emotion
from .features import extract_features
from .models import EmotionEstimate
from .register import register_directive_from_emotion

logger = logging.getLogger(__name__)

_estimator: Optional[EmotionEstimator] = None
_lock = threading.Lock()


def _get() -> EmotionEstimator:
    global _estimator
    if _estimator is None:
        with _lock:
            if _estimator is None:
                _estimator = AcousticHeuristicSER()
    return _estimator


def reset_for_test() -> None:
    """테스트 전용 — 환경변수 토글 후 재생성하도록 초기화."""

    global _estimator
    with _lock:
        _estimator = None


def estimate_from_samples(
    samples: Sequence[float],
    *,
    sample_rate: int = 16000,
) -> Optional[EmotionEstimate]:
    """PCM 샘플 → 감정 추정(best-effort). flag off/실패 시 ``None``."""

    try:
        if not is_emotion_ser_enabled() or not samples:
            return None
        features = extract_features(samples, sample_rate=sample_rate)
        return _get().estimate(features)
    except Exception:  # pragma: no cover - 방어적
        logger.debug("[emotion-ser] estimate_from_samples skipped", exc_info=True)
        return None


def estimate_as_telemetry(
    samples: Sequence[float],
    *,
    sample_rate: int = 16000,
) -> Optional[dict[str, Any]]:
    """로그/텔레메트리 부착용 dict 반환(best-effort). flag off 시 ``None``."""

    est = estimate_from_samples(samples, sample_rate=sample_rate)
    return est.to_dict() if est is not None else None


def build_register_hint_from_pcm16(
    audio_bytes: Optional[bytes],
    *,
    target_lang: Optional[str] = None,
    sample_rate: int = 16000,
) -> Optional[str]:
    """E1: PCM16 오디오 → 감정 추정 → register 지시문(best-effort).

    `COMM_V2_EMOTION_REGISTER` off / 오디오 없음 / 중립·저신뢰면 ``None`` →
    MT는 기존과 동일하게 동작. **절대 throw 금지.** SER 텔레메트리 플래그와 독립.
    """

    try:
        if not is_emotion_register_enabled() or not audio_bytes:
            return None
        samples = pcm16_samples_from_bytes(audio_bytes)
        if not samples:
            return None
        cfg = get_emotion_ser_config()
        features = extract_features(samples, sample_rate=sample_rate)
        estimate = _get().estimate(features)
        return register_directive_from_emotion(
            estimate, target_lang=target_lang,
            min_confidence=cfg.register_min_confidence,
        )
    except Exception:  # pragma: no cover - 방어적, hot path 보호
        logger.debug("[emotion-ser] build_register_hint skipped", exc_info=True)
        return None


def build_emotion_probe(
    src_audio_bytes: Optional[bytes],
    out_audio_bytes: Optional[bytes],
    *,
    src_sample_rate: int = 16000,
    out_sample_rate: int = 16000,
) -> Optional[dict[str, Any]]:
    """E2: 원문(입력 PCM16)↔출력(TTS) 감정을 추정해 ``VOIP_EMOTION_PROBE`` 페이로드 생성.

    - ``COMM_V2_EMOTION_PROBE`` off / src·out 어느 한쪽이라도 비면 ``None``.
    - src 는 designated/VOIP raw PCM16(WAV), out 은 TTS(mp3/wav) → ffmpeg best-effort 디코딩.
    - 평가 하니스(`eval/worldlinco/objective.py`)가 요구하는 flat 4필드
      (``src/out_arousal·valence``)를 보장하며 라벨/신뢰도는 부가 정보.
    - **절대 throw 금지** — off-path 텔레메트리, hot path 무영향.
    """

    try:
        if not is_emotion_probe_enabled():
            return None
        if not src_audio_bytes or not out_audio_bytes:
            return None
        src_samples = pcm16_samples_from_bytes(src_audio_bytes)
        out_samples = decode_audio_to_pcm16(out_audio_bytes, sample_rate=out_sample_rate)
        if not src_samples or not out_samples:
            return None
        estimator = _get()
        src = estimator.estimate(extract_features(src_samples, sample_rate=src_sample_rate))
        out = estimator.estimate(extract_features(out_samples, sample_rate=out_sample_rate))
        return {
            "src_arousal": round(src.arousal, 3),
            "src_valence": round(src.valence, 3),
            "src_label": src.label.value,
            "src_confidence": round(src.confidence, 3),
            "out_arousal": round(out.arousal, 3),
            "out_valence": round(out.valence, 3),
            "out_label": out.label.value,
            "out_confidence": round(out.confidence, 3),
        }
    except Exception:  # pragma: no cover - 방어적, hot path 보호
        logger.debug("[emotion-ser] build_emotion_probe skipped", exc_info=True)
        return None


def build_expressive_tts_plan_from_pcm16(
    src_audio_bytes: Optional[bytes],
    *,
    sample_rate: int = 16000,
    base_rate_pct: float = 0.0,
) -> Optional[ExpressiveTTSParams]:
    """E3: 원문 PCM16 → 감정 추정 → 표현형 TTS 운율 파라미터(best-effort).

    - ``COMM_V2_EMOTION_EXPRESSIVE_TTS`` off / 오디오 없음 / 저신뢰·중립이면 ``None`` →
      합성은 기존(비표현형)과 동일(안전 폴백).
    - 반환된 ``ExpressiveTTSParams`` 는 엔진(edge-tts/Azure)에 운율을 적용하는 데 쓰인다.
    - **카나리 전 hot path 무배선** — 이 진입점은 게이트(flag) 하에서만 호출된다.
    - **절대 throw 금지.**
    """

    try:
        if not is_emotion_expressive_tts_enabled() or not src_audio_bytes:
            return None
        samples = pcm16_samples_from_bytes(src_audio_bytes)
        if not samples:
            return None
        cfg = get_emotion_ser_config()
        estimate = _get().estimate(extract_features(samples, sample_rate=sample_rate))
        params = expressive_params_from_emotion(
            estimate,
            min_confidence=cfg.expressive_min_confidence,
            base_rate_pct=base_rate_pct,
        )
        return None if params.neutral else params
    except Exception:  # pragma: no cover - 방어적, hot path 보호
        logger.debug("[emotion-ser] build_expressive_tts_plan skipped", exc_info=True)
        return None
