"""PPO 처리량/수렴 측정 하니스.

단일 프로세스 numpy PPO(`PPOAgent`/`ContinuousPPOAgent`)의 **처리량(steps/sec)** 과
**수렴(반복별 총보상 곡선)** 을 측정한다. 동일 지표 정의를 RLlib 분산 PPO 실측
(`scripts/bench_rllib_ppo.py`)에서도 그대로 사용하므로, 로컬에서 측정 방법론을 검증해 둔다.
"""
from __future__ import annotations

import time

from .env import TradingEnv


def benchmark_ppo(agent, env: TradingEnv, *, iterations: int = 40,
                  steps_per_iter: int | None = None, seed: int | None = 0) -> dict:
    """PPO/cPPO 에이전트의 처리량·수렴을 측정.

    agent 는 `collect(env, steps, seed=)` 와 `update(batch)` 를 제공해야 한다(PPOAgent/ContinuousPPOAgent).
    """
    steps = steps_per_iter or min(2048, max(256, len(env) - 1))
    reward_curve: list[float] = []
    total_steps = 0
    t0 = time.perf_counter()
    for _ in range(iterations):
        batch = agent.collect(env, steps, seed=seed)
        agent.update(batch)
        reward_curve.append(float(batch[2].sum()))
        total_steps += steps
    wall = time.perf_counter() - t0

    tail = reward_curve[-5:] if reward_curve else [0.0]
    return {
        "backend": "numpy-ppo",
        "iterations": iterations,
        "steps_per_iter": steps,
        "total_steps": total_steps,
        "wall_sec": round(wall, 4),
        "steps_per_sec": round(total_steps / wall, 1) if wall > 0 else 0.0,
        "reward_curve": [round(r, 4) for r in reward_curve],
        "final_mean": round(sum(tail) / len(tail), 4),
        "improved": bool(reward_curve and reward_curve[-1] >= reward_curve[0]),
    }
