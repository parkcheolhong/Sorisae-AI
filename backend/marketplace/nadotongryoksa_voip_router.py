"""
VoIP Call Management Router
Handles call initiation, signaling relay, and call state management
Integrates with PSTN gateway for reservation center outbound
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta, timezone
import base64
import importlib
import uuid
import json
import logging
import asyncio
import os
import time
import urllib.error
import urllib.request
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from backend.database import SessionLocal, get_db
from backend.auth import get_current_user, SECRET_KEY, ALGORITHM
from backend.marketplace import models
from backend.marketplace.call_mode_schema import (
    CallModeAuditEventCreate,
    CallModeAuditEventRead,
)
from backend.marketplace.nadotongryoksa_chat_router import (
    _append_message as _append_chat_message,
    _create_room_member as _create_chat_room_member,
    _find_direct_room as _find_direct_chat_room,
    _normalize_text as _normalize_chat_text,
    _resolve_user_language,
    _serialize_message as _serialize_chat_message,
)
from backend.marketplace.services.call_mode_audit_service import (
    _deserialize_metadata,
    list_call_mode_events,
    record_call_mode_event,
)

try:
    GoogleAuthRequest = importlib.import_module(
        "google.auth.transport.requests"
    ).Request
    service_account = importlib.import_module(
        "google.oauth2.service_account"
    )
except Exception:  # pragma: no cover - optional runtime dependency
    GoogleAuthRequest = None
    service_account = None

try:
    from aiortc import (
        RTCConfiguration,
        RTCIceCandidate,
        RTCIceServer,
        RTCPeerConnection,
        RTCSessionDescription,
    )
    from aiortc.sdp import candidate_from_sdp
except Exception:  # pragma: no cover - optional runtime dependency
    RTCConfiguration = None
    RTCIceCandidate = None
    RTCIceServer = None
    RTCPeerConnection = None
    RTCSessionDescription = None
    candidate_from_sdp = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/voip", tags=["voip"])

# ============================================================================
# Data Models
# ============================================================================


class TURNServer(BaseModel):
    urls: List[str]
    username: Optional[str] = None
    credential: Optional[str] = None


class CallInitiateRequest(BaseModel):
    """Request to initiate a VoIP call"""
    callee_phone: Optional[str] = None
    # E.164-like format, e.g. +82-10-1234-5678
    callee_user_id: Optional[int] = None
    callee_voice_id: Optional[str] = None
    friend_id: Optional[int] = None
    caller_id: str  # user@nadotongryoksa
    session_id: Optional[str] = None
    # interpreter session ID for translation relay
    mode: Optional[str] = None
    auto_relay: Optional[bool] = None


class CallInitiateResponse(BaseModel):
    """Response with call ID and signaling server details"""
    call_id: str
    signaling_server: str
    turn_servers: List[TURNServer]
    call_route: str = "app_webrtc"
    pstn_gateway_configured: bool = False
    phone_dialer_required: bool = False
    callee_app_online: bool = False
    caller_voice_id: Optional[str] = None
    callee_voice_id: Optional[str] = None
    callee_user_id: Optional[int] = None
    participant_role: str = "caller"
    display_label: Optional[str] = None
    display_language: Optional[str] = None
    display_country_code: Optional[str] = None
    status: Optional[str] = None
    user_message: Optional[str] = None
    fallback_dial_url: Optional[str] = None
    requested_mode: str = "pstn_assist"
    resolved_mode: str = "pstn_assist"
    auto_relay_requested: bool = False
    auto_relay_applied: bool = False
    error_code: Optional[str] = None


class PendingIncomingCallResponse(CallInitiateResponse):
    caller_user_id: Optional[int] = None
    caller_label: Optional[str] = None


def _default_turn_servers() -> List[TURNServer]:
    return [
        TURNServer(urls=["stun:stun.l.google.com:19302"]),
        TURNServer(urls=["stun:stun1.l.google.com:19302"]),
        TURNServer(urls=["stun:stun.cloudflare.com:3478"]),
    ]


class CallEndRequest(BaseModel):
    """Request to end a call"""
    duration_sec: int
    call_quality: Optional[str] = None  # "good", "fair", "poor"


# ============================================================================
# In-Memory Call State (Production: use Redis)
# ============================================================================

class CallState:
    def __init__(
        self,
        call_id: str,
        callee_phone: Optional[str],
        caller_id: str,
        session_id: Optional[str],
        caller_user_id: Optional[int] = None,
        callee_user_id: Optional[int] = None,
        caller_voice_id: Optional[str] = None,
        callee_voice_id: Optional[str] = None,
        call_route: str = "native_phone_dialer",
        requested_mode: str = "pstn_assist",
        resolved_mode: str = "pstn_assist",
        auto_relay_requested: bool = False,
        auto_relay_applied: bool = False,
        error_code: Optional[str] = None,
    ):
        self.call_id = call_id
        self.callee_phone = callee_phone
        self.caller_id = caller_id
        self.session_id = session_id
        self.caller_user_id = caller_user_id
        self.callee_user_id = callee_user_id
        self.caller_voice_id = caller_voice_id
        self.callee_voice_id = callee_voice_id
        self.call_route = call_route
        self.requested_mode = requested_mode
        self.resolved_mode = resolved_mode
        self.auto_relay_requested = auto_relay_requested
        self.auto_relay_applied = auto_relay_applied
        self.error_code = error_code
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.created_at = now
        self.updated_at = now
        self.status_changed_at = now
        self.status = "initiated"  # initiated → ringing → active → ended
        self.local_sdp: Optional[str] = None
        self.remote_sdp: Optional[str] = None
        self.duration_sec = 0
        self.incoming_payload: Optional[Dict[str, Any]] = None

    def set_status(self, status: str) -> None:
        self.status = status
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.updated_at = now
        self.status_changed_at = now


STALE_RESUMABLE_CALL_TTL_SECONDS = max(
    30,
    int(os.getenv("VOIP_STALE_RESUMABLE_CALL_TTL_SECONDS", "120")),
)
RESUMABLE_VOIP_STATUSES = {"initiated", "ringing", "callee_offline", "connecting", "active"}


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _resumable_call_age_seconds(call_state: CallState) -> float:
    anchor = call_state.status_changed_at or call_state.updated_at or call_state.created_at
    return max(0.0, (_utc_now_naive() - anchor).total_seconds())


def _cleanup_call_runtime_state(call_id: str) -> None:
    call_participants.pop(call_id, None)
    pending_signal_messages.pop(call_id, None)
    signal_queue_alert_last_len.pop(call_id, None)
    stale_client_keys = [
        key
        for key in list(connected_clients.keys())
        if key == call_id or str(key).startswith(f"{call_id}:")
    ]
    for key in stale_client_keys:
        connected_clients.pop(key, None)


def _collapse_voice_relay_text(text: str, min_repeat: int = 3) -> str:
    import re

    trimmed = re.sub(r"\s+", " ", str(text or "").strip())
    if not trimmed:
        return ""
    sentence_parts = [
        part.strip().rstrip(".!?。")
        for part in re.split(r"\.\s+", trimmed)
        if part.strip()
    ]
    if len(sentence_parts) >= min_repeat:
        first_norm = sentence_parts[0].casefold()
        if all(part.casefold() == first_norm for part in sentence_parts):
            return sentence_parts[0]
    comma_parts = [part.strip() for part in trimmed.split(", ") if part.strip()]
    if len(comma_parts) >= min_repeat:
        first_norm = comma_parts[0].casefold()
        if all(part.casefold() == first_norm for part in comma_parts):
            return comma_parts[0]
    return trimmed


def _should_reject_voice_translation_relay(
    *,
    source_lang: str,
    target_lang: str,
    transcript: str,
    translated_text: str,
) -> bool:
    if not transcript or not translated_text:
        return True
    source = str(source_lang or "").strip().lower().split("-")[0]
    target = str(target_lang or "").strip().lower().split("-")[0]
    if source and target and source != target:
        normalized_transcript = " ".join(transcript.strip().lower().split())
        normalized_translation = " ".join(translated_text.strip().lower().split())
        if normalized_transcript == normalized_translation:
            return True
    return False


VALID_CALL_MODES = {"pstn_assist", "voip_full_auto"}


def _normalize_call_mode(
    raw_mode: Optional[str], *, has_app_target: bool
) -> str:
    normalized = str(raw_mode or "").strip().lower()
    if normalized in VALID_CALL_MODES:
        return normalized
    return "voip_full_auto" if has_app_target else "pstn_assist"


def _append_mode_message(
    message: str,
    *,
    resolved_mode: str,
    auto_relay_applied: bool,
    error_code: Optional[str],
) -> str:
    suffixes: List[str] = []
    if resolved_mode == "voip_full_auto":
        suffixes.append("모드: VoIP 완전자동")
    else:
        suffixes.append("모드: 일반통화 보조")
    if auto_relay_applied:
        suffixes.append("자동 릴레이 활성화")
    if error_code == "VOIP_MODE_FALLBACK_TO_PSTN_ASSIST":
        suffixes.append("전화번호 전용 대상이라 일반통화 보조 경로로 폴백")
    elif error_code == "PSTN_ASSIST_REQUIRES_PHONE_TARGET":
        suffixes.append("전화번호가 없어 VoIP 경로 유지")
    return f"{message} ({' / '.join(suffixes)})" if suffixes else message


def _record_call_mode_audit(
    db: Session,
    *,
    call_id: str,
    session_id: Optional[str],
    event_type: str,
    requested_mode: str,
    resolved_mode: str,
    auto_relay_requested: bool,
    auto_relay_applied: bool,
    call_route: Optional[str],
    caller_user_id: Optional[int],
    callee_user_id: Optional[int],
    callee_phone: Optional[str],
    status: Optional[str],
    error_code: Optional[str],
    latency_ms: Optional[int] = None,
    duration_sec: Optional[int] = None,
    call_quality: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    record_call_mode_event(
        db,
        CallModeAuditEventCreate(
            call_id=call_id,
            session_id=session_id,
            event_type=event_type,
            requested_mode=requested_mode,
            resolved_mode=resolved_mode,
            auto_relay_requested=auto_relay_requested,
            auto_relay_applied=auto_relay_applied,
            call_route=call_route,
            caller_user_id=caller_user_id,
            callee_user_id=callee_user_id,
            callee_phone=callee_phone,
            status=status,
            error_code=error_code,
            latency_ms=latency_ms,
            duration_sec=duration_sec,
            call_quality=call_quality,
            metadata=metadata or {},
        ),
    )


# In-memory store (replace with Redis for production)
call_states: Dict[str, CallState] = {}
connected_clients: Dict[str, WebSocket] = {}
call_participants: Dict[str, Dict[str, WebSocket]] = {}
online_voice_clients: Dict[str, WebSocket] = {}
pending_signal_messages: Dict[str, Dict[str, List[dict]]] = {}
signal_queue_alert_last_len: Dict[str, Dict[str, int]] = {}
webrtc_peers: Dict[str, Any] = {}


def _maybe_prune_stale_resumable_call(call_state: CallState, db: Session) -> bool:
    if call_state.status not in RESUMABLE_VOIP_STATUSES:
        return False
    age_seconds = _resumable_call_age_seconds(call_state)
    if age_seconds <= STALE_RESUMABLE_CALL_TTL_SECONDS:
        return False

    participants = call_participants.get(call_state.call_id, {})
    if call_state.status == "active":
        if participants:
            return False
    elif call_state.status == "connecting":
        if participants.get("caller") and participants.get("callee"):
            return False
    elif participants:
        return False

    previous_status = call_state.status
    call_state.set_status("ended")
    call_state.error_code = "STALE_SESSION_PRUNED"
    call_state.duration_sec = 0
    _cleanup_call_runtime_state(call_state.call_id)
    _record_call_mode_audit(
        db,
        call_id=call_state.call_id,
        session_id=call_state.session_id,
        event_type="call_ended",
        requested_mode=call_state.requested_mode,
        resolved_mode=call_state.resolved_mode,
        auto_relay_requested=call_state.auto_relay_requested,
        auto_relay_applied=call_state.auto_relay_applied,
        call_route=call_state.call_route,
        caller_user_id=call_state.caller_user_id,
        callee_user_id=call_state.callee_user_id,
        callee_phone=call_state.callee_phone,
        status=call_state.status,
        error_code=call_state.error_code,
        duration_sec=0,
        metadata={
            "reason": "stale_session_pruned",
            "previous_status": previous_status,
            "age_seconds": int(age_seconds),
        },
    )
    logger.info(
        "[VoIP] Stale resumable call pruned | call_id=%s | previous_status=%s | age_seconds=%s",
        call_state.call_id,
        previous_status,
        int(age_seconds),
    )
    return True


def _call_mode_audit_participant_user_ids(
    events: List[CallModeAuditEventRead],
    call_id: str,
) -> set[int]:
    participant_ids: set[int] = set()
    for event in events:
        if event.caller_user_id is not None:
            participant_ids.add(int(event.caller_user_id))
        if event.callee_user_id is not None:
            participant_ids.add(int(event.callee_user_id))

    call_state = call_states.get(call_id)
    if call_state is not None:
        if call_state.caller_user_id is not None:
            participant_ids.add(int(call_state.caller_user_id))
        if call_state.callee_user_id is not None:
            participant_ids.add(int(call_state.callee_user_id))
    return participant_ids


def _user_can_read_call_mode_audit(
    current_user,
    *,
    call_id: str,
    events: List[CallModeAuditEventRead],
) -> bool:
    if getattr(current_user, "is_admin", False):
        return True
    participant_ids = _call_mode_audit_participant_user_ids(events, call_id)
    if not participant_ids:
        return True
    return int(current_user.id) in participant_ids


def _get_signal_queue_alert_threshold() -> int:
    raw = os.getenv("VOIP_SIGNAL_QUEUE_ALERT_THRESHOLD", "10").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 10


def _maybe_log_signal_queue_threshold(
    call_id: str,
    target_role: str,
    queue_len: int,
    message_type: str,
    sender_role: str,
) -> None:
    threshold = _get_signal_queue_alert_threshold()
    if queue_len < threshold:
        return

    role_state = signal_queue_alert_last_len.setdefault(call_id, {})
    last_logged_len = role_state.get(target_role, 0)
    if queue_len <= last_logged_len:
        return

    role_state[target_role] = queue_len
    queue_snapshot = {
        role: len(messages)
        for role, messages in pending_signal_messages.get(call_id, {}).items()
    }
    logger.error(
        (
            "[VoIP] Signal queue threshold exceeded | call_id=%s | "
            "to=%s | queue_len=%s | threshold=%s | latest_type=%s | "
            "from=%s | queue_snapshot=%s"
        ),
        call_id,
        target_role,
        queue_len,
        threshold,
        message_type,
        sender_role,
        queue_snapshot,
    )


def _build_voice_id(user: Any) -> str:
    return f"nado-{int(user.id):06d}"


def _build_voip_topic(voice_id: str) -> str:
    normalized = "".join(
        ch if ch.isalnum() else "_"
        for ch in str(voice_id or "").strip().lower()
    )
    normalized = "_".join(part for part in normalized.split("_") if part)
    return f"worldlingo_voip_{normalized}" if normalized else ""


def _stringify_push_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return str(value)


def _post_fcm_legacy(server_key: str, payload: dict) -> tuple[int, str]:
    request = urllib.request.Request(
        "https://fcm.googleapis.com/fcm/send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"key={server_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return (
            response.status,
            response.read().decode("utf-8", errors="replace"),
        )


def _load_fcm_service_account_info() -> Optional[dict[str, Any]]:
    if inline_json := os.getenv("FCM_SERVICE_ACCOUNT_JSON", "").strip():
        return json.loads(inline_json)

    if inline_b64 := os.getenv("FCM_SERVICE_ACCOUNT_JSON_B64", "").strip():
        decoded = base64.b64decode(inline_b64.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)

    json_path = os.getenv("FCM_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if json_path and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    return None


def _post_fcm_v1(
    service_account_info: dict[str, Any],
    project_id: str,
    payload: dict,
) -> tuple[int, str]:
    if service_account is None or GoogleAuthRequest is None:
        raise RuntimeError(
            "google-auth dependency is required for FCM v1 push delivery."
        )

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"],
    )
    credentials.refresh(GoogleAuthRequest())
    request = urllib.request.Request(
        f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return (
            response.status,
            response.read().decode("utf-8", errors="replace"),
        )


def _resolve_user_by_voice_id(
    db: Session, voice_id: str
) -> Optional[models.User]:
    normalized = str(voice_id or "").strip().lower()
    if not normalized:
        return None
    if normalized.startswith("nado-"):
        suffix = normalized[5:]
        if suffix.isdigit():
            return (
                db.query(models.User)
                .filter(models.User.id == int(suffix))
                .first()
            )
    return (
        db.query(models.User)
        .filter(
            (models.User.username == normalized)
            | (models.User.email == normalized)
        )
        .first()
    )


def _resolve_authenticated_user_from_token(
    db: Session,
    token: str,
) -> Optional[models.User]:
    token_value = str(token or "").strip()
    if not token_value:
        return None
    try:
        payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
    except JWTError:
        subject = None
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


def _resolve_app_callee(
    db: Session,
    current_user: Any,
    request: CallInitiateRequest,
) -> Optional[models.User]:
    if request.friend_id is not None:
        friend = (
            db.query(models.Friend)
            .filter(models.Friend.id == request.friend_id)
            .first()
        )
        if friend is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="친구 항목을 찾을 수 없습니다",
            )
        if (
            friend.user_id != int(current_user.id)
            and not getattr(current_user, "is_admin", False)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 친구에게 통화할 권한이 없습니다",
            )
        if friend.friend_user_id is None:
            return None
        return (
            db.query(models.User)
            .filter(models.User.id == friend.friend_user_id)
            .first()
        )

    if request.callee_user_id is not None:
        return (
            db.query(models.User)
            .filter(models.User.id == request.callee_user_id)
            .first()
        )

    if request.callee_voice_id:
        return _resolve_user_by_voice_id(db, request.callee_voice_id)

    return None


async def _close_webrtc_peer(call_id: str) -> None:
    peer = webrtc_peers.pop(call_id, None)
    if peer is None:
        return
    try:
        await peer.close()
    except Exception as exc:
        logger.warning(
            "[VoIP] Peer close failed | call_id=%s | error=%s",
            call_id,
            exc,
        )


async def _wait_for_ice_gathering(peer, timeout_sec: float = 5.0) -> None:
    """Wait briefly so aiortc answer SDP includes ICE candidates."""
    if getattr(peer, "iceGatheringState", None) == "complete":
        return
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_sec
    while loop.time() < deadline:
        if getattr(peer, "iceGatheringState", None) == "complete":
            return
        await asyncio.sleep(0.1)


def _build_signaling_server_url(request: Request, call_id: str) -> str:
    forwarded_proto = (
        (request.headers.get("x-forwarded-proto") or "")
        .split(",")[0]
        .strip()
        .lower()
    )
    forwarded_host = (
        (request.headers.get("x-forwarded-host") or "")
        .split(",")[0]
        .strip()
    )
    request_host = (
        (request.headers.get("host") or request.url.netloc or "")
        .split(",")[0]
        .strip()
    )

    proto = forwarded_proto or request.url.scheme or "http"
    host = forwarded_host or request_host or "127.0.0.1:8000"
    ws_proto = "wss" if proto == "https" else "ws"
    return f"{ws_proto}://{host}/api/v1/voip/signal?call_id={call_id}"


def _with_signal_role(signaling_url: str, role: str) -> str:
    separator = "&" if "?" in signaling_url else "?"
    return f"{signaling_url}{separator}role={role}"


def _is_pstn_gateway_configured() -> bool:
    enabled = os.getenv("VOIP_PSTN_GATEWAY_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    gateway_url = os.getenv("VOIP_PSTN_GATEWAY_URL", "").strip()
    sip_trunk_uri = os.getenv("SIP_TRUNK_URI", "").strip()
    twilio_ready = all(
        os.getenv(name, "").strip()
        for name in (
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_FROM_NUMBER",
        )
    )
    return bool(enabled and (gateway_url or sip_trunk_uri or twilio_ready))


def _build_tel_url(phone: str) -> str:
    sanitized = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    return f"tel:{sanitized}"


def _serialize_voip_payload(payload: Dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


async def _send_incoming_call_invite(
    callee_voice_id: str, payload: dict
) -> bool:
    websocket = online_voice_clients.get(callee_voice_id)
    if websocket is None:
        logger.info(
            (
                "[VoIP] Incoming invite skipped; callee offline | "
                "voice_id=%s | call_id=%s | payload=%s"
            ),
            callee_voice_id,
            payload.get("call_id"),
            _serialize_voip_payload(payload),
        )
        return False
    try:
        logger.info(
            (
                "[VoIP] Publishing incoming invite | voice_id=%s | "
                "call_id=%s | payload=%s"
            ),
            callee_voice_id,
            payload.get("call_id"),
            _serialize_voip_payload(payload),
        )
        await websocket.send_json(payload)
        return True
    except Exception as exc:
        logger.warning(
            (
                "[VoIP] Failed to send incoming invite | voice_id=%s | "
                "call_id=%s | payload=%s | error=%s"
            ),
            callee_voice_id,
            payload.get("call_id"),
            _serialize_voip_payload(payload),
            exc,
        )
        online_voice_clients.pop(callee_voice_id, None)
        return False


async def _send_incoming_call_push_invite(
    callee_voice_id: str, payload: dict
) -> bool:
    server_key = os.getenv("FCM_SERVER_KEY", "").strip()
    service_account_info = _load_fcm_service_account_info()
    topic = _build_voip_topic(callee_voice_id)
    project_id = (
        os.getenv("FCM_PROJECT_ID", "").strip()
        or str((service_account_info or {}).get("project_id") or "").strip()
    )
    if not topic:
        return False

    caller_label = (
        payload.get("caller_label")
        or payload.get("display_label")
        or payload.get("caller_voice_id")
        or "월드링코 보이스톡"
    )
    legacy_payload = {
        "to": f"/topics/{topic}",
        "priority": "high",
        "data": {
            key: _stringify_push_value(value)
            for key, value in payload.items()
            if value is not None
        },
        "notification": {
            "title": "(월드링코)WorldLingo 보이스톡",
            "body": f"{caller_label} 님이 보이스톡을 걸고 있습니다.",
        },
    }
    v1_payload = {
        "message": {
            "topic": topic,
            "data": legacy_payload["data"],
            "notification": legacy_payload["notification"],
            "android": {"priority": "HIGH"},
        }
    }

    try:
        if server_key:
            status_code, response_body = await asyncio.to_thread(
                _post_fcm_legacy,
                server_key,
                legacy_payload,
            )
            success = 200 <= status_code < 300 and (
                '"message_id"' in response_body
                or '"success":1' in response_body
                or '"success": 1' in response_body
            )
        elif service_account_info and project_id:
            status_code, response_body = await asyncio.to_thread(
                _post_fcm_v1,
                service_account_info,
                project_id,
                v1_payload,
            )
            success = 200 <= status_code < 300 and '"name"' in response_body
        else:
            return False
        if not success:
            logger.warning(
                (
                    "[VoIP] FCM push invite failed | voice_id=%s | "
                    "status=%s | body=%s"
                ),
                callee_voice_id,
                status_code,
                response_body,
            )
        return success
    except urllib.error.URLError as exc:
        logger.warning(
            "[VoIP] FCM push invite network error | voice_id=%s | error=%s",
            callee_voice_id,
            exc,
        )
        return False
    except Exception as exc:
        logger.warning(
            "[VoIP] FCM push invite unexpected error | voice_id=%s | error=%s",
            callee_voice_id,
            exc,
        )
        return False


def _build_pending_incoming_call_response(
    call_state: CallState,
) -> Optional[PendingIncomingCallResponse]:
    if not call_state.incoming_payload:
        return None
    payload = dict(call_state.incoming_payload)
    payload["status"] = call_state.status
    payload.setdefault("call_id", call_state.call_id)
    payload.setdefault("session_id", call_state.session_id)
    payload.setdefault("caller_voice_id", call_state.caller_voice_id)
    payload.setdefault("callee_voice_id", call_state.callee_voice_id)
    payload.setdefault("callee_user_id", call_state.callee_user_id)
    return PendingIncomingCallResponse(**payload)


def _build_active_call_response(
    db: Session,
    call_state: CallState,
    *,
    current_user_id: int,
    request: Optional[Request] = None,
) -> Optional[CallInitiateResponse]:
    if call_state.call_route != "app_webrtc":
        return None

    if current_user_id == (call_state.caller_user_id or 0):
        participant_role = "caller"
        counterpart_user_id = call_state.callee_user_id
    elif current_user_id == (call_state.callee_user_id or 0):
        participant_role = "callee"
        counterpart_user_id = call_state.caller_user_id
    else:
        return None

    counterpart = None
    if counterpart_user_id is not None:
        counterpart = (
            db.query(models.User)
            .filter(models.User.id == counterpart_user_id)
            .first()
        )

    incoming_payload = call_state.incoming_payload or {}
    counterpart_label = (
        getattr(counterpart, "username", None)
        or getattr(counterpart, "email", None)
        or incoming_payload.get("caller_label")
        or call_state.caller_id
    )
    counterpart_language = (
        getattr(counterpart, "preferred_language", None)
        or incoming_payload.get("display_language")
    )
    counterpart_country_code = (
        getattr(counterpart, "country_code", None)
        or incoming_payload.get("display_country_code")
    )
    signaling_server = (
        _with_signal_role(
            _build_signaling_server_url(request, call_state.call_id),
            participant_role,
        )
        if request is not None
        else f"/api/v1/voip/signal?call_id={call_state.call_id}&role={participant_role}"
    )

    return CallInitiateResponse(
        call_id=call_state.call_id,
        signaling_server=signaling_server,
        turn_servers=_default_turn_servers(),
        session_id=call_state.session_id,
        call_route=call_state.call_route,
        pstn_gateway_configured=False,
        phone_dialer_required=False,
        callee_app_online=call_state.status != "callee_offline",
        caller_voice_id=call_state.caller_voice_id,
        callee_voice_id=call_state.callee_voice_id,
        callee_user_id=call_state.callee_user_id,
        participant_role=participant_role,
        display_label=counterpart_label,
        display_language=counterpart_language,
        display_country_code=counterpart_country_code,
        status=call_state.status,
        requested_mode=call_state.requested_mode,
        resolved_mode=call_state.resolved_mode,
        auto_relay_requested=call_state.auto_relay_requested,
        auto_relay_applied=call_state.auto_relay_applied,
        error_code=call_state.error_code,
        user_message=_append_mode_message(
            "진행 중인 VoIP 통화를 다시 연결합니다.",
            resolved_mode=call_state.resolved_mode,
            auto_relay_applied=call_state.auto_relay_applied,
            error_code=call_state.error_code,
        ),
    )


# ============================================================================
# REST Endpoints
# ============================================================================

@router.get("/identity")
async def get_voip_identity(current_user=Depends(get_current_user)) -> dict:
    """Return the app-scoped voice ID used for friend-to-friend voice calls."""
    return {
        "user_id": int(current_user.id),
        "voice_id": _build_voice_id(current_user),
        "username": getattr(current_user, "username", None),
        "email": getattr(current_user, "email", None),
    }


@router.post("/calls/initiate", response_model=CallInitiateResponse)
async def initiate_voip_call(
    http_request: Request,
    request: CallInitiateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CallInitiateResponse:
    """
    Initiate a VoIP call to a reservation center.

    - Validates callee phone number format
    - Creates call session in backend
    - Returns signaling server URL + TURN servers
    - Triggers PSTN gateway outbound SIP INVITE (async)

    Args:
        request: Call initiation details
        user_id: Current user ID (from auth)
        db: Database session

    Returns:
        Call details with signaling server and TURN servers

    Raises:
        HTTPException: 400 if phone format invalid, 500 if PSTN gateway fails
    """

    started_at = time.perf_counter()
    app_callee = _resolve_app_callee(db, current_user, request)
    caller_voice_id = _build_voice_id(current_user)
    callee_voice_id = (
        _build_voice_id(app_callee) if app_callee is not None else None
    )
    requested_app_call = bool(
        request.friend_id is not None
        or request.callee_user_id is not None
        or request.callee_voice_id
    )
    if (
        requested_app_call
        and app_callee is not None
        and int(app_callee.id) == int(current_user.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="본인 계정으로는 VoIP 통화를 걸 수 없습니다",
        )
    callee_app_online = bool(
        callee_voice_id and callee_voice_id in online_voice_clients
    )
    requested_mode = _normalize_call_mode(
        request.mode,
        has_app_target=requested_app_call,
    )
    resolved_mode = requested_mode
    auto_relay_requested = bool(request.auto_relay)
    auto_relay_applied = False
    error_code: Optional[str] = None

    if requested_mode == "pstn_assist":
        if request.callee_phone:
            requested_app_call = False
        elif requested_app_call:
            resolved_mode = "voip_full_auto"
            error_code = "PSTN_ASSIST_REQUIRES_PHONE_TARGET"
    elif not requested_app_call:
        resolved_mode = "pstn_assist"
        error_code = "VOIP_MODE_FALLBACK_TO_PSTN_ASSIST"

    auto_relay_applied = (
        auto_relay_requested
        and resolved_mode == "voip_full_auto"
        and requested_app_call
    )

    # Validate phone number format only for phone/PSTN fallback calls.
    if not requested_app_call and not request.callee_phone:
        raise HTTPException(
            status_code=400,
            detail="전화번호 또는 앱 친구/보이스 ID 대상이 필요합니다",
        )

    if request.callee_phone and not request.callee_phone.startswith("+"):
        raise HTTPException(
            status_code=400,
            detail="Phone number must be in E.164 format (+country-number)"
        )

    if requested_app_call and app_callee is None:
        if request.callee_phone:
            requested_app_call = False
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="앱 보이스톡 대상 사용자를 찾을 수 없습니다. 친구 이메일이 앱 가입 계정인지 확인해주세요.",
            )

    # Create unique call ID
    call_id = f"call-{uuid.uuid4().hex[:12]}"

    # Create call state
    call_state = CallState(
        call_id=call_id,
        callee_phone=request.callee_phone,
        caller_id=request.caller_id,
        session_id=request.session_id,
        caller_user_id=int(current_user.id),
        callee_user_id=int(app_callee.id) if app_callee is not None else None,
        caller_voice_id=caller_voice_id,
        callee_voice_id=callee_voice_id,
        call_route=(
            "app_webrtc" if requested_app_call else "native_phone_dialer"
        ),
        requested_mode=requested_mode,
        resolved_mode=resolved_mode,
        auto_relay_requested=auto_relay_requested,
        auto_relay_applied=auto_relay_applied,
        error_code=error_code,
    )
    call_states[call_id] = call_state

    logger.info(
        "[VoIP] Call initiated | call_id=%s | callee=%s | caller=%s",
        call_id,
        request.callee_phone or callee_voice_id,
        current_user.id,
    )

    signaling_server = _build_signaling_server_url(http_request, call_id)

    if requested_app_call:
        assert app_callee is not None
        incoming_payload = {
            "type": "incoming_call",
            "call_id": call_id,
            "caller_user_id": int(current_user.id),
            "caller_voice_id": caller_voice_id,
            "caller_label": (
                getattr(current_user, "username", None)
                or getattr(current_user, "email", "caller")
            ),
            "display_language": getattr(
                current_user, "preferred_language", None
            ),
            "display_country_code": getattr(
                current_user, "country_code", None
            ),
            "callee_user_id": int(app_callee.id),
            "callee_voice_id": callee_voice_id,
            "participant_role": "callee",
            "display_label": (
                getattr(current_user, "username", None)
                or getattr(current_user, "email", "caller")
            ),
            "signaling_server": _with_signal_role(signaling_server, "callee"),
            "turn_servers": [
                {"urls": ["stun:stun.l.google.com:19302"]},
                {"urls": ["stun:stun1.l.google.com:19302"]},
                {"urls": ["stun:stun.cloudflare.com:3478"]},
            ],
            "call_route": "app_webrtc",
            "requested_mode": requested_mode,
            "resolved_mode": resolved_mode,
            "auto_relay_requested": auto_relay_requested,
            "auto_relay_applied": auto_relay_applied,
            "callee_app_online": callee_app_online,
            "status": "ringing",
            "user_message": "상대 단말에 수신 알림을 보냈습니다. 앱이 열리면 자동으로 통화 화면으로 진입합니다.",
            "session_id": request.session_id,
        }

        logger.info(
            (
                "[VoIP] Incoming invite prepared | call_id=%s | "
                "callee_voice_id=%s | payload=%s"
            ),
            call_id,
            callee_voice_id,
            _serialize_voip_payload(incoming_payload),
        )

        call_state.set_status("ringing")
        call_state.incoming_payload = dict(incoming_payload)
        invite_sent = False
        if callee_app_online:
            invite_sent = await _send_incoming_call_invite(
                callee_voice_id or "",
                incoming_payload,
            )
        push_sent = await _send_incoming_call_push_invite(
            callee_voice_id or "",
            incoming_payload,
        )
        if not invite_sent and not push_sent:
            call_state.set_status("callee_offline")
            callee_app_online = False

        _record_call_mode_audit(
            db,
            call_id=call_id,
            session_id=request.session_id,
            event_type="call_initiated",
            requested_mode=requested_mode,
            resolved_mode=resolved_mode,
            auto_relay_requested=auto_relay_requested,
            auto_relay_applied=auto_relay_applied,
            call_route="app_webrtc",
            caller_user_id=int(current_user.id),
            callee_user_id=int(app_callee.id),
            callee_phone=request.callee_phone,
            status=call_state.status,
            error_code=error_code,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            metadata={
                "requested_app_call": True,
                "callee_app_online": callee_app_online,
                "invite_sent": invite_sent,
                "push_sent": push_sent,
            },
        )

        response_payload = CallInitiateResponse(
            call_id=call_id,
            signaling_server=_with_signal_role(signaling_server, "caller"),
            turn_servers=[
                TURNServer(urls=["stun:stun.l.google.com:19302"]),
                TURNServer(urls=["stun:stun1.l.google.com:19302"]),
                TURNServer(urls=["stun:stun.cloudflare.com:3478"]),
            ],
            call_route="app_webrtc",
            pstn_gateway_configured=False,
            phone_dialer_required=False,
            callee_app_online=callee_app_online,
            caller_voice_id=caller_voice_id,
            callee_voice_id=callee_voice_id,
            callee_user_id=int(app_callee.id),
            participant_role="caller",
            display_label=(
                getattr(app_callee, "username", None)
                or getattr(app_callee, "email", None)
            ),
            display_language=getattr(app_callee, "preferred_language", None),
            display_country_code=getattr(app_callee, "country_code", None),
            status=call_state.status,
            user_message=_append_mode_message(
                (
                    "친구 앱으로 보이스톡 초대와 푸시 수신 알림을 보냈습니다."
                    if invite_sent and push_sent
                    else "친구 앱으로 보이스톡 초대를 보냈습니다."
                    if invite_sent
                    else (
                        "상대 단말에 수신 알림을 보냈습니다. 앱이 열리면 "
                        "자동으로 통화 화면으로 진입합니다."
                    )
                    if push_sent
                    else (
                        "상대 앱이 현재 보이스톡 수신 대기 상태가 아닙니다. "
                        "상대가 앱에 로그인해 있어야 보이스톡이 연결됩니다."
                    )
                ),
                resolved_mode=resolved_mode,
                auto_relay_applied=auto_relay_applied,
                error_code=error_code,
            ),
            requested_mode=requested_mode,
            resolved_mode=resolved_mode,
            auto_relay_requested=auto_relay_requested,
            auto_relay_applied=auto_relay_applied,
            error_code=error_code,
        )

        logger.info(
            "[VoIP] Call initiate response | call_id=%s | payload=%s",
            call_id,
            response_payload.model_dump_json(exclude_none=False),
        )

        return response_payload

    pstn_gateway_configured = _is_pstn_gateway_configured()
    phone_dialer_required = not pstn_gateway_configured
    if phone_dialer_required:
        call_state.status = "dialer_required"
        logger.warning(
            (
                "[VoIP] PSTN gateway is not configured; returning "
                "native dialer fallback | call_id=%s | callee=%s"
            ),
            call_id,
            request.callee_phone,
        )
    else:
        # TODO: Trigger async PSTN gateway SIP INVITE to callee_phone
        # Example: await pstn_gateway.invite(call_id, request.callee_phone)
        call_state.status = "routing_pending"

    _record_call_mode_audit(
        db,
        call_id=call_id,
        session_id=request.session_id,
        event_type="call_initiated",
        requested_mode=requested_mode,
        resolved_mode=resolved_mode,
        auto_relay_requested=auto_relay_requested,
        auto_relay_applied=auto_relay_applied,
        call_route=(
            "native_phone_dialer"
            if phone_dialer_required
            else "pstn_gateway"
        ),
        caller_user_id=int(current_user.id),
        callee_user_id=int(app_callee.id) if app_callee is not None else None,
        callee_phone=request.callee_phone,
        status=call_state.status,
        error_code=error_code,
        latency_ms=int((time.perf_counter() - started_at) * 1000),
        metadata={
            "requested_app_call": requested_app_call,
            "pstn_gateway_configured": pstn_gateway_configured,
        },
    )

    return CallInitiateResponse(
        call_id=call_id,
        signaling_server=_with_signal_role(signaling_server, "caller"),
        turn_servers=[
            TURNServer(urls=["stun:stun.l.google.com:19302"]),
            TURNServer(urls=["stun:stun1.l.google.com:19302"]),
            TURNServer(urls=["stun:stun.cloudflare.com:3478"]),
        ],
        call_route=(
            "native_phone_dialer"
            if phone_dialer_required
            else "pstn_gateway"
        ),
        pstn_gateway_configured=pstn_gateway_configured,
        phone_dialer_required=phone_dialer_required,
        callee_app_online=False,
        caller_voice_id=caller_voice_id,
        participant_role="caller",
        display_label=request.callee_phone,
        status=call_state.status,
        user_message=_append_mode_message((
            "전화번호만 있는 상대는 현재 앱 내부 WebRTC로 직접 울릴 수 없어 시스템 전화앱으로 연결해야 합니다."
            if phone_dialer_required
            else "PSTN 게이트웨이 라우팅 대기 중입니다."
        ),
            resolved_mode=resolved_mode,
            auto_relay_applied=auto_relay_applied,
            error_code=error_code,
        ),
        fallback_dial_url=(
            _build_tel_url(request.callee_phone or "")
            if phone_dialer_required
            else None
        ),
        requested_mode=requested_mode,
        resolved_mode=resolved_mode,
        auto_relay_requested=auto_relay_requested,
        auto_relay_applied=auto_relay_applied,
        error_code=error_code,
    )


@router.get(
    "/calls/pending-incoming",
    response_model=Optional[PendingIncomingCallResponse],
)
async def get_pending_incoming_voip_call(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[PendingIncomingCallResponse]:
    pending_statuses = {"ringing", "callee_offline"}
    matching_calls = [
        call_state
        for call_state in call_states.values()
        if call_state.callee_user_id == int(current_user.id)
        and call_state.call_route == "app_webrtc"
        and call_state.status in pending_statuses
    ]
    if not matching_calls:
        return None

    matching_calls.sort(key=lambda item: item.created_at, reverse=True)
    pending_call = matching_calls[0]
    if _maybe_prune_stale_resumable_call(pending_call, db):
        return None
    logger.info(
        "[VoIP] Pending incoming call fetched | user_id=%s | call_id=%s | status=%s",
        current_user.id,
        pending_call.call_id,
        pending_call.status,
    )
    return _build_pending_incoming_call_response(pending_call)


@router.post("/calls/{call_id}/accept", response_model=CallInitiateResponse)
async def accept_voip_call(
    call_id: str,
    http_request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CallInitiateResponse:
    """Callee joins a ringing app-to-app call and receives signaling URL (role=callee)."""
    if call_id not in call_states:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="합류 가능한 통화를 찾을 수 없습니다.",
        )

    call_state = call_states[call_id]
    if call_state.call_route != "app_webrtc":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="앱 보이스톡 통화가 아닙니다.",
        )
    if int(current_user.id) != int(call_state.callee_user_id or 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 통화의 착신 당사자가 아닙니다.",
        )
    if call_state.status not in {"ringing", "callee_offline", "initiated", "connecting"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"현재 상태에서는 수락할 수 없습니다: {call_state.status}",
        )

    call_state.set_status("connecting")
    response = _build_active_call_response(
        db,
        call_state,
        current_user_id=int(current_user.id),
        request=http_request,
    )
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="합류 가능한 통화를 찾을 수 없습니다.",
        )

    _record_call_mode_audit(
        db,
        call_id=call_id,
        session_id=call_state.session_id,
        event_type="call_accepted",
        requested_mode=call_state.requested_mode,
        resolved_mode=call_state.resolved_mode,
        auto_relay_requested=call_state.auto_relay_requested,
        auto_relay_applied=call_state.auto_relay_applied,
        call_route=call_state.call_route,
        caller_user_id=call_state.caller_user_id,
        callee_user_id=call_state.callee_user_id,
        callee_phone=call_state.callee_phone,
        status=call_state.status,
        error_code=call_state.error_code,
        metadata={"accepted_by_user_id": int(current_user.id)},
    )

    logger.info(
        "[VoIP] Call accepted | call_id=%s | callee_user_id=%s",
        call_id,
        current_user.id,
    )
    return response


@router.get(
    "/calls/active-current",
    response_model=Optional[CallInitiateResponse],
)
async def get_active_current_voip_call(
    http_request: Request,
    last_call_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[CallInitiateResponse]:
    resumable_statuses = {"initiated", "ringing", "callee_offline", "connecting", "active"}
    matching_calls = [
        call_state
        for call_state in call_states.values()
        if call_state.call_route == "app_webrtc"
        and call_state.status in resumable_statuses
        and int(current_user.id) in {
            int(call_state.caller_user_id or 0),
            int(call_state.callee_user_id or 0),
        }
    ]
    if not matching_calls:
        return None

    if last_call_id:
        matching_calls = [
            call_state for call_state in matching_calls if call_state.call_id == last_call_id
        ]
        if not matching_calls:
            return None

    matching_calls.sort(key=lambda item: item.created_at, reverse=True)
    active_call = matching_calls[0]
    if _maybe_prune_stale_resumable_call(active_call, db):
        return None
    logger.info(
        "[VoIP] Active current call fetched | user_id=%s | call_id=%s | status=%s",
        current_user.id,
        active_call.call_id,
        active_call.status,
    )
    return _build_active_call_response(
        db,
        active_call,
        current_user_id=int(current_user.id),
        request=http_request,
    )


@router.post("/calls/{call_id}/end")
async def end_voip_call(
    call_id: str,
    request: CallEndRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    End a VoIP call and log metadata.

    Args:
        call_id: Call ID to end
        request: Duration and quality info
        user_id: Current user ID
        db: Database session

    Returns:
        Confirmation with call summary
    """

    if call_id not in call_states:
        raise HTTPException(
            status_code=404,
            detail=f"Call {call_id} not found",
        )

    call_state = call_states[call_id]
    previous_status = call_state.status
    call_state.set_status("ended")
    call_state.duration_sec = request.duration_sec
    _cleanup_call_runtime_state(call_id)

    logger.info(
        f"[VoIP] Call ended | call_id={call_id} | "
        f"duration={request.duration_sec}s | quality={request.call_quality}"
    )

    _record_call_mode_audit(
        db,
        call_id=call_id,
        session_id=call_state.session_id,
        event_type="call_ended",
        requested_mode=call_state.requested_mode,
        resolved_mode=call_state.resolved_mode,
        auto_relay_requested=call_state.auto_relay_requested,
        auto_relay_applied=call_state.auto_relay_applied,
        call_route=call_state.call_route,
        caller_user_id=call_state.caller_user_id,
        callee_user_id=call_state.callee_user_id,
        callee_phone=call_state.callee_phone,
        status=call_state.status,
        error_code=call_state.error_code,
        duration_sec=request.duration_sec,
        call_quality=request.call_quality,
        metadata={"ended_by_user_id": int(current_user.id)},
    )

    if (
        call_state.call_route == "app_webrtc"
        and call_state.callee_user_id is not None
        and request.duration_sec == 0
        and previous_status in {"ringing", "connecting", "callee_offline"}
    ):
        _record_call_mode_audit(
            db,
            call_id=call_id,
            session_id=call_state.session_id,
            event_type="call_missed",
            requested_mode=call_state.requested_mode,
            resolved_mode=call_state.resolved_mode,
            auto_relay_requested=call_state.auto_relay_requested,
            auto_relay_applied=call_state.auto_relay_applied,
            call_route=call_state.call_route,
            caller_user_id=call_state.caller_user_id,
            callee_user_id=call_state.callee_user_id,
            callee_phone=call_state.callee_phone,
            status="missed",
            error_code=call_state.error_code,
            duration_sec=0,
            metadata={
                "previous_status": previous_status,
                "ended_by_user_id": int(current_user.id),
                "caller_voice_id": call_state.caller_voice_id,
            },
        )

    # TODO: Store call log in database
    # await db.add(CallLog(...))

    # TODO: Trigger async PSTN gateway SIP BYE
    # Example: await pstn_gateway.hangup(call_id)

    return {
        "status": "ok",
        "call_id": call_id,
        "duration_sec": request.duration_sec,
    }


@router.get(
    "/calls/{call_id}/audit",
    response_model=List[CallModeAuditEventRead],
)
async def get_call_mode_audit(
    call_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[CallModeAuditEventRead]:
    events = list_call_mode_events(db, call_id=call_id)
    if not events:
        return []

    if not _user_can_read_call_mode_audit(
        current_user,
        call_id=call_id,
        events=events,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 통화 감사 로그를 조회할 권한이 없습니다.",
        )

    return events


@router.get("/calls/missed/recent")
async def get_recent_missed_calls(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = (
        db.query(models.CallModeAuditLog)
        .filter(models.CallModeAuditLog.event_type == "call_missed")
        .filter(models.CallModeAuditLog.callee_user_id == int(current_user.id))
        .order_by(
            models.CallModeAuditLog.created_at.desc(),
            models.CallModeAuditLog.id.desc(),
        )
        .limit(20)
        .all()
    )

    payload: list[dict[str, Any]] = []
    for row in rows:
        metadata = _deserialize_metadata(row.metadata_json)
        caller = None
        if row.caller_user_id is not None:
            caller = (
                db.query(models.User)
                .filter(models.User.id == row.caller_user_id)
                .first()
            )
        payload.append(
            {
                "id": int(row.id),
                "callId": row.call_id,
                "createdAt": (
                    row.created_at.isoformat() if row.created_at else ""
                ),
                "callerUserId": row.caller_user_id,
                "callerVoiceId": (
                    _build_voice_id(caller)
                    if getattr(caller, "id", None)
                    else metadata.get("caller_voice_id")
                ),
                "callerLabel": (
                    getattr(caller, "username", None)
                    or getattr(caller, "email", None)
                    or "알 수 없는 발신자"
                ),
                "callerPreferredLanguage": getattr(
                    caller, "preferred_language", None
                ),
                "callerCountryCode": getattr(caller, "country_code", None),
                "status": row.status or "missed",
            }
        )
    return payload


# ============================================================================
# WebSocket Signaling Relay
# ============================================================================

@router.websocket("/presence")
async def websocket_presence(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db),
):
    """Keep a logged-in user available for incoming app-to-app voice calls."""
    user = _resolve_authenticated_user_from_token(db, token)
    if user is None or not getattr(user, "is_active", False):
        await websocket.close(code=4401)
        return

    voice_id = _build_voice_id(user)
    await websocket.accept()
    online_voice_clients[voice_id] = websocket
    logger.info(
        "[VoIP] Presence connected | voice_id=%s | user_id=%s",
        voice_id,
        user.id,
    )
    try:
        await websocket.send_json(
            {
                "type": "presence_ready",
                "voice_id": voice_id,
                "user_id": int(user.id),
            }
        )
        while True:
            raw_message = await websocket.receive_text()
            message = json.loads(raw_message)
            if message.get("type") == "ping":
                await websocket.send_json(
                    {"type": "pong", "voice_id": voice_id}
                )
    except WebSocketDisconnect:
        logger.info("[VoIP] Presence disconnected | voice_id=%s", voice_id)
    except Exception as exc:
        logger.warning(
            "[VoIP] Presence error | voice_id=%s | error=%s",
            voice_id,
            exc,
        )
    finally:
        if online_voice_clients.get(voice_id) is websocket:
            online_voice_clients.pop(voice_id, None)


async def _relay_app_signal(
    call_id: str, sender_role: str, message: dict
) -> None:
    target_role = "callee" if sender_role == "caller" else "caller"
    message["from_role"] = sender_role
    message["call_id"] = call_id
    message_type = str(message.get("type") or "unknown")
    has_sdp = bool(message.get("sdp"))
    has_candidate = bool(message.get("candidate"))
    target_socket = call_participants.get(call_id, {}).get(target_role)
    if target_socket is not None:
        await target_socket.send_json(message)
        logger.info(
            (
                "[VoIP] Signal relayed | call_id=%s | type=%s | "
                "from=%s | to=%s | delivered=true | has_sdp=%s | "
                "has_candidate=%s"
            ),
            call_id,
            message_type,
            sender_role,
            target_role,
            has_sdp,
            has_candidate,
        )
        return
    queue = pending_signal_messages.setdefault(call_id, {}).setdefault(
        target_role, []
    )
    queue.append(message)
    logger.warning(
        (
            "[VoIP] Signal queued (target disconnected) | call_id=%s | "
            "type=%s | from=%s | to=%s | queue_len=%s | has_sdp=%s | "
            "has_candidate=%s"
        ),
        call_id,
        message_type,
        sender_role,
        target_role,
        len(queue),
        has_sdp,
        has_candidate,
    )
    _maybe_log_signal_queue_threshold(
        call_id,
        target_role,
        len(queue),
        message_type,
        sender_role,
    )


async def _send_app_signal_to_role(
    call_id: str,
    target_role: str,
    message: dict,
    *,
    queue_if_missing: bool = False,
) -> bool:
    outbound = dict(message)
    outbound["call_id"] = call_id
    message_type = str(outbound.get("type") or "unknown")
    has_sdp = bool(outbound.get("sdp"))
    has_candidate = bool(outbound.get("candidate"))
    target_socket = call_participants.get(call_id, {}).get(target_role)
    if target_socket is not None:
        await target_socket.send_json(outbound)
        logger.info(
            (
                "[VoIP] Signal direct-send | call_id=%s | type=%s | "
                "to=%s | delivered=true | has_sdp=%s | has_candidate=%s"
            ),
            call_id,
            message_type,
            target_role,
            has_sdp,
            has_candidate,
        )
        return True
    if queue_if_missing:
        queue = pending_signal_messages.setdefault(call_id, {}).setdefault(
            target_role, []
        )
        queue.append(outbound)
        logger.warning(
            (
                "[VoIP] Signal direct-send queued | call_id=%s | type=%s "
                "| to=%s | queue_len=%s | has_sdp=%s | has_candidate=%s"
            ),
            call_id,
            message_type,
            target_role,
            len(queue),
            has_sdp,
            has_candidate,
        )
        _maybe_log_signal_queue_threshold(
            call_id,
            target_role,
            len(queue),
            message_type,
            "system",
        )
    else:
        logger.warning(
            (
                "[VoIP] Signal direct-send dropped (target disconnected) "
                "| call_id=%s | type=%s | to=%s | has_sdp=%s | "
                "has_candidate=%s"
            ),
            call_id,
            message_type,
            target_role,
            has_sdp,
            has_candidate,
        )
    return False


def _get_or_create_voip_direct_room(
    db: Session,
    *,
    caller_user_id: int,
    callee_user_id: int,
) -> Optional[models.ChatRoom]:
    room = _find_direct_chat_room(db, caller_user_id, callee_user_id)
    if room is not None:
        return room

    caller_user = (
        db.query(models.User)
        .filter(models.User.id == caller_user_id)
        .first()
    )
    callee_user = (
        db.query(models.User)
        .filter(models.User.id == callee_user_id)
        .first()
    )
    if caller_user is None or callee_user is None:
        return None

    now = datetime.utcnow()
    room = models.ChatRoom(
        room_uuid=str(uuid.uuid4()),
        room_type="direct",
        owner_user_id=caller_user_id,
        default_source_lang=_normalize_chat_text(
            _resolve_user_language(caller_user),
            max_length=16,
        ),
        default_target_lang=_normalize_chat_text(
            _resolve_user_language(callee_user),
            max_length=16,
        ),
        translation_mode="direct_auto",
        last_message_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(room)
    db.flush()
    db.add_all(
        [
            _create_chat_room_member(room.id, caller_user_id, "owner"),
            _create_chat_room_member(room.id, callee_user_id, "member"),
        ]
    )
    db.flush()
    return room


def _persist_voip_chat_message(
    call_state: "CallState",
    *,
    sender_role: str,
    text: str,
) -> Optional[dict[str, Any]]:
    sender_user_id = (
        call_state.caller_user_id if sender_role == "caller" else call_state.callee_user_id
    )
    recipient_user_id = (
        call_state.callee_user_id if sender_role == "caller" else call_state.caller_user_id
    )
    if sender_user_id is None or recipient_user_id is None:
        return None

    db = SessionLocal()
    try:
        room = _get_or_create_voip_direct_room(
            db,
            caller_user_id=call_state.caller_user_id,
            callee_user_id=call_state.callee_user_id,
        )
        if room is None:
            return None

        message = _append_chat_message(
            db,
            room=room,
            sender_user_id=sender_user_id,
            message_type="text",
            body=text,
            translated_body=None,
            source_lang=None,
            target_lang=None,
            request_translation=True,
            reply_to_message_id=None,
            translation_engine="voip-signal",
        )
        db.commit()
        db.refresh(room)
        db.refresh(message)
        recipient_message = _serialize_chat_message(
            db,
            room,
            message,
            recipient_user_id,
        )
        sender_message = _serialize_chat_message(
            db,
            room,
            message,
            sender_user_id,
        )
        return {
            "room_id": room.room_uuid,
            "message_id": message.message_uuid,
            "sender_message": sender_message,
            "recipient_message": recipient_message,
        }
    except Exception as exc:
        logger.warning(
            "[VoIP] Chat persistence/translation failed | call_id=%s | sender_role=%s | error=%s",
            call_state.call_id,
            sender_role,
            exc,
        )
        db.rollback()
        return None
    finally:
        db.close()


async def _flush_pending_signals(
    call_id: str, role: str, websocket: WebSocket
) -> None:
    queued = pending_signal_messages.get(call_id, {}).pop(role, [])
    call_alert_state = signal_queue_alert_last_len.get(call_id)
    if call_alert_state is not None:
        call_alert_state.pop(role, None)
        if not call_alert_state:
            signal_queue_alert_last_len.pop(call_id, None)
    if queued:
        logger.info(
            "[VoIP] Pending signal flush | call_id=%s | role=%s | count=%s",
            call_id,
            role,
            len(queued),
        )
    for message in queued:
        await websocket.send_json(message)


def _build_voice_translation_relay_payload(message: Dict[str, Any]) -> Dict[str, Any]:
    transcript = _collapse_voice_relay_text(str(message.get("transcript") or "").strip())
    translated_text = _collapse_voice_relay_text(str(message.get("translated_text") or "").strip())
    source_lang = str(message.get("source_lang") or "").strip()[:32]
    target_lang = str(message.get("target_lang") or "").strip()[:32]
    if _should_reject_voice_translation_relay(
        source_lang=source_lang,
        target_lang=target_lang,
        transcript=transcript,
        translated_text=translated_text,
    ):
        return {}
    payload: Dict[str, Any] = {
        "type": "voice_translation",
        "transcript": transcript[:280],
        "translated_text": translated_text[:280],
        "source_lang": source_lang,
        "target_lang": target_lang,
        "audio_url": (
            str(message.get("audio_url") or "").strip()[:2048] or None
        ),
        "audio_base64": (
            str(message.get("audio_base64") or "").strip()[:2_000_000] or None
        ),
        "audio_format": (
            str(message.get("audio_format") or "").strip()[:128] or None
        ),
        "sent_at": message.get("sent_at") or datetime.utcnow().isoformat(),
    }
    seq_id = message.get("seq_id")
    if isinstance(seq_id, (int, float)) and not isinstance(seq_id, bool):
        payload["seq_id"] = int(seq_id)
    utterance_id = str(message.get("utterance_id") or "").strip()
    if utterance_id:
        payload["utterance_id"] = utterance_id[:128]
    chunk_index = message.get("chunk_index")
    if isinstance(chunk_index, (int, float)) and not isinstance(chunk_index, bool):
        payload["chunk_index"] = max(0, int(chunk_index))
    if isinstance(message.get("is_final"), bool):
        payload["is_final"] = message["is_final"]
    detected_lang = str(message.get("detected_lang") or "").strip()
    if detected_lang:
        payload["detected_lang"] = detected_lang[:32]
    return payload


@router.websocket("/signal")
async def websocket_signaling(
    websocket: WebSocket,
    call_id: str,
    role: str = "caller",
    token: Optional[str] = None,
):
    """
    WebSocket endpoint for SDP offer/answer and ICE candidate relay.

    Messages:
    - {"type": "offer", "call_id": "...", "sdp": "..."}
    - {"type": "answer", "call_id": "...", "sdp": "..."}
    - {"type": "candidate", "call_id": "...", "candidate": "...", ...}
     - {"type": "chat_message", "call_id": "...", "text": "...",
         "sent_at": "..."}
     - {"type": "voice_translation", "call_id": "...",
         "transcript": "...", "translated_text": "...",
         "source_lang": "ko", "target_lang": "en",
         "audio_url": "...", "sent_at": "..."}
    - {"type": "hangup", "call_id": "..."}

    This relay connects:
    1. Mobile app (caller)
    2. Media relay (receiver + PSTN forwarder)
    """

    if call_id not in call_states:
        logger.warning(
            (
                "[VoIP] Call state missing at signaling connect; "
                "creating fallback state | call_id=%s"
            ),
            call_id,
        )
        call_states[call_id] = CallState(
            call_id=call_id,
            callee_phone="unknown",
            caller_id="unknown",
            session_id=None,
        )

    await websocket.accept()
    call_state = call_states[call_id]
    normalized_role = role if role in {"caller", "callee"} else "caller"
    client_host = None
    if websocket.client is not None:
        client_host = f"{websocket.client.host}:{websocket.client.port}"
    logger.info(
        (
            "[VoIP] Signal websocket accepted | call_id=%s | role=%s | "
            "route=%s | client=%s"
        ),
        call_id,
        normalized_role,
        call_state.call_route,
        client_host,
    )

    if call_state.call_route == "app_webrtc":
        call_participants.setdefault(call_id, {})[normalized_role] = websocket
        connected_clients[f"{call_id}:{normalized_role}"] = websocket
        logger.info(
            "[VoIP] App signaling connected | call_id=%s | role=%s",
            call_id,
            normalized_role,
        )
        await _flush_pending_signals(call_id, normalized_role, websocket)
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                message_type = message.get("type")
                if message_type in {"offer", "answer", "candidate"}:
                    logger.info(
                        (
                            "[VoIP] Signal inbound | call_id=%s | role=%s | "
                            "type=%s | has_sdp=%s | has_candidate=%s"
                        ),
                        call_id,
                        normalized_role,
                        message_type,
                        bool(message.get("sdp")),
                        bool(message.get("candidate")),
                    )
                if message_type == "offer":
                    call_state.local_sdp = message.get("sdp")
                    await _relay_app_signal(call_id, normalized_role, message)
                elif message_type == "answer":
                    call_state.remote_sdp = message.get("sdp")
                    call_state.set_status("active")
                    await _relay_app_signal(call_id, normalized_role, message)
                elif message_type == "candidate":
                    await _relay_app_signal(call_id, normalized_role, message)
                elif message_type == "chat_message":
                    text = str(message.get("text") or "").strip()
                    if not text:
                        continue
                    client_sent_at = (
                        message.get("sent_at")
                        or datetime.utcnow().isoformat()
                    )
                    persisted_message = _persist_voip_chat_message(
                        call_state,
                        sender_role=normalized_role,
                        text=text[:280],
                    )
                    relay_payload = {
                        "type": "chat_message",
                        "text": text[:280],
                        "sent_at": client_sent_at,
                        "client_sent_at": client_sent_at,
                    }
                    if persisted_message is not None:
                        recipient_message = persisted_message["recipient_message"]
                        sender_message = persisted_message["sender_message"]
                        relay_payload.update(
                            {
                                "message_id": persisted_message["message_id"],
                                "room_id": persisted_message["room_id"],
                                "translated_text": recipient_message.get("translated_body"),
                                "source_lang": recipient_message.get("body_source_lang"),
                                "target_lang": recipient_message.get("body_target_lang"),
                                "translation_status": recipient_message.get("translation_status"),
                                "sender_label": recipient_message.get("sender_label"),
                                "sender_voice_id": recipient_message.get("sender_voice_id"),
                                "sent_at": recipient_message.get("created_at")
                                or relay_payload["sent_at"],
                            }
                        )
                    await _relay_app_signal(
                        call_id,
                        normalized_role,
                        relay_payload,
                    )
                    if persisted_message is not None:
                        await _send_app_signal_to_role(
                            call_id,
                            normalized_role,
                            {
                                "type": "chat_message",
                                "from_role": normalized_role,
                                "text": text[:280],
                                "sent_at": sender_message.get("created_at")
                                or relay_payload["sent_at"],
                                "client_sent_at": client_sent_at,
                                "message_id": persisted_message["message_id"],
                                "room_id": persisted_message["room_id"],
                                "translated_text": sender_message.get("translated_body"),
                                "source_lang": sender_message.get("body_source_lang"),
                                "target_lang": sender_message.get("body_target_lang"),
                                "translation_status": sender_message.get("translation_status"),
                                "sender_label": sender_message.get("sender_label"),
                                "sender_voice_id": sender_message.get("sender_voice_id"),
                            },
                        )
                elif message_type == "voice_translation":
                    relay_payload = _build_voice_translation_relay_payload(message)
                    if (
                        not relay_payload.get("transcript")
                        or not relay_payload.get("translated_text")
                    ):
                        continue
                    await _relay_app_signal(
                        call_id,
                        normalized_role,
                        relay_payload,
                    )
                elif message_type == "hangup":
                    call_state.set_status("ended")
                    _cleanup_call_runtime_state(call_id)
                    await _relay_app_signal(call_id, normalized_role, message)
                    break
                elif message_type == "ping":
                    logger.info(
                        "[VoIP] Signal ping | call_id=%s | role=%s",
                        call_id,
                        normalized_role,
                    )
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "call_id": call_id,
                            "role": normalized_role,
                        }
                    )
                else:
                    logger.warning(
                        (
                            "[VoIP] Unknown app signal | call_id=%s | "
                            "role=%s | type=%s"
                        ),
                        call_id,
                        normalized_role,
                        message_type,
                    )
        except WebSocketDisconnect:
            logger.info(
                "[VoIP] App signaling disconnected | call_id=%s | role=%s",
                call_id,
                normalized_role,
            )
        except Exception as exc:
            logger.error(
                (
                    "[VoIP] App signaling error | call_id=%s | "
                    "role=%s | error=%s"
                ),
                call_id,
                normalized_role,
                exc,
            )
        finally:
            participants = call_participants.get(call_id, {})
            if participants.get(normalized_role) is websocket:
                participants.pop(normalized_role, None)
            connected_clients.pop(f"{call_id}:{normalized_role}", None)
        return

    connected_clients[call_id] = websocket
    logger.info(f"[VoIP] Signaling client connected | call_id={call_id}")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            call_state = call_states[call_id]

            # Route message to media relay (or other participant)
            if message.get("type") == "offer":
                call_state.local_sdp = message.get("sdp")
                logger.info(f"[VoIP] Offer received | call_id={call_id}")

                if RTCPeerConnection is None or RTCSessionDescription is None:
                    logger.error(
                        "[VoIP] aiortc not available | call_id=%s",
                        call_id,
                    )
                    await websocket.send_json(
                        {
                            "type": "error",
                            "call_id": call_id,
                            "reason": "voip_media_unavailable",
                        }
                    )
                    continue

                await _close_webrtc_peer(call_id)

                assert RTCConfiguration is not None
                assert RTCIceServer is not None
                assert RTCPeerConnection is not None

                rtc_config = RTCConfiguration(
                    iceServers=[
                        RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
                        RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
                        RTCIceServer(urls=["stun:stun.cloudflare.com:3478"]),
                    ]
                )
                peer = RTCPeerConnection(configuration=rtc_config)
                current_peer = peer
                webrtc_peers[call_id] = current_peer

                @current_peer.on("connectionstatechange")
                async def on_connectionstatechange():
                    state = current_peer.connectionState
                    logger.info(
                        "[VoIP] Peer state changed | call_id=%s | state=%s",
                        call_id,
                        state,
                    )
                    if state == "connected":
                        call_state.set_status("active")
                    elif state in {"failed", "closed", "disconnected"}:
                        call_state.set_status("ended")

                @current_peer.on("icecandidate")
                async def on_icecandidate(candidate):
                    if candidate is None:
                        return
                    await websocket.send_json(
                        {
                            "type": "candidate",
                            "call_id": call_id,
                            "candidate": candidate.to_sdp(),
                            "sdpMid": candidate.sdpMid,
                            "sdpMLineIndex": candidate.sdpMLineIndex,
                        }
                    )

                current_peer.addTransceiver("audio", direction="recvonly")
                await current_peer.setRemoteDescription(
                    RTCSessionDescription(
                        sdp=message.get("sdp", ""),
                        type="offer",
                    )
                )
                answer = await current_peer.createAnswer()
                await current_peer.setLocalDescription(answer)
                await _wait_for_ice_gathering(current_peer)

                # Send answer back to mobile client
                try:
                    answer_message = {
                        "type": "answer",
                        "call_id": call_id,
                        "sdp": current_peer.localDescription.sdp,
                    }
                    await websocket.send_json(answer_message)
                    logger.info(f"[VoIP] Answer sent | call_id={call_id}")
                except Exception as e:
                    logger.error(
                        "[VoIP] Failed to send answer | call_id=%s | error=%s",
                        call_id,
                        str(e),
                    )

            elif message.get("type") == "answer":
                call_state.remote_sdp = message.get("sdp")
                logger.info(f"[VoIP] Answer received | call_id={call_id}")

                # TODO: Forward answer to mobile app (relay)
                # This would come from media relay back to app

            elif message.get("type") == "candidate":
                logger.debug(
                    "[VoIP] ICE candidate | call_id=%s | %s",
                    call_id,
                    message.get("candidate"),
                )

                peer = webrtc_peers.get(call_id)
                if peer is None or candidate_from_sdp is None:
                    logger.warning(
                        "[VoIP] Candidate received with no peer | call_id=%s",
                        call_id,
                    )
                    continue
                try:
                    raw_candidate = message.get("candidate")
                    if raw_candidate:
                        normalized = raw_candidate
                        if normalized.startswith("candidate:"):
                            normalized = normalized[len("candidate:"):]
                        candidate = candidate_from_sdp(normalized)
                        candidate.sdpMid = message.get("sdpMid")
                        candidate.sdpMLineIndex = message.get("sdpMLineIndex")
                        await peer.addIceCandidate(candidate)
                except Exception as exc:
                    logger.warning(
                        "[VoIP] Candidate add failed | call_id=%s | error=%s",
                        call_id,
                        exc,
                    )

            elif message.get("type") == "hangup":
                call_state.set_status("ended")
                logger.info(f"[VoIP] Hangup received | call_id={call_id}")

                await _close_webrtc_peer(call_id)

                break

    except WebSocketDisconnect:
        logger.info(
            "[VoIP] Signaling client disconnected | call_id=%s",
            call_id,
        )
    except Exception as e:
        logger.error(
            "[VoIP] Signaling error | call_id=%s | error=%s",
            call_id,
            str(e),
        )
    finally:
        if call_id in connected_clients:
            del connected_clients[call_id]
        await _close_webrtc_peer(call_id)
        call_states[call_id].status = "ended"


# ============================================================================
# Health & Debug Endpoints
# ============================================================================

@router.get("/health")
async def voip_health() -> dict:
    """Health check for VoIP service"""
    return {
        "status": "ok",
        "active_calls": len(call_states),
        "connected_clients": len(connected_clients),
        "online_voice_clients": len(online_voice_clients),
        "app_call_participants": sum(
            len(participants) for participants in call_participants.values()
        ),
    }


@router.get("/calls/{call_id}")
async def get_call_details(
    call_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """Get call details (debug endpoint)"""

    if call_id not in call_states:
        raise HTTPException(
            status_code=404,
            detail=f"Call {call_id} not found",
        )

    call_state = call_states[call_id]

    return {
        "call_id": call_id,
        "status": call_state.status,
        "callee_phone": call_state.callee_phone,
        "caller_id": call_state.caller_id,
        "call_route": call_state.call_route,
        "caller_user_id": call_state.caller_user_id,
        "callee_user_id": call_state.callee_user_id,
        "caller_voice_id": call_state.caller_voice_id,
        "callee_voice_id": call_state.callee_voice_id,
        "session_id": call_state.session_id,
        "phone_dialer_required": call_state.status == "dialer_required",
        "created_at": call_state.created_at.isoformat(),
        "duration_sec": call_state.duration_sec,
    }
