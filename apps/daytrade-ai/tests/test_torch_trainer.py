import numpy as np
import pytest

from daytrade.features.engine import FEATURE_NAMES, FeatureVector
from daytrade.feed.simulated import SimulatedFeed
from daytrade.training.dataset import build_dataset

torch = pytest.importorskip("torch")
ort = pytest.importorskip("onnxruntime")

from daytrade.inference.model import SequenceOnnxModel  # noqa: E402
from daytrade.training.onnx_export import export_torch_sequence_to_onnx  # noqa: E402
from daytrade.training.torch_trainer import (  # noqa: E402
    build_sequence_dataset,
    train_sequence_model,
)

SEQ_LEN = 8
F = len(FEATURE_NAMES)


def _seq_data():
    bundle = build_dataset(SimulatedFeed(symbol="T", n_ticks=600, seed=2), horizon=10)
    return build_sequence_dataset(bundle, SEQ_LEN)


@pytest.mark.parametrize("kind", ["lstm", "transformer"])
def test_train_outputs_probabilities(kind):
    seqs, Y = _seq_data()
    module, metrics = train_sequence_model(seqs, Y, kind=kind, hidden=16, epochs=3)
    assert metrics["kind"] == kind
    assert metrics["seq_len"] == SEQ_LEN
    with torch.no_grad():
        out = module(torch.as_tensor(seqs[:4])).numpy()
    assert out.shape == (4, 2)
    assert np.all((out >= 0.0) & (out <= 1.0))


def test_lstm_onnx_roundtrip_matches_torch(tmp_path):
    seqs, Y = _seq_data()
    module, _ = train_sequence_model(seqs, Y, kind="lstm", hidden=16, epochs=3)
    path = export_torch_sequence_to_onnx(module, tmp_path / "seq.onnx", seq_len=SEQ_LEN, n_features=F)

    sm = SequenceOnnxModel(path, seq_len=SEQ_LEN, n_features=F)
    # SequenceOnnxModel 에 SEQ_LEN 개의 FeatureVector 를 순서대로 주입 → 마지막 윈도가 채워짐.
    window = seqs[0]  # (SEQ_LEN, F)
    pb = ps = 0.0
    for row in window:
        fv = FeatureVector(ts_ns=1, symbol="T", **dict(zip(FEATURE_NAMES, [float(v) for v in row])))
        pb, ps = sm.predict(fv)

    with torch.no_grad():
        ref = module(torch.as_tensor(window[None, :, :].astype(np.float32))).numpy()[0]
    assert abs(pb - float(ref[0])) < 1e-3
    assert abs(ps - float(ref[1])) < 1e-3
