"""M6 — 모니터링(Prometheus exporter)·감사로그(해시체인)·알림 규칙 테스트(설계서 §8/§10-5)."""
from __future__ import annotations

from daytrade.monitoring import (
    AlertEngine,
    AuditLog,
    MetricsRegistry,
    default_rules,
    registry_from_run,
)
from daytrade.monitoring.metrics import MetricsCollector


# ---------------- Prometheus exporter ----------------

def test_registry_counter_gauge_render():
    reg = MetricsRegistry()
    reg.counter("orders_total", "주문 수")
    reg.gauge("equity", "순자산")
    reg.inc("orders_total", 3, {"symbol": "AAPL"})
    reg.set("equity", 1_000_500.0, {"symbol": "AAPL"})
    text = reg.render()
    assert "# TYPE orders_total counter" in text
    assert 'orders_total{symbol="AAPL"} 3' in text
    assert 'equity{symbol="AAPL"} 1000500' in text


def test_registry_histogram_cumulative_buckets():
    reg = MetricsRegistry()
    reg.histogram("lat_ms", (0.5, 1.0, 5.0), "레이턴시")
    for v in (0.2, 0.7, 0.7, 3.0, 9.0):
        reg.observe("lat_ms", v)
    text = reg.render()
    assert "# TYPE lat_ms histogram" in text
    # 누적: le=0.5 →1, le=1.0 →3, le=5.0 →4, +Inf →5
    assert 'lat_ms_bucket{le="0.5"} 1' in text
    assert 'lat_ms_bucket{le="1"} 3' in text
    assert 'lat_ms_bucket{le="5"} 4' in text
    assert 'lat_ms_bucket{le="+Inf"} 5' in text
    assert "lat_ms_count 5" in text


def test_registry_from_run():
    mc = MetricsCollector(start_equity=1_000_000.0)
    mc.record_signal()
    mc.record_order()
    mc.record_fill(0.0002)
    mc.record_tick(0.3, 1_000_100.0)
    run = mc.finalize()
    reg = registry_from_run(run, symbol="AAPL", mode="paper")
    text = reg.render()
    assert 'daytrade_fills_total{mode="paper",symbol="AAPL"} 1' in text
    assert "daytrade_circuit_breaker_halted" in text


# ---------------- Audit log (hash chain) ----------------

def test_audit_log_append_and_verify(tmp_path):
    path = str(tmp_path / "audit.jsonl")
    log = AuditLog(path)
    log.append("order", symbol="AAPL", side="buy", qty=10)
    log.append("fill", symbol="AAPL", qty=10, price=100.01)
    log.append("reject", symbol="AAPL", reason="slippage")
    res = log.verify()
    assert res.ok and res.records == 3


def test_audit_log_resume_extends_chain(tmp_path):
    path = str(tmp_path / "audit.jsonl")
    AuditLog(path).append("order", id=1)
    log2 = AuditLog(path)  # 재개 — 이전 해시 이어받기
    log2.append("fill", id=1)
    res = log2.verify()
    assert res.ok and res.records == 2
    assert log2.read_all()[1]["seq"] == 2


def test_audit_log_detects_tampering(tmp_path):
    path = str(tmp_path / "audit.jsonl")
    log = AuditLog(path)
    log.append("order", symbol="AAPL", qty=10)
    log.append("fill", symbol="AAPL", qty=10, price=100.0)
    # 디스크의 payload 를 변조(수량 10→9999).
    data = open(path, encoding="utf-8").read().replace('"qty":10', '"qty":9999', 1)
    open(path, "w", encoding="utf-8").write(data)
    res = AuditLog(path).verify()
    assert not res.ok
    assert res.broken_seq is not None


# ---------------- Alert rules ----------------

def test_alerts_circuit_breaker_and_drawdown():
    engine = AlertEngine(default_rules(max_drawdown_pct=2.0))
    alerts = engine.evaluate({"halted": True, "max_drawdown_pct": 3.5,
                              "latency_ms_p99": 0.5, "orders_submitted": 10, "rejects": 1})
    names = {a.name for a in alerts}
    assert "CircuitBreakerHalted" in names
    assert "DrawdownExceeded" in names
    assert any(a.severity == "critical" for a in alerts)


def test_alerts_none_when_healthy():
    engine = AlertEngine(default_rules())
    alerts = engine.evaluate({"halted": False, "max_drawdown_pct": 0.1,
                              "latency_ms_p99": 0.4, "orders_submitted": 100, "rejects": 1,
                              "staleness_ms": 100.0})
    assert alerts == []


def test_alerts_reject_rate_and_staleness():
    engine = AlertEngine(default_rules(max_reject_rate=0.5, max_staleness_ms=1000.0))
    alerts = engine.evaluate({"orders_submitted": 10, "rejects": 8, "staleness_ms": 3000.0,
                              "halted": False, "max_drawdown_pct": 0.0, "latency_ms_p99": 0.1})
    names = {a.name for a in alerts}
    assert "OrderRejectRateHigh" in names and "FeedStale" in names
