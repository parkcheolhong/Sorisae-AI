"""Gymnasium 어댑터 + RLlib 브리지 테스트.

gymnasium/ray 는 선택 의존성이므로 미설치 시 자동 skip. 설치 시 표준 Env 계약을 검증한다.
"""
from __future__ import annotations

import pytest

from daytrade.feed.simulated import SimulatedFeed
from daytrade.rl import OBS_DIM, RLConfig
from daytrade.rl.gym_env import make_gym_trading_env


def _ticks(n=300, seed=2):
    return list(SimulatedFeed(symbol="GYM", n_ticks=n, seed=seed).ticks())


def test_gym_import_error_message_without_gymnasium():
    """gymnasium 미설치면 ImportError(설치 안내) — 설치돼 있으면 정상 생성."""
    import importlib.util

    if importlib.util.find_spec("gymnasium") is None:
        with pytest.raises(ImportError, match="gymnasium"):
            make_gym_trading_env(_ticks(), RLConfig())
    else:  # pragma: no cover - 설치 환경에서만
        env = make_gym_trading_env(_ticks(), RLConfig())
        assert env is not None


@pytest.mark.skipif(
    __import__("importlib.util", fromlist=["util"]).find_spec("gymnasium") is None,
    reason="gymnasium 미설치",
)
def test_gym_env_contract():  # pragma: no cover - 설치 환경에서만 실행
    env = make_gym_trading_env(_ticks(), RLConfig())
    assert env.action_space.n == 3
    assert env.observation_space.shape == (OBS_DIM,)
    obs, info = env.reset(seed=0)
    assert obs.shape == (OBS_DIM,)
    obs, reward, terminated, truncated, info = env.step(1)
    assert obs.shape == (OBS_DIM,)
    assert isinstance(float(reward), float)
    assert isinstance(terminated, bool)


def test_rllib_bridge_importable_and_guarded():
    """RLlib 브리지는 import 가능해야 하며, ray 미설치 시 명확한 ImportError 를 낸다."""
    import importlib.util

    from daytrade.rl import train_ppo_rllib

    assert callable(train_ppo_rllib)
    if importlib.util.find_spec("ray") is None:
        with pytest.raises(ImportError, match="ray"):
            train_ppo_rllib(_ticks(), RLConfig(), iterations=1)
