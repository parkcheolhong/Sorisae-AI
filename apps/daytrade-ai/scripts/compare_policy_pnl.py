"""연속행동 RL 정책(ONNX)을 실제 `TradingPipeline` 백테스트에 연결해 PnL 비교.

흐름:
  1) 틱 로드(--sim 합성 / --csv 리플레이)
  2) `ContinuousPPOAgent` 학습 → `export_continuous_policy_to_onnx`(표준화 내장 그래프)
  3) 동일 `TradingConfig` 로 백테스트 3종 비교:
       - rules-only      : 규칙(detection)만, AI 게이트 없음(--no-ai 상당)
       - heuristic-AI    : detection + `HeuristicModel` 확인 게이트
       - rl-policy-AI    : detection + `OnnxPolicyModel`(연속 RL 정책, 자동 로드)
  4) return% / realized PnL / sharpe / maxDD / fills 표로 비교

주의: 데모 목적상 RL 학습/평가가 동일 구간(in-sample)일 수 있다. 진짜 OOS 성능은
`walkforward` 서브커맨드로 별도 검증한다. 본 스크립트의 목적은 "RL 정책 → ONNX →
실제 추론 인터페이스(OnnxPolicyModel) → 파이프라인 백테스트" 결선이 동작함을 PnL 로 확인하는 것.

사용:
    python scripts/compare_policy_pnl.py --sim --ticks 6000 --iterations 60 --ai-threshold 0.5
    python scripts/compare_policy_pnl.py --csv data/sol_events.csv --iterations 80
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

# 패키지 루트(apps/daytrade-ai)를 import 경로에 추가 — `python scripts/...` 직접 실행 지원.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_ticks(args) -> list:
    from daytrade.feed.replay import CsvReplayFeed
    from daytrade.feed.simulated import SimulatedFeed

    if args.sim:
        return list(SimulatedFeed(symbol=args.symbol, n_ticks=args.ticks, seed=args.seed).ticks())
    return list(CsvReplayFeed(args.csv).ticks())


def _train_policy_onnx(args, ticks, onnx_path: str) -> dict:
    """ContinuousPPOAgent 학습 후 ONNX export. 학습 요약 dict 반환."""
    from daytrade.rl import ContinuousPPOAgent, RLConfig, TradingEnv, run_episode, train_ppo_continuous
    from daytrade.training.onnx_export import export_continuous_policy_to_onnx

    env = TradingEnv(
        ticks,
        RLConfig(depth=args.depth, cost_bps=args.cost_bps,
                 reward_scale=args.reward_scale, action_mode="continuous"),
    )
    agent = ContinuousPPOAgent(seed=args.seed)
    _, _, _, base = run_episode(env, agent, greedy=False, seed=args.seed)
    history = train_ppo_continuous(env, agent, iterations=args.iterations, seed=args.seed)
    _, _, _, trained = run_episode(env, agent, greedy=True, seed=args.seed)
    export_continuous_policy_to_onnx(agent.W, agent.b, env._mean, env._std, onnx_path)
    import numpy as np

    return {
        "baseline_reward": round(float(base), 4),
        "trained_greedy_reward": round(float(trained), 4),
        "final10_mean": round(float(np.mean(history[-10:])), 4) if history else 0.0,
    }


def _run(args, ticks, *, use_ai: bool, model=None) -> dict:
    from daytrade.backtest.runner import run_backtest
    from daytrade.config import RiskConfig, SignalConfig, TradingConfig, TradingMode
    from daytrade.feed.memory import ListFeed

    signal = SignalConfig(
        depth=args.depth,
        obi_threshold=args.obi_threshold,
        volume_spike_ratio=args.vol_spike,
        ai_buy_threshold=args.ai_threshold,
        ai_sell_threshold=args.ai_threshold,
        use_ai=use_ai,
    )
    config = TradingConfig(
        mode=TradingMode.BACKTEST,
        symbols=(args.symbol,),
        starting_cash=args.cash,
        signal=signal,
        # 결정적 비교를 위해 벽시계 레이턴시 서킷브레이커 비활성.
        risk=RiskConfig(max_latency_ms=float("inf")),
        seed=args.seed,
    )
    report = run_backtest(config, ListFeed(ticks), model=model)
    m = report.metrics
    return {
        "signals": m.signals,
        "orders": m.orders_submitted,
        "fills": m.fills,
        "return_pct": round(m.total_return_pct, 4),
        "realized_pnl": round(m.realized_pnl, 2),
        "sharpe": round(m.sharpe, 4),
        "max_dd_pct": round(m.max_drawdown_pct, 4),
        "end_equity": round(m.end_equity, 2),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="RL 정책(ONNX) vs 휴리스틱 PnL 비교(실제 파이프라인)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv")
    src.add_argument("--sim", action="store_true")
    p.add_argument("--symbol", default="SOLUSDT")
    p.add_argument("--ticks", type=int, default=6000)
    p.add_argument("--depth", type=int, default=10)
    p.add_argument("--iterations", type=int, default=60)
    p.add_argument("--cost-bps", dest="cost_bps", type=float, default=1.0)
    p.add_argument("--reward-scale", dest="reward_scale", type=float, default=1e4)
    p.add_argument("--cash", type=float, default=1_000_000.0)
    p.add_argument("--ai-threshold", dest="ai_threshold", type=float, default=0.5,
                   help="AI 확인 게이트 임계(휴리스틱/RL 정책 공통 적용)")
    p.add_argument("--obi-threshold", dest="obi_threshold", type=float, default=1.0e6,
                   help="detection OBI 임계(자산 스케일에 맞춰 조정; 암호화폐는 수~수십)")
    p.add_argument("--vol-spike", dest="vol_spike", type=float, default=2.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--onnx", help="정책 ONNX 저장 경로(미지정 시 임시파일)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    ticks = _load_ticks(args)
    if len(ticks) < 100:
        print("[ERR] 비교에는 더 많은 틱이 필요합니다(>=100).")
        return 2

    onnx_path = args.onnx or str(Path(tempfile.gettempdir()) / "daytrade_policy_cmp.onnx")
    train_info = _train_policy_onnx(args, ticks, onnx_path)

    # 정책 ONNX 자동 로드(load_model 이 출력차원 1 → OnnxPolicyModel 로 디스패치).
    from daytrade.inference.model import HeuristicModel, load_model

    policy_model = load_model(onnx_path)
    rows = {
        "rules-only": _run(args, ticks, use_ai=False),
        "heuristic-AI": _run(args, ticks, use_ai=True, model=HeuristicModel()),
        "rl-policy-AI": _run(args, ticks, use_ai=True, model=policy_model),
    }
    result = {
        "source": "sim" if args.sim else args.csv,
        "ticks": len(ticks),
        "ai_threshold": args.ai_threshold,
        "policy_onnx": onnx_path,
        "policy_loader": type(policy_model).__name__,
        "train": train_info,
        "backtests": rows,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print("=" * 78)
    print(" daytrade-ai — 연속행동 RL 정책(ONNX) vs 휴리스틱 PnL 비교")
    print("=" * 78)
    print(f"  source={result['source']}  ticks={result['ticks']}  ai_threshold={args.ai_threshold}")
    print(f"  policy ONNX={onnx_path}  loader={result['policy_loader']}")
    print(f"  RL 학습: baseline={train_info['baseline_reward']} → greedy={train_info['trained_greedy_reward']}"
          f" (final10={train_info['final10_mean']})")
    print("-" * 78)
    hdr = f"  {'variant':14s} {'signals':>8s} {'fills':>6s} {'return%':>9s} {'realizedPnL':>13s} {'sharpe':>8s} {'maxDD%':>8s}"
    print(hdr)
    print("-" * 78)
    for name, r in rows.items():
        print(f"  {name:14s} {r['signals']:>8d} {r['fills']:>6d} {r['return_pct']:>9.4f}"
              f" {r['realized_pnl']:>13,.2f} {r['sharpe']:>8.4f} {r['max_dd_pct']:>8.4f}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
