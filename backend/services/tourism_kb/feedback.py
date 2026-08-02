"""관광 AI 파일럿 베타 피드백 — 만족도(엄지)·NPS·A/B 태깅 수집 + 집계.

법·윤리·품질 체크리스트 '품질 검증'의 단계 5(파일럿·피드백) 사용자 피드백 루프.
- 사람검수(review.py, 전문가)와 상호보완: 실제 사용자가 일정 결과를 평가.
- 수집: thumbs(up/down), NPS(0~10), 자유 코멘트, A/B variant, 지연(timing) 메타.
- 저장: Postgres `tourism_answer_feedback`(경량 raw SQL, review.py 동일 패턴, graceful·PII 비저장).
- 집계: NPS(=%추천자(9~10) - %비추천자(0~6)), 엄지 긍정률, variant(A/B)별 분해.

개인정보: 식별자/좌표를 저장하지 않는다(질의 텍스트만; 클라이언트가 PII 제거 후 전송 권장).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_VALID_RATINGS = {"up", "down"}
_VALID_VARIANTS = {"A", "B"}
_VALID_EVIDENCE_GRADES = {"확정", "추정", "미확인"}

_DDL = (
    """
    CREATE TABLE IF NOT EXISTS tourism_answer_feedback (
        id BIGSERIAL PRIMARY KEY,
        query TEXT,
        language TEXT,
        variant TEXT DEFAULT 'A',
        rating TEXT,
        nps SMALLINT,
        comment TEXT,
        days SMALLINT,
        candidate_count INT,
        cached BOOLEAN,
        total_ms REAL,
        evidence_grade TEXT,
        uncertainty_disclosed BOOLEAN,
        created_at TIMESTAMP DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tourism_feedback_variant ON tourism_answer_feedback (variant)",
    "CREATE INDEX IF NOT EXISTS idx_tourism_feedback_created ON tourism_answer_feedback (created_at)",
    "ALTER TABLE tourism_answer_feedback ADD COLUMN IF NOT EXISTS evidence_grade TEXT",
    "ALTER TABLE tourism_answer_feedback ADD COLUMN IF NOT EXISTS uncertainty_disclosed BOOLEAN",
)


def _clamp_nps(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n < 0 or n > 10:
        return None
    return n


class TourismFeedbackStore:
    _instance: Optional["TourismFeedbackStore"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._engine = None
        self._ensured = False
        self._connect()

    @classmethod
    def shared(cls) -> "TourismFeedbackStore":
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
            logger.warning("[tourism_kb.feedback] DB 연결 실패(피드백 비활성): %s", exc)
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
            logger.warning("[tourism_kb.feedback] 스키마 생성 실패: %s", exc)

    # ── 저장 ─────────────────────────────────────────────────────────────
    def save_feedback(self, fb: Dict[str, Any]) -> bool:
        """단건 피드백 저장. rating/nps 중 최소 하나 유효해야 저장."""
        if not self._engine:
            return False
        self.ensure_schema()

        rating = str(fb.get("rating") or "").strip().lower() or None
        if rating not in (_VALID_RATINGS | {None}):
            rating = None
        nps = _clamp_nps(fb.get("nps"))
        if rating is None and nps is None:
            return False  # 빈 피드백 거부

        variant = str(fb.get("variant") or "A").strip().upper()
        if variant not in _VALID_VARIANTS:
            variant = "A"

        def _int_or_none(v: Any) -> Optional[int]:
            try:
                return int(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        def _float_or_none(v: Any) -> Optional[float]:
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        row = {
            "query": (str(fb.get("query") or "").strip()[:500] or None),
            "language": (str(fb.get("language") or "").strip()[:16] or None),
            "variant": variant,
            "rating": rating,
            "nps": nps,
            "comment": (str(fb.get("comment") or "").strip()[:1000] or None),
            "days": _int_or_none(fb.get("days")),
            "candidate_count": _int_or_none(fb.get("candidate_count")),
            "cached": bool(fb.get("cached")) if fb.get("cached") is not None else None,
            "total_ms": _float_or_none(fb.get("total_ms")),
        }
        sql = (
            "INSERT INTO tourism_answer_feedback "
            "(query, language, variant, rating, nps, comment, days, candidate_count, cached, total_ms, evidence_grade, uncertainty_disclosed) "
            "VALUES (%(query)s, %(language)s, %(variant)s, %(rating)s, %(nps)s, %(comment)s, "
            "%(days)s, %(candidate_count)s, %(cached)s, %(total_ms)s, %(evidence_grade)s, %(uncertainty_disclosed)s)"
        )
        evidence_grade = str(fb.get("evidence_grade") or "").strip()
        if evidence_grade not in _VALID_EVIDENCE_GRADES:
            evidence_grade = None
        uncertainty_disclosed = fb.get("uncertainty_disclosed")
        if uncertainty_disclosed is None:
            uncertainty_disclosed = None
        else:
            uncertainty_disclosed = bool(uncertainty_disclosed)
        try:
            with self._engine.begin() as conn:
                raw = conn.connection
                cur = raw.cursor()
                row["evidence_grade"] = evidence_grade
                row["uncertainty_disclosed"] = uncertainty_disclosed
                cur.execute(sql, row)
                cur.close()
            return True
        except Exception as exc:
            logger.warning("[tourism_kb.feedback] 저장 실패: %s", exc)
            return False

    # ── 집계 ─────────────────────────────────────────────────────────────
    @staticmethod
    def _nps_from_counts(promoters: int, passives: int, detractors: int) -> Optional[float]:
        total = promoters + passives + detractors
        if total <= 0:
            return None
        return round((promoters - detractors) * 100.0 / total, 1)

    def _variant_block(self, conn, variant: Optional[str]) -> Dict[str, Any]:
        where = ""
        params: tuple = ()
        if variant:
            where = " WHERE variant = %s"
            params = (variant,)
        raw = conn.connection
        cur = raw.cursor()
        try:
            cur.execute(
                "SELECT "
                "COUNT(*), "
                "COUNT(*) FILTER (WHERE rating = 'up'), "
                "COUNT(*) FILTER (WHERE rating = 'down'), "
                "COUNT(*) FILTER (WHERE nps BETWEEN 9 AND 10), "
                "COUNT(*) FILTER (WHERE nps BETWEEN 7 AND 8), "
                "COUNT(*) FILTER (WHERE nps BETWEEN 0 AND 6), "
                "AVG(nps), AVG(total_ms), "
                "COUNT(*) FILTER (WHERE evidence_grade = '확정'), "
                "COUNT(*) FILTER (WHERE evidence_grade = '추정'), "
                "COUNT(*) FILTER (WHERE evidence_grade = '미확인'), "
                "COUNT(*) FILTER (WHERE uncertainty_disclosed IS TRUE), "
                "COUNT(*) FILTER (WHERE uncertainty_disclosed IS NOT NULL) "
                "FROM tourism_answer_feedback" + where,
                params,
            )
            r = cur.fetchone() or (0, 0, 0, 0, 0, 0, None, None, 0, 0, 0, 0, 0)
        finally:
            cur.close()
        total, up, down, promoters, passives, detractors, avg_nps, avg_ms, grade_confirmed, grade_estimated, grade_unverified, uncertainty_true, uncertainty_total = r
        thumbs = (int(up) + int(down))
        return {
            "total": int(total or 0),
            "thumbs_up": int(up or 0),
            "thumbs_down": int(down or 0),
            "thumbs_up_rate": round(int(up) / thumbs, 4) if thumbs else None,
            "nps": self._nps_from_counts(int(promoters or 0), int(passives or 0), int(detractors or 0)),
            "nps_responses": int(promoters or 0) + int(passives or 0) + int(detractors or 0),
            "promoters": int(promoters or 0),
            "passives": int(passives or 0),
            "detractors": int(detractors or 0),
            "avg_nps": round(float(avg_nps), 2) if avg_nps is not None else None,
            "avg_total_ms": round(float(avg_ms), 1) if avg_ms is not None else None,
            "evidence_grades": {
                "확정": int(grade_confirmed or 0),
                "추정": int(grade_estimated or 0),
                "미확인": int(grade_unverified or 0),
            },
            "uncertainty_disclosure_rate": round(int(uncertainty_true) / int(uncertainty_total), 4) if int(uncertainty_total or 0) > 0 else None,
        }

    def stats(self) -> Dict[str, Any]:
        if not self._engine:
            return {"available": False}
        self.ensure_schema()
        try:
            with self._engine.connect() as conn:
                overall = self._variant_block(conn, None)
                by_variant = {v: self._variant_block(conn, v) for v in sorted(_VALID_VARIANTS)}
        except Exception as exc:
            logger.warning("[tourism_kb.feedback] stats 실패: %s", exc)
            return {"available": True, "error": "stats_unavailable"}
        return {"available": True, "overall": overall, "by_variant": by_variant}


def get_feedback_store() -> TourismFeedbackStore:
    return TourismFeedbackStore.shared()
