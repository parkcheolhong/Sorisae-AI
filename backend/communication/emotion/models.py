"""감정 SER(E0) 도메인 모델 (순수 dataclass).

감정은 **차원(arousal·valence)** 을 1차로 추정하고 범주는 차원에서 유도한다.
음향 SER에서 arousal(각성/에너지)은 비교적 신뢰 가능, valence(긍/부정)은 약한 신호다
(설계서 §6 오인식 안전망). 텍스트 비의존 = 언어 무관.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


def _now() -> float:
    return time.time()


class EmotionLabel(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"      # high arousal, high valence
    ANGRY = "angry"      # high arousal, low valence
    SAD = "sad"          # low arousal, low valence
    CALM = "calm"        # low arousal, high valence


@dataclass(frozen=True)
class AcousticFeatures:
    """언어 무관 음향 특징(프레임 집계).

    Attributes:
        rms: 평균 RMS 에너지(0..1, 라우드니스 → arousal 주신호).
        zcr: 영교차율(0..1, 스펙트럼/voicing 거칢 proxy).
        energy_var: 프레임 에너지 분산(0..1, 운율 역동성 → arousal 보조).
        n_samples: 사용된 샘플 수(신뢰도 산정용).
        pitch_hz: (선택) 추정 피치 — 베이스라인은 None.
    """

    rms: float
    zcr: float
    energy_var: float
    n_samples: int
    pitch_hz: Optional[float] = None


@dataclass
class EmotionEstimate:
    """감정 추정 결과(텔레메트리 부착 단위)."""

    label: EmotionLabel
    arousal: float       # 0..1
    valence: float       # 0..1 (0.5=중립)
    confidence: float    # 0..1
    source: str = "acoustic_heuristic_v0"
    at: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label.value,
            "arousal": round(self.arousal, 3),
            "valence": round(self.valence, 3),
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "at": self.at,
        }
