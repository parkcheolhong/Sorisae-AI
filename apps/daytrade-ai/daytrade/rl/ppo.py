"""PPOAgent — 순수 numpy PPO(Proximal Policy Optimization).

REINFORCE 베이스라인을 대체하는 정식 PPO 구현(의존성 0). Ray-RLlib 미설치 환경에서도
동작하며, 동일 `TradingEnv` 인터페이스를 쓴다(RLlib 설치 시 `rl/rllib_train.py` 로 교체 가능).

구성:
  - 선형 정책 π(a|s)=softmax(W·s+b), 선형 가치 V(s)=w·s+c (actor-critic).
  - GAE(λ) 어드밴티지, 클리핑된 surrogate 목적함수(ratio clip ε), 가치손실, 엔트로피 보너스.
  - 미니배치 K-epoch 갱신. seed 고정 시 결정적.
`act(obs, greedy=)` 시그니처가 REINFORCE 와 동일 → `run_episode` 로 평가 공유.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np  # pyright: ignore[reportMissingImports]

from .env import OBS_DIM, TradingEnv


def _softmax(z: "np.ndarray") -> "np.ndarray":
    z = z - np.max(z)
    e = np.exp(z)
    return e / np.sum(e)


def compute_gae(rews, vals, dones, last_v, gamma: float, lam: float):
    """GAE(λ) 어드밴티지 + 리턴. discrete/continuous 공용."""
    n = len(rews)
    adv = np.zeros(n)
    gae = 0.0
    for t in reversed(range(n)):
        next_v = last_v if t == n - 1 else vals[t + 1]
        nonterminal = 0.0 if dones[t] else 1.0
        delta = rews[t] + gamma * next_v * nonterminal - vals[t]
        gae = delta + gamma * lam * nonterminal * gae
        adv[t] = gae
    return adv, adv + vals


@dataclass
class PPOAgent:
    n_actions: int = 3
    obs_dim: int = OBS_DIM
    lr_pi: float = 0.02
    lr_v: float = 0.05
    gamma: float = 0.99
    lam: float = 0.95          # GAE λ
    clip: float = 0.2          # PPO ratio clip ε
    entropy_coef: float = 0.01
    epochs: int = 6            # 배치당 갱신 epoch
    minibatch: int = 256
    seed: int | None = 0

    W: "np.ndarray" = field(init=False)
    b: "np.ndarray" = field(init=False)
    w_v: "np.ndarray" = field(init=False)
    c_v: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self.W = self._rng.normal(0.0, 0.01, size=(self.n_actions, self.obs_dim))
        self.b = np.zeros(self.n_actions)
        self.w_v = np.zeros(self.obs_dim)
        self.c_v = 0.0

    # ---- 정책/가치 ----
    def probs(self, obs: "np.ndarray") -> "np.ndarray":
        return _softmax(self.W @ np.asarray(obs, dtype=np.float64) + self.b)

    def value(self, obs: "np.ndarray") -> float:
        return float(self.w_v @ np.asarray(obs, dtype=np.float64) + self.c_v)

    def act(self, obs: "np.ndarray", *, greedy: bool = False) -> int:
        p = self.probs(obs)
        if greedy:
            return int(np.argmax(p))
        return int(self._rng.choice(self.n_actions, p=p))

    # ---- 롤아웃 수집 ----
    def collect(self, env: TradingEnv, steps: int, *, seed: int | None = None):
        obss, acts, rews, vals, dones, logps = [], [], [], [], [], []
        obs, _ = env.reset(seed=seed)
        for _ in range(steps):
            p = self.probs(obs)
            a = int(self._rng.choice(self.n_actions, p=p))
            v = self.value(obs)
            obss.append(np.asarray(obs, dtype=np.float64))
            acts.append(a)
            vals.append(v)
            logps.append(float(np.log(p[a] + 1e-12)))
            obs, r, terminated, truncated, _ = env.step(a)
            rews.append(r)
            done = terminated or truncated
            dones.append(done)
            if done:
                obs, _ = env.reset(seed=seed)
        last_v = self.value(obs)
        return (
            np.array(obss), np.array(acts), np.array(rews, dtype=np.float64),
            np.array(vals, dtype=np.float64), np.array(dones, dtype=bool),
            np.array(logps, dtype=np.float64), last_v,
        )

    def _gae(self, rews, vals, dones, last_v):
        return compute_gae(rews, vals, dones, last_v, self.gamma, self.lam)

    # ---- 갱신 ----
    def update(self, batch) -> dict:
        obss, acts, rews, vals, dones, logps_old, last_v = batch
        adv, returns = self._gae(rews, vals, dones, last_v)
        adv_std = adv.std()
        adv_n = (adv - adv.mean()) / (adv_std + 1e-8)

        n = len(obss)
        idx_all = np.arange(n)
        for _ in range(self.epochs):
            self._rng.shuffle(idx_all)
            for start in range(0, n, self.minibatch):
                mb = idx_all[start:start + self.minibatch]
                self._update_minibatch(obss[mb], acts[mb], logps_old[mb], adv_n[mb], returns[mb])
        return {"adv_std": float(adv_std), "mean_return": float(returns.mean())}

    def _update_minibatch(self, obss, acts, logps_old, adv, returns):
        gW = np.zeros_like(self.W)
        gb = np.zeros_like(self.b)
        gwv = np.zeros_like(self.w_v)
        gcv = 0.0
        m = len(obss)
        for i in range(m):
            o = obss[i]
            p = _softmax(self.W @ o + self.b)
            a = int(acts[i])
            logp = np.log(p[a] + 1e-12)
            ratio = np.exp(logp - logps_old[i])
            A = adv[i]

            # 클리핑된 surrogate 의 정책경사: 활성 분기만 기여.
            unclipped = ratio * A
            clipped = np.clip(ratio, 1 - self.clip, 1 + self.clip) * A
            onehot = np.zeros(self.n_actions)
            onehot[a] = 1.0
            dlogits_pi = np.zeros(self.n_actions)
            if unclipped <= clipped:  # min 이 unclipped 선택 → 경사 통과
                dlogits_pi = A * ratio * (onehot - p)
            # 엔트로피 보너스 경사: dH/dlogits = -p*(logp+1) + p*sum(p*(logp+1))
            logp_all = np.log(p + 1e-12)
            t = p * (logp_all + 1.0)
            dent = -t + p * np.sum(t)
            dlogits = dlogits_pi + self.entropy_coef * dent

            gW += np.outer(dlogits, o)
            gb += dlogits

            # 가치 회귀(MSE) 경사하강
            v = self.w_v @ o + self.c_v
            verr = v - returns[i]
            gwv += verr * o
            gcv += verr

        inv = 1.0 / max(m, 1)
        # 정책은 목적함수 최대화(상승), 가치는 손실 최소화(하강)
        self.W += self.lr_pi * gW * inv
        self.b += self.lr_pi * gb * inv
        self.w_v -= self.lr_v * 2.0 * gwv * inv
        self.c_v -= self.lr_v * 2.0 * gcv * inv


def train_ppo(
    env: TradingEnv,
    agent: PPOAgent,
    *,
    iterations: int = 40,
    steps_per_iter: int | None = None,
    seed: int | None = 0,
) -> list[float]:
    """PPO 학습 루프. 반복별 평균 스텝보상(×steps)을 history 로 반환."""
    steps = steps_per_iter or min(2048, max(256, len(env) - 1))
    history: list[float] = []
    for _ in range(iterations):
        batch = agent.collect(env, steps, seed=seed)
        agent.update(batch)
        rews = batch[2]
        history.append(float(rews.sum()))
    return history


@dataclass
class ContinuousPPOAgent:
    """연속 행동 PPO — 목표 포지션 사이즈 ∈ [-1,1] 를 직접 출력하는 Gaussian 정책.

    정책: mean = tanh(W·s + b)(∈[-1,1]), 표준편차 std = exp(log_std)(상태무관 파라미터).
    행동 a ~ N(mean, std) 를 [-1,1] 로 클립. log-prob 은 Gaussian 근사(tanh/clip 보정 생략 — 실용적).
    가치 V(s)=w·s+c. GAE + 클리핑 surrogate 로 학습. `act(obs, greedy=)` → float(REINFORCE/run_episode 호환).
    """

    obs_dim: int = OBS_DIM
    lr_pi: float = 0.02
    lr_v: float = 0.05
    gamma: float = 0.99
    lam: float = 0.95
    clip: float = 0.2
    init_log_std: float = -0.7      # std≈0.5 로 시작(탐험)
    epochs: int = 6
    minibatch: int = 256
    seed: int | None = 0

    W: "np.ndarray" = field(init=False)
    b: float = field(init=False, default=0.0)
    log_std: float = field(init=False, default=0.0)
    w_v: "np.ndarray" = field(init=False)
    c_v: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self.W = self._rng.normal(0.0, 0.01, size=self.obs_dim)
        self.b = 0.0
        self.log_std = float(self.init_log_std)
        self.w_v = np.zeros(self.obs_dim)
        self.c_v = 0.0

    def mean(self, obs: "np.ndarray") -> float:
        return float(np.tanh(self.W @ np.asarray(obs, dtype=np.float64) + self.b))

    def value(self, obs: "np.ndarray") -> float:
        return float(self.w_v @ np.asarray(obs, dtype=np.float64) + self.c_v)

    def act(self, obs: "np.ndarray", *, greedy: bool = False) -> float:
        mu = self.mean(obs)
        if greedy:
            return mu
        std = float(np.exp(self.log_std))
        return float(np.clip(mu + std * self._rng.normal(), -1.0, 1.0))

    def _logp(self, mu: float, a: float) -> float:
        std = float(np.exp(self.log_std))
        return -0.5 * ((a - mu) / std) ** 2 - self.log_std - 0.5 * np.log(2 * np.pi)

    def collect(self, env: TradingEnv, steps: int, *, seed: int | None = None):
        obss, acts, rews, vals, dones, logps = [], [], [], [], [], []
        obs, _ = env.reset(seed=seed)
        std = float(np.exp(self.log_std))
        for _ in range(steps):
            o = np.asarray(obs, dtype=np.float64)
            mu = self.mean(o)
            a = float(np.clip(mu + std * self._rng.normal(), -1.0, 1.0))
            obss.append(o)
            acts.append(a)
            vals.append(self.value(o))
            logps.append(self._logp(mu, a))
            obs, r, terminated, truncated, _ = env.step(a)
            rews.append(r)
            done = terminated or truncated
            dones.append(done)
            if done:
                obs, _ = env.reset(seed=seed)
        last_v = self.value(np.asarray(obs, dtype=np.float64))
        return (
            np.array(obss), np.array(acts, dtype=np.float64), np.array(rews, dtype=np.float64),
            np.array(vals, dtype=np.float64), np.array(dones, dtype=bool),
            np.array(logps, dtype=np.float64), last_v,
        )

    def update(self, batch) -> dict:
        obss, acts, rews, vals, dones, logps_old, last_v = batch
        adv, returns = compute_gae(rews, vals, dones, last_v, self.gamma, self.lam)
        adv_std = adv.std()
        adv_n = (adv - adv.mean()) / (adv_std + 1e-8)
        n = len(obss)
        idx_all = np.arange(n)
        for _ in range(self.epochs):
            self._rng.shuffle(idx_all)
            for start in range(0, n, self.minibatch):
                mb = idx_all[start:start + self.minibatch]
                self._update_minibatch(obss[mb], acts[mb], logps_old[mb], adv_n[mb], returns[mb])
        return {"adv_std": float(adv_std), "log_std": float(self.log_std)}

    def _update_minibatch(self, obss, acts, logps_old, adv, returns):
        gW = np.zeros_like(self.W)
        gb = 0.0
        glogstd = 0.0
        gwv = np.zeros_like(self.w_v)
        gcv = 0.0
        m = len(obss)
        std = float(np.exp(self.log_std))
        for i in range(m):
            o = obss[i]
            z = self.W @ o + self.b
            mu = np.tanh(z)
            a = acts[i]
            logp = -0.5 * ((a - mu) / std) ** 2 - self.log_std - 0.5 * np.log(2 * np.pi)
            ratio = np.exp(logp - logps_old[i])
            A = adv[i]
            unclipped = ratio * A
            clipped = np.clip(ratio, 1 - self.clip, 1 + self.clip) * A
            if unclipped <= clipped:  # surrogate 활성 분기
                # dlogp/dmu = (a-mu)/std^2 ; dmu/dz = 1-tanh^2 = 1-mu^2
                dlogp_dmu = (a - mu) / (std * std)
                dz = dlogp_dmu * (1.0 - mu * mu)
                coeff = A * ratio
                gW += coeff * dz * o
                gb += coeff * dz
                # dlogp/dlog_std = ((a-mu)/std)^2 - 1
                glogstd += coeff * (((a - mu) / std) ** 2 - 1.0)
            v = self.w_v @ o + self.c_v
            verr = v - returns[i]
            gwv += verr * o
            gcv += verr
        inv = 1.0 / max(m, 1)
        self.W += self.lr_pi * gW * inv
        self.b += self.lr_pi * gb * inv
        # log_std 는 천천히(과도한 분산 붕괴 방지) + 하한 클립.
        self.log_std = float(np.clip(self.log_std + 0.3 * self.lr_pi * glogstd * inv, -3.0, 1.0))
        self.w_v -= self.lr_v * 2.0 * gwv * inv
        self.c_v -= self.lr_v * 2.0 * gcv * inv


def train_ppo_continuous(
    env: TradingEnv,
    agent: ContinuousPPOAgent,
    *,
    iterations: int = 40,
    steps_per_iter: int | None = None,
    seed: int | None = 0,
) -> list[float]:
    """연속 PPO 학습 루프. 반복별 총 스텝보상을 history 로 반환."""
    steps = steps_per_iter or min(2048, max(256, len(env) - 1))
    history: list[float] = []
    for _ in range(iterations):
        batch = agent.collect(env, steps, seed=seed)
        agent.update(batch)
        history.append(float(batch[2].sum()))
    return history
