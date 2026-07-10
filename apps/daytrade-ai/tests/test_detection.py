from daytrade.config import SignalConfig
from daytrade.detection.engine import DetectionEngine
from daytrade.features.engine import FeatureVector
from daytrade.types import SignalSide


def fv(obi, obi_norm, vol_spike, momentum):
    return FeatureVector(
        ts_ns=1, symbol="T", obi=obi, obi_norm=obi_norm, volume_spike=vol_spike,
        micro_momentum=momentum, vwap=100.0, vwap_delta=0.0, spread=0.02, mid_price=100.0,
    )


def test_buy_signal_when_all_conditions_met():
    eng = DetectionEngine(SignalConfig(obi_threshold=1e6, volume_spike_ratio=2.0))
    sig = eng.evaluate(fv(obi=2e6, obi_norm=3.0, vol_spike=3.0, momentum=0.5))
    assert sig.side == SignalSide.BUY
    assert sig.confidence > 0


def test_sell_signal_when_all_conditions_met():
    eng = DetectionEngine(SignalConfig(obi_threshold=1e6, volume_spike_ratio=2.0))
    sig = eng.evaluate(fv(obi=-2e6, obi_norm=-3.0, vol_spike=3.0, momentum=-0.5))
    assert sig.side == SignalSide.SELL


def test_flat_when_volume_not_spiking():
    eng = DetectionEngine(SignalConfig(obi_threshold=1e6, volume_spike_ratio=2.0))
    sig = eng.evaluate(fv(obi=2e6, obi_norm=3.0, vol_spike=1.1, momentum=0.5))
    assert sig.side == SignalSide.FLAT


def test_flat_when_momentum_opposes():
    eng = DetectionEngine(SignalConfig(obi_threshold=1e6, volume_spike_ratio=2.0))
    sig = eng.evaluate(fv(obi=2e6, obi_norm=3.0, vol_spike=3.0, momentum=-0.5))
    assert sig.side == SignalSide.FLAT


def test_confidence_in_unit_range():
    eng = DetectionEngine(SignalConfig(obi_threshold=1e6, volume_spike_ratio=2.0))
    sig = eng.evaluate(fv(obi=9e9, obi_norm=50.0, vol_spike=99.0, momentum=5.0))
    assert 0.0 <= sig.confidence <= 1.0
