"""M7 재학습 오케스트레이션 CLI(설계서 §7) — TradeStore 트리거 → 재학습 → 워크포워드 → 핫스왑.

상주 러너가 쌓은 sqlite(`TradeStore`)의 최신 run 성과로 재학습 트리거를 판정하고, 캡처된
시장 틱(CSV 또는 합성)으로 모델을 재학습·검증·export 한다. 인수 게이트를 통과하면 버전 아티팩트
(`models/model_vN.json`/`.onnx` + `current.json`)를 만들고, 감사로그에 핫스왑 트리거를 남긴다.

사용:
    # 라이브 sqlite 트리거 + CSV 캡처로 재학습
    python scripts/retrain.py --db runs/live.sqlite --csv data/sol_events.csv \
        --model-dir models --audit runs/retrain_audit.jsonl

    # 트리거 무시하고 강제 재학습(스케줄/수동)
    python scripts/retrain.py --db runs/live.sqlite --synthetic 4000 --force --model-dir models
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _build_feed(args):
    from daytrade.feed.replay import CsvReplayFeed
    from daytrade.feed.simulated import SimulatedFeed

    if args.csv:
        return CsvReplayFeed(args.csv)
    return SimulatedFeed(symbol=args.symbol, n_ticks=args.synthetic, seed=args.seed)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="daytrade-ai 재학습 오케스트레이터(M7)")
    p.add_argument("--db", default=":memory:", help="TradeStore sqlite 경로(트리거 입력)")
    p.add_argument("--run-id", dest="run_id", type=int, help="대상 run_id(미지정=최신)")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--csv", help="학습용 캡처 CSV(리플레이)")
    src.add_argument("--synthetic", type=int, default=4000, help="합성 틱 수(CSV 미지정 시)")
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--model-dir", dest="model_dir", default="models")
    p.add_argument("--audit", help="해시체인 감사로그(JSONL) 경로")
    p.add_argument("--horizon", type=int, default=20)
    p.add_argument("--up-bps", dest="up_bps", type=float, default=5.0)
    p.add_argument("--down-bps", dest="down_bps", type=float, default=5.0)
    p.add_argument("--n-splits", dest="n_splits", type=int, default=4)
    # 트리거 임계
    p.add_argument("--min-fills", dest="min_fills", type=int, default=20)
    p.add_argument("--max-drawdown", dest="max_drawdown", type=float, default=1.5)
    p.add_argument("--min-return", dest="min_return", type=float, default=0.0)
    p.add_argument("--force", action="store_true", help="트리거 무시 강제 재학습")
    # 인수 게이트
    p.add_argument("--min-bal-acc", dest="min_bal_acc", type=float, default=0.50)
    p.add_argument("--max-overfit-gap", dest="max_gap", type=float, default=0.10)
    p.add_argument("--min-samples", dest="min_samples", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    from daytrade.config import SignalConfig
    from daytrade.execution import TradeStore
    from daytrade.monitoring import AuditLog
    from daytrade.ops import AcceptanceConfig, RetrainOrchestrator, TriggerConfig

    store = TradeStore(args.db)
    audit = AuditLog(args.audit) if args.audit else None

    orch = RetrainOrchestrator(
        signal=SignalConfig(use_ai=True),
        model_dir=args.model_dir, horizon=args.horizon,
        up_bps=args.up_bps, down_bps=args.down_bps, n_splits=args.n_splits,
        acceptance=AcceptanceConfig(min_oos_bal_acc=args.min_bal_acc,
                                    max_overfit_gap=args.max_gap, min_samples=args.min_samples),
        audit=audit,
    )
    trigger = TriggerConfig(min_new_fills=args.min_fills, max_drawdown_pct=args.max_drawdown,
                            min_return_pct=args.min_return, force=args.force)

    rep = orch.orchestrate(store, _build_feed(args), run_id=args.run_id, trigger=trigger)
    store.close()

    out = rep.as_dict()
    if audit:
        out["audit_verified"] = audit.verify().ok
    print(json.dumps(out, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
