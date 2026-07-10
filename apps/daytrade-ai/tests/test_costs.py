from daytrade.config import ExecutionConfig
from daytrade.execution.paper import PaperExecutor
from daytrade.execution.portfolio import Portfolio
from daytrade.types import MarketTick, Order, OrderBookLevel, OrderSide, OrderType


def tick(price=100.0, bid_qty=1000.0, ask_qty=1000.0):
    bids = (OrderBookLevel(price - 0.05, bid_qty),)
    asks = (OrderBookLevel(price + 0.05, ask_qty),)
    return MarketTick(ts_ns=1, symbol="T", bids=bids, asks=asks, last_price=price, last_qty=10)


def test_commission_applied_on_buy():
    ex = PaperExecutor(ExecutionConfig(paper_slippage_bps=0, commission_bps=10))  # 0.1%
    fill = ex.submit(Order(symbol="T", side=OrderSide.BUY, qty=100, order_type=OrderType.IOC), tick())
    # notional ~ 100 * 100.05 = 10005 → fee ~ 10.005
    assert fill.fee > 0
    assert abs(fill.fee - (100 * 100.05) * 0.001) < 1e-6


def test_sell_tax_only_on_sell():
    ex = PaperExecutor(ExecutionConfig(paper_slippage_bps=0, commission_bps=0, sell_tax_bps=20))
    buy_fill = ex.submit(Order(symbol="T", side=OrderSide.BUY, qty=100, order_type=OrderType.IOC), tick())
    sell_fill = ex.submit(Order(symbol="T", side=OrderSide.SELL, qty=100, order_type=OrderType.IOC), tick())
    assert buy_fill.fee == 0.0
    assert sell_fill.fee > 0.0


def test_partial_fill_limited_to_top_level_qty():
    ex = PaperExecutor(ExecutionConfig(partial_fill=True))
    fill = ex.submit(
        Order(symbol="T", side=OrderSide.BUY, qty=5000, order_type=OrderType.IOC),
        tick(ask_qty=300.0),
    )
    assert fill.status == "partial"
    assert fill.filled_qty == 300.0


def test_partial_fill_full_when_enough_liquidity():
    ex = PaperExecutor(ExecutionConfig(partial_fill=True))
    fill = ex.submit(
        Order(symbol="T", side=OrderSide.BUY, qty=100, order_type=OrderType.IOC),
        tick(ask_qty=1000.0),
    )
    assert fill.status == "filled"
    assert fill.filled_qty == 100


def test_fee_reduces_cash_and_realized_pnl():
    pf = Portfolio(starting_cash=100_000)
    ex = PaperExecutor(ExecutionConfig(paper_slippage_bps=0, commission_bps=10))
    fill = ex.submit(Order(symbol="T", side=OrderSide.BUY, qty=100, order_type=OrderType.IOC), tick())
    pf.apply_fill(fill)
    notional = 100 * 100.05
    assert abs(pf.cash - (100_000 - notional - fill.fee)) < 1e-6
    assert pf.position("T").realized_pnl == -fill.fee


def test_round_trip_pnl_net_of_costs():
    pf = Portfolio(starting_cash=100_000)
    ex = PaperExecutor(ExecutionConfig(paper_slippage_bps=0, commission_bps=10, sell_tax_bps=10))
    pf.apply_fill(ex.submit(Order(symbol="T", side=OrderSide.BUY, qty=100, order_type=OrderType.IOC), tick(100.0)))
    pf.apply_fill(ex.submit(Order(symbol="T", side=OrderSide.SELL, qty=100, order_type=OrderType.IOC), tick(100.0)))
    # 가격 동일 왕복 → 비용만큼 손실(음수)
    assert pf.position("T").qty == 0
    assert pf.realized_pnl() < 0
