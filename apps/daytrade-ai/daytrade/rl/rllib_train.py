"""Ray-RLlib PPO 브리지 — 동일 `TradingEnv` 를 RLlib 분산 PPO 로 학습.

설계서 §2 의 Ray-RLlib 경로. ray[rllib] 설치 환경에서만 동작하며, 미설치 시 명확한
ImportError 로 안내한다(개발 PC 기본값은 순수 numpy `PPOAgent` — `rl/ppo.py`).
RLlib 로 학습한 정책은 ONNX export → M4 추론 엔진으로 이어진다.
"""
from __future__ import annotations

from typing import Sequence

from ..types import MarketTick
from .env import RLConfig
from .gym_env import make_gym_trading_env


def train_ppo_rllib(
    ticks: Sequence[MarketTick],
    config: RLConfig | None = None,
    *,
    iterations: int = 20,
    num_env_runners: int = 1,
    train_batch_size: int = 4000,
):
    """RLlib PPO 로 `TradingEnv` 학습. ray[rllib] 필요. 반환: 학습된 Algorithm.

    Raises:
        ImportError: ray[rllib] 미설치.
    """
    try:
        import ray  # type: ignore
        from ray.rllib.algorithms.ppo import PPOConfig  # type: ignore
        from ray.tune.registry import register_env  # type: ignore
    except ImportError as e:  # pragma: no cover - 설치 환경에서만 분기
        raise ImportError(
            "RLlib PPO 학습에는 ray[rllib] 가 필요합니다: pip install 'ray[rllib]'\n"
            "  (의존성 없이 학습하려면 daytrade.rl.PPOAgent + train_ppo 를 사용하세요)"
        ) from e

    env_name = "daytrade_trading_env"
    register_env(env_name, lambda env_config: make_gym_trading_env(ticks, config))

    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True, include_dashboard=False)

    builder = (
        PPOConfig()
        .environment(env_name)
        .env_runners(num_env_runners=num_env_runners)
        .training(train_batch_size=train_batch_size)
    )
    # ray>=2.4x: build() → build_algo() 로 이름 변경(구버전 호환 폴백).
    algo = builder.build_algo() if hasattr(builder, "build_algo") else builder.build()
    for _ in range(iterations):
        algo.train()
    return algo
