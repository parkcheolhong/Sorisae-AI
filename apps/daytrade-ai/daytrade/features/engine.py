"""Feature Engine — 틱 스트림에서 단타 시그널용 피처를 실시간 계산.

설계서 §3-1 시그널 종류를 그대로 구현한다:
    - OBI(Order Book Imbalance): Σbid_qty(depth) − Σask_qty(depth)
    - obi_norm: z-score 정규화(이동 평균/표준편차)
    - volume_spike: vol_t / vol_{t-1}
    - micro_momentum: price_t − price_{t-Δ}
    - vwap / vwap_delta: 거래량 가중 평균가 및 그 변화
    - spread: best_ask − best_bid

상태(이전 틱·볼륨/가격/OBI 히스토리)를 보관하는 stateful 엔진이다.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from ..types import MarketTick, total_qty


FEATURE_NAMES: tuple[str, ...] = (
    "obi",
    "obi_norm",
    "volume_spike",
    "micro_momentum",
    "vwap",
    "vwap_delta",
    "spread",
    "mid_price",
)


@dataclass(frozen=True, slots=True)
class FeatureVector:
    ts_ns: int
    symbol: str
    obi: float
    obi_norm: float
    volume_spike: float
    micro_momentum: float
    vwap: float
    vwap_delta: float
    spread: float
    mid_price: float

    def as_array(self) -> list[float]:
        """AI 추론 입력용 순서 고정 벡터(FEATURE_NAMES 순서)."""
        return [
            self.obi,
            self.obi_norm,
            self.volume_spike,
            self.micro_momentum,
            self.vwap,
            self.vwap_delta,
            self.spread,
            self.mid_price,
        ]


@dataclass(slots=True)
class FeatureEngine:
    depth: int = 10
    vwap_window: int = 50
    obi_stat_window: int = 200
    momentum_window: int = 1  # 몇 틱 전 가격과 비교(=Δ). 1이면 직전 틱.

    _prev_price: float | None = field(default=None, init=False)
    _prev_volume: float | None = field(default=None, init=False)
    _prev_vwap: float | None = field(default=None, init=False)
    _price_hist: deque[float] = field(default_factory=deque, init=False)
    _obi_hist: deque[float] = field(default_factory=deque, init=False)
    _vwap_pv: deque[float] = field(default_factory=deque, init=False)  # price*vol
    _vwap_v: deque[float] = field(default_factory=deque, init=False)   # vol

    def reset(self) -> None:
        self._prev_price = None
        self._prev_volume = None
        self._prev_vwap = None
        self._price_hist.clear()
        self._obi_hist.clear()
        self._vwap_pv.clear()
        self._vwap_v.clear()

    def update(self, tick: MarketTick) -> FeatureVector:
        bids = tick.bids[: self.depth]
        asks = tick.asks[: self.depth]
        bid_sum = total_qty(bids)
        ask_sum = total_qty(asks)
        obi = bid_sum - ask_sum

        # OBI 정규화(z-score) — 절대 임계값 의존을 줄이고 종목/체제 변화에 강건.
        self._obi_hist.append(obi)
        while len(self._obi_hist) > self.obi_stat_window:
            self._obi_hist.popleft()
        obi_norm = _zscore(obi, self._obi_hist)

        # 거래량 급증
        vol = float(tick.last_qty)
        if self._prev_volume is None or self._prev_volume <= 0:
            volume_spike = 1.0
        else:
            volume_spike = vol / self._prev_volume

        # 마이크로 모멘텀
        price = float(tick.last_price)
        self._price_hist.append(price)
        while len(self._price_hist) > self.momentum_window + 1:
            self._price_hist.popleft()
        if len(self._price_hist) > self.momentum_window:
            ref = self._price_hist[0]
            micro_momentum = price - ref
        else:
            micro_momentum = 0.0

        # VWAP(이동 윈도)
        self._vwap_pv.append(price * max(vol, 0.0))
        self._vwap_v.append(max(vol, 0.0))
        while len(self._vwap_v) > self.vwap_window:
            self._vwap_pv.popleft()
            self._vwap_v.popleft()
        vsum = sum(self._vwap_v)
        vwap = (sum(self._vwap_pv) / vsum) if vsum > 0 else price
        vwap_delta = 0.0 if self._prev_vwap is None else (vwap - self._prev_vwap)

        spread = tick.spread if tick.spread is not None else 0.0
        mid = tick.mid_price if tick.mid_price is not None else price

        # 상태 갱신
        self._prev_price = price
        self._prev_volume = vol
        self._prev_vwap = vwap

        return FeatureVector(
            ts_ns=tick.ts_ns,
            symbol=tick.symbol,
            obi=obi,
            obi_norm=obi_norm,
            volume_spike=volume_spike,
            micro_momentum=micro_momentum,
            vwap=vwap,
            vwap_delta=vwap_delta,
            spread=spread,
            mid_price=mid,
        )


def _zscore(value: float, hist: "deque[float]") -> float:
    n = len(hist)
    if n < 2:
        return 0.0
    mean = sum(hist) / n
    var = sum((x - mean) ** 2 for x in hist) / (n - 1)
    if var <= 0:
        return 0.0
    return (value - mean) / (var ** 0.5)
