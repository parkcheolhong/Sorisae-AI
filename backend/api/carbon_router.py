"""추론 탄소·전력 집계 조회 라우터(ops). 관리자 토큰 필요."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.auth import get_current_user

router = APIRouter(prefix="/api/ops/carbon", tags=["ops-carbon"])


@router.get("/stats")
def carbon_stats(_current_user: Any = Depends(get_current_user)) -> Any:
    from backend.services.carbon_meter import get_carbon_meter

    return get_carbon_meter().stats()
