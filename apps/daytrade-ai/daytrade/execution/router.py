"""OrderRouter — 스마트 주문 라우팅(설계서 §6 Order Router / Execution Engine).

기존 `OrderExecutor`(PaperExecutor·FixExecutor 등)를 감싸 다음을 더한다:
  - **멱등 client_order_id**: 미지정 시 결정적 ID 부여(중복 전송 방지·체결 추적).
  - **슬리피지 가드**: 체결 슬리피지가 한도를 넘으면 해당 체결을 거절 처리(불리한 체결 차단).
  - **재견적(re-quote)**: 지정가가 거절되면 더 공격적으로(스프레드 횡단) 재호가해 재시도(같은 틱 내 N회).
  - **체결 피드백 콜백**: 승인된 각 체결을 `on_fill(fill)` 로 통지(상태 영속·재학습 데이터 수집 훅).

자체가 `OrderExecutor` 이므로 파이프라인/봇에 그대로 끼울 수 있다(드롭인).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..types import Fill, MarketTick, Order, OrderSide, OrderType
from .base import OrderExecutor


@dataclass
class RouterStats:
    submitted: int = 0
    filled: int = 0
    partial: int = 0
    rejected: int = 0
    requotes: int = 0
    slippage_blocks: int = 0
    errors: int = 0           # 실행기 예외(브로커 단절 등)를 흡수한 횟수.

    def as_dict(self) -> dict:
        return {
            "submitted": self.submitted, "filled": self.filled, "partial": self.partial,
            "rejected": self.rejected, "requotes": self.requotes,
            "slippage_blocks": self.slippage_blocks, "errors": self.errors,
        }


class OrderRouter(OrderExecutor):
    def __init__(
        self,
        executor: OrderExecutor,
        *,
        max_slippage_pct: float | None = None,
        max_requotes: int = 1,
        on_fill: Callable[[Fill], None] | None = None,
        coid_prefix: str = "DT",
    ) -> None:
        self.executor = executor
        self.max_slippage_pct = max_slippage_pct
        self.max_requotes = max(0, int(max_requotes))
        self.on_fill = on_fill
        self.coid_prefix = coid_prefix
        self.stats = RouterStats()
        self._counter = 0

    @property
    def is_live(self) -> bool:
        return self.executor.is_live

    def _next_coid(self, order: Order) -> str:
        self._counter += 1
        return f"{self.coid_prefix}-{order.symbol}-{order.ts_ns}-{self._counter}"

    def _with(self, order: Order, **changes) -> Order:
        return Order(
            symbol=changes.get("symbol", order.symbol),
            side=changes.get("side", order.side),
            qty=changes.get("qty", order.qty),
            order_type=changes.get("order_type", order.order_type),
            limit_price=changes.get("limit_price", order.limit_price),
            ts_ns=changes.get("ts_ns", order.ts_ns),
            client_order_id=changes.get("client_order_id", order.client_order_id),
        )

    def submit(self, order: Order, tick: MarketTick) -> Fill:
        self.stats.submitted += 1
        if not order.client_order_id:
            order = self._with(order, client_order_id=self._next_coid(order))

        attempt = order
        last_reject: Fill | None = None
        for requote in range(self.max_requotes + 1):
            # 실행기 예외(브로커 단절·타임아웃 등)는 거절로 흡수 → 파이프라인 크래시 방지.
            try:
                fill = self.executor.submit(attempt, tick)
            except Exception:  # noqa: BLE001 — chaos 내성: 예외를 거절로 격하
                self.stats.errors += 1
                last_reject = Fill(order=attempt, filled_qty=0.0, avg_price=0.0,
                                   ts_ns=tick.ts_ns, status="rejected")
                if requote < self.max_requotes and attempt.order_type == OrderType.LIMIT:
                    aggressive = self._requote_price(attempt, tick)
                    if aggressive is not None:
                        self.stats.requotes += 1
                        attempt = self._with(attempt, limit_price=aggressive)
                        continue
                break

            # 슬리피지 가드: 한도 초과 체결은 거절로 간주(승인하지 않음).
            if (
                self.max_slippage_pct is not None
                and fill.status in ("filled", "partial")
                and abs(fill.slippage) > self.max_slippage_pct
            ):
                self.stats.slippage_blocks += 1
                last_reject = Fill(order=attempt, filled_qty=0.0, avg_price=0.0,
                                   ts_ns=tick.ts_ns, status="rejected")
                break  # 슬리피지 과다 → 재견적해도 동일, 즉시 중단

            if fill.status in ("filled", "partial"):
                if fill.status == "filled":
                    self.stats.filled += 1
                else:
                    self.stats.partial += 1
                if self.on_fill:
                    self.on_fill(fill)
                return fill

            # 거절: 지정가였다면 더 공격적으로 재호가(스프레드 횡단) 후 재시도.
            last_reject = fill
            if requote < self.max_requotes and attempt.order_type == OrderType.LIMIT:
                aggressive = self._requote_price(attempt, tick)
                if aggressive is not None:
                    self.stats.requotes += 1
                    attempt = self._with(attempt, limit_price=aggressive)
                    continue
            break

        self.stats.rejected += 1
        return last_reject or Fill(order=order, filled_qty=0.0, avg_price=0.0,
                                   ts_ns=tick.ts_ns, status="rejected")

    @staticmethod
    def _requote_price(order: Order, tick: MarketTick) -> float | None:
        """지정가를 반대 호가 best 로 끌어올려(매수=ask, 매도=bid) 즉시 체결 가능하게."""
        if order.side == OrderSide.BUY and tick.best_ask is not None:
            return tick.best_ask
        if order.side == OrderSide.SELL and tick.best_bid is not None:
            return tick.best_bid
        return None
