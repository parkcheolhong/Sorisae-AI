"""응답속도 KPI 벤치 — 검색(RAG retrieval) + /answer E2E + 서버측 단계 분해.

로드맵 단계5 KPI: 응답시간 < 1s.
- 검색 단계(retrieval)는 KPI 1초 게이트 대상(임베딩 ONNX/CPU + Qdrant hybrid).
- /answer E2E 는 LLM 생성을 포함하므로 별도 측정·보고(생성 지연은 모델/하드웨어 종속).
- 서버가 응답에 실어 보내는 timing_ms(retrieval/generation/media/total)도 함께 집계.

사용:
  python scripts/bench_tourism_latency.py --mode search   --iters 5
  python scripts/bench_tourism_latency.py --mode answer   --iters 3 --base-url http://127.0.0.1:8000
  python scripts/bench_tourism_latency.py --mode both
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.request
from typing import Any, Dict, List, Optional

REPORT_PATH = os.path.join("reports", "tourism_latency_bench.json")
SEARCH_KPI_MS = 1000.0  # 검색 응답 < 1s

GOLDEN = [
    {"query": "오사카 라멘 맛집", "lat": 34.69, "lon": 135.50},
    {"query": "서울 박물관 추천", "lat": 37.55, "lon": 126.98},
    {"query": "파리 미술관 일정", "lat": 48.86, "lon": 2.35},
    {"query": "방콕 관광명소 코스", "lat": 13.75, "lon": 100.52},
    {"query": "뉴욕 레스토랑", "lat": 40.75, "lon": -73.98},
    {"query": "부산 가볼만한 곳", "lat": 35.15, "lon": 129.07},
]


def _pcts(samples: List[float]) -> Dict[str, float]:
    if not samples:
        return {"n": 0}
    s = sorted(samples)

    def _p(q: float) -> float:
        idx = min(len(s) - 1, int(round(q * (len(s) - 1))))
        return round(s[idx], 1)

    return {
        "n": len(s),
        "mean": round(statistics.fmean(s), 1),
        "p50": _p(0.50),
        "p90": _p(0.90),
        "p95": _p(0.95),
        "max": round(s[-1], 1),
    }


def bench_search(iters: int) -> Dict[str, Any]:
    from backend.services.tourism_kb import search_tourism_places

    # 워밍업(임베딩 모델 로드).
    search_tourism_places(GOLDEN[0]["query"], limit=10, latitude=GOLDEN[0]["lat"], longitude=GOLDEN[0]["lon"])
    samples: List[float] = []
    for _ in range(iters):
        for q in GOLDEN:
            t0 = time.perf_counter()
            search_tourism_places(q["query"], limit=10, latitude=q["lat"], longitude=q["lon"])
            samples.append((time.perf_counter() - t0) * 1000.0)
    stats = _pcts(samples)
    stats["kpi_ms"] = SEARCH_KPI_MS
    stats["kpi_pass"] = bool(stats.get("p95", 1e9) < SEARCH_KPI_MS)
    return stats


def _post_answer(base_url: str, q: Dict[str, Any], timeout: float = 90.0) -> Optional[dict]:
    body = json.dumps({
        "query": q["query"], "language": "ko", "latitude": q["lat"], "longitude": q["lon"], "days": 1,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/llm/voice/answer", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8", "ignore"))


def bench_answer(iters: int, base_url: str) -> Dict[str, Any]:
    e2e: List[float] = []
    srv_total: List[float] = []
    srv_ret: List[float] = []
    srv_gen: List[float] = []
    errors = 0
    for _ in range(iters):
        for q in GOLDEN:
            t0 = time.perf_counter()
            try:
                data = _post_answer(base_url, q)
            except Exception:
                errors += 1
                continue
            e2e.append((time.perf_counter() - t0) * 1000.0)
            tm = (data or {}).get("timing_ms") or {}
            if tm:
                srv_total.append(float(tm.get("total") or 0))
                srv_ret.append(float(tm.get("retrieval") or 0))
                srv_gen.append(float(tm.get("generation") or 0))
    return {
        "e2e_http": _pcts(e2e),
        "server_total": _pcts(srv_total),
        "server_retrieval": _pcts(srv_ret),
        "server_generation": _pcts(srv_gen),
        "errors": errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["search", "answer", "both"], default="both")
    ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--base-url", default=os.getenv("LOCAL_API_BASE_URL", "http://127.0.0.1:8000"))
    args = ap.parse_args()

    report: Dict[str, Any] = {"golden_n": len(GOLDEN), "iters": args.iters}

    if args.mode in ("search", "both"):
        print("[검색 단계 latency] 측정 중...")
        report["search"] = bench_search(args.iters)
        s = report["search"]
        print(f"  retrieval: mean={s.get('mean')}ms p50={s.get('p50')} p90={s.get('p90')} "
              f"p95={s.get('p95')} max={s.get('max')} → KPI<{SEARCH_KPI_MS:.0f}ms: "
              f"{'PASS' if s.get('kpi_pass') else 'FAIL'}")

    if args.mode in ("answer", "both"):
        print("[/answer E2E latency] 측정 중(LLM 생성 포함)...")
        report["answer"] = bench_answer(args.iters, args.base_url)
        a = report["answer"]
        print(f"  e2e_http:          {a['e2e_http']}")
        print(f"  server_total:      {a['server_total']}")
        print(f"  server_retrieval:  {a['server_retrieval']}")
        print(f"  server_generation: {a['server_generation']}")
        if a["errors"]:
            print(f"  errors: {a['errors']}")

    os.makedirs("reports", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n리포트 저장: {REPORT_PATH}")

    # 검색 KPI 미충족 시 nonzero(게이트 용도).
    if report.get("search") and not report["search"].get("kpi_pass"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
