"""(나) 틱 스토어(.dts) CLI 결선 — 확장자 디스패치 + replay/walkforward 입력."""
from __future__ import annotations

from daytrade.cli import load_replay_feed, main
from daytrade.feed.replay import CsvReplayFeed
from daytrade.feed.simulated import SimulatedFeed
from daytrade.storage import TickStoreFeed, write_ticks_store


def _make_store(tmp_path, n=1500):
    ticks = list(SimulatedFeed(symbol="AAPL", n_ticks=n, seed=11).ticks())
    path = tmp_path / "aapl.dts"
    write_ticks_store(path, ticks)
    return path, ticks


def test_load_replay_feed_dispatch(tmp_path):
    path, ticks = _make_store(tmp_path)
    feed = load_replay_feed(str(path))
    assert isinstance(feed, TickStoreFeed)
    assert sum(1 for _ in feed.ticks()) == len(ticks)
    # CSV 경로는 기존 CsvReplayFeed.
    assert isinstance(load_replay_feed("x.csv"), CsvReplayFeed)


def test_replay_backtest_accepts_dts(tmp_path):
    path, _ = _make_store(tmp_path)
    rc = main(["replay", "--csv", str(path), "--symbol", "AAPL", "--no-ai", "--json"])
    assert rc == 0


def test_walkforward_accepts_dts(tmp_path):
    path, _ = _make_store(tmp_path, n=2000)
    rc = main(["walkforward", "--csv", str(path), "--symbol", "AAPL",
               "--n-splits", "3", "--horizon", "20", "--json"])
    assert rc == 0
