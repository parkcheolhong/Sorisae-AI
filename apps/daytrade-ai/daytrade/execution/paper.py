"""PaperExecutor — 모의투자 체결기(기본·안전). 실주문 없음.

체결 모델:
    - 시장가/IOC: 매수는 best_ask, 매도는 best_bid 에서 체결하고, 추가로
      ``paper_slippage_bps`` 만큼 불리하게 슬리피지를 적용한다(현실적 비용 반영).
    - 지정가: 가격이 도달 가능한 경우에만 체결(아니면 거절).
    - ``paper_reject_prob`` 확률로 거절(거래소 거절 시뮬레이션, 기본 0).
슬리피지는 의도가(mid 또는 limit) 대비 체결가 차이로 측정한다.
"""
from __future__ import annotations

import numpy as np  # pyright: ignore[reportMissingImports]

from ..config import ExecutionConfig
from ..types import Fill, MarketTick, Order, OrderSide, OrderType


class PaperExecutor:
    def __init__(self, config: ExecutionConfig | None = None, seed: int | None = 7) -> None:
        self.config = config or ExecutionConfig()
        self._rng = np.random.default_rng(seed)

    @property
    def is_live(self) -> bool:
        return False

    def submit(self, order: Order, tick: MarketTick) -> Fill:
        cfg = self.config

        if cfg.paper_reject_prob > 0 and self._rng.random() < cfg.paper_reject_prob:
            return Fill(order=order, filled_qty=0.0, avg_price=0.0, ts_ns=tick.ts_ns, status="rejected")

        mid = tick.mid_price
        best_bid = tick.best_bid
        best_ask = tick.best_ask
        if mid is None or best_bid is None or best_ask is None:
            return Fill(order=order, filled_qty=0.0, avg_price=0.0, ts_ns=tick.ts_ns, status="rejected")

        slip_frac = cfg.paper_slippage_bps / 10_000.0
        intended = mid

        if order.order_type == OrderType.LIMIT and order.limit_price is not None:
            if order.side == OrderSide.BUY and best_ask > order.limit_price:
                return Fill(order=order, filled_qty=0.0, avg_price=0.0, ts_ns=tick.ts_ns, status="rejected")
            if order.side == OrderSide.SELL and best_bid < order.limit_price:
                return Fill(order=order, filled_qty=0.0, avg_price=0.0, ts_ns=tick.ts_ns, status="rejected")
            intended = order.limit_price
            fill_price = order.limit_price
        else:
            # 시장가/IOC: 반대 호가에서 체결 + 불리한 슬리피지
            if order.side == OrderSide.BUY:
                fill_price = best_ask * (1.0 + slip_frac)
            else:
                fill_price = best_bid * (1.0 - slip_frac)

        if order.side == OrderSide.BUY:
            slippage = (fill_price - intended) / intended if intended else 0.0
        else:
            slippage = (intended - fill_price) / intended if intended else 0.0

        # 부분체결: 반대 호가 best 레벨 가용 수량까지만 체결.
        filled_qty = order.qty
        status = "filled"
        if cfg.partial_fill:
            opposite = tick.asks if order.side == OrderSide.BUY else tick.bids
            available = opposite[0].qty if opposite else 0.0
            if available <= 0:
                return Fill(order=order, filled_qty=0.0, avg_price=0.0, ts_ns=tick.ts_ns, status="rejected")
            if available < filled_qty:
                filled_qty = available
                status = "partial"

        # 비용: 수수료(매수·매도 공통) + 거래세(매도).
        notional = filled_qty * fill_price
        fee = notional * (cfg.commission_bps / 10_000.0)
        if order.side == OrderSide.SELL:
            fee += notional * (cfg.sell_tax_bps / 10_000.0)

        return Fill(
            order=order,
            filled_qty=filled_qty,
            avg_price=round(fill_price, 6),
            ts_ns=tick.ts_ns,
            slippage=slippage,
            fee=round(fee, 6),
            status=status,
        )
