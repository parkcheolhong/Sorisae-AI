"""VoIP REST 계약 모델 — 모바일(src/services/voipCallClient.ts)과 1:1 매핑."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CallInitiateRequest(BaseModel):
    """모바일 useVoipAutoController.ts / useVoIPCall.ts 의 initiate 요청 본문."""

    callee_phone: Optional[str] = None
    callee_user_id: Optional[int] = None
    callee_voice_id: Optional[str] = None
    friend_id: Optional[str | int] = None
    caller_id: Optional[str] = None
    session_id: Optional[str] = None
    mode: str = "voip_full_auto"
    auto_relay: bool = False


class TurnServerModel(BaseModel):
    urls: List[str]
    username: Optional[str] = None
    credential: Optional[str] = None


class CallInitResponse(BaseModel):
    """모바일 CallInitResponse 인터페이스와 동일한 필드 집합."""

    call_id: str
    signaling_server: str
    turn_servers: List[TurnServerModel] = []
    session_id: Optional[str] = None
    call_route: Optional[str] = None  # app | pstn_fallback
    phone_dialer_required: Optional[bool] = None
    fallback_dial_url: Optional[str] = None
    user_message: Optional[str] = None
    callee_app_online: Optional[bool] = None
    caller_user_id: Optional[int] = None
    caller_voice_id: Optional[str] = None
    callee_voice_id: Optional[str] = None
    callee_user_id: Optional[int] = None
    participant_role: Optional[str] = None  # caller | callee
    display_label: Optional[str] = None
    display_language: Optional[str] = None
    display_country_code: Optional[str] = None
    status: Optional[str] = None
    requested_mode: Optional[str] = None
    resolved_mode: Optional[str] = None
    auto_relay_requested: Optional[bool] = None
    auto_relay_applied: Optional[bool] = None
    error_code: Optional[str] = None


class AuditResponse(BaseModel):
    call_id: str
    status: str
    created_at: float
    session_id: Optional[str] = None
    mode: Optional[str] = None
    participants: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
