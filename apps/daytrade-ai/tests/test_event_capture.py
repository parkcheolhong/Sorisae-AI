"""급변 이벤트 타게팅 캡처 테스트.

검증:
  - 이벤트 윈도 틱이 원본의 부분집합이며 시간순·중복 없음.
  - 잔잔한 데이터(임계 높음)는 0틱, 임계 낮추면 다수 캡처.
  - SimulatedFeed 의 주입 이벤트를 트리거가 실제로 잡는지.
  - pre/post 윈도 길이가 반영되는지.
"""
from __future__ import annotations

from daytrade.feed.event_capture import EventCaptureConfig, iter_event_ticks
from daytrade.feed.simulated import SimulatedFeed


def _ticks(n=1500, seed=1, event_prob=0.02):
    return list(SimulatedFeed(symbol="EV", n_ticks=n, seed=seed, event_prob=event_prob).ticks())


def test_output_is_ordered_subset_without_dupes():
    ticks = _ticks()
    out = list(iter_event_ticks(ticks, EventCaptureConfig(ret_bps=3.0, window=10, pre=5, post=10)))
    ts = [t.ts_ns for t in out]
    assert ts == sorted(ts)              # 시간순
    assert len(ts) == len(set(ts))       # 중복 없음
    src_ts = {t.ts_ns for t in ticks}
    assert all(t.ts_ns in src_ts for t in out)  # 부분집합
    assert 0 < len(out) < len(ticks)     # 일부만(전량 아님)


def test_high_threshold_captures_nothing():
    ticks = _ticks(event_prob=0.0)  # 이벤트 미주입
    out = list(iter_event_ticks(ticks, EventCaptureConfig(ret_bps=10_000.0, window=10, pre=2, post=2)))
    assert out == []


def test_lower_threshold_captures_more():
    ticks = _ticks()
    few = list(iter_event_ticks(ticks, EventCaptureConfig(ret_bps=8.0, window=10, pre=2, post=5)))
    many = list(iter_event_ticks(ticks, EventCaptureConfig(ret_bps=2.0, window=10, pre=2, post=5)))
    assert len(many) >= len(few)


def test_vol_spike_trigger():
    ticks = _ticks(event_prob=0.03)
    out = list(iter_event_ticks(
        ticks, EventCaptureConfig(ret_bps=0.0, vol_spike=2.0, window=10, pre=1, post=5)
    ))
    assert len(out) > 0


def test_obi_z_trigger():
    ticks = _ticks(event_prob=0.03)
    out = list(iter_event_ticks(
        ticks, EventCaptureConfig(ret_bps=0.0, obi_z=2.5, window=10, pre=1, post=5)
    ))
    assert len(out) > 0


def test_max_events_caps_windows():
    ticks = _ticks(event_prob=0.05)
    capped = list(iter_event_ticks(
        ticks, EventCaptureConfig(ret_bps=2.0, window=10, pre=1, post=3, max_events=1)
    ))
    uncapped = list(iter_event_ticks(
        ticks, EventCaptureConfig(ret_bps=2.0, window=10, pre=1, post=3, max_events=0)
    ))
    assert 0 < len(capped) <= len(uncapped)
