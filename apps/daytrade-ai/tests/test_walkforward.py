import numpy as np

from daytrade.config import RiskConfig, SignalConfig, TradingConfig, TradingMode
from daytrade.feed.memory import ListFeed
from daytrade.feed.simulated import SimulatedFeed
from daytrade.features.engine import FEATURE_NAMES
from daytrade.training.dataset import DatasetBundle, build_dataset
from daytrade.training.walkforward import (
    WFSplit,
    walk_forward_backtest,
    walk_forward_splits,
    walk_forward_validate,
)


# ── splitter ──

def test_rolling_splits_are_chronological_and_nonoverlapping():
    splits = walk_forward_splits(1000, n_splits=4, scheme="rolling", purge=0)
    assert len(splits) == 4
    for sp in splits:
        assert sp.train_idx[-1] < sp.test_idx[0]  # train precedes test
    # 인접 폴드의 test 는 겹치지 않음
    for a, b in zip(splits, splits[1:]):
        assert a.test_idx[-1] < b.test_idx[0]


def test_anchored_train_grows_from_zero():
    splits = walk_forward_splits(1000, n_splits=4, scheme="anchored")
    for sp in splits:
        assert sp.train_idx[0] == 0
    assert len(splits[1].train_idx) > len(splits[0].train_idx)


def test_purge_creates_gap_between_train_and_test():
    purge = 10
    splits = walk_forward_splits(1000, n_splits=3, scheme="rolling", purge=purge)
    for sp in splits:
        gap = sp.test_idx[0] - sp.train_idx[-1] - 1
        assert gap >= purge


def test_explicit_sizes():
    splits = walk_forward_splits(500, train_size=100, test_size=50, n_splits=0)
    assert all(len(sp.test_idx) == 50 for sp in splits)
    assert all(len(sp.train_idx) == 100 for sp in splits[1:])


def test_tiny_n_returns_empty():
    assert walk_forward_splits(1) == []


# ── classification validate ──

def _separable_bundle(n=3000, horizon=10, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, len(FEATURE_NAMES)))
    yb = (X[:, 0] > 0.2).astype(np.float32)
    ys = (X[:, 3] < -0.2).astype(np.float32)
    return DatasetBundle(X=X, y_buy=yb, y_sell=ys, feature_names=FEATURE_NAMES, horizon=horizon)


def test_validate_reports_oos_metrics_and_gap():
    bundle = _separable_bundle()
    report = walk_forward_validate(bundle, n_splits=4, epochs=200)
    assert report.summary["n_folds"] == 4
    # 분리 가능한 신호 → OOS 정확도 높고 과최적화 갭 작음
    assert report.summary["mean_oos_acc_buy"] > 0.85
    assert abs(report.summary["mean_overfit_gap"]) < 0.1
    for f in report.folds:
        assert "oos_acc_buy" in f and "overfit_gap" in f
        # 불균형 노출용 지표가 함께 보고돼야 한다.
        assert "oos_bal_acc_buy" in f and "oos_pos_rate_buy" in f


def test_balanced_acc_exposes_imbalance():
    from daytrade.training.walkforward import _balanced_acc

    # 95% 음성 라벨을 전부 0 으로 예측 → 정확도 0.95 지만 balanced_acc 는 0.5(음성만 맞춤).
    y = np.array([0.0] * 95 + [1.0] * 5)
    pred_all_zero = np.zeros_like(y)
    assert _balanced_acc(y, pred_all_zero) == 0.5
    # 완벽 예측 → 1.0
    assert _balanced_acc(y, y.copy()) == 1.0


# ── backtest walk-forward ──

def _config():
    return TradingConfig(
        mode=TradingMode.BACKTEST,
        symbols=("T",),
        signal=SignalConfig(use_ai=True, ai_buy_threshold=0.55, ai_sell_threshold=0.55),
        risk=RiskConfig(max_latency_ms=float("inf")),
        seed=7,
    )


def test_backtest_walkforward_produces_oos_folds():
    ticks = list(SimulatedFeed(symbol="T", n_ticks=6000, seed=11, event_prob=0.05).ticks())
    report = walk_forward_backtest(ticks, _config(), horizon=20, n_splits=4, epochs=120)
    assert report.summary["n_folds"] == 4
    assert "mean_oos_return_pct" in report.summary
    assert "mean_oos_sharpe" in report.summary
    assert "positive_fold_ratio" in report.summary
    for f in report.folds:
        assert f["n_train"] > 0 and f["n_test"] > 0
        assert "oos_return_pct" in f and "oos_sharpe" in f


def test_backtest_walkforward_is_deterministic():
    ticks = list(SimulatedFeed(symbol="T", n_ticks=4000, seed=5, event_prob=0.05).ticks())
    r1 = walk_forward_backtest(ticks, _config(), horizon=15, n_splits=3, epochs=80)
    r2 = walk_forward_backtest(ticks, _config(), horizon=15, n_splits=3, epochs=80)
    assert r1.folds == r2.folds
