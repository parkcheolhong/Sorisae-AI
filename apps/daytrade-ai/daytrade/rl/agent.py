"""LinearPolicyAgent — 순수 numpy REINFORCE(정책경사) 에이전트.

외부 RL 프레임워크(Ray RLlib 등) 없이도 `TradingEnv` 가 학습 가능함을 보이는 경량 베이스라인.
softmax 선형 정책 π(a|s) = softmax(W·s + b) 를 REINFORCE(baseline=리턴 평균) 로 갱신한다.
결정성: seed 고정 시 동일 결과. 추후 PPO/RLlib 로 교체해도 환경 인터페이스는 동일.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np  # pyright: ignore[reportMissingImports]

from .env import OBS_DIM, TradingEnv


def _softmax(z: "np.ndarray") -> "np.ndarray":
    z = z - np.max(z)
    e = np.exp(z)
    return e / np.sum(e)


@dataclass
class LinearPolicyAgent:
    n_actions: int = 3
    obs_dim: int = OBS_DIM
    lr: float = 0.05
    gamma: float = 0.99
    seed: int | None = 0

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        # 작은 난수 초기화(0 초기화는 대칭성으로 학습 정체).
        self.W = self._rng.normal(0.0, 0.01, size=(self.n_actions, self.obs_dim))
        self.b = np.zeros(self.n_actions)

    def probs(self, obs: "np.ndarray") -> "np.ndarray":
        return _softmax(self.W @ np.asarray(obs, dtype=np.float64) + self.b)

    def act(self, obs: "np.ndarray", *, greedy: bool = False) -> int:
        p = self.probs(obs)
        if greedy:
            return int(np.argmax(p))
        return int(self._rng.choice(self.n_actions, p=p))

    def _discounted_returns(self, rewards: list[float]) -> "np.ndarray":
        g = 0.0
        out = np.zeros(len(rewards))
        for i in reversed(range(len(rewards))):
            g = rewards[i] + self.gamma * g
            out[i] = g
        return out

    def update(self, obss: list["np.ndarray"], actions: list[int], rewards: list[float]) -> float:
        """한 에피소드의 (obs, action, reward) 로 REINFORCE 갱신. 반환: 에피소드 총보상."""
        returns = self._discounted_returns(rewards)
        baseline = float(np.mean(returns)) if len(returns) else 0.0
        adv = returns - baseline
        # 표준화로 스텝수/스케일에 둔감하게.
        std = float(np.std(adv))
        if std > 1e-8:
            adv = adv / std

        gradW = np.zeros_like(self.W)
        gradb = np.zeros_like(self.b)
        for obs, a, A in zip(obss, actions, adv):
            obs = np.asarray(obs, dtype=np.float64)
            p = self.probs(obs)
            onehot = np.zeros(self.n_actions)
            onehot[a] = 1.0
            dlogits = onehot - p  # ∂logπ/∂logits
            gradW += A * np.outer(dlogits, obs)
            gradb += A * dlogits
        self.W += self.lr * gradW
        self.b += self.lr * gradb
        return float(np.sum(rewards))


def run_episode(env: TradingEnv, agent: LinearPolicyAgent, *, greedy: bool = False, seed: int | None = None):
    """에이전트로 1 에피소드 실행 → (obss, actions, rewards, total_reward)."""
    obs, _ = env.reset(seed=seed)
    obss: list = []
    actions: list[int] = []
    rewards: list[float] = []
    terminated = truncated = False
    while not (terminated or truncated):
        a = agent.act(obs, greedy=greedy)
        obss.append(obs)
        actions.append(a)
        obs, r, terminated, truncated, _ = env.step(a)
        rewards.append(r)
    return obss, actions, rewards, float(sum(rewards))


def train(env: TradingEnv, agent: LinearPolicyAgent, *, episodes: int = 200, seed: int | None = 0) -> list[float]:
    """REINFORCE 학습 루프. 에피소드별 총보상 리스트 반환(학습곡선)."""
    history: list[float] = []
    for _ in range(episodes):
        obss, actions, rewards, _ = run_episode(env, agent, greedy=False, seed=seed)
        total = agent.update(obss, actions, rewards)
        history.append(total)
    return history
