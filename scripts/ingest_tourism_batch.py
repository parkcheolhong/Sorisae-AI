"""관광 KB 글로벌 배치 적재기 — 여러 도시를 한 번에 멱등 적재(자동화/스케줄용).

설계: docs/worldlinco-v2/TOURISM_AI_KNOWLEDGE_RAG_DESIGN.md (§4 지속 최신화, 글로벌 확대)
- 공유 컬렉션 'tourism_places' 에 도시별 POI 를 멱등(source+source_id) upsert → 재실행 시 갱신.
- 다도시 배치에서는 --fresh 금지(전체 삭제됨). 차원 변경 등 전체 리셋은 1회성으로 별도 수행.
- 도시별 실패는 건너뛰고 계속 → 마지막에 요약 + 비정상 시 exit code != 0(알림 연동).

사용:
  python scripts/ingest_tourism_batch.py --all                 # 등록된 전 도시
  python scripts/ingest_tourism_batch.py --cities seoul,busan,osaka
  python scripts/ingest_tourism_batch.py --country KR,JP        # 국가 단위
  python scripts/ingest_tourism_batch.py --all --reset-first    # 첫 도시만 컬렉션 리셋(차원변경 후)

cron 예시(매주 일요일 03:00, 공용 Overpass 부하 고려해 주1회):
  0 3 * * 0  cd /workspace && python scripts/ingest_tourism_batch.py --all >> /var/log/tourism_kb.log 2>&1
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ingest_tourism_city import CITY_REGISTRY, ingest_city  # noqa: E402


def _select_cities(args) -> list[str]:
    if args.all:
        return sorted(CITY_REGISTRY.keys())
    if args.cities:
        names = [c.strip().lower() for c in args.cities.split(",") if c.strip()]
        unknown = [c for c in names if c not in CITY_REGISTRY]
        if unknown:
            raise SystemExit(f"미등록 도시: {unknown} (등록: {sorted(CITY_REGISTRY)})")
        return names
    if args.country:
        codes = {c.strip().upper() for c in args.country.split(",") if c.strip()}
        return sorted(name for name, (_b, cc) in CITY_REGISTRY.items() if cc in codes)
    raise SystemExit("--all / --cities / --country 중 하나는 필수")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="등록된 전 도시")
    ap.add_argument("--cities", help="쉼표구분 도시명(예: seoul,busan)")
    ap.add_argument("--country", help="쉼표구분 국가코드(예: KR,JP)")
    ap.add_argument("--limit", type=int, default=700, help="도시·소스별 최대 수집 건수")
    ap.add_argument("--no-wikidata", action="store_true", help="Wikidata 보강 생략")
    ap.add_argument("--reset-first", action="store_true", help="첫 도시만 컬렉션 리셋(차원변경 후 1회)")
    ap.add_argument("--sleep", type=float, default=2.0, help="도시간 대기초(공용 API 예의)")
    args = ap.parse_args()

    cities = _select_cities(args)
    print(f"[batch] 대상 {len(cities)}개 도시: {', '.join(cities)}")
    t0 = time.time()
    results = []
    for i, name in enumerate(cities):
        bbox, country = CITY_REGISTRY[name]
        print(f"\n===== [{i+1}/{len(cities)}] {name} ({country}) =====")
        try:
            r = ingest_city(
                name, bbox, country,
                limit=args.limit,
                with_wikidata=not args.no_wikidata,
                fresh=(args.reset_first and i == 0),
            )
        except Exception as exc:
            print(f"[error] {name} 적재 실패(건너뜀): {exc}")
            r = {"label": name, "ok": False, "count": 0, "reason": str(exc)}
        results.append(r)
        if i < len(cities) - 1 and args.sleep > 0:
            time.sleep(args.sleep)

    ok = [r for r in results if r.get("ok")]
    failed = [r for r in results if not r.get("ok")]
    total_pts = sum(r.get("count", 0) for r in ok)
    print("\n========== 배치 요약 ==========")
    print(f"성공 {len(ok)}/{len(results)} 도시 · 총 {total_pts} POI · 소요 {time.time()-t0:.1f}s")
    for r in ok:
        print(f"  ✓ {r['label']}: {r['count']}건")
    for r in failed:
        print(f"  ✗ {r['label']}: {r.get('reason')}")
    return 0 if not failed else 3


if __name__ == "__main__":
    raise SystemExit(main())
