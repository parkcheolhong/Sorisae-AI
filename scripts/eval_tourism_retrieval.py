"""관광 검색 정확도 메트릭 하니스 — 골든 질의셋으로 hybrid 검색 정확도를 측정.

지표(top-k):
- category_hit@k: top-k 안에 기대 카테고리(집합) 결과가 1개 이상 → 질의 적중.
- precision@k: top-k 중 기대 카테고리에 부합하는 비율(평균).
- country_hit@k: top-k 안에 기대 국가코드 결과 존재 비율(지오 적합성 보조지표).
- accuracy = mean(category_hit@k). 목표 EVAL_ACCURACY_TARGET(기본 0.90) 이상이면 통과.

실행(권장: 컨테이너 — 임베딩 모델·Qdrant 가 웜):
  docker cp scripts/eval_tourism_retrieval.py devanalysis114-backend:/tmp/eval_tourism_retrieval.py
  docker exec devanalysis114-backend python /tmp/eval_tourism_retrieval.py --k 5
리포트: /app/reports/tourism_retrieval_eval.json (호스트 reports/ 로 마운트됨).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

for _root in (os.getenv("APP_ROOT", "/app"), str(Path(__file__).resolve().parents[1])):
    if _root and _root not in sys.path and Path(_root).exists():
        sys.path.insert(0, _root)

from backend.services.tourism_kb import search_tourism_places  # noqa: E402

# 골든 질의셋(자체완결): 도시 중심좌표·기대 카테고리 집합·국가코드를 포함.
# 카테고리는 풍부히 적재된 종류(restaurant/cafe/museum/attraction) 위주로 공정 평가.
GOLDEN = [
    {"query": "오사카 라멘 맛집", "lat": 34.65, "lon": 135.50, "country": "JP", "expect": {"restaurant", "fast_food"}},
    {"query": "도쿄 카페 추천", "lat": 35.675, "lon": 139.735, "country": "JP", "expect": {"cafe", "restaurant"}},
    {"query": "서울 박물관", "lat": 37.55, "lon": 126.975, "country": "KR", "expect": {"museum", "gallery", "attraction"}},
    {"query": "부산 맛집", "lat": 35.15, "lon": 129.065, "country": "KR", "expect": {"restaurant", "fast_food", "cafe"}},
    {"query": "파리 미술관", "lat": 48.86, "lon": 2.345, "country": "FR", "expect": {"museum", "gallery", "attraction"}},
    {"query": "뉴욕 레스토랑", "lat": 40.75, "lon": -73.975, "country": "US", "expect": {"restaurant", "fast_food"}},
    {"query": "방콕 관광명소", "lat": 13.75, "lon": 100.525, "country": "TH", "expect": {"attraction", "museum", "viewpoint", "gallery"}},
    {"query": "로마 관광명소", "lat": 41.90, "lon": 12.50, "country": "IT", "expect": {"attraction", "museum", "viewpoint", "gallery"}},
    {"query": "바르셀로나 레스토랑", "lat": 41.395, "lon": 2.175, "country": "ES", "expect": {"restaurant", "fast_food", "cafe"}},
    {"query": "교토 관광명소", "lat": 35.015, "lon": 135.755, "country": "JP", "expect": {"attraction", "museum", "viewpoint", "gallery"}},
    {"query": "싱가포르 식당", "lat": 1.32, "lon": 103.84, "country": "SG", "expect": {"restaurant", "fast_food", "cafe"}},
    {"query": "시드니 카페", "lat": -33.865, "lon": 151.21, "country": "AU", "expect": {"cafe", "restaurant"}},
    {"query": "타이베이 맛집", "lat": 25.05, "lon": 121.55, "country": "TW", "expect": {"restaurant", "fast_food", "cafe", "marketplace"}},
    {"query": "암스테르담 미술관", "lat": 52.37, "lon": 4.90, "country": "NL", "expect": {"museum", "gallery", "attraction"}},
    {"query": "런던 카페", "lat": 51.515, "lon": -0.09, "country": "GB", "expect": {"cafe", "restaurant"}},
    {"query": "홍콩 맛집", "lat": 22.30, "lon": 114.18, "country": "HK", "expect": {"restaurant", "fast_food", "cafe"}},
]


def main() -> int:
    ap = argparse.ArgumentParser(description="tourism 검색 정확도 평가")
    ap.add_argument("--k", type=int, default=5, help="top-k")
    ap.add_argument("--target", type=float, default=float(os.getenv("EVAL_ACCURACY_TARGET", "0.90")))
    args = ap.parse_args()
    k = max(1, args.k)

    per_query = []
    cat_hits = 0
    country_hits = 0
    precision_sum = 0.0
    started = time.time()

    for g in GOLDEN:
        results = search_tourism_places(g["query"], limit=k, latitude=g["lat"], longitude=g["lon"])
        cats = [str(r.get("category") or "") for r in results]
        countries = [str(r.get("country") or "") for r in results]
        matched = [c for c in cats if c in g["expect"]]
        cat_hit = len(matched) > 0
        country_hit = g["country"] in countries
        precision = (len(matched) / len(results)) if results else 0.0
        cat_hits += 1 if cat_hit else 0
        country_hits += 1 if country_hit else 0
        precision_sum += precision
        per_query.append({
            "query": g["query"],
            "expect": sorted(g["expect"]),
            "n_results": len(results),
            "top_categories": cats,
            "category_hit": cat_hit,
            "country_hit": country_hit,
            "precision_at_k": round(precision, 3),
        })

    n = len(GOLDEN)
    accuracy = cat_hits / n if n else 0.0
    summary = {
        "k": k,
        "queries": n,
        "accuracy_category_hit": round(accuracy, 4),
        "mean_precision_at_k": round(precision_sum / n, 4) if n else 0.0,
        "country_hit_rate": round(country_hits / n, 4) if n else 0.0,
        "target": args.target,
        "passed": accuracy >= args.target,
        "run_time_sec": round(time.time() - started, 3),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "per_query": per_query,
    }

    print(f"[eval] queries={n} accuracy(category_hit@{k})={summary['accuracy_category_hit']} "
          f"meanP@{k}={summary['mean_precision_at_k']} country_hit={summary['country_hit_rate']} "
          f"target={args.target} passed={summary['passed']} ({summary['run_time_sec']}s)")
    for q in per_query:
        flag = "OK " if q["category_hit"] else "MISS"
        print(f"  [{flag}] {q['query']} → cats={q['top_categories']} P@k={q['precision_at_k']}")

    out_dir = Path(os.getenv("APP_ROOT", "/app")) / "reports"
    if not out_dir.exists():
        out_dir = Path(__file__).resolve().parents[1] / "reports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "tourism_retrieval_eval.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[eval] 리포트 저장: {out_path}")

    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
