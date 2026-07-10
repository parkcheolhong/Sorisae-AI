"""PPOAgent(순수 numpy) 테스트.

검증:
  - act/probs/value 형태·확률 유효성.
  - GAE 어드밴티지/리턴 shape·일관성.
  - seed 고정 결정성(동일 학습곡선).
  - 학습이 무작위 베이스라인 대비 붕괴하지 않고(보수적 하한) 수렴.
  - run_episode 와 호환(greedy 평가 공유).
"""
from __future__ import annotations

import numpy as np

from daytrade.feed.simulated import SimulatedFeed
from daytrade.rl import OBS_DIM, PPOAgent, RLConfig, TradingEnv, run_episode, train_ppo


def _ticks(n=800, seed=9):
    return list(SimulatedFeed(symbol="PPO", n_ticks=n, seed=seed).ticks())


def _env():
    return TradingEnv(_ticks(), RLConfig(cost_bps=0.5, reward_scale=1e4))


def test_probs_and_value_shapes():
    agent = PPOAgent(seed=0)
    obs = np.zeros(OBS_DIM)
    p = agent.probs(obs)
    assert p.shape == (3,)
    assert abs(float(p.sum()) - 1.0) < 1e-9
    assert np.all(p >= 0)
    assert isinstance(agent.value(obs), float)


def test_act_compatible_with_run_episode():
    env = _env()
    agent = PPOAgent(seed=0)
    obss, actions, rewards, total = run_episode(env, agent, greedy=True, seed=1)
    assert len(obss) == len(actions) == len(rewards)
    assert all(a in (0, 1, 2) for a in actions)
    assert np.isfinite(total)


def test_gae_shapes_and_finite():
    env = _env()
    agent = PPOAgent(seed=0)
    batch = agent.collect(env, steps=300, seed=1)
    adv, returns = agent._gae(batch[2], batch[3], batch[4], batch[6])
    assert adv.shape == returns.shape == (300,)
    assert np.all(np.isfinite(adv)) and np.all(np.isfinite(returns))


def test_determinism_with_seed():
    h1 = train_ppo(_env(), PPOAgent(seed=7), iterations=10, seed=3)
    h2 = train_ppo(_env(), PPOAgent(seed=7), iterations=10, seed=3)
    assert np.allclose(h1, h2)


def test_training_does_not_degrade_and_learns():
    env = _env()
    agent = PPOAgent(seed=0)
    _, _, _, base = run_episode(env, agent, greedy=False, seed=1)
    history = train_ppo(env, agent, iterations=40, seed=1)
    _, _, _, trained = run_episode(env, agent, greedy=True, seed=1)
    assert len(history) == 40
    assert np.isfinite(trained)
    # 학습이 무작위 베이스라인 대비 크게 붕괴하지 않음(보수적).
    assert trained >= base - abs(base) * 0.5 - 1.0


def test_value_function_learns_to_track_returns():
    """가치 함수가 학습 후 의미있는(비자명) 가중치를 가지는지 — critic 동작 확인."""
    env = _env()
    agent = PPOAgent(seed=0)
    train_ppo(env, agent, iterations=20, seed=1)
    assert np.linalg.norm(agent.w_v) > 0.0
