"""Prometheus 메트릭 exporter(설계서 §10-5 모니터링).

의존성 없는 순수 파이썬으로 Prometheus **text exposition format** 을 생성한다(Counter/Gauge/
Histogram). `prometheus_client` 미설치 환경에서도 동작하며, 생성한 텍스트를 파일/HTTP `/metrics`
로 노출하면 Prometheus 가 스크레이프한다. 라벨(symbol/mode 등) 지원.

설계서 §10-5 권장 지표: 레이턴시 히스토그램·슬리피지·P&L·포지션·주문 성공률·서킷브레이커 상태.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

_LabelKey = tuple[tuple[str, str], ...]


def _fmt(v: float) -> str:
    if v != v:  # NaN
        return "NaN"
    if v == int(v):
        return str(int(v))
    return repr(v)


def _labels_str(labels: _LabelKey) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{k}="{_escape(v)}"' for k, v in labels)
    return "{" + inner + "}"


def _escape(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


@dataclass
class _Metric:
    name: str
    help: str
    mtype: str  # counter | gauge | histogram
    values: dict[_LabelKey, float] = field(default_factory=dict)
    # histogram 전용
    buckets: tuple[float, ...] = ()
    bucket_counts: dict[_LabelKey, list[int]] = field(default_factory=dict)
    sums: dict[_LabelKey, float] = field(default_factory=dict)
    counts: dict[_LabelKey, int] = field(default_factory=dict)


class MetricsRegistry:
    """스레드 안전 메트릭 레지스트리 → Prometheus 노출 텍스트 렌더."""

    def __init__(self) -> None:
        self._metrics: dict[str, _Metric] = {}
        self._lock = threading.Lock()

    def _key(self, labels: dict[str, str] | None) -> _LabelKey:
        return tuple(sorted((labels or {}).items()))

    def counter(self, name: str, help: str = "") -> None:
        self._ensure(name, help, "counter")

    def gauge(self, name: str, help: str = "") -> None:
        self._ensure(name, help, "gauge")

    def histogram(self, name: str, buckets: tuple[float, ...], help: str = "") -> None:
        m = self._ensure(name, help, "histogram")
        m.buckets = tuple(sorted(buckets))

    def _ensure(self, name: str, help: str, mtype: str) -> _Metric:
        with self._lock:
            m = self._metrics.get(name)
            if m is None:
                m = _Metric(name=name, help=help, mtype=mtype)
                self._metrics[name] = m
            return m

    def inc(self, name: str, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
        k = self._key(labels)
        with self._lock:
            m = self._metrics[name]
            m.values[k] = m.values.get(k, 0.0) + amount

    def set(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        k = self._key(labels)
        with self._lock:
            self._metrics[name].values[k] = value

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        k = self._key(labels)
        with self._lock:
            m = self._metrics[name]
            if k not in m.bucket_counts:
                m.bucket_counts[k] = [0] * (len(m.buckets) + 1)  # +Inf 포함
                m.sums[k] = 0.0
                m.counts[k] = 0
            placed = False
            for i, b in enumerate(m.buckets):
                if value <= b:
                    m.bucket_counts[k][i] += 1
                    placed = True
                    break
            if not placed:
                m.bucket_counts[k][-1] += 1
            m.sums[k] += value
            m.counts[k] += 1

    def render(self) -> str:  # NOSONAR
        """Prometheus text exposition format 문자열 생성."""
        lines: list[str] = []
        with self._lock:
            for m in self._metrics.values():
                if m.help:
                    lines.append(f"# HELP {m.name} {m.help}")
                lines.append(f"# TYPE {m.name} {m.mtype}")
                if m.mtype == "histogram":
                    for k in sorted(m.bucket_counts, key=lambda x: str(x)):
                        cumulative = 0
                        for i, b in enumerate(m.buckets):
                            cumulative += m.bucket_counts[k][i]
                            le = dict(k) | {"le": _fmt(b)}
                            lines.append(f"{m.name}_bucket{_labels_str(tuple(sorted(le.items())))} {cumulative}")
                        cumulative += m.bucket_counts[k][-1]
                        le_inf = dict(k) | {"le": "+Inf"}
                        lines.append(f"{m.name}_bucket{_labels_str(tuple(sorted(le_inf.items())))} {cumulative}")
                        lines.append(f"{m.name}_sum{_labels_str(k)} {_fmt(m.sums[k])}")
                        lines.append(f"{m.name}_count{_labels_str(k)} {m.counts[k]}")
                else:
                    for k, v in m.values.items():
                        lines.append(f"{m.name}{_labels_str(k)} {_fmt(v)}")
        return "\n".join(lines) + "\n"


# Prometheus 권장 레이턴시 버킷(초 단위; 스캘핑은 ms 이하라 마이크로~밀리초 위주).
LATENCY_MS_BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0)


class LiveMetrics:
    """라이브 갱신용 레지스트리 래퍼 — `MetricsCollector` 상태를 매 N틱 싸게 반영.

    HTTP `/metrics` 서버에 `registry_provider` 로 `.registry` 를 넘기면, 트레이딩 루프가 `.update()`
    를 호출할 때마다 스크레이프에 즉시 반영된다(finalize 불필요).
    """

    def __init__(self, *, symbol: str, mode: str) -> None:
        self._lbl = {"symbol": symbol, "mode": mode}
        self.registry = MetricsRegistry()
        r = self.registry
        r.gauge("daytrade_equity", "현재 순자산")
        r.gauge("daytrade_circuit_breaker_halted", "서킷브레이커 중단(1=halted)")
        r.gauge("daytrade_last_tick_unixtime", "마지막 틱 처리 unixtime(정체 감지)")
        r.gauge("daytrade_ticks_total", "처리 틱 수")
        r.gauge("daytrade_signals_total", "시그널 수")
        r.gauge("daytrade_orders_total", "주문 제출 수")
        r.gauge("daytrade_fills_total", "체결 수")
        r.gauge("daytrade_rejects_total", "거절 수")
        # M7-I: 재학습/핫스왑 추적(Grafana에서 모델 승격·런타임 교체 시점 가시화).
        r.gauge("daytrade_model_version", "현재 운영 모델 버전(current.json)")
        r.gauge("daytrade_model_reloads_total", "런타임 모델 핫스왑 누적 횟수")

    def update(self, collector, equity: float, *, now_unixtime: float | None = None) -> None:
        import time as _t

        lbl = self._lbl
        self.registry.set("daytrade_equity", equity, lbl)
        self.registry.set("daytrade_circuit_breaker_halted", 1.0 if collector.halted else 0.0, lbl)
        self.registry.set("daytrade_last_tick_unixtime", now_unixtime if now_unixtime is not None else _t.time(), lbl)
        self.registry.set("daytrade_ticks_total", collector.ticks, lbl)
        self.registry.set("daytrade_signals_total", collector.signals, lbl)
        self.registry.set("daytrade_orders_total", collector.orders_submitted, lbl)
        self.registry.set("daytrade_fills_total", collector.fills, lbl)
        self.registry.set("daytrade_rejects_total", collector.rejects, lbl)

    def set_model(self, version: int | None, reloads: int) -> None:
        """운영 모델 버전·핫스왑 횟수 게이지 갱신(LiveRunner 핫스왑 시 호출)."""
        lbl = self._lbl
        self.registry.set("daytrade_model_version", float(version or 0), lbl)
        self.registry.set("daytrade_model_reloads_total", float(reloads), lbl)


def registry_from_run(run_metrics, *, symbol: str, mode: str, router_stats: dict | None = None) -> MetricsRegistry:
    """`RunMetrics`(+선택 RouterStats)를 Prometheus 레지스트리로 변환."""
    reg = MetricsRegistry()
    lbl = {"symbol": symbol, "mode": mode}

    reg.gauge("daytrade_equity", "현재 순자산")
    reg.gauge("daytrade_return_pct", "총 수익률(%)")
    reg.gauge("daytrade_realized_pnl", "실현 손익")
    reg.gauge("daytrade_sharpe", "Sharpe(틱 기반)")
    reg.gauge("daytrade_max_drawdown_pct", "최대 낙폭(%)")
    reg.gauge("daytrade_latency_ms_p99", "처리 레이턴시 p99(ms)")
    reg.gauge("daytrade_mean_slippage_pct", "평균 슬리피지(%)")
    reg.gauge("daytrade_circuit_breaker_halted", "서킷브레이커 중단(1=halted)")
    reg.counter("daytrade_signals_total", "시그널 수")
    reg.counter("daytrade_orders_total", "주문 제출 수")
    reg.counter("daytrade_fills_total", "체결 수")
    reg.counter("daytrade_rejects_total", "거절 수")

    reg.set("daytrade_equity", run_metrics.end_equity, lbl)
    reg.set("daytrade_return_pct", run_metrics.total_return_pct, lbl)
    reg.set("daytrade_realized_pnl", run_metrics.realized_pnl, lbl)
    reg.set("daytrade_sharpe", run_metrics.sharpe, lbl)
    reg.set("daytrade_max_drawdown_pct", run_metrics.max_drawdown_pct, lbl)
    reg.set("daytrade_latency_ms_p99", run_metrics.latency_ms_p99, lbl)
    reg.set("daytrade_mean_slippage_pct", run_metrics.mean_slippage_pct * 100.0, lbl)
    reg.set("daytrade_circuit_breaker_halted", 1.0 if run_metrics.halted else 0.0, lbl)
    reg.inc("daytrade_signals_total", run_metrics.signals, lbl)
    reg.inc("daytrade_orders_total", run_metrics.orders_submitted, lbl)
    reg.inc("daytrade_fills_total", run_metrics.fills, lbl)
    reg.inc("daytrade_rejects_total", run_metrics.rejects, lbl)
    return reg


def registry_from_kpi_verdict(verdict: dict, *, registry: MetricsRegistry | None = None) -> MetricsRegistry:
    """KPI 회귀셋 verdict(`KpiRegressionReport.verdict`)를 Prometheus 게이지로 변환(M7-G/I).

    배치(CI/스케줄) 작업이 textfile collector/pushgateway 로 노출하기 위한 용도.
    `metric` 라벨로 목적 지표를 구분한다.
    """
    reg = registry or MetricsRegistry()
    lbl = {"metric": str(verdict.get("metric", "mean_oos_sharpe"))}
    reg.gauge("daytrade_kpi_passed", "KPI 회귀 개선 판정(1=PASS)")
    reg.gauge("daytrade_kpi_baseline_sharpe", "레짐 평균 OOS Sharpe(baseline)")
    reg.gauge("daytrade_kpi_tuned_sharpe", "레짐 평균 OOS Sharpe(tuned)")
    reg.gauge("daytrade_kpi_baseline_return_pct", "레짐 평균 OOS 수익률%(baseline)")
    reg.gauge("daytrade_kpi_tuned_return_pct", "레짐 평균 OOS 수익률%(tuned)")
    reg.gauge("daytrade_kpi_baseline_worst_mdd_pct", "레짐 평균 최악 MDD%(baseline)")
    reg.gauge("daytrade_kpi_tuned_worst_mdd_pct", "레짐 평균 최악 MDD%(tuned)")
    reg.gauge("daytrade_kpi_regimes_improved", "개선된 레짐 수")
    reg.gauge("daytrade_kpi_regimes_total", "총 레짐 수")

    reg.set("daytrade_kpi_passed", 1.0 if verdict.get("passed") else 0.0, lbl)
    reg.set("daytrade_kpi_baseline_sharpe", float(verdict.get("baseline_mean_sharpe", 0.0)), lbl)
    reg.set("daytrade_kpi_tuned_sharpe", float(verdict.get("tuned_mean_sharpe", 0.0)), lbl)
    reg.set("daytrade_kpi_baseline_return_pct", float(verdict.get("baseline_mean_return_pct", 0.0)), lbl)
    reg.set("daytrade_kpi_tuned_return_pct", float(verdict.get("tuned_mean_return_pct", 0.0)), lbl)
    reg.set("daytrade_kpi_baseline_worst_mdd_pct", float(verdict.get("baseline_mean_worst_mdd_pct", 0.0)), lbl)
    reg.set("daytrade_kpi_tuned_worst_mdd_pct", float(verdict.get("tuned_mean_worst_mdd_pct", 0.0)), lbl)
    reg.set("daytrade_kpi_regimes_improved", float(verdict.get("regimes_improved", 0)), lbl)
    reg.set("daytrade_kpi_regimes_total", float(verdict.get("regimes_total", 0)), lbl)
    return reg
