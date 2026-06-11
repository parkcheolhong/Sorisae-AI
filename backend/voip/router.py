"""VoIP 통역 통화 API (P1 + P2) — REST initiate/audit/end + WebSocket 시그널링.

설계: NADOTONGRYOKSA_VOIP_BACKEND_DESIGN.md
인증: REST 3종은 Bearer(get_current_user). WebSocket은 query token(initiate가 발급한 단기 JWT).
스토어/릴레이는 환경변수 VOIP_REDIS_URL 유무에 따라 인메모리(P1) 또는 Redis pub/sub(P2)로 동작.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from backend.auth import ALGORITHM, SECRET_KEY, create_access_token, get_current_user

from . import push
from .config import build_signaling_url, get_ice_servers, signaling_token_ttl_sec
from .models import AuditResponse, CallInitiateRequest, CallInitResponse, DeviceRegisterRequest
from .presence import get_presence
from .redis_backend import get_relay, get_store
from .signaling import RELAY_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voip", tags=["voip"])


def _mint_ws_token(*, username: str, user_id: Optional[int], call_id: str, role: str) -> str:
    return create_access_token(
        {"sub": username, "uid": user_id, "voip_call_id": call_id, "voip_role": role},
        expires_delta=timedelta(seconds=signaling_token_ttl_sec()),
    )


@router.post("/devices/register")
async def register_device(payload: DeviceRegisterRequest, user=Depends(get_current_user)) -> Dict[str, Any]:
    """P3-A: 콜리 착신용 FCM 디바이스 토큰 등록 + presence 갱신."""
    user_id = getattr(user, "id", None)
    if user_id is None:
        raise HTTPException(status_code=400, detail="사용자 식별 실패")
    presence = get_presence()
    await presence.register_device(user_id, payload.fcm_token.strip(), payload.platform)
    await presence.mark_online(user_id)
    return {"ok": True, "user_id": user_id}


@router.post("/calls/initiate", response_model=CallInitResponse)
async def initiate_call(payload: CallInitiateRequest, request: Request, user=Depends(get_current_user)) -> CallInitResponse:
    caller_user_id = getattr(user, "id", None)
    caller_username = getattr(user, "username", None) or getattr(user, "email", None) or "caller"

    has_app_target = bool(payload.callee_user_id or payload.callee_voice_id or payload.friend_id)

    # PSTN-only 요청은 P1에서 다이얼러 폴백(앱↔앱만 실제 연결).
    if not has_app_target:
        if payload.callee_phone:
            return CallInitResponse(
                call_id="",
                signaling_server="",
                turn_servers=[],
                session_id=payload.session_id,
                call_route="pstn_fallback",
                phone_dialer_required=True,
                fallback_dial_url=f"tel:{payload.callee_phone}",
                user_message="앱 통화 대상이 아니어서 전화 다이얼러로 연결합니다.",
                status="dialer_required",
                requested_mode=payload.mode,
                resolved_mode="pstn_fallback",
                auto_relay_requested=payload.auto_relay,
                auto_relay_applied=False,
                participant_role="caller",
            )
        raise HTTPException(
            status_code=400,
            detail={"code": "no_target", "message": "통화 대상(callee_user_id/voice_id/friend_id/phone)이 필요합니다."},
        )

    store = get_store()
    room, role = await store.create_or_match(
        caller_user_id=caller_user_id,
        caller_username=caller_username,
        callee_user_id=payload.callee_user_id,
        callee_voice_id=payload.callee_voice_id,
        session_id=payload.session_id,
        mode=payload.mode,
        auto_relay=payload.auto_relay,
    )

    token = _mint_ws_token(
        username=caller_username,
        user_id=caller_user_id,
        call_id=room.call_id,
        role=role,
    )
    signaling_url = build_signaling_url(
        call_id=room.call_id,
        token=token,
        role=role,
        request_scheme=request.url.scheme,
        request_host=request.headers.get("host"),
    )

    # P3-A: 발신자(caller) 턴에서 콜리 presence 확인 + FCM 착신 푸시.
    callee_online = True
    if role == "caller" and room.callee.user_id is not None:
        presence = get_presence()
        await presence.mark_online(caller_user_id)  # 발신자도 온라인 표시
        callee_online = await presence.is_online(room.callee.user_id)
        tokens = await presence.get_devices(room.callee.user_id)
        push_result = await push.send_incoming_call_push(
            tokens,
            call_id=room.call_id,
            caller_label=str(caller_username),
            data={"caller_user_id": caller_user_id, "session_id": room.session_id or ""},
        )
        await store.add_event(
            room.call_id,
            "push_skipped" if push_result.get("skipped") else "push_sent",
            "caller",
            {"sent": push_result.get("sent", 0), "reason": push_result.get("reason"),
             "callee_online": callee_online, "device_count": len(tokens)},
        )

    return CallInitResponse(
        call_id=room.call_id,
        signaling_server=signaling_url,
        turn_servers=get_ice_servers(user_key=str(caller_user_id or room.call_id)),
        session_id=room.session_id,
        call_route="app",
        phone_dialer_required=False,
        callee_app_online=callee_online,
        caller_user_id=room.caller.user_id,
        callee_user_id=room.callee.user_id,
        callee_voice_id=room.callee.voice_id,
        participant_role=role,
        status=room.status,
        requested_mode=payload.mode,
        resolved_mode=room.mode,
        auto_relay_requested=payload.auto_relay,
        auto_relay_applied=room.auto_relay,
    )


@router.get("/calls/{call_id}/audit", response_model=AuditResponse)
async def audit_call(call_id: str, user=Depends(get_current_user)) -> AuditResponse:
    room = await get_store().get(call_id)
    if room is None:
        raise HTTPException(status_code=404, detail="해당 call_id의 통화를 찾을 수 없습니다.")
    return AuditResponse(
        call_id=room.call_id,
        status=room.status,
        created_at=room.created_at,
        session_id=room.session_id,
        mode=room.mode,
        participants=room.participants_summary(),
        events=room.events,
    )


@router.post("/calls/{call_id}/end")
async def end_call(call_id: str, user=Depends(get_current_user)) -> Dict[str, Any]:
    room = await get_store().end(call_id, role=None)
    if room is None:
        raise HTTPException(status_code=404, detail="해당 call_id의 통화를 찾을 수 없습니다.")
    # 연결된 참가자에게 hangup 통지.
    await get_relay().notify_hangup(call_id)
    return {"call_id": call_id, "status": "ended"}


def _decode_ws_token(token: str, call_id: str, role: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("voip_call_id") != call_id:
        return None
    if payload.get("voip_role") != role:
        return None
    return payload


@router.websocket("/ws/{call_id}")
async def voip_signaling(websocket: WebSocket, call_id: str) -> None:
    token = websocket.query_params.get("token", "")
    role = websocket.query_params.get("role", "")
    if role not in ("caller", "callee"):
        await websocket.close(code=1008)
        return
    payload = _decode_ws_token(token, call_id, role)
    if payload is None:
        await websocket.close(code=1008)
        return

    store = get_store()
    room = await store.get(call_id)
    if room is None or room.status == "ended":
        await websocket.close(code=1008)
        return

    relay = get_relay()
    # register(구독)을 accept보다 먼저 수행 → 클라이언트가 메시지를 보내기 전에
    # 릴레이 구독이 활성화되도록 보장(Redis pub/sub 메시지 유실 방지).
    await relay.register(call_id, role, websocket)
    await websocket.accept()
    await store.mark_connected(call_id, role)
    # P3-A: ws 접속 = 해당 사용자 온라인 표시(presence 갱신).
    uid = payload.get("uid")
    if uid is not None:
        try:
            await get_presence().mark_online(int(uid))
        except (TypeError, ValueError):
            pass

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = str(message.get("type") or "").strip().lower()
            message.setdefault("call_id", call_id)

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "call_id": call_id})
                continue

            if msg_type == "hangup":
                # 상태를 먼저 ended로 확정한 뒤 상대에게 통지(수신 측이 audit를 조회해도 일관).
                await store.end(call_id, role=role)
                await relay.send_to_peer(call_id, role, {"type": "hangup", "call_id": call_id})
                break

            if msg_type in RELAY_TYPES:
                message["from_role"] = role
                await relay.send_to_peer(call_id, role, message)
                await _record_relay_event(store, call_id, role, msg_type, message)
                continue

            logger.debug("[VoIP] unknown signaling type ignored: %s", msg_type)
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("[VoIP] signaling loop error (call_id=%s role=%s): %s", call_id, role, exc)
    finally:
        await relay.unregister(call_id, role, websocket)
        await store.add_event(call_id, "ws_disconnected", role, {})


async def _record_relay_event(store, call_id: str, role: str, msg_type: str, message: Dict[str, Any]) -> None:
    detail: Dict[str, Any] = {}
    if msg_type in ("offer", "answer"):
        detail["sdp_length"] = len(str(message.get("sdp") or ""))
    elif msg_type == "candidate":
        detail["has_candidate"] = bool(message.get("candidate"))
    # answer 수신 시 통화 상태를 connected로 전이.
    set_status = "connected" if msg_type == "answer" else None
    await store.add_event(call_id, msg_type, role, detail, set_status=set_status)
