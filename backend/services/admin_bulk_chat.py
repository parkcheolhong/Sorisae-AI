"""Admin bulk in-app chat announcements (no phone number required)."""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.marketplace.fcm_push import send_push_to_user
from backend.services.admin_bulk_notify_common import (
    MAX_ANNOUNCEMENT_BODY_LEN,
    MAX_RECIPIENTS_PER_CAMPAIGN,
    normalize_source_lang,
    query_recipient_users,
    resolve_user_notify_language,
    summarize_recipients_by_language,
    translate_for_lang,
)
from backend.time_utils import utcnow

SELF_ROOM_TITLE = "번역 보관함"
_CAMPAIGN_HISTORY_MAX = 40


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _campaign_history_path() -> Path:
    return _project_root() / "knowledge" / "admin_bulk_chat_campaigns.json"


def _load_campaign_history() -> List[Dict[str, Any]]:
    path = _campaign_history_path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
    except (OSError, json.JSONDecodeError):
        return []
    return []


def _save_campaign_record(record: Dict[str, Any]) -> Dict[str, Any]:
    history = _load_campaign_history()
    history.append(record)
    if len(history) > _CAMPAIGN_HISTORY_MAX:
        history = history[-_CAMPAIGN_HISTORY_MAX:]
    path = _campaign_history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def _ensure_self_room(db: Session, user_id: int):
    from backend.marketplace import models
    from backend.marketplace.nadotongryoksa_chat_router import (
        ACTIVE_MEMBERSHIP,
        _create_room_member,
        _find_self_room,
        _get_room_members,
    )

    room = _find_self_room(db, user_id)
    if room is not None:
        return room

    now = utcnow().replace(tzinfo=None)
    room = models.ChatRoom(
        room_uuid=str(uuid4()),
        room_type="group",
        title=SELF_ROOM_TITLE,
        owner_user_id=user_id,
        default_source_lang=None,
        default_target_lang=None,
        translation_mode="manual",
        allow_member_invites=False,
        member_limit=1,
        last_message_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(room)
    db.flush()
    db.add(_create_room_member(room.id, user_id, "owner"))
    db.flush()
    return room


def _build_chat_recipient_rows(
    users: Sequence[Any],
    *,
    source_text: str,
    source_lang: str,
) -> List[Dict[str, Any]]:
    translation_cache: Dict[str, str] = {}
    recipients: List[Dict[str, Any]] = []

    for user in users:
        target_lang = resolve_user_notify_language(
            preferred_language=getattr(user, "preferred_language", None),
            country_code=getattr(user, "country_code", None),
        )
        body = translate_for_lang(source_text, source_lang, target_lang, translation_cache)
        if len(body) > MAX_ANNOUNCEMENT_BODY_LEN:
            body = body[: MAX_ANNOUNCEMENT_BODY_LEN - 1] + "…"
        recipients.append({
            "user_id": int(getattr(user, "id", 0) or 0),
            "country_code": getattr(user, "country_code", None),
            "language": target_lang,
            "body": body,
        })

    if len(recipients) > MAX_RECIPIENTS_PER_CAMPAIGN:
        recipients = recipients[:MAX_RECIPIENTS_PER_CAMPAIGN]
    return recipients


def preview_bulk_chat_campaign(
    db: Session,
    *,
    source_text: str,
    source_lang: str = "ko",
    active_only: bool = True,
    country_codes: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    normalized_source = str(source_text or "").strip()
    if not normalized_source:
        raise ValueError("안내 문구를 입력하세요.")
    normalized_lang = normalize_source_lang(source_lang)
    users = query_recipient_users(db, active_only=active_only, country_codes=country_codes)
    recipients = _build_chat_recipient_rows(
        users,
        source_text=normalized_source,
        source_lang=normalized_lang,
    )
    return {
        "preview_id": str(uuid4()),
        "channel": "in_app_chat",
        "delivery_target": "self_room",
        "source_text": normalized_source,
        "source_lang": normalized_lang,
        "recipient_count": len(recipients),
        "language_breakdown": summarize_recipients_by_language(recipients),
        "sample_recipients": recipients[:12],
    }


async def _push_chat_announcement(user_id: int, room_uuid: str, body_preview: str) -> bool:
    try:
        return await send_push_to_user(
            user_id,
            data_payload={
                "type": "chat_message",
                "room_id": room_uuid,
                "message_id": "",
                "sender_label": "WorldLinco",
                "body_preview": body_preview,
                "alert_phrase": "안내",
            },
            title="(월드링코) 안내",
            body=f"WorldLinco: {body_preview}",
        )
    except Exception:
        return False


def send_bulk_chat_campaign(
    db: Session,
    *,
    source_text: str,
    source_lang: str = "ko",
    active_only: bool = True,
    country_codes: Optional[Sequence[str]] = None,
    dry_run: bool = False,
    initiated_by: str = "admin",
) -> Dict[str, Any]:
    from backend.marketplace.nadotongryoksa_chat_router import _append_message

    preview = preview_bulk_chat_campaign(
        db,
        source_text=source_text,
        source_lang=source_lang,
        active_only=active_only,
        country_codes=country_codes,
    )
    users = query_recipient_users(db, active_only=active_only, country_codes=country_codes)
    user_by_id = {int(getattr(user, "id", 0)): user for user in users}
    recipients = _build_chat_recipient_rows(
        users,
        source_text=preview["source_text"],
        source_lang=preview["source_lang"],
    )

    sent = 0
    failed = 0
    push_targets: List[tuple[int, str, str]] = []

    if not dry_run:
        for recipient in recipients:
            user_id = int(recipient["user_id"])
            user = user_by_id.get(user_id)
            if user is None:
                failed += 1
                continue
            try:
                room = _ensure_self_room(db, user_id)
                _append_message(
                    db,
                    room=room,
                    sender_user_id=None,
                    message_type="system_announcement",
                    body=recipient["body"],
                    translated_body=None,
                    source_lang=preview["source_lang"],
                    target_lang=recipient["language"],
                    request_translation=False,
                    reply_to_message_id=None,
                )
                sent += 1
                push_targets.append((user_id, room.room_uuid, recipient["body"][:80]))
            except Exception:
                failed += 1
        db.commit()

        async def _dispatch_pushes() -> int:
            results = await asyncio.gather(
                *[
                    _push_chat_announcement(user_id, room_uuid, preview_text)
                    for user_id, room_uuid, preview_text in push_targets
                ],
                return_exceptions=True,
            )
            return sum(1 for item in results if item is True)

        push_sent = asyncio.run(_dispatch_pushes()) if push_targets else 0
    else:
        push_sent = 0

    record = {
        "campaign_id": str(uuid4()),
        "created_at": utcnow().replace(microsecond=0).isoformat() + "Z",
        "initiated_by": initiated_by,
        "channel": "in_app_chat",
        "dry_run": dry_run,
        "source_text": preview["source_text"],
        "source_lang": preview["source_lang"],
        "recipient_count": len(recipients),
        "sent_count": sent,
        "failed_count": failed,
        "push_sent_count": push_sent if not dry_run else 0,
        "language_breakdown": preview["language_breakdown"],
    }
    _save_campaign_record(deepcopy(record))
    return record


def list_bulk_chat_campaign_history(limit: int = 20) -> List[Dict[str, Any]]:
    capped = max(1, min(int(limit), _CAMPAIGN_HISTORY_MAX))
    history = _load_campaign_history()
    return list(reversed(history[-capped:]))
