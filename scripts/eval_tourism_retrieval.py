"""관광 검색 정확도 메트릭 하니스 — 골든 질의셋으로 hybrid 검색 정확도를 측정.

지표(top-k):
- category_hit@k: top-k 안에 기대 카테고리(집합) 결과가 1개 이상 → 질의 적중.
- precision@k: top-k 중 기대 카테고리에 부합하는 비율(평균).
- country_hit@k: top-k 안에 기대 국가코드 결과 존재 비율(지오 적합성 보조지표).
- accuracy = mean(category_hit@k). 목표 EVAL_ACCURACY_TARGET(기본 0.90) 이상이면 통과.

실행(권장: 컨테이너 — 임베딩 모델·Qdrant 가 웜):
  docker cp scripts/eval_tourism_retrieval.py devanalysis114-backend:/tmp/eval_tourism_retrieval.py
  docker exec devanalysis114-backend python /tmp/eval_tourism_retrieval.py --k 5

RAG top-k 자동 튜닝(제안기, --sweep):
  # k 후보들을 동일 골든셋으로 평가해 최적 k 를 *제안*(배포 아님 — 사람 승인 게이트).
  docker exec devanalysis114-backend python /tmp/eval_tourism_retrieval.py --sweep 3,5,8,12
  # 채택 시 운영자가 런타임 SSOT 적용(재기동 불필요):  export TOURISM_RAG_TOP_K=<k>
리포트: /app/reports/tourism_retrieval_eval.json · 제안: /app/reports/tourism_rag_topk_proposal.json
(호스트 reports/ 로 마운트됨).

설계 메모: RAG top-k 노브는 VoIP voice-relay 자동 튜너(eval/worldlinco, VAD/턴테이킹 QoE
목적함수)와 분리된 *관광 검색 정확도* 목적함수에 연결한다. 두 도메인의 목적함수가 다르므로
worldlinco SEARCH_SPACE 에 섞지 않는다(미연결 노브 = 무의미한 제안 방지).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

for _root in (os.getenv("APP_ROOT", "/app"), str(Path(__file__).resolve().parents[1])):
    if _root and _root not in sys.path and Path(_root).exists():
        sys.path.insert(0, _root)

from backend.services.tourism_kb import search_tourism_places, tourism_rag_top_k  # noqa: E402

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


def evaluate_k(k: int, *, target: float) -> dict:
    """골든셋을 top-k 로 1회 평가해 요약 dict 반환(Qdrant/임베딩 필요)."""
    k = max(1, int(k))
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
    return {
        "k": k,
        "queries": n,
        "accuracy_category_hit": round(accuracy, 4),
        "mean_precision_at_k": round(precision_sum / n, 4) if n else 0.0,
        "country_hit_rate": round(country_hits / n, 4) if n else 0.0,
        "target": target,
        "passed": accuracy >= target,
        "run_time_sec": round(time.time() - started, 3),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "per_query": per_query,
    }


def _reports_dir() -> Path:
    out_dir = Path(os.getenv("APP_ROOT", "/app")) / "reports"
    if not out_dir.exists():
        out_dir = Path(__file__).resolve().parents[1] / "reports"
    out_dir.mkdir(exist_ok=True)
    return out_dir


def select_best_k(summaries: list[dict]) -> dict:
    """k-스윕 요약 리스트에서 최적 k 를 *제안*(배포 아님).

    선택 기준(사전식): (1) accuracy_category_hit ↑ (2) mean_precision_at_k ↑
    (3) run_time_sec ↓ (4) k ↓(프롬프트 절약). 동률은 더 작은 k 를 선호한다.

    정직성: 현재 운영 k 가 스윕 후보에 없으면 그 정확도를 *측정하지 않은* 것이므로
    `improves_over_current` 를 단정하지 않고 `null`(+`current_in_sweep=false`)로 둔다
    (헌법: 검증 없이 개선으로 기록 금지). 반환: 제안 메타 dict(사람 승인 게이트 표식 포함)."""
    if not summaries:
        return {}
    ranked = sorted(
        summaries,
        key=lambda s: (
            -float(s.get("accuracy_category_hit", 0.0)),
            -float(s.get("mean_precision_at_k", 0.0)),
            float(s.get("run_time_sec", 0.0)),
            int(s.get("k", 1_000_000)),
        ),
    )
    best = ranked[0]
    current = tourism_rag_top_k()
    proposed = int(best.get("k", current))
    by_k = {int(s["k"]): s for s in summaries if s.get("k") is not None}
    current_in_sweep = current in by_k

    if not current_in_sweep:
        improves: Optional[bool] = None  # 현재 k 미측정 → 개선 여부 단정 불가
        note = (f"현재 운영 k={current} 는 스윕 후보에 없어 개선 여부 미확정 — "
                f"비교하려면 --sweep 에 {current} 를 포함하세요.")
    elif proposed == current:
        improves = False
        note = "제안 k 가 현재 k 와 동일(현 설정 유지 권장)."
    else:
        cur = by_k[current]
        improves = (
            (float(best["accuracy_category_hit"]), float(best["mean_precision_at_k"]))
            > (float(cur["accuracy_category_hit"]), float(cur["mean_precision_at_k"]))
        )
        note = ("측정된 현재 k 대비 정확도/정밀도 개선." if improves
                else "제안 k 가 더 작거나 동률이라 채택해도 품질 손실 없음(프롬프트 절약).")

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "objective": "tourism_retrieval(category_hit@k · meanP@k · latency)",
        "gate_status": "PROPOSAL_ONLY_REQUIRES_HUMAN_APPROVAL",
        "runtime_ssot_env": "TOURISM_RAG_TOP_K",
        "current_top_k": current,
        "current_in_sweep": current_in_sweep,
        "proposed_top_k": proposed,
        "improves_over_current": improves,
        "note": note,
        "apply_hint": f"export TOURISM_RAG_TOP_K={proposed}  # 재기동 불필요(매 호출 env 재평가)",
        "candidates": [
            {"k": s["k"], "accuracy_category_hit": s["accuracy_category_hit"],
             "mean_precision_at_k": s["mean_precision_at_k"],
             "country_hit_rate": s["country_hit_rate"],
             "run_time_sec": s["run_time_sec"]}
            for s in sorted(summaries, key=lambda s: int(s.get("k", 0)))
        ],
    }


def _print_summary(summary: dict) -> None:
    k = summary["k"]
    print(f"[eval] queries={summary['queries']} accuracy(category_hit@{k})={summary['accuracy_category_hit']} "
          f"meanP@{k}={summary['mean_precision_at_k']} country_hit={summary['country_hit_rate']} "
          f"target={summary['target']} passed={summary['passed']} ({summary['run_time_sec']}s)")
    for q in summary["per_query"]:
        flag = "OK " if q["category_hit"] else "MISS"
        print(f"  [{flag}] {q['query']} → cats={q['top_categories']} P@k={q['precision_at_k']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="tourism 검색 정확도 평가 / RAG top-k 제안기")
    ap.add_argument("--k", type=int, default=None,
                    help="top-k(미지정 시 런타임 SSOT tourism_rag_top_k())")
    ap.add_argument("--sweep", default=None,
                    help="k 후보 쉼표목록(예: 3,5,8,12) — 최적 k 를 제안(배포 아님)")
    ap.add_argument("--target", type=float, default=float(os.getenv("EVAL_ACCURACY_TARGET", "0.90")))
    args = ap.parse_args()
    out_dir = _reports_dir()

    if args.sweep:
        try:
            ks = sorted({max(1, int(x)) for x in str(args.sweep).split(",") if str(x).strip()})
        except ValueError:
            print(f"[eval] --sweep 파싱 실패: {args.sweep!r}")
            return 2
        if not ks:
            print("[eval] --sweep 후보가 비었습니다")
            return 2
        summaries = []
        for k in ks:
            s = evaluate_k(k, target=args.target)
            _print_summary(s)
            summaries.append(s)
        proposal = select_best_k(summaries)
        prop_path = out_dir / "tourism_rag_topk_proposal.json"
        prop_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
        improves = proposal["improves_over_current"]
        improves_str = "미확정(현재 k 미측정)" if improves is None else ("예" if improves else "아니오")
        print(f"\n[sweep] 현재 top-k={proposal['current_top_k']} → 제안 top-k={proposal['proposed_top_k']} "
              f"(개선={improves_str})")
        print(f"[sweep] {proposal['note']}")
        print(f"[sweep] ⚠️ 제안은 배포가 아닙니다 — 사람 승인 후 적용: {proposal['apply_hint']}")
        print(f"[sweep] 제안 저장: {prop_path}")
        # 제안된 k 의 정확도가 목표 미달이면 비0 종료(게이트 신호).
        best = next((s for s in summaries if s["k"] == proposal["proposed_top_k"]), summaries[0])
        return 0 if best["passed"] else 1

    k = max(1, args.k) if args.k is not None else tourism_rag_top_k()
    summary = evaluate_k(k, target=args.target)
    _print_summary(summary)
    out_path = out_dir / "tourism_retrieval_eval.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[eval] 리포트 저장: {out_path}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
