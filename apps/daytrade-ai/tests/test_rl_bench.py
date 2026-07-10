"""PPO 처리량/수렴 측정 하니스 테스트(서버 RLlib 실측과 동일 지표 정의)."""
from __future__ import annotations

from daytrade.feed.simulated import SimulatedFeed
from daytrade.rl import ContinuousPPOAgent, PPOAgent, RLConfig, TradingEnv, benchmark_ppo


def _ticks(n=400, seed=3):
    return list(SimulatedFeed(symbol="BENCH", n_ticks=n, seed=seed).ticks())


def test_benchmark_ppo_discrete_metrics():
    env = TradingEnv(_ticks(), RLConfig(cost_bps=0.5, reward_scale=1e4))
    res = benchmark_ppo(PPOAgent(seed=0), env, iterations=5, steps_per_iter=200, seed=1)
    assert res["iterations"] == 5
    assert res["steps_per_iter"] == 200
    assert res["total_steps"] == 1000
    assert res["wall_sec"] > 0
    assert res["steps_per_sec"] > 0
    assert len(res["reward_curve"]) == 5
    assert "final_mean" in res and "improved" in res


def test_benchmark_ppo_continuous_runs():
    env = TradingEnv(_ticks(), RLConfig(cost_bps=0.5, reward_scale=1e4, action_mode="continuous"))
    res = benchmark_ppo(ContinuousPPOAgent(seed=0), env, iterations=4, steps_per_iter=150, seed=1)
    assert res["total_steps"] == 600
    assert len(res["reward_curve"]) == 4
    assert res["steps_per_sec"] > 0


def test_benchmark_determinism():
    env1 = TradingEnv(_ticks(), RLConfig(action_mode="discrete"))
    env2 = TradingEnv(_ticks(), RLConfig(action_mode="discrete"))
    r1 = benchmark_ppo(PPOAgent(seed=5), env1, iterations=4, steps_per_iter=150, seed=2)
    r2 = benchmark_ppo(PPOAgent(seed=5), env2, iterations=4, steps_per_iter=150, seed=2)
    assert r1["reward_curve"] == r2["reward_curve"]
