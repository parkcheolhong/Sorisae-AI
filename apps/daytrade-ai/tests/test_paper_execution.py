from daytrade.config import ExecutionConfig
from daytrade.execution.paper import PaperExecutor
from daytrade.types import MarketTick, Order, OrderBookLevel, OrderSide, OrderType


def tick(price=100.0):
    bids = (OrderBookLevel(price - 0.05, 1000),)
    asks = (OrderBookLevel(price + 0.05, 1000),)
    return MarketTick(ts_ns=1, symbol="T", bids=bids, asks=asks, last_price=price, last_qty=10)


def test_market_buy_fills_at_ask_with_slippage():
    ex = PaperExecutor(ExecutionConfig(paper_slippage_bps=10))
    fill = ex.submit(Order(symbol="T", side=OrderSide.BUY, qty=100, order_type=OrderType.IOC), tick(100.0))
    assert fill.status == "filled"
    assert fill.filled_qty == 100
    # ask=100.05, +10bps
    assert fill.avg_price > 100.05
    assert fill.slippage > 0


def test_market_sell_fills_at_bid_with_slippage():
    ex = PaperExecutor(ExecutionConfig(paper_slippage_bps=10))
    fill = ex.submit(Order(symbol="T", side=OrderSide.SELL, qty=100, order_type=OrderType.IOC), tick(100.0))
    assert fill.status == "filled"
    assert fill.avg_price < 99.95


def test_limit_buy_rejected_when_price_too_low():
    ex = PaperExecutor(ExecutionConfig())
    order = Order(symbol="T", side=OrderSide.BUY, qty=100, order_type=OrderType.LIMIT, limit_price=99.0)
    fill = ex.submit(order, tick(100.0))
    assert fill.status == "rejected"


def test_reject_probability_one_always_rejects():
    ex = PaperExecutor(ExecutionConfig(paper_reject_prob=1.0))
    fill = ex.submit(Order(symbol="T", side=OrderSide.BUY, qty=100), tick(100.0))
    assert fill.status == "rejected"


def test_executor_is_not_live():
    assert PaperExecutor().is_live is False
