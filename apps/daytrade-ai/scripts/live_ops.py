"""라이브 상시운영 러너 CLI(설계서 §6/§10-5) — 페이퍼봇을 무중단 가동.

`LiveRunner`(자동재연결·heartbeat·일일리포트)에 M6 구성요소(`/metrics` HTTP·해시체인 감사로그·알림)
와 `TradeStore`(sqlite)를 결선한다. 피드가 끊기면 지수 백오프로 재연결하고, 주기적으로 heartbeat
(JSON 한 줄)를 출력하며, UTC 자정마다 일일 리포트를 산출한다.

사용:
    # 합성/리플레이(즉시·반복 재연결로 무중단 시뮬레이션)
    python scripts/live_ops.py --feed sim --symbol AAPL --metrics-port 9108 --audit runs/audit.jsonl \
        --report-dir runs/reports --db runs/live.sqlite --heartbeat 5 --max-runtime 30

    # 실시간(거래소/브로커 — websockets/계정 필요)
    python scripts/live_ops.py --feed binance --symbol BTCUSDT --metrics-port 9108 \
        --audit runs/audit.jsonl --report-dir runs/reports --db runs/live.sqlite
    python scripts/live_ops.py --feed upbit  --symbol KRW-BTC
    python scripts/live_ops.py --feed alpaca --symbol AAPL    # ALPACA_API_KEY/SECRET_KEY env
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _install_signal_handlers(runner) -> None:
    """SIGTERM/SIGINT → runner.request_stop()(메인 스레드에서만 가능). 미지원 플랫폼은 무시."""
    import signal

    def _handler(signum, _frame):
        print(json.dumps({"event": "signal", "signal": int(signum), "action": "graceful_stop"}), flush=True)
        runner.request_stop()

    for name in ("SIGTERM", "SIGINT"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):  # 비메인 스레드/미지원
            pass


def _build_feed_factory(args):
    from daytrade.feed.alpaca import AlpacaFeed
    from daytrade.feed.binance import BinanceFeed
    from daytrade.feed.replay import CsvReplayFeed
    from daytrade.feed.simulated import SimulatedFeed
    from daytrade.feed.upbit import UpbitFeed

    feed = args.feed
    n = args.session_ticks
    if feed == "binance":
        return lambda: BinanceFeed(symbol=args.symbol, depth=args.depth, max_ticks=n)
    if feed == "upbit":
        return lambda: UpbitFeed(symbol=args.symbol, depth=args.depth, max_ticks=n)
    if feed == "alpaca":
        return lambda: AlpacaFeed(symbol=args.symbol, max_ticks=n)
    if feed == "csv":
        return lambda: CsvReplayFeed(args.csv)
    return lambda: SimulatedFeed(symbol=args.symbol, n_ticks=n, depth=args.depth, seed=args.seed)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="daytrade-ai 라이브 상시운영 러너(무중단 페이퍼봇)")
    p.add_argument("--feed", choices=["sim", "csv", "binance", "upbit", "alpaca"], default="sim")
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--csv", help="--feed csv 일 때 CSV 경로")
    p.add_argument("--depth", type=int, default=10)
    p.add_argument("--cash", type=float, default=1_000_000.0)
    p.add_argument("--ai-threshold", dest="ai_threshold", type=float, default=0.9)
    p.add_argument("--no-ai", action="store_true")
    p.add_argument("--model", help="추론 모델 경로(*.json/*.onnx)")
    p.add_argument("--model-dir", dest="model_dir",
                   help="current.json 감시 디렉터리(M7 핫스왑 결선 — 시동·세션 경계마다 최신 승격 모델 로드)")
    p.add_argument("--rollback", action="store_true",
                   help="핫스왑 후 라이브 낙폭 악화 시 직전 버전 자동 롤백(M7-L)")
    p.add_argument("--rollback-drawdown", dest="rollback_drawdown", type=float, default=1.0,
                   help="롤백 트리거 낙폭(%) — 스왑 이후 기준")
    p.add_argument("--rollback-window", dest="rollback_window", type=float, default=300.0,
                   help="스왑 후 KPI 감시 윈도(초)")
    p.add_argument("--session-ticks", dest="session_ticks", type=int, default=2000,
                   help="라이브 외 피드의 세션당 틱(재연결 시뮬레이션). 라이브는 max_ticks 로 작용")
    p.add_argument("--heartbeat", type=float, default=15.0, help="heartbeat 주기(초)")
    p.add_argument("--reconnect-base", dest="reconnect_base", type=float, default=1.0)
    p.add_argument("--reconnect-max", dest="reconnect_max", type=float, default=30.0)
    p.add_argument("--max-reconnects", dest="max_reconnects", type=int, default=0, help="0=무제한")
    p.add_argument("--max-runtime", dest="max_runtime", type=float, default=0.0, help="초, 0=무제한")
    p.add_argument("--max-ticks", dest="max_ticks", type=int, default=0, help="0=무제한")
    p.add_argument("--db", default=":memory:", help="sqlite 영속 경로")
    p.add_argument("--audit", help="해시체인 감사로그(JSONL) 경로")
    p.add_argument("--metrics-port", dest="metrics_port", type=int, default=0, help="라이브 /metrics 포트(0=비활성)")
    p.add_argument("--metrics-host", dest="metrics_host", default="127.0.0.1",
                   help="/metrics 바인드 호스트(컨테이너/k8s 노출 시 0.0.0.0)")
    p.add_argument("--ready-staleness", dest="ready_staleness", type=float, default=10.0,
                   help="/readyz 가 ready 로 판정하는 최대 틱 신선도(초)")
    p.add_argument("--report-dir", dest="report_dir", help="일일 리포트 저장 디렉터리")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    from daytrade.config import SignalConfig, TradingConfig, TradingMode
    from daytrade.execution import TradeStore
    from daytrade.monitoring import AlertEngine, AuditLog, LiveMetrics, MetricsServer
    from daytrade.ops import LiveRunner, RunnerConfig
    from daytrade.pipeline import TradingPipeline
    from daytrade.types import Fill, Order, OrderSide

    config = TradingConfig(
        mode=TradingMode.PAPER,
        symbols=(args.symbol,),
        starting_cash=args.cash,
        signal=SignalConfig(depth=args.depth, ai_buy_threshold=args.ai_threshold,
                            ai_sell_threshold=args.ai_threshold, use_ai=not args.no_ai),
        seed=args.seed,
    )

    store = TradeStore(args.db)
    run_id = store.start_run(mode=config.mode.value, symbol=args.symbol,
                             started_at=datetime.now(timezone.utc).isoformat(), note="live_ops")
    audit = AuditLog(args.audit) if args.audit else None

    def on_event(ev: dict) -> None:
        if ev.get("event") != "fill":
            return
        order = Order(symbol=ev["symbol"], side=OrderSide(ev["side"]), qty=ev["qty"], ts_ns=0,
                      client_order_id=f"live-{run_id}-{ev['symbol']}")
        store.record_fill(Fill(order=order, filled_qty=ev["qty"], avg_price=ev["price"],
                               ts_ns=0, slippage=ev["slippage"], status="filled"), run_id=run_id)
        if audit:
            audit.append("fill", symbol=ev["symbol"], side=ev["side"], qty=ev["qty"],
                         price=ev["price"], slippage=ev["slippage"])

    pipeline = TradingPipeline(config, model_path=args.model, on_event=on_event)

    live = LiveMetrics(symbol=args.symbol, mode=pipeline.effective_mode.value)

    def on_heartbeat(hb: dict) -> None:
        print(json.dumps({"event": "heartbeat", **hb}, ensure_ascii=False), flush=True)

    def on_report(rep) -> None:
        print(json.dumps({"event": "daily_report", **rep.as_dict()}, ensure_ascii=False), flush=True)

    def on_reload(info: dict) -> None:
        ev = info.pop("event", "model_reload")
        print(json.dumps({"event": ev, **info}, ensure_ascii=False), flush=True)

    rollback_fn = None
    if args.rollback and args.model_dir:
        from daytrade.ops import auto_rollback
        # 롤백 + 나쁜 시그니처 블랙리스트(쿨다운) + 롤백 기록(연속 롤백 → 재학습 일시중지 근거).
        rollback_fn = lambda: auto_rollback(args.model_dir)  # noqa: E731

    runner = LiveRunner(
        pipeline,
        feed_factory=_build_feed_factory(args),
        config=RunnerConfig(
            symbol=args.symbol, heartbeat_sec=args.heartbeat,
            reconnect_base_sec=args.reconnect_base, reconnect_max_sec=args.reconnect_max,
            max_reconnects=args.max_reconnects, max_runtime_sec=args.max_runtime,
            max_ticks=args.max_ticks, report_dir=args.report_dir, model_dir=args.model_dir,
            rollback_enabled=args.rollback, rollback_drawdown_pct=args.rollback_drawdown,
            rollback_window_sec=args.rollback_window,
        ),
        audit=audit, alert_engine=AlertEngine(), live=live,
        on_heartbeat=on_heartbeat, on_report=on_report, on_reload=on_reload,
        rollback_fn=rollback_fn,
    )

    # /metrics + /healthz(liveness) + /readyz(readiness: 서킷브레이커·틱 신선도).
    server = None
    if args.metrics_port:
        server = MetricsServer(
            lambda: live.registry, host=args.metrics_host, port=args.metrics_port,
            ready_provider=lambda: runner.is_healthy(max_staleness_sec=args.ready_staleness),
        ).start()
        print(json.dumps({"event": "metrics_serving", "url": server.url}), flush=True)

    # 그레이스풀 셧다운: SIGTERM/SIGINT → 안전 종료 요청(당일 리포트·run_end 감사 후 정상 종료).
    _install_signal_handlers(runner)

    try:
        summary = runner.run()
    finally:
        if server is not None:
            server.stop()
        store.record_equity(pipeline.metrics.ticks, pipeline.portfolio.equity({args.symbol: 0.0}), run_id=run_id)
        store.close()

    out = {"event": "run_end", **summary,
           "audit_verified": (audit.verify().ok if audit else None)}
    print(json.dumps(out, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
