"""관광 KB 멀티모달 백필 — POI 대표 이미지를 CLIP-vision 으로 임베딩해 별도 컬렉션 적재.

설계: docs/worldlinco-v2/TOURISM_AI_KNOWLEDGE_RAG_DESIGN.md (§3 멀티모달)
- 본 컬렉션('tourism_places')을 스캔 → 이미지 참조(wikimedia_commons/wikidata)가 있는 POI 만 대상.
- Wikimedia Commons 썸네일(저작권 게이트 통과분)을 받아 CLIP-vision(512d)으로 임베딩.
- 별도 컬렉션('tourism_places_clip', 동일 point id)에 적재 → 검색 시 CLIP-text 와 RRF 융합.
- 본 컬렉션(dense/sparse)은 건드리지 않으므로 재적재 불필요(비파괴 enrichment).

전제: 환경변수 TOURISM_CLIP_ENABLED=1 (모델 로드). 모델은 최초 1회 다운로드(약 350MB, ONNX/CPU).

사용:
  TOURISM_CLIP_ENABLED=1 python scripts/index_tourism_clip.py            # 전체
  TOURISM_CLIP_ENABLED=1 python scripts/index_tourism_clip.py --limit 500
  TOURISM_CLIP_ENABLED=1 python scripts/index_tourism_clip.py --batch 32 --progress
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description="관광 KB CLIP 이미지 벡터 백필")
    parser.add_argument("--limit", type=int, default=0, help="스캔할 최대 POI 수(0=전체)")
    parser.add_argument("--batch", type=int, default=64, help="CLIP 컬렉션 upsert 배치 크기")
    parser.add_argument("--progress", action="store_true", help="진행 로그 출력")
    args = parser.parse_args()

    # 스크립트는 멀티모달을 강제 활성화(미설정 시에도 동작하도록).
    os.environ.setdefault("TOURISM_CLIP_ENABLED", "1")

    from backend.services.tourism_kb import get_tourism_store
    from backend.services.tourism_kb.multimodal import get_clip_embedder

    store = get_tourism_store()
    if not store.available:
        print("[clip-backfill] Qdrant 미연결 — 중단", file=sys.stderr)
        return 2

    clip = get_clip_embedder()
    if not clip.available:
        print("[clip-backfill] CLIP 임베더 로드 실패(fastembed/Pillow 확인) — 중단", file=sys.stderr)
        return 3

    report = store.backfill_clip_vectors(limit=args.limit, batch=args.batch, progress=args.progress)
    print(json.dumps({"ok": True, "report": report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
