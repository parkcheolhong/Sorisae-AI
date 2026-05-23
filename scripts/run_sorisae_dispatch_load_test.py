import argparse
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import requests

BASE_URL = "http://127.0.0.1:8000"
LOGIN_PATH = "/api/auth/login"
DISPATCH_PATH = "/api/marketplace/sorisae/dispatch"
CORE_ENGINES = [
    "voice_movie",
    "detective_dashboard",
    "integrated_dashboard",
    "movie_server",
    "master",
    "shopping",
]


@dataclass
class DispatchResult:
    engine: str
    ok: bool
    http_status: int
    latency_ms: float
    status: str
    error_code: str
    source: str


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    rank = (len(values) - 1) * p
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return values[lower]
    weight = rank - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def login(
    session: requests.Session,
    username: str,
    password: str,
    timeout_sec: float,
    max_attempts: int = 20,
    retry_sleep_sec: float = 1.0,
) -> str:
    last_exc: Exception | None = None
    for _ in range(max_attempts):
        try:
            resp = session.post(
                f"{BASE_URL}{LOGIN_PATH}",
                data={"username": username, "password": password},
                timeout=timeout_sec,
            )
            resp.raise_for_status()
            body = resp.json()
            return body["access_token"]
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(retry_sleep_sec)

    raise RuntimeError("login failed after retries") from last_exc


def single_dispatch(
    token: str,
    engine: str,
    req_index: int,
    timeout_sec: float,
    round_label: str,
) -> DispatchResult:
    headers = {"Authorization": f"Bearer {token}"}
    payload: dict[str, Any] = {
        "engine_type": engine,
        "context": {
            "load_test": True,
            "round": round_label,
            "req_index": req_index,
            "ts": time.time(),
        },
        "entry_fn": "main",
        "use_module_adapter": True,
        "adapter_entry_candidates": ["run", "execute", "start"],
    }

    started = time.perf_counter()
    try:
        resp = requests.post(
            f"{BASE_URL}{DISPATCH_PATH}",
            headers=headers,
            json=payload,
            timeout=timeout_sec,
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        body = resp.json()

        if resp.status_code >= 400:
            detail = body.get("detail", {}) if isinstance(body, dict) else {}
            return DispatchResult(
                engine=engine,
                ok=False,
                http_status=resp.status_code,
                latency_ms=latency_ms,
                status=str(detail.get("status") or "http_error"),
                error_code=str(detail.get("error_code") or "HTTP_ERROR"),
                source=str(detail.get("source") or "http_layer"),
            )

        status = str(body.get("status") or "")
        error_code = str(body.get("error_code") or "")
        source = str(body.get("source") or "")
        is_ok = resp.status_code == 200 and status == "flask_server_ok"
        return DispatchResult(
            engine=engine,
            ok=is_ok,
            http_status=resp.status_code,
            latency_ms=latency_ms,
            status=status,
            error_code=error_code,
            source=source,
        )
    except requests.Timeout:
        latency_ms = (time.perf_counter() - started) * 1000.0
        return DispatchResult(
            engine=engine,
            ok=False,
            http_status=0,
            latency_ms=latency_ms,
            status="client_timeout",
            error_code="CLIENT_TIMEOUT",
            source="load_tester",
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - started) * 1000.0
        return DispatchResult(
            engine=engine,
            ok=False,
            http_status=0,
            latency_ms=latency_ms,
            status="client_error",
            error_code=type(exc).__name__,
            source="load_tester",
        )


def run_round(
    *,
    round_label: str,
    username: str,
    password: str,
    requests_per_engine: int,
    concurrency: int,
    timeout_sec: float,
) -> dict[str, Any]:
    session = requests.Session()
    token = login(session, username, password, timeout_sec)

    all_results: list[DispatchResult] = []
    futures = []
    planned = []
    for engine in CORE_ENGINES:
        for idx in range(requests_per_engine):
            planned.append((engine, idx))

    started_at = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for engine, idx in planned:
            futures.append(
                executor.submit(single_dispatch, token, engine, idx, timeout_sec, round_label)
            )

        for future in as_completed(futures):
            all_results.append(future.result())
    elapsed_sec = time.perf_counter() - started_at

    total = len(all_results)
    ok_count = sum(1 for r in all_results if r.ok)
    fail_count = total - ok_count
    latencies = sorted(r.latency_ms for r in all_results)

    by_engine: dict[str, dict[str, Any]] = {}
    error_breakdown = Counter()
    for engine in CORE_ENGINES:
        engine_rows = [r for r in all_results if r.engine == engine]
        engine_latencies = sorted(r.latency_ms for r in engine_rows)
        engine_ok = sum(1 for r in engine_rows if r.ok)
        engine_total = len(engine_rows)
        engine_fail = engine_total - engine_ok
        by_engine[engine] = {
            "total": engine_total,
            "ok": engine_ok,
            "fail": engine_fail,
            "error_rate": round((engine_fail / engine_total) * 100.0, 3) if engine_total else 0.0,
            "p95_ms": round(percentile(engine_latencies, 0.95), 3) if engine_latencies else 0.0,
            "max_ms": round(max(engine_latencies), 3) if engine_latencies else 0.0,
            "avg_ms": round(statistics.mean(engine_latencies), 3) if engine_latencies else 0.0,
        }

    for row in all_results:
        if row.ok:
            continue
        key = f"{row.status}|{row.error_code}|{row.source}|http={row.http_status}"
        error_breakdown[key] += 1

    return {
        "round": round_label,
        "requests_per_engine": requests_per_engine,
        "engines": CORE_ENGINES,
        "concurrency": concurrency,
        "timeout_sec": timeout_sec,
        "total_requests": total,
        "ok": ok_count,
        "fail": fail_count,
        "error_rate": round((fail_count / total) * 100.0, 3) if total else 0.0,
        "throughput_rps": round(total / elapsed_sec, 3) if elapsed_sec > 0 else 0.0,
        "latency_ms": {
            "avg": round(statistics.mean(latencies), 3) if latencies else 0.0,
            "p50": round(percentile(latencies, 0.50), 3) if latencies else 0.0,
            "p95": round(percentile(latencies, 0.95), 3) if latencies else 0.0,
            "p99": round(percentile(latencies, 0.99), 3) if latencies else 0.0,
            "max": round(max(latencies), 3) if latencies else 0.0,
        },
        "by_engine": by_engine,
        "error_breakdown": dict(error_breakdown),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sorisae dispatch load test runner")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--requests-per-engine", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--timeout-sec", type=float, default=12.0)
    parser.add_argument("--output", default="")
    parser.add_argument("--round-label", default="R1")
    args = parser.parse_args()

    report = run_round(
        round_label=args.round_label,
        username=args.username,
        password=args.password,
        requests_per_engine=args.requests_per_engine,
        concurrency=args.concurrency,
        timeout_sec=args.timeout_sec,
    )

    print(json.dumps(report, ensure_ascii=True, indent=2))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fp:
            json.dump(report, fp, ensure_ascii=True, indent=2)


if __name__ == "__main__":
    main()
