"""Detection Engine — 규칙 기반 단타 시그널 생성.

설계서 §3-2 의 C++ detection_thread 의사코드를 Python 으로 옮긴다:
    buy  = (obi >  OBI_THRESH && vol_ratio > VOL_SPIKE && price_delta > 0)
    sell = (obi < -OBI_THRESH && vol_ratio > VOL_SPIKE && price_delta < 0)

추가로, 각 조건의 충족 정도를 합성해 confidence∈[0,1] 를 산출한다.
이 confidence 는 이후 AI 추론과 결합(또는 AI 미사용 시 단독 사용)된다.
"""
from __future__ import annotations

from ..config import SignalConfig
from ..features.engine import FeatureVector
from ..types import Signal, SignalSide


class DetectionEngine:
    def __init__(self, config: SignalConfig | None = None) -> None:
        self.config = config or SignalConfig()

    def evaluate(self, fv: FeatureVector) -> Signal:
        cfg = self.config
        obi_thresh = cfg.obi_threshold
        vol_spike = cfg.volume_spike_ratio

        buy = fv.obi > obi_thresh and fv.volume_spike > vol_spike and fv.micro_momentum > 0.0
        sell = fv.obi < -obi_thresh and fv.volume_spike > vol_spike and fv.micro_momentum < 0.0

        features = {
            "obi": fv.obi,
            "obi_norm": fv.obi_norm,
            "volume_spike": fv.volume_spike,
            "micro_momentum": fv.micro_momentum,
            "vwap_delta": fv.vwap_delta,
            "spread": fv.spread,
        }

        if buy:
            return Signal(
                side=SignalSide.BUY,
                confidence=self._confidence(fv, side=SignalSide.BUY),
                ts_ns=fv.ts_ns,
                symbol=fv.symbol,
                reason="obi>thresh & vol_spike & momentum_up",
                features=features,
            )
        if sell:
            return Signal(
                side=SignalSide.SELL,
                confidence=self._confidence(fv, side=SignalSide.SELL),
                ts_ns=fv.ts_ns,
                symbol=fv.symbol,
                reason="obi<-thresh & vol_spike & momentum_down",
                features=features,
            )
        return Signal(
            side=SignalSide.FLAT,
            confidence=0.0,
            ts_ns=fv.ts_ns,
            symbol=fv.symbol,
            reason="no_signal",
            features=features,
        )

    def _confidence(self, fv: FeatureVector, side: SignalSide) -> float:
        """조건 강도를 0~1 로 합성한다.

        - OBI 강도: |obi_norm| 을 시그모이드 유사 매핑(z=2 → ~0.76).
        - 볼륨 강도: vol_spike 가 임계 대비 얼마나 큰지.
        - 모멘텀 강도: 부호 일치 시 가산.
        """
        obi_strength = _squash(abs(fv.obi_norm) / 2.0)
        vol_ratio = fv.volume_spike / max(self.config.volume_spike_ratio, 1e-9)
        vol_strength = _squash(max(0.0, vol_ratio - 1.0))
        mom_ok = (side == SignalSide.BUY and fv.micro_momentum > 0) or (
            side == SignalSide.SELL and fv.micro_momentum < 0
        )
        mom_strength = 1.0 if mom_ok else 0.0
        conf = 0.45 * obi_strength + 0.35 * vol_strength + 0.20 * mom_strength
        return max(0.0, min(1.0, conf))


def _squash(x: float) -> float:
    """음수 클립 후 [0,1) 로 부드럽게 매핑: x/(1+x)."""
    if x <= 0:
        return 0.0
    return x / (1.0 + x)
