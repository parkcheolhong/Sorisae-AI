"""순수 numpy 로지스틱 회귀 — 의존성 없는 기본 학습 모델(항상 동작).

두 개의 독립 로지스틱 헤드(buy/sell)를 경사하강으로 학습한다. 표준화(mean/std)를
모델에 내장해 추론·ONNX export 시 원시 피처가 그대로 들어와도 동일 결과를 보장한다.

JSON 직렬화 포맷(`model.json`)은 onnxruntime 없이도 `NumpyLogRegModel` 로 즉시 추론 가능하며,
동일 파라미터로 `onnx_export.export_numpy_logreg_to_onnx` 가 ONNX(생산 아티팩트)를 생성한다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..features.engine import FEATURE_NAMES

MODEL_KIND = "numpy_logreg"
MODEL_VERSION = 1


def _sigmoid(z: "np.ndarray") -> "np.ndarray":
    # clip 으로 overflow 방지(sigmoid(±60)≈0/1 로 충분히 포화).
    z = np.clip(np.asarray(z, dtype=np.float64), -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-z))


@dataclass(slots=True)
class NumpyLogReg:
    """표준화 내장 이진 로지스틱(2-head). W:(F,2), b:(2,), mean/std:(F,)."""

    W: "np.ndarray"
    b: "np.ndarray"
    mean: "np.ndarray"
    std: "np.ndarray"
    feature_names: tuple[str, ...]
    horizon: int = 0

    @property
    def n_features(self) -> int:
        return int(self.W.shape[0])

    def standardize(self, X: "np.ndarray") -> "np.ndarray":
        return (np.asarray(X, dtype=np.float64) - self.mean) / self.std

    def predict_proba(self, X: "np.ndarray") -> "np.ndarray":
        X = np.atleast_2d(np.asarray(X, dtype=np.float64))
        logits = self.standardize(X) @ self.W + self.b
        return _sigmoid(logits)

    # ── 직렬화 ──
    def to_dict(self) -> dict:
        return {
            "kind": MODEL_KIND,
            "version": MODEL_VERSION,
            "feature_names": list(self.feature_names),
            "horizon": int(self.horizon),
            "W": self.W.tolist(),
            "b": self.b.tolist(),
            "mean": self.mean.tolist(),
            "std": self.std.tolist(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NumpyLogReg":
        return cls(
            W=np.asarray(d["W"], dtype=np.float64),
            b=np.asarray(d["b"], dtype=np.float64),
            mean=np.asarray(d["mean"], dtype=np.float64),
            std=np.asarray(d["std"], dtype=np.float64),
            feature_names=tuple(d.get("feature_names", FEATURE_NAMES)),
            horizon=int(d.get("horizon", 0)),
        )

    def save_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> "NumpyLogReg":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))  # NOSONAR


def _logloss(y: "np.ndarray", p: "np.ndarray") -> float:
    eps = 1e-7
    p = np.clip(p, eps, 1.0 - eps)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def train_logreg(
    X: "np.ndarray",
    y_buy: "np.ndarray",
    y_sell: "np.ndarray",
    *,
    feature_names: tuple[str, ...] = FEATURE_NAMES,
    horizon: int = 0,
    epochs: int = 300,
    lr: float = 0.1,
    l2: float = 1e-4,
    val_frac: float = 0.2,
    seed: int = 42,
) -> tuple[NumpyLogReg, dict]:
    """2-head 로지스틱 학습. (model, metrics) 반환.

    표준화 통계는 **train 구간에서만** 추정(누수 방지)하여 모델에 내장한다.
    """
    from .dataset import train_val_split

    X = np.atleast_2d(np.asarray(X, dtype=np.float64))
    Y = np.stack([np.asarray(y_buy, dtype=np.float64), np.asarray(y_sell, dtype=np.float64)], axis=1)
    n, f = X.shape
    if n == 0:
        raise ValueError("empty dataset")

    tr, va = train_val_split(n, val_frac)
    Xtr, Ytr = X[tr], Y[tr]

    mean = Xtr.mean(axis=0)
    std = Xtr.std(axis=0)
    std = np.where(std < 1e-8, 1.0, std)  # 상수 피처 보호

    Xtr_n = (Xtr - mean) / std
    rng = np.random.default_rng(seed)
    W = rng.normal(0.0, 0.01, size=(f, 2))
    b = np.zeros(2)

    m = Xtr_n.shape[0]
    for _ in range(epochs):
        p = _sigmoid(Xtr_n @ W + b)
        grad = p - Ytr  # (m,2)
        gW = Xtr_n.T @ grad / m + l2 * W
        gb = grad.mean(axis=0)
        W -= lr * gW
        b -= lr * gb

    model = NumpyLogReg(W=W, b=b, mean=mean, std=std, feature_names=tuple(feature_names), horizon=horizon)

    def _head_metrics(idx: "np.ndarray") -> dict:
        if len(idx) == 0:
            return {"n": 0}
        proba = model.predict_proba(X[idx])
        out = {"n": int(len(idx))}
        for k, name in enumerate(("buy", "sell")):
            yk = Y[idx, k]
            pk = proba[:, k]
            acc = float(np.mean((pk >= 0.5).astype(np.float64) == yk))
            out[name] = {"acc": acc, "logloss": _logloss(yk, pk), "pos_rate": float(yk.mean())}
        return out

    metrics = {
        "train": _head_metrics(tr),
        "val": _head_metrics(va),
        "epochs": epochs,
        "lr": lr,
        "l2": l2,
        "n_features": f,
        "horizon": horizon,
    }
    return model, metrics
