"""경량 인프로세스 스케줄러(설계서 §7 일일 재학습 / §9 주기 튜닝) — Airflow 없이 상주.

간격(interval) 작업과 UTC 시각(daily) 작업을 한 프로세스에서 돌린다. 외부 의존성 0, 주입 가능한
시계/sleep 으로 테스트 가능. 작업 예외는 흡수(스케줄러 계속 가동)하고 실행 이력/에러를 기록한다.
그레이스풀 종료(`request_stop`)를 지원해 systemd/Docker SIGTERM 과 결합한다.

용도(`scripts/scheduler.py`): 일일 02:00 UTC **재학습**, 5분마다 **튜닝 트리거**.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


@dataclass
class Job:
    name: str
    fn: Callable[[], object]
    kind: str                      # "interval" | "daily"
    interval_sec: float = 0.0
    at_hour: int = 0
    at_minute: int = 0
    next_mono: float = 0.0         # interval 작업 다음 실행(monotonic)
    next_wall: float = 0.0         # daily 작업 다음 실행(unix wall)
    runs: int = 0
    errors: int = 0
    last_error: str = ""
    last_result: object = None


def _next_daily_wall(now_wall: float, hour: int, minute: int) -> float:
    """now 이후 가장 가까운 hour:minute(UTC) 의 unix timestamp."""
    now = datetime.fromtimestamp(now_wall, tz=timezone.utc)
    cand = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    ts = cand.timestamp()
    if ts <= now_wall:
        ts += 86400.0
    return ts


class Scheduler:
    def __init__(
        self,
        *,
        mono: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
        poll_sec: float = 1.0,
        on_event: Callable[[dict], None] | None = None,
        stop_flag: Callable[[], bool] | None = None,
    ) -> None:
        self._mono = mono
        self._wall = wall
        self._sleep = sleep
        self.poll_sec = poll_sec
        self.on_event = on_event
        self.stop_flag = stop_flag
        self._stop = False
        self.jobs: list[Job] = []

    # ── 등록 ──
    def every(self, name: str, interval_sec: float, fn: Callable[[], object], *, run_at_start: bool = False) -> Job:
        job = Job(name=name, fn=fn, kind="interval", interval_sec=float(interval_sec),
                  next_mono=self._mono() + (0.0 if run_at_start else interval_sec))
        self.jobs.append(job)
        return job

    def daily(self, name: str, at_hour: int, fn: Callable[[], object], *, at_minute: int = 0) -> Job:
        job = Job(name=name, fn=fn, kind="daily", at_hour=int(at_hour), at_minute=int(at_minute),
                  next_wall=_next_daily_wall(self._wall(), at_hour, at_minute))
        self.jobs.append(job)
        return job

    # ── 제어 ──
    def request_stop(self) -> None:
        self._stop = True

    def _should_stop(self) -> bool:
        return self._stop or (self.stop_flag is not None and self.stop_flag())

    # ── 실행 ──
    def _emit(self, event: str, **kw) -> None:
        if self.on_event is not None:
            self.on_event({"event": event, **kw})

    def run_due(self, now_mono: float, now_wall: float) -> list[str]:
        """현재 시각 기준 due 작업을 1회씩 실행하고 실행된 작업명을 반환(테스트 가능 단위)."""
        ran: list[str] = []
        for job in self.jobs:
            due = (job.kind == "interval" and now_mono >= job.next_mono) or \
                  (job.kind == "daily" and now_wall >= job.next_wall)
            if not due:
                continue
            self._emit("job_start", job=job.name, kind=job.kind)
            try:
                job.last_result = job.fn()
                job.runs += 1
                self._emit("job_done", job=job.name, runs=job.runs)
            except Exception as exc:  # noqa: BLE001 — 작업 실패는 흡수(상주 지속)
                job.errors += 1
                job.last_error = f"{type(exc).__name__}: {exc}"
                self._emit("job_error", job=job.name, error=job.last_error)
            # 다음 실행 예약.
            if job.kind == "interval":
                job.next_mono = now_mono + job.interval_sec
            else:
                job.next_wall = _next_daily_wall(now_wall, job.at_hour, job.at_minute)
            ran.append(job.name)
        return ran

    def run(self, *, max_iterations: int | None = None, max_runtime_sec: float = 0.0) -> dict:
        """폴링 루프. max_iterations/max_runtime_sec/stop 으로 종료(상주 시 둘 다 0)."""
        start = self._mono()
        it = 0
        while not self._should_stop():
            self.run_due(self._mono(), self._wall())
            it += 1
            if max_iterations is not None and it >= max_iterations:
                break
            if max_runtime_sec and (self._mono() - start) >= max_runtime_sec:
                break
            self._sleep(self.poll_sec)
        return self.summary()

    def summary(self) -> dict:
        return {"jobs": [{"name": j.name, "kind": j.kind, "runs": j.runs,
                          "errors": j.errors, "last_error": j.last_error} for j in self.jobs]}
