"""M5 — Order Router + FIX + 영속 테스트(설계서 §6). 의존성 없이 전부 로컬 검증."""
from __future__ import annotations

from daytrade.config import ExecutionConfig
from daytrade.execution import (
    FixExecutor,
    OrderRouter,
    PaperExecutor,
    SimulatedFixVenue,
    TradeStore,
)
from daytrade.execution import fix
from daytrade.types import MarketTick, Order, OrderBookLevel, OrderSide, OrderType


def _tick(symbol="AAPL", bid=99.99, ask=100.01, qty=1000.0, ts=1_000):
    return MarketTick(
        ts_ns=ts, symbol=symbol,
        bids=(OrderBookLevel(bid, qty),), asks=(OrderBookLevel(ask, qty),),
        last_price=(bid + ask) / 2, last_qty=10.0,
    )


# ---------------- FIX codec ----------------

def test_fix_roundtrip_checksum_and_bodylength():
    order = Order(symbol="AAPL", side=OrderSide.BUY, qty=100, order_type=OrderType.IOC, ts_ns=42)
    msg = fix.build_new_order_single(order, sender="C", target="V", seq_num=1, sending_time="20260624-00:00:00.000")
    assert msg.startswith("8=FIX.4.4\x01")
    assert "\x019=" in msg and msg.endswith("\x01")
    assert fix.verify_checksum(msg)
    tags = fix.decode(msg)
    assert tags[35] == "D" and tags[55] == "AAPL" and tags[54] == "1"
    assert tags[40] == "1" and tags[59] == fix.TIF_IOC  # IOC → ordtype market + TIF 3


def test_fix_checksum_detects_corruption():
    order = Order(symbol="X", side=OrderSide.SELL, qty=5, ts_ns=1)
    msg = fix.build_new_order_single(order, sender="C", target="V", seq_num=2, sending_time="t")
    corrupted = msg.replace("55=X", "55=Y")
    assert not fix.verify_checksum(corrupted)


def test_fix_limit_includes_price():
    order = Order(symbol="A", side=OrderSide.BUY, qty=1, order_type=OrderType.LIMIT, limit_price=123.5, ts_ns=1)
    tags = fix.decode(fix.build_new_order_single(order, sender="C", target="V", seq_num=1, sending_time="t"))
    assert tags[40] == "2" and float(tags[44]) == 123.5


# ---------------- FixExecutor + SimulatedFixVenue ----------------

def test_fix_executor_fills_via_wire():
    venue = SimulatedFixVenue(ExecutionConfig(paper_slippage_bps=1.0))
    ex = FixExecutor(venue)
    assert ex.is_live is False
    order = Order(symbol="AAPL", side=OrderSide.BUY, qty=100, order_type=OrderType.IOC, ts_ns=1000)
    fill = ex.submit(order, _tick())
    assert fill.status == "filled"
    assert fill.filled_qty == 100
    assert fill.avg_price > 100.0  # 매수 = ask + 슬리피지
    assert fill.slippage > 0  # mid 대비 불리


def test_fix_executor_partial_fill():
    venue = SimulatedFixVenue(ExecutionConfig(partial_fill=True))
    ex = FixExecutor(venue)
    order = Order(symbol="AAPL", side=OrderSide.BUY, qty=5000, order_type=OrderType.IOC, ts_ns=1)
    fill = ex.submit(order, _tick(qty=1000.0))
    assert fill.status == "partial"
    assert fill.filled_qty == 1000.0


# ---------------- OrderRouter ----------------

def test_router_assigns_idempotent_coid():
    captured = []
    router = OrderRouter(PaperExecutor(ExecutionConfig()), on_fill=captured.append)
    order = Order(symbol="AAPL", side=OrderSide.BUY, qty=10, order_type=OrderType.IOC, ts_ns=7)
    fill = router.submit(order, _tick())
    assert fill.status == "filled"
    assert fill.order.client_order_id  # 자동 부여
    assert len(captured) == 1
    assert router.stats.filled == 1


def test_router_slippage_guard_blocks():
    # 슬리피지 0.005 인데 한도 0.0001 → 차단(거절).
    router = OrderRouter(PaperExecutor(ExecutionConfig(paper_slippage_bps=50.0)), max_slippage_pct=0.0001)
    order = Order(symbol="AAPL", side=OrderSide.BUY, qty=10, order_type=OrderType.IOC, ts_ns=1)
    fill = router.submit(order, _tick())
    assert fill.status == "rejected"
    assert router.stats.slippage_blocks == 1


def test_router_requotes_rejected_limit():
    # 비마케터블 지정가(매수 90 < ask 100.01) → 거절 → 재견적(ask 로 끌어올림) → 체결.
    router = OrderRouter(PaperExecutor(ExecutionConfig()), max_requotes=1)
    order = Order(symbol="AAPL", side=OrderSide.BUY, qty=10, order_type=OrderType.LIMIT,
                  limit_price=90.0, ts_ns=1)
    fill = router.submit(order, _tick())
    assert fill.status == "filled"
    assert router.stats.requotes == 1


def test_router_live_flag_passthrough():
    assert OrderRouter(FixExecutor(SimulatedFixVenue())).is_live is False


# ---------------- Alpaca adapter(payload/parse, 네트워크 불요) ----------------

def test_alpaca_build_order_payload():
    from daytrade.execution import build_alpaca_order

    o = Order(symbol="AAPL", side=OrderSide.BUY, qty=10, order_type=OrderType.IOC,
              client_order_id="c1", ts_ns=1)
    p = build_alpaca_order(o)
    assert p == {"symbol": "AAPL", "qty": "10", "side": "buy", "type": "market",
                 "time_in_force": "ioc", "client_order_id": "c1"}
    lim = Order(symbol="X", side=OrderSide.SELL, qty=2, order_type=OrderType.LIMIT,
                limit_price=50.25, ts_ns=1)
    pl = build_alpaca_order(lim)
    assert pl["type"] == "limit" and pl["limit_price"] == "50.25" and pl["side"] == "sell"


def test_alpaca_parse_fill_and_reject():
    from daytrade.execution import parse_alpaca_fill

    o = Order(symbol="AAPL", side=OrderSide.BUY, qty=10, ts_ns=5)
    filled = parse_alpaca_fill({"status": "filled", "filled_qty": "10", "filled_avg_price": "100.5"}, o, ts_ns=5)
    assert filled.status == "filled" and filled.filled_qty == 10 and filled.avg_price == 100.5
    rej = parse_alpaca_fill({"status": "rejected"}, o, ts_ns=5)
    assert rej.status == "rejected" and rej.filled_qty == 0.0


def test_alpaca_executor_with_fake_session():
    from daytrade.execution import AlpacaExecutor

    class _Resp:
        def json(self):
            return {"status": "filled", "filled_qty": "10", "filled_avg_price": "100.0"}

    class _Sess:
        def __init__(self):
            self.calls = []

        def post(self, url, json, headers, timeout):
            self.calls.append((url, json))
            return _Resp()

    sess = _Sess()
    ex = AlpacaExecutor("k", "s", session=sess)
    assert ex.is_live is False  # paper 계좌 기본
    order = Order(symbol="AAPL", side=OrderSide.BUY, qty=10, order_type=OrderType.IOC, ts_ns=1)
    fill = ex.submit(order, _tick())
    assert fill.status == "filled" and fill.filled_qty == 10
    assert sess.calls[0][0].endswith("/v2/orders")


# ---------------- TradeStore ----------------

def test_pipeline_fill_events_persist_to_store():
    """페이퍼 봇 핵심 결선: TradingPipeline on_event(fill) → TradeStore 적재."""
    from daytrade.config import SignalConfig, TradingConfig, TradingMode
    from daytrade.feed.simulated import SimulatedFeed
    from daytrade.pipeline import TradingPipeline
    from daytrade.types import Fill, Order, OrderSide

    store = TradeStore(":memory:")
    rid = store.start_run(mode="paper", symbol="AAPL", started_at="t")

    def on_event(ev):
        if ev.get("event") != "fill":
            return
        order = Order(symbol=ev["symbol"], side=OrderSide(ev["side"]), qty=ev["qty"], ts_ns=0)
        store.record_fill(Fill(order=order, filled_qty=ev["qty"], avg_price=ev["price"],
                               ts_ns=0, slippage=ev["slippage"], status="filled"), run_id=rid)

    config = TradingConfig(mode=TradingMode.PAPER, symbols=("AAPL",),
                           signal=SignalConfig(depth=10, use_ai=False), seed=1)
    pipe = TradingPipeline(config, on_event=on_event)
    feed = SimulatedFeed(symbol="AAPL", n_ticks=2000, seed=1)
    for tick in feed.ticks():
        pipe.process_tick(tick)
    m = pipe.metrics.finalize()
    s = store.summary(rid)
    assert s["fills"] == m.fills
    store.close()


def test_trade_store_persist_and_summary():
    with TradeStore(":memory:") as store:
        rid = store.start_run(mode="paper", symbol="AAPL", started_at="2026-06-24T00:00:00Z")
        ex = PaperExecutor(ExecutionConfig(commission_bps=2.0))
        for i in range(3):
            order = Order(symbol="AAPL", side=OrderSide.BUY, qty=10, order_type=OrderType.IOC,
                          ts_ns=1000 + i, client_order_id=f"c{i}")
            store.record_fill(ex.submit(order, _tick(ts=1000 + i)))
        store.record_equity(1000, 1_000_000.0)
        store.record_equity(1003, 1_000_500.0)
        s = store.summary(rid)
        assert s["fills"] == 3
        assert s["total_qty"] == 30.0
        assert s["total_fee"] > 0
        assert s["start_equity"] == 1_000_000.0 and s["end_equity"] == 1_000_500.0
        assert s["equity_points"] == 2
