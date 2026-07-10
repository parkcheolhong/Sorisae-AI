"""백테스트 러너 — feed + config 로 파이프라인을 돌리고 리포트를 만든다."""
from __future__ import annotations

from dataclasses import dataclass

from ..config import TradingConfig
from ..feed.base import MarketFeed
from ..inference.model import InferenceModel
from ..monitoring.metrics import RunMetrics
from ..pipeline import TradingPipeline


@dataclass(slots=True)
class BacktestReport:
    metrics: RunMetrics
    effective_mode: str
    safety_reason: str

    def summary_lines(self) -> list[str]:
        m = self.metrics
        return [
            f"mode               : {self.effective_mode}  ({self.safety_reason})",
            f"ticks / signals    : {m.ticks} / {m.signals}",
            f"orders / fills / rej: {m.orders_submitted} / {m.fills} / {m.rejects}",
            f"latency p50/p95/p99: {m.latency_ms_p50:.3f} / {m.latency_ms_p95:.3f} / {m.latency_ms_p99:.3f} ms",
            f"latency max        : {m.latency_ms_max:.3f} ms",
            f"mean slippage      : {m.mean_slippage_pct * 100:.4f} %",
            f"equity start/end   : {m.start_equity:,.2f} -> {m.end_equity:,.2f}",
            f"total return       : {m.total_return_pct:.4f} %",
            f"realized pnl       : {m.realized_pnl:,.2f}",
            f"sharpe             : {m.sharpe:.4f}",
            f"max drawdown       : {m.max_drawdown_pct:.4f} %",
            f"halted (breaker)   : {m.halted}",
        ]


def run_backtest(
    config: TradingConfig,
    feed: MarketFeed,
    *,
    model: InferenceModel | None = None,
    model_path: str | None = None,
    max_ticks: int | None = None,
) -> BacktestReport:
    pipeline = TradingPipeline(config, model=model, model_path=model_path)
    result = pipeline.run(feed, max_ticks=max_ticks)
    return BacktestReport(
        metrics=result.metrics,
        effective_mode=result.effective_mode.value,
        safety_reason=result.safety_reason,
    )
