"""Session Core ↔ hot path 얇은 연결 (best-effort, 완전 가드).

오케스트레이터(`nadotongryoksa_voip_router`)와 통역 엔드포인트(`voice-translate`)가
**한 줄 훅**으로 호출하는 진입점이다. 설계 불변식:

1. **flag off(기본) = 완전 no-op.** `COMM_V2_SESSION_CORE` 꺼져 있으면 즉시 반환.
2. **절대 throw 금지.** 모든 예외를 삼켜(debug 로그만) hot path 에 전파하지 않는다.
3. **contract 무변경.** 입력은 단순 스칼라/튜플만 받아 라우터가 도메인 객체를 몰라도 된다.

이 모듈만이 hot path 와 Session Core 사이의 유일한 접점이다.
"""

from __future__ import annotations

import logging
import threading
from typing import Iterable, Optional

from .manager import SessionManager
from .models import LanguagePair, Participant, TurnRecord

logger = logging.getLogger(__name__)

_manager: Optional[SessionManager] = None
_lock = threading.Lock()


def _get_manager() -> SessionManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = SessionManager()
    return _manager


def reset_manager_for_test() -> None:
    """테스트 전용 — 환경변수 토글 후 매니저를 재생성하도록 초기화."""

    global _manager
    with _lock:
        _manager = None


def record_call_init(
    session_id: Optional[str],
    *,
    call_id: Optional[str] = None,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    participants: Optional[Iterable[tuple[str, Optional[str]]]] = None,
) -> None:
    """call_init 시 세션 언어쌍·참가자 기록(best-effort)."""

    try:
        mgr = _get_manager()
        if not mgr.enabled or not session_id:
            return
        if source_lang and target_lang:
            mgr.update_language_pair(session_id, source_lang, target_lang, call_id=call_id)
        else:
            mgr.get_or_create(session_id, call_id=call_id)
        for user_ref, pref_lang in participants or []:
            if not user_ref:
                continue
            mgr.upsert_participant(
                session_id,
                Participant(user_ref=str(user_ref), preferred_language=pref_lang),
                call_id=call_id,
            )
    except Exception:  # pragma: no cover - 방어적, hot path 보호
        logger.debug("[session-core] record_call_init skipped", exc_info=True)


def build_context_hint(
    session_id: Optional[str],
    *,
    max_turns: int = 4,
    max_chars: int = 600,
) -> Optional[str]:
    """최근 대화 맥락을 한 줄 요약으로 반환(best-effort).

    flag off / 세션 없음 / 턴 없음이면 ``None``. MT 프롬프트 보조 힌트용으로만 쓰인다.
    """

    try:
        mgr = _get_manager()
        if not mgr.enabled or not session_id:
            return None
        turns = mgr.recent_turns(session_id, limit=max_turns)
        if not turns:
            return None
        parts: list[str] = []
        for t in turns:
            src = (t.source_text or "").strip().replace("\n", " ")
            dst = (t.translated_text or "").strip().replace("\n", " ")
            if not src and not dst:
                continue
            parts.append(f"{src} -> {dst}".strip(" ->"))
        if not parts:
            return None
        hint = " | ".join(parts)
        return hint[:max_chars]
    except Exception:  # pragma: no cover - 방어적, hot path 보호
        logger.debug("[session-core] build_context_hint skipped", exc_info=True)
        return None


def record_relay_turn(
    session_id: Optional[str],
    *,
    call_id: Optional[str] = None,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    source_text: str = "",
    translated_text: str = "",
    speaker_ref: Optional[str] = None,
) -> None:
    """relay(번역) 1턴 기록(best-effort)."""

    try:
        mgr = _get_manager()
        if not mgr.enabled or not session_id:
            return
        if not (source_lang and target_lang):
            return
        mgr.record_turn(
            session_id,
            TurnRecord(
                direction=LanguagePair(source=source_lang, target=target_lang),
                source_text=source_text or "",
                translated_text=translated_text or "",
                speaker_ref=speaker_ref,
            ),
            call_id=call_id,
        )
    except Exception:  # pragma: no cover - 방어적, hot path 보호
        logger.debug("[session-core] record_relay_turn skipped", exc_info=True)
