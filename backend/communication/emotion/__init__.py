"""WorldLinco V2 — 감정 E0: 언어 무관 SER 베이스라인 (off-path, additive).

[`EMOTION_EXPRESSIVE_DESIGN.md`](../../../docs/worldlinco-v2/EMOTION_EXPRESSIVE_DESIGN.md) §5 E0.
음향 특징(언어 무관)으로 감정 차원(arousal/valence)·범주를 추정해 **통화 텔레메트리에
감정 라벨을 부착**한다. hot path(번역/통화) 와 완전 분리 — `COMM_V2_EMOTION_SER` opt-in,
기본 off. 현재 추정기는 **휴리스틱 베이스라인**(GPU/모델 불필요)이며, 향후 wav2vec2/HuBERT
미세조정 SER로 교체할 자리다(E0→실모델).
"""

from .config import (
    EmotionSerConfig,
    get_emotion_ser_config,
    is_emotion_expressive_tts_enabled,
    is_emotion_probe_enabled,
    is_emotion_register_enabled,
    is_emotion_ser_enabled,
)
from .models import EmotionLabel, AcousticFeatures, EmotionEstimate
from .estimator import EmotionEstimator, AcousticHeuristicSER
from .expressive_tts import (
    ExpressiveTTSParams,
    expressive_params_from_emotion,
    to_azure_ssml,
    to_edge_tts_kwargs,
)
from .budget import (
    expressive_allowed,
    observe_tts_latency,
    p95_ms as expressive_p95_ms,
)

__all__ = [
    "EmotionSerConfig",
    "get_emotion_ser_config",
    "is_emotion_ser_enabled",
    "is_emotion_register_enabled",
    "is_emotion_probe_enabled",
    "is_emotion_expressive_tts_enabled",
    "EmotionLabel",
    "AcousticFeatures",
    "EmotionEstimate",
    "EmotionEstimator",
    "AcousticHeuristicSER",
    "ExpressiveTTSParams",
    "expressive_params_from_emotion",
    "to_edge_tts_kwargs",
    "to_azure_ssml",
    "expressive_allowed",
    "observe_tts_latency",
    "expressive_p95_ms",
]
