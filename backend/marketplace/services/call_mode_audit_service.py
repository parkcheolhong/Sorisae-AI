from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.marketplace.call_mode_schema import (
    CallModeAuditEventCreate,
    CallModeAuditEventRead,
)

_AUDIT_EVENTS: list[CallModeAuditEventRead] = []
_NEXT_ID = 1


def _deserialize_metadata(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def record_call_mode_event(db: Session, event: CallModeAuditEventCreate) -> CallModeAuditEventRead:
    global _NEXT_ID
    stored = CallModeAuditEventRead(
        id=_NEXT_ID,
        call_id=event.call_id,
        session_id=event.session_id,
        event_type=event.event_type,
        requested_mode=event.requested_mode,
        resolved_mode=event.resolved_mode,
        auto_relay_requested=event.auto_relay_requested,
        auto_relay_applied=event.auto_relay_applied,
        call_route=event.call_route,
        caller_user_id=event.caller_user_id,
        callee_user_id=event.callee_user_id,
        callee_phone=event.callee_phone,
        status=event.status,
        error_code=event.error_code,
        latency_ms=event.latency_ms,
        duration_sec=event.duration_sec,
        call_quality=event.call_quality,
        metadata=dict(event.metadata or {}),
        created_at=datetime.now(timezone.utc),
    )
    _NEXT_ID += 1
    _AUDIT_EVENTS.append(stored)
    return stored


def list_call_mode_events(db: Session, *, call_id: str) -> List[CallModeAuditEventRead]:
    return [event for event in _AUDIT_EVENTS if event.call_id == call_id]
