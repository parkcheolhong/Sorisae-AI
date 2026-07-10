"""M6-A — /metrics HTTP 노출 서버 + 인프로세스 트레이싱(파이프라인 span) 테스트."""
from __future__ import annotations

import urllib.error
import urllib.request

from daytrade.config import SignalConfig, TradingConfig
from daytrade.feed.simulated import SimulatedFeed
from daytrade.monitoring import (
    LiveMetrics,
    MetricsRegistry,
    MetricsServer,
    Tracer,
)
from daytrade.monitoring.metrics import MetricsCollector
from daytrade.pipeline import TradingPipeline


# ---------------- HTTP /metrics 서버 ----------------

def _get(url: str) -> tuple[int, str]:
    with urllib.request.urlopen(url, timeout=3) as r:  # noqa: S310 (로컬 테스트)
        return r.status, r.read().decode("utf-8")


def test_metrics_server_serves_render():
    reg = MetricsRegistry()
    reg.gauge("daytrade_equity", "eq")
    reg.set("daytrade_equity", 1_000_000.0, {"symbol": "AAPL"})
    with MetricsServer(lambda: reg, port=0) as srv:
        status, body = _get(srv.url)
        assert status == 200
        assert 'daytrade_equity{symbol="AAPL"} 1000000' in body
        hstatus, hbody = _get(f"http://127.0.0.1:{srv.port}/healthz")
        assert hstatus == 200 and hbody == "ok"


def test_metrics_server_readyz_provider():
    state = {"ready": True}
    reg = MetricsRegistry()
    reg.gauge("x", "x")
    with MetricsServer(lambda: reg, port=0, ready_provider=lambda: state["ready"]) as srv:
        s1, b1 = _get(f"http://127.0.0.1:{srv.port}/readyz")
        assert s1 == 200 and b1 == "ready"
        state["ready"] = False
        try:
            _get(f"http://127.0.0.1:{srv.port}/readyz")
            assert False, "503 이어야 함"
        except urllib.error.HTTPError as e:
            assert e.code == 503


def test_metrics_server_reflects_live_updates():
    live = LiveMetrics(symbol="AAPL", mode="paper")
    with MetricsServer(lambda: live.registry, port=0) as srv:
        mc = MetricsCollector(start_equity=1_000_000.0)
        mc.record_fill(0.0)
        mc.record_tick(0.2, 1_000_500.0)
        live.update(mc, 1_000_500.0)
        _, body = _get(srv.url)
        assert 'daytrade_fills_total{mode="paper",symbol="AAPL"} 1' in body
        assert 'daytrade_equity{mode="paper",symbol="AAPL"} 1000500' in body


# ---------------- 인프로세스 트레이싱 ----------------

def test_tracer_records_nested_spans():
    tr = Tracer(sample_rate=1)
    tr.new_trace()
    with tr.span("outer"):
        with tr.span("inner"):
            pass
    names = {s.name for s in tr.spans}
    assert names == {"outer", "inner"}
    inner = next(s for s in tr.spans if s.name == "inner")
    outer = next(s for s in tr.spans if s.name == "outer")
    assert inner.parent_id == outer.span_id  # 부모-자식 관계
    assert inner.trace_id == outer.trace_id


def test_tracer_sampling_skips_traces():
    tr = Tracer(sample_rate=3)
    for _ in range(6):  # 트레이스 3,6 만 샘플
        tr.new_trace()
        with tr.span("s"):
            pass
    assert len(tr.spans) == 2


def test_pipeline_tracing_stage_summary():
    cfg = TradingConfig(symbols=("AAPL",), signal=SignalConfig(use_ai=True, ai_buy_threshold=0.0, ai_sell_threshold=0.0))
    tr = Tracer(sample_rate=1)
    pipe = TradingPipeline(cfg, tracer=tr)
    pipe.run(SimulatedFeed(symbol="AAPL", n_ticks=300, seed=1), max_ticks=300)
    summary = tr.stage_summary()
    assert "features" in summary and "detection" in summary and "inference" in summary
    assert summary["features"]["count"] == 300
    jaeger = tr.export_jaeger()
    assert jaeger and "operationName" in jaeger[0] and "duration" in jaeger[0]


def test_pipeline_noop_tracer_default_no_spans():
    cfg = TradingConfig(symbols=("AAPL",), signal=SignalConfig(use_ai=False))
    pipe = TradingPipeline(cfg)  # 기본 NoopTracer
    pipe.run(SimulatedFeed(symbol="AAPL", n_ticks=50, seed=1), max_ticks=50)
    assert pipe.tracer.spans == []
