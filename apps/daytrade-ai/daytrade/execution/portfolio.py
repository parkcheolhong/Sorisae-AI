"""Portfolio — 현금/포지션/실현손익 회계.

부호 있는 포지션(롱+/숏−)을 지원하며, 체결이 포지션을 늘리거나(증가) 줄이거나(감소)
부호를 넘길 때(flip) 평균단가·실현손익을 정확히 갱신한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..types import Fill, OrderSide, Position


@dataclass(slots=True)
class Portfolio:
    starting_cash: float = 1_000_000.0
    cash: float = field(default=0.0)
    positions: dict[str, Position] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.cash == 0.0:
            self.cash = self.starting_cash

    def position(self, symbol: str) -> Position:
        pos = self.positions.get(symbol)
        if pos is None:
            pos = Position(symbol=symbol)
            self.positions[symbol] = pos
        return pos

    def apply_fill(self, fill: Fill) -> None:
        if fill.filled_qty <= 0 or fill.status == "rejected":
            return
        pos = self.position(fill.order.symbol)
        signed = fill.filled_qty if fill.order.side == OrderSide.BUY else -fill.filled_qty
        price = fill.avg_price

        # 현금 이동: 매수 -금액, 매도 +금액. 수수료+세금(fee)은 항상 현금 차감.
        self.cash -= signed * price
        self.cash -= fill.fee
        if fill.fee:
            pos.realized_pnl -= fill.fee

        old_qty = pos.qty
        new_qty = old_qty + signed

        if old_qty == 0 or (old_qty > 0) == (signed > 0):
            # 신규 진입 또는 같은 방향 증가 → 가중평균 단가
            total_cost = pos.avg_entry * abs(old_qty) + price * abs(signed)
            pos.avg_entry = total_cost / abs(new_qty) if new_qty != 0 else 0.0
        else:
            # 반대 방향(감소 또는 flip) → 청산분 실현손익 인식
            closing = min(abs(signed), abs(old_qty))
            direction = 1.0 if old_qty > 0 else -1.0
            pos.realized_pnl += (price - pos.avg_entry) * closing * direction
            if abs(signed) > abs(old_qty):
                # flip: 남은 수량은 새 방향의 신규 진입
                pos.avg_entry = price
            elif new_qty == 0:
                pos.avg_entry = 0.0
            # 부분 감소면 avg_entry 유지

        pos.qty = new_qty

    def realized_pnl(self) -> float:
        return sum(p.realized_pnl for p in self.positions.values())

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        total = 0.0
        for sym, pos in self.positions.items():
            px = prices.get(sym)
            if px is not None:
                total += pos.unrealized_pnl(px)
        return total

    def equity(self, prices: dict[str, float]) -> float:
        """순자산 = 현금 + 보유 포지션 시가평가."""
        market = 0.0
        for sym, pos in self.positions.items():
            px = prices.get(sym)
            if px is not None:
                market += pos.market_value(px)
        return self.cash + market

    def gross_exposure(self, prices: dict[str, float]) -> float:
        total = 0.0
        for sym, pos in self.positions.items():
            px = prices.get(sym)
            if px is not None:
                total += abs(pos.market_value(px))
        return total
