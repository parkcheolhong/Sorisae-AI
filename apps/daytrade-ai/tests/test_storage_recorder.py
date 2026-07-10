"""틱 스토어 레코더 테스트 — 통과기록·일별 로테이션·이어쓰기(캡처 재시작 안전)."""
from __future__ import annotations

from datetime import datetime, timezone

from daytrade.feed.memory import ListFeed
from daytrade.feed.simulated import SimulatedFeed
from daytrade.storage import (
    RollingTickStoreWriter,
    StoreRecordingFeed,
    TickStore,
    TickStoreWriter,
)


def _ticks(n=300, seed=5):
    return list(SimulatedFeed(symbol="BTCUSDT", n_ticks=n, seed=seed).ticks())


def _ts(date_str: str) -> float:
    return datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp()


def test_recording_feed_passthrough_and_persists(tmp_path):
    ticks = _ticks()
    feed = StoreRecordingFeed(ListFeed(ticks), tmp_path, symbol="BTCUSDT", depth=10,
                              wall=lambda: _ts("20260101"))
    passed = list(feed.ticks())
    assert len(passed) == len(ticks)            # 통과(pass-through) 무손실
    assert feed.recorded == len(ticks)

    # 같은 날 → 단일 파일에 전량 기록.
    files = sorted(tmp_path.glob("*.dts"))
    assert len(files) == 1
    store = TickStore(files[0])
    assert len(store) == len(ticks)
    assert store.symbol == "BTCUSDT"
    assert [t.ts_ns for t in store.read_all()] == [t.ts_ns for t in ticks]


def test_rolling_writer_rotates_on_utc_date(tmp_path):
    ticks = _ticks(n=10)
    clock = {"t": _ts("20260101")}
    w = RollingTickStoreWriter(tmp_path, "BTCUSDT", depth=10, wall=lambda: clock["t"])
    for t in ticks[:6]:
        w.append(t)
    clock["t"] = _ts("20260102")     # 날짜 경계 넘김.
    for t in ticks[6:]:
        w.append(t)
    w.close()

    f1 = tmp_path / "ticks_BTCUSDT_20260101.dts"
    f2 = tmp_path / "ticks_BTCUSDT_20260102.dts"
    assert f1.exists() and f2.exists()
    assert len(TickStore(f1)) == 6
    assert len(TickStore(f2)) == 4
    assert w.total == 10


def test_append_mode_continues_same_file(tmp_path):
    ticks = _ticks(n=20)
    path = tmp_path / "btc.dts"
    with TickStoreWriter(path, depth=10, symbol="BTCUSDT") as w:
        w.extend(ticks[:8])
    assert len(TickStore(path)) == 8
    # 이어쓰기로 재오픈(재시작 시뮬) → 헤더/depth 재사용, 기존 8개 보존 + 추가.
    with TickStoreWriter(path, append=True) as w:
        assert w.count == 8
        assert w.depth == 10 and w.symbol == "BTCUSDT"
        w.extend(ticks[8:])
    store = TickStore(path)
    assert len(store) == 20
    assert [t.ts_ns for t in store.read_all()] == [t.ts_ns for t in ticks]


def test_rolling_restart_appends_not_truncates(tmp_path):
    ticks = _ticks(n=12)
    clock = lambda: _ts("20260101")  # noqa: E731
    w1 = RollingTickStoreWriter(tmp_path, "BTCUSDT", depth=10, wall=clock)
    for t in ticks[:5]:
        w1.append(t)
    w1.close()
    # 재시작: 같은 날 동일 파일에 이어쓰기.
    w2 = RollingTickStoreWriter(tmp_path, "BTCUSDT", depth=10, wall=clock)
    for t in ticks[5:]:
        w2.append(t)
    w2.close()
    store = TickStore(tmp_path / "ticks_BTCUSDT_20260101.dts")
    assert len(store) == 12
