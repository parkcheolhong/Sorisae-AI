"""인프로세스 장애 주입(chaos) 테스트 — 끊김/드롭/손상 피드 + 거부/예외/부분체결 실행기.

Chaos-Mesh 없이 `LiveRunner` 의 자동 재연결·회복과 실행기 장애 내성을 결정론적으로 검증한다.
"""
from __future__ import annotations

import pytest

from daytrade.config import SignalConfig, TradingConfig
from daytrade.execution.base import OrderExecutor
from daytrade.feed.memory import ListFeed
from daytrade.monitoring import AuditLog
from daytrade.ops import LiveRunner, RunnerConfig
from daytrade.pipeline import TradingPipeline
from daytrade.testing import FaultInjectingFeed, FlakyExecutor, FlakyFeedFactory
from daytrade.types import Fill, MarketTick, Order, OrderBookLevel, OrderSide, OrderType


def _tick(i, price=100.0):
    return MarketTick(ts_ns=i, symbol="AAPL",
                      bids=(OrderBookLevel(price - 0.01, 1000.0),),
                      asks=(OrderBookLevel(price + 0.01, 1000.0),),
                      last_price=price, last_qty=10.0)


def _pipeline():
    return TradingPipeline(TradingConfig(symbols=("AAPL",), signal=SignalConfig(use_ai=False)))


# ── FaultInjectingFeed ──

def test_feed_disconnect_after_raises():
    feed = FaultInjectingFeed(ListFeed([_tick(i) for i in range(10)]), disconnect_after=4)
    got = []
    with pytest.raises(ConnectionError):
        for t in feed.ticks():
            got.append(t)
    assert len(got) == 4


def test_feed_drop_indices_skips():
    feed = FaultInjectingFeed(ListFeed([_tick(i) for i in range(6)]), drop_indices={1, 3})
    out = list(feed.ticks())
    assert [t.ts_ns for t in out] == [0, 2, 4, 5]


def test_feed_corrupt_empties_book():
    feed = FaultInjectingFeed(ListFeed([_tick(i) for i in range(4)]), corrupt_indices={2})
    out = list(feed.ticks())
    assert out[2].bids == () and out[2].asks == ()
    assert out[0].bids and out[1].asks  # 다른 틱은 정상


def test_feed_latency_calls_sleep():
    calls = []
    feed = FaultInjectingFeed(ListFeed([_tick(i) for i in range(4)]),
                              latency_indices={1, 2}, sleep=calls.append, latency_sec=0.02)
    list(feed.ticks())
    assert calls == [0.02, 0.02]


# ── FlakyFeedFactory + LiveRunner 회복 ──

def test_runner_recovers_after_flaky_sessions():
    factory = FlakyFeedFactory(
        lambda: ListFeed([_tick(i) for i in range(5)]),
        fail_sessions=2, disconnect_after=3)
    sleeps: list[float] = []
    runner = LiveRunner(
        _pipeline(), feed_factory=factory,
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=11),
        sleep=sleeps.append, mono=lambda: 0.0)
    summary = runner.run()
    # 실패 세션 2회(각 3틱) + 회복 세션(5틱) = 3+3+5 = 11 에서 정지.
    assert summary["ticks"] == 11
    assert summary["reconnects"] >= 2
    assert len(sleeps) >= 2          # 세션 사이 백오프


def test_runner_audits_feed_error(tmp_path):
    import json

    audit_path = tmp_path / "audit.jsonl"
    audit = AuditLog(str(audit_path))
    factory = FlakyFeedFactory(
        lambda: ListFeed([_tick(i) for i in range(5)]),
        fail_sessions=1, disconnect_after=3)
    runner = LiveRunner(
        _pipeline(), feed_factory=factory,
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=8),
        audit=audit, sleep=lambda s: None, mono=lambda: 0.0)
    runner.run()
    events = [json.loads(ln)["event"] for ln in audit_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert "feed_error" in events        # 주입된 ConnectionError 가 감사에 기록
    assert "feed_disconnect" in events   # 재연결 경계
    assert audit.verify().ok             # 해시 체인 무결


# ── FlakyExecutor ──

class _Inner(OrderExecutor):
    def submit(self, order: Order, tick: MarketTick) -> Fill:
        return Fill(order=order, filled_qty=order.qty, avg_price=tick.last_price,
                    ts_ns=tick.ts_ns, status="filled")


def _order(qty=10.0):
    return Order(symbol="AAPL", side=OrderSide.BUY, qty=qty, order_type=OrderType.MARKET)


def test_flaky_executor_reject_raise_partial():
    ex = FlakyExecutor(_Inner(), reject_indices={1}, raise_indices={2}, partial_indices={3},
                       partial_ratio=0.5)
    t = _tick(0)
    f0 = ex.submit(_order(), t)
    assert f0.status == "filled" and f0.filled_qty == 10.0
    f1 = ex.submit(_order(), t)
    assert f1.status == "rejected" and f1.filled_qty == 0.0
    with pytest.raises(ConnectionError):
        ex.submit(_order(), t)
    f3 = ex.submit(_order(qty=10.0), t)
    assert f3.status == "partial" and f3.filled_qty == 5.0


def test_flaky_executor_passthrough_is_live():
    inner = _Inner()
    ex = FlakyExecutor(inner)
    assert ex.is_live == inner.is_live
    assert ex.submit(_order(), _tick(0)).status == "filled"
