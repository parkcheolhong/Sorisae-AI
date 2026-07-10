"""(다) OrderRouter 장애 주입 복원력 — FlakyExecutor 로 거부/예외/부분체결 주입.

라우터의 멱등 COID·재견적·슬리피지 가드·예외 흡수 동작을 chaos 하에서 검증한다.
"""
from __future__ import annotations

from daytrade.execution.base import OrderExecutor
from daytrade.execution.router import OrderRouter
from daytrade.testing import FlakyExecutor
from daytrade.types import Fill, MarketTick, Order, OrderBookLevel, OrderSide, OrderType


def _tick(price=100.0):
    return MarketTick(ts_ns=42, symbol="AAPL",
                      bids=(OrderBookLevel(price - 0.01, 1000.0),),
                      asks=(OrderBookLevel(price + 0.01, 1000.0),),
                      last_price=price, last_qty=10.0)


class _Filler(OrderExecutor):
    """항상 전량 체결하는 내부 실행기(슬리피지 0)."""

    def __init__(self, slippage=0.0):
        self.slippage = slippage
        self.calls = 0

    def submit(self, order: Order, tick: MarketTick) -> Fill:
        self.calls += 1
        return Fill(order=order, filled_qty=order.qty, avg_price=tick.last_price,
                    ts_ns=tick.ts_ns, slippage=self.slippage, status="filled")


def _order(otype=OrderType.MARKET, coid=""):
    return Order(symbol="AAPL", side=OrderSide.BUY, qty=10.0, order_type=otype,
                 limit_price=100.0 if otype == OrderType.LIMIT else None,
                 ts_ns=42, client_order_id=coid)


def test_idempotent_coid_assigned_and_preserved():
    router = OrderRouter(_Filler())
    f1 = router.submit(_order(), _tick())
    assert f1.order.client_order_id.startswith("DT-AAPL-")     # 자동 부여
    f2 = router.submit(_order(coid="MY-ID"), _tick())
    assert f2.order.client_order_id == "MY-ID"                 # 지정값 보존


def test_market_reject_not_requoted():
    # 시장가 거부 → 재견적 대상 아님 → 즉시 거절.
    router = OrderRouter(FlakyExecutor(_Filler(), reject_indices={0}), max_requotes=2)
    fill = router.submit(_order(OrderType.MARKET), _tick())
    assert fill.status == "rejected"
    assert router.stats.rejected == 1 and router.stats.requotes == 0


def test_limit_reject_then_requote_fills():
    # 지정가 첫 시도 거부 → 공격적 재견적(ask 횡단) → 두번째 시도 체결.
    router = OrderRouter(FlakyExecutor(_Filler(), reject_indices={0}), max_requotes=1)
    fill = router.submit(_order(OrderType.LIMIT), _tick(price=100.0))
    assert fill.status == "filled"
    assert router.stats.requotes == 1 and router.stats.filled == 1
    assert fill.order.limit_price == _tick().best_ask     # 재호가 가격 = best ask


def test_slippage_guard_blocks():
    # 큰 슬리피지 체결 → 가드가 거절로 격하.
    router = OrderRouter(_Filler(slippage=5.0), max_slippage_pct=1.0)
    fill = router.submit(_order(), _tick())
    assert fill.status == "rejected"
    assert router.stats.slippage_blocks == 1


def test_broker_exception_absorbed_as_reject():
    # 실행기 예외(브로커 단절) → 크래시 없이 거절로 흡수.
    router = OrderRouter(FlakyExecutor(_Filler(), raise_indices={0}))
    fill = router.submit(_order(OrderType.MARKET), _tick())
    assert fill.status == "rejected"
    assert router.stats.errors == 1 and router.stats.rejected == 1


def test_limit_exception_then_requote_recovers():
    # 지정가 첫 시도 예외 → 재견적 → 두번째 시도 체결(예외 후 회복).
    router = OrderRouter(FlakyExecutor(_Filler(), raise_indices={0}), max_requotes=1)
    fill = router.submit(_order(OrderType.LIMIT), _tick())
    assert fill.status == "filled"
    assert router.stats.errors == 1 and router.stats.requotes == 1


def test_partial_fill_reported():
    router = OrderRouter(FlakyExecutor(_Filler(), partial_indices={0}, partial_ratio=0.5))
    fill = router.submit(_order(), _tick())
    assert fill.status == "partial" and fill.filled_qty == 5.0
    assert router.stats.partial == 1


def test_stats_dict_includes_errors():
    assert "errors" in OrderRouter(_Filler()).stats.as_dict()
