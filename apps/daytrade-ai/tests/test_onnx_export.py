import numpy as np
import pytest

from daytrade.features.engine import FEATURE_NAMES, FeatureVector
from daytrade.training.logreg import train_logreg

onnx = pytest.importorskip("onnx")
ort = pytest.importorskip("onnxruntime")

from daytrade.inference.model import OnnxModel  # noqa: E402
from daytrade.training.onnx_export import export_numpy_logreg_to_onnx  # noqa: E402


def _trained():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(1500, len(FEATURE_NAMES)))
    yb = (X[:, 0] > 0.0).astype(np.float32)
    ys = (X[:, 3] < 0.0).astype(np.float32)
    model, _ = train_logreg(X, yb, ys, epochs=150, horizon=20)
    return model


def test_export_and_check_model(tmp_path):
    model = _trained()
    path = export_numpy_logreg_to_onnx(model, tmp_path / "m.onnx")
    loaded = onnx.load(path)
    onnx.checker.check_model(loaded)


def test_onnx_matches_numpy(tmp_path):
    model = _trained()
    path = export_numpy_logreg_to_onnx(model, tmp_path / "m.onnx")
    om = OnnxModel(path)
    fv = FeatureVector(ts_ns=1, symbol="T", obi=0.7, obi_norm=-0.4, volume_spike=1.5,
                       micro_momentum=-0.02, vwap=100.0, vwap_delta=0.05, spread=0.03, mid_price=100.0)
    pb, ps = om.predict(fv)
    ref = model.predict_proba([fv.as_array()])[0]
    assert abs(pb - ref[0]) < 1e-4
    assert abs(ps - ref[1]) < 1e-4


def test_onnx_input_output_shapes(tmp_path):
    model = _trained()
    path = export_numpy_logreg_to_onnx(model, tmp_path / "m.onnx")
    sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name
    x = np.zeros((1, len(FEATURE_NAMES)), dtype=np.float32)
    out = sess.run(None, {name: x})[0]
    assert out.shape == (1, 2)
    assert np.all((out >= 0.0) & (out <= 1.0))
