"""(라) 백테스트 리포트 고도화 — equity curve 분석 + JSON/HTML export + CLI 결선."""
from __future__ import annotations

import json

from daytrade.backtest.report import (
    analyze_equity_curve,
    report_to_html,
    report_to_json,
)
from daytrade.cli import main
from daytrade.monitoring.metrics import RunMetrics


def _metrics(curve):
    return RunMetrics(
        ticks=len(curve), signals=0, orders_submitted=0, fills=0, rejects=0,
        latency_ms_p50=0.0, latency_ms_p95=0.0, latency_ms_p99=0.0, latency_ms_max=0.0,
        mean_slippage_pct=0.0, start_equity=curve[0], end_equity=curve[-1],
        total_return_pct=(curve[-1] - curve[0]) / curve[0] * 100.0, realized_pnl=curve[-1] - curve[0],
        sharpe=0.0, max_drawdown_pct=0.0, halted=False, equity_curve=list(curve))


def test_analyze_uptrend_positive_metrics():
    curve = [100.0 + i for i in range(50)]   # 단조 상승
    a = analyze_equity_curve(curve, 100.0)
    assert a.total_return_pct > 0
    assert a.positive_ratio == 1.0           # 모든 틱 수익률 > 0
    assert a.max_drawdown_pct == 0.0
    assert a.max_drawdown_duration == 0
    assert a.worst_tick_pct >= 0.0


def test_analyze_drawdown_detected():
    # 상승 후 하락 → 낙폭 + 수중 구간 길이 > 0.
    curve = [100, 110, 120, 115, 108, 105, 112]
    a = analyze_equity_curve([float(x) for x in curve], 100.0)
    assert a.max_drawdown_pct > 0
    assert a.max_drawdown_duration >= 3      # 120 이후 수중 구간
    assert a.worst_tick_pct < 0
    assert 0.0 <= a.positive_ratio <= 1.0


def test_analyze_empty_curve_safe():
    a = analyze_equity_curve([], 1000.0)
    assert a.n_points == 1 and a.total_return_pct == 0.0


def test_report_json_and_html(tmp_path):
    curve = [100.0, 101.0, 99.0, 103.0, 102.0, 105.0]
    m = _metrics(curve)
    jpath = tmp_path / "r.json"
    payload = report_to_json(m, jpath)
    assert "summary" in payload and "analytics" in payload
    on_disk = json.loads(jpath.read_text(encoding="utf-8"))
    assert on_disk["analytics"]["n_points"] == len(curve)

    hpath = tmp_path / "r.html"
    html = report_to_html(m, hpath, title="t")
    assert "<svg" in html and "equity curve" in html
    assert hpath.exists() and hpath.stat().st_size > 0


def test_cli_emits_reports(tmp_path):
    jpath = tmp_path / "cli.json"
    hpath = tmp_path / "cli.html"
    rc = main(["sim", "--symbol", "AAPL", "--ticks", "800", "--no-ai",
               "--report-json", str(jpath), "--report-html", str(hpath), "--json"])
    assert rc == 0
    assert jpath.exists() and hpath.exists()
    data = json.loads(jpath.read_text(encoding="utf-8"))
    assert "analytics" in data and data["analytics"]["n_points"] >= 1
