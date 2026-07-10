"""M7 (G) KPI 회귀셋 CLI — 튜닝 전/후 모델을 다중 레짐에서 비교(자동 튜닝 KPI 개선 증빙).

각 레짐(다른 변동성/시간대 캡처)에서 baseline vs tuned 워크포워드 OOS KPI(평균 수익률·Sharpe·최악
MDD·수익폴드비율)를 산출하고, 레짐 평균으로 개선 판정을 낸다. CI 게이트로 쓸 수 있게 개선 실패 시
비정상 종료(exit 1)한다.

사용:
    # 합성 다중 레짐(저변동/고변동/이벤트빈발 자동 생성)
    python scripts/kpi_regression.py --synthetic-regimes --ticks 1500 --n-trials 20 \
        --backend auto --max-mdd 3.0 --out runs/kpi_regression.json

    # 실제 캡처 다중 레짐(NAME=CSV 반복)
    python scripts/kpi_regression.py --regime open=data/sol_open.csv \
        --regime news=data/sol_news.csv --n-trials 30
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _synthetic_regimes(symbol: str, n: int, seed: int) -> dict:
    """대표 레짐 3종: 잔잔(low-vol)·변동(high-vol)·이벤트빈발(event-rich)."""
    from daytrade.feed.simulated import SimulatedFeed

    specs = {
        "calm":    dict(volatility=0.01, event_prob=0.005),
        "volatile": dict(volatility=0.05, event_prob=0.02),
        "event_rich": dict(volatility=0.03, event_prob=0.06),
    }
    out = {}
    for i, (name, kw) in enumerate(specs.items()):
        out[name] = list(SimulatedFeed(symbol=symbol, n_ticks=n, seed=seed + i, **kw).ticks())
    return out


def _csv_regimes(pairs: list[str]) -> dict:
    from daytrade.feed.replay import CsvReplayFeed

    out = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--regime 형식은 NAME=CSV 입니다: {pair!r}")
        name, path = pair.split("=", 1)
        out[name] = list(CsvReplayFeed(path).ticks())
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="daytrade-ai KPI 회귀셋(M7-G 튜닝 전/후 비교)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--synthetic-regimes", action="store_true", help="합성 다중 레짐 자동 생성")
    src.add_argument("--regime", action="append", default=[], help="NAME=CSV (반복 지정)")
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--ticks", type=int, default=1500, help="합성 레짐 틱 수")
    p.add_argument("--metric", default="mean_oos_sharpe", help="개선 판정 목적 지표")
    p.add_argument("--n-splits", dest="n_splits", type=int, default=3)
    p.add_argument("--scheme", default="rolling", choices=["rolling", "anchored"])
    p.add_argument("--n-trials", dest="n_trials", type=int, default=20)
    p.add_argument("--backend", default="auto", choices=["auto", "optuna", "random"])
    p.add_argument("--max-mdd", dest="max_mdd", type=float, default=3.0,
                   help="튜닝 제약: OOS 최악 MDD 한도(%)")
    p.add_argument("--no-constraints", action="store_true", help="튜닝 리스크 제약 비활성")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", help="리포트 JSON 저장 경로")
    p.add_argument("--metrics-out", dest="metrics_out",
                   help="verdict 를 Prometheus textfile(.prom)로 저장(node_exporter textfile collector/pushgateway)")
    args = p.parse_args(argv)

    from daytrade.config import SignalConfig, TradingConfig
    from daytrade.training import RiskConstraints, compare_regimes

    if args.synthetic_regimes:
        regimes = _synthetic_regimes(args.symbol, args.ticks, args.seed)
    else:
        regimes = _csv_regimes(args.regime)

    base_config = TradingConfig(symbols=(args.symbol,), signal=SignalConfig(use_ai=True))
    constraints = None if args.no_constraints else RiskConstraints(max_worst_mdd_pct=args.max_mdd)

    report = compare_regimes(
        regimes, base_config, metric=args.metric, n_splits=args.n_splits, scheme=args.scheme,
        n_trials=args.n_trials, backend=args.backend, constraints=constraints, seed=args.seed,
    )
    out = report.as_dict()
    payload = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload, encoding="utf-8")
    print(payload, flush=True)

    v = out["verdict"]
    if args.metrics_out:
        from daytrade.monitoring import registry_from_kpi_verdict

        Path(args.metrics_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.metrics_out).write_text(registry_from_kpi_verdict(v).render(), encoding="utf-8")
    print(f"\n[verdict] metric={v['metric']} "
          f"sharpe {v['baseline_mean_sharpe']:+.3f}→{v['tuned_mean_sharpe']:+.3f} "
          f"(improved={v['sharpe_improved']}), "
          f"worst_mdd {v['baseline_mean_worst_mdd_pct']:.3f}→{v['tuned_mean_worst_mdd_pct']:.3f} "
          f"(not_worse={v['mdd_not_worse']}), "
          f"regimes_improved={v['regimes_improved']}/{v['regimes_total']} "
          f"=> {'PASS' if v['passed'] else 'FAIL'}", flush=True)
    return 0 if v["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
