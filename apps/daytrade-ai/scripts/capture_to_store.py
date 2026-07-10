"""실데이터 장기 캡처 → 일별 바이너리 틱 스토어 적재(증설 전 데이터 축적용).

라이브 피드(Binance/Upbit/Alpaca) 또는 합성(sim)을 일별 `.dts` 파일로 무손실 기록한다. 피드가
끊기면 지수 백오프로 자동 재연결하며(같은 날 파일에 이어쓰기), SIGINT/SIGTERM 으로 안전 종료한다.

예:
    python scripts/capture_to_store.py --source binance --symbol BTCUSDT --out-dir data/ticks --max-ticks 100000
    python scripts/capture_to_store.py --source sim --symbol AAPL --out-dir data/ticks --max-ticks 5000
"""
from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from daytrade.storage import RollingTickStoreWriter  # noqa: E402


def _make_feed(args):
    if args.source == "binance":
        from daytrade.feed.binance import BinanceFeed
        return BinanceFeed(symbol=args.symbol, depth=args.depth, max_ticks=args.max_ticks)
    if args.source == "upbit":
        from daytrade.feed.upbit import UpbitFeed
        return UpbitFeed(symbol=args.symbol, depth=args.depth, max_ticks=args.max_ticks)
    if args.source == "alpaca":
        from daytrade.feed.alpaca import AlpacaFeed
        return AlpacaFeed(symbol=args.symbol, max_ticks=args.max_ticks)
    from daytrade.feed.simulated import SimulatedFeed
    return SimulatedFeed(symbol=args.symbol, n_ticks=args.max_ticks or 5000, depth=args.depth,
                         seed=args.seed)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="라이브 피드 → 일별 틱 스토어 캡처")
    p.add_argument("--source", choices=["binance", "upbit", "alpaca", "sim"], default="binance")
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--depth", type=int, default=10)
    p.add_argument("--out-dir", dest="out_dir", required=True, help="`.dts` 저장 디렉터리")
    p.add_argument("--prefix", default="ticks")
    p.add_argument("--max-ticks", dest="max_ticks", type=int, default=0, help="총 틱 한도(0=무제한)")
    p.add_argument("--duration-sec", dest="duration_sec", type=float, default=0.0,
                   help="총 가동 시간 한도(0=무제한)")
    p.add_argument("--reconnect-base", dest="reconnect_base", type=float, default=1.0)
    p.add_argument("--reconnect-max", dest="reconnect_max", type=float, default=30.0)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    stop = {"flag": False}

    def _handle(signum, frame):  # noqa: ARG001
        stop["flag"] = True
        print(f"\n[signal] {signum} 수신 — 안전 종료합니다…", flush=True)

    for s in ("SIGINT", "SIGTERM"):
        if hasattr(signal, s):
            try:
                signal.signal(getattr(signal, s), _handle)
            except (ValueError, OSError):
                pass

    writer = RollingTickStoreWriter(args.out_dir, args.symbol, depth=args.depth, prefix=args.prefix)
    start = time.time()
    total = 0
    reconnects = 0
    consecutive = 0

    print(f"[capture] source={args.source} symbol={args.symbol} -> {args.out_dir}", flush=True)
    try:
        while not stop["flag"]:
            if args.max_ticks and total >= args.max_ticks:
                break
            if args.duration_sec and (time.time() - start) >= args.duration_sec:
                break
            got = False
            try:
                feed = _make_feed(args)
                for tick in feed.ticks():
                    writer.append(tick)
                    total += 1
                    got = True
                    if total % 1000 == 0:
                        print(f"[capture] {total} ticks  files={len(writer.files)}", flush=True)
                    if stop["flag"] or (args.max_ticks and total >= args.max_ticks):
                        break
                    if args.duration_sec and (time.time() - start) >= args.duration_sec:
                        break
            except ModuleNotFoundError:
                print("[ERR] 라이브 캡처에는 'websockets' 패키지가 필요합니다: pip install websockets")
                return 2
            except Exception as exc:  # noqa: BLE001 — 끊김은 재연결로 흡수
                print(f"[capture] 피드 오류({type(exc).__name__}: {str(exc)[:120]}) — 재연결", flush=True)
            if stop["flag"]:
                break
            reconnects += 1
            consecutive = 0 if got else consecutive + 1
            backoff = min(args.reconnect_base * (2 ** max(0, consecutive - 1)), args.reconnect_max)
            time.sleep(backoff)
    finally:
        writer.close()

    print(f"[capture] 종료: total={total} ticks, files={len(writer.files)}, reconnects={reconnects}")
    for f in writer.files:
        print(f"  - {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
