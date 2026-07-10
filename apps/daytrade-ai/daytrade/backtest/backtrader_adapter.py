"""Backtrader 연동 어댑터 — 우리 틱 데이터를 Backtrader 에서 백테스트.

의존성 없는 코어: `ticks_to_ohlcv` 가 MarketTick 스트림을 시간버킷 OHLCV 바로 집계한다.
결선부(`bars_to_dataframe`/`ticks_to_backtrader_feed`/`run_backtrader`)는 pandas·backtrader 가
설치된 경우에만 동작하며, 미설치 시 설치 안내가 담긴 ImportError 를 던진다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..types import MarketTick

NS_PER_SEC = 1_000_000_000


@dataclass(frozen=True, slots=True)
class Bar:
    """OHLCV 바 1개. `ts_ns` 는 버킷 시작 경계(나노초)."""

    ts_ns: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int


def _bar_price(tick: MarketTick) -> float | None:
    """체결가 우선, 없으면(0/None) 중간가로 폴백."""
    if tick.last_price:
        return float(tick.last_price)
    mid = tick.mid_price
    return float(mid) if mid is not None else None


def ticks_to_ohlcv(ticks: Iterable[MarketTick], *, bar_sec: float = 1.0) -> list[Bar]:
    """틱 스트림을 `bar_sec` 초 단위 OHLCV 바로 집계(의존성 없음).

    가격은 체결가(없으면 중간가), 거래량은 구간 내 `last_qty` 합. 빈 버킷은 생성하지 않는다
    (틱이 존재하는 구간만). 입력은 ts_ns 오름차순을 가정한다.
    """
    bar_ns = max(1, int(bar_sec * NS_PER_SEC))
    bars: list[Bar] = []
    cur_bucket: int | None = None
    o = h = l = c = 0.0
    vol = 0.0
    n = 0
    for tick in ticks:
        px = _bar_price(tick)
        if px is None:
            continue
        bucket = (tick.ts_ns // bar_ns) * bar_ns
        if cur_bucket is None:
            cur_bucket = bucket
            o = h = l = c = px
            vol = float(tick.last_qty)
            n = 1
        elif bucket == cur_bucket:
            h = max(h, px)
            l = min(l, px)
            c = px
            vol += float(tick.last_qty)
            n += 1
        else:
            bars.append(Bar(cur_bucket, o, h, l, c, vol, n))
            cur_bucket = bucket
            o = h = l = c = px
            vol = float(tick.last_qty)
            n = 1
    if cur_bucket is not None:
        bars.append(Bar(cur_bucket, o, h, l, c, vol, n))
    return bars


def has_backtrader() -> bool:
    try:
        import backtrader  # noqa: F401
        import pandas  # noqa: F401
    except Exception:
        return False
    return True


def _require(mod: str):
    try:
        return __import__(mod)
    except Exception as exc:  # noqa: BLE001
        raise ImportError(
            f"'{mod}' 가 필요합니다. `pip install backtrader pandas` 후 사용하세요 "
            "(틱→OHLCV 집계 `ticks_to_ohlcv` 는 의존성 없이 사용 가능)."
        ) from exc


def bars_to_dataframe(bars: list[Bar]):
    """OHLCV 바 → pandas DataFrame(DatetimeIndex). pandas 필요."""
    pd = _require("pandas")
    if not bars:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    idx = pd.to_datetime([b.ts_ns for b in bars], unit="ns")
    return pd.DataFrame(
        {"open": [b.open for b in bars], "high": [b.high for b in bars],
         "low": [b.low for b in bars], "close": [b.close for b in bars],
         "volume": [b.volume for b in bars]},
        index=idx,
    )


def ticks_to_backtrader_feed(ticks: Iterable[MarketTick], *, bar_sec: float = 1.0):
    """틱 스트림 → `bt.feeds.PandasData`. backtrader·pandas 필요."""
    bt = _require("backtrader")
    df = bars_to_dataframe(ticks_to_ohlcv(ticks, bar_sec=bar_sec))
    return bt.feeds.PandasData(dataname=df)


def run_backtrader(ticks: Iterable[MarketTick], strategy, *, bar_sec: float = 1.0,
                   cash: float = 100_000.0, commission: float = 0.0005,
                   strategy_kwargs: dict | None = None) -> dict:
    """Cerebro 로 전략을 백테스트하고 결과 요약을 반환. backtrader·pandas 필요.

    반환: {start_cash, final_value, pnl, return_pct, bars}.
    """
    bt = _require("backtrader")
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy, **(strategy_kwargs or {}))
    cerebro.adddata(ticks_to_backtrader_feed(ticks, bar_sec=bar_sec))
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)
    cerebro.run()
    final = cerebro.broker.getvalue()
    return {
        "start_cash": cash,
        "final_value": final,
        "pnl": final - cash,
        "return_pct": (final - cash) / cash * 100.0 if cash else 0.0,
    }
