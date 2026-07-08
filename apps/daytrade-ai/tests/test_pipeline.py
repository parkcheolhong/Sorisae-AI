import pytest

from daytrade.config import (
    LIVE_ENV_KEY,
    LIVE_ENV_TOKEN,
    RiskConfig,
    SignalConfig,
    TradingConfig,
    TradingMode,
)
from daytrade.execution.paper import PaperExecutor
from daytrade.feed.simulated import SimulatedFeed
from daytrade.pipeline import TradingPipeline
from daytrade.types import Fill, MarketTick, Order


def test_pipeline_runs_and_produces_metrics():
    cfg = TradingConfig.backtest(
        symbols=("AAPL",),
        signal=SignalConfig(obi_threshold=1.0e5, volume_spike_ratio=1.5),
        seed=42,
    )
    feed = SimulatedFeed(symbol="AAPL", n_ticks=2000, seed=42, event_prob=0.05)
    result = TradingPipeline(cfg).run(feed)
    assert result.metrics.ticks == 2000
    assert result.effective_mode == TradingMode.BACKTEST
    # 이벤트가 충분하면 시그널/주문이 발생해야 한다.
    assert result.metrics.signals > 0
    assert result.metrics.orders_submitted > 0


def test_pipeline_deterministic_with_seed():
    # 레이턴시 서킷브레이커는 벽시계 기반(비결정적)이라 시스템 부하에 따라 한 런만 halt 되어
    # 매매가 갈릴 수 있다. 결정성 검증에서는 임계값을 무한대로 둬 wall-clock 의존을 제거한다.
    cfg = TradingConfig.backtest(
        signal=SignalConfig(obi_threshold=1e5, volume_spike_ratio=1.5),
        risk=RiskConfig(max_latency_ms=float("inf")),
        seed=42,
    )
    feed1 = SimulatedFeed(n_ticks=1000, seed=123, event_prob=0.05)
    feed2 = SimulatedFeed(n_ticks=1000, seed=123, event_prob=0.05)
    r1 = TradingPipeline(cfg).run(feed1)
    r2 = TradingPipeline(cfg).run(feed2)
    # 레이턴시(벽시계 기반)는 본질적으로 비결정적이므로 매매 결과 필드만 비교한다.
    def trading_fields(d):
        return {k: v for k, v in d.items() if not k.startswith("latency_ms")}
    assert trading_fields(r1.metrics.as_dict()) == trading_fields(r2.metrics.as_dict())


def test_no_ai_mode_still_trades():
    cfg = TradingConfig.backtest(signal=SignalConfig(obi_threshold=1e5, volume_spike_ratio=1.5, use_ai=False), seed=42)
    feed = SimulatedFeed(n_ticks=1500, seed=7, event_prob=0.05)
    result = TradingPipeline(cfg).run(feed)
    assert result.metrics.ticks == 1500


class _FakeLiveExecutor(PaperExecutor):
    @property
    def is_live(self):
        return True


def test_paper_mode_ignores_live_executor():
    cfg = TradingConfig.paper()
    pipe = TradingPipeline(cfg, executor=_FakeLiveExecutor())
    # paper 모드 → 내부적으로 PaperExecutor 로 강제(전달한 live 실행기 무시)
    assert pipe.executor.is_live is False


def test_live_mode_requires_live_executor():
    cfg = TradingConfig(mode=TradingMode.LIVE)
    env = {LIVE_ENV_KEY: LIVE_ENV_TOKEN}
    with pytest.raises(RuntimeError):
        TradingPipeline(cfg, executor=None, env=env)


def test_live_without_token_falls_back_to_paper():
    cfg = TradingConfig(mode=TradingMode.LIVE)
    # 토큰 없음 → paper 강등 → live 실행기 없어도 생성 성공
    pipe = TradingPipeline(cfg, env={})
    assert pipe.effective_mode == TradingMode.PAPER
    assert pipe.executor.is_live is False


def test_pipeline_applies_signal_momentum_window_ms():
    cfg = TradingConfig.backtest(signal=SignalConfig(momentum_window_ms=30.0))
    pipe = TradingPipeline(cfg)

    assert pipe.features.momentum_window == 3

    pipe.apply_signal_config(SignalConfig(momentum_window_ms=40.0))

    assert pipe.features.momentum_window == 4
