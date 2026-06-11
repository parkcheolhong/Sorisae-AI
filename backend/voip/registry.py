"""인메모리 통화 레지스트리 (Phase P1, 단일 워커 전제).

- 앱↔앱 자동 매칭: A가 B에게 걸면 room.callee.user_id=B. 이후 B가 initiate하면
  '자신이 callee인 ringing room'을 찾아 callee로 합류한다(별도 엔드포인트 불필요).
- 감사(audit) 이벤트를 룸에 축적하여 /audit로 노출하고 실기기 게이트 로그를 서버측에도 남긴다.

멀티 워커 확장(Redis 백엔드)은 P2에서 교체한다.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Participant:
    role: str  # caller | callee
    user_id: Optional[int] = None
    username: Optional[str] = None
    voice_id: Optional[str] = None
    friend_id: Optional[str] = None
    connected_at: Optional[float] = None


@dataclass
class CallRoom:
    call_id: str
    status: str  # ringing | connecting | connected | ended
    created_at: float
    caller: Participant
    callee: Participant
    session_id: Optional[str] = None
    mode: str = "voip_full_auto"
    auto_relay: bool = False
    events: List[Dict[str, Any]] = field(default_factory=list)

    def add_event(self, event_type: str, role: Optional[str] = None, detail: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({
            "ts": round(time.time(), 3),
            "type": event_type,
            "role": role,
            "detail": detail or {},
        })

    def participants_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "role": p.role,
                "user_id": p.user_id,
                "voice_id": p.voice_id,
                "friend_id": p.friend_id,
                "connected": p.connected_at is not None,
            }
            for p in (self.caller, self.callee)
        ]


class CallRegistry:
    def __init__(self) -> None:
        self._rooms: Dict[str, CallRoom] = {}
        self._lock = asyncio.Lock()

    async def create_or_match(
        self,
        *,
        caller_user_id: Optional[int],
        caller_username: Optional[str],
        caller_id: Optional[str],
        callee_user_id: Optional[int],
        callee_voice_id: Optional[str],
        friend_id: Optional[Any],
        session_id: Optional[str],
        mode: str,
        auto_relay: bool,
    ) -> Tuple[CallRoom, str]:
        """(room, role) 반환. role은 'caller' 또는 'callee'."""
        caller_id = self._normalize_identifier(caller_id)
        callee_voice_id = self._normalize_identifier(callee_voice_id)
        friend_id = self._normalize_identifier(friend_id)
        async with self._lock:
            # 1) 내가 callee인 대기중(ringing) room이 있으면 그 통화에 합류한다.
            for room in self._rooms.values():
                if (
                    room.status == "ringing"
                    and room.callee.connected_at is None
                    and self._matches_callee(room, caller_user_id, caller_id, friend_id)
                ):
                    room.callee.user_id = caller_user_id
                    room.callee.username = caller_username
                    room.add_event("accept", "callee", {"user_id": caller_user_id})
                    return room, "callee"

            # 2) 새 통화 생성(내가 caller).
            call_id = "c_" + uuid.uuid4().hex[:12]
            room = CallRoom(
                call_id=call_id,
                status="ringing",
                created_at=round(time.time(), 3),
                caller=Participant(role="caller", user_id=caller_user_id, username=caller_username, voice_id=caller_id),
                callee=Participant(role="callee", user_id=callee_user_id, voice_id=callee_voice_id, friend_id=friend_id),
                session_id=session_id,
                mode=mode,
                auto_relay=auto_relay,
            )
            room.add_event("initiate", "caller", {
                "user_id": caller_user_id,
                "callee_user_id": callee_user_id,
                "callee_voice_id": callee_voice_id,
                "friend_id": friend_id,
                "mode": mode,
            })
            self._rooms[call_id] = room
            return room, "caller"

    def _matches_callee(
        self,
        room: CallRoom,
        caller_user_id: Optional[int],
        caller_id: Optional[str],
        friend_id: Optional[Any],
    ) -> bool:
        if caller_user_id is not None and room.caller.user_id == caller_user_id:
            return False

        if caller_user_id is not None:
            if room.callee.user_id == caller_user_id:
                return True
            if room.callee.friend_id and room.callee.friend_id == str(caller_user_id):
                return True

        normalized_caller_id = self._normalize_identifier(caller_id)
        if normalized_caller_id and room.callee.voice_id == normalized_caller_id:
            return True

        normalized_friend_id = self._normalize_identifier(friend_id)
        if normalized_friend_id and room.callee.friend_id == normalized_friend_id:
            return True

        return False

    @staticmethod
    def _normalize_identifier(value: Optional[Any]) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    async def get(self, call_id: str) -> Optional[CallRoom]:
        async with self._lock:
            return self._rooms.get(call_id)

    async def end(self, call_id: str, role: Optional[str] = None) -> Optional[CallRoom]:
        async with self._lock:
            room = self._rooms.get(call_id)
            if room is None:
                return None
            room.status = "ended"
            room.add_event("end", role, {})
            return room

    async def mark_connected(self, call_id: str, role: str) -> Optional[CallRoom]:
        async with self._lock:
            room = self._rooms.get(call_id)
            if room is None:
                return None
            participant = room.caller if role == "caller" else room.callee
            participant.connected_at = round(time.time(), 3)
            if room.status == "ringing":
                room.status = "connecting"
            room.add_event("ws_connected", role, {})
            return room

    async def clear(self) -> None:
        async with self._lock:
            self._rooms.clear()


# 프로세스 전역 단일 레지스트리(P1: 단일 워커 전제).
registry = CallRegistry()
