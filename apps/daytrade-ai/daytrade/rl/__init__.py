"""RL 패키지 — 단타 강화학습 환경 및 베이스라인 에이전트.

- `TradingEnv`: Gym/Gymnasium 호환 순수 파이썬 환경(운영 `FeatureEngine` 재사용).
- `LinearPolicyAgent`: 순수 numpy REINFORCE 베이스라인(Ray RLlib 교체 전 검증용).
"""
from .agent import LinearPolicyAgent, run_episode, train
from .bench import benchmark_ppo
from .env import ACTION_TO_POSITION, OBS_DIM, Box, Discrete, RLConfig, TradingEnv
from .gym_env import make_gym_trading_env
from .ppo import ContinuousPPOAgent, PPOAgent, train_ppo, train_ppo_continuous
from .rllib_train import train_ppo_rllib

__all__ = [
    "TradingEnv",
    "RLConfig",
    "Discrete",
    "Box",
    "ACTION_TO_POSITION",
    "OBS_DIM",
    "LinearPolicyAgent",
    "run_episode",
    "train",
    "PPOAgent",
    "train_ppo",
    "ContinuousPPOAgent",
    "train_ppo_continuous",
    "make_gym_trading_env",
    "train_ppo_rllib",
    "benchmark_ppo",
]
