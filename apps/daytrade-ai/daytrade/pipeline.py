"""TradingPipeline — 전체 파이프라인 결선(설계서 §1 주요 흐름 대응).

흐름(틱당):
    feed → FeatureEngine → DetectionEngine → (AI Inference) → 결합 → RiskManager → Executor → Portfolio
       └──────────────────────────── Monitoring(레이턴시/슬리피지/P&L) ───────────────────────────┘

스캘핑 포지션 규칙(MVP):
    BUY  시그널 → 목표 포지션 +default_qty
    SELL 시그널 → 목표 포지션 −default_qty
    FLAT        → 현 포지션 유지(주문 없음)
    주문수량 = 목표 − 현재(부호) → 자연스러운 진입/청산/플립으로 왕복손익 발생.

안전: 실효 모드가 LIVE 가 아니면 executor 는 항상 PaperExecutor(모의)로 강제된다.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from .config import TradingConfig, TradingMode, resolve_safety_gate
from .detection.engine import DetectionEngine
from .execution.base import OrderExecutor
from .execution.paper import PaperExecutor
from .execution.portfolio import Portfolio
from .features.engine import FeatureEngine
from .feed.base import MarketFeed
from .inference.model import InferenceModel, load_model
from .monitoring.metrics import MetricsCollector, RunMetrics
from .monitoring.tracing import NoopTracer
from .risk.manager import RiskManager
from .types import MarketTick, Order, OrderSide, OrderType, Signal, SignalSide


@dataclass(slots=True)
class PipelineResult:
    metrics: RunMetrics
    portfolio: Portfolio
    effective_mode: TradingMode
    safety_reason: str


class TradingPipeline:
    def __init__(
        self,
        config: TradingConfig,
        *,
        executor: OrderExecutor | None = None,
        model: InferenceModel | None = None,
        model_path: str | None = None,
        env: dict[str, str] | None = None,
        on_event=None,  # optional callback(dict) for live monitoring/logging
        tracer=None,  # optional monitoring.tracing.Tracer (default NoopTracer = 무오버헤드)
    ) -> None:
        self.config = config
        self.on_event = on_event
        self.tracer = tracer or NoopTracer()

        # --- 안전 게이트: LIVE 가 아니면(또는 미인가면) paper 로 강제 ---
        self.safety = resolve_safety_gate(config, env=env)
        self.effective_mode = self.safety.effective_mode

        if self.effective_mode == TradingMode.LIVE:
            if executor is None or not executor.is_live:
                raise RuntimeError(
                    "LIVE mode requires an explicit live OrderExecutor implementation, "
                    "which is intentionally not bundled. Provide your own broker adapter."
                )
            self.executor = executor
        else:
            # paper/backtest → 항상 모의 체결기(외부에서 live 실행기를 줘도 무시).
            self.executor = PaperExecutor(config.execution, seed=config.seed)

        self.features = FeatureEngine(
            depth=config.signal.depth,
            vwap_window=config.signal.vwap_window,
            momentum_window=config.signal.momentum_window_ticks,
        )
        self.detection = DetectionEngine(config.signal)
        self.model = model or load_model(model_path)
        self.portfolio = Portfolio(starting_cash=config.starting_cash)
        self.risk = RiskManager(config.risk, starting_equity=config.starting_cash)
        self.metrics = MetricsCollector(start_equity=config.starting_cash)

    # ── 런타임 모델/시그널 핫스왑(M7 — current.json 결선) ───────────
    def apply_signal_config(self, signal) -> None:
        """시그널 임계를 런타임에 교체(탐지 엔진까지 즉시 반영). 피처 설정 변경 시 FeatureEngine 재구성."""
        old = self.config.signal
        self.config.signal = signal
        self.detection.config = signal
        if (
            signal.depth != old.depth
            or signal.vwap_window != old.vwap_window
            or signal.momentum_window_ms != old.momentum_window_ms
        ):
            self.features = FeatureEngine(
                depth=signal.depth,
                vwap_window=signal.vwap_window,
                momentum_window=signal.momentum_window_ticks,
            )

    def reload_model(self, model_path: str | None) -> None:
        """추론 모델을 런타임에 교체(Blue-Green 핫스왑 결과 적용)."""
        self.model = load_model(model_path)

    def reload_from_current(self, model_dir: str) -> dict | None:
        """`<model_dir>/current.json` 을 읽어 모델 + best 시그널 임계를 런타임에 적용.

        반환: 적용된 {version, model_path, signal} 또는 current.json 없으면 None.
        """
        from .ops.registry import apply_signal_overrides, load_current

        cur = load_current(model_dir)
        if cur is None:
            return None
        if cur.model_path:
            self.reload_model(cur.model_path)
        new_cfg = apply_signal_overrides(self.config, cur)
        self.apply_signal_config(new_cfg.signal)
        return {"version": cur.version, "model_path": cur.model_path, "signal": cur.signal}

    def _final_side(self, signal: Signal, prob_buy: float, prob_sell: float) -> tuple[SignalSide, float]:
        cfg = self.config.signal
        if not cfg.use_ai:
            return signal.side, signal.confidence

        # AI 확인 게이트: 탐지 후보 방향을 AI 확률로 확인.
        if signal.side == SignalSide.BUY and prob_buy >= cfg.ai_buy_threshold:
            return SignalSide.BUY, max(signal.confidence, prob_buy)
        if signal.side == SignalSide.SELL and prob_sell >= cfg.ai_sell_threshold:
            return SignalSide.SELL, max(signal.confidence, prob_sell)
        return SignalSide.FLAT, 0.0

    def _desired_target(self, side: SignalSide) -> float | None:
        qty = self.config.execution.default_qty
        if side == SignalSide.BUY:
            return qty
        if side == SignalSide.SELL:
            return -qty
        return None  # FLAT → 유지

    def process_tick(self, tick: MarketTick) -> None:
        t0 = time.perf_counter_ns()
        prices = {tick.symbol: tick.last_price}
        self.tracer.new_trace()

        with self.tracer.span("features", symbol=tick.symbol):
            fv = self.features.update(tick)
        with self.tracer.span("detection"):
            signal = self.detection.evaluate(fv)

        prob_buy, prob_sell = (0.0, 0.0)
        if self.config.signal.use_ai:
            with self.tracer.span("inference"):
                prob_buy, prob_sell = self.model.predict(fv)

        final_side, confidence = self._final_side(signal, prob_buy, prob_sell)
        if final_side != SignalSide.FLAT:
            self.metrics.record_signal()

        # 서킷브레이커 갱신(레이턴시는 직전까지의 처리시간 추정 + 일일손익).
        equity_now = self.portfolio.equity(prices)
        latency_ms_so_far = (time.perf_counter_ns() - t0) / 1e6
        self.risk.update_circuit_breaker(latency_ms=latency_ms_so_far, equity=equity_now)
        if self.risk.halted:
            self.metrics.mark_halted()

        target = self._desired_target(final_side)
        if target is not None and not self.risk.halted:
            pos = self.portfolio.position(tick.symbol)
            order_signed = target - pos.qty
            if abs(order_signed) >= 1.0:
                side = OrderSide.BUY if order_signed > 0 else OrderSide.SELL
                order = Order(
                    symbol=tick.symbol,
                    side=side,
                    qty=abs(order_signed),
                    order_type=OrderType.IOC,
                    ts_ns=tick.ts_ns,
                )
                expected_slip = self.config.execution.paper_slippage_bps / 10_000.0
                with self.tracer.span("risk"):
                    decision = self.risk.approve(
                        order,
                        portfolio=self.portfolio,
                        prices=prices,
                        expected_slippage_pct=expected_slip,
                    )
                if decision.approved:
                    sized = Order(
                        symbol=order.symbol,
                        side=order.side,
                        qty=decision.adjusted_qty,
                        order_type=order.order_type,
                        ts_ns=order.ts_ns,
                    )
                    self.metrics.record_order()
                    with self.tracer.span("execution", side=side.value):
                        fill = self.executor.submit(sized, tick)
                    if fill.status == "rejected" or fill.filled_qty <= 0:
                        self.metrics.record_reject()
                    else:
                        self.portfolio.apply_fill(fill)
                        self.metrics.record_fill(fill.slippage)
                        if self.on_event:
                            self.on_event({
                                "event": "fill",
                                "symbol": fill.order.symbol,
                                "side": fill.order.side.value,
                                "qty": fill.filled_qty,
                                "price": fill.avg_price,
                                "slippage": fill.slippage,
                                "confidence": confidence,
                            })

        latency_ms = (time.perf_counter_ns() - t0) / 1e6
        equity = self.portfolio.equity({tick.symbol: tick.last_price})
        self.metrics.record_tick(latency_ms, equity)

    def run(self, feed: MarketFeed, max_ticks: int | None = None) -> PipelineResult:
        count = 0
        for tick in feed.ticks():
            self.process_tick(tick)
            count += 1
            if max_ticks is not None and count >= max_ticks:
                break
        return PipelineResult(
            metrics=self.metrics.finalize(),
            portfolio=self.portfolio,
            effective_mode=self.effective_mode,
            safety_reason=self.safety.reason,
        )
