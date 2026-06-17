from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import (
    get_current_user,
    resolve_token_subject,
)
from backend.database import get_db
from backend.designated_language import (
    DESIGNATED_LANGUAGE_MISMATCH_DETAIL,
    text_matches_designated_language,
)
from backend.marketplace import models
from backend.marketplace.fcm_push import send_push_to_user
from backend.services.nadotongryoksa.translator import (
    NadoTranslator,
    SUPPORTED_LANGUAGES,
)


router = APIRouter(prefix="/mobile/chat", tags=["nadotongryoksa-chat"])
logger = logging.getLogger("nadotongryoksa.chat")

ACTIVE_MEMBERSHIP = "active"
SELF_ROOM_TITLE = "번역 보관함"
GROUP_ROOM_MIN_MEMBER_LIMIT = 3
GROUP_ROOM_MAX_MEMBER_LIMIT = 10
DEFAULT_GROUP_ROOM_MEMBER_LIMIT = 10


class ChatRoomWebSocketHub:
    def __init__(self) -> None:
        self._connections: dict[str, dict[int, set[WebSocket]]] = {}

    async def connect(
        self,
        room_id: str,
        user_id: int,
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()
        room_connections = self._connections.setdefault(room_id, {})
        room_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(
        self,
        room_id: str,
        user_id: int,
        websocket: WebSocket,
    ) -> None:
        room_connections = self._connections.get(room_id)
        if room_connections is None:
            return
        user_connections = room_connections.get(user_id)
        if user_connections is None:
            return
        user_connections.discard(websocket)
        if not user_connections:
            room_connections.pop(user_id, None)
        if not room_connections:
            self._connections.pop(room_id, None)

    async def send_to_user(
        self,
        room_id: str,
        user_id: int,
        payload: dict[str, Any],
    ) -> None:
        room_connections = self._connections.get(room_id)
        if room_connections is None:
            return
        user_connections = list(room_connections.get(user_id, set()))
        for websocket in user_connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(room_id, user_id, websocket)

    def is_user_connected(self, room_id: str, user_id: int) -> bool:
        room_connections = self._connections.get(room_id)
        if room_connections is None:
            return False
        return bool(room_connections.get(user_id))


chat_room_ws_hub = ChatRoomWebSocketHub()


class DirectRoomCreateRequest(BaseModel):
    friend_user_id: int
    initial_message: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None


class GroupRoomCreateRequest(BaseModel):
    title: str
    member_user_ids: list[int]
    default_source_lang: Optional[str] = None
    default_target_lang: Optional[str] = None
    translation_mode: str = "assist"
    allow_member_invites: bool = False
    member_limit: Optional[int] = DEFAULT_GROUP_ROOM_MEMBER_LIMIT


class SelfRoomCreateRequest(BaseModel):
    initial_message: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None


class RoomMembersAddRequest(BaseModel):
    member_user_ids: list[int]


class RoomSettingsUpdateRequest(BaseModel):
    allow_member_invites: Optional[bool] = None
    member_limit: Optional[int] = None


class MessageCreateRequest(BaseModel):
    message_type: str = "text"
    body: str
    translated_body: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    request_translation: bool = False
    reply_to_message_id: Optional[str] = None


class ReadUpdateRequest(BaseModel):
    last_read_message_id: Optional[str] = None


def _utcnow() -> datetime:
    return datetime.utcnow()


def _normalize_text(
    value: Optional[str], *, max_length: Optional[int] = None
) -> Optional[str]:
    if not (text := (value or "").strip()):
        return None
    return text[:max_length] if max_length is not None else text


def _normalize_language_code(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_text(value, max_length=16)
    if not normalized:
        return None
    lowered = normalized.lower()
    return lowered if lowered in SUPPORTED_LANGUAGES else None


def _build_voice_id(user_id: int) -> str:
    return f"nado-{user_id:06d}"


def _get_room_members(
    db: Session, room_id: int
) -> list[models.ChatRoomMember]:
    return (
        db.query(models.ChatRoomMember)
        .filter(
            models.ChatRoomMember.room_id == room_id,
            models.ChatRoomMember.membership_status == ACTIVE_MEMBERSHIP,
        )
        .order_by(
            models.ChatRoomMember.joined_at.asc(),
            models.ChatRoomMember.id.asc(),
        )
        .all()
    )


def _get_room_by_uuid(db: Session, room_uuid: str) -> models.ChatRoom:
    room = (
        db.query(models.ChatRoom)
        .filter(models.ChatRoom.room_uuid == room_uuid)
        .first()
    )
    if room is None or room.is_archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대화방을 찾을 수 없습니다",
        )
    return room


def _require_room_member(
    db: Session, room_uuid: str, user_id: int
) -> tuple[models.ChatRoom, models.ChatRoomMember]:
    room = _get_room_by_uuid(db, room_uuid)
    member = (
        db.query(models.ChatRoomMember)
        .filter(
            models.ChatRoomMember.room_id == room.id,
            models.ChatRoomMember.user_id == user_id,
            models.ChatRoomMember.membership_status == ACTIVE_MEMBERSHIP,
        )
        .first()
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="대화방 접근 권한이 없습니다",
        )
    return room, member


def _resolve_user(db: Session, user_id: int) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )
    return user


def _resolve_authenticated_chat_user_from_token(
    db: Session,
    token: Optional[str],
) -> Optional[models.User]:
    subject = resolve_token_subject(str(token or ""))
    if not isinstance(subject, str) or not subject.strip():
        return None

    return (
        db.query(models.User)
        .filter(
            (models.User.username == subject)
            | (models.User.email == subject)
        )
        .first()
    )


def _find_direct_room(
    db: Session, user_a_id: int, user_b_id: int
) -> Optional[models.ChatRoom]:
    candidate_rooms = (
        db.query(models.ChatRoom)
        .filter(
            models.ChatRoom.room_type == "direct",
            models.ChatRoom.is_archived.is_(False),
        )
        .order_by(models.ChatRoom.updated_at.desc(), models.ChatRoom.id.desc())
        .all()
    )
    expected_member_ids = {user_a_id, user_b_id}
    for room in candidate_rooms:
        member_ids = {
            member.user_id for member in _get_room_members(db, room.id)
        }
        if member_ids == expected_member_ids:
            return room
    return None


def _find_self_room(
    db: Session, owner_user_id: int
) -> Optional[models.ChatRoom]:
    candidate_rooms = (
        db.query(models.ChatRoom)
        .filter(
            models.ChatRoom.owner_user_id == owner_user_id,
            models.ChatRoom.title == SELF_ROOM_TITLE,
            models.ChatRoom.is_archived.is_(False),
        )
        .order_by(models.ChatRoom.updated_at.desc(), models.ChatRoom.id.desc())
        .all()
    )
    for room in candidate_rooms:
        member_ids = [
            member.user_id for member in _get_room_members(db, room.id)
        ]
        if member_ids == [owner_user_id]:
            return room
    return None


def _serialize_user_summary(
    user: Optional[models.User],
) -> Optional[dict[str, Any]]:
    if user is None:
        return None
    nickname_source = getattr(user, "username", None) or getattr(
        user, "email", "사용자"
    ).split("@")[0]
    nickname = nickname_source.strip() or "사용자"
    return {
        "user_id": user.id,
        "nickname": nickname,
        "voice_id": _build_voice_id(user.id),
        "preferred_language": getattr(user, "preferred_language", None),
        "country_code": getattr(user, "country_code", None),
    }


def _resolve_user_language(user: Optional[models.User]) -> Optional[str]:
    if user is None:
        return None
    return _normalize_language_code(getattr(user, "preferred_language", None))


@dataclass(frozen=True)
class MessageTranslationPlan:
    scope: str
    source_lang: Optional[str]
    primary_target_lang: Optional[str]
    recipient_target_languages: tuple[str, ...] = ()
    include_sender: bool = False


def _resolve_direct_translation_plan(
    db: Session,
    room: models.ChatRoom,
    sender_user_id: int,
) -> MessageTranslationPlan:
    sender = (
        db.query(models.User)
        .filter(models.User.id == sender_user_id)
        .first()
    )
    sender_language = _resolve_user_language(sender)

    if room.room_type == "direct":
        counterpart_language = None
        for member in _get_room_members(db, room.id):
            if member.user_id == sender_user_id:
                continue
            counterpart = (
                db.query(models.User)
                .filter(models.User.id == member.user_id)
                .first()
            )
            counterpart_language = _resolve_user_language(counterpart)
            if counterpart_language:
                break
        return MessageTranslationPlan(
            scope="direct",
            source_lang=sender_language,
            primary_target_lang=counterpart_language,
            recipient_target_languages=(
                (counterpart_language,) if counterpart_language else ()
            ),
            include_sender=False,
        )

    return MessageTranslationPlan(
        scope="direct",
        source_lang=sender_language,
        primary_target_lang=None,
        include_sender=False,
    )


def _resolve_group_translation_plan(
    db: Session,
    room: models.ChatRoom,
    sender_user_id: int,
    request_translation: bool,
) -> MessageTranslationPlan:
    sender = (
        db.query(models.User)
        .filter(models.User.id == sender_user_id)
        .first()
    )
    sender_language = _resolve_user_language(sender)

    if not request_translation:
        return MessageTranslationPlan(
            scope="group",
            source_lang=sender_language,
            primary_target_lang=None,
            include_sender=False,
        )

    target_languages = sorted({
        language
        for member in _get_room_members(db, room.id)
        if member.user_id != sender_user_id
        for language in [
            _resolve_user_language(
                _resolve_user(db, member.user_id)
            )
        ]
        if language
    })
    resolved_target = (
        target_languages[0]
        if len(target_languages) == 1
        else None
    )

    return MessageTranslationPlan(
        scope="group",
        source_lang=sender_language,
        primary_target_lang=resolved_target,
        recipient_target_languages=tuple(target_languages),
        include_sender=False,
    )


def _resolve_message_translation_plan(
    db: Session,
    room: models.ChatRoom,
    sender_user_id: int,
    request_translation: bool,
) -> MessageTranslationPlan:
    if room.room_type == "direct":
        return _resolve_direct_translation_plan(
            db,
            room,
            sender_user_id,
        )

    return _resolve_group_translation_plan(
        db,
        room,
        sender_user_id,
        request_translation,
    )


def _resolve_message_translation(
    db: Session,
    room: models.ChatRoom,
    sender_user_id: Optional[int],
    message_type: str,
    body: str,
    translated_body: Optional[str],
    source_lang: Optional[str],
    target_lang: Optional[str],
    request_translation: bool,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    normalized_translated = _normalize_text(translated_body)
    normalized_source = _normalize_language_code(source_lang)
    normalized_target = _normalize_language_code(target_lang)
    if (
        normalized_translated
        or message_type != "text"
        or sender_user_id is None
    ):
        return (
            normalized_translated,
            normalized_source,
            normalized_target,
            None,
        )

    plan = _resolve_message_translation_plan(
        db,
        room,
        sender_user_id,
        request_translation,
    )
    resolved_source = plan.source_lang
    if (
        resolved_source
        and message_type == "text"
        and not text_matches_designated_language(body, resolved_source)
    ):
        logger.info(
            "chat designated-language mismatch room=%s sender=%s designated=%s",
            room.room_uuid,
            sender_user_id,
            resolved_source,
        )
        return None, resolved_source, plan.primary_target_lang, None
    if plan.scope == "group" and room.title != SELF_ROOM_TITLE:
        return None, resolved_source, None, None
    resolved_target = plan.primary_target_lang
    if (
        not resolved_source
        or not resolved_target
        or resolved_source == resolved_target
    ):
        return None, resolved_source, resolved_target, None

    try:
        translated = NadoTranslator.get_instance().translate(
            body,
            from_lang=resolved_source,
            to_lang=resolved_target,
        )
    except Exception as exc:
        logger.warning(
            "chat auto-translation failed room=%s sender=%s %s->%s err=%s",
            room.room_uuid,
            sender_user_id,
            resolved_source,
            resolved_target,
            exc,
        )
        return None, resolved_source, resolved_target, None

    return (
        _normalize_text(translated),
        resolved_source,
        resolved_target,
        "nado-translator",
    )


def _list_message_translations(
    db: Session, message_id: int
) -> list[models.ChatMessageTranslation]:
    return (
        db.query(models.ChatMessageTranslation)
        .filter(models.ChatMessageTranslation.message_id == message_id)
        .order_by(
            models.ChatMessageTranslation.recipient_user_id.asc(),
            models.ChatMessageTranslation.id.asc(),
        )
        .all()
    )


def _build_group_delivery_summary(
    translation_rows: list[models.ChatMessageTranslation],
) -> dict[str, Any]:
    pending_count = 0
    done_count = 0
    failed_count = 0
    skipped_count = 0
    for row in translation_rows:
        if row.translation_status == "pending":
            pending_count += 1
        elif row.translation_status == "failed":
            failed_count += 1
        elif row.translation_status == "skipped":
            skipped_count += 1
            done_count += 1
        elif row.translation_status == "done":
            done_count += 1

    if failed_count and done_count:
        status = "partial_failed"
    elif failed_count:
        status = "failed"
    elif pending_count:
        status = "pending"
    elif done_count:
        status = "done"
    else:
        status = "none"

    return {
        "recipient_count": len(translation_rows),
        "pending_count": pending_count,
        "done_count": done_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "status": status,
    }


def _serialize_viewer_translation(
    translation_row: Optional[models.ChatMessageTranslation],
) -> Optional[dict[str, Any]]:
    if translation_row is None:
        return None
    return {
        "target_lang": translation_row.target_lang,
        "translated_body": translation_row.translated_body,
        "translation_status": translation_row.translation_status,
        "failure_code": translation_row.failure_code,
        "failure_detail": translation_row.failure_detail,
    }


def _select_group_viewer_translation(
    translation_rows: list[models.ChatMessageTranslation],
    current_user_id: int,
) -> Optional[models.ChatMessageTranslation]:
    return next(
        (
            row
            for row in translation_rows
            if row.recipient_user_id == current_user_id
        ),
        None,
    )


def _resolve_message_source_language(
    db: Session,
    message: models.ChatMessage,
) -> Optional[str]:
    normalized_source = _normalize_language_code(message.body_source_lang)
    if normalized_source:
        return normalized_source

    sender_user_id = message.sender_user_id
    if sender_user_id is None:
        return None

    sender = (
        db.query(models.User)
        .filter(models.User.id == sender_user_id)
        .first()
    )
    return _resolve_user_language(sender)


def _build_group_viewer_translation_fallback(
    db: Session,
    message: models.ChatMessage,
    current_user_id: int,
) -> Optional[dict[str, Any]]:
    if message.message_type != "text":
        return None

    viewer = (
        db.query(models.User)
        .filter(models.User.id == current_user_id)
        .first()
    )
    target_lang = _resolve_user_language(viewer)
    if not target_lang:
        return None

    source_lang = _resolve_message_source_language(db, message)
    if not source_lang or source_lang == target_lang:
        return {
            "target_lang": target_lang,
            "translated_body": None,
            "translation_status": "skipped",
            "failure_code": None,
            "failure_detail": None,
        }

    try:
        translated = NadoTranslator.get_instance().translate(
            message.body,
            from_lang=source_lang,
            to_lang=target_lang,
        )
    except Exception as exc:
        logger.warning(
            "group viewer fallback translation failed "
            "room_message=%s viewer=%s %s->%s err=%s",
            message.message_uuid,
            current_user_id,
            source_lang,
            target_lang,
            exc,
        )
        return {
            "target_lang": target_lang,
            "translated_body": None,
            "translation_status": "failed",
            "failure_code": "translation_error",
            "failure_detail": str(exc),
        }

    return {
        "target_lang": target_lang,
        "translated_body": _normalize_text(translated),
        "translation_status": "done",
        "failure_code": None,
        "failure_detail": None,
    }


def _append_group_message_translations(
    db: Session,
    *,
    room: models.ChatRoom,
    message: models.ChatMessage,
    sender_user_id: int,
    body: str,
    source_lang: Optional[str],
    request_translation: bool,
) -> None:
    if (
        room.room_type != "group"
        or room.title == SELF_ROOM_TITLE
        or message.message_type != "text"
        or not request_translation
        or not source_lang
    ):
        return

    translation_rows: list[models.ChatMessageTranslation] = []
    for member in _get_room_members(db, room.id):
        if member.user_id == sender_user_id:
            continue
        recipient = _resolve_user(db, member.user_id)
        target_lang = _resolve_user_language(recipient)
        if not target_lang:
            continue

        translated_body = None
        translation_engine = None
        translation_status = "skipped"
        failure_code = None
        failure_detail = None
        delivered_at = _utcnow()

        if source_lang != target_lang:
            try:
                translated_body = _normalize_text(
                    NadoTranslator.get_instance().translate(
                        body,
                        from_lang=source_lang,
                        to_lang=target_lang,
                    )
                )
                translation_engine = "nado-translator"
                translation_status = "done"
            except Exception as exc:
                logger.warning(
                    "group recipient translation failed "
                    "room=%s message=%s recipient=%s %s->%s err=%s",
                    room.room_uuid,
                    message.message_uuid,
                    member.user_id,
                    source_lang,
                    target_lang,
                    exc,
                )
                translation_status = "failed"
                failure_code = "translation_error"
                failure_detail = str(exc)
                delivered_at = None

        translation_rows.append(
            models.ChatMessageTranslation(
                message_id=message.id,
                recipient_user_id=member.user_id,
                target_lang=target_lang,
                translated_body=translated_body,
                translation_engine=translation_engine,
                translation_status=translation_status,
                failure_code=failure_code,
                failure_detail=failure_detail,
                delivered_at=delivered_at,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
        )

    for translation_row in translation_rows:
        db.add(translation_row)

    if not translation_rows:
        message.translation_status = "none"
        return

    delivery_summary = _build_group_delivery_summary(translation_rows)
    message.translation_status = str(delivery_summary["status"])


def _serialize_message(
    db: Session,
    room: models.ChatRoom,
    message: models.ChatMessage,
    current_user_id: int,
) -> dict[str, Any]:
    sender_user_id = message.sender_user_id
    created_at = message.created_at
    sender = None
    if sender_user_id is not None:
        sender = (
            db.query(models.User)
            .filter(models.User.id == sender_user_id)
            .first()
        )
    sender_summary = _serialize_user_summary(sender)
    translation_rows: list[models.ChatMessageTranslation] = []
    viewer_translation_row = None
    viewer_translation_payload = None
    if room.room_type == "group" and room.title != SELF_ROOM_TITLE:
        translation_rows = _list_message_translations(db, message.id)
        viewer_translation_row = _select_group_viewer_translation(
            translation_rows,
            current_user_id,
        )
        viewer_translation_payload = _serialize_viewer_translation(
            viewer_translation_row
        )
        if (
            viewer_translation_payload is None
            and (
                message.translated_body is not None
                or message.body_target_lang is not None
            )
        ):
            viewer_translation_payload = (
                _build_group_viewer_translation_fallback(
                    db,
                    message,
                    current_user_id,
                )
            )

    payload = {
        "message_id": message.message_uuid,
        "room_id": room.room_uuid,
        "sender_user_id": sender_user_id,
        "sender_label": (
            sender_summary["nickname"] if sender_summary else "system"
        ),
        "sender_voice_id": (
            sender_summary["voice_id"] if sender_summary else None
        ),
        "message_type": message.message_type,
        "body": message.body,
        "translated_body": (
            viewer_translation_payload.get("translated_body")
            if viewer_translation_payload is not None
            else message.translated_body
        ),
        "body_source_lang": message.body_source_lang,
        "body_target_lang": (
            viewer_translation_payload.get("target_lang")
            if viewer_translation_payload is not None
            else message.body_target_lang
        ),
        "translation_status": (
            viewer_translation_payload.get("translation_status")
            if viewer_translation_payload is not None
            else message.translation_status
        ),
        "created_at": created_at.isoformat() if created_at else "",
        "mine": (sender_user_id or 0) == current_user_id,
    }
    if room.room_type == "group" and room.title != SELF_ROOM_TITLE:
        payload["viewer_translation"] = viewer_translation_payload
        payload["delivery_summary"] = _build_group_delivery_summary(
            translation_rows
        )
    return payload


def _serialize_message_created_event(
    db: Session,
    room: models.ChatRoom,
    message: models.ChatMessage,
    viewer_user_id: int,
) -> dict[str, Any]:
    return {
        "type": "message_created",
        "room_id": room.room_uuid,
        "viewer_user_id": viewer_user_id,
        "message": _serialize_message(
            db,
            room,
            message,
            viewer_user_id,
        ),
    }


def _resolve_message_preview(
    db: Session,
    room: models.ChatRoom,
    message: models.ChatMessage,
    current_user_id: int,
) -> str:
    if room.room_type == "group" and room.title != SELF_ROOM_TITLE:
        viewer_translation_row = _select_group_viewer_translation(
            _list_message_translations(db, message.id),
            current_user_id,
        )
        if viewer_translation_row is not None:
            return (
                _normalize_text(
                    viewer_translation_row.translated_body or message.body,
                    max_length=80,
                )
                or ""
            )

    return (
        _normalize_text(
            message.translated_body or message.body,
            max_length=80,
        )
        or ""
    )


def _resolve_room_title(
    db: Session,
    room: models.ChatRoom,
    current_user_id: int,
    members: list[models.ChatRoomMember],
) -> tuple[str, Optional[dict[str, Any]]]:
    counterpart = None
    if room.room_type == "direct":
        counterpart_member = next(
            (
                member
                for member in members
                if member.user_id != current_user_id
            ),
            None,
        )
        if counterpart_member is not None:
            counterpart_user = (
                db.query(models.User)
                .filter(models.User.id == counterpart_member.user_id)
                .first()
            )
            counterpart = _serialize_user_summary(counterpart_user)
            if counterpart is not None:
                return counterpart["nickname"], counterpart
    title = _normalize_text(room.title, max_length=120)
    return title or "이름 없는 대화방", counterpart


def _compute_unread_count(
    db: Session,
    room: models.ChatRoom,
    member: models.ChatRoomMember,
    current_user_id: int,
) -> int:
    query = db.query(models.ChatMessage).filter(
        models.ChatMessage.room_id == room.id,
        models.ChatMessage.is_deleted.is_(False),
    )
    if member.last_read_at is not None:
        query = query.filter(
            models.ChatMessage.created_at > member.last_read_at
        )
    query = query.filter(
        (models.ChatMessage.sender_user_id.is_(None))
        | (models.ChatMessage.sender_user_id != current_user_id)
    )
    return query.count()


def _normalize_group_member_limit(member_limit: Optional[int]) -> int:
    normalized = (
        DEFAULT_GROUP_ROOM_MEMBER_LIMIT
        if member_limit is None
        else int(member_limit)
    )
    if (
        normalized < GROUP_ROOM_MIN_MEMBER_LIMIT
        or normalized > GROUP_ROOM_MAX_MEMBER_LIMIT
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"그룹방 정원은 {GROUP_ROOM_MIN_MEMBER_LIMIT}명부터 "
                f"{GROUP_ROOM_MAX_MEMBER_LIMIT}명까지만 설정할 수 있습니다"
            ),
        )
    return normalized


def _resolve_room_member_limit(room: models.ChatRoom) -> Optional[int]:
    if room.room_type != "group":
        return None
    if room.title == SELF_ROOM_TITLE:
        return 1
    stored_limit = getattr(room, "member_limit", None)
    if isinstance(stored_limit, int):
        return _normalize_group_member_limit(stored_limit)
    return DEFAULT_GROUP_ROOM_MEMBER_LIMIT


def _assert_group_room_capacity(
    room: models.ChatRoom,
    *,
    current_member_count: int,
    incoming_member_count: int = 0,
) -> None:
    member_limit = _resolve_room_member_limit(room)
    if member_limit is None:
        return
    next_member_count = current_member_count + incoming_member_count
    if next_member_count <= member_limit:
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"이 그룹방 정원은 {member_limit}명으로 고정되어 있어 더 이상 입장할 수 없습니다"
        ),
    )


def _can_invite_members(
    room: models.ChatRoom,
    current_user_id: int,
    current_member_count: Optional[int] = None,
) -> bool:
    return (
        room.room_type == "group"
        and room.title != SELF_ROOM_TITLE
        and (
            current_member_count is None
            or current_member_count < _resolve_room_member_limit(room) # type: ignore
        )
        and (
            room.owner_user_id == current_user_id
            or room.allow_member_invites
        )
    )


def _serialize_room_summary(
    db: Session, room: models.ChatRoom, current_user_id: int
) -> dict[str, Any]:
    last_message_id = room.last_message_id
    last_message_at = room.last_message_at
    created_at = room.created_at
    members = _get_room_members(db, room.id)
    current_member = next(
        (
            member
            for member in members
            if member.user_id == current_user_id
        ),
        None,
    )
    if current_member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="대화방 접근 권한이 없습니다",
        )
    title, counterpart = _resolve_room_title(
        db, room, current_user_id, members
    )
    last_message = None
    if last_message_id is not None:
        last_message = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.id == last_message_id)
            .first()
        )
    preview = ""
    message_type = None
    display_last_message_at = last_message_at or created_at
    if last_message is not None:
        preview = _resolve_message_preview(
            db,
            room,
            last_message,
            current_user_id,
        )
        message_type = last_message.message_type
        display_last_message_at = (
            last_message.created_at or display_last_message_at
        )
    return {
        "room_id": room.room_uuid,
        "room_type": room.room_type,
        "title": title,
        "member_count": len(members),
        "member_limit": _resolve_room_member_limit(room),
        "allow_member_invites": room.allow_member_invites,
        "can_invite_members": _can_invite_members(
            room,
            current_user_id,
            len(members),
        ),
        "unread_count": _compute_unread_count(
            db, room, current_member, current_user_id
        ),
        "last_message_preview": preview,
        "last_message_type": message_type,
        "last_message_at": (
            display_last_message_at.isoformat()
            if display_last_message_at
            else ""
        ),
        "counterpart": counterpart,
    }


def _serialize_room_detail(
    db: Session, room: models.ChatRoom, current_user_id: int
) -> dict[str, Any]:
    members = _get_room_members(db, room.id)
    title, counterpart = _resolve_room_title(
        db, room, current_user_id, members
    )
    serialized_members: list[dict[str, Any]] = []
    for member in members:
        user = (
            db.query(models.User)
            .filter(models.User.id == member.user_id)
            .first()
        )
        summary = _serialize_user_summary(user)
        serialized_members.append(
            {
                "user_id": member.user_id,
                "nickname": summary["nickname"] if summary else "사용자",
                "voice_id": summary["voice_id"] if summary else None,
                "preferred_language": (
                    summary["preferred_language"] if summary else None
                ),
                "role": member.role,
                "membership_status": member.membership_status,
            }
        )
    return {
        "room_id": room.room_uuid,
        "room_type": room.room_type,
        "title": title,
        "owner_user_id": room.owner_user_id,
        "default_source_lang": room.default_source_lang,
        "default_target_lang": room.default_target_lang,
        "translation_mode": room.translation_mode,
        "member_limit": _resolve_room_member_limit(room),
        "allow_member_invites": room.allow_member_invites,
        "can_invite_members": _can_invite_members(
            room,
            current_user_id,
            len(members),
        ),
        "counterpart": counterpart,
        "members": serialized_members,
    }


def _create_room_member(
    room_id: int, user_id: int, role: str
) -> models.ChatRoomMember:
    return models.ChatRoomMember(
        room_id=room_id,
        user_id=user_id,
        role=role,
        membership_status=ACTIVE_MEMBERSHIP,
        joined_at=_utcnow(),
        mute_notifications=False,
    )


def _can_manage_group_room(
    room: models.ChatRoom,
    membership: models.ChatRoomMember,
    current_user: Any,
) -> bool:
    current_user_id = int(current_user.id)
    return (
        getattr(current_user, "is_admin", False)
        or membership.role == "owner"
        or room.allow_member_invites
        or room.owner_user_id == current_user_id
    )


def _require_friend_link(
    db: Session,
    owner_user_id: int,
    invited_user_id: int,
    current_user: Any,
) -> None:
    if getattr(current_user, "is_admin", False):
        return
    friend_link = (
        db.query(models.Friend)
        .filter(
            models.Friend.user_id == owner_user_id,
            models.Friend.friend_user_id == invited_user_id,
        )
        .first()
    )
    if friend_link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="친구 관계가 확인되지 않은 사용자는 초대할 수 없습니다",
        )


def _append_message(
    db: Session,
    *,
    room: models.ChatRoom,
    sender_user_id: int,
    message_type: str,
    body: str,
    translated_body: Optional[str],
    source_lang: Optional[str],
    target_lang: Optional[str],
    request_translation: bool,
    reply_to_message_id: Optional[str],
    translation_engine: Optional[str] = None,
) -> models.ChatMessage:
    room_id = room.id
    reply_to_id = None
    if reply_to_message_id:
        reply_target = (
            db.query(models.ChatMessage)
            .filter(
                models.ChatMessage.room_id == room_id,
                models.ChatMessage.message_uuid == reply_to_message_id,
            )
            .first()
        )
        if reply_target is not None:
            reply_to_id = reply_target.id
    normalized_message_type = (
        _normalize_text(message_type, max_length=24) or "text"
    )
    (
        resolved_translated_body,
        resolved_source_lang,
        resolved_target_lang,
        resolved_engine,
    ) = _resolve_message_translation(
        db,
        room,
        sender_user_id,
        normalized_message_type,
        body,
        translated_body,
        source_lang,
        target_lang,
        request_translation,
    )
    message = models.ChatMessage(
        message_uuid=str(uuid4()),
        room_id=room_id,
        sender_user_id=sender_user_id,
        message_type=normalized_message_type,
        body=body,
        translated_body=(
            None
            if (
                room.room_type == "group"
                and room.title != SELF_ROOM_TITLE
            )
            else resolved_translated_body
        ),
        body_source_lang=resolved_source_lang,
        body_target_lang=(
            None
            if (
                room.room_type == "group"
                and room.title != SELF_ROOM_TITLE
            )
            else resolved_target_lang
        ),
        translation_engine=(
            None
            if (
                room.room_type == "group"
                and room.title != SELF_ROOM_TITLE
            )
            else resolved_engine
            or _normalize_text(translation_engine, max_length=40)
        ),
        translation_status=(
            "pending"
            if (
                request_translation
                and (
                    room.room_type != "group"
                    or room.title == SELF_ROOM_TITLE
                )
                and not resolved_translated_body
                and resolved_source_lang is not None
                and resolved_target_lang is not None
                and resolved_source_lang != resolved_target_lang
            )
            else ("done" if resolved_translated_body else "none")
        ),
        reply_to_message_id=reply_to_id,
        created_at=_utcnow(),
    )
    db.add(message)
    db.flush()
    _append_group_message_translations(
        db,
        room=room,
        message=message,
        sender_user_id=sender_user_id,
        body=body,
        source_lang=resolved_source_lang,
        request_translation=request_translation,
    )
    message_id = message.id
    message_created_at = message.created_at or _utcnow()
    room.last_message_id = message_id
    room.last_message_at = message_created_at
    room.updated_at = message_created_at
    sender_member = (
        db.query(models.ChatRoomMember)
        .filter(
            models.ChatRoomMember.room_id == room_id,
            models.ChatRoomMember.user_id == sender_user_id,
            models.ChatRoomMember.membership_status == ACTIVE_MEMBERSHIP,
        )
        .first()
    )
    if sender_member is not None:
        sender_member.last_read_message_id = message_id
        sender_member.last_read_at = message_created_at
    db.flush()
    return message


@router.get("/rooms")
def list_chat_rooms(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    current_user_id = int(current_user.id)
    memberships = (
        db.query(models.ChatRoomMember)
        .filter(
            models.ChatRoomMember.user_id == current_user_id,
            models.ChatRoomMember.membership_status == ACTIVE_MEMBERSHIP,
        )
        .order_by(models.ChatRoomMember.id.desc())
        .all()
    )
    room_ids = [item.room_id for item in memberships]
    if not room_ids:
        return {"items": [], "next_cursor": None}

    rooms = (
        db.query(models.ChatRoom)
        .filter(
            models.ChatRoom.id.in_(room_ids),
            models.ChatRoom.is_archived.is_(False),
        )
        .order_by(
            models.ChatRoom.last_message_at.desc(),
            models.ChatRoom.id.desc(),
        )
        .all()
    )
    return {
        "items": [
            _serialize_room_summary(db, room, current_user_id)
            for room in rooms
        ],
        "next_cursor": None,
    }


@router.post("/rooms/direct")
def create_or_get_direct_room(
    request: DirectRoomCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    current_user_id = int(current_user.id)
    friend_user_id = request.friend_user_id
    if friend_user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신과 direct room을 만들 수 없습니다",
        )
    friend_link = (
        db.query(models.Friend)
        .filter(
            models.Friend.user_id == current_user_id,
            models.Friend.friend_user_id == friend_user_id,
        )
        .first()
    )
    if friend_link is None and not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="친구 관계가 확인되지 않았습니다",
        )
    friend_user = _resolve_user(db, friend_user_id)
    room = _find_direct_room(db, current_user_id, friend_user_id)
    created_now = room is None
    owner_language = _resolve_user_language(current_user)
    friend_language = _resolve_user_language(friend_user)
    if room is None:
        now = _utcnow()
        room = models.ChatRoom(
            room_uuid=str(uuid4()),
            room_type="direct",
            owner_user_id=current_user_id,
            default_source_lang=owner_language,
            default_target_lang=friend_language,
            translation_mode="direct_auto",
            last_message_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(room)
        db.flush()
        db.add_all(
            [
                _create_room_member(room.id, current_user_id, "owner"),
                _create_room_member(room.id, friend_user_id, "member"),
            ]
        )
        db.flush()
    initial_message = _normalize_text(request.initial_message)
    if created_now and initial_message:
        _append_message(
            db,
            room=room,
            sender_user_id=current_user_id,
            message_type="text",
            body=initial_message,
            translated_body=None,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            request_translation=False,
            reply_to_message_id=None,
        )
    db.commit()
    db.refresh(room)
    return _serialize_room_summary(db, room, current_user_id)


@router.post("/rooms/group")
def create_group_room(
    request: GroupRoomCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    current_user_id = int(current_user.id)
    title = _normalize_text(request.title, max_length=120)
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="그룹방 이름을 입력해야 합니다",
        )
    member_user_ids = sorted(
        {
            user_id
            for user_id in request.member_user_ids
            if user_id != current_user_id
        }
    )
    member_limit = _normalize_group_member_limit(request.member_limit)
    initial_member_count = len(member_user_ids) + 1
    if initial_member_count > member_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"현재 선택한 인원은 총 {initial_member_count}명입니다. "
                f"정원 {member_limit}명 이하로만 그룹방을 만들 수 있습니다"
            ),
        )
    for user_id in member_user_ids:
        _resolve_user(db, user_id)
    now = _utcnow()
    room = models.ChatRoom(
        room_uuid=str(uuid4()),
        room_type="group",
        title=title,
        owner_user_id=current_user_id,
        default_source_lang=None,
        default_target_lang=None,
        translation_mode=(
            _normalize_text(request.translation_mode, max_length=20)
            or "assist"
        ),
        allow_member_invites=request.allow_member_invites,
        member_limit=member_limit,
        last_message_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(room)
    db.flush()
    db.add(_create_room_member(room.id, current_user_id, "owner"))
    for user_id in member_user_ids:
        db.add(_create_room_member(room.id, user_id, "member"))
    db.commit()
    db.refresh(room)
    return _serialize_room_summary(db, room, current_user_id)


@router.post("/rooms/self")
def create_or_get_self_room(
    request: SelfRoomCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    current_user_id = int(current_user.id)
    room = _find_self_room(db, current_user_id)
    created_now = room is None
    if room is None:
        now = _utcnow()
        room = models.ChatRoom(
            room_uuid=str(uuid4()),
            room_type="group",
            title=SELF_ROOM_TITLE,
            owner_user_id=current_user_id,
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
        db.add(
            _create_room_member(room.id, current_user_id, "owner")
        )
        db.flush()
    initial_message = _normalize_text(request.initial_message)
    if created_now and initial_message:
        _append_message(
            db,
            room=room,
            sender_user_id=current_user_id,
            message_type="text",
            body=initial_message,
            translated_body=None,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            request_translation=False,
            reply_to_message_id=None,
        )
    db.commit()
    db.refresh(room)
    return _serialize_room_summary(db, room, current_user_id)


@router.get("/rooms/{room_id}")
def get_chat_room_detail(
    room_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    current_user_id = int(current_user.id)
    room, _member = _require_room_member(db, room_id, current_user_id)
    return _serialize_room_detail(db, room, current_user_id)


@router.patch("/rooms/{room_id}/settings")
def update_chat_room_settings(
    room_id: str,
    request: RoomSettingsUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    current_user_id = int(current_user.id)
    room, membership = _require_room_member(db, room_id, current_user_id)
    if room.room_type != "group":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="그룹방에서만 설정을 변경할 수 있습니다",
        )
    if room.title == SELF_ROOM_TITLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="번역 보관함 설정은 변경할 수 없습니다",
        )
    if (
        membership.role != "owner"
        and not getattr(current_user, "is_admin", False)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="방 설정을 변경할 권한이 없습니다",
        )

    if (
        request.allow_member_invites is None
        and request.member_limit is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="변경할 그룹방 설정을 하나 이상 전달해야 합니다",
        )

    if request.allow_member_invites is not None:
        room.allow_member_invites = request.allow_member_invites

    if request.member_limit is not None:
        next_member_limit = _normalize_group_member_limit(request.member_limit)
        active_member_count = len(_get_room_members(db, room.id))
        if active_member_count > next_member_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"현재 활성 멤버가 {active_member_count}명이라 정원을 "
                    f"{next_member_limit}명으로 낮출 수 없습니다"
                ),
            )
        room.member_limit = next_member_limit

    room.updated_at = _utcnow()
    db.commit()
    db.refresh(room)
    return _serialize_room_detail(db, room, current_user_id)


@router.post("/rooms/{room_id}/members")
def add_chat_room_members(
    room_id: str,
    request: RoomMembersAddRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    current_user_id = int(current_user.id)
    room, membership = _require_room_member(db, room_id, current_user_id)
    if room.room_type != "group":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="그룹방에서만 멤버를 초대할 수 있습니다",
        )
    if room.title == SELF_ROOM_TITLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="번역 보관함에는 다른 멤버를 초대할 수 없습니다",
        )
    if not _can_manage_group_room(room, membership, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="멤버를 초대할 권한이 없습니다",
        )

    requested_user_ids = sorted(
        {
            user_id
            for user_id in request.member_user_ids
            if user_id != current_user_id
        }
    )
    if not requested_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="초대할 멤버를 선택해야 합니다",
        )

    room_id_value = room.id
    active_members = _get_room_members(db, room_id_value)
    active_member_ids = {member.user_id for member in active_members}
    candidate_user_ids = [
        user_id
        for user_id in requested_user_ids
        if user_id not in active_member_ids
    ]
    _assert_group_room_capacity(
        room,
        current_member_count=len(active_members),
        incoming_member_count=len(candidate_user_ids),
    )
    added_user_ids: list[int] = []

    for user_id in requested_user_ids:
        _resolve_user(db, user_id)
        _require_friend_link(db, current_user_id, user_id, current_user)
        if user_id in active_member_ids:
            continue
        db.add(_create_room_member(room_id_value, user_id, "member"))
        added_user_ids.append(user_id)

    if added_user_ids:
        labels: list[str] = []
        for user_id in added_user_ids:
            invited_user = (
                db.query(models.User)
                .filter(models.User.id == user_id)
                .first()
            )
            labels.append(
                (_serialize_user_summary(invited_user) or {}).get("nickname")
                or f"user-{user_id}"
            )
        _append_message(
            db,
            room=room,
            sender_user_id=current_user_id,
            message_type="system_invite",
            body=f"초대 멤버: {', '.join(labels)}",
            translated_body=None,
            source_lang=None,
            target_lang=None,
            request_translation=False,
            reply_to_message_id=None,
        )

    db.commit()
    db.refresh(room)
    return {
        "room": _serialize_room_detail(db, room, current_user_id),
        "added_user_ids": added_user_ids,
    }


@router.get("/rooms/{room_id}/messages")
def list_chat_room_messages(
    room_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    current_user_id = int(current_user.id)
    room, _member = _require_room_member(db, room_id, current_user_id)
    latest_messages = (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.room_id == room.id,
            models.ChatMessage.is_deleted.is_(False),
        )
        .order_by(
            models.ChatMessage.created_at.desc(),
            models.ChatMessage.id.desc(),
        )
        .limit(limit)
        .all()
    )
    messages = list(reversed(latest_messages))
    return {
        "items": [
            _serialize_message(db, room, message, current_user_id)
            for message in messages
        ],
        "next_cursor": None,
    }


@router.websocket("/rooms/{room_id}/ws")
async def websocket_chat_room_events(
    websocket: WebSocket,
    room_id: str,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    header_token = str(
        websocket.headers.get("authorization") or ""
    ).removeprefix("Bearer ").strip()
    authenticated_user = _resolve_authenticated_chat_user_from_token(
        db,
        token or header_token,
    )
    if authenticated_user is None or not getattr(
        authenticated_user, "is_active", False
    ):
        await websocket.close(code=4401)
        return

    current_user_id = int(authenticated_user.id)
    try:
        _require_room_member(db, room_id, current_user_id)
    except HTTPException:
        await websocket.close(code=4403)
        return

    await chat_room_ws_hub.connect(room_id, current_user_id, websocket)
    try:
        await websocket.send_json(
            {
                "type": "chat_room_ready",
                "room_id": room_id,
                "viewer_user_id": current_user_id,
            }
        )
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                        "room_id": room_id,
                        "viewer_user_id": current_user_id,
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        chat_room_ws_hub.disconnect(room_id, current_user_id, websocket)


@router.post("/rooms/{room_id}/messages")
async def create_chat_message(
    room_id: str,
    request: MessageCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    current_user_id = int(current_user.id)
    room, _member = _require_room_member(db, room_id, current_user_id)
    body = _normalize_text(request.body)
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="메시지 본문을 입력해야 합니다",
        )
    sender = (
        db.query(models.User)
        .filter(models.User.id == current_user_id)
        .first()
    )
    designated_language = _resolve_user_language(sender)
    if (
        designated_language
        and (request.message_type or "text") == "text"
        and not text_matches_designated_language(body, designated_language)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=DESIGNATED_LANGUAGE_MISMATCH_DETAIL,
        )
    message = _append_message(
        db,
        room=room,
        sender_user_id=current_user_id,
        message_type=request.message_type,
        body=body,
        translated_body=request.translated_body,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        request_translation=request.request_translation,
        reply_to_message_id=request.reply_to_message_id,
    )
    db.commit()
    db.refresh(room)
    db.refresh(message)
    active_members = _get_room_members(db, room.id)
    serialized_sender = _serialize_message(db, room, message, current_user_id)
    sender_label = str(serialized_sender.get("sender_label") or "친구")
    body_preview = _normalize_text(body, max_length=80)
    for member in active_members:
        member_user_id = int(member.user_id)
        await chat_room_ws_hub.send_to_user(
            room.room_uuid,
            member_user_id,
            _serialize_message_created_event(
                db,
                room,
                message,
                member_user_id,
            ),
        )
        if member_user_id == current_user_id:
            continue
        if chat_room_ws_hub.is_user_connected(room.room_uuid, member_user_id):
            continue
        await send_push_to_user(
            member_user_id,
            data_payload={
                "type": "chat_message",
                "room_id": room.room_uuid,
                "message_id": message.message_uuid,
                "sender_label": sender_label,
                "body_preview": body_preview,
                "alert_phrase": "친구야~",
            },
            title="(월드링코) 채팅",
            body=f"{sender_label}: 친구야~ {body_preview}",
            channel_id="worldlinco_chat_message",
        )
    return serialized_sender


@router.post("/rooms/{room_id}/read")
def mark_chat_room_read(
    room_id: str,
    request: ReadUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    current_user_id = int(current_user.id)
    room, member = _require_room_member(db, room_id, current_user_id)
    room_last_message_id = room.last_message_id
    target_message = None
    if request.last_read_message_id:
        target_message = (
            db.query(models.ChatMessage)
            .filter(
                models.ChatMessage.room_id == room.id,
                models.ChatMessage.message_uuid
                == request.last_read_message_id,
                models.ChatMessage.is_deleted.is_(False),
            )
            .first()
        )
    if target_message is None and room.last_message_id is not None:
        target_message = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.id == room_last_message_id)
            .first()
        )
    target_message_id = (
        target_message.id if target_message is not None else None
    )
    target_message_created_at = (
        target_message.created_at if target_message is not None else None
    )
    member.last_read_message_id = target_message_id
    member.last_read_at = target_message_created_at or _utcnow()
    db.commit()
    return {
        "status": "ok",
        "room_id": room.room_uuid,
        "last_read_message_id": (
            target_message.message_uuid if target_message is not None else None
        ),
    }
