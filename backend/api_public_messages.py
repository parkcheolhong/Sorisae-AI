"""Shared public-facing API messages and stable error codes.

User-visible strings default to Korean. Handlers should return these constants
instead of embedding duplicate literals or leaking internal exception text.

Semantics for tourism stats payloads:
- ``available=True``: aggregation succeeded; metric fields are present.
- ``available=False``: no metrics to render; inspect ``error`` (machine code).
"""

from __future__ import annotations

from typing import Any, Dict


class PublicErrorCode:
    STATS_UNAVAILABLE = "stats_unavailable"


class PublicErrorMessage:
    CONNECTION_FAILED = "연결 실패"
    ENGINE_EXECUTION_FAILED = "엔진 실행에 실패했습니다."
    MODULE_EXECUTION_FAILED = "모듈 실행에 실패했습니다."
    CATEGORY_EXPERIMENT_FAILED = "카테고리 실험에 실패했습니다."
    TRANSLATION_PROCESSING_FAILED = "번역 처리 중 오류가 발생했습니다."
    CONNECTOR_TEST_FAILED = "연결 테스트에 실패했습니다."
    WEBHOOK_TEST_FAILED = "웹훅 테스트에 실패했습니다."


def resolve_actor_label(actor: Any) -> str:
    if actor is None:
        return "unknown"
    email = getattr(actor, "email", None)
    if email:
        return str(email)
    actor_id = getattr(actor, "id", None)
    if actor_id is not None:
        return f"user:{actor_id}"
    return str(actor)


def tourism_stats_unavailable_payload() -> Dict[str, Any]:
    return {
        "available": False,
        "error": PublicErrorCode.STATS_UNAVAILABLE,
    }
