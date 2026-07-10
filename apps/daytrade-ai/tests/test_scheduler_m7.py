"""M7 (F) — 경량 인프로세스 스케줄러 테스트(interval/daily, 예외 흡수, 그레이스풀 종료)."""
from __future__ import annotations

from datetime import datetime, timezone

from daytrade.ops import Scheduler


class _Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


def test_interval_job_fires_on_schedule():
    mono = _Clock(0.0)
    hits = []
    sch = Scheduler(mono=mono, wall=lambda: 0.0, sleep=lambda s: None)
    sch.every("tick", 5.0, lambda: hits.append(mono.t))
    # t=0,1,..,12 폴링: 5,10 에서 발화(첫 due=5).
    for t in range(0, 13):
        mono.t = float(t)
        sch.run_due(mono.t, 0.0)
    assert hits == [5.0, 10.0]


def test_interval_run_at_start():
    mono = _Clock(0.0)
    hits = []
    sch = Scheduler(mono=mono, wall=lambda: 0.0)
    sch.every("now", 10.0, lambda: hits.append(1), run_at_start=True)
    sch.run_due(0.0, 0.0)
    assert hits == [1]


def test_daily_job_fires_after_utc_hour():
    base = datetime(2026, 6, 24, 1, 0, tzinfo=timezone.utc).timestamp()  # 01:00
    wall = _Clock(base)
    runs = []
    sch = Scheduler(mono=lambda: 0.0, wall=wall, sleep=lambda s: None)
    sch.daily("retrain", at_hour=2, fn=lambda: runs.append(wall.t))  # 02:00 UTC
    sch.run_due(0.0, wall.t)                 # 01:00 → 아직
    assert runs == []
    wall.t = datetime(2026, 6, 24, 2, 1, tzinfo=timezone.utc).timestamp()
    sch.run_due(0.0, wall.t)                 # 02:01 → 발화
    assert len(runs) == 1
    # 다음 실행은 익일로 예약(같은 날 재발화 없음).
    wall.t = datetime(2026, 6, 24, 23, 0, tzinfo=timezone.utc).timestamp()
    sch.run_due(0.0, wall.t)
    assert len(runs) == 1


def test_job_exception_is_absorbed():
    events = []
    sch = Scheduler(mono=_Clock(100.0), wall=lambda: 0.0, on_event=events.append)

    def _boom():
        raise RuntimeError("fail")

    job = sch.every("bad", 1.0, _boom, run_at_start=True)
    sch.run_due(100.0, 0.0)
    assert job.errors == 1 and "RuntimeError" in job.last_error
    assert any(e["event"] == "job_error" for e in events)


def test_run_loop_max_iterations_and_stop():
    mono = _Clock(0.0)
    n = {"c": 0}
    sch = Scheduler(mono=mono, wall=lambda: 0.0, sleep=lambda s: None)
    sch.every("count", 1.0, lambda: n.__setitem__("c", n["c"] + 1), run_at_start=True)
    # mono 가 고정이면 첫 발화 후 next_mono=1 로 더는 안 됨 → max_iterations 로 종료.
    summary = sch.run(max_iterations=5)
    assert summary["jobs"][0]["runs"] == 1
    assert n["c"] == 1


def test_request_stop_halts_run():
    mono = _Clock(0.0)
    sch = Scheduler(mono=mono, wall=lambda: 0.0, sleep=lambda s: None)
    calls = {"n": 0}

    def _job():
        calls["n"] += 1
        sch.request_stop()  # 첫 실행에서 종료 요청

    sch.every("once", 1.0, _job, run_at_start=True)
    sch.run(max_iterations=1000)
    assert calls["n"] == 1
