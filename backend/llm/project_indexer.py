"""Project-wide code context indexer.

Qdrant is used when available, with an in-memory fallback.
"""
from __future__ import annotations

import hashlib
import os
import re
import socket
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, cast
from urllib.parse import urlparse

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams
except Exception:
    QdrantClient = None
    Distance = None
    PointStruct = None
    VectorParams = None


CODE_INDEX_COLLECTION = "code_context"
VECTOR_SIZE = 384
TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".yml",
    ".yaml",
    ".css",
    ".scss",
    ".html",
    ".sql",
}
SKIP_PARTS = {
    ".git",
    ".next",
    ".venv",
    "node_modules",
    "__pycache__",
    "archive",
    "uploads",
}
MAX_INDEXED_ROOTS = 6
QDRANT_TIMEOUT_SEC = max(
    1,
    int(os.getenv("QDRANT_HTTP_TIMEOUT_SEC", "3")),
)


class ProjectIndexer:
    def __init__(self) -> None:
        self.client = None
        self.last_connect_error = ""
        self.memory_index: Dict[str, Dict[str, Any]] = {}
        self._indexed_roots: set[str] = set()
        self._root_entries: Dict[str, set[str]] = {}
        self._root_order: List[str] = []

    def _disable_qdrant(self, reason: str) -> None:
        self.client = None
        self.last_connect_error = reason

    def _is_qdrant_reachable(self, qdrant_url: str) -> bool:
        parsed = urlparse(qdrant_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6333
        try:
            with socket.create_connection(
                (host, port),
                timeout=QDRANT_TIMEOUT_SEC,
            ):
                return True
        except OSError:
            self.last_connect_error = (
                f"qdrant socket 연결 실패: {host}:{port}"
            )
            return False

    def _connect(self) -> None:
        if QdrantClient is None:
            self.last_connect_error = "qdrant_client import 불가"
            return
        try:
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
            if not self._is_qdrant_reachable(qdrant_url):
                self._disable_qdrant(self.last_connect_error)
                return
            # Qdrant 지연이 self-run 전체를 멈추지 않도록 짧은 타임아웃으로 빠르게 fallback 한다.
            self.client = QdrantClient(
                url=qdrant_url,
                timeout=QDRANT_TIMEOUT_SEC,
            )
            self._ensure_collection()
            self.last_connect_error = ""
        except Exception:
            self._disable_qdrant("qdrant 연결 또는 컬렉션 초기화 실패")

    def _ensure_collection(self) -> None:
        if not self.client or VectorParams is None or Distance is None:
            return
        try:
            self.client.get_collection(CODE_INDEX_COLLECTION)
        except Exception:
            try:
                self.client.create_collection(
                    collection_name=CODE_INDEX_COLLECTION,
                    vectors_config=VectorParams(
                        size=VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )
            except Exception:
                self._disable_qdrant("qdrant 컬렉션 생성 실패")

    def _text_to_vector(self, text: str) -> List[float]:
        hash_bytes = hashlib.sha256(
            text.encode("utf-8", errors="ignore")
        ).digest()
        vector: List[float] = []
        for index in range(VECTOR_SIZE):
            byte_val = hash_bytes[index % len(hash_bytes)]
            vector.append((byte_val - 128) / 128.0)
        return vector

    def _token_score(self, query: str, text: str) -> float:
        query_tokens = set(re.findall(r"[a-zA-Z0-9_가-힣]+", query.lower()))
        text_tokens = set(re.findall(r"[a-zA-Z0-9_가-힣]+", text.lower()))
        if not query_tokens or not text_tokens:
            return 0.0
        return len(query_tokens & text_tokens) / len(query_tokens)

    def _iter_files(self, workspace_root: Path) -> Iterable[Path]:
        for path in workspace_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            yield path

    def _point_id(self, rel_path: str) -> int:
        digest = hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:16]
        return int(digest, 16)

    def _storage_key(self, workspace_root: Path, rel_path: str) -> str:
        normalized_rel_path = rel_path.replace("\\", "/")
        return f"{workspace_root.resolve()}::{normalized_rel_path}"

    def _clear_root_entries(self, root_key: str) -> None:
        for storage_key in self._root_entries.pop(root_key, set()):
            self.memory_index.pop(storage_key, None)
        self._indexed_roots.discard(root_key)
        self._root_order = [
            item for item in self._root_order if item != root_key
        ]

    def _touch_root(self, root_key: str) -> None:
        self._root_order = [
            item for item in self._root_order if item != root_key
        ]
        self._root_order.append(root_key)

    def _prune_roots(self) -> None:
        # 최근 작업 루트만 유지해 실험 복제본 반복 실행 시 메모리 누적을 막는다.
        while len(self._root_order) > MAX_INDEXED_ROOTS:
            oldest_root = self._root_order[0]
            self._clear_root_entries(oldest_root)

    def index_file(
        self,
        workspace_root: Path,
        rel_path: str,
        content: str,
    ) -> None:
        rel_norm = str(rel_path).replace("\\", "/")
        root_key = str(workspace_root.resolve())
        storage_key = self._storage_key(workspace_root, rel_norm)
        payload = {
            "path": rel_norm,
            "content": content[:8000],
        }
        self.memory_index[storage_key] = payload
        self._root_entries.setdefault(root_key, set()).add(storage_key)

        if not self.client:
            self._connect()
        if not self.client or PointStruct is None:
            return
        try:
            # 벡터 업서트가 지연되면 즉시 in-memory fallback 으로 전환한다.
            self.client.upsert(
                collection_name=CODE_INDEX_COLLECTION,
                points=[
                    PointStruct(
                        id=self._point_id(rel_norm),
                        vector=self._text_to_vector(
                            f"{rel_norm}\n{content[:4000]}"
                        ),
                        payload=payload,
                    )
                ],
                wait=False,
                timeout=QDRANT_TIMEOUT_SEC,
            )
        except Exception as exc:
            self._disable_qdrant(f"qdrant upsert 실패: {exc}")
            return

    def index_workspace(
        self,
        workspace_root: Path,
        force: bool = False,
    ) -> int:
        root_key = str(workspace_root.resolve())
        if (not force) and root_key in self._indexed_roots:
            self._touch_root(root_key)
            return len(self._root_entries.get(root_key, set()))

        self._clear_root_entries(root_key)

        count = 0
        for path in self._iter_files(workspace_root):
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            rel_path = str(path.relative_to(workspace_root)).replace("\\", "/")
            self.index_file(workspace_root, rel_path, content)
            count += 1

        self._indexed_roots.add(root_key)
        self._touch_root(root_key)
        self._prune_roots()
        return count

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not self.client:
            self._connect()
        if self.client:
            try:
                found = cast(Any, self.client).search(
                    collection_name=CODE_INDEX_COLLECTION,
                    query_vector=self._text_to_vector(query),
                    limit=limit,
                    score_threshold=0.05,
                    timeout=QDRANT_TIMEOUT_SEC,
                )
                for item in found:
                    payload = item.payload or {}
                    results.append(
                        {
                            "path": payload.get("path", "unknown"),
                            "content": payload.get("content", ""),
                            "score": item.score,
                        }
                    )
            except Exception as exc:
                self._disable_qdrant(f"qdrant search 실패: {exc}")
                results = []

        if results:
            return results[:limit]

        ranked: List[Dict[str, Any]] = []
        for payload in self.memory_index.values():
            rel_path = str(payload.get("path") or "")
            score = self._token_score(
                query,
                f"{rel_path}\n{payload.get('content', '')}",
            )
            if score <= 0:
                continue
            ranked.append(
                {
                    "path": rel_path,
                    "content": payload.get("content", ""),
                    "score": score,
                }
            )
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:limit]

    def build_prompt_context(
        self,
        query: str,
        workspace_root: Optional[Path],
        limit: int = 4,
    ) -> str:
        if workspace_root is not None:
            self.index_workspace(workspace_root)

        hits = self.search(query, limit=limit)
        if not hits:
            return ""

        blocks: List[str] = []
        for hit in hits:
            snippet = str(hit.get("content", ""))[:1200].strip()
            if not snippet:
                continue
            blocks.append(f"[{hit['path']}]\n{snippet}")
        return "\n\n".join(blocks)


project_indexer = ProjectIndexer()
