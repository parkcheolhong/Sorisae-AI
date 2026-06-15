from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class CallModeAuditEventCreate(BaseModel):
    call_id: str
    session_id: Optional[str] = None
    event_type: str
    requested_mode: str = ""
    resolved_mode: str = ""
    auto_relay_requested: bool = False
    auto_relay_applied: bool = False
    call_route: Optional[str] = None
    caller_user_id: Optional[int] = None
    callee_user_id: Optional[int] = None
    callee_phone: Optional[str] = None
    status: Optional[str] = None
    error_code: Optional[str] = None
    latency_ms: Optional[int] = None
    duration_sec: Optional[int] = None
    call_quality: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CallModeAuditEventRead(BaseModel):
    id: int
    call_id: str
    session_id: Optional[str] = None
    event_type: str
    requested_mode: str = ""
    resolved_mode: str = ""
    auto_relay_requested: bool = False
    auto_relay_applied: bool = False
    call_route: Optional[str] = None
    caller_user_id: Optional[int] = None
    callee_user_id: Optional[int] = None
    callee_phone: Optional[str] = None
    status: Optional[str] = None
    error_code: Optional[str] = None
    latency_ms: Optional[int] = None
    duration_sec: Optional[int] = None
    call_quality: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
