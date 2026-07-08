"""페이퍼 트레이딩 봇(설계서 §6) — 실시간/리플레이 피드 → 파이프라인 → 모의주문 → sqlite 영속.

`TradingPipeline`(feature→detection→AI→risk→paper execution→portfolio)을 그대로 구동하면서
체결 이벤트를 `TradeStore` 에 적재하고, 주기적으로 자본곡선을 스냅샷한다(상태 DB 영속 + 재학습
데이터 수집 훅). 실거래(LIVE)는 이중 안전 게이트가 없으면 항상 paper 로 강등된다.

사용:
    # 합성/리플레이(즉시 실행)
    python scripts/paper_trading_bot.py --sim --symbol AAPL --ticks 4000 --db runs.sqlite
    python scripts/paper_trading_bot.py --csv data/sol_events.csv --db runs.sqlite

    # 실시간(Binance, websockets 필요)
    python scripts/paper_trading_bot.py --live --symbol BTCUSDT --ticks 2000 --db runs.sqlite
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _build_feed(args):
    from daytrade.feed.replay import CsvReplayFeed
    from daytrade.feed.simulated import SimulatedFeed

    if args.live:
        from daytrade.feed.binance import BinanceFeed

        return BinanceFeed(symbol=args.symbol, depth=args.depth, max_ticks=args.ticks)
    if args.sim:
        return SimulatedFeed(symbol=args.symbol, n_ticks=args.ticks, depth=args.depth, seed=args.seed)
    return CsvReplayFeed(args.csv)


def main(argv=None) -> int:  # NOSONAR
    p = argparse.ArgumentParser(description="daytrade-ai 페이퍼 트레이딩 봇(피드→파이프라인→sqlite)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--sim", action="store_true", help="합성 시뮬레이션 피드")
    src.add_argument("--csv", help="리플레이 CSV 피드")
    src.add_argument("--live", action="store_true", help="Binance 실시간 피드(websockets 필요)")
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--depth", type=int, default=10)
    p.add_argument("--ticks", type=int, default=4000)
    p.add_argument("--cash", type=float, default=1_000_000.0)
    p.add_argument("--obi-threshold", dest="obi_threshold", type=float, default=1.0e6)
    p.add_argument("--ai-threshold", dest="ai_threshold", type=float, default=0.9)
    p.add_argument("--no-ai", action="store_true")
    p.add_argument("--model", help="추론 모델 경로(*.json/*.onnx; 연속RL정책 자동판별)")
    p.add_argument("--db", default=":memory:", help="sqlite 영속 경로(기본 메모리)")
    p.add_argument("--equity-every", dest="equity_every", type=int, default=200,
                   help="자본곡선 스냅샷 주기(틱)")
    p.add_argument("--audit", help="해시체인 감사로그(JSONL) 경로(M6)")
    p.add_argument("--metrics-out", dest="metrics_out", help="Prometheus 메트릭 노출 텍스트 저장 경로(M6)")
    p.add_argument("--metrics-port", dest="metrics_port", type=int, default=0,
                   help="라이브 /metrics HTTP 노출 포트(0=비활성). 스크레이프용(M6-A)")
    p.add_argument("--serve-seconds", dest="serve_seconds", type=float, default=0.0,
                   help="종료 후 /metrics 를 유지하는 시간(초). 배치 스크레이프 윈도(M6-A)")
    p.add_argument("--trace-out", dest="trace_out", help="Jaeger식 span JSON 저장 경로(M6-A)")
    p.add_argument("--trace-sample", dest="trace_sample", type=int, default=50,
                   help="트레이싱 샘플링(N틱당 1트레이스, --trace-out 시 적용)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    from daytrade.config import SignalConfig, TradingConfig, TradingMode
    from daytrade.execution import TradeStore
    from daytrade.monitoring import (
        AlertEngine,
        AuditLog,
        LiveMetrics,
        MetricsServer,
        Tracer,
        registry_from_run,
    )
    from daytrade.pipeline import TradingPipeline
    from daytrade.types import Order, OrderSide

    config = TradingConfig(
        mode=TradingMode.PAPER,
        symbols=(args.symbol,),
        starting_cash=args.cash,
        signal=SignalConfig(depth=args.depth, obi_threshold=args.obi_threshold,
                            ai_buy_threshold=args.ai_threshold, ai_sell_threshold=args.ai_threshold,
                            use_ai=not args.no_ai),
        seed=args.seed,
    )

    store = TradeStore(args.db)
    started = datetime.now(timezone.utc).isoformat()
    run_id = store.start_run(mode=config.mode.value, symbol=args.symbol, started_at=started,
                             note="paper_trading_bot")

    audit = AuditLog(args.audit) if args.audit else None
    if audit:
        audit.append("run_start", run_id=run_id, mode=config.mode.value, symbol=args.symbol)

    # 체결 이벤트 → sqlite 적재 + 불변 감사로그(피드백 루프 + 감사 적재 지점).
    def on_event(ev: dict) -> None:
        if ev.get("event") != "fill":
            return
        side = OrderSide(ev["side"])
        order = Order(symbol=ev["symbol"], side=side, qty=ev["qty"], ts_ns=0,
                      client_order_id=f"bot-{run_id}-{ev['symbol']}")
        from daytrade.types import Fill

        store.record_fill(Fill(order=order, filled_qty=ev["qty"], avg_price=ev["price"],
                               ts_ns=0, slippage=ev["slippage"], status="filled"), run_id=run_id)
        if audit:
            audit.append("fill", symbol=ev["symbol"], side=ev["side"], qty=ev["qty"],
                         price=ev["price"], slippage=ev["slippage"])

    tracer = Tracer(sample_rate=args.trace_sample) if args.trace_out else None
    pipeline = TradingPipeline(config, model_path=args.model, on_event=on_event, tracer=tracer)

    # 라이브 /metrics 노출(스크레이프). registry 는 루프에서 갱신.
    live = None
    server = None
    if args.metrics_port:
        live = LiveMetrics(symbol=args.symbol, mode=pipeline.effective_mode.value)
        server = MetricsServer(lambda: live.registry, port=args.metrics_port).start()
        print(f"[metrics] serving {server.url}")

    # 자본곡선 스냅샷을 위해 process_tick 을 감싼다(주기적 equity 기록).
    feed = _build_feed(args)
    count = 0
    try:
        for tick in feed.ticks():
            pipeline.process_tick(tick)
            count += 1
            if count % args.equity_every == 0:
                eq = pipeline.portfolio.equity({tick.symbol: tick.last_price})
                store.record_equity(tick.ts_ns, eq, run_id=run_id)
                if live is not None:
                    live.update(pipeline.metrics, eq)
            if count >= args.ticks:
                break
    except ModuleNotFoundError:
        print("[ERR] 실시간 피드에는 'websockets' 패키지가 필요합니다: pip install websockets")
        if server is not None:
            server.stop()
        store.close()
        return 2

    metrics = pipeline.metrics.finalize()
    # 마지막 equity 스냅샷.
    store.record_equity(metrics.ticks, metrics.end_equity, run_id=run_id)

    # Prometheus 메트릭 노출 텍스트 저장(M6).
    if args.metrics_out:
        reg = registry_from_run(metrics, symbol=args.symbol, mode=pipeline.effective_mode.value)
        Path(args.metrics_out).write_text(reg.render(), encoding="utf-8")

    # 트레이싱 span 덤프 + 구간 요약(M6-A).
    trace_summary = None
    if tracer is not None:
        trace_summary = tracer.stage_summary()
        if args.trace_out:
            Path(args.trace_out).write_text(
                json.dumps(tracer.export_jaeger(), ensure_ascii=False, indent=2), encoding="utf-8"
            )

    # 라이브 메트릭 최종 갱신 + 종료 후 스크레이프 윈도 유지(M6-A).
    if live is not None:
        live.update(pipeline.metrics, metrics.end_equity)
    if server is not None and args.serve_seconds > 0:
        import time as _time

        print(f"[metrics] holding {server.url} for {args.serve_seconds}s")
        _time.sleep(args.serve_seconds)
    if server is not None:
        server.stop()

    # 알림 규칙 평가(M6) — 서킷브레이커/낙폭/레이턴시/거절률.
    snapshot = {**metrics.as_dict(), "orders_submitted": metrics.orders_submitted}
    alerts = [{"name": a.name, "severity": a.severity, "message": a.message}
              for a in AlertEngine().evaluate(snapshot)]

    if audit:
        audit.append("run_end", run_id=run_id, ticks=metrics.ticks, fills=metrics.fills,
                     return_pct=round(metrics.total_return_pct, 4), alerts=len(alerts))

    summary = {
        "run_id": run_id,
        "db": args.db,
        "effective_mode": pipeline.effective_mode.value,
        "ticks": metrics.ticks,
        "signals": metrics.signals,
        "fills": metrics.fills,
        "return_pct": round(metrics.total_return_pct, 4),
        "realized_pnl": round(metrics.realized_pnl, 2),
        "sharpe": round(metrics.sharpe, 4),
        "max_dd_pct": round(metrics.max_drawdown_pct, 4),
        "end_equity": round(metrics.end_equity, 2),
        "store_summary": store.summary(run_id),
        "alerts": alerts,
        "audit": ({"path": args.audit, "verified": audit.verify().ok} if audit else None),
        "trace_summary": trace_summary,
    }
    store.close()

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("=" * 64)
        print(" daytrade-ai 페이퍼 트레이딩 봇 — 결과")
        print("=" * 64)
        for k, v in summary.items():
            print(f"  {k:16s}: {v}")
        print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
