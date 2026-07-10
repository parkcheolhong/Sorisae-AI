"""M7 (G) — KPI 회귀셋(튜닝 전/후 다중 레짐 비교) 테스트."""
from __future__ import annotations

from daytrade.config import SignalConfig, TradingConfig
from daytrade.feed.simulated import SimulatedFeed
from daytrade.training import (
    KpiRegressionReport,
    RegimeResult,
    compare_regime,
    compare_regimes,
)
from daytrade.training.kpi import KPI_KEYS


def _regimes(n=900):
    return {
        "calm": list(SimulatedFeed(symbol="AAPL", n_ticks=n, seed=1, volatility=0.01).ticks()),
        "volatile": list(SimulatedFeed(symbol="AAPL", n_ticks=n, seed=2, volatility=0.05).ticks()),
    }


def _base():
    return TradingConfig(symbols=("AAPL",), signal=SignalConfig(use_ai=True))


def test_compare_regime_produces_baseline_and_tuned():
    ticks = list(SimulatedFeed(symbol="AAPL", n_ticks=900, seed=3, volatility=0.04).ticks())
    res = compare_regime("vol", ticks, _base(), n_trials=4, n_splits=3,
                         backend="random", seed=7)
    assert isinstance(res, RegimeResult)
    for k in KPI_KEYS:
        assert k in res.baseline and k in res.tuned
    # tuned 가 목적 지표에서 baseline 이상이면 improved=True (탐색이 baseline 후보를 포함/지배).
    assert res.improved == (res.tuned["mean_oos_sharpe"] >= res.baseline["mean_oos_sharpe"])
    assert set(res.delta) == set(KPI_KEYS)
    assert {"horizon", "up_bps", "lr"} <= set(res.best_params)


def test_compare_regimes_report_and_verdict():
    report = compare_regimes(_regimes(), _base(), n_trials=4, n_splits=3,
                             backend="random", seed=11)
    assert isinstance(report, KpiRegressionReport)
    assert len(report.regimes) == 2
    v = report.verdict
    assert set(v) >= {"sharpe_improved", "mdd_not_worse", "passed",
                      "regimes_improved", "regimes_total"}
    assert v["regimes_total"] == 2
    # 튜닝은 워크포워드 Sharpe 를 최대화하므로 tuned 평균 Sharpe ≥ baseline (탐색이 baseline 을 지배).
    assert v["tuned_mean_sharpe"] >= v["baseline_mean_sharpe"]
    assert v["sharpe_improved"] is True
    d = report.as_dict()
    assert "regimes" in d and "verdict" in d and len(d["regimes"]) == 2


def test_kpi_verdict_to_prometheus_registry():
    from daytrade.monitoring import registry_from_kpi_verdict

    report = compare_regimes(_regimes(700), _base(), n_trials=4, n_splits=2,
                             backend="random", seed=8)
    reg = registry_from_kpi_verdict(report.verdict)
    text = reg.render()
    assert "daytrade_kpi_passed" in text
    assert "daytrade_kpi_tuned_sharpe" in text
    assert 'metric="mean_oos_sharpe"' in text
    # passed 게이지가 verdict 와 일치.
    passed_vals = list(reg._metrics["daytrade_kpi_passed"].values.values())
    assert passed_vals[0] == (1.0 if report.verdict["passed"] else 0.0)


def test_tuned_dominates_baseline_objective():
    # run_tuning 의 검색공간은 baseline 라벨/시그널 근방을 포함 → 목적 지표상 tuned ≥ baseline 보장.
    report = compare_regimes(_regimes(700), _base(), n_trials=6, n_splits=2,
                             backend="random", seed=5)
    assert report.verdict["passed"] is True
