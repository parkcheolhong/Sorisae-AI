from daytrade.feed.binance import BinanceFeed
from daytrade.feed.recorder import RecordingFeed, build_header, write_ticks_csv
from daytrade.feed.replay import CsvReplayFeed
from daytrade.feed.simulated import SimulatedFeed


def _depth_messages(n):
    msgs = []
    for i in range(n):
        msgs.append({
            "stream": "btcusdt@aggTrade",
            "data": {"e": "aggTrade", "p": str(100.0 + i * 0.01), "q": "1.5"},
        })
        msgs.append({
            "stream": "btcusdt@depth10@100ms",
            "data": {
                "bids": [[str(99.9 - j * 0.1), str(5 - j)] for j in range(3)],
                "asks": [[str(100.1 + j * 0.1), str(4 + j)] for j in range(3)],
            },
        })
    return msgs


def test_header_shape():
    h = build_header(depth=2)
    assert h[:4] == ["ts_ns", "symbol", "last_price", "last_qty"]
    assert "bid_px_0" in h and "bid_qty_1" in h and "ask_px_0" in h and "ask_qty_1" in h


def test_write_ticks_csv_and_replay_roundtrip(tmp_path):
    feed = SimulatedFeed(symbol="SIM", n_ticks=50, seed=1)
    ticks = list(feed.ticks())
    path = tmp_path / "rec.csv"
    n = write_ticks_csv(path, ticks, depth=10)
    assert n == 50

    replayed = list(CsvReplayFeed(path).ticks())
    assert len(replayed) == 50
    # 핵심 필드 라운드트립 보존
    for a, b in zip(ticks, replayed):
        assert a.ts_ns == b.ts_ns
        assert a.symbol == b.symbol
        assert abs(a.last_price - b.last_price) < 1e-6
        assert len(a.bids) == len(b.bids)
        assert abs(a.bids[0].price - b.bids[0].price) < 1e-6


def test_recording_feed_passthrough_and_persist(tmp_path):
    feed = BinanceFeed(symbol="BTCUSDT", message_source=_depth_messages(5))
    path = tmp_path / "live_rec.csv"
    rec = RecordingFeed(feed, path, depth=10)

    streamed = list(rec.ticks())
    assert len(streamed) == 5
    assert rec.recorded == 5

    # 기록된 CSV 를 리플레이하면 동일 개수/심볼
    replayed = list(CsvReplayFeed(path).ticks())
    assert len(replayed) == 5
    assert all(t.symbol == "BTCUSDT" for t in replayed)
    assert replayed[0].best_bid == 99.9
