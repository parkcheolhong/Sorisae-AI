from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field


class IndexProjectRequest(BaseModel):
    project_id: int = Field(..., gt=0, description="양의 정수 project_id 필수")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


def _noop_auth():
    return None


def build_search_router(contract: Optional[Any] = None) -> APIRouter:
    router = APIRouter()
    _auth = contract.get_current_user if contract is not None else _noop_auth

    @router.get("/search/semantic")
    def semantic_search_projects(
        q: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        from .vector_service import vector_service

        query = q.strip()
        if not query:
            return {"results": [], "query": "", "count": 0}
        results = vector_service.search_projects(query, limit=min(limit, 50))
        return {"results": results, "query": query, "count": len(results)}

    @router.post("/search/index-project")
    def index_project_vector(
        payload: IndexProjectRequest,
        current_user=Depends(_auth),
    ) -> dict[str, Any]:
        del current_user
        from .vector_service import vector_service

        ok = vector_service.index_project(payload.project_id, payload.title, payload.description)
        return {"indexed": ok, "project_id": payload.project_id}

    @router.get("/search/stats")
    def vector_search_stats() -> dict[str, Any]:
        from .vector_service import vector_service

        return vector_service.get_stats()

    return router


# Module-level router for direct import in main.py
router = build_search_router()