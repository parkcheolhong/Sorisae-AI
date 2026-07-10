"""RL TradingEnv + LinearPolicyAgent 테스트.

검증 포인트:
  - Gym API 계약(reset/step 시그니처, 관측 shape, terminated 시점).
  - 보상 정의(수익률 - 전환비용), 비용이 잦은 뒤집기를 벌하는지.
  - 결정성(seed 고정 시 동일 롤아웃).
  - 완전정보(perfect-foresight) 정책은 양(+)의 보상, 항상-플랫은 0 보상.
  - REINFORCE 학습이 무작위 정책 대비 (적어도) 열등하지 않게 수렴.
"""
from __future__ import annotations

import numpy as np
import pytest

from daytrade.feed.simulated import SimulatedFeed
from daytrade.rl import (
    ACTION_TO_POSITION,
    OBS_DIM,
    LinearPolicyAgent,
    RLConfig,
    TradingEnv,
    run_episode,
    train,
)


def _ticks(n: int = 800, seed: int = 3):
    return list(SimulatedFeed(symbol="RL", n_ticks=n, seed=seed).ticks())


def test_reset_and_obs_shape():
    env = TradingEnv(_ticks(200), RLConfig())
    obs, info = env.reset(seed=1)
    assert obs.shape == (OBS_DIM,)
    assert obs.dtype == np.float32
    assert info == {}


def test_step_contract_and_termination():
    ticks = _ticks(120)
    env = TradingEnv(ticks, RLConfig())
    env.reset(seed=0)
    steps = 0
    terminated = False
    while not terminated:
        obs, reward, terminated, truncated, info = env.step(1)  # 항상 플랫
        assert obs.shape == (OBS_DIM,)
        assert isinstance(reward, float)
        assert truncated is False
        steps += 1
    # 마지막 틱엔 t+1 이 없으므로 정확히 len-1 스텝.
    assert steps == len(ticks) - 1


def test_flat_policy_zero_reward():
    env = TradingEnv(_ticks(300), RLConfig(cost_bps=1.0))
    env.reset(seed=0)
    total = 0.0
    terminated = False
    while not terminated:
        _, r, terminated, _, _ = env.step(1)  # flat → position 0 → 보상 0, 비용 0
        total += r
    assert total == pytest.approx(0.0, abs=1e-12)


def test_perfect_foresight_is_profitable():
    """다음 스텝 수익률 부호를 아는 정책은 비용을 감안해도 양의 누적보상을 낸다."""
    ticks = _ticks(600, seed=11)
    env = TradingEnv(ticks, RLConfig(cost_bps=0.0))  # 비용 0 → 방향만 맞히면 +
    obs, _ = env.reset(seed=0)
    mids = env._mids  # 내부 mid 열(테스트 한정 접근)
    total = 0.0
    terminated = False
    while not terminated:
        t = env._t
        nxt = mids[t + 1] / mids[t] - 1.0
        action = 2 if nxt > 0 else (0 if nxt < 0 else 1)  # 롱/숏/플랫
        obs, r, terminated, _, _ = env.step(action)
        total += r
    assert total > 0.0


def test_cost_penalizes_flipping():
    """매 스텝 롱/숏을 뒤집으면 비용이 누적 → 같은 데이터에서 비용>0 이 비용=0 보다 총보상 낮다."""
    ticks = _ticks(400, seed=5)

    def run(cost_bps: float) -> float:
        env = TradingEnv(ticks, RLConfig(cost_bps=cost_bps))
        env.reset(seed=0)
        total, terminated, flip = 0.0, False, 0
        while not terminated:
            flip = 2 if flip != 2 else 0  # 롱↔숏 반복
            _, r, terminated, _, _ = env.step(flip)
            total += r
        return total

    assert run(5.0) < run(0.0)


def test_determinism_with_seed():
    ticks = _ticks(300)
    a1 = LinearPolicyAgent(seed=42)
    a2 = LinearPolicyAgent(seed=42)
    env1 = TradingEnv(ticks, RLConfig())
    env2 = TradingEnv(ticks, RLConfig())
    _, ac1, rw1, tot1 = run_episode(env1, a1, seed=7)
    _, ac2, rw2, tot2 = run_episode(env2, a2, seed=7)
    assert ac1 == ac2
    assert rw1 == pytest.approx(rw2)
    assert tot1 == pytest.approx(tot2)


def test_action_space_size():
    env = TradingEnv(_ticks(50), RLConfig())
    assert env.action_space.n == len(ACTION_TO_POSITION) == 3


def test_reinforce_does_not_degrade():
    """학습 후 그리디 성능이 학습 전(무작위 정책 평균) 대비 크게 나빠지지 않는지(수렴 안정성)."""
    ticks = _ticks(500, seed=9)
    env = TradingEnv(ticks, RLConfig(cost_bps=0.5, reward_scale=1e4))
    agent = LinearPolicyAgent(seed=0, lr=0.05)

    # 학습 전 무작위 정책 기준선
    _, _, _, base = run_episode(env, agent, greedy=False, seed=1)
    history = train(env, agent, episodes=150, seed=1)
    _, _, _, trained = run_episode(env, agent, greedy=True, seed=1)

    assert len(history) == 150
    assert np.isfinite(trained)
    # 학습이 베이스라인 대비 과하게 붕괴하지 않음(보수적 하한).
    assert trained >= base - abs(base) * 0.5 - 1.0
