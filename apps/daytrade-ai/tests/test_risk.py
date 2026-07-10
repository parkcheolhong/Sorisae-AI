from daytrade.config import RiskConfig
from daytrade.execution.portfolio import Portfolio
from daytrade.risk.manager import RiskManager
from daytrade.types import Order, OrderSide


def mk_order(qty, side=OrderSide.BUY):
    return Order(symbol="T", side=side, qty=qty)


def test_approves_within_limits():
    rm = RiskManager(RiskConfig(max_position_qty=1000, max_position_value=1e9, max_gross_exposure=1e9, max_leverage=10), starting_equity=100_000)
    pf = Portfolio(starting_cash=100_000)
    d = rm.approve(mk_order(100), portfolio=pf, prices={"T": 50.0})
    assert d.approved
    assert d.adjusted_qty == 100


def test_caps_qty_to_position_limit():
    rm = RiskManager(RiskConfig(max_position_qty=120, max_position_value=1e9, max_gross_exposure=1e9, max_leverage=10), starting_equity=100_000)
    pf = Portfolio(starting_cash=100_000)
    d = rm.approve(mk_order(500), portfolio=pf, prices={"T": 50.0})
    assert d.approved
    assert d.adjusted_qty == 120


def test_rejects_when_slippage_too_high():
    rm = RiskManager(RiskConfig(max_slippage_pct=0.001), starting_equity=100_000)
    pf = Portfolio(starting_cash=100_000)
    d = rm.approve(mk_order(100), portfolio=pf, prices={"T": 50.0}, expected_slippage_pct=0.01)
    assert not d.approved


def test_leverage_limit_caps_exposure():
    rm = RiskManager(RiskConfig(max_position_qty=1e9, max_position_value=1e9, max_gross_exposure=1e9, max_leverage=1.0), starting_equity=100_000)
    pf = Portfolio(starting_cash=100_000)
    # price 50 → max gross = 100_000 → max 2000 shares
    d = rm.approve(mk_order(5000), portfolio=pf, prices={"T": 50.0})
    assert d.approved
    assert d.adjusted_qty == 2000


def test_latency_circuit_breaker_halts():
    rm = RiskManager(RiskConfig(max_latency_ms=5.0), starting_equity=100_000)
    rm.update_circuit_breaker(latency_ms=20.0, equity=100_000)
    assert rm.halted
    pf = Portfolio(starting_cash=100_000)
    d = rm.approve(mk_order(100), portfolio=pf, prices={"T": 50.0})
    assert not d.approved
    assert d.halted


def test_day_stop_loss_halts():
    rm = RiskManager(RiskConfig(day_stop_loss_pct=0.02), starting_equity=100_000)
    rm.update_circuit_breaker(latency_ms=0.1, equity=97_000)  # -3%
    assert rm.halted
