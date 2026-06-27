"""관광 AI 파일럿 베타 피드백 라우터 — 만족도(엄지)·NPS·A/B 수집 + 집계.

- POST `/api/tourism-feedback`        : 일반 사용자(모바일/웹)가 일정 결과를 평가(공개).
- GET  `/api/tourism-feedback/stats`  : NPS·엄지·A/B 집계(운영은 관리자 인증/내부망 뒤 전제).

기본 활성(`TOURISM_FEEDBACK_ENABLED=1`). 식별자/좌표는 저장하지 않는다(질의 텍스트만).
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/tourism-feedback", tags=["tourism-feedback"])


def _enabled() -> bool:
    return os.getenv("TOURISM_FEEDBACK_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off", ""}


def _guard():
    if not _enabled():
        raise HTTPException(status_code=404, detail="tourism feedback disabled")


class AnswerFeedback(BaseModel):
    query: Optional[str] = None
    language: Optional[str] = None
    variant: Optional[str] = "A"
    rating: Optional[str] = None   # 'up' | 'down'
    nps: Optional[int] = None      # 0~10
    comment: Optional[str] = None
    days: Optional[int] = None
    candidate_count: Optional[int] = None
    cached: Optional[bool] = None
    total_ms: Optional[float] = None


@router.post("")
def submit_feedback(fb: AnswerFeedback) -> Any:
    _guard()
    from backend.services.tourism_kb.feedback import get_feedback_store

    store = get_feedback_store()
    if not store.available:
        raise HTTPException(status_code=503, detail="feedback DB unavailable")
    saved = store.save_feedback(fb.model_dump())
    if not saved:
        raise HTTPException(status_code=422, detail="rating(up/down) 또는 nps(0~10) 중 하나가 필요합니다")
    return {"saved": True}


@router.get("/stats")
def feedback_stats() -> Any:
    _guard()
    from backend.services.tourism_kb.feedback import get_feedback_store

    return get_feedback_store().stats()
