#!/usr/bin/env python3
"""
24시간 capabilities summary latency 모니터
- 주기적으로 /api/admin/orchestrator/capabilities/summary 지연시간을 수집
- JSONL 로그 + 최종 요약 JSON 저장

사용 예시:
python scripts/monitor_capabilities_summary_latency_24h.py \
  --base-url http://127.0.0.1:8000 \
  --username ui.admin.round@devanalysis.local \
  --password RoundUi!20260426 \
  --interval-sec 60
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


LOGIN_PATH_DEFAULT = "/api/auth/login"
SUMMARY_PATH_DEFAULT = "/api/admin/orchestrator/capabilities/summary"


@dataclass
class Sample:
    timestamp_utc: str
    latency_ms: float | None
    status_code: int | None
    ok: bool
    error: str | None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = int(round((len(sorted_values) - 1) * p))
    idx = max(0, min(idx, len(sorted_values) - 1))
    return sorted_values[idx]


def post_form_json(url: str, form_data: dict[str, str], timeout_sec: float) -> tuple[int, dict[str, Any]]:
    body = parse.urlencode(form_data).encode("utf-8")
    req = request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with request.urlopen(req, timeout=timeout_sec) as resp:
        payload = resp.read().decode("utf-8")
        return resp.status, json.loads(payload)


def get_with_bearer(url: str, token: str, timeout_sec: float) -> tuple[int, bytes]:
    req = request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    with request.urlopen(req, timeout=timeout_sec) as resp:
        return resp.status, resp.read()


def login(base_url: str, login_path: str, username: str, password: str, timeout_sec: float) -> str:
    login_url = f"{base_url.rstrip('/')}{login_path}"
    status, payload = post_form_json(login_url, {"username": username, "password": password}, timeout_sec)
    if status < 200 or status >= 300:
        raise RuntimeError(f"login failed: status={status}")
    token = payload.get("access_token") or payload.get("token")
    if not token:
        raise RuntimeError("login succeeded but token is missing")
    return token


def collect_once(base_url: str, summary_path: str, token: str, timeout_sec: float) -> Sample:
    url = f"{base_url.rstrip('/')}{summary_path}"
    t0 = time.perf_counter()
    try:
        status, _ = get_with_bearer(url, token, timeout_sec)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return Sample(
            timestamp_utc=utc_now_iso(),
            latency_ms=dt_ms,
            status_code=status,
            ok=(200 <= status < 300),
            error=None if 200 <= status < 300 else f"http_status_{status}",
        )
    except error.HTTPError as e:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return Sample(
            timestamp_utc=utc_now_iso(),
            latency_ms=dt_ms,
            status_code=e.code,
            ok=False,
            error=f"http_error_{e.code}",
        )
    except Exception as e:  # noqa: BLE001
        return Sample(
            timestamp_utc=utc_now_iso(),
            latency_ms=None,
            status_code=None,
            ok=False,
            error=f"exception:{type(e).__name__}:{e}",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="24h capabilities summary latency monitor")
    parser.add_argument("--base-url", default=os.getenv("CAP_MON_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--login-path", default=os.getenv("CAP_MON_LOGIN_PATH", LOGIN_PATH_DEFAULT))
    parser.add_argument("--summary-path", default=os.getenv("CAP_MON_SUMMARY_PATH", SUMMARY_PATH_DEFAULT))
    parser.add_argument("--username", default=os.getenv("CAP_MON_USERNAME"))
    parser.add_argument("--password", default=os.getenv("CAP_MON_PASSWORD"))
    parser.add_argument("--duration-hours", type=float, default=float(os.getenv("CAP_MON_DURATION_HOURS", "24")))
    parser.add_argument("--interval-sec", type=float, default=float(os.getenv("CAP_MON_INTERVAL_SEC", "60")))
    parser.add_argument("--timeout-sec", type=float, default=float(os.getenv("CAP_MON_TIMEOUT_SEC", "20")))
    parser.add_argument("--output-dir", default=os.getenv("CAP_MON_OUTPUT_DIR", "reports/capabilities-latency"))
    parser.add_argument("--print-every", type=int, default=int(os.getenv("CAP_MON_PRINT_EVERY", "10")))
    args = parser.parse_args()

    if not args.username or not args.password:
        raise SystemExit("username/password is required (args or env CAP_MON_USERNAME/CAP_MON_PASSWORD)")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = out_dir / f"cap_summary_latency_{session_id}.jsonl"
    summary_path = out_dir / f"cap_summary_latency_{session_id}_summary.json"

    print(f"[monitor] start session={session_id}")
    print(f"[monitor] output={jsonl_path}")

    token = login(args.base_url, args.login_path, args.username, args.password, args.timeout_sec)
    end_at = datetime.now(timezone.utc) + timedelta(hours=args.duration_hours)

    samples: list[Sample] = []
    count = 0

    with jsonl_path.open("w", encoding="utf-8") as f:
        while datetime.now(timezone.utc) < end_at:
            count += 1
            sample = collect_once(args.base_url, args.summary_path, token, args.timeout_sec)

            if sample.status_code == 401:
                # 토큰 만료 시 1회 재로그인 후 재시도
                try:
                    token = login(args.base_url, args.login_path, args.username, args.password, args.timeout_sec)
                    sample = collect_once(args.base_url, args.summary_path, token, args.timeout_sec)
                except Exception as e:  # noqa: BLE001
                    sample = Sample(
                        timestamp_utc=utc_now_iso(),
                        latency_ms=None,
                        status_code=None,
                        ok=False,
                        error=f"relogin_failed:{type(e).__name__}:{e}",
                    )

            samples.append(sample)
            f.write(json.dumps(asdict(sample), ensure_ascii=False) + "\n")
            f.flush()

            if count % max(1, args.print_every) == 0:
                latencies = sorted(s.latency_ms for s in samples if s.latency_ms is not None)
                ok_count = sum(1 for s in samples if s.ok)
                err_count = len(samples) - ok_count
                if latencies:
                    print(
                        "[monitor]"
                        f" count={len(samples)} ok={ok_count} err={err_count}"
                        f" p50={statistics.median(latencies):.1f}ms"
                        f" p95={percentile(latencies, 0.95):.1f}ms"
                        f" p99={percentile(latencies, 0.99):.1f}ms"
                        f" max={max(latencies):.1f}ms"
                    )
                else:
                    print(f"[monitor] count={len(samples)} ok={ok_count} err={err_count} (no latency samples)")

            time.sleep(max(0.1, args.interval_sec))

    latencies = sorted(s.latency_ms for s in samples if s.latency_ms is not None)
    ok_count = sum(1 for s in samples if s.ok)
    err_count = len(samples) - ok_count

    summary: dict[str, Any] = {
        "session_id": session_id,
        "started_at_utc": samples[0].timestamp_utc if samples else utc_now_iso(),
        "ended_at_utc": utc_now_iso(),
        "base_url": args.base_url,
        "summary_path": args.summary_path,
        "duration_hours": args.duration_hours,
        "interval_sec": args.interval_sec,
        "timeout_sec": args.timeout_sec,
        "total_samples": len(samples),
        "ok_samples": ok_count,
        "error_samples": err_count,
        "error_rate": (err_count / len(samples)) if samples else 0.0,
    }

    if latencies:
        summary.update(
            {
                "min_ms": min(latencies),
                "p50_ms": statistics.median(latencies),
                "p95_ms": percentile(latencies, 0.95),
                "p99_ms": percentile(latencies, 0.99),
                "max_ms": max(latencies),
                "avg_ms": sum(latencies) / len(latencies),
            }
        )

    summary["recent_errors"] = [asdict(s) for s in samples if not s.ok][-20:]

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("[monitor] done")
    print(f"[monitor] summary={summary_path}")
    if latencies:
        print(
            "[monitor]"
            f" count={len(samples)} ok={ok_count} err={err_count}"
            f" p50={summary['p50_ms']:.1f}ms p95={summary['p95_ms']:.1f}ms"
            f" p99={summary['p99_ms']:.1f}ms max={summary['max_ms']:.1f}ms"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
