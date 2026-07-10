"""MetricsCollector — 실행 중 핵심 지표 집계 + 최종 요약(RunMetrics).

수집: 처리 레이턴시(ms), 체결 슬리피지, 순자산(equity) 곡선, 시그널/주문/체결 카운트.
요약: 레이턴시 p50/p95/p99, 평균 슬리피지, 총/실현 손익, Sharpe(샘플 기반), 최대낙폭(MDD).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np  # pyright: ignore[reportMissingImports]


@dataclass(slots=True)
class RunMetrics:
    ticks: int
    signals: int
    orders_submitted: int
    fills: int
    rejects: int
    latency_ms_p50: float
    latency_ms_p95: float
    latency_ms_p99: float
    latency_ms_max: float
    mean_slippage_pct: float
    start_equity: float
    end_equity: float
    total_return_pct: float
    realized_pnl: float
    sharpe: float
    max_drawdown_pct: float
    halted: bool
    equity_curve: list[float] = field(default_factory=list)  # 분석/리포트용(as_dict 제외)

    def as_dict(self) -> dict[str, float | int | bool]:
        return {
            "ticks": self.ticks,
            "signals": self.signals,
            "orders_submitted": self.orders_submitted,
            "fills": self.fills,
            "rejects": self.rejects,
            "latency_ms_p50": round(self.latency_ms_p50, 4),
            "latency_ms_p95": round(self.latency_ms_p95, 4),
            "latency_ms_p99": round(self.latency_ms_p99, 4),
            "latency_ms_max": round(self.latency_ms_max, 4),
            "mean_slippage_pct": round(self.mean_slippage_pct, 6),
            "start_equity": round(self.start_equity, 2),
            "end_equity": round(self.end_equity, 2),
            "total_return_pct": round(self.total_return_pct, 4),
            "realized_pnl": round(self.realized_pnl, 2),
            "sharpe": round(self.sharpe, 4),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "halted": self.halted,
        }


@dataclass(slots=True)
class MetricsCollector:
    start_equity: float
    ticks: int = 0
    signals: int = 0
    orders_submitted: int = 0
    fills: int = 0
    rejects: int = 0
    halted: bool = False
    _latencies_ms: list[float] = field(default_factory=list)
    _slippages: list[float] = field(default_factory=list)
    _equity_curve: list[float] = field(default_factory=list)

    def record_tick(self, latency_ms: float, equity: float) -> None:
        self.ticks += 1
        self._latencies_ms.append(latency_ms)
        self._equity_curve.append(equity)

    def record_signal(self) -> None:
        self.signals += 1

    def record_order(self) -> None:
        self.orders_submitted += 1

    def record_fill(self, slippage: float) -> None:
        self.fills += 1
        self._slippages.append(abs(slippage))

    def record_reject(self) -> None:
        self.rejects += 1

    def mark_halted(self) -> None:
        self.halted = True

    def finalize(self) -> RunMetrics:
        lat = np.asarray(self._latencies_ms, dtype=float) if self._latencies_ms else np.zeros(1)
        slips = np.asarray(self._slippages, dtype=float) if self._slippages else np.zeros(1)
        equity = np.asarray(self._equity_curve, dtype=float) if self._equity_curve else np.asarray([self.start_equity])

        end_equity = float(equity[-1])
        total_return = (end_equity - self.start_equity) / self.start_equity if self.start_equity else 0.0

        return RunMetrics(
            ticks=self.ticks,
            signals=self.signals,
            orders_submitted=self.orders_submitted,
            fills=self.fills,
            rejects=self.rejects,
            latency_ms_p50=float(np.percentile(lat, 50)),
            latency_ms_p95=float(np.percentile(lat, 95)),
            latency_ms_p99=float(np.percentile(lat, 99)),
            latency_ms_max=float(np.max(lat)),
            mean_slippage_pct=float(np.mean(slips)),
            start_equity=self.start_equity,
            end_equity=end_equity,
            total_return_pct=total_return * 100.0,
            realized_pnl=end_equity - self.start_equity,
            sharpe=_sharpe(equity),
            max_drawdown_pct=_max_drawdown(equity) * 100.0,
            halted=self.halted,
            equity_curve=[float(x) for x in equity],
        )


def _sharpe(equity: np.ndarray) -> float:
    """순자산 곡선의 틱-수익률 기반 Sharpe(무위험 0 가정). 샘플<2면 0."""
    if equity.size < 2:
        return 0.0
    rets = np.diff(equity) / equity[:-1]
    rets = rets[np.isfinite(rets)]
    if rets.size < 2:
        return 0.0
    std = float(np.std(rets, ddof=1))
    if std <= 0:
        return 0.0
    return float(np.mean(rets) / std * np.sqrt(rets.size))


def _max_drawdown(equity: np.ndarray) -> float:
    if equity.size == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return float(abs(np.min(dd)))
