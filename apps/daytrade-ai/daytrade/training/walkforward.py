"""워크포워드 검증 — 과최적화 방지를 위한 시간순 out-of-sample 평가(설계서 §2/§7).

두 가지 산출물:
  1) `walk_forward_validate`  — 폴드별 모델 재학습 후 **분류 OOS 지표**(acc/logloss)와
     과최적화 갭(train_acc − oos_acc)을 집계. 일반화 성능을 직접 측정.
  2) `walk_forward_backtest`  — 폴드별로 train 구간에서 학습한 모델로 **test 구간 틱을
     실제 파이프라인 백테스트**(OOS P&L/Sharpe/MDD)하고 집계. 설계서의 "walk-forward Sharpe".

look-ahead/누수 차단:
  - 분할은 항상 시간순(train 이 test 보다 앞).
  - 라벨이 미래 horizon 을 보므로 train/test 경계에서 `purge=horizon` 만큼 train 끝을 잘라낸다(embargo).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..config import TradingConfig
from ..feed.memory import ListFeed
from ..inference.model import NumpyLogRegModel
from ..types import MarketTick
from .dataset import DatasetBundle, build_feature_matrix
from .labeling import make_labels
from .logreg import train_logreg


@dataclass(frozen=True, slots=True)
class WFSplit:
    fold: int
    train_idx: "np.ndarray"
    test_idx: "np.ndarray"


def walk_forward_splits(
    n: int,
    *,
    n_splits: int = 5,
    scheme: str = "rolling",
    train_size: int | None = None,
    test_size: int | None = None,
    purge: int = 0,
) -> list[WFSplit]:
    """시간순 워크포워드 분할.

    Args:
        n: 표본 수.
        n_splits: 최대 폴드 수(크기 미지정 시 이 값으로 test_size 자동 산정).
        scheme: "rolling"(슬라이딩, 고정 train 윈도) | "anchored"(확장, train=처음~경계).
        train_size/test_size: 명시 시 그 크기 사용(rolling 의 step=test_size).
        purge: train/test 경계에서 train 끝을 잘라낼 샘플 수(라벨 horizon 누수 방지).
    """
    if n <= 1:
        return []
    if scheme not in ("rolling", "anchored"):
        raise ValueError("scheme must be 'rolling' or 'anchored'")
    if test_size is None:
        test_size = max(1, n // (max(n_splits, 1) + 1))
    if train_size is None:
        train_size = test_size

    splits: list[WFSplit] = []
    start_test = train_size
    fold = 0
    while start_test + test_size <= n:
        if n_splits and fold >= n_splits:
            break
        test_idx = np.arange(start_test, start_test + test_size)
        tr_start = 0 if scheme == "anchored" else max(0, start_test - train_size)
        tr_end = max(tr_start, start_test - purge)
        train_idx = np.arange(tr_start, tr_end)
        if len(train_idx) > 0 and len(test_idx) > 0:
            splits.append(WFSplit(fold=fold, train_idx=train_idx, test_idx=test_idx))
            fold += 1
        start_test += test_size
    return splits


# ── 1) 분류 워크포워드 ──

@dataclass(slots=True)
class WalkForwardReport:
    folds: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def summary_lines(self) -> list[str]:
        s = self.summary
        lines = [f"folds              : {s.get('n_folds', 0)} ({s.get('scheme', '?')})"]
        for f in self.folds:
            lines.append(
                f"  fold {f['fold']:>2}  train={f.get('n_train', 0):>6} test={f.get('n_test', 0):>6}  "
                + _fold_line(f)
            )
        for k, v in s.items():
            if k in ("n_folds", "scheme"):
                continue
            lines.append(f"{k:<19}: {v}")
        return lines


def _fold_line(f: dict) -> str:
    if "oos_return_pct" in f:
        return (
            f"ret={f['oos_return_pct']:+.3f}% sharpe={f['oos_sharpe']:.2f} "
            f"mdd={f['oos_mdd_pct']:.2f}% sig={f.get('signals', 0)}"
        )
    return (
        f"oos_acc={f.get('oos_acc_buy', 0):.3f}/{f.get('oos_acc_sell', 0):.3f} "
        f"bal_acc={f.get('oos_bal_acc_buy', 0):.3f}/{f.get('oos_bal_acc_sell', 0):.3f} "
        f"pos_rate={f.get('oos_pos_rate_buy', 0):.3f}/{f.get('oos_pos_rate_sell', 0):.3f} "
        f"gap={f.get('overfit_gap', 0):+.3f}"
    )


def walk_forward_validate(
    bundle: DatasetBundle,
    *,
    n_splits: int = 5,
    scheme: str = "rolling",
    epochs: int = 200,
    lr: float = 0.1,
    seed: int = 42,
) -> WalkForwardReport:
    """폴드별 로지스틱 재학습 → 분류 OOS 지표 + 과최적화 갭 집계."""
    X, yb, ys = bundle.X, bundle.y_buy, bundle.y_sell
    n = len(bundle)
    splits = walk_forward_splits(
        n, n_splits=n_splits, scheme=scheme, purge=bundle.horizon
    )
    folds: list[dict] = []
    for sp in splits:
        model, _ = train_logreg(
            X[sp.train_idx], yb[sp.train_idx], ys[sp.train_idx],
            feature_names=bundle.feature_names, horizon=bundle.horizon,
            epochs=epochs, lr=lr, seed=seed, val_frac=0.0,
        )
        tr_acc = _acc2(model, X[sp.train_idx], yb[sp.train_idx], ys[sp.train_idx])
        oos_acc = _acc2(model, X[sp.test_idx], yb[sp.test_idx], ys[sp.test_idx])
        # balanced accuracy(=recall 평균)와 pos_rate 를 함께 산출 → 클래스 불균형 노출.
        oos_bal = _balanced_acc2(model, X[sp.test_idx], yb[sp.test_idx], ys[sp.test_idx])
        folds.append({
            "fold": sp.fold,
            "n_train": int(len(sp.train_idx)),
            "n_test": int(len(sp.test_idx)),
            "train_acc_buy": tr_acc[0], "train_acc_sell": tr_acc[1],
            "oos_acc_buy": oos_acc[0], "oos_acc_sell": oos_acc[1],
            "oos_bal_acc_buy": oos_bal[0], "oos_bal_acc_sell": oos_bal[1],
            "oos_pos_rate_buy": round(float(np.mean(yb[sp.test_idx])) if len(sp.test_idx) else 0.0, 4),
            "oos_pos_rate_sell": round(float(np.mean(ys[sp.test_idx])) if len(sp.test_idx) else 0.0, 4),
            "overfit_gap": round(((tr_acc[0] + tr_acc[1]) - (oos_acc[0] + oos_acc[1])) / 2.0, 4),
        })
    summary = {"n_folds": len(folds), "scheme": scheme}
    if folds:
        summary["mean_oos_acc_buy"] = round(float(np.mean([f["oos_acc_buy"] for f in folds])), 4)
        summary["mean_oos_acc_sell"] = round(float(np.mean([f["oos_acc_sell"] for f in folds])), 4)
        summary["mean_oos_bal_acc_buy"] = round(float(np.mean([f["oos_bal_acc_buy"] for f in folds])), 4)
        summary["mean_oos_bal_acc_sell"] = round(float(np.mean([f["oos_bal_acc_sell"] for f in folds])), 4)
        summary["mean_oos_pos_rate_buy"] = round(float(np.mean([f["oos_pos_rate_buy"] for f in folds])), 4)
        summary["mean_oos_pos_rate_sell"] = round(float(np.mean([f["oos_pos_rate_sell"] for f in folds])), 4)
        summary["mean_overfit_gap"] = round(float(np.mean([f["overfit_gap"] for f in folds])), 4)
    return WalkForwardReport(folds=folds, summary=summary)


def _acc2(model, X, yb, ys) -> tuple[float, float]:
    if len(X) == 0:
        return 0.0, 0.0
    p = model.predict_proba(X)
    acc_b = float(np.mean((p[:, 0] >= 0.5).astype(np.float64) == yb))
    acc_s = float(np.mean((p[:, 1] >= 0.5).astype(np.float64) == ys))
    return round(acc_b, 4), round(acc_s, 4)


def _balanced_acc(y: "np.ndarray", pred: "np.ndarray") -> float:
    """balanced accuracy = (recall_pos + recall_neg)/2. 양/음 클래스 한쪽이 없으면 존재하는 쪽만."""
    recalls = []
    for cls in (1.0, 0.0):
        mask = y == cls
        if mask.any():
            recalls.append(float(np.mean(pred[mask] == cls)))
    return round(float(np.mean(recalls)), 4) if recalls else 0.0


def _balanced_acc2(model, X, yb, ys) -> tuple[float, float]:
    if len(X) == 0:
        return 0.0, 0.0
    p = model.predict_proba(X)
    pb = (p[:, 0] >= 0.5).astype(np.float64)
    ps = (p[:, 1] >= 0.5).astype(np.float64)
    return _balanced_acc(yb, pb), _balanced_acc(ys, ps)


# ── 2) 백테스트 워크포워드 (OOS P&L) ──

def walk_forward_backtest(
    ticks: list[MarketTick],
    config: TradingConfig,
    *,
    horizon: int = 20,
    up_bps: float = 5.0,
    down_bps: float = 5.0,
    price_kind: str = "mid",
    n_splits: int = 5,
    scheme: str = "rolling",
    epochs: int = 200,
    lr: float = 0.1,
    seed: int = 42,
) -> WalkForwardReport:
    """폴드별 학습→test 틱 OOS 백테스트. config.signal.use_ai 가 켜져 있어야 모델이 작동.

    주의: 각 폴드의 OOS 파이프라인은 FeatureEngine 을 test 구간에서 새로 워밍업하므로,
    초기 일부 틱은 콜드스타트 영향이 있다(누수가 아니라 보수적 저평가 방향).
    """
    from ..pipeline import TradingPipeline  # 지연 임포트(순환 방지)

    X, prices, names = build_feature_matrix(ListFeed(ticks), config.signal, price_kind=price_kind)
    y_buy, y_sell, m = make_labels(prices, horizon, up_bps, down_bps)
    X = X[:m]
    splits = walk_forward_splits(m, n_splits=n_splits, scheme=scheme, purge=horizon)

    folds: list[dict] = []
    for sp in splits:
        model, _ = train_logreg(
            X[sp.train_idx], y_buy[sp.train_idx], y_sell[sp.train_idx],
            feature_names=names, horizon=horizon, epochs=epochs, lr=lr, seed=seed, val_frac=0.0,
        )
        rt = NumpyLogRegModel(model=model)
        test_ticks = [ticks[int(i)] for i in sp.test_idx]
        result = TradingPipeline(config, model=rt).run(ListFeed(test_ticks))
        mx = result.metrics
        folds.append({
            "fold": sp.fold,
            "n_train": int(len(sp.train_idx)),
            "n_test": int(len(sp.test_idx)),
            "oos_return_pct": round(mx.total_return_pct, 4),
            "oos_sharpe": round(mx.sharpe, 4),
            "oos_mdd_pct": round(mx.max_drawdown_pct, 4),
            "signals": mx.signals,
            "fills": mx.fills,
        })

    summary = {"n_folds": len(folds), "scheme": scheme}
    if folds:
        rets = np.array([f["oos_return_pct"] for f in folds], dtype=float)
        summary["mean_oos_return_pct"] = round(float(rets.mean()), 4)
        summary["std_oos_return_pct"] = round(float(rets.std()), 4)
        summary["mean_oos_sharpe"] = round(float(np.mean([f["oos_sharpe"] for f in folds])), 4)
        summary["worst_oos_mdd_pct"] = round(float(np.max([f["oos_mdd_pct"] for f in folds])), 4)
        summary["positive_fold_ratio"] = round(float(np.mean(rets > 0.0)), 4)
    return WalkForwardReport(folds=folds, summary=summary)
