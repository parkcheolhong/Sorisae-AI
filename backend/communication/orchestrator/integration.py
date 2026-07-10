"""Call Orchestrator ↔ hot path 얇은 연결 (best-effort, 완전 가드).

`nadotongryoksa_voip_router` 가 **한 줄 훅**으로 호출하는 진입점. Session Core
integration과 동일한 설계 불변식:

1. **flag off(기본) = 완전 no-op.** `COMM_V2_CALL_ORCHESTRATOR` 꺼져 있으면 즉시 반환.
2. **절대 throw 금지.** 모든 예외를 삼켜(debug 로그만) hot path 에 전파하지 않는다.
3. **contract 무변경.** 입력은 단순 스칼라만 받는다.

이 모듈만이 hot path 와 Call Orchestrator 사이의 유일한 접점이다.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from .manager import CallOrchestrator
from .models import PolicyDecision

logger = logging.getLogger(__name__)

_orchestrator: Optional[CallOrchestrator] = None
_lock = threading.Lock()


def _get() -> CallOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        with _lock:
            if _orchestrator is None:
                _orchestrator = CallOrchestrator()
    return _orchestrator


def reset_for_test() -> None:
    """테스트 전용 — 환경변수 토글 후 재생성하도록 초기화."""

    global _orchestrator
    with _lock:
        _orchestrator = None


def evaluate_admission() -> PolicyDecision:
    """새 통화 admission 결정(best-effort). 실패/비활성 시 allow."""

    try:
        return _get().evaluate_admission()
    except Exception:  # pragma: no cover - 방어적, hot path 보호
        logger.debug("[call-orch] evaluate_admission skipped", exc_info=True)
        return PolicyDecision(allow=True, code="error_allow", reason="")


def on_call_init(
    call_id: Optional[str],
    *,
    session_id: Optional[str] = None,
    route: Optional[str] = None,
    initial_status: Optional[str] = None,
    admission: Optional[PolicyDecision] = None,
) -> None:
    """call_init 시 라이프사이클 시작 기록(best-effort)."""

    try:
        orch = _get()
        if not orch.enabled or not call_id:
            return
        orch.on_call_init(
            call_id, session_id=session_id, route=route,
            initial_status=initial_status, admission=admission,
        )
    except Exception:  # pragma: no cover
        logger.debug("[call-orch] on_call_init skipped", exc_info=True)


def on_call_status(call_id: Optional[str], status: Optional[str], *, reason: Optional[str] = None) -> None:
    """상태 전이 기록(best-effort)."""

    try:
        orch = _get()
        if not orch.enabled or not call_id or not status:
            return
        orch.on_status(call_id, status, reason=reason)
    except Exception:  # pragma: no cover
        logger.debug("[call-orch] on_call_status skipped", exc_info=True)


def on_call_end(call_id: Optional[str], *, status: str = "ended", reason: Optional[str] = None) -> None:
    """통화 종료 기록(best-effort)."""

    try:
        orch = _get()
        if not orch.enabled or not call_id:
            return
        orch.on_call_end(call_id, status=status, reason=reason)
    except Exception:  # pragma: no cover
        logger.debug("[call-orch] on_call_end skipped", exc_info=True)
