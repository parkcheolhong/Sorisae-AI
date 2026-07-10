from daytrade.features.engine import FeatureVector
from daytrade.inference.model import HeuristicModel, load_model


def fv(obi_norm, momentum, vol_spike=1.0):
    return FeatureVector(
        ts_ns=1, symbol="T", obi=0.0, obi_norm=obi_norm, volume_spike=vol_spike,
        micro_momentum=momentum, vwap=100.0, vwap_delta=0.0, spread=0.02, mid_price=100.0,
    )


def test_heuristic_probs_in_range():
    m = HeuristicModel()
    pb, ps = m.predict(fv(2.0, 0.5))
    assert 0.0 <= pb <= 1.0
    assert 0.0 <= ps <= 1.0


def test_bullish_features_favor_buy():
    m = HeuristicModel()
    pb, ps = m.predict(fv(3.0, 0.8, vol_spike=3.0))
    assert pb > ps


def test_bearish_features_favor_sell():
    m = HeuristicModel()
    pb, ps = m.predict(fv(-3.0, -0.8, vol_spike=3.0))
    assert ps > pb


def test_load_model_falls_back_to_heuristic_without_onnx():
    # 존재하지 않는 경로 → onnxruntime 미설치/로드 실패 → HeuristicModel 폴백
    m = load_model("/nonexistent/model.onnx")
    assert isinstance(m, HeuristicModel)


def test_load_model_default_is_heuristic():
    assert isinstance(load_model(None), HeuristicModel)
