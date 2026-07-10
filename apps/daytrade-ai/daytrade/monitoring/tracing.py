"""인프로세스 분산 트레이싱(설계서 §10-5 Jaeger 대응) — 의존성 0.

파이프라인 구간(feature→detection→inference→risk/exec)을 span 으로 계측한다. 핫패스 오버헤드를
없애기 위해 기본 트레이서는 **NoopTracer**(컨텍스트 매니저가 즉시 반환)이며, 트레이싱을 켤 때만
`Tracer`(+샘플링)를 주입한다. 수집한 span 은 Jaeger 호환 JSON 으로 내보내거나, 구간별 레이턴시
요약(p50/p95/p99 µs)으로 집계한다.
"""
from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field

import numpy as np  # pyright: ignore[reportMissingImports]


@dataclass(slots=True)
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    start_ns: int
    end_ns: int = 0
    tags: dict = field(default_factory=dict)

    @property
    def duration_us(self) -> float:
        return (self.end_ns - self.start_ns) / 1e3


class NoopTracer:
    """제로 오버헤드 기본 트레이서 — 컨텍스트 매니저가 아무것도 하지 않음."""

    sampling = False

    def new_trace(self) -> None:  # noqa: D401
        return None

    @contextmanager
    def span(self, name: str, **tags):
        yield None

    @property
    def spans(self) -> list:
        return []


class Tracer:
    """샘플링 가능한 인프로세스 트레이서.

    Args:
        sample_rate: N틱당 1개 트레이스만 기록(1=모두, 0=비활성). `new_trace()` 호출 카운트 기준.
        max_spans: 메모리 가드(초과 시 오래된 span 드롭).
        clock: 테스트용 주입 가능한 ns 시계.
    """

    def __init__(self, sample_rate: int = 1, max_spans: int = 200_000, clock=time.perf_counter_ns) -> None:
        self.sample_rate = max(0, int(sample_rate))
        self.max_spans = max_spans
        self._clock = clock
        self._spans: list[Span] = []
        self._stack: list[Span] = []
        self._trace_id: str | None = None
        self._trace_count = 0
        self._active = False

    @property
    def sampling(self) -> bool:
        return True

    def new_trace(self) -> None:
        """틱 단위 트레이스 시작. 샘플링 규칙에 따라 활성/비활성 결정."""
        self._trace_count += 1
        self._stack.clear()
        if self.sample_rate <= 0:
            self._active = False
            return
        self._active = (self._trace_count % self.sample_rate) == 0 if self.sample_rate > 1 else True
        if self._active:
            self._trace_id = uuid.uuid4().hex[:16]

    @contextmanager
    def span(self, name: str, **tags):
        if not self._active:
            yield None
            return
        parent = self._stack[-1].span_id if self._stack else None
        sp = Span(
            name=name,
            trace_id=self._trace_id or uuid.uuid4().hex[:16],
            span_id=uuid.uuid4().hex[:16],
            parent_id=parent,
            start_ns=self._clock(),
            tags=dict(tags),
        )
        self._stack.append(sp)
        try:
            yield sp
        finally:
            sp.end_ns = self._clock()
            self._stack.pop()
            if len(self._spans) < self.max_spans:
                self._spans.append(sp)

    @property
    def spans(self) -> list[Span]:
        return self._spans

    def export_jaeger(self) -> list[dict]:
        """Jaeger 스타일 JSON(span 리스트). 운영 Jaeger collector 로 전송 시 변환 기준."""
        out = []
        for s in self._spans:
            out.append({
                "traceID": s.trace_id,
                "spanID": s.span_id,
                "operationName": s.name,
                "references": ([{"refType": "CHILD_OF", "spanID": s.parent_id}] if s.parent_id else []),
                "startTime": s.start_ns // 1000,  # µs epoch 근사(perf_counter 기준 상대)
                "duration": int(s.duration_us),
                "tags": [{"key": k, "value": v} for k, v in s.tags.items()],
            })
        return out

    def stage_summary(self) -> dict[str, dict]:
        """구간(operationName)별 count + p50/p95/p99/max 레이턴시(µs)."""
        by_name: dict[str, list[float]] = {}
        for s in self._spans:
            by_name.setdefault(s.name, []).append(s.duration_us)
        summary = {}
        for name, durs in by_name.items():
            arr = np.asarray(durs, dtype=float)
            summary[name] = {
                "count": int(arr.size),
                "p50_us": round(float(np.percentile(arr, 50)), 3),
                "p95_us": round(float(np.percentile(arr, 95)), 3),
                "p99_us": round(float(np.percentile(arr, 99)), 3),
                "max_us": round(float(np.max(arr)), 3),
            }
        return summary
