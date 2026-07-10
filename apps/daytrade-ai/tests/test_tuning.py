import numpy as np
import pytest

from daytrade.config import RiskConfig, SignalConfig, TradingConfig, TradingMode
from daytrade.feed.simulated import SimulatedFeed
from daytrade.training.tuning import (
    ParamSpec,
    default_search_space,
    run_tuning,
)


def _base_config():
    return TradingConfig(
        mode=TradingMode.BACKTEST,
        symbols=("T",),
        signal=SignalConfig(use_ai=True),
        risk=RiskConfig(max_latency_ms=float("inf")),
        seed=7,
    )


def _ticks(n=4000, seed=11):
    return list(SimulatedFeed(symbol="T", n_ticks=n, seed=seed, event_prob=0.05).ticks())


# ── ParamSpec sampling ──

def test_paramspec_sampling_ranges():
    rng = np.random.default_rng(0)
    pi = ParamSpec("int", 5, 10)
    pf = ParamSpec("float", 0.5, 0.7)
    pl = ParamSpec("loguniform", 1e3, 1e5)
    pc = ParamSpec("categorical", choices=("a", "b", "c"))
    for _ in range(50):
        assert 5 <= pi.sample(rng) <= 10
        assert 0.5 <= pf.sample(rng) <= 0.7
        assert 1e3 <= pl.sample(rng) <= 1e5
        assert pc.sample(rng) in ("a", "b", "c")


def test_default_space_keys():
    space = default_search_space()
    for k in ("horizon", "up_bps", "down_bps", "lr", "epochs", "ai_threshold",
              "obi_threshold", "volume_spike_ratio"):
        assert k in space


# ── random backend ──

def test_random_tuning_returns_best_of_trials():
    res = run_tuning(_ticks(), _base_config(), n_trials=5, n_splits=3,
                     seed=1, backend="random")
    assert res.backend == "random"
    assert len(res.trials) == 5
    # best_value 는 모든 trial value 의 최댓값과 일치
    assert res.best_value == max(t["value"] for t in res.trials)
    # best_params 는 검색공간 키를 모두 포함
    assert set(res.best_params) == set(default_search_space())


def test_random_tuning_is_deterministic():
    r1 = run_tuning(_ticks(seed=3), _base_config(), n_trials=4, n_splits=2, seed=9, backend="random")
    r2 = run_tuning(_ticks(seed=3), _base_config(), n_trials=4, n_splits=2, seed=9, backend="random")
    assert r1.trials == r2.trials
    assert r1.best_params == r2.best_params


def test_metric_sharpe_selectable():
    res = run_tuning(_ticks(), _base_config(), n_trials=3, n_splits=2,
                     metric="mean_oos_sharpe", seed=2, backend="random")
    assert res.metric == "mean_oos_sharpe"


def test_default_metric_is_sharpe():
    res = run_tuning(_ticks(), _base_config(), n_trials=2, n_splits=2, seed=1, backend="random")
    assert res.metric == "mean_oos_sharpe"


def test_score_summary_constraints_penalize():
    from daytrade.training import RiskConstraints, score_summary

    summary = {"n_folds": 4, "mean_oos_sharpe": 1.0,
               "worst_oos_mdd_pct": 6.0, "positive_fold_ratio": 0.25}
    raw = score_summary(summary, "mean_oos_sharpe", None)
    constrained = score_summary(summary, "mean_oos_sharpe",
                                RiskConstraints(max_worst_mdd_pct=3.0, min_positive_fold_ratio=0.5,
                                                mdd_penalty=0.5, fold_penalty=3.0))
    assert raw == 1.0
    # 패널티: MDD 초과 3%p*0.5=1.5, 폴드비율 부족 0.25*3=0.75 → 1.0-2.25
    assert constrained == pytest.approx(1.0 - 1.5 - 0.75)


def test_score_summary_no_folds_is_worst():
    from daytrade.training import score_summary
    from daytrade.training.tuning import WORST

    assert score_summary({"n_folds": 0}, "mean_oos_sharpe") == WORST


# ── optuna backend (설치 시) ──

def test_optuna_backend_runs():
    pytest.importorskip("optuna")
    res = run_tuning(_ticks(), _base_config(), n_trials=5, n_splits=3,
                     seed=42, backend="optuna")
    assert res.backend == "optuna"
    assert len(res.trials) == 5
    assert res.best_value == pytest.approx(max(t["value"] for t in res.trials if t["value"] is not None))
    assert set(res.best_params) == set(default_search_space())
