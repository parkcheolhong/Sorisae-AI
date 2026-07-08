from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.marketplace.call_mode_schema import (
    CallModeAuditEventCreate,
    CallModeAuditEventRead,
)
from backend.marketplace import models

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
    try:
        db_row = models.CallModeAuditLog(
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
            metadata_json=json.dumps(dict(event.metadata or {}), ensure_ascii=False),
        )
        db.add(db_row)
        db.commit()
    except Exception:
        db.rollback()
    return stored


def list_call_mode_events(db: Session, *, call_id: str) -> List[CallModeAuditEventRead]:
    try:
        db_rows = (
            db.query(models.CallModeAuditLog)
            .filter(models.CallModeAuditLog.call_id == call_id)
            .order_by(models.CallModeAuditLog.created_at.asc(), models.CallModeAuditLog.id.asc())
            .all()
        )
        if db_rows:
            return [
                CallModeAuditEventRead(
                    id=int(row.id),
                    call_id=row.call_id,
                    session_id=row.session_id,
                    event_type=row.event_type,
                    requested_mode=row.requested_mode,
                    resolved_mode=row.resolved_mode,
                    auto_relay_requested=bool(row.auto_relay_requested),
                    auto_relay_applied=bool(row.auto_relay_applied),
                    call_route=row.call_route,
                    caller_user_id=row.caller_user_id,
                    callee_user_id=row.callee_user_id,
                    callee_phone=row.callee_phone,
                    status=row.status,
                    error_code=row.error_code,
                    latency_ms=row.latency_ms,
                    duration_sec=row.duration_sec,
                    call_quality=row.call_quality,
                    metadata=_deserialize_metadata(row.metadata_json),
                    created_at=(
                        row.created_at
                        if row.created_at is not None and row.created_at.tzinfo is not None
                        else (
                            row.created_at.replace(tzinfo=timezone.utc)
                            if row.created_at is not None
                            else datetime.now(timezone.utc)
                        )
                    ),
                )
                for row in db_rows
            ]
    except Exception:
        pass
    return [event for event in _AUDIT_EVENTS if event.call_id == call_id]
