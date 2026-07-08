"""연속행동 RL 정책(ONNX) → OnnxPolicyModel → 실제 파이프라인 백테스트 결선 테스트.

onnx/onnxruntime 미설치 시 graceful skip.
"""
from __future__ import annotations

import pytest

pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")


def _ticks(n=400, seed=0):
    from daytrade.feed.simulated import SimulatedFeed

    return list(SimulatedFeed(symbol="AAPL", n_ticks=n, seed=seed).ticks())


def _train_and_export(tmp_path, ticks):
    from daytrade.rl import ContinuousPPOAgent, RLConfig, TradingEnv, train_ppo_continuous
    from daytrade.training.onnx_export import export_continuous_policy_to_onnx

    env = TradingEnv(ticks, RLConfig(action_mode="continuous", reward_scale=1e4))
    agent = ContinuousPPOAgent(seed=0)
    train_ppo_continuous(env, agent, iterations=3, seed=0)
    path = str(tmp_path / "policy.onnx")
    export_continuous_policy_to_onnx(agent.W, agent.b, env._mean, env._std, path)
    return path


def test_load_model_dispatches_policy_onnx(tmp_path):
    """출력 차원 1 의 정책 ONNX 는 OnnxPolicyModel 로 로드되어야 한다."""
    from daytrade.inference.model import OnnxPolicyModel, load_model

    ticks = _ticks()
    path = _train_and_export(tmp_path, ticks)
    model = load_model(path)
    assert isinstance(model, OnnxPolicyModel)


def test_policy_model_runs_in_pipeline_backtest(tmp_path):
    """OnnxPolicyModel 을 실제 run_backtest 에 물려 정상 동작(틱/장비/모드)."""
    from daytrade.backtest.runner import run_backtest
    from daytrade.config import RiskConfig, SignalConfig, TradingConfig, TradingMode
    from daytrade.feed.memory import ListFeed
    from daytrade.inference.model import OnnxPolicyModel

    ticks = _ticks()
    path = _train_and_export(tmp_path, ticks)

    config = TradingConfig(
        mode=TradingMode.BACKTEST,
        symbols=("AAPL",),
        starting_cash=1_000_000.0,
        signal=SignalConfig(depth=10, ai_buy_threshold=0.3, ai_sell_threshold=0.3, use_ai=True),
        risk=RiskConfig(max_latency_ms=float("inf")),
        seed=0,
    )
    report = run_backtest(config, ListFeed(ticks), model=OnnxPolicyModel(path))
    assert report.metrics.ticks == len(ticks)
    assert report.effective_mode == "backtest"
    # 백테스트가 서킷브레이커로 중단되지 않고 끝까지 진행되어야 한다.
    assert not report.metrics.halted


def test_policy_probs_bounded(tmp_path):
    """OnnxPolicyModel.predict 출력이 (prob_buy, prob_sell) ∈ [0,1] 이고 한쪽은 0."""
    from daytrade.features.engine import FeatureEngine
    from daytrade.inference.model import OnnxPolicyModel

    ticks = _ticks()
    path = _train_and_export(tmp_path, ticks)
    model = OnnxPolicyModel(path)
    eng = FeatureEngine(depth=10)
    for tick in ticks[:50]:
        fv = eng.update(tick)
        pb, ps = model.predict(fv)
        assert 0.0 <= pb <= 1.0 and 0.0 <= ps <= 1.0
        assert pb <= 1e-9 or ps <= 1e-9  # target 부호상 한쪽은 항상 0
