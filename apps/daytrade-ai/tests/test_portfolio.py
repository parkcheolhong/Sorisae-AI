from daytrade.execution.portfolio import Portfolio
from daytrade.types import Fill, Order, OrderSide


def buy(symbol, qty, price, ts=1):
    return Fill(order=Order(symbol=symbol, side=OrderSide.BUY, qty=qty), filled_qty=qty, avg_price=price, ts_ns=ts)


def sell(symbol, qty, price, ts=1):
    return Fill(order=Order(symbol=symbol, side=OrderSide.SELL, qty=qty), filled_qty=qty, avg_price=price, ts_ns=ts)


def test_buy_updates_cash_and_avg_entry():
    pf = Portfolio(starting_cash=100_000)
    pf.apply_fill(buy("T", 100, 50.0))
    pos = pf.position("T")
    assert pos.qty == 100
    assert pos.avg_entry == 50.0
    assert pf.cash == 100_000 - 5_000


def test_weighted_average_on_scale_in():
    pf = Portfolio(starting_cash=100_000)
    pf.apply_fill(buy("T", 100, 50.0))
    pf.apply_fill(buy("T", 100, 60.0))
    pos = pf.position("T")
    assert pos.qty == 200
    assert pos.avg_entry == 55.0


def test_realized_pnl_on_close():
    pf = Portfolio(starting_cash=100_000)
    pf.apply_fill(buy("T", 100, 50.0))
    pf.apply_fill(sell("T", 100, 55.0))
    pos = pf.position("T")
    assert pos.qty == 0
    assert round(pos.realized_pnl, 6) == 500.0  # (55-50)*100


def test_flip_long_to_short():
    pf = Portfolio(starting_cash=100_000)
    pf.apply_fill(buy("T", 100, 50.0))
    pf.apply_fill(sell("T", 150, 55.0))  # close 100 + open short 50
    pos = pf.position("T")
    assert pos.qty == -50
    assert pos.avg_entry == 55.0
    assert round(pos.realized_pnl, 6) == 500.0


def test_equity_includes_market_value():
    pf = Portfolio(starting_cash=100_000)
    pf.apply_fill(buy("T", 100, 50.0))
    # cash 95_000 + 100 * 60 = 101_000
    assert pf.equity({"T": 60.0}) == 101_000
