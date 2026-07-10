"""RiskManager — 주문 전 사전 점검(pre-trade risk) + 서킷브레이커.

설계서 §8/§12 위험관리 대응:
    - 포지션 가치/수량 한도, 총노출 한도, 레버리지 상한
    - 당일 손절(-2%)·익절(+2%) → 도달 시 신규 진입 차단
    - 레이턴시 서킷브레이커: 처리 지연 > max_latency_ms → 신규 진입 일시 중단
    - 슬리피지 가드: 예상 슬리피지 > max_slippage_pct → 주문 거절
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import RiskConfig
from ..execution.portfolio import Portfolio
from ..types import Order, OrderSide


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    reason: str
    adjusted_qty: float = 0.0
    halted: bool = False  # 서킷브레이커로 인한 전체 중단 여부


class RiskManager:
    def __init__(self, config: RiskConfig, starting_equity: float) -> None:
        self.config = config
        self.starting_equity = starting_equity
        self._halted = False
        self._halt_reason = ""

    @property
    def halted(self) -> bool:
        return self._halted

    def update_circuit_breaker(self, *, latency_ms: float, equity: float) -> None:
        """매 틱 호출 — 레이턴시/일일 손익 한도로 전체 거래 중단 여부를 갱신한다."""
        cfg = self.config
        if latency_ms > cfg.max_latency_ms:
            self._halted = True
            self._halt_reason = f"latency {latency_ms:.2f}ms > {cfg.max_latency_ms}ms"
            return
        day_return = (equity - self.starting_equity) / self.starting_equity if self.starting_equity else 0.0
        if day_return <= -cfg.day_stop_loss_pct:
            self._halted = True
            self._halt_reason = f"day stop-loss hit ({day_return:.4f})"
            return
        if day_return >= cfg.day_take_profit_pct:
            self._halted = True
            self._halt_reason = f"day take-profit hit ({day_return:.4f})"
            return

    def reset_halt(self) -> None:
        self._halted = False
        self._halt_reason = ""

    def approve(
        self,
        order: Order,
        *,
        portfolio: Portfolio,
        prices: dict[str, float],
        expected_slippage_pct: float = 0.0,
    ) -> RiskDecision:
        cfg = self.config

        if self._halted:
            return RiskDecision(False, f"halted: {self._halt_reason}", 0.0, halted=True)

        if order.qty <= 0:
            return RiskDecision(False, "non-positive qty", 0.0)

        if expected_slippage_pct > cfg.max_slippage_pct:
            return RiskDecision(
                False,
                f"slippage {expected_slippage_pct:.4f} > {cfg.max_slippage_pct}",
                0.0,
            )

        price = prices.get(order.symbol)
        if price is None or price <= 0:
            return RiskDecision(False, "no price", 0.0)

        pos = portfolio.position(order.symbol)
        signed = order.qty if order.side == OrderSide.BUY else -order.qty
        projected_qty = pos.qty + signed

        # 1) 종목 수량 한도
        qty = order.qty
        if abs(projected_qty) > cfg.max_position_qty:
            allowed = cfg.max_position_qty - abs(pos.qty)
            if allowed <= 0:
                return RiskDecision(False, "max_position_qty reached", 0.0)
            qty = min(qty, allowed)

        # 2) 종목 가치 한도
        projected_value = abs(projected_qty) * price
        if projected_value > cfg.max_position_value:
            allowed_value = cfg.max_position_value - abs(pos.qty) * price
            if allowed_value <= 0:
                return RiskDecision(False, "max_position_value reached", 0.0)
            qty = min(qty, allowed_value / price)

        # 3) 총노출 한도
        gross = portfolio.gross_exposure(prices)
        add_exposure = qty * price
        if gross + add_exposure > cfg.max_gross_exposure:
            allowed = cfg.max_gross_exposure - gross
            if allowed <= 0:
                return RiskDecision(False, "max_gross_exposure reached", 0.0)
            qty = min(qty, allowed / price)

        # 4) 레버리지 상한(총노출 / 순자산 ≤ max_leverage)
        equity = portfolio.equity(prices)
        if equity > 0:
            projected_gross = gross + qty * price
            leverage = projected_gross / equity
            if leverage > cfg.max_leverage:
                allowed_gross = cfg.max_leverage * equity - gross
                if allowed_gross <= 0:
                    return RiskDecision(False, "max_leverage reached", 0.0)
                qty = min(qty, allowed_gross / price)

        qty = _round_down(qty)
        if qty <= 0:
            return RiskDecision(False, "qty reduced to zero by limits", 0.0)

        return RiskDecision(True, "ok", qty)


def _round_down(qty: float) -> float:
    # 정수 주식 단위로 내림(소수 주식 미지원 가정). 필요 시 정책 교체 지점.
    return float(int(qty))
