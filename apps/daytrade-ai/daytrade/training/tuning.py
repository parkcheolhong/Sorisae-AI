"""하이퍼파라미터 탐색 — 워크포워드 OOS 점수를 목적함수로(설계서 §9 자동 튜닝).

목적함수 = `walk_forward_backtest(...).summary[metric]` (예: mean_oos_return_pct / mean_oos_sharpe)을
**최대화**. 라벨/모델/시그널 하이퍼파라미터를 함께 탐색하되, 평가는 항상 시간순 OOS 이므로
in-sample 과최적화로 흐르지 않는다(워크포워드 자체가 일반화 측정).

백엔드 계층:
  - `optuna` 설치 시 TPE 샘플러 사용.
  - 미설치 시 순수 파이썬 **random search**(seed 고정, 항상 동작·테스트 가능).
동일 검색공간(`ParamSpec`)을 두 백엔드가 공유한다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from ..config import TradingConfig
from ..types import MarketTick
from .walkforward import walk_forward_backtest

WORST = -1.0e9  # 폴드 산출 불가 시 페널티 점수


@dataclass(frozen=True, slots=True)
class RiskConstraints:
    """워크포워드 목적함수에 리스크 제약을 패널티로 반영(설계서 §9 목적함수/제약).

    Sharpe 를 최대화하되, OOS 최대낙폭이 한도를 넘거나 수익 폴드 비율이 낮으면 점수를 깎는다
    (soft constraint). 과최적화로 한두 폴드에 베팅하는 해를 억제한다.
    """

    max_worst_mdd_pct: float = 3.0       # OOS 최악 폴드 MDD 한도(%)
    min_positive_fold_ratio: float = 0.5  # 수익 폴드 비율 하한
    mdd_penalty: float = 0.5              # 한도 1%p 초과당 점수 차감
    fold_penalty: float = 3.0             # 수익폴드비율 1.0 부족당 점수 차감


def score_summary(summary: dict, metric: str, constraints: "RiskConstraints | None" = None) -> float:
    """워크포워드 summary → (제약 반영) 목적 점수. 폴드 없으면 WORST."""
    if not summary or summary.get("n_folds", 0) == 0:
        return WORST
    base = summary.get(metric)
    if base is None:
        return WORST
    score = float(base)
    if constraints is not None:
        mdd = float(summary.get("worst_oos_mdd_pct", 0.0))
        if mdd > constraints.max_worst_mdd_pct:
            score -= constraints.mdd_penalty * (mdd - constraints.max_worst_mdd_pct)
        pfr = float(summary.get("positive_fold_ratio", 0.0))
        if pfr < constraints.min_positive_fold_ratio:
            score -= constraints.fold_penalty * (constraints.min_positive_fold_ratio - pfr)
    return score


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """탐색 파라미터 정의. kind: int | float | loguniform | categorical."""

    kind: str
    low: float = 0.0
    high: float = 1.0
    choices: tuple = ()

    def sample(self, rng: "np.random.Generator"):
        if self.kind == "int":
            return int(rng.integers(int(self.low), int(self.high) + 1))
        if self.kind == "float":
            return float(rng.uniform(self.low, self.high))
        if self.kind == "loguniform":
            return float(math.exp(rng.uniform(math.log(self.low), math.log(self.high))))
        if self.kind == "categorical":
            return self.choices[int(rng.integers(0, len(self.choices)))]
        raise ValueError(f"unknown kind: {self.kind}")

    def suggest(self, trial, name):
        if self.kind == "int":
            return trial.suggest_int(name, int(self.low), int(self.high))
        if self.kind == "float":
            return trial.suggest_float(name, self.low, self.high)
        if self.kind == "loguniform":
            return trial.suggest_float(name, self.low, self.high, log=True)
        if self.kind == "categorical":
            return trial.suggest_categorical(name, list(self.choices))
        raise ValueError(f"unknown kind: {self.kind}")


def default_search_space() -> dict[str, ParamSpec]:
    """단타 라벨/모델/시그널 핵심 하이퍼파라미터 기본 공간."""
    return {
        "horizon": ParamSpec("int", 5, 40),
        "up_bps": ParamSpec("float", 2.0, 15.0),
        "down_bps": ParamSpec("float", 2.0, 15.0),
        "lr": ParamSpec("loguniform", 0.01, 0.5),
        "epochs": ParamSpec("int", 50, 400),
        "ai_threshold": ParamSpec("float", 0.50, 0.70),
        "obi_threshold": ParamSpec("loguniform", 1.0e4, 5.0e5),
        "volume_spike_ratio": ParamSpec("float", 1.2, 3.0),
    }


@dataclass(slots=True)
class TuningResult:
    best_params: dict
    best_value: float
    metric: str
    backend: str
    trials: list[dict] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        lines = [
            f"backend            : {self.backend}",
            f"objective(metric)  : {self.metric} (maximize)",
            f"trials             : {len(self.trials)}",
            f"best value         : {self.best_value:.6f}",
            "best params        :",
        ]
        for k, v in self.best_params.items():
            vv = f"{v:.5g}" if isinstance(v, float) else v
            lines.append(f"  {k:<20}: {vv}")
        return lines


def _build_config(base: TradingConfig, params: dict) -> TradingConfig:
    ai = float(params["ai_threshold"])
    signal = replace(
        base.signal,
        obi_threshold=float(params["obi_threshold"]),
        volume_spike_ratio=float(params["volume_spike_ratio"]),
        ai_buy_threshold=ai,
        ai_sell_threshold=ai,
        use_ai=True,
    )
    return replace(base, signal=signal)


def _make_objective(
    ticks: list[MarketTick],
    base_config: TradingConfig,
    *,
    metric: str,
    n_splits: int,
    scheme: str,
    seed: int,
    constraints: "RiskConstraints | None" = None,
):
    def evaluate(params: dict) -> float:
        cfg = _build_config(base_config, params)
        report = walk_forward_backtest(
            ticks, cfg,
            horizon=int(params["horizon"]),
            up_bps=float(params["up_bps"]),
            down_bps=float(params["down_bps"]),
            n_splits=n_splits, scheme=scheme,
            epochs=int(params["epochs"]), lr=float(params["lr"]), seed=seed,
        )
        return score_summary(report.summary, metric, constraints)

    return evaluate


def run_tuning(
    ticks: list[MarketTick],
    base_config: TradingConfig,
    *,
    space: dict[str, ParamSpec] | None = None,
    n_trials: int = 20,
    metric: str = "mean_oos_sharpe",
    n_splits: int = 3,
    scheme: str = "rolling",
    seed: int = 42,
    backend: str = "auto",
    constraints: "RiskConstraints | None" = None,
) -> TuningResult:
    """워크포워드 점수를 최대화하는 하이퍼파라미터 탐색.

    metric: 워크포워드 summary 키(기본 `mean_oos_sharpe` — 설계서 §2/§7 walk-forward Sharpe).
    constraints: 지정 시 OOS MDD/수익폴드비율 제약을 패널티로 반영(과최적화 억제).
    backend: "auto"(optuna 있으면 TPE, 없으면 random) | "optuna" | "random".
    """
    space = space or default_search_space()
    evaluate = _make_objective(
        ticks, base_config, metric=metric, n_splits=n_splits, scheme=scheme,
        seed=seed, constraints=constraints,
    )

    chosen = backend
    if backend == "auto":
        chosen = "optuna" if _optuna_available() else "random"

    if chosen == "optuna":
        return _run_optuna(evaluate, space, n_trials, metric, seed)
    if chosen == "random":
        return _run_random(evaluate, space, n_trials, metric, seed)
    raise ValueError(f"unknown backend: {backend!r}")


def _optuna_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("optuna") is not None


def _run_random(evaluate, space, n_trials, metric, seed) -> TuningResult:
    rng = np.random.default_rng(seed)
    trials: list[dict] = []
    best_params: dict = {}
    best_value = WORST
    for i in range(n_trials):
        params = {name: spec.sample(rng) for name, spec in space.items()}
        value = evaluate(params)
        trials.append({"trial": i, "params": params, "value": round(value, 6)})
        if value > best_value:
            best_value, best_params = value, params
    return TuningResult(
        best_params=best_params, best_value=round(best_value, 6),
        metric=metric, backend="random", trials=trials,
    )


def _run_optuna(evaluate, space, n_trials, metric, seed) -> TuningResult:
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        params = {name: spec.suggest(trial, name) for name, spec in space.items()}
        return evaluate(params)

    study = optuna.create_study(
        direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed)
    )
    study.optimize(objective, n_trials=n_trials)
    trials = [
        {"trial": t.number, "params": dict(t.params), "value": (round(t.value, 6) if t.value is not None else None)}
        for t in study.trials
    ]
    return TuningResult(
        best_params=dict(study.best_params), best_value=round(float(study.best_value), 6),
        metric=metric, backend="optuna", trials=trials,
    )
