import numpy as np
import pytest

from daytrade.training.labeling import make_labels


def test_forward_return_labels_basic():
    prices = np.array([100.0, 100.0, 100.0, 101.0, 99.0], dtype=float)
    # horizon=1, up/down 50bps(0.5%)
    y_buy, y_sell, n = make_labels(prices, horizon=1, up_bps=50, down_bps=50)
    assert n == 4
    # t=0:100->100 flat; t=1:100->100 flat; t=2:100->101 (+1%) buy; t=3:101->99 (-1.98%) sell
    assert list(y_buy) == [0, 0, 1, 0]
    assert list(y_sell) == [0, 0, 0, 1]


def test_no_lookahead_drops_last_horizon_rows():
    prices = np.arange(10, dtype=float) + 1.0
    _, _, n = make_labels(prices, horizon=3)
    assert n == 7  # 10 - 3


def test_horizon_too_large_returns_empty():
    prices = np.array([1.0, 2.0], dtype=float)
    y_buy, y_sell, n = make_labels(prices, horizon=5)
    assert n == 0 and len(y_buy) == 0 and len(y_sell) == 0


def test_horizon_must_be_positive():
    with pytest.raises(ValueError):
        make_labels(np.array([1.0, 2.0]), horizon=0)
