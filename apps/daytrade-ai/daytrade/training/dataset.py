"""데이터셋 빌더 — feed → FeatureEngine → (X 피처행렬, 라벨).

런타임과 동일한 `FeatureEngine` 으로 피처를 만들어 train/serve skew 를 제거한다.
시퀀스 모델(LSTM/Transformer)용 윈도잉(`make_sequences`)과 시간순 train/val 분할을 제공한다.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import SignalConfig
from ..features.engine import FEATURE_NAMES, FeatureEngine
from ..feed.base import MarketFeed
from .labeling import make_labels


@dataclass(slots=True)
class DatasetBundle:
    """학습 입력 묶음. X 는 (N, F) 피처행렬, y_buy/y_sell 은 (N,)."""

    X: "np.ndarray"
    y_buy: "np.ndarray"
    y_sell: "np.ndarray"
    feature_names: tuple[str, ...]
    horizon: int

    def __len__(self) -> int:
        return int(self.X.shape[0])


def build_feature_matrix(
    feed: MarketFeed,
    signal: SignalConfig | None = None,
    *,
    price_kind: str = "mid",
    max_ticks: int | None = None,
) -> tuple["np.ndarray", "np.ndarray", tuple[str, ...]]:
    """feed 의 모든 틱을 FeatureEngine 으로 처리해 (X, prices, feature_names) 반환.

    price_kind: "mid"(기본, mid_price 우선) | "last"(체결가). 라벨 기준가로 사용.
    """
    signal = signal or SignalConfig()
    fe = FeatureEngine(depth=signal.depth, vwap_window=signal.vwap_window)
    feats: list[list[float]] = []
    prices: list[float] = []
    for i, tick in enumerate(feed.ticks()):
        fv = fe.update(tick)
        feats.append(fv.as_array())
        if price_kind == "last":
            px = float(tick.last_price)
        else:
            px = tick.mid_price if tick.mid_price is not None else float(tick.last_price)
        prices.append(px)
        if max_ticks is not None and (i + 1) >= max_ticks:
            break
    X = np.asarray(feats, dtype=np.float64) if feats else np.zeros((0, len(FEATURE_NAMES)))
    p = np.asarray(prices, dtype=np.float64)
    return X, p, FEATURE_NAMES


def build_dataset(
    feed: MarketFeed,
    signal: SignalConfig | None = None,
    *,
    horizon: int = 20,
    up_bps: float = 5.0,
    down_bps: float = 5.0,
    price_kind: str = "mid",
    max_ticks: int | None = None,
) -> DatasetBundle:
    """feed → 라벨링된 학습 데이터셋(look-ahead 차단 포함)."""
    X, prices, names = build_feature_matrix(
        feed, signal, price_kind=price_kind, max_ticks=max_ticks
    )
    y_buy, y_sell, n = make_labels(prices, horizon, up_bps, down_bps)
    X = X[:n]  # 미래가 있는 시점만 유지
    return DatasetBundle(X=X, y_buy=y_buy, y_sell=y_sell, feature_names=names, horizon=horizon)


def make_sequences(X: "np.ndarray", seq_len: int) -> tuple["np.ndarray", "np.ndarray"]:
    """단일 피처행렬 (N,F) → 시퀀스 텐서 (M, seq_len, F).

    각 시퀀스는 [t-seq_len+1 .. t] 의 피처 윈도(현재 t 포함). 인덱스 i 의 시퀀스는
    라벨 인덱스 (seq_len-1+i) 에 대응한다. (M, idx_offset) 를 함께 반환.
    """
    X = np.asarray(X, dtype=np.float64)
    n = X.shape[0]
    if seq_len < 1:
        raise ValueError("seq_len must be >= 1")
    m = n - seq_len + 1
    if m <= 0:
        return np.zeros((0, seq_len, X.shape[1])), np.zeros((0,), dtype=int)
    seqs = np.stack([X[i : i + seq_len] for i in range(m)], axis=0)
    label_idx = np.arange(seq_len - 1, n)
    return seqs, label_idx


def train_val_split(
    n: int, val_frac: float = 0.2
) -> tuple["np.ndarray", "np.ndarray"]:
    """시간순(누수 없는) train/val 인덱스 분할. 앞쪽 train, 뒤쪽 val."""
    val_frac = min(max(val_frac, 0.0), 0.9)
    cut = int(round(n * (1.0 - val_frac)))
    cut = max(1, min(cut, n))
    train_idx = np.arange(0, cut)
    val_idx = np.arange(cut, n)
    return train_idx, val_idx
