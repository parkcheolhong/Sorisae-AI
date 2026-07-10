"""M7 (F) 경량 스케줄러 CLI(설계서 §7/§9) — Airflow 없이 상주 가동.

두 작업을 한 프로세스에서 주기 실행한다:
  - **daily**: 매일 지정 UTC 시각(기본 02:00)에 전체 **재학습**(TradeStore 트리거 → 워크포워드 → 핫스왑).
  - **interval**: N분(기본 5분)마다 **튜닝 트리거** — 트리거 조건 충족 시 워크포워드 Sharpe 목적함수로
    하이퍼파라미터 탐색 후 재학습 게이트를 통과하면 승격(`tune_and_validate`).

SIGTERM/SIGINT 로 그레이스풀 종료(현재 작업 완료 후 정지). 모든 이벤트는 JSON 한 줄로 출력.

사용:
    python scripts/scheduler.py --db runs/live.sqlite --csv data/sol_events.csv \
        --model-dir models --audit runs/sched_audit.jsonl \
        --daily-hour 2 --tune-every 300 --tune-trials 30

    # 즉시 동작 확인(각 작업 1회 실행 후 종료)
    python scripts/scheduler.py --db :memory: --synthetic 1500 --once
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


def _load_ticks(args) -> list:
    return list(_build_feed(args).ticks())


def _install_signal_handlers(scheduler) -> None:
    import signal

    def _handler(signum, _frame):
        print(json.dumps({"event": "signal", "signal": int(signum), "action": "graceful_stop"}), flush=True)
        scheduler.request_stop()

    for name in ("SIGTERM", "SIGINT"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):
            pass


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="daytrade-ai 경량 스케줄러(M7-F)")
    p.add_argument("--db", default=":memory:", help="TradeStore sqlite 경로(트리거 입력)")
    p.add_argument("--run-id", dest="run_id", type=int, help="대상 run_id(미지정=최신)")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--csv", help="학습/튜닝용 캡처 CSV")
    src.add_argument("--synthetic", type=int, default=2000, help="합성 틱 수(CSV 미지정 시)")
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--model-dir", dest="model_dir", default="models")
    p.add_argument("--audit", help="해시체인 감사로그(JSONL) 경로")
    # 스케줄
    p.add_argument("--daily-hour", dest="daily_hour", type=int, default=2, help="일일 재학습 UTC 시각(시)")
    p.add_argument("--daily-minute", dest="daily_minute", type=int, default=0)
    p.add_argument("--tune-every", dest="tune_every", type=float, default=300.0, help="튜닝 트리거 주기(초)")
    p.add_argument("--poll", type=float, default=1.0, help="폴링 granularity(초)")
    p.add_argument("--once", action="store_true", help="각 작업 1회 즉시 실행 후 종료(스모크)")
    p.add_argument("--max-runtime", dest="max_runtime", type=float, default=0.0, help="최대 가동(초), 0=무제한")
    # 라벨/검증/트리거/인수 게이트
    p.add_argument("--horizon", type=int, default=20)
    p.add_argument("--up-bps", dest="up_bps", type=float, default=5.0)
    p.add_argument("--down-bps", dest="down_bps", type=float, default=5.0)
    p.add_argument("--n-splits", dest="n_splits", type=int, default=4)
    p.add_argument("--min-fills", dest="min_fills", type=int, default=20)
    p.add_argument("--max-drawdown", dest="max_drawdown", type=float, default=1.5)
    p.add_argument("--min-return", dest="min_return", type=float, default=0.0)
    p.add_argument("--force", action="store_true", help="트리거 무시 강제 재학습/튜닝")
    p.add_argument("--min-bal-acc", dest="min_bal_acc", type=float, default=0.50)
    p.add_argument("--max-overfit-gap", dest="max_gap", type=float, default=0.10)
    p.add_argument("--min-samples", dest="min_samples", type=int, default=100)
    # 튜닝
    p.add_argument("--tune-trials", dest="tune_trials", type=int, default=20)
    p.add_argument("--tune-metric", dest="tune_metric", default="mean_oos_sharpe")
    p.add_argument("--tune-backend", dest="tune_backend", default="auto")
    p.add_argument("--max-mdd", dest="max_mdd", type=float, default=3.0, help="튜닝 제약: OOS 최악 MDD 한도(%)")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    from daytrade.config import SignalConfig
    from daytrade.execution import TradeStore
    from daytrade.monitoring import AuditLog
    from daytrade.ops import (
        AcceptanceConfig,
        RetrainOrchestrator,
        Scheduler,
        TriggerConfig,
        evaluate_trigger,
    )
    from daytrade.training import RiskConstraints

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
    constraints = RiskConstraints(max_worst_mdd_pct=args.max_mdd)

    def _emit(ev: dict) -> None:
        print(json.dumps(ev, ensure_ascii=False), flush=True)

    def _daily_retrain():
        rep = orch.orchestrate(store, _build_feed(args), run_id=args.run_id, trigger=trigger)
        _emit({"event": "daily_retrain", **rep.as_dict()})
        return rep.as_dict()

    def _tune_trigger():
        decision = evaluate_trigger(store, args.run_id, cfg=trigger)
        if not decision.should_retrain:
            _emit({"event": "tune_skip", "reasons": decision.reasons, "live": decision.live})
            return {"triggered": False, "reasons": decision.reasons}
        ticks = _load_ticks(args)
        rep = orch.tune_and_validate(
            ticks, n_trials=args.tune_trials, metric=args.tune_metric,
            backend=args.tune_backend, constraints=constraints,
            n_splits=args.n_splits, tuning_seed=args.seed,
        )
        _emit({"event": "tune_retrain", **rep.as_dict()})
        return rep.as_dict()

    scheduler = Scheduler(poll_sec=args.poll, on_event=_emit)
    scheduler.daily("daily_retrain", at_hour=args.daily_hour, fn=_daily_retrain,
                    at_minute=args.daily_minute)
    scheduler.every("tune_trigger", args.tune_every, _tune_trigger)

    _install_signal_handlers(scheduler)
    _emit({"event": "scheduler_start", "daily_hour": args.daily_hour,
           "tune_every_sec": args.tune_every, "db": args.db, "model_dir": args.model_dir})

    if args.once:
        # 스모크: 스케줄 무시하고 두 작업 즉시 1회 실행.
        _daily_retrain()
        _tune_trigger()
        summary = scheduler.summary()
    else:
        summary = scheduler.run(max_runtime_sec=args.max_runtime)

    store.close()
    out = {"event": "scheduler_end", **summary,
           "audit_verified": (audit.verify().ok if audit else None)}
    _emit(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
