"""
Qdrant 벡터 DB 서비스 (의미론적 검색)
- 주의: sentence-transformers 대신 간단한 텍스트 기반 검색 사용
- 실제 배포 시: sentence-transformers 또는 다른 임베딩 모델 사용
"""

import hashlib
import os
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class VectorService:
    """Qdrant 벡터 검색 서비스 (시뮬레이션)"""

    @staticmethod
    def _collection_stat(
        collection,
        primary_key: str,
        fallback_key: str = None,
    ):
        primary_value = getattr(collection, primary_key, None)
        if primary_value is not None:
            return primary_value
        if fallback_key:
            fallback_value = getattr(collection, fallback_key, None)
            if fallback_value is not None:
                return fallback_value

        if hasattr(collection, "model_dump"):
            payload = collection.model_dump()
            result = (
                payload.get("result") if isinstance(payload, dict) else None
            )
            if isinstance(result, dict):
                if primary_key in result:
                    return result.get(primary_key)
                if fallback_key and fallback_key in result:
                    return result.get(fallback_key)
            if isinstance(payload, dict):
                if primary_key in payload:
                    return payload.get(primary_key)
                if fallback_key and fallback_key in payload:
                    return payload.get(fallback_key)
        return 0

    def __init__(self):
        """Qdrant 클라이언트 초기화"""
        self.client = None
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_prefer_grpc = str(os.getenv("QDRANT_PREFER_GRPC") or "false").strip().lower() in {"1", "true", "yes", "on"}
        self._connect()

    def _connect(self):
        try:
            self.client = QdrantClient(
                url=self.qdrant_url,
                prefer_grpc=self.qdrant_prefer_grpc,
                timeout=5.0,
            )

            # 컬렉션 확인
            self._ensure_collections()
            print("✅ Qdrant 연결 성공")
        except Exception as e:
            print(f"❌ Qdrant 연결 실패: {e}")
            self.client = None

    def _ensure_collections(self):
        """필요한 컬렉션 생성 (미존재 시)"""
        collections = ["projects", "reviews"]

        for collection_name in collections:
            try:
                self.client.get_collection(collection_name)
            except Exception:
                # 컬렉션 생성 (384차원 - 임베딩 시뮬레이션)
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=384,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"✅ 컬렉션 생성: {collection_name}")

    def _text_to_vector(self, text: str) -> List[float]:
        """텍스트를 벡터로 변환 (해시 기반 시뮬레이션)"""
        # 실제 환경에서는 sentence-transformers 또는 다른 모델 사용
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # 384차원 벡터 생성 (정규화됨)
        vector = []
        for i in range(384):
            byte_val = hash_bytes[i % len(hash_bytes)]
            vector.append((byte_val - 128) / 128.0)
        return vector

    def index_project(self, project_id: int, title: str, description: str):
        """프로젝트 벡터 인덱싱"""
        if not self.client:
            self._connect()
        if not self.client:
            return False

        try:
            # 텍스트 결합 및 벡터 생성
            text = f"{title} {description}"
            vector = self._text_to_vector(text)

            # Qdrant에 저장
            self.client.upsert(
                collection_name="projects",
                points=[
                    PointStruct(
                        id=project_id,
                        vector=vector,
                        payload={
                            "project_id": project_id,
                            "title": title,
                            "description": description,
                        },
                    )
                ],
            )
            return True
        except Exception as e:
            print(f"❌ 프로젝트 인덱싱 실패 ({project_id}): {e}")
            return False

    def search_projects(self, query: str, limit: int = 10) -> List[dict]:
        """프로젝트 검색 (텍스트 기반)"""
        if not self.client:
            self._connect()
        if not self.client:
            return []

        try:
            # 쿼리 벡터 생성
            query_vector = self._text_to_vector(query)

            # qdrant-client 1.17+ removes `search`; prefer `query_points` and
            # keep backward compatibility for older client versions.
            if hasattr(self.client, "query_points"):
                query_response = self.client.query_points(
                    collection_name="projects",
                    query=query_vector,
                    limit=limit,
                    score_threshold=0.1,
                )
                search_results = getattr(query_response, "points", []) or []
            else:
                search_results = self.client.search(
                    collection_name="projects",
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=0.1,
                )

            # 결과 포맷팅
            results = []
            for result in search_results:
                results.append({
                    "project_id": result.payload["project_id"],
                    "title": result.payload["title"],
                    "description": result.payload["description"],
                    "score": result.score,
                })

            return results
        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            return []

    def index_review(self, review_id: int, comment: str, project_id: int):
        """리뷰 벡터 인덱싱"""
        if not self.client:
            self._connect()
        if not self.client:
            return False

        try:
            vector = self._text_to_vector(comment)

            self.client.upsert(
                collection_name="reviews",
                points=[
                    PointStruct(
                        id=review_id,
                        vector=vector,
                        payload={
                            "review_id": review_id,
                            "comment": comment,
                            "project_id": project_id,
                        },
                    )
                ],
            )
            return True
        except Exception as e:
            print(f"❌ 리뷰 인덱싱 실패 ({review_id}): {e}")
            return False

    def search_reviews(
        self,
        query: str,
        project_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[dict]:
        """리뷰 검색"""
        if not self.client:
            self._connect()
        if not self.client:
            return []

        try:
            query_vector = self._text_to_vector(query)

            search_results = self.client.search(
                collection_name="reviews",
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.1,
            )

            results = []
            for result in search_results:
                # 프로젝트 필터 적용
                if project_id and result.payload["project_id"] != project_id:
                    continue
                results.append({
                    "review_id": result.payload["review_id"],
                    "comment": result.payload["comment"],
                    "project_id": result.payload["project_id"],
                    "score": result.score,
                })

            return results[:limit]
        except Exception as e:
            print(f"❌ 리뷰 검색 실패: {e}")
            return []

    def delete_project(self, project_id: int) -> bool:
        """프로젝트 벡터 삭제"""
        if not self.client:
            self._connect()
        if not self.client:
            return False

        try:
            self.client.delete(
                collection_name="projects",
                points_selector=project_id,
            )
            return True
        except Exception as e:
            print(f"❌ 프로젝트 삭제 실패 ({project_id}): {e}")
            return False

    def get_stats(self) -> dict:
        """Qdrant 통계"""
        if not self.client:
            self._connect()
        if not self.client:
            return {"status": "disconnected"}

        try:
            projects_collection = self.client.get_collection("projects")
            reviews_collection = self.client.get_collection("reviews")
            project_vectors_count = self._collection_stat(
                projects_collection,
                "vectors_count",
                "indexed_vectors_count",
            )
            project_points_count = self._collection_stat(
                projects_collection,
                "points_count",
            )
            review_vectors_count = self._collection_stat(
                reviews_collection,
                "vectors_count",
                "indexed_vectors_count",
            )
            review_points_count = self._collection_stat(
                reviews_collection,
                "points_count",
            )

            return {
                "status": "connected",
                "projects": {
                    "vectors_count": project_vectors_count,
                    "points_count": project_points_count,
                },
                "reviews": {
                    "vectors_count": review_vectors_count,
                    "points_count": review_points_count,
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# 글로벌 인스턴스
vector_service = VectorService()
