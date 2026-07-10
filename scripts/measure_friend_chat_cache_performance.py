from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
API_PATH = "/api/llm/voice/friend-chat"


@dataclass
class CallResult:
    status: int
    elapsed_ms: float
    total_ms: Optional[float]
    llm_ms: Optional[float]
    cache_hit: Optional[bool]
    ok: bool
    response_text_len: int


def _post_json(url: str, payload: dict[str, Any], timeout_sec: float) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            status = int(resp.status)
            body = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
            return status, body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw}
        return int(exc.code), body
    except Exception as exc:
        return 599, {"error": str(exc)}


def _call_friend_chat(base_url: str, payload: dict[str, Any], timeout_sec: float) -> CallResult:
    started = time.perf_counter()
    status, body = _post_json(base_url.rstrip("/") + API_PATH, payload, timeout_sec)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    timing = body.get("timing_ms") if isinstance(body, dict) else None
    total_ms: Optional[float] = None
    llm_ms: Optional[float] = None
    if isinstance(timing, dict):
        try:
            if timing.get("total") is not None:
                total_ms = float(timing.get("total"))
        except (TypeError, ValueError):
            total_ms = None
        try:
            if timing.get("llm") is not None:
                llm_ms = float(timing.get("llm"))
        except (TypeError, ValueError):
            llm_ms = None

    response_text = str(body.get("response_text") or "") if isinstance(body, dict) else ""
    cache_hit: Optional[bool] = None
    if isinstance(body, dict) and body.get("cache_hit") is not None:
        cache_hit = bool(body.get("cache_hit"))
    return CallResult(
        status=status,
        elapsed_ms=elapsed_ms,
        total_ms=total_ms,
        llm_ms=llm_ms,
        cache_hit=cache_hit,
        ok=(status == 200),
        response_text_len=len(response_text),
    )


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = int(round((len(sorted_values) - 1) * q))
    return float(sorted_values[max(0, min(idx, len(sorted_values) - 1))])


def _summarize(results: list[CallResult]) -> dict[str, float]:
    elapsed = [r.elapsed_ms for r in results if r.ok]
    totals = [r.total_ms for r in results if r.ok and r.total_ms is not None]
    llm = [r.llm_ms for r in results if r.ok and r.llm_ms is not None]
    ok_count = sum(1 for r in results if r.ok)
    err_count = len(results) - ok_count

    cache_hits = 0
    cache_miss = 0
    for r in results:
        if not r.ok:
            continue
        if r.cache_hit is True:
            cache_hits += 1
            continue
        if r.cache_hit is False:
            cache_miss += 1
            continue
        if r.llm_ms is None:
            cache_hits += 1
        else:
            cache_miss += 1

    total_for_rate = cache_hits + cache_miss
    hit_rate = (cache_hits / total_for_rate) * 100.0 if total_for_rate else 0.0
    elapsed_sum_ms = sum(r.elapsed_ms for r in results)
    throughput_per_min = (ok_count / elapsed_sum_ms) * 60_000.0 if elapsed_sum_ms > 0 else 0.0
    error_rate = (err_count / len(results)) * 100.0 if results else 0.0

    return {
        "count": float(len(results)),
        "ok": float(ok_count),
        "err": float(err_count),
        "error_rate_pct": error_rate,
        "elapsed_avg_ms": statistics.fmean(elapsed) if elapsed else 0.0,
        "elapsed_p95_ms": _percentile(elapsed, 0.95),
        "timing_total_avg_ms": statistics.fmean(totals) if totals else 0.0,
        "timing_total_p95_ms": _percentile(totals, 0.95),
        "timing_llm_avg_ms": statistics.fmean(llm) if llm else 0.0,
        "timing_llm_p95_ms": _percentile(llm, 0.95),
        "cache_hits": float(cache_hits),
        "cache_miss": float(cache_miss),
        "cache_hit_rate_pct": hit_rate,
        "throughput_per_min": throughput_per_min,
    }


def _print_summary(title: str, data: dict[str, float]) -> None:
    print(f"\n=== {title} ===")
    print(f"requests        : {int(data['count'])}")
    print(f"ok/err          : {int(data['ok'])}/{int(data['err'])} (error {data['error_rate_pct']:.2f}%)")
    print(f"elapsed avg/p95 : {data['elapsed_avg_ms']:.1f}ms / {data['elapsed_p95_ms']:.1f}ms")
    print(f"timing avg/p95  : {data['timing_total_avg_ms']:.1f}ms / {data['timing_total_p95_ms']:.1f}ms")
    print(f"llm avg/p95     : {data['timing_llm_avg_ms']:.1f}ms / {data['timing_llm_p95_ms']:.1f}ms")
    print(f"cache hit/miss  : {int(data['cache_hits'])}/{int(data['cache_miss'])} ({data['cache_hit_rate_pct']:.1f}%)")
    print(f"throughput/min  : {data['throughput_per_min']:.1f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure friend-chat cache hit/miss performance")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--miss-runs", type=int, default=20)
    parser.add_argument("--hit-runs", type=int, default=30)
    parser.add_argument("--target-hit", type=float, default=75.0)
    parser.add_argument("--target-p95", type=float, default=520.0)
    args = parser.parse_args()

    base_payload = {
        "transcript": "오늘 기분이 좀 다운됐어. 짧게 위로해줘.",
        "language": "ko",
        "tts": False,
        "region_hint": "Fukuoka",
        "country_code": "JP",
        "latitude": 33.5902,
        "longitude": 130.4017,
        "accuracy_m": 30,
        "conversation": [],
        "web_search": False,
    }

    print("[1/3] miss phase: unique transcript to force cache misses")
    miss_results: list[CallResult] = []
    for i in range(max(1, args.miss_runs)):
        payload = dict(base_payload)
        payload["transcript"] = f"{base_payload['transcript']} (miss-{i}-{int(time.time())})"
        miss_results.append(_call_friend_chat(args.base_url, payload, args.timeout))

    print("[2/3] warm + hit phase: fixed transcript to maximize cache hits")
    hit_results: list[CallResult] = []
    warm_payload = dict(base_payload)
    _ = _call_friend_chat(args.base_url, warm_payload, args.timeout)
    for _i in range(max(1, args.hit_runs)):
        hit_results.append(_call_friend_chat(args.base_url, warm_payload, args.timeout))

    print("[3/3] summarize")
    miss_summary = _summarize(miss_results)
    hit_summary = _summarize(hit_results)
    combined_summary = _summarize(miss_results + hit_results)

    _print_summary("MISS PHASE", miss_summary)
    _print_summary("HIT PHASE", hit_summary)
    _print_summary("COMBINED", combined_summary)

    hit_rate = combined_summary["cache_hit_rate_pct"]
    p95 = combined_summary["timing_total_p95_ms"]
    steady_hit_rate = hit_summary["cache_hit_rate_pct"]
    steady_p95 = hit_summary["timing_total_p95_ms"]
    print("\n=== TARGET CHECK ===")
    print(f"cache_hit_rate target {args.target_hit:.1f}% : {'PASS' if hit_rate >= args.target_hit else 'FAIL'} ({hit_rate:.1f}%)")
    print(f"p95_latency target <= {args.target_p95:.1f}ms : {'PASS' if p95 <= args.target_p95 else 'FAIL'} ({p95:.1f}ms)")
    print("\n=== TARGET CHECK (STEADY STATE / HIT PHASE) ===")
    print(
        f"cache_hit_rate target {args.target_hit:.1f}% : "
        f"{'PASS' if steady_hit_rate >= args.target_hit else 'FAIL'} ({steady_hit_rate:.1f}%)"
    )
    print(
        f"p95_latency target <= {args.target_p95:.1f}ms : "
        f"{'PASS' if steady_p95 <= args.target_p95 else 'FAIL'} ({steady_p95:.1f}ms)"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
