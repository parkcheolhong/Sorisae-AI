"""M4 추론 엔진 스캐폴드 테스트 — 폴백/계측/핫스왑(GPU 없이 검증).

TensorRT/CUDA 없는 개발 PC 에서 `load_inference_model` 이 안전 폴백하고,
`LatencyHistogram`/`MeasuredModel`/`HotSwapModel` 이 올바로 동작하는지 검증한다.
"""
from __future__ import annotations

from daytrade.features.engine import FeatureEngine
from daytrade.feed.simulated import SimulatedFeed
from daytrade.inference import (
    HeuristicModel,
    HotSwapModel,
    LatencyHistogram,
    MeasuredModel,
    build_engine,
    load_inference_model,
)
from daytrade.inference.model import InferenceModel


def _feature():
    ticks = list(SimulatedFeed(symbol="AAPL", n_ticks=60, seed=0).ticks())
    eng = FeatureEngine(depth=10)
    fv = None
    for t in ticks:
        fv = eng.update(t)
    return fv


class _ConstModel(InferenceModel):
    def __init__(self, pb, ps):
        self.pb, self.ps = pb, ps
        self.warmed = False

    def warmup(self):
        self.warmed = True

    def predict(self, fv):
        return self.pb, self.ps


def test_latency_histogram_percentiles():
    h = LatencyHistogram()
    for us in range(1, 101):  # 1..100 us
        h.record_ns(us * 1_000)
    s = h.summary()
    assert s["count"] == 100
    assert s["p50_us"] <= s["p95_us"] <= s["p99_us"] <= s["max_us"]
    assert abs(s["max_us"] - 100.0) < 1e-6


def test_latency_histogram_empty():
    assert LatencyHistogram().summary()["count"] == 0


def test_measured_model_records():
    m = MeasuredModel(HeuristicModel())
    fv = _feature()
    for _ in range(5):
        pb, ps = m.predict(fv)
        assert 0.0 <= pb <= 1.0 and 0.0 <= ps <= 1.0
    assert m.histogram.summary()["count"] == 5


def test_hotswap_blue_green():
    fv = _feature()
    blue = _ConstModel(0.1, 0.2)
    green = _ConstModel(0.9, 0.0)
    hs = HotSwapModel(blue)
    assert hs.predict(fv) == (0.1, 0.2)

    # stage 는 트래픽에 영향 없음(아직 blue), activate 후 green.
    hs.stage(green)
    assert green.warmed  # stage 시 warmup 호출
    assert hs.predict(fv) == (0.1, 0.2)
    old = hs.activate()
    assert old is blue
    assert hs.predict(fv) == (0.9, 0.0)
    assert hs.generation == 1


def test_hotswap_swap_shortcut():
    fv = _feature()
    hs = HotSwapModel(_ConstModel(0.0, 0.5))
    old = hs.swap(_ConstModel(0.7, 0.0))
    assert old.predict(fv) == (0.0, 0.5)
    assert hs.predict(fv) == (0.7, 0.0)


def test_load_inference_model_fallback_heuristic():
    """모델 경로 없음 → 휴리스틱. TensorRT/엔진 없음 → 폴백 동작."""
    m = load_inference_model(None)
    assert isinstance(m, HeuristicModel)
    pb, ps = m.predict(_feature())
    assert 0.0 <= pb <= 1.0 and 0.0 <= ps <= 1.0


def test_load_inference_model_measured_and_hotswap_wrappers():
    m = load_inference_model(None, measure=True, hot_swappable=True)
    assert isinstance(m, HotSwapModel)
    assert isinstance(m.active, MeasuredModel)
    m.predict(_feature())
    assert m.active.histogram.summary()["count"] == 1


def test_load_inference_model_bad_engine_falls_back():
    """존재하지 않는 TensorRT 엔진 경로 → 예외 삼키고 휴리스틱 폴백."""
    m = load_inference_model(None, engine_path="/nonexistent/x.plan")
    assert isinstance(m, HeuristicModel)


def test_build_engine_requires_tensorrt():
    """개발 PC(tensorrt 미설치)에서는 명확한 ModuleNotFoundError."""
    import pytest

    try:
        import tensorrt  # noqa: F401  # type: ignore
        has_trt = True
    except ModuleNotFoundError:
        has_trt = False
    if has_trt:
        pytest.skip("tensorrt 설치 환경 — 폴백 분기 테스트 불가")
    with pytest.raises(ModuleNotFoundError):
        build_engine("x.onnx", "x.plan")
