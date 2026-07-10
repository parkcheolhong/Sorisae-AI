import numpy as np

from daytrade.features.engine import FEATURE_NAMES
from daytrade.feed.simulated import SimulatedFeed
from daytrade.training.dataset import (
    build_dataset,
    build_feature_matrix,
    make_sequences,
    train_val_split,
)


def _feed(n=500):
    return SimulatedFeed(symbol="T", n_ticks=n, depth=10, seed=1)


def test_feature_matrix_shape_and_order():
    X, prices, names = build_feature_matrix(_feed(300))
    assert names == FEATURE_NAMES
    assert X.shape[1] == len(FEATURE_NAMES)
    assert X.shape[0] == len(prices) == 300


def test_build_dataset_drops_horizon_rows():
    horizon = 25
    bundle = build_dataset(_feed(400), horizon=horizon)
    assert len(bundle) == 400 - horizon
    assert bundle.X.shape[0] == len(bundle.y_buy) == len(bundle.y_sell)
    assert bundle.feature_names == FEATURE_NAMES


def test_make_sequences_windowing():
    X = np.arange(20).reshape(10, 2).astype(float)
    seqs, idx = make_sequences(X, seq_len=4)
    assert seqs.shape == (7, 4, 2)
    assert list(idx) == [3, 4, 5, 6, 7, 8, 9]
    # 첫 시퀀스는 X[0:4]
    assert np.array_equal(seqs[0], X[0:4])


def test_train_val_split_is_chronological():
    tr, va = train_val_split(100, val_frac=0.2)
    assert len(tr) == 80 and len(va) == 20
    assert tr[-1] < va[0]  # train 이 시간상 앞
