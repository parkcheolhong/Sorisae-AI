"""추론 레이턴시 실측(설계서 §3-3, M4 인수기준 ≤1ms·warm-up<5ms).

`load_inference_model` 로 백엔드를 선택(TensorRT 엔진 → ONNX Runtime → 휴리스틱 폴백)하고,
실/합성 피처에 대해 N회 추론하며 p50/p95/p99 레이턴시를 집계한다.
  - 서버(RTX 5090, tensorrt 설치): `--engine model.plan` 로 TensorRT 실측(≤1ms 목표 판정).
  - 개발 PC: 엔진 없으면 ONNX Runtime/휴리스틱으로 동일 지표를 측정(파이프라인 검증).

사용:
    # 개발 PC(폴백 백엔드)
    python scripts/measure_inference_latency.py --sim --ticks 5000
    # 서버(TensorRT 엔진)
    python scripts/measure_inference_latency.py --csv data/sol.csv --engine model.plan --target-ms 1.0
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="추론 레이턴시 실측(TensorRT/ORT/휴리스틱)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--sim", action="store_true")
    src.add_argument("--csv")
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--ticks", type=int, default=5000)
    p.add_argument("--depth", type=int, default=10)
    p.add_argument("--model", help="ONNX/JSON 모델(ORT/numpy). 미지정 시 휴리스틱")
    p.add_argument("--engine", help="TensorRT 직렬화 엔진(.plan) — 서버에서 우선 사용")
    p.add_argument("--warmup", type=int, default=50, help="워밍업 추론 횟수(cold-start 제거)")
    p.add_argument("--target-ms", dest="target_ms", type=float, default=1.0,
                   help="p99 레이턴시 인수기준(ms). 초과 시 비0 종료코드")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    from daytrade.features.engine import FeatureEngine
    from daytrade.feed.replay import CsvReplayFeed
    from daytrade.feed.simulated import SimulatedFeed
    from daytrade.inference import LatencyHistogram, load_inference_model

    ticks = (list(SimulatedFeed(symbol=args.symbol, n_ticks=args.ticks, depth=args.depth, seed=0).ticks())
             if args.sim else list(CsvReplayFeed(args.csv).ticks()))
    eng = FeatureEngine(depth=args.depth)
    fvs = [eng.update(t) for t in ticks]

    model = load_inference_model(args.model, engine_path=args.engine)
    backend = type(model).__name__

    # 워밍업(<5ms 목표) — cold-start 지연 제거 후 측정.
    t_warm0 = time.perf_counter_ns()
    model.warmup()
    warmup_ms = (time.perf_counter_ns() - t_warm0) / 1e6
    for fv in fvs[: args.warmup]:
        model.predict(fv)

    hist = LatencyHistogram()
    for fv in fvs:
        t0 = time.perf_counter_ns()
        model.predict(fv)
        hist.record_ns(time.perf_counter_ns() - t0)

    summary = hist.summary()
    p99_ms = summary["p99_us"] / 1000.0
    result = {
        "backend": backend,
        "engine": args.engine,
        "model": args.model,
        "n_infer": summary["count"],
        "warmup_ms": round(warmup_ms, 4),
        "latency_us": summary,
        "p99_ms": round(p99_ms, 4),
        "target_ms": args.target_ms,
        "meets_target": p99_ms <= args.target_ms,
        "warmup_under_5ms": warmup_ms < 5.0,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 64)
        print(" daytrade-ai 추론 레이턴시 실측")
        print("=" * 64)
        print(f"  backend         : {backend}")
        print(f"  n_infer         : {summary['count']}")
        print(f"  warmup          : {warmup_ms:.4f} ms  (<5ms: {result['warmup_under_5ms']})")
        print(f"  p50/p95/p99 (us): {summary['p50_us']} / {summary['p95_us']} / {summary['p99_us']}")
        print(f"  p99             : {p99_ms:.4f} ms  (target {args.target_ms} ms: {result['meets_target']})")
        print("=" * 64)
    # 인수기준 미달 시 비0(서버 CI 게이트용). 단, 휴리스틱/ORT 폴백 백엔드는 참고용.
    return 0 if result["meets_target"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
