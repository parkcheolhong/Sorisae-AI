"""VoIP 통역 통화 API (Phase P1) — REST initiate/audit/end + WebSocket 시그널링.

설계: NADOTONGRYOKSA_VOIP_BACKEND_DESIGN.md
인증: REST 3종은 Bearer(get_current_user). WebSocket은 query token(initiate가 발급한 단기 JWT).
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from backend.auth import ALGORITHM, SECRET_KEY, create_access_token, get_current_user

from .config import build_signaling_url, get_ice_servers, signaling_token_ttl_sec
from .models import AuditResponse, CallInitiateRequest, CallInitResponse
from .registry import registry
from .signaling import RELAY_TYPES, hub

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voip", tags=["voip"])


def _mint_ws_token(*, username: str, user_id: Optional[int], call_id: str, role: str) -> str:
    return create_access_token(
        {"sub": username, "uid": user_id, "voip_call_id": call_id, "voip_role": role},
        expires_delta=timedelta(seconds=signaling_token_ttl_sec()),
    )


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

    room, role = await registry.create_or_match(
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

    return CallInitResponse(
        call_id=room.call_id,
        signaling_server=signaling_url,
        turn_servers=get_ice_servers(),
        session_id=room.session_id,
        call_route="app",
        phone_dialer_required=False,
        callee_app_online=True,  # P1: 낙관적. 정확한 presence는 FCM(P3).
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
    room = await registry.get(call_id)
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
    room = await registry.end(call_id, role=None)
    if room is None:
        raise HTTPException(status_code=404, detail="해당 call_id의 통화를 찾을 수 없습니다.")
    # 남은 참가자에게 hangup 통지(있다면).
    for role in ("caller", "callee"):
        peer = hub._rooms.get(call_id, {}).get(role)
        if peer is not None:
            try:
                await peer.send_json({"type": "hangup", "call_id": call_id})
            except Exception:
                pass
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

    room = await registry.get(call_id)
    if room is None or room.status == "ended":
        await websocket.close(code=1008)
        return

    await websocket.accept()
    hub.add(call_id, role, websocket)
    await registry.mark_connected(call_id, role)

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = str(message.get("type") or "").strip().lower()
            message.setdefault("call_id", call_id)

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "call_id": call_id})
                continue

            if msg_type == "hangup":
                await hub.relay(call_id, role, {"type": "hangup", "call_id": call_id})
                await registry.end(call_id, role=role)
                break

            if msg_type in RELAY_TYPES:
                message["from_role"] = role
                delivered = await hub.relay(call_id, role, message)
                _record_relay_event(call_id, role, msg_type, message, delivered)
                continue

            logger.debug("[VoIP] unknown signaling type ignored: %s", msg_type)
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("[VoIP] signaling loop error (call_id=%s role=%s): %s", call_id, role, exc)
    finally:
        hub.remove(call_id, role)
        room = await registry.get(call_id)
        if room is not None:
            room.add_event("ws_disconnected", role, {})


def _record_relay_event(call_id: str, role: str, msg_type: str, message: Dict[str, Any], delivered: bool) -> None:
    room = registry._rooms.get(call_id)
    if room is None:
        return
    detail: Dict[str, Any] = {"delivered": delivered}
    if msg_type in ("offer", "answer"):
        detail["sdp_length"] = len(str(message.get("sdp") or ""))
    elif msg_type == "candidate":
        detail["has_candidate"] = bool(message.get("candidate"))
    room.add_event(msg_type, role, detail)
    if msg_type == "answer":
        room.status = "connected"
