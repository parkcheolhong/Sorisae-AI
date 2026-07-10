"""M3 골든 동일성 테스트 — C++ 코어가 Python 레퍼런스와 수치적으로 동일한지 검증.

C++ 확장(`daytrade_cpp`)이 빌드되어 있지 않으면 자동 skip 한다(현재 개발 PC 에는
C++ 툴체인 미설치 → 실서버에서 `cpp/build.ps1`|`build.sh` 빌드 후 활성화).

검증 내용:
  1. FeatureEngine.update() 의 8개 피처(FEATURE_NAMES)가 1e-9 이내로 일치.
  2. DetectionEngine.evaluate() 의 side/confidence 가 동일.
동일 입력(시드 고정 SimulatedFeed)을 양쪽 엔진에 주입해 틱별로 비교한다.
"""
from __future__ import annotations

import pytest

cpp = pytest.importorskip(
    "daytrade_cpp",
    reason="C++ 코어 미빌드 — cpp/build.ps1|build.sh 로 빌드 후 실행(실서버).",
)

from daytrade.config import SignalConfig
from daytrade.detection.engine import DetectionEngine
from daytrade.features.engine import FEATURE_NAMES, FeatureEngine
from daytrade.feed.simulated import SimulatedFeed
from daytrade.types import MarketTick, OrderBookLevel

TOL = 1e-9


def _ticks(n: int = 1500, seed: int = 7):
    return list(SimulatedFeed(symbol="TEST", n_ticks=n, seed=seed).ticks())


def _edge_ticks() -> list[MarketTick]:
    """경계 입력(빈 호가창·단측·0/음수 볼륨) — 폴백 경로(spread=0/mid=price/vol=1)의 C++ 패리티."""
    def lv(p, q):
        return OrderBookLevel(p, q)
    return [
        MarketTick(ts_ns=1, symbol="E", bids=(), asks=(), last_price=100.0, last_qty=0.0),
        MarketTick(ts_ns=2, symbol="E", bids=(lv(99.9, 5.0),), asks=(), last_price=100.0, last_qty=3.0),
        MarketTick(ts_ns=3, symbol="E", bids=(), asks=(lv(100.1, 4.0),), last_price=100.1, last_qty=0.0),
        MarketTick(ts_ns=4, symbol="E", bids=(lv(99.8, 2.0),), asks=(lv(100.2, 2.0),),
                   last_price=100.0, last_qty=-1.0),
        MarketTick(ts_ns=5, symbol="E", bids=(lv(99.9, 8.0), lv(99.8, 4.0)),
                   asks=(lv(100.1, 1.0),), last_price=100.05, last_qty=10.0),
    ]


def _assert_feature_parity(ticks):
    py_eng = FeatureEngine(depth=10, vwap_window=50, obi_stat_window=200, momentum_window=1)
    cc_eng = cpp.FeatureEngine(10, 50, 200, 1)
    max_diff = 0.0
    for tick in ticks:
        bids = [(lvl.price, lvl.qty) for lvl in tick.bids]
        asks = [(lvl.price, lvl.qty) for lvl in tick.asks]
        pf = py_eng.update(tick)
        cf = cc_eng.update(tick.ts_ns, tick.symbol, bids, asks, tick.last_price, tick.last_qty)
        for name in FEATURE_NAMES:
            diff = abs(getattr(pf, name) - getattr(cf, name))
            max_diff = max(max_diff, diff)
            assert diff <= TOL, f"{name}: py={getattr(pf, name)} cpp={getattr(cf, name)} diff={diff}"
    return max_diff


@pytest.mark.parametrize("seed", [7, 13, 101])
def test_feature_engine_equivalence(seed):
    # 다중 시드(여러 레짐)에서 8개 피처 1e-9 일치.
    assert _assert_feature_parity(_ticks(seed=seed)) <= TOL


def test_feature_engine_equivalence_edge_cases():
    # 빈/단측 호가창·0/음수 볼륨 등 경계에서도 동일(폴백 연산순서 미러 검증).
    assert _assert_feature_parity(_edge_ticks()) <= TOL


def test_detection_engine_equivalence():
    ticks = _ticks()
    # 시그널이 실제로 점화되도록 낮은 임계값 사용(buy/sell/flat 혼합 검증).
    cfg = SignalConfig(obi_threshold=5_000.0, volume_spike_ratio=1.3)
    py_feat = FeatureEngine(depth=10)
    cc_feat = cpp.FeatureEngine(10, 50, 200, 1)
    py_det = DetectionEngine(cfg)
    cc_det = cpp.DetectionEngine(cfg.obi_threshold, cfg.volume_spike_ratio)

    sides_seen = set()
    for tick in ticks:
        bids = [(lvl.price, lvl.qty) for lvl in tick.bids]
        asks = [(lvl.price, lvl.qty) for lvl in tick.asks]
        pf = py_feat.update(tick)
        cf = cc_feat.update(tick.ts_ns, tick.symbol, bids, asks, tick.last_price, tick.last_qty)
        ps = py_det.evaluate(pf)
        cs = cc_det.evaluate(cf)
        assert ps.side.value == cs.side, f"side mismatch: py={ps.side.value} cpp={cs.side}"
        assert abs(ps.confidence - cs.confidence) <= TOL
        sides_seen.add(cs.side)

    # 임계값이 낮으므로 적어도 flat 이외의 시그널이 한 번은 나와야 의미있는 검증.
    assert sides_seen - {"flat"}, "신호가 전혀 점화되지 않음 — 임계값/데이터 점검 필요"
