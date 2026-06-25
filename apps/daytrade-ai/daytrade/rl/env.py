"""TradingEnv — 단타 강화학습용 순수 파이썬 환경(Gym/Gymnasium 호환 API).

설계 의도:
  - **train/serve skew 제거**: 관측(observation)을 운영과 동일한 `FeatureEngine` 으로 만든다.
  - **스케일 불변 보상**: 가격 차가 아닌 **수익률(return)** 기반 보상을 써 종목/가격대에 무관하게 학습 가능.
  - **현실적 비용**: 포지션 전환 시 `cost_bps`(수수료+슬리피지) 를 보상에서 차감(잦은 뒤집기 억제 → 스캘핑 현실 반영).
  - **의존성 0**: gymnasium 미설치 환경에서도 동작(경량 Space 폴백). 설치 시 `gymnasium.Env` 와 동일 시그니처.

행동(이산):
    0 → 숏(-1), 1 → 플랫(0), 2 → 롱(+1)   (목표 포지션)
보상(스텝 t):
    reward_t = position_t * ret_{t→t+1} - |Δposition| * cost_bps/1e4
    ret_{t→t+1} = mid_{t+1}/mid_t - 1
관측:
    [표준화된 8개 피처(FEATURE_NAMES 순서), 현재 포지션] → shape (9,)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np  # pyright: ignore[reportMissingImports]

from ..features.engine import FEATURE_NAMES, FeatureEngine
from ..types import MarketTick

# 행동 인덱스 → 목표 포지션
ACTION_TO_POSITION: tuple[int, ...] = (-1, 0, 1)
OBS_DIM = len(FEATURE_NAMES) + 1  # 피처 + 포지션


@dataclass(frozen=True, slots=True)
class RLConfig:
    depth: int = 10
    vwap_window: int = 50
    obi_stat_window: int = 200
    momentum_window: int = 1
    cost_bps: float = 1.0          # 포지션 1단위 전환당 비용(bps). 수수료+슬리피지 합산 근사.
    reward_scale: float = 1.0      # 보상 스케일(학습 안정화용). 수익률이 작아 기본 1.0(또는 1e4 권장).
    standardize: bool = True       # 피처 z-표준화(틱셋 통계로 fit). 선형 정책 안정화에 필수적.
    # 행동 모드: "discrete"(숏/플랫/롱) | "continuous"(목표 포지션 사이즈 ∈ [-1,1]).
    action_mode: str = "discrete"


class Discrete:
    """gymnasium.spaces.Discrete 경량 폴백."""

    def __init__(self, n: int) -> None:
        self.n = int(n)

    def sample(self, rng: "np.random.Generator") -> int:
        return int(rng.integers(0, self.n))


class Box:
    """gymnasium.spaces.Box 경량 폴백(shape 만 사용)."""

    def __init__(self, low: float, high: float, shape: tuple[int, ...]) -> None:
        self.low = float(low)
        self.high = float(high)
        self.shape = tuple(shape)

    def sample(self, rng: "np.random.Generator") -> "np.ndarray":
        return rng.uniform(self.low, self.high, size=self.shape).astype(np.float32)


class TradingEnv:
    """틱 시퀀스를 1 에피소드로 재생하는 단타 트레이딩 환경.

    Args:
        ticks: `MarketTick` 시퀀스(에피소드 데이터). 결정성을 위해 list 로 보관.
        config: RLConfig.
    """

    metadata = {"render_modes": []}

    def __init__(self, ticks: Sequence[MarketTick] | Iterable[MarketTick], config: RLConfig | None = None) -> None:
        self.cfg = config or RLConfig()
        self._ticks: list[MarketTick] = list(ticks)
        if len(self._ticks) < 3:
            raise ValueError("TradingEnv 에는 최소 3틱 이상이 필요합니다.")

        # 피처 행렬을 한 번 계산: (1) mid 가격열, (2) 표준화 통계 fit.
        self._feature_matrix, self._mids = self._precompute()
        self._mean, self._std = self._fit_scaler(self._feature_matrix)

        self.action_space, self.observation_space = self._make_spaces()

        # 에피소드 상태
        self._t = 0
        self._position = 0
        self._rng = np.random.default_rng()

    # ---- 셋업 ----
    def _precompute(self) -> tuple["np.ndarray", "np.ndarray"]:
        eng = FeatureEngine(
            depth=self.cfg.depth,
            vwap_window=self.cfg.vwap_window,
            obi_stat_window=self.cfg.obi_stat_window,
            momentum_window=self.cfg.momentum_window,
        )
        feats: list[list[float]] = []
        mids: list[float] = []
        for tick in self._ticks:
            fv = eng.update(tick)
            feats.append(fv.as_array())
            mid = tick.mid_price if tick.mid_price is not None else float(tick.last_price)
            mids.append(float(mid))
        return np.asarray(feats, dtype=np.float64), np.asarray(mids, dtype=np.float64)

    @staticmethod
    def _fit_scaler(matrix: "np.ndarray") -> tuple["np.ndarray", "np.ndarray"]:
        mean = matrix.mean(axis=0)
        std = matrix.std(axis=0)
        std = np.where(std < 1e-12, 1.0, std)  # 상수 피처 보호
        return mean, std

    def _make_spaces(self):
        continuous = self.cfg.action_mode == "continuous"
        try:  # gymnasium 있으면 표준 Space 사용(외부 RL 라이브러리 호환)
            from gymnasium import spaces  # type: ignore

            obs = spaces.Box(low=-np.inf, high=np.inf, shape=(OBS_DIM,), dtype=np.float32)
            if continuous:
                act = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
            else:
                act = spaces.Discrete(len(ACTION_TO_POSITION))
            return act, obs
        except Exception:
            if continuous:
                return Box(-1.0, 1.0, (1,)), Box(-np.inf, np.inf, (OBS_DIM,))
            return Discrete(len(ACTION_TO_POSITION)), Box(-np.inf, np.inf, (OBS_DIM,))

    # ---- 관측 ----
    def _obs(self, t: int) -> "np.ndarray":
        row = self._feature_matrix[t]
        if self.cfg.standardize:
            row = (row - self._mean) / self._std
        return np.concatenate([row, [float(self._position)]]).astype(np.float32)

    # ---- Gym API ----
    def reset(self, *, seed: int | None = None, options: dict | None = None):
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._t = 0
        self._position = 0
        return self._obs(self._t), {}

    def step(self, action):
        if self.cfg.action_mode == "continuous":
            # 스칼라 또는 shape (1,) 배열을 허용. [-1,1] 로 클립한 목표 포지션.
            a = float(np.asarray(action).reshape(-1)[0])
            target = max(-1.0, min(1.0, a))
        else:
            if not (0 <= int(action) < len(ACTION_TO_POSITION)):
                raise ValueError(f"잘못된 action: {action}")
            target = ACTION_TO_POSITION[int(action)]
        delta = abs(target - self._position)
        cost = delta * (self.cfg.cost_bps / 10_000.0)

        # t → t+1 수익률로 보상 산출
        ret = (self._mids[self._t + 1] / self._mids[self._t]) - 1.0 if self._mids[self._t] > 0 else 0.0
        reward = (target * ret - cost) * self.cfg.reward_scale

        self._position = target
        self._t += 1
        terminated = self._t >= (len(self._ticks) - 1)  # 마지막 틱엔 t+1 없음
        truncated = False
        info = {"position": self._position, "ret": ret, "cost": cost, "t": self._t}
        return self._obs(self._t), float(reward), bool(terminated), bool(truncated), info

    def __len__(self) -> int:
        return len(self._ticks)
