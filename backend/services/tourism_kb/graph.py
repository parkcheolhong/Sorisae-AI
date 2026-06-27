"""관광 KG — 경량 그래프(순수 Postgres 인접테이블).

설계: docs/worldlinco-v2/TOURISM_AI_KNOWLEDGE_RAG_DESIGN.md §5-d ③.
- Neo4j/AGE 대신 Postgres 인접테이블로 시작(postgres:15-alpine 에 AGE 미설치 → 컴파일 회피).
- 관계: (City)-[HOSTS]->(Festival), (Region|City)-[FAMOUS_FOR]->(Food).
  POI 는 Qdrant(tourism_places)에 그대로 두고, POI↔도시는 좌표(bbox/근접)로 질의 시 연결한다.
- 기존 마켓플레이스 ORM 과 분리: 전용 테이블(tourism_city/festival/food)만 raw SQL 로 멱등 관리.
- DB 미연결/미설치 시 graceful: 모든 메서드가 [] / no-op (상위 그라운딩은 벡터·웹으로 폴백).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DDL = (
    """
    CREATE TABLE IF NOT EXISTS tourism_city (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        country_code TEXT,
        lat DOUBLE PRECISION,
        lon DOUBLE PRECISION
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tourism_festival (
        id TEXT PRIMARY KEY,
        city_id TEXT,
        name TEXT NOT NULL,
        season TEXT,
        month INTEGER,
        description TEXT,
        source TEXT,
        license TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tourism_festival_city ON tourism_festival (city_id)",
    """
    CREATE TABLE IF NOT EXISTS tourism_food (
        id TEXT PRIMARY KEY,
        scope_type TEXT NOT NULL,
        scope_code TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        source TEXT,
        license TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tourism_food_scope ON tourism_food (scope_type, scope_code)",
)


class TourismGraph:
    """관광 그래프(도시↔축제↔음식) 경량 래퍼. DB 미연결 시 비활성(graceful)."""

    _instance: Optional["TourismGraph"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._engine = None
        self._ensured = False
        self._connect()

    @classmethod
    def shared(cls) -> "TourismGraph":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _connect(self):
        try:
            from backend.marketplace.database import engine

            # 살아있는 엔진인지 가벼운 핑(드라이버 로딩/연결 확인).
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            self._engine = engine
        except Exception as exc:
            logger.warning("[tourism_kb.graph] DB 연결 실패(그래프 비활성): %s", exc)
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
            logger.warning("[tourism_kb.graph] 스키마 생성 실패: %s", exc)

    # ── 적재(멱등 upsert) ────────────────────────────────────────────────
    def upsert_cities(self, cities: List[Dict[str, Any]]) -> int:
        if not self._engine or not cities:
            return 0
        self.ensure_schema()
        sql = (
            "INSERT INTO tourism_city (id, name, country_code, lat, lon) "
            "VALUES (%(id)s, %(name)s, %(country_code)s, %(lat)s, %(lon)s) "
            "ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, "
            "country_code=EXCLUDED.country_code, lat=EXCLUDED.lat, lon=EXCLUDED.lon"
        )
        return self._executemany(sql, [
            {
                "id": str(c.get("id") or "").strip(),
                "name": str(c.get("name") or c.get("id") or "").strip(),
                "country_code": (str(c.get("country_code") or "").strip().upper() or None),
                "lat": _as_float(c.get("lat")),
                "lon": _as_float(c.get("lon")),
            }
            for c in cities if str(c.get("id") or "").strip()
        ])

    def upsert_festivals(self, festivals: List[Dict[str, Any]]) -> int:
        if not self._engine or not festivals:
            return 0
        self.ensure_schema()
        sql = (
            "INSERT INTO tourism_festival (id, city_id, name, season, month, description, source, license) "
            "VALUES (%(id)s, %(city_id)s, %(name)s, %(season)s, %(month)s, %(description)s, %(source)s, %(license)s) "
            "ON CONFLICT (id) DO UPDATE SET city_id=EXCLUDED.city_id, name=EXCLUDED.name, "
            "season=EXCLUDED.season, month=EXCLUDED.month, description=EXCLUDED.description, "
            "source=EXCLUDED.source, license=EXCLUDED.license"
        )
        return self._executemany(sql, [
            {
                "id": str(f.get("id") or "").strip(),
                "city_id": str(f.get("city_id") or "").strip() or None,
                "name": str(f.get("name") or "").strip(),
                "season": (str(f.get("season") or "").strip() or None),
                "month": _as_int(f.get("month")),
                "description": (str(f.get("description") or "").strip() or None),
                "source": (str(f.get("source") or "curated").strip() or None),
                "license": (str(f.get("license") or "").strip() or None),
            }
            for f in festivals if str(f.get("id") or "").strip() and str(f.get("name") or "").strip()
        ])

    def upsert_foods(self, foods: List[Dict[str, Any]]) -> int:
        if not self._engine or not foods:
            return 0
        self.ensure_schema()
        sql = (
            "INSERT INTO tourism_food (id, scope_type, scope_code, name, description, source, license) "
            "VALUES (%(id)s, %(scope_type)s, %(scope_code)s, %(name)s, %(description)s, %(source)s, %(license)s) "
            "ON CONFLICT (id) DO UPDATE SET scope_type=EXCLUDED.scope_type, scope_code=EXCLUDED.scope_code, "
            "name=EXCLUDED.name, description=EXCLUDED.description, source=EXCLUDED.source, license=EXCLUDED.license"
        )
        return self._executemany(sql, [
            {
                "id": str(f.get("id") or "").strip(),
                "scope_type": str(f.get("scope_type") or "country").strip().lower(),
                "scope_code": str(f.get("scope_code") or "").strip(),
                "name": str(f.get("name") or "").strip(),
                "description": (str(f.get("description") or "").strip() or None),
                "source": (str(f.get("source") or "curated").strip() or None),
                "license": (str(f.get("license") or "").strip() or None),
            }
            for f in foods if str(f.get("id") or "").strip() and str(f.get("name") or "").strip()
        ])

    def _executemany(self, sql: str, rows: List[Dict[str, Any]]) -> int:
        rows = [r for r in rows if r]
        if not rows:
            return 0
        try:
            with self._engine.begin() as conn:
                raw = conn.connection
                cur = raw.cursor()
                cur.executemany(sql, rows)
                cur.close()
            return len(rows)
        except Exception as exc:
            logger.warning("[tourism_kb.graph] upsert 실패: %s", exc)
            return 0

    # ── 질의 ────────────────────────────────────────────────────────────
    def _query(self, sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self._engine:
            return []
        self.ensure_schema()
        try:
            with self._engine.connect() as conn:
                result = conn.exec_driver_sql(sql, params)
                cols = list(result.keys())
                return [dict(zip(cols, row)) for row in result.fetchall()]
        except Exception as exc:
            logger.warning("[tourism_kb.graph] query 실패: %s", exc)
            return []

    def resolve_city(
        self,
        *,
        city_id: Optional[str] = None,
        name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """도시 해석: id 우선 → 이름(부분일치) → 좌표 근접(약 ±0.4°)."""
        if city_id:
            rows = self._query("SELECT * FROM tourism_city WHERE id = %(id)s", {"id": str(city_id).strip().lower()})
            if rows:
                return rows[0]
        if name:
            rows = self._query(
                "SELECT * FROM tourism_city WHERE LOWER(name) = LOWER(%(n)s) OR id = LOWER(%(n)s) LIMIT 1",
                {"n": str(name).strip()},
            )
            if rows:
                return rows[0]
        lat = _as_float(latitude)
        lon = _as_float(longitude)
        if lat is not None and lon is not None:
            rows = self._query(
                "SELECT *, (ABS(lat - %(lat)s) + ABS(lon - %(lon)s)) AS dist FROM tourism_city "
                "WHERE lat IS NOT NULL AND lon IS NOT NULL "
                "AND ABS(lat - %(lat)s) <= 0.6 AND ABS(lon - %(lon)s) <= 0.6 "
                "ORDER BY dist ASC LIMIT 1",
                {"lat": lat, "lon": lon},
            )
            if rows:
                return rows[0]
        return None

    def city_festivals(self, city_id: str, *, month: Optional[int] = None) -> List[Dict[str, Any]]:
        cid = str(city_id or "").strip().lower()
        if not cid:
            return []
        if month is not None:
            return self._query(
                "SELECT * FROM tourism_festival WHERE city_id = %(cid)s AND (month = %(m)s OR month IS NULL) "
                "ORDER BY month NULLS LAST, name",
                {"cid": cid, "m": int(month)},
            )
        return self._query(
            "SELECT * FROM tourism_festival WHERE city_id = %(cid)s ORDER BY month NULLS LAST, name",
            {"cid": cid},
        )

    def region_foods(self, country_code: Optional[str], *, city_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cc = str(country_code or "").strip().upper()
        cid = str(city_id or "").strip().lower()
        return self._query(
            "SELECT * FROM tourism_food WHERE "
            "(scope_type = 'country' AND scope_code = %(cc)s) OR "
            "(scope_type = 'city' AND scope_code = %(cid)s) "
            "ORDER BY (scope_type = 'city') DESC, name",
            {"cc": cc, "cid": cid},
        )

    def city_context(
        self,
        *,
        city_id: Optional[str] = None,
        name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        month: Optional[int] = None,
    ) -> Dict[str, Any]:
        """도시 1곳의 관계 컨텍스트: {city, festivals[], foods[]}. 미해석 시 빈 구조."""
        city = self.resolve_city(city_id=city_id, name=name, latitude=latitude, longitude=longitude)
        if not city:
            return {"city": None, "festivals": [], "foods": []}
        cid = str(city.get("id"))
        return {
            "city": city,
            "festivals": self.city_festivals(cid, month=month),
            "foods": self.region_foods(city.get("country_code"), city_id=cid),
        }


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


_graph_singleton: Optional[TourismGraph] = None
_graph_lock = threading.Lock()


def get_tourism_graph() -> TourismGraph:
    global _graph_singleton
    with _graph_lock:
        if _graph_singleton is None:
            _graph_singleton = TourismGraph()
        return _graph_singleton


def get_city_context(
    *,
    city_id: Optional[str] = None,
    name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    month: Optional[int] = None,
) -> Dict[str, Any]:
    """편의 함수 — 미가동 시 빈 구조(상위에서 무시)."""
    try:
        graph = get_tourism_graph()
        if not graph.available:
            return {"city": None, "festivals": [], "foods": []}
        return graph.city_context(
            city_id=city_id, name=name, latitude=latitude, longitude=longitude, month=month
        )
    except Exception as exc:
        logger.warning("[tourism_kb.graph] get_city_context 실패: %s", exc)
        return {"city": None, "festivals": [], "foods": []}
