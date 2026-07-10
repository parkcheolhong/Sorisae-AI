"""Persist 소리새 friend-chat turns into trip_sessions / conversation_turns."""
from __future__ import annotations

import json
from typing import Any, Optional, Tuple
from uuid import uuid4

from backend.time_utils import utcnow


def ensure_friend_chat_trip_session(
    db: Any,
    *,
    trip_session_id: Optional[str],
    user_id: Optional[int],
    country_code: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Tuple[Optional[int], str]:
    from backend.marketplace import models as marketplace_models

    session_id = (trip_session_id or "").strip() or f"sorisae-{uuid4().hex[:16]}"
    if db is None or not all(hasattr(db, attr) for attr in ("add", "commit", "flush", "query")):
        return None, session_id
    try:
        existing = (
            db.query(marketplace_models.TripSession)
            .filter(marketplace_models.TripSession.session_id == session_id)
            .first()
        )
        if existing is not None:
            if user_id and existing.user_id is None:
                existing.user_id = user_id
                existing.updated_at = utcnow()
                db.commit()
            return int(existing.id), session_id
        context: dict[str, Any] = {"source": "friend-chat"}
        if latitude is not None and longitude is not None:
            context["lat"] = latitude
            context["lon"] = longitude
        session = marketplace_models.TripSession(
            session_id=session_id,
            user_id=user_id,
            status="active",
            origin_country=(country_code or "").strip().upper() or None,
            context_json=json.dumps(context, ensure_ascii=False),
        )
        db.add(session)
        db.flush()
        db.commit()
        return int(session.id), session_id
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None, session_id


def _next_turn_index(db: Any, trip_session_pk: int) -> int:
    from backend.marketplace.models import ConversationTurn

    latest = (
        db.query(ConversationTurn.turn_index)
        .filter(ConversationTurn.trip_session_id == trip_session_pk)
        .order_by(ConversationTurn.turn_index.desc())
        .first()
    )
    if latest is None:
        return 0
    return int(latest[0]) + 1


def record_friend_chat_turn(
    db: Any,
    *,
    trip_session_pk: int,
    user_utterance: str,
    assistant_utterance: str,
    language_code: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    from backend.marketplace.models import ConversationTurn

    if db is None or not all(hasattr(db, attr) for attr in ("add", "commit", "flush")):
        return
    user_text = str(user_utterance or "").strip()
    assistant_text = str(assistant_utterance or "").strip()
    if not user_text and not assistant_text:
        return
    try:
        turn_index = _next_turn_index(db, trip_session_pk)
        metadata = {"channel": "friend-chat"}
        if correlation_id:
            metadata["correlation_id"] = correlation_id
        if user_text:
            db.add(
                ConversationTurn(
                    trip_session_id=trip_session_pk,
                    turn_index=turn_index,
                    role="user",
                    utterance=user_text,
                    language_code=language_code,
                    intent="friend_chat",
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                )
            )
        if assistant_text:
            db.add(
                ConversationTurn(
                    trip_session_id=trip_session_pk,
                    turn_index=turn_index + (1 if user_text else 0),
                    role="assistant",
                    utterance=assistant_text,
                    language_code=language_code,
                    intent="friend_chat",
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                )
            )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def persist_friend_chat_exchange(
    *,
    trip_session_id: Optional[str],
    user_id: Optional[int],
    country_code: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    user_utterance: str,
    assistant_utterance: str,
    language_code: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Optional[str]:
    """Best-effort DB persist; returns resolved trip_session_id or None on skip."""
    user_text = str(user_utterance or "").strip()
    assistant_text = str(assistant_utterance or "").strip()
    if not user_text or not assistant_text:
        return (trip_session_id or "").strip() or None
    try:
        from backend.marketplace.database import SessionLocal

        db = SessionLocal()
        try:
            trip_session_pk, resolved_id = ensure_friend_chat_trip_session(
                db,
                trip_session_id=trip_session_id,
                user_id=user_id,
                country_code=country_code,
                latitude=latitude,
                longitude=longitude,
            )
            if trip_session_pk is not None:
                record_friend_chat_turn(
                    db,
                    trip_session_pk=trip_session_pk,
                    user_utterance=user_text,
                    assistant_utterance=assistant_text,
                    language_code=language_code,
                    correlation_id=correlation_id,
                )
            return resolved_id
        finally:
            db.close()
    except Exception:
        return (trip_session_id or "").strip() or None
