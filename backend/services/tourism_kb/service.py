"""관광 KB — 실 임베딩 + Qdrant 벡터 검색(마켓플레이스 스텁과 분리).

설계 근거: docs/worldlinco-v2/TOURISM_AI_KNOWLEDGE_RAG_DESIGN.md
- 임베딩: 다국어 sentence-transformers(기본 paraphrase-multilingual-MiniLM-L12-v2, 384d).
  대면/소리새 AI 는 한·일·중·영 등 다국어 질의가 많아 다국어 모델을 기본으로 한다.
- 저장: Qdrant 컬렉션 'tourism_places'. payload 에 출처/라이선스를 함께 보관해
  ODbL share-alike·출처표기 의무를 추적한다.
- 모든 의존성은 지연 로딩(lazy) + 실패 시 graceful 폴백 → 미설치 환경에서도 import 안전.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 기본 임베딩: multilingual-e5-large(1024d). 다국어 검색 품질이 MiniLM 대비 크게 우수하다.
# e5 계열은 'query:'/'passage:' 프리픽스를 요구하므로 encode 에서 자동 부착한다.
TOURISM_EMBED_MODEL = os.getenv("TOURISM_EMBED_MODEL", "intfloat/multilingual-e5-large")
TOURISM_EMBED_DIM = int(os.getenv("TOURISM_EMBED_DIM", "1024"))
TOURISM_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
TOURISM_COLLECTION = os.getenv("TOURISM_COLLECTION", "tourism_places")

# Hybrid 검색(BM25 sparse + dense, RRF 융합). dense=의미(다국어), sparse=고유명사·숫자·외래어
# 정확매칭. 끄면 dense 단독. Qdrant/bm25 는 언어무관 BM25 — 서버측 IDF(Modifier.IDF)와 결합.
TOURISM_HYBRID = os.getenv("TOURISM_HYBRID", "1").lower() in ("1", "true", "yes", "on")
TOURISM_SPARSE_MODEL = os.getenv("TOURISM_SPARSE_MODEL", "Qdrant/bm25")
_DENSE = "dense"   # named dense 벡터 이름
_SPARSE = "sparse"  # named sparse 벡터 이름
# 멀티모달 CLIP 은 본 컬렉션에 named vector 를 추가(in-place)할 수 없어(qdrant-client 제약)
# 별도 컬렉션('tourism_places_clip', 512d 단일벡터, 동일 point id)에 보관하고 검색은 RRF 로 병합.
TOURISM_CLIP_COLLECTION = os.getenv("TOURISM_CLIP_COLLECTION", f"{TOURISM_COLLECTION}_clip")


class TourismEmbedder:
    """다국어 문장 임베딩. 기본 백엔드는 fastembed(ONNX, torch 불필요)로,
    토치가 깨진 환경(예: 일부 Windows/Python 3.13)에서도 동작한다.
    fastembed 미설치 시 sentence-transformers(torch)로 폴백.
    모델은 최초 사용 시 1회 로드(lazy)."""

    _instance: Optional["TourismEmbedder"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: str = TOURISM_EMBED_MODEL):
        # fastembed 는 'sentence-transformers/' 프리픽스 없는 이름도 동일 모델로 인식.
        self.model_name = model_name
        self._model = None
        self._backend: Optional[str] = None  # 'fastembed' | 'sentence_transformers'

    @classmethod
    def shared(cls) -> "TourismEmbedder":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        # 1순위: fastembed(ONNX) — torch 불필요.
        try:
            from fastembed import TextEmbedding

            logger.info("[tourism_kb] fastembed 임베딩 로드: %s", self.model_name)
            self._model = TextEmbedding(model_name=self.model_name)
            self._backend = "fastembed"
            return self._model
        except Exception as exc:
            logger.warning("[tourism_kb] fastembed 로드 실패, sentence-transformers 폴백: %s", exc)
        # 2순위: sentence-transformers(torch).
        from sentence_transformers import SentenceTransformer

        logger.info("[tourism_kb] sentence-transformers 임베딩 로드: %s", self.model_name)
        self._model = SentenceTransformer(self.model_name)
        self._backend = "sentence_transformers"
        return self._model

    @property
    def dim(self) -> int:
        try:
            self._ensure_model()
            probe = self.encode(["_dim_probe_"])
            if probe and probe[0]:
                return len(probe[0])
        except Exception:
            pass
        return TOURISM_EMBED_DIM

    @staticmethod
    def _normalize(vec: List[float]) -> List[float]:
        norm = sum(x * x for x in vec) ** 0.5
        if norm <= 0:
            return vec
        return [x / norm for x in vec]

    @property
    def _is_e5(self) -> bool:
        return "e5" in self.model_name.lower()

    def _apply_prefix(self, texts: List[str], is_query: bool) -> List[str]:
        # e5 계열은 비대칭 프리픽스 필수: 질의='query: ', 문서='passage: '.
        if not self._is_e5:
            return list(texts)
        tag = "query: " if is_query else "passage: "
        return [tag + str(t) for t in texts]

    def encode(self, texts: List[str], *, is_query: bool = False, batch_size: int = 64) -> List[List[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        prepared = self._apply_prefix(list(texts), is_query)
        if self._backend == "fastembed":
            out = [list(map(float, v)) for v in model.embed(prepared, batch_size=batch_size)]
            return [self._normalize(v) for v in out]
        vectors = model.encode(
            prepared,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]

    def encode_one(self, text: str, *, is_query: bool = False) -> List[float]:
        out = self.encode([text], is_query=is_query)
        return out[0] if out else []


class TourismSparseEmbedder:
    """BM25 희소 임베딩(fastembed 'Qdrant/bm25', 언어무관).
    고유명사·숫자·외래어 정확매칭을 dense 의미검색에 보강한다.
    미설치/로드 실패 시 unavailable → dense 단독으로 graceful 폴백."""

    _instance: Optional["TourismSparseEmbedder"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: str = TOURISM_SPARSE_MODEL):
        self.model_name = model_name
        self._model = None
        self._unavailable = False

    @classmethod
    def shared(cls) -> "TourismSparseEmbedder":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _ensure(self):
        if self._model is not None or self._unavailable:
            return self._model
        try:
            from fastembed import SparseTextEmbedding

            logger.info("[tourism_kb] BM25 sparse 임베딩 로드: %s", self.model_name)
            self._model = SparseTextEmbedding(model_name=self.model_name)
        except Exception as exc:
            logger.warning("[tourism_kb] sparse 임베딩 로드 실패(dense 단독): %s", exc)
            self._unavailable = True
            self._model = None
        return self._model

    @property
    def available(self) -> bool:
        return self._ensure() is not None

    def embed(self, texts: List[str], *, is_query: bool = False) -> List[tuple]:
        """반환: [(indices:list[int], values:list[float]), ...]. 미가동 시 []."""
        model = self._ensure()
        if model is None or not texts:
            return []
        try:
            gen = model.query_embed(list(texts)) if is_query else model.embed(list(texts))
            out = []
            for e in gen:
                out.append((list(map(int, e.indices)), list(map(float, e.values))))
            return out
        except Exception as exc:
            logger.warning("[tourism_kb] sparse embed 실패: %s", exc)
            return []


# 질의 불용어(요청/위치 필러). 임베딩 전에 제거해 핵심 명사(라멘/약국 등)에 집중시킨다.
# 위치 의도는 좌표 지오필터가 따로 처리하므로 '근처/near me' 류를 빼도 정확도 손실이 없다.
_QUERY_FILLER = (
    "근처에", "근처", "주변에", "주변", "여기서", "여기", "이근처", "이 근처", "가까운", "가까이",
    "알려줘", "알려주세요", "알려 줘", "추천해줘", "추천해 줘", "추천 좀", "추천", "찾아줘", "찾아 줘",
    "찾아주세요", "어디야", "어디에", "어디", "좀", "있어", "있나요", "있을까", "가고 싶어", "가고싶어",
    "near me", "nearby", "near here", "around here", "please", "find me", "find", "show me",
    "recommend", "where is", "where can i", "i want to", "can you",
)


def _normalize_query(text: str) -> str:
    norm = " ".join(str(text or "").split())
    low = norm.lower()
    for f in _QUERY_FILLER:
        low = low.replace(f, " ")
    cleaned = " ".join(low.split())
    # 모두 제거돼 비면 원문 유지(불용어만 있던 게 아니라면 손실 방지).
    return cleaned if cleaned else norm


def _rrf_merge(lists: List[List[Any]], top: int, *, k: int = 60) -> tuple:
    """여러 검색 결과 리스트를 Reciprocal Rank Fusion 으로 병합(클라이언트측).
    반환: (ordered_points, scores_by_id). 먼저 등장한 리스트(주 검색)의 point 객체를
    우선 보존(payload 가 더 풍부)하고, 동일 id 는 RRF 점수를 합산한다."""
    scores: Dict[Any, float] = {}
    best_obj: Dict[Any, Any] = {}
    for lst in lists:
        for rank, h in enumerate(lst or []):
            pid = getattr(h, "id", None)
            if pid is None:
                continue
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (k + rank + 1)
            if pid not in best_obj:
                best_obj[pid] = h
    ordered_ids = sorted(scores.keys(), key=lambda p: scores[p], reverse=True)[: max(1, top)]
    return [best_obj[pid] for pid in ordered_ids], scores


def _stable_point_id(source: str, source_id: str) -> int:
    """소스+소스ID 로 결정적(idempotent) 64bit 양수 ID 생성(재적재 시 중복 방지)."""
    raw = f"{source}:{source_id}".encode("utf-8")
    return int(hashlib.sha1(raw).hexdigest(), 16) % (2**63)


# 알려진 카테고리 화이트리스트(QC 게이트) — 적재기 CATEGORY_SYNONYMS/OSM_CATEGORY_CAPS 와 정합.
# 미지정 카테고리는 '경고'만 집계하고 드롭하지 않는다(신규 종류 유입 차단 방지).
_KNOWN_CATEGORIES = {
    "restaurant", "cafe", "fast_food", "bar", "pharmacy", "hospital", "bank", "atm",
    "police", "marketplace", "hotel", "hostel", "guest_house", "attraction", "museum",
    "gallery", "viewpoint", "theme_park", "zoo", "aquarium",
}


def validate_places(
    places: List[Dict[str, Any]],
    *,
    bbox: Optional[tuple] = None,
    bbox_margin_deg: float = 0.02,
    max_drop_rate: float = 0.9,
    min_valid: int = 5,
) -> tuple:
    """적재 전 데이터 품질 게이트(설계 §5-d ④). 반환: (clean_places, report).

    검사: (1) 이름 누락 (2) 좌표 누락/비정상 (3) bbox 범위 밖(여유 margin 허용)
    (4) (source, source_id) 중복 (5) 미지정 카테고리(경고만). report['blocked']=True 면
    상위에서 적재를 중단해야 한다(데이터 소스 이상으로 품질이 무너진 경우).
    bbox=(south, west, north, east)."""
    total = len(places or [])
    report: Dict[str, Any] = {
        "total": total, "kept": 0, "dropped": 0, "reasons": {},
        "unknown_category": 0, "drop_rate": 0.0, "blocked": False,
    }
    if total == 0:
        report["blocked"] = True
        return [], report

    south = west = north = east = None
    if bbox and len(bbox) == 4:
        try:
            south, west, north, east = (float(x) for x in bbox)
            south -= bbox_margin_deg
            west -= bbox_margin_deg
            north += bbox_margin_deg
            east += bbox_margin_deg
        except (TypeError, ValueError):
            south = west = north = east = None

    def _bump(reason: str):
        report["reasons"][reason] = report["reasons"].get(reason, 0) + 1
        report["dropped"] += 1

    seen: set = set()
    clean: List[Dict[str, Any]] = []
    for p in places:
        name = str(p.get("name") or "").strip()
        if not name:
            _bump("null_name")
            continue
        try:
            latf = float(p.get("lat"))
            lonf = float(p.get("lon"))
        except (TypeError, ValueError):
            _bump("null_coord")
            continue
        if not (-90.0 <= latf <= 90.0 and -180.0 <= lonf <= 180.0):
            _bump("invalid_coord")
            continue
        if south is not None and not (south <= latf <= north and west <= lonf <= east):
            _bump("out_of_bbox")
            continue
        key = (str(p.get("source") or "osm"), str(p.get("source_id") or name))
        if key in seen:
            _bump("dup")
            continue
        seen.add(key)
        cat = str(p.get("category") or "").strip()
        if cat and cat not in _KNOWN_CATEGORIES:
            report["unknown_category"] += 1
        clean.append(p)

    report["kept"] = len(clean)
    report["drop_rate"] = round(report["dropped"] / total, 3) if total else 0.0
    if len(clean) < min_valid or report["drop_rate"] > max_drop_rate:
        report["blocked"] = True
    return clean, report


class TourismVectorStore:
    """Qdrant 'tourism_places' 컬렉션 래퍼. 미연결/미설치 시 graceful 비활성."""

    def __init__(
        self,
        embedder: Optional[TourismEmbedder] = None,
        *,
        url: str = TOURISM_QDRANT_URL,
        collection: str = TOURISM_COLLECTION,
    ):
        self.embedder = embedder or TourismEmbedder.shared()
        self.url = url
        self.collection = collection
        self.hybrid = TOURISM_HYBRID
        self.sparse = TourismSparseEmbedder.shared() if TOURISM_HYBRID else None
        self.clip = None  # 멀티모달(CLIP) 임베더 — 지연 로딩.
        self.client = None
        self._connect()

    @property
    def _use_sparse(self) -> bool:
        return bool(self.hybrid and self.sparse is not None and self.sparse.available)

    @property
    def _use_clip(self) -> bool:
        """멀티모달 CLIP 검색 경로 가용성(플래그 ON + 임베더 로드 성공)."""
        from backend.services.tourism_kb.multimodal import TOURISM_CLIP_ENABLED, get_clip_embedder

        if not TOURISM_CLIP_ENABLED:
            return False
        if self.clip is None:
            self.clip = get_clip_embedder()
        return self.clip.available

    def _connect(self):
        try:
            from qdrant_client import QdrantClient

            self.client = QdrantClient(url=self.url, timeout=5.0)
        except Exception as exc:  # 미설치/미연결 → 비활성(폴백)
            logger.warning("[tourism_kb] Qdrant 연결 실패(폴백 동작): %s", exc)
            self.client = None

    @property
    def available(self) -> bool:
        return self.client is not None

    def ensure_collection(self, dim: Optional[int] = None):
        if not self.client:
            return
        from qdrant_client.models import Distance, VectorParams

        vec_dim = dim or self.embedder.dim
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection not in existing:
            # named dense('dense') + sparse('sparse', BM25/IDF) — Hybrid RRF 용.
            vectors_config = {_DENSE: VectorParams(size=vec_dim, distance=Distance.COSINE)}
            sparse_config = None
            if self._use_sparse:
                from qdrant_client.models import (
                    Modifier,
                    SparseIndexParams,
                    SparseVectorParams,
                )

                sparse_config = {
                    _SPARSE: SparseVectorParams(index=SparseIndexParams(), modifier=Modifier.IDF)
                }
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_config,
            )
            logger.info(
                "[tourism_kb] 컬렉션 생성: %s (dim=%d, hybrid=%s)",
                self.collection, vec_dim, bool(sparse_config),
            )
        # 지오 필터('near me')용 location payload 인덱스(멱등 — 이미 있으면 무시).
        try:
            from qdrant_client.models import PayloadSchemaType

            self.client.create_payload_index(
                collection_name=self.collection,
                field_name="location",
                field_schema=PayloadSchemaType.GEO,
            )
        except Exception:
            pass

    def recreate(self, dim: Optional[int] = None):
        """컬렉션을 삭제 후 재생성(적재 편향/차원 변경 시 초기화용)."""
        if not self.client:
            return
        try:
            self.client.delete_collection(collection_name=self.collection)
        except Exception:
            pass
        self.ensure_collection(dim=dim)

    # ── 멀티모달 CLIP(별도 컬렉션) ───────────────────────────────────────
    def ensure_clip_collection(self):
        """CLIP 이미지 벡터 전용 컬렉션('..._clip', 512d 단일벡터) 멱등 생성."""
        if not self.client:
            return
        from qdrant_client.models import Distance, VectorParams
        from backend.services.tourism_kb.multimodal import TOURISM_CLIP_DIM

        existing = {c.name for c in self.client.get_collections().collections}
        if TOURISM_CLIP_COLLECTION not in existing:
            self.client.create_collection(
                collection_name=TOURISM_CLIP_COLLECTION,
                vectors_config=VectorParams(size=TOURISM_CLIP_DIM, distance=Distance.COSINE),
            )
            logger.info("[tourism_kb] CLIP 컬렉션 생성: %s (dim=%d)", TOURISM_CLIP_COLLECTION, TOURISM_CLIP_DIM)
        try:
            from qdrant_client.models import PayloadSchemaType

            self.client.create_payload_index(
                collection_name=TOURISM_CLIP_COLLECTION,
                field_name="location",
                field_schema=PayloadSchemaType.GEO,
            )
        except Exception:
            pass

    def index_clip_images(self, items: List[Dict[str, Any]]) -> int:
        """items: [{id, vector(512d), payload}] → CLIP 컬렉션 upsert. 반환=적재 건수."""
        if not self.client or not items:
            return 0
        from qdrant_client.models import PointStruct

        self.ensure_clip_collection()
        points = []
        for it in items:
            vec = it.get("vector")
            if not vec:
                continue
            points.append(PointStruct(id=it["id"], vector=vec, payload=it.get("payload") or {}))
        if not points:
            return 0
        self.client.upsert(collection_name=TOURISM_CLIP_COLLECTION, points=points)
        return len(points)

    def backfill_clip_vectors(self, *, limit: int = 0, batch: int = 64, progress: bool = False) -> Dict[str, Any]:
        """본 컬렉션을 스캔해 이미지 참조(commons/wikidata)가 있는 POI 의 대표 이미지를
        CLIP-vision 으로 임베딩 → CLIP 컬렉션에 적재. 저작권 게이트 통과 이미지만 사용.

        반환: {scanned, with_media, embedded, indexed}. limit=0 이면 전체.
        """
        report = {"scanned": 0, "with_media": 0, "embedded": 0, "indexed": 0}
        if not self.client:
            return report
        from backend.services.tourism_kb.multimodal import get_clip_embedder
        from backend.services.tourism_media import has_media_ref, place_media

        clip = get_clip_embedder()
        self.ensure_clip_collection()

        offset = None
        pending: List[Dict[str, Any]] = []

        def _flush() -> None:
            if pending:
                report["indexed"] += self.index_clip_images(pending)
                pending.clear()

        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not points:
                break
            for pt in points:
                report["scanned"] += 1
                payload = dict(pt.payload or {})
                if not has_media_ref(payload):
                    continue
                report["with_media"] += 1
                media = place_media(payload, max_items=1)
                if not media:
                    continue
                url = media[0].get("url")
                vec = clip.embed_image_url(str(url)) if url else []
                if not vec:
                    continue
                report["embedded"] += 1
                keep = {k: payload.get(k) for k in (
                    "source", "source_id", "name", "lat", "lon", "category",
                    "address", "country", "license", "wikidata", "wikimedia_commons",
                ) if payload.get(k) is not None}
                if payload.get("lat") is not None and payload.get("lon") is not None:
                    try:
                        keep["location"] = {"lat": float(payload["lat"]), "lon": float(payload["lon"])}
                    except (TypeError, ValueError):
                        pass
                keep["clip_image_url"] = url
                pending.append({"id": pt.id, "vector": vec, "payload": keep})
                if len(pending) >= batch:
                    _flush()
                if progress and report["scanned"] % 500 == 0:
                    logger.info("[tourism_kb] CLIP 백필 진행: %s", report)
            if limit and report["scanned"] >= limit:
                break
            if offset is None:
                break
        _flush()
        logger.info("[tourism_kb] CLIP 백필 완료: %s", report)
        return report

    def upsert_places(self, places: List[Dict[str, Any]]) -> int:
        """places: [{source, source_id, name, lat, lon, category, address, country,
        license, phone, hours, website, text}] → 임베딩 후 upsert. 반환=적재 건수."""
        if not self.client or not places:
            return 0
        from qdrant_client.models import PointStruct

        self.ensure_collection()
        texts = []
        for p in places:
            text = p.get("text") or " · ".join(
                str(p.get(k) or "").strip()
                for k in ("name", "category", "address", "country")
                if p.get(k)
            )
            texts.append(text or str(p.get("name") or ""))
        vectors = self.embedder.encode(texts)
        # BM25 sparse 동시 적재(가용 시). dense 와 동일 순서로 정렬됨.
        use_sparse = self._use_sparse
        sparse_vectors = self.sparse.embed(texts, is_query=False) if use_sparse else []
        sparse_ok = use_sparse and len(sparse_vectors) == len(places)
        if use_sparse and not sparse_ok:
            logger.warning("[tourism_kb] sparse 개수 불일치(dense 단독 적재): %d/%d",
                           len(sparse_vectors), len(places))
        points = []
        for i, (p, vec) in enumerate(zip(places, vectors)):
            if not vec:
                continue
            pid = _stable_point_id(str(p.get("source") or "osm"), str(p.get("source_id") or p.get("name")))
            payload = {k: p.get(k) for k in (
                "source", "source_id", "name", "lat", "lon", "category",
                "address", "country", "license", "phone", "hours", "website",
                # 콘텐츠 저작권 게이트 실연동용 이미지 참조(있을 때만 저장).
                "wikidata", "wikimedia_commons",
            ) if p.get(k) is not None}
            # Qdrant 지오 필터용 정식 location 필드(lat/lon 동시 존재 시).
            if p.get("lat") is not None and p.get("lon") is not None:
                try:
                    payload["location"] = {"lat": float(p["lat"]), "lon": float(p["lon"])}
                except (TypeError, ValueError):
                    pass
            vector_payload: Any = {_DENSE: vec}
            if sparse_ok:
                idx, val = sparse_vectors[i]
                if idx:
                    from qdrant_client.models import SparseVector

                    vector_payload[_SPARSE] = SparseVector(indices=idx, values=val)
            points.append(PointStruct(id=pid, vector=vector_payload, payload=payload))
        if not points:
            return 0
        self.client.upsert(collection_name=self.collection, points=points)
        return len(points)

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 30.0,
    ) -> List[Dict[str, Any]]:
        if not self.client or not str(query or "").strip():
            return []
        query = _normalize_query(query)
        # (검색 질의는 아래 encode_one(is_query=True) 로 e5 'query:' 프리픽스 적용)
        try:
            from qdrant_client.models import (
                FieldCondition,
                Filter,
                GeoBoundingBox,
                GeoPoint,
            )
        except Exception:
            Filter = None  # type: ignore
        qvec = self.embedder.encode_one(query, is_query=True)
        if not qvec:
            return []
        query_filter = None
        if latitude is not None and longitude is not None and Filter is not None:
            try:
                d = radius_km / 111.0  # 위도 1도 ≈ 111km 근사
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="location",
                            geo_bounding_box=GeoBoundingBox(
                                top_left=GeoPoint(lon=float(longitude) - d, lat=float(latitude) + d),
                                bottom_right=GeoPoint(lon=float(longitude) + d, lat=float(latitude) - d),
                            ),
                        )
                    ]
                )
            except Exception:
                query_filter = None
        top = max(1, int(limit))

        def _dense_query(use_filter: bool):
            # named 벡터이므로 using='dense' 지정 필수.
            return self.client.query_points(
                collection_name=self.collection,
                query=qvec,
                using=_DENSE,
                limit=top,
                query_filter=query_filter if use_filter else None,
                with_payload=True,
            ).points

        def _hybrid_query(use_filter: bool):
            from qdrant_client.models import Fusion, FusionQuery, Prefetch, SparseVector

            flt = query_filter if use_filter else None
            depth = max(20, top * 4)
            prefetch = [Prefetch(query=qvec, using=_DENSE, limit=depth, filter=flt)]
            sp = self.sparse.embed([query], is_query=True)
            if sp and sp[0][0]:
                idx, val = sp[0]
                prefetch.append(Prefetch(
                    query=SparseVector(indices=idx, values=val),
                    using=_SPARSE, limit=depth, filter=flt,
                ))
            return self.client.query_points(
                collection_name=self.collection,
                prefetch=prefetch,
                query=FusionQuery(fusion=Fusion.RRF),
                limit=top,
                with_payload=True,
            ).points

        def _clip_query(use_filter: bool):
            """별도 CLIP 컬렉션을 질의(텍스트→이미지 정렬 공간). 단일벡터라 using 불필요."""
            qv = self.clip.embed_text_one(query) if self.clip else []
            if not qv:
                return []
            flt = query_filter if use_filter else None
            try:
                pts = self.client.query_points(
                    collection_name=TOURISM_CLIP_COLLECTION,
                    query=qv, limit=max(20, top * 4), query_filter=flt, with_payload=True,
                ).points
            except Exception as exc:
                logger.warning("[tourism_kb] clip query 실패: %s", exc)
                return []
            if not pts and flt is not None:
                try:
                    pts = self.client.query_points(
                        collection_name=TOURISM_CLIP_COLLECTION,
                        query=qv, limit=max(20, top * 4), query_filter=None, with_payload=True,
                    ).points
                except Exception:
                    pts = []
            return pts

        run = _hybrid_query if self._use_sparse else _dense_query
        hits = []
        try:
            hits = run(use_filter=query_filter is not None)
        except Exception as exc:
            logger.warning("[tourism_kb] %s search 실패(dense 폴백): %s",
                           "hybrid" if run is _hybrid_query else "dense", exc)
            # hybrid 실패 시 dense 단독으로 한 번 더 시도.
            if run is _hybrid_query:
                try:
                    hits = _dense_query(use_filter=query_filter is not None)
                except Exception:
                    hits = []
        # 지오 필터 결과가 비면(필드 미인덱스/범위밖) 무필터로 폴백 — 의미검색은 살린다.
        if not hits and query_filter is not None:
            try:
                hits = run(use_filter=False)
            except Exception:
                try:
                    hits = _dense_query(use_filter=False)
                except Exception:
                    return []

        # 멀티모달 CLIP 융합: 텍스트→이미지 정렬 검색 결과를 RRF 로 병합(가용 시).
        merged_scores: Optional[Dict[Any, float]] = None
        if self._use_clip:
            try:
                clip_hits = _clip_query(use_filter=query_filter is not None)
            except Exception:
                clip_hits = []
            if clip_hits:
                hits, merged_scores = _rrf_merge([hits, clip_hits], top)

        results = []
        for h in hits:
            payload = dict(h.payload or {})
            if merged_scores is not None:
                payload["score"] = round(float(merged_scores.get(h.id, 0.0)), 6)
            else:
                payload["score"] = float(getattr(h, "score", 0.0) or 0.0)
            # 콘텐츠 저작권 게이트: 미디어성 필드가 있으면 허용 라이선스 + 출처표기 통과분만 노출.
            if any(k in payload for k in ("media", "image", "image_url")):
                try:
                    from backend.services.media_license import gate_payload_media

                    payload["media"] = gate_payload_media(payload)
                except Exception:
                    payload["media"] = []
            results.append(payload)
        return results


_store_singleton: Optional[TourismVectorStore] = None
_store_lock = threading.Lock()


def get_tourism_store() -> TourismVectorStore:
    global _store_singleton
    with _store_lock:
        if _store_singleton is None:
            _store_singleton = TourismVectorStore()
        return _store_singleton


def search_tourism_places(
    query: str,
    *,
    limit: int = 5,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """friend-chat 그라운딩용 편의 함수. 미가동 시 빈 리스트(상위에서 OSM/웹 폴백)."""
    try:
        store = get_tourism_store()
        if not store.available:
            return []
        return store.search(query, limit=limit, latitude=latitude, longitude=longitude)
    except Exception as exc:
        logger.warning("[tourism_kb] search_tourism_places 실패(폴백): %s", exc)
        return []
