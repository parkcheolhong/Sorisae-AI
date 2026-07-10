"""관광 데이터 사람검수(human-in-the-loop) — 샘플링 + 라벨 저장 + 집계.

법·윤리·품질 체크리스트 '품질 검증'의 사람검수 루프.
- 자동 하니스(quality.py / eval)와 상호보완: 전문가가 표본을 검수해 사람 기준 정확도를 산출.
- 두 검수 모드:
  · poi      : tourism_places 표본 POI 의 분류/실재성/이름·주소 정확도 검수.
  · retrieval: 질의→top-k 결과의 관련성(relevant/irrelevant) 검수 → 사람 precision@k.
- 라벨은 Postgres `tourism_review_label` 에 저장(경량 raw SQL, graph.py 와 동일 패턴, graceful).
"""

from __future__ import annotations

import logging
import random
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_VALID_VERDICTS = {"relevant", "irrelevant", "correct", "incorrect", "unsure"}

_DDL = (
    """
    CREATE TABLE IF NOT EXISTS tourism_review_label (
        id BIGSERIAL PRIMARY KEY,
        item_type TEXT NOT NULL,
        query TEXT,
        place_source TEXT,
        place_source_id TEXT,
        place_name TEXT,
        category TEXT,
        reviewer TEXT,
        verdict TEXT NOT NULL,
        note TEXT,
        created_at TIMESTAMP DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tourism_review_type ON tourism_review_label (item_type)",
    "CREATE INDEX IF NOT EXISTS idx_tourism_review_created ON tourism_review_label (created_at)",
)

# retrieval 검수 기본 질의셋(자동 eval 골든과 동일 계열, 좌표 포함).
_DEFAULT_REVIEW_QUERIES = [
    {"query": "오사카 라멘 맛집", "lat": 34.65, "lon": 135.50},
    {"query": "서울 박물관", "lat": 37.55, "lon": 126.975},
    {"query": "파리 미술관", "lat": 48.86, "lon": 2.345},
    {"query": "방콕 관광명소", "lat": 13.75, "lon": 100.525},
    {"query": "뉴욕 레스토랑", "lat": 40.75, "lon": -73.975},
    {"query": "부산 맛집", "lat": 35.15, "lon": 129.065},
]


class TourismReviewStore:
    _instance: Optional["TourismReviewStore"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._engine = None
        self._ensured = False
        self._connect()

    @classmethod
    def shared(cls) -> "TourismReviewStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _connect(self):
        try:
            from backend.marketplace.database import engine

            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            self._engine = engine
        except Exception as exc:
            logger.warning("[tourism_kb.review] DB 연결 실패(검수 비활성): %s", exc)
            self._engine = None

    @property
    def available(self) -> bool:
        return self._engine is not None

    def ensure_schema(self):
        if not self._engine or self._ensured:
            return
        try:
            with self._engine.begin() as conn:
                for stmt in _DDL:
                    conn.exec_driver_sql(stmt)
            self._ensured = True
        except Exception as exc:
            logger.warning("[tourism_kb.review] 스키마 생성 실패: %s", exc)

    # ── 샘플링 ───────────────────────────────────────────────────────────
    def sample_pois(self, n: int = 20, *, prefer_unknown: bool = True, seed: Optional[int] = None) -> List[Dict[str, Any]]:
        """tourism_places 표본 POI. prefer_unknown=True 면 미지/누락 카테고리를 우선 포함."""
        from backend.services.tourism_kb.quality import load_points_from_qdrant
        from backend.services.tourism_kb.service import _KNOWN_CATEGORIES

        rows = load_points_from_qdrant()
        if not rows:
            return []
        rng = random.Random(seed)
        n = max(1, min(int(n), 200))
        picked: List[Dict[str, Any]] = []
        if prefer_unknown:
            unknown = [r for r in rows if (r.get("category") or "") not in _KNOWN_CATEGORIES]
            rng.shuffle(unknown)
            picked.extend(unknown[: n // 2])
        remaining = [r for r in rows if r not in picked]
        rng.shuffle(remaining)
        picked.extend(remaining[: n - len(picked)])
        return [self._poi_view(r) for r in picked[:n]]

    @staticmethod
    def _poi_view(r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "place_source": r.get("source"),
            "place_source_id": str(r.get("source_id") or ""),
            "place_name": r.get("name"),
            "category": r.get("category"),
            "address": r.get("address"),
            "country": r.get("country"),
            "lat": r.get("lat"),
            "lon": r.get("lon"),
        }

    def sample_retrieval(self, *, k: int = 5, queries: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """질의→top-k 결과를 관련성 검수용으로 반환."""
        from backend.services.tourism_kb import search_tourism_places

        qs = queries or _DEFAULT_REVIEW_QUERIES
        out: List[Dict[str, Any]] = []
        for q in qs:
            results = search_tourism_places(
                q["query"], limit=max(1, int(k)), latitude=q.get("lat"), longitude=q.get("lon")
            )
            out.append({
                "query": q["query"],
                "results": [
                    {
                        "place_source": r.get("source"),
                        "place_source_id": str(r.get("source_id") or ""),
                        "place_name": r.get("name"),
                        "category": r.get("category"),
                        "address": r.get("address"),
                        "score": round(float(r.get("score") or 0.0), 4),
                    }
                    for r in results
                ],
            })
        return out

    # ── 라벨 저장 ────────────────────────────────────────────────────────
    def save_labels(self, labels: List[Dict[str, Any]], *, reviewer: Optional[str] = None) -> int:
        if not self._engine or not labels:
            return 0
        self.ensure_schema()
        rows = []
        for lb in labels:
            verdict = str(lb.get("verdict") or "").strip().lower()
            if verdict not in _VALID_VERDICTS:
                continue
            rows.append({
                "item_type": str(lb.get("item_type") or "poi").strip().lower(),
                "query": (str(lb.get("query") or "").strip() or None),
                "place_source": (str(lb.get("place_source") or "").strip() or None),
                "place_source_id": (str(lb.get("place_source_id") or "").strip() or None),
                "place_name": (str(lb.get("place_name") or "").strip() or None),
                "category": (str(lb.get("category") or "").strip() or None),
                "reviewer": (str(lb.get("reviewer") or reviewer or "").strip() or None),
                "verdict": verdict,
                "note": (str(lb.get("note") or "").strip() or None),
            })
        if not rows:
            return 0
        sql = (
            "INSERT INTO tourism_review_label "
            "(item_type, query, place_source, place_source_id, place_name, category, reviewer, verdict, note) "
            "VALUES (%(item_type)s, %(query)s, %(place_source)s, %(place_source_id)s, %(place_name)s, "
            "%(category)s, %(reviewer)s, %(verdict)s, %(note)s)"
        )
        try:
            with self._engine.begin() as conn:
                raw = conn.connection
                cur = raw.cursor()
                cur.executemany(sql, rows)
                cur.close()
            return len(rows)
        except Exception as exc:
            logger.warning("[tourism_kb.review] 라벨 저장 실패: %s", exc)
            return 0

    # ── 집계 ─────────────────────────────────────────────────────────────
    def stats(self) -> Dict[str, Any]:
        if not self._engine:
            return {"available": False}
        self.ensure_schema()
        try:
            with self._engine.connect() as conn:
                total = conn.exec_driver_sql("SELECT COUNT(*) FROM tourism_review_label").scalar() or 0
                reviewers = conn.exec_driver_sql(
                    "SELECT COUNT(DISTINCT reviewer) FROM tourism_review_label WHERE reviewer IS NOT NULL"
                ).scalar() or 0
                by_verdict = dict(conn.exec_driver_sql(
                    "SELECT verdict, COUNT(*) FROM tourism_review_label GROUP BY verdict"
                ).fetchall())
        except Exception as exc:
            logger.warning("[tourism_kb.review] stats 실패: %s", exc)
            return {"available": True, "error": str(exc)}

        rel = int(by_verdict.get("relevant", 0))
        irr = int(by_verdict.get("irrelevant", 0))
        cor = int(by_verdict.get("correct", 0))
        inc = int(by_verdict.get("incorrect", 0))
        human_precision = round(rel / (rel + irr), 4) if (rel + irr) else None
        poi_accuracy = round(cor / (cor + inc), 4) if (cor + inc) else None
        return {
            "available": True,
            "total_labels": int(total),
            "reviewers": int(reviewers),
            "by_verdict": {k: int(v) for k, v in by_verdict.items()},
            "human_precision_retrieval": human_precision,
            "poi_accuracy": poi_accuracy,
        }


def get_review_store() -> TourismReviewStore:
    return TourismReviewStore.shared()
