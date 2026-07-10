from daytrade.features.engine import FeatureEngine, FEATURE_NAMES
from daytrade.types import MarketTick, OrderBookLevel


def make_tick(ts, price, bid_qty, ask_qty, last_qty, depth=10):
    bids = tuple(OrderBookLevel(price - 0.01 * i, bid_qty) for i in range(depth))
    asks = tuple(OrderBookLevel(price + 0.01 * (i + 1), ask_qty) for i in range(depth))
    return MarketTick(ts_ns=ts, symbol="T", bids=bids, asks=asks, last_price=price, last_qty=last_qty)


def test_feature_vector_order_matches_names():
    eng = FeatureEngine(depth=10)
    fv = eng.update(make_tick(1, 100.0, 100, 50, 10))
    assert len(fv.as_array()) == len(FEATURE_NAMES)


def test_obi_positive_when_more_bids():
    eng = FeatureEngine(depth=10)
    fv = eng.update(make_tick(1, 100.0, 200, 50, 10))
    # 10 levels * (200 - 50) = 1500
    assert fv.obi == 1500.0


def test_volume_spike_ratio():
    eng = FeatureEngine(depth=10)
    eng.update(make_tick(1, 100.0, 100, 100, 10))
    fv2 = eng.update(make_tick(2, 100.0, 100, 100, 30))
    assert fv2.volume_spike == 3.0


def test_micro_momentum_sign():
    eng = FeatureEngine(depth=10)
    eng.update(make_tick(1, 100.0, 100, 100, 10))
    fv_up = eng.update(make_tick(2, 101.0, 100, 100, 10))
    assert fv_up.micro_momentum > 0
    fv_dn = eng.update(make_tick(3, 99.0, 100, 100, 10))
    assert fv_dn.micro_momentum < 0


def test_spread_and_mid():
    eng = FeatureEngine(depth=10)
    fv = eng.update(make_tick(1, 100.0, 100, 100, 10))
    assert fv.spread > 0
    assert 99.0 < fv.mid_price < 101.0


def test_reset_clears_state():
    eng = FeatureEngine(depth=10)
    eng.update(make_tick(1, 100.0, 100, 100, 50))
    eng.reset()
    fv = eng.update(make_tick(2, 100.0, 100, 100, 99))
    # 리셋 후 첫 틱은 prev_volume 없음 → spike=1.0
    assert fv.volume_spike == 1.0
