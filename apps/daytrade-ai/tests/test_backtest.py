from daytrade.backtest.runner import run_backtest
from daytrade.config import SignalConfig, TradingConfig
from daytrade.feed.simulated import SimulatedFeed


def test_backtest_report_summary():
    cfg = TradingConfig.backtest(signal=SignalConfig(obi_threshold=1e5, volume_spike_ratio=1.5), seed=42)
    feed = SimulatedFeed(n_ticks=3000, seed=42, event_prob=0.05)
    report = run_backtest(cfg, feed)
    d = report.metrics.as_dict()
    assert d["ticks"] == 3000
    assert "sharpe" in d
    assert "max_drawdown_pct" in d
    lines = report.summary_lines()
    assert any("sharpe" in line for line in lines)


def test_backtest_max_ticks_limit():
    cfg = TradingConfig.backtest(seed=1)
    feed = SimulatedFeed(n_ticks=10_000, seed=1)
    report = run_backtest(cfg, feed, max_ticks=500)
    assert report.metrics.ticks == 500
