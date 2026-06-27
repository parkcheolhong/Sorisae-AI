"""관광 KB 멀티모달 일괄 갱신 — 27개 도시 재적재(이미지 참조 보존) → CLIP 백필 1회.

설계: docs/worldlinco-v2/TOURISM_AI_KNOWLEDGE_RAG_DESIGN.md (§3 멀티모달, §4 지속 최신화)
- 1단계: scripts/ingest_tourism_city.ingest_city 로 도시별 멱등 적재. 보강된 적재기가
  OSM `wikidata`/`wikimedia_commons` 와 Wikidata QID 를 payload 에 보존한다.
- 2단계: TourismVectorStore.backfill_clip_vectors 로 본 컬렉션 전체를 스캔 →
  이미지 참조가 있는 POI 의 대표 이미지를 CLIP-vision(512d) 으로 임베딩 → 'tourism_places_clip'.
- 비파괴: 본 컬렉션(dense/sparse)은 갱신만, CLIP 은 별도 컬렉션이라 재적재 불요.
- 멀티모달은 백필 후 백엔드 env `TOURISM_CLIP_ENABLED=1` + 재기동 시 질의에서 RRF 융합.

사용(컨테이너/venv 공통, repo 루트에서):
  python scripts/tourism_kb_clip_refresh.py --all                  # 27개 도시 전체
  python scripts/tourism_kb_clip_refresh.py --cities paris,kyoto   # 일부 도시
  python scripts/tourism_kb_clip_refresh.py --country KR,JP        # 국가 단위
  python scripts/tourism_kb_clip_refresh.py --all --skip-ingest    # 적재 생략, 백필만
  python scripts/tourism_kb_clip_refresh.py --all --skip-backfill  # 적재만

도커 컴포즈(운영):
  docker compose build backend && docker compose up -d backend     # fastembed/scripts 반영
  docker compose exec -e TOURISM_CLIP_ENABLED=1 backend python scripts/tourism_kb_clip_refresh.py --all --progress
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# CLIP 백필이 모델을 로드하도록 강제(미설정 시에도 동작).
os.environ.setdefault("TOURISM_CLIP_ENABLED", "1")


def _select_cities(args) -> list[str]:
    from scripts.ingest_tourism_city import CITY_REGISTRY

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
        return sorted(n for n, (_b, cc) in CITY_REGISTRY.items() if cc in codes)
    raise SystemExit("--all / --cities / --country 중 하나는 필수")


def main() -> int:
    ap = argparse.ArgumentParser(description="관광 KB 멀티모달 일괄 갱신(재적재→CLIP 백필)")
    ap.add_argument("--all", action="store_true", help="등록된 전 도시(27)")
    ap.add_argument("--cities", help="쉼표구분 도시명(예: paris,kyoto)")
    ap.add_argument("--country", help="쉼표구분 국가코드(예: KR,JP)")
    ap.add_argument("--limit", type=int, default=700, help="도시·소스별 최대 수집 건수")
    ap.add_argument("--no-wikidata", action="store_true",
                    help="Wikidata 보강 생략(주의: 이미지 참조 대부분이 Wikidata P18 기반)")
    ap.add_argument("--sleep", type=float, default=2.0, help="도시간 대기초(공용 API 예의)")
    ap.add_argument("--batch", type=int, default=64, help="CLIP upsert 배치 크기")
    ap.add_argument("--skip-ingest", action="store_true", help="적재 생략(백필만)")
    ap.add_argument("--skip-backfill", action="store_true", help="백필 생략(적재만)")
    ap.add_argument("--progress", action="store_true", help="진행 로그")
    args = ap.parse_args()

    from backend.services.tourism_kb import get_tourism_store

    t0 = time.time()
    ingest_summary: list[dict] = []

    if not args.skip_ingest:
        from scripts.ingest_tourism_city import CITY_REGISTRY, ingest_city

        cities = _select_cities(args)
        print(f"[refresh] 1단계 적재 대상 {len(cities)}개 도시: {', '.join(cities)}")
        for i, name in enumerate(cities):
            bbox, country = CITY_REGISTRY[name]
            print(f"\n===== [{i+1}/{len(cities)}] {name} ({country}) =====")
            try:
                r = ingest_city(
                    name, bbox, country,
                    limit=args.limit,
                    with_wikidata=not args.no_wikidata,
                    fresh=False,  # 다도시 배치는 절대 fresh 금지(전체 삭제 방지).
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[error] {name} 적재 실패(건너뜀): {exc}")
                r = {"label": name, "ok": False, "count": 0, "reason": str(exc)}
            ingest_summary.append(r)
            if i < len(cities) - 1 and args.sleep > 0:
                time.sleep(args.sleep)
        ok = [r for r in ingest_summary if r.get("ok")]
        pts = sum(r.get("count", 0) for r in ok)
        print(f"\n[refresh] 적재 완료: 성공 {len(ok)}/{len(ingest_summary)} 도시 · {pts} POI")
    else:
        print("[refresh] 1단계 적재 생략(--skip-ingest)")

    backfill_report = None
    if not args.skip_backfill:
        store = get_tourism_store()
        if not store.available:
            print("[refresh] Qdrant 미연결 — 백필 중단", file=sys.stderr)
            return 2
        from backend.services.tourism_kb.multimodal import get_clip_embedder

        if not get_clip_embedder().available:
            print("[refresh] CLIP 임베더 로드 실패(fastembed/Pillow) — 백필 중단", file=sys.stderr)
            return 3
        print("\n[refresh] 2단계 CLIP 백필 시작(전체 컬렉션 스캔)...")
        backfill_report = store.backfill_clip_vectors(limit=0, batch=args.batch, progress=args.progress)
    else:
        print("[refresh] 2단계 백필 생략(--skip-backfill)")

    elapsed = round(time.time() - t0, 1)
    out = {
        "ok": all(r.get("ok") for r in ingest_summary) if ingest_summary else True,
        "elapsed_sec": elapsed,
        "ingest": ingest_summary,
        "backfill": backfill_report,
    }
    print("\n========== 멀티모달 일괄 갱신 요약 ==========")
    print(json.dumps(out, ensure_ascii=False))
    failed = [r for r in ingest_summary if not r.get("ok")]
    return 0 if not failed else 3


if __name__ == "__main__":
    raise SystemExit(main())
