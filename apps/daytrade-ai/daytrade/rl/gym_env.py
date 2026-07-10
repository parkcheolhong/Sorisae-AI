"""Gymnasium 어댑터 — `TradingEnv` 를 표준 `gymnasium.Env` 로 감싼다(RLlib/SB3 호환).

순수 파이썬 `TradingEnv` 는 gymnasium 없이도 동작하지만, 외부 RL 프레임워크(Ray-RLlib,
Stable-Baselines3)는 `gymnasium.Env` 서브클래스를 요구한다. 본 모듈은 gymnasium 이
설치된 경우에만 동작하는 얇은 어댑터를 제공한다(미설치 시 명확한 ImportError).
"""
from __future__ import annotations

from typing import Iterable, Sequence

from ..types import MarketTick
from .env import ACTION_TO_POSITION, OBS_DIM, RLConfig, TradingEnv


def make_gym_trading_env(
    ticks: Sequence[MarketTick] | Iterable[MarketTick], config: RLConfig | None = None
):
    """`gymnasium.Env` 인스턴스를 반환. gymnasium 미설치 시 ImportError."""
    try:
        import gymnasium as gym  # type: ignore
        import numpy as np  # pyright: ignore[reportMissingImports]
        from gymnasium import spaces  # type: ignore
    except ImportError as e:  # pragma: no cover - 설치 환경에서만 경로 분기
        raise ImportError(
            "gymnasium 이 필요합니다(RLlib/SB3 호환): pip install gymnasium"
        ) from e

    class GymTradingEnv(gym.Env):
        metadata = {"render_modes": []}

        def __init__(self) -> None:
            super().__init__()
            self._inner = TradingEnv(ticks, config)
            self.action_space = spaces.Discrete(len(ACTION_TO_POSITION))
            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(OBS_DIM,), dtype=np.float32
            )

        def reset(self, *, seed=None, options=None):
            super().reset(seed=seed)
            return self._inner.reset(seed=seed, options=options)

        def step(self, action):
            return self._inner.step(int(action))

    return GymTradingEnv()
