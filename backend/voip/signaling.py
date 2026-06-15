"""WebSocket 시그널링 허브 — 같은 call_id 룸의 두 참가자 간 메시지 릴레이.

서버는 미디어를 중계하지 않으며, SDP/ICE/채팅/음성번역 메시지를 상대 역할에게 그대로 전달한다.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 상대에게 릴레이되는 메시지 타입(ping/pong/hangup은 별도 처리)
RELAY_TYPES = {"offer", "answer", "candidate", "chat_message", "voice_translation"}


def _other_role(role: str) -> str:
    return "callee" if role == "caller" else "caller"


class SignalingHub:
    def __init__(self) -> None:
        # call_id -> {role -> websocket}
        self._rooms: Dict[str, Dict[str, Any]] = {}

    def add(self, call_id: str, role: str, websocket: Any) -> None:
        self._rooms.setdefault(call_id, {})[role] = websocket

    def remove(self, call_id: str, role: str) -> None:
        room = self._rooms.get(call_id)
        if not room:
            return
        if room.get(role) is not None:
            room.pop(role, None)
        if not room:
            self._rooms.pop(call_id, None)

    def peer(self, call_id: str, role: str) -> Optional[Any]:
        return self._rooms.get(call_id, {}).get(_other_role(role))

    async def relay(self, call_id: str, role: str, message: Dict[str, Any]) -> bool:
        """상대 역할 소켓으로 메시지를 전달. 상대가 없으면 False."""
        peer = self.peer(call_id, role)
        if peer is None:
            return False
        await peer.send_json(message)
        return True


hub = SignalingHub()
