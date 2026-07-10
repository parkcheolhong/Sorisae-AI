"""KPI 회귀셋 — 튜닝 전/후 모델을 **다중 레짐**에서 비교(M7 인수기준: 자동 튜닝 KPI 개선 정량 증빙).

각 레짐(시간대/변동성 다른 캡처)에 대해:
  - **baseline**: 기본 라벨/시그널 파라미터로 워크포워드 OOS 백테스트.
  - **tuned**: `run_tuning`(워크포워드 Sharpe 목적함수)으로 찾은 best 파라미터로 동일 워크포워드 백테스트.
두 결과 모두 **OOS(폴드)** 로 측정하므로 in-sample 과최적화로 흐르지 않는다(워크포워드 자체가 일반화 측정).
KPI: 평균 OOS 수익률·Sharpe, 최악 폴드 MDD, 수익 폴드 비율. 레짐 평균으로 **개선 판정(verdict)** 을 낸다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import TradingConfig
from ..types import MarketTick
from .tuning import RiskConstraints, default_search_space, run_tuning
from .walkforward import walk_forward_backtest

# baseline 라벨/학습 기본값(설계 기본 — 튜닝 미적용 상태 대표).
BASELINE_PARAMS = {"horizon": 20, "up_bps": 5.0, "down_bps": 5.0, "lr": 0.1, "epochs": 200}

KPI_KEYS = ("mean_oos_return_pct", "mean_oos_sharpe", "worst_oos_mdd_pct", "positive_fold_ratio")


def _kpis(summary: dict) -> dict:
    return {k: float(summary.get(k, 0.0)) for k in KPI_KEYS} | {"n_folds": int(summary.get("n_folds", 0))}


@dataclass(slots=True)
class RegimeResult:
    name: str
    baseline: dict
    tuned: dict
    best_params: dict
    improved: bool

    @property
    def delta(self) -> dict:
        return {k: round(self.tuned[k] - self.baseline[k], 4) for k in KPI_KEYS}


@dataclass(slots=True)
class KpiRegressionReport:
    regimes: list[RegimeResult] = field(default_factory=list)
    metric: str = "mean_oos_sharpe"

    def _mean(self, side: str, key: str) -> float:
        vals = [getattr(r, side)[key] for r in self.regimes if getattr(r, side).get("n_folds", 0) > 0]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    @property
    def verdict(self) -> dict:
        """레짐 평균 기준 개선 판정: 목적 지표(Sharpe) 향상 + 최악 MDD 비악화(허용 0.1%p)."""
        base_sh = self._mean("baseline", "mean_oos_sharpe")
        tuned_sh = self._mean("tuned", "mean_oos_sharpe")
        base_mdd = self._mean("baseline", "worst_oos_mdd_pct")
        tuned_mdd = self._mean("tuned", "worst_oos_mdd_pct")
        base_ret = self._mean("baseline", "mean_oos_return_pct")
        tuned_ret = self._mean("tuned", "mean_oos_return_pct")
        return {
            "metric": self.metric,
            "baseline_mean_sharpe": base_sh, "tuned_mean_sharpe": tuned_sh,
            "baseline_mean_return_pct": base_ret, "tuned_mean_return_pct": tuned_ret,
            "baseline_mean_worst_mdd_pct": base_mdd, "tuned_mean_worst_mdd_pct": tuned_mdd,
            "sharpe_improved": tuned_sh >= base_sh,
            "mdd_not_worse": tuned_mdd <= base_mdd + 0.1,
            "regimes_improved": sum(1 for r in self.regimes if r.improved),
            "regimes_total": len(self.regimes),
            "passed": (tuned_sh >= base_sh) and (tuned_mdd <= base_mdd + 0.1),
        }

    def as_dict(self) -> dict:
        return {
            "metric": self.metric,
            "regimes": [{"name": r.name, "baseline": r.baseline, "tuned": r.tuned,
                         "delta": r.delta, "best_params": r.best_params, "improved": r.improved}
                        for r in self.regimes],
            "verdict": self.verdict,
        }


def _build_tuned_config(base: TradingConfig, best: dict) -> TradingConfig:
    from dataclasses import replace
    ai = float(best["ai_threshold"])
    signal = replace(base.signal, obi_threshold=float(best["obi_threshold"]),
                     volume_spike_ratio=float(best["volume_spike_ratio"]),
                     ai_buy_threshold=ai, ai_sell_threshold=ai, use_ai=True)
    return replace(base, signal=signal)


def compare_regime(
    name: str,
    ticks: list[MarketTick],
    base_config: TradingConfig,
    *,
    metric: str = "mean_oos_sharpe",
    n_splits: int = 3,
    scheme: str = "rolling",
    n_trials: int = 20,
    backend: str = "auto",
    constraints: RiskConstraints | None = None,
    seed: int = 42,
) -> RegimeResult:
    """한 레짐에서 baseline vs tuned 워크포워드 OOS KPI 비교."""
    base_summary = walk_forward_backtest(
        ticks, base_config, n_splits=n_splits, scheme=scheme, seed=seed, **BASELINE_PARAMS,
    ).summary
    result = run_tuning(
        ticks, base_config, space=default_search_space(), n_trials=n_trials, metric=metric,
        n_splits=n_splits, scheme=scheme, seed=seed, backend=backend, constraints=constraints,
    )
    best = result.best_params
    tuned_summary = walk_forward_backtest(
        ticks, _build_tuned_config(base_config, best),
        horizon=int(best["horizon"]), up_bps=float(best["up_bps"]), down_bps=float(best["down_bps"]),
        n_splits=n_splits, scheme=scheme, epochs=int(best["epochs"]), lr=float(best["lr"]), seed=seed,
    ).summary
    base_kpi, tuned_kpi = _kpis(base_summary), _kpis(tuned_summary)
    improved = tuned_kpi[metric] >= base_kpi[metric]
    return RegimeResult(name=name, baseline=base_kpi, tuned=tuned_kpi,
                        best_params=best, improved=improved)


def compare_regimes(
    regimes: dict[str, list[MarketTick]],
    base_config: TradingConfig,
    *,
    metric: str = "mean_oos_sharpe",
    **kwargs,
) -> KpiRegressionReport:
    """여러 레짐에 대해 baseline vs tuned 를 일괄 비교해 회귀 리포트 생성."""
    report = KpiRegressionReport(metric=metric)
    for nm, ticks in regimes.items():
        report.regimes.append(compare_regime(nm, ticks, base_config, metric=metric, **kwargs))
    return report
