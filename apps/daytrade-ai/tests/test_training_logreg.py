import numpy as np

from daytrade.features.engine import FEATURE_NAMES
from daytrade.training.logreg import NumpyLogReg, train_logreg


def _separable(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, len(FEATURE_NAMES)))
    # 피처 0 이 매수, 피처 3 이 매도를 강하게 결정.
    y_buy = (X[:, 0] > 0.3).astype(np.float32)
    y_sell = (X[:, 3] < -0.3).astype(np.float32)
    return X, y_buy, y_sell


def test_logreg_learns_separable_signal():
    X, yb, ys = _separable()
    model, metrics = train_logreg(X, yb, ys, epochs=400, lr=0.2, seed=1)
    assert metrics["val"]["buy"]["acc"] > 0.85
    assert metrics["val"]["sell"]["acc"] > 0.85
    assert metrics["n_features"] == len(FEATURE_NAMES)


def test_standardization_stats_from_train_only():
    X, yb, ys = _separable(n=1000)
    model, _ = train_logreg(X, yb, ys, epochs=10, val_frac=0.2)
    assert model.mean.shape == (len(FEATURE_NAMES),)
    assert np.all(model.std > 0)


def test_predict_proba_in_range_and_shape():
    X, yb, ys = _separable(n=500)
    model, _ = train_logreg(X, yb, ys, epochs=50)
    p = model.predict_proba(X[:10])
    assert p.shape == (10, 2)
    assert np.all((p >= 0.0) & (p <= 1.0))


def test_json_roundtrip(tmp_path):
    X, yb, ys = _separable(n=500)
    model, _ = train_logreg(X, yb, ys, epochs=30, horizon=20)
    path = tmp_path / "model.json"
    model.save_json(path)
    loaded = NumpyLogReg.load_json(path)
    assert loaded.horizon == 20
    assert loaded.feature_names == FEATURE_NAMES
    np.testing.assert_allclose(loaded.predict_proba(X[:5]), model.predict_proba(X[:5]))
