import numpy as np

from daytrade.config import SignalConfig, TradingConfig, TradingMode
from daytrade.features.engine import FEATURE_NAMES, FeatureVector
from daytrade.feed.simulated import SimulatedFeed
from daytrade.inference.model import HeuristicModel, NumpyLogRegModel, load_model
from daytrade.pipeline import TradingPipeline
from daytrade.training.logreg import train_logreg


def _train_json(tmp_path, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(1500, len(FEATURE_NAMES)))
    yb = (X[:, 0] > 0.0).astype(np.float32)
    ys = (X[:, 3] < 0.0).astype(np.float32)
    model, _ = train_logreg(X, yb, ys, epochs=100, horizon=20)
    path = tmp_path / "model.json"
    model.save_json(path)
    return path, model


def test_numpy_model_matches_trainer(tmp_path):
    path, trainer_model = _train_json(tmp_path)
    rt = NumpyLogRegModel(str(path))
    fv = FeatureVector(ts_ns=1, symbol="T", obi=1.0, obi_norm=0.5, volume_spike=2.0,
                       micro_momentum=0.01, vwap=100.0, vwap_delta=0.1, spread=0.02, mid_price=100.0)
    pb, ps = rt.predict(fv)
    ref = trainer_model.predict_proba([fv.as_array()])[0]
    assert abs(pb - ref[0]) < 1e-9 and abs(ps - ref[1]) < 1e-9


def test_load_model_dispatch_json(tmp_path):
    path, _ = _train_json(tmp_path)
    assert isinstance(load_model(str(path)), NumpyLogRegModel)


def test_load_model_bad_path_falls_back_to_heuristic():
    assert isinstance(load_model("does_not_exist.onnx"), HeuristicModel)


def test_feature_order_mismatch_raises(tmp_path):
    import json

    path, _ = _train_json(tmp_path)
    d = json.loads(path.read_text(encoding="utf-8"))
    d["feature_names"] = list(reversed(d["feature_names"]))
    path.write_text(json.dumps(d), encoding="utf-8")
    try:
        NumpyLogRegModel(str(path))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_pipeline_runs_with_numpy_model(tmp_path):
    path, _ = _train_json(tmp_path)
    cfg = TradingConfig(
        mode=TradingMode.BACKTEST,
        symbols=("T",),
        signal=SignalConfig(use_ai=True, ai_buy_threshold=0.5, ai_sell_threshold=0.5),
        seed=3,
    )
    pipe = TradingPipeline(cfg, model=NumpyLogRegModel(str(path)))
    res = pipe.run(SimulatedFeed(symbol="T", n_ticks=600, seed=3), max_ticks=600)
    assert res.metrics.ticks == 600
