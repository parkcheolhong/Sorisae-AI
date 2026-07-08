"""소리새 AI 관광 지식 베이스(Tourism Knowledge Base).

마켓플레이스의 해시 스텁 VectorService 와 100% 분리된 전용 모듈.
합법 오픈데이터(OSM ODbL / Wikidata CC0 / 공공누리)만 적재·임베딩하여
friend-chat 그라운딩의 1차 소스로 사용한다.
"""

from backend.services.tourism_kb.service import (
    TourismEmbedder,
    TourismVectorStore,
    get_tourism_store,
    search_tourism_places,
    validate_places,
)
from backend.services.tourism_kb.graph import (
    TourismGraph,
    get_city_context,
    get_tourism_graph,
)

__all__ = [
    "TourismEmbedder",
    "TourismVectorStore",
    "get_tourism_store",
    "search_tourism_places",
    "validate_places",
    "TourismGraph",
    "get_tourism_graph",
    "get_city_context",
]
