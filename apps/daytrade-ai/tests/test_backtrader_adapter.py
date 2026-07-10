"""Backtrader 어댑터 테스트 — 의존성 없는 OHLCV 집계 코어 + bt 결선(설치 시)."""
from __future__ import annotations

import pytest

from daytrade.backtest import Bar, has_backtrader, ticks_to_ohlcv
from daytrade.backtest.backtrader_adapter import NS_PER_SEC
from daytrade.feed.simulated import SimulatedFeed
from daytrade.types import MarketTick, OrderBookLevel


def _tick(ts_ns, price, qty=1.0):
    return MarketTick(ts_ns=ts_ns, symbol="X",
                      bids=(OrderBookLevel(price - 0.5, 10),),
                      asks=(OrderBookLevel(price + 0.5, 10),),
                      last_price=price, last_qty=qty)


def test_ohlcv_buckets_and_aggregates():
    # 1초 버킷: [0..0.9s) 한 바, [1..1.9s) 한 바.
    s = NS_PER_SEC
    ticks = [
        _tick(0, 100.0, 1), _tick(s // 2, 102.0, 2), _tick(s - 1, 101.0, 1),  # bar 0
        _tick(s, 103.0, 1), _tick(s + s // 2, 99.0, 4),                       # bar 1
    ]
    bars = ticks_to_ohlcv(ticks, bar_sec=1.0)
    assert len(bars) == 2
    b0 = bars[0]
    assert isinstance(b0, Bar)
    assert b0.open == 100.0 and b0.close == 101.0
    assert b0.high == 102.0 and b0.low == 100.0
    assert b0.volume == 4.0 and b0.trades == 3
    b1 = bars[1]
    assert b1.open == 103.0 and b1.low == 99.0 and b1.close == 99.0
    assert b1.volume == 5.0


def test_ohlcv_uses_mid_when_no_last_price():
    t = MarketTick(ts_ns=0, symbol="X", bids=(OrderBookLevel(99.0, 1),),
                   asks=(OrderBookLevel(101.0, 1),), last_price=0.0, last_qty=0.0)
    bars = ticks_to_ohlcv([t], bar_sec=1.0)
    assert len(bars) == 1 and bars[0].close == 100.0  # mid


def test_ohlcv_empty():
    assert ticks_to_ohlcv([], bar_sec=1.0) == []


def test_ohlcv_monotonic_buckets():
    ticks = list(SimulatedFeed(symbol="X", n_ticks=300, seed=3).ticks())
    bars = ticks_to_ohlcv(ticks, bar_sec=0.001)
    assert bars  # 합성 틱 간격에 따라 다수 바
    ts = [b.ts_ns for b in bars]
    assert ts == sorted(ts)
    assert all(b.high >= b.low for b in bars)
    assert all(b.high >= b.open and b.high >= b.close for b in bars)
    assert all(b.low <= b.open and b.low <= b.close for b in bars)


@pytest.mark.skipif(not has_backtrader(), reason="backtrader/pandas 미설치")
def test_backtrader_run_smoke():
    import backtrader as bt

    class _Buy(bt.Strategy):
        def next(self):
            if not self.position:
                self.buy(size=1)

    from daytrade.backtest import run_backtrader
    ticks = list(SimulatedFeed(symbol="X", n_ticks=300, seed=3).ticks())
    res = run_backtrader(ticks, _Buy, bar_sec=0.001, cash=10_000.0)
    assert "final_value" in res and res["start_cash"] == 10_000.0


def _has(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def test_bt_feed_raises_without_backtrader():
    if _has("backtrader"):
        pytest.skip("backtrader 설치됨 — ImportError 경로 미적용")
    from daytrade.backtest import ticks_to_backtrader_feed
    with pytest.raises(ImportError):
        ticks_to_backtrader_feed([])


def test_bars_to_dataframe_raises_without_pandas():
    if _has("pandas"):
        pytest.skip("pandas 설치됨 — ImportError 경로 미적용")
    from daytrade.backtest import bars_to_dataframe
    with pytest.raises(ImportError):
        bars_to_dataframe([])
