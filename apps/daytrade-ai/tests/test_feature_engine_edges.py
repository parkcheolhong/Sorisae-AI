"""(마) FeatureEngine 경계 동작 잠금 — C++ 코어(M3)가 미러해야 할 폴백 규약을 항상 검증.

골든 패리티 테스트(test_cpp_golden.py)는 C++ 빌드 시에만 실행되지만, 본 테스트는 **레퍼런스(Python)
의 경계 동작**(빈/단측 호가창·0/음수 볼륨·첫 틱)을 항상 고정해, C++ 측이 맞춰야 할 사양을 회귀로 보호한다.
"""
from __future__ import annotations

from daytrade.detection.engine import DetectionEngine
from daytrade.config import SignalConfig
from daytrade.features.engine import FeatureEngine
from daytrade.types import MarketTick, OrderBookLevel


def _lv(p, q):
    return OrderBookLevel(p, q)


def test_empty_book_fallbacks():
    fe = FeatureEngine(depth=10)
    fv = fe.update(MarketTick(ts_ns=1, symbol="E", bids=(), asks=(), last_price=100.0, last_qty=0.0))
    assert fv.obi == 0.0           # 양측 합 0
    assert fv.spread == 0.0        # 호가 없음 → 0 폴백
    assert fv.mid_price == 100.0   # mid 없음 → last_price 폴백
    assert fv.volume_spike == 1.0  # 첫 틱 → 1.0
    assert fv.vwap == 100.0        # vol=0 → price 폴백
    assert fv.obi_norm == 0.0      # 표본<2 → 0
    assert fv.micro_momentum == 0.0


def test_one_sided_book_obi():
    fe = FeatureEngine(depth=10)
    fv = fe.update(MarketTick(ts_ns=1, symbol="E", bids=(_lv(99.9, 5.0),), asks=(),
                              last_price=100.0, last_qty=2.0))
    assert fv.obi == 5.0           # bid만 존재 → +5
    assert fv.spread == 0.0        # 단측 → spread 폴백 0
    assert fv.mid_price == 100.0


def test_zero_and_negative_volume_spike():
    fe = FeatureEngine(depth=10)
    fe.update(MarketTick(ts_ns=1, symbol="E", bids=(_lv(99.9, 1.0),), asks=(_lv(100.1, 1.0),),
                         last_price=100.0, last_qty=0.0))
    # 직전 볼륨 0(<=0) → 다음 틱도 1.0 폴백.
    fv2 = fe.update(MarketTick(ts_ns=2, symbol="E", bids=(_lv(99.9, 1.0),), asks=(_lv(100.1, 1.0),),
                               last_price=100.0, last_qty=5.0))
    assert fv2.volume_spike == 1.0
    # 음수 볼륨은 vwap 누적에서 max(vol,0) 으로 0 처리(가격 폴백 경로 안전).
    fv3 = fe.update(MarketTick(ts_ns=3, symbol="E", bids=(_lv(99.9, 1.0),), asks=(_lv(100.1, 1.0),),
                               last_price=101.0, last_qty=-2.0))
    assert fv3.vwap > 0.0


def test_detection_flat_on_empty_book():
    fe = FeatureEngine(depth=10)
    det = DetectionEngine(SignalConfig(obi_threshold=1.0, volume_spike_ratio=1.1))
    fv = fe.update(MarketTick(ts_ns=1, symbol="E", bids=(), asks=(), last_price=100.0, last_qty=0.0))
    sig = det.evaluate(fv)
    assert sig.side.value == "flat" and sig.confidence == 0.0
