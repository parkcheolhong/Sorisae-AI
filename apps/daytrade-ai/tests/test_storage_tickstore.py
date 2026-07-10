"""고속 바이너리 틱 스토어(TickStore) 테스트 — 라운드트립·범위질의·CSV 변환·용량."""
from __future__ import annotations

from daytrade.feed.recorder import write_ticks_csv
from daytrade.feed.replay import CsvReplayFeed
from daytrade.feed.simulated import SimulatedFeed
from daytrade.storage import TickStore, TickStoreFeed, csv_to_store, write_ticks_store


def _ticks(n=500, seed=7):
    return list(SimulatedFeed(symbol="BTCUSDT", n_ticks=n, seed=seed).ticks())


def test_roundtrip_preserves_ticks(tmp_path):
    ticks = _ticks()
    path = tmp_path / "btc.dts"
    n = write_ticks_store(path, ticks, depth=10)
    assert n == len(ticks)

    store = TickStore(path)
    assert len(store) == len(ticks)
    assert store.symbol == "BTCUSDT"

    out = list(store.read_all())
    assert len(out) == len(ticks)
    for a, b in zip(ticks, out):
        assert a.ts_ns == b.ts_ns
        assert abs(a.last_price - b.last_price) < 1e-9
        assert len(a.bids) == len(b.bids) and len(a.asks) == len(b.asks)
        assert abs(a.bids[0].price - b.bids[0].price) < 1e-9
        assert abs(a.asks[0].qty - b.asks[0].qty) < 1e-9


def test_time_bounds_and_random_access(tmp_path):
    ticks = _ticks()
    path = tmp_path / "btc.dts"
    write_ticks_store(path, ticks)
    store = TickStore(path)
    lo, hi = store.time_bounds()
    assert lo == ticks[0].ts_ns and hi == ticks[-1].ts_ns
    assert store.get(0).ts_ns == ticks[0].ts_ns
    assert store.get(-1).ts_ns == ticks[-1].ts_ns


def test_read_range_binary_search(tmp_path):
    ticks = _ticks(n=400)
    path = tmp_path / "btc.dts"
    write_ticks_store(path, ticks)
    store = TickStore(path)
    start = ticks[100].ts_ns
    end = ticks[200].ts_ns
    sliced = list(store.read_range(start, end))
    expected = [t for t in ticks if start <= t.ts_ns <= end]
    assert len(sliced) == len(expected)
    assert sliced[0].ts_ns == expected[0].ts_ns
    assert sliced[-1].ts_ns == expected[-1].ts_ns
    # 모든 결과가 구간 내.
    assert all(start <= t.ts_ns <= end for t in sliced)


def test_tickstore_feed_plugs_into_pipeline_shape(tmp_path):
    ticks = _ticks(n=120)
    path = tmp_path / "btc.dts"
    write_ticks_store(path, ticks)
    feed = TickStoreFeed(path)
    assert sum(1 for _ in feed.ticks()) == len(ticks)
    # 범위 피드.
    rng = TickStoreFeed(path, start_ns=ticks[10].ts_ns, end_ns=ticks[20].ts_ns)
    got = list(rng.ticks())
    assert got[0].ts_ns == ticks[10].ts_ns and got[-1].ts_ns == ticks[20].ts_ns


def test_csv_to_store_matches_csv(tmp_path):
    ticks = _ticks(n=200)
    csv_path = tmp_path / "btc.csv"
    write_ticks_csv(csv_path, ticks, depth=10)
    store_path = tmp_path / "btc.dts"
    n = csv_to_store(csv_path, store_path, depth=10)
    assert n == len(ticks)

    csv_out = list(CsvReplayFeed(csv_path).ticks())
    store_out = list(TickStore(store_path).read_all())
    assert len(csv_out) == len(store_out) == len(ticks)
    for a, b in zip(csv_out, store_out):
        assert a.ts_ns == b.ts_ns
        assert abs(a.last_price - b.last_price) < 1e-9


def test_binary_smaller_than_csv(tmp_path):
    ticks = _ticks(n=1000)
    csv_path = tmp_path / "btc.csv"
    store_path = tmp_path / "btc.dts"
    write_ticks_csv(csv_path, ticks, depth=10)
    write_ticks_store(store_path, ticks, depth=10)
    # 바이너리 고정폭이 텍스트 CSV 보다 작다(파싱도 불필요).
    assert store_path.stat().st_size < csv_path.stat().st_size


def test_empty_store(tmp_path):
    path = tmp_path / "empty.dts"
    write_ticks_store(path, [], depth=5, symbol="AAPL")
    store = TickStore(path)
    assert len(store) == 0
    assert store.time_bounds() is None
    assert list(store.read_all()) == []
