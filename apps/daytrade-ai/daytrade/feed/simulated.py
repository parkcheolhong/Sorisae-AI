"""합성(synthetic) 시장 데이터 피드 — 재현 가능한 단타 시뮬레이션용.

기하 브라운 운동(GBM) 기반 미드가격 + 오더북 깊이/불균형/체결량을 생성한다.
가끔 '이벤트'(거래량 급증 + 오더북 불균형 + 모멘텀)를 주입해 탐지 로직이 시그널을
잡을 수 있는 현실적 자극을 제공한다(테스트/데모 결정성 보장 — seed 고정).
"""
from __future__ import annotations

import math
from typing import Iterator

import numpy as np  # pyright: ignore[reportMissingImports]

from ..types import MarketTick, OrderBookLevel


class SimulatedFeed:
    """합성 틱 생성기.

    Args:
        symbol: 종목 코드.
        n_ticks: 생성할 틱 수.
        start_price: 시작가.
        depth: 오더북 레벨 수.
        tick_interval_ms: 틱 간 모델 시간 간격(ms) — 모멘텀/급증 계산 기준.
        volatility: 틱당 변동성(σ).
        seed: RNG 시드(재현성).
        event_prob: 틱마다 급변 이벤트가 시작될 확률.
    """

    def __init__(
        self,
        symbol: str = "AAPL",
        n_ticks: int = 5_000,
        start_price: float = 100.0,
        depth: int = 10,
        tick_interval_ms: float = 10.0,
        volatility: float = 0.02,
        seed: int | None = 42,
        event_prob: float = 0.01,
        base_qty: float = 50_000.0,
    ) -> None:
        self.symbol = symbol
        self.n_ticks = int(n_ticks)
        self.start_price = float(start_price)
        self.depth = int(depth)
        self.tick_interval_ms = float(tick_interval_ms)
        self.volatility = float(volatility)
        self.event_prob = float(event_prob)
        # 오더북 레벨당 기준 수량. 설계서 OBI 임계(≈1e6)와 정합되도록 현실적 규모로 둔다.
        self.base_qty = float(base_qty)
        self._rng = np.random.default_rng(seed)

    def ticks(self) -> Iterator[MarketTick]:
        rng = self._rng
        price = self.start_price
        ts_ns = 0
        interval_ns = int(self.tick_interval_ms * 1_000_000)
        base_qty = self.base_qty

        # 진행 중 이벤트 상태: (남은 틱 수, 방향[+1/-1], 강도)
        event_left = 0
        event_dir = 0
        event_mag = 0.0

        for _ in range(self.n_ticks):
            # --- 이벤트 점화 ---
            if event_left <= 0 and rng.random() < self.event_prob:
                event_left = int(rng.integers(5, 25))
                event_dir = 1 if rng.random() < 0.5 else -1
                event_mag = float(rng.uniform(2.0, 5.0))

            drift = 0.0
            imbalance_bias = 0.0
            vol_mult = 1.0
            if event_left > 0:
                drift = event_dir * self.volatility * event_mag
                imbalance_bias = event_dir * event_mag
                vol_mult = event_mag
                event_left -= 1

            # --- 미드가격 진행(GBM 유사) ---
            shock = rng.normal(0.0, self.volatility)
            price = max(0.01, price * math.exp((drift + shock) / 100.0))

            spread = max(0.01, price * 0.0002)  # 2bp 스프레드
            best_bid = price - spread / 2.0
            best_ask = price + spread / 2.0

            # --- 오더북 레벨 생성(불균형 반영) ---
            bid_levels: list[OrderBookLevel] = []
            ask_levels: list[OrderBookLevel] = []
            for i in range(self.depth):
                level_price_bid = best_bid - i * spread
                level_price_ask = best_ask + i * spread
                decay = math.exp(-0.15 * i)
                bid_qty = base_qty * decay * (1.0 + max(0.0, imbalance_bias)) * float(rng.uniform(0.7, 1.3))
                ask_qty = base_qty * decay * (1.0 + max(0.0, -imbalance_bias)) * float(rng.uniform(0.7, 1.3))
                bid_levels.append(OrderBookLevel(price=round(level_price_bid, 4), qty=round(bid_qty, 2)))
                ask_levels.append(OrderBookLevel(price=round(level_price_ask, 4), qty=round(ask_qty, 2)))

            trade_vol = base_qty * vol_mult * float(rng.uniform(0.2, 1.0))

            ts_ns += interval_ns
            yield MarketTick(
                ts_ns=ts_ns,
                symbol=self.symbol,
                bids=tuple(bid_levels),
                asks=tuple(ask_levels),
                last_price=round(price, 4),
                last_qty=round(trade_vol, 2),
            )
