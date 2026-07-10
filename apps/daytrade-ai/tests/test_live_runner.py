"""B — 라이브 상시운영 러너 테스트(자동재연결·heartbeat·일일리포트·정지조건).

네트워크/실시간 없이 검증하기 위해 벽시계/단조시계/sleep 을 주입하고, 유한 `ListFeed` 로 끊김/
재연결을 시뮬레이션한다.
"""
from __future__ import annotations

from datetime import datetime, timezone

from daytrade.config import SignalConfig, TradingConfig
from daytrade.feed.base import MarketFeed
from daytrade.feed.memory import ListFeed
from daytrade.monitoring import AuditLog, LiveMetrics
from daytrade.ops import LiveRunner, RunnerConfig
from daytrade.pipeline import TradingPipeline
from daytrade.types import MarketTick, OrderBookLevel


def _tick(i: int, symbol="AAPL", price=100.0):
    return MarketTick(
        ts_ns=i, symbol=symbol,
        bids=(OrderBookLevel(price - 0.01, 1000.0),),
        asks=(OrderBookLevel(price + 0.01, 1000.0),),
        last_price=price, last_qty=10.0,
    )


def _pipeline():
    cfg = TradingConfig(symbols=("AAPL",), signal=SignalConfig(use_ai=False))
    return TradingPipeline(cfg)


class _Counter:
    """호출마다 step 만큼 증가하는 단조 시계 스텁."""

    def __init__(self, start=0.0, step=1.0):
        self.t = start
        self.step = step

    def __call__(self):
        self.t += self.step
        return self.t


# ---------------- 자동 재연결 ----------------

def test_auto_reconnect_across_sessions():
    sessions = iter([ListFeed([_tick(i) for i in range(5)]) for _ in range(10)])
    sleeps: list[float] = []
    runner = LiveRunner(
        _pipeline(),
        feed_factory=lambda: next(sessions),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=12),
        sleep=sleeps.append,
        mono=lambda: 0.0,
    )
    summary = runner.run()
    assert summary["ticks"] == 12          # 5+5+2(=세 번째 세션 중 정지)
    assert summary["reconnects"] >= 2      # 최소 2회 재연결
    assert len(sleeps) >= 2                 # 세션 사이 백오프 슬립


def test_reconnect_failure_limit_stops():
    # 항상 빈 피드 → 연속 실패 → max_reconnects 초과 시 정지(무한루프 방지).
    sleeps: list[float] = []
    runner = LiveRunner(
        _pipeline(),
        feed_factory=lambda: ListFeed([]),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_reconnects=3,
                            reconnect_base_sec=1.0, reconnect_max_sec=8.0),
        sleep=sleeps.append,
        mono=lambda: 0.0,
    )
    summary = runner.run()
    assert summary["ticks"] == 0
    assert summary["reconnects"] >= 3
    # 지수 백오프 상한 적용 확인.
    assert max(sleeps) <= 8.0 and len(sleeps) >= 3


def test_feed_error_is_absorbed_as_reconnect():
    def factory():
        raise ConnectionError("ws drop")

    audit_events: list[str] = []

    class _RecAudit:
        def append(self, event, **kw):
            audit_events.append(event)

    runner = LiveRunner(
        _pipeline(),
        feed_factory=factory,
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_reconnects=2),
        audit=_RecAudit(),
        sleep=lambda s: None,
        mono=lambda: 0.0,
    )
    runner.run()
    assert "feed_error" in audit_events and "feed_disconnect" in audit_events


# ---------------- heartbeat ----------------

def test_heartbeat_fires_and_updates_live_metrics():
    beats: list[dict] = []
    live = LiveMetrics(symbol="AAPL", mode="paper")
    runner = LiveRunner(
        _pipeline(),
        feed_factory=lambda: ListFeed([_tick(i) for i in range(10)]),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=2.0, max_ticks=10),
        live=live,
        on_heartbeat=beats.append,
        mono=_Counter(step=1.0),
    )
    runner.run()
    assert len(beats) >= 3
    assert beats[-1]["ticks"] > 0
    assert 'daytrade_ticks_total{mode="paper",symbol="AAPL"}' in live.registry.render()


# ---------------- 일일 리포트 ----------------

def test_daily_report_rolls_on_utc_midnight():
    day1 = datetime(2026, 6, 24, 23, 0, tzinfo=timezone.utc).timestamp()
    day2 = datetime(2026, 6, 25, 0, 30, tzinfo=timezone.utc).timestamp()
    holder = {"wall": day1}

    class _ClockFeed(MarketFeed):
        def __init__(self, items):
            self.items = items

        def ticks(self):
            for tk, w in self.items:
                holder["wall"] = w
                yield tk

    items = [(_tick(i), day1) for i in range(3)] + [(_tick(i), day2) for i in range(3, 6)]
    reports = []
    runner = LiveRunner(
        _pipeline(),
        feed_factory=lambda: _ClockFeed(items),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=6),
        on_report=reports.append,
        wall=lambda: holder["wall"],
        mono=lambda: 0.0,
    )
    summary = runner.run()
    # day1 마감 리포트 1건 + 종료 시 day2 강제 마감 1건.
    assert len(reports) == 2
    assert reports[0].date == "2026-06-24" and reports[1].date == "2026-06-25"
    assert reports[0].ticks == 3  # 경계 틱이 다음 날로 정확히 귀속
    assert summary["days_reported"] == 2


# ---------------- 정지 조건 ----------------

def test_stop_flag_halts_run():
    flag = {"stop": False}
    n = {"count": 0}

    def factory():
        n["count"] += 1
        if n["count"] >= 2:
            flag["stop"] = True
        return ListFeed([_tick(i) for i in range(3)])

    runner = LiveRunner(
        _pipeline(),
        feed_factory=factory,
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9),
        stop_flag=lambda: flag["stop"],
        sleep=lambda s: None,
        mono=lambda: 0.0,
    )
    summary = runner.run()
    assert summary["ticks"] >= 3  # 무한 루프 없이 stop_flag 로 종료


# ---------------- 그레이스풀 종료 / 헬스 ----------------

def test_request_stop_graceful_shutdown():
    audit_events: list[str] = []

    class _RecAudit:
        def append(self, event, **kw):
            audit_events.append(event)

    runner = LiveRunner(
        _pipeline(),
        feed_factory=lambda: ListFeed([_tick(i) for i in range(1000)]),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9),
        audit=_RecAudit(),
        mono=lambda: 0.0,
    )
    # 5틱 처리 후 시그널 핸들러처럼 종료 요청.
    runner.on_tick = lambda tk: runner.request_stop() if runner._total_ticks >= 5 else None
    summary = runner.run()
    assert summary["ticks"] == 5                     # 즉시 무한루프 없이 종료
    assert audit_events[-1] == "run_end"             # 마감 감사 기록(그레이스풀)
    assert "daily_report" in audit_events             # 당일 리포트 강제 마감


def test_is_healthy_reflects_staleness_and_halt():
    holder = {"wall": 1000.0}
    runner = LiveRunner(
        _pipeline(),
        feed_factory=lambda: ListFeed([_tick(0)]),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=1),
        wall=lambda: holder["wall"],
        mono=lambda: 0.0,
    )
    runner.run()
    assert runner.is_healthy(max_staleness_sec=10.0)   # 방금 틱 → 신선
    holder["wall"] = 1100.0                              # 100초 경과 → 정체
    assert not runner.is_healthy(max_staleness_sec=10.0)
    runner.pipeline.metrics.mark_halted()                # 서킷브레이커 → 비정상
    holder["wall"] = 1000.0
    assert not runner.is_healthy(max_staleness_sec=10.0)
