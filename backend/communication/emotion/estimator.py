"""감정 추정기 — 인터페이스 + 휴리스틱 베이스라인(E0).

`AcousticHeuristicSER` 는 GPU/모델 없이 음향 특징만으로 arousal/valence/범주를 추정하는
**투명한 베이스라인**이다. 운영 정확도가 목표가 아니라, 파이프라인·텔레메트리·평가 척도를
먼저 세우는 것이 E0의 목적이다. E0→실모델 단계에서 동일 인터페이스(`EmotionEstimator`)로
wav2vec2/HuBERT 미세조정 SER을 끼워 넣는다.

휴리스틱(문서화된 근거):
- **arousal** ≈ RMS 에너지 + 에너지 분산 + ZCR 가중합 — 음향적으로 비교적 신뢰.
- **valence** 는 음향만으로 약함 → ZCR·에너지 기반 *약한* proxy + 낮은 신뢰도(중립 0.5 근처).
- **confidence** ≈ 중립 기준선과의 거리 × 샘플 충분성. 임계 미만이면 **중립 폴백**(오인식 안전망).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .config import EmotionSerConfig, get_emotion_ser_config
from .models import AcousticFeatures, EmotionEstimate, EmotionLabel


class EmotionEstimator(ABC):
    """SER 추정기 인터페이스 (실모델 교체 대비)."""

    @abstractmethod
    def estimate(self, features: AcousticFeatures) -> EmotionEstimate:
        ...


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class AcousticHeuristicSER(EmotionEstimator):
    """음향 휴리스틱 베이스라인 (언어 무관, stdlib)."""

    source = "acoustic_heuristic_v0"

    def __init__(self, config: Optional[EmotionSerConfig] = None) -> None:
        self._config = config or get_emotion_ser_config()

    def estimate(self, features: AcousticFeatures) -> EmotionEstimate:
        cfg = self._config

        # 샘플 부족 → 저신뢰 중립.
        if features.n_samples < cfg.min_samples:
            return EmotionEstimate(
                label=EmotionLabel.NEUTRAL, arousal=0.5, valence=0.5,
                confidence=0.0, source=self.source,
            )

        # arousal: 에너지/역동성/ZCR 가중합.
        arousal = _clamp01(0.55 * features.rms + 0.30 * features.energy_var + 0.15 * features.zcr)

        # valence(약한 proxy): 높은 ZCR+높은 에너지는 부정(분노)쪽으로, 낮은 ZCR은 긍/중립쪽.
        # 0.5 중심에서 소폭 이동만(음향 valence 불확실성 반영).
        valence = _clamp01(0.5 - 0.25 * (features.zcr - 0.1) + 0.10 * (0.3 - features.rms))

        # confidence: 중립(0.5,0.5)에서의 거리 + 샘플 충분성 × **에너지 존재 게이트**.
        # 무음/초저에너지(rms≈0)는 거리상 멀어 보여도 신뢰할 수 없으므로 presence로 억제.
        dist = ((arousal - 0.5) ** 2 + (valence - 0.5) ** 2) ** 0.5  # 0..~0.707
        sample_factor = _clamp01(features.n_samples / (cfg.min_samples * 4))
        presence = _clamp01(features.rms / 0.08)  # 무음 → 0, 정상 발화 → ~1
        confidence = _clamp01(((dist / 0.707) * 0.85 + sample_factor * 0.15) * presence)

        # 임계 미만 → 중립 폴백(오인식 안전망).
        if confidence < cfg.confidence_threshold:
            return EmotionEstimate(
                label=EmotionLabel.NEUTRAL, arousal=arousal, valence=valence,
                confidence=confidence, source=self.source,
            )

        label = self._label_from_dimensions(arousal, valence)
        return EmotionEstimate(
            label=label, arousal=arousal, valence=valence,
            confidence=confidence, source=self.source,
        )

    @staticmethod
    def _label_from_dimensions(arousal: float, valence: float) -> EmotionLabel:
        hi_a = arousal >= 0.55
        hi_v = valence >= 0.5
        if hi_a and not hi_v:
            return EmotionLabel.ANGRY
        if hi_a and hi_v:
            return EmotionLabel.HAPPY
        if not hi_a and not hi_v:
            return EmotionLabel.SAD
        if not hi_a and hi_v:
            return EmotionLabel.CALM
        return EmotionLabel.NEUTRAL
