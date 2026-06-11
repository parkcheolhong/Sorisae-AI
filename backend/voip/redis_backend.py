"""P2: Redis 백엔드 통화 스토어 + pub/sub 시그널링 릴레이(멀티 워커 지원).

기능 플래그: 환경변수 `VOIP_REDIS_URL` 이 설정되면 활성화. 미설정 시 인메모리(P1) 기본 동작.

- RedisCallStore: 룸 메타데이터/감사 이벤트를 Redis에 저장(워커 간 initiate/audit/end 일관).
  앱↔앱 자동 매칭은 `voip:incoming:{user_id}` 인덱스 세트로 O(1) 조회.
- RedisRelay: 시그널링 메시지를 `voip:relay:{call_id}` 채널로 publish하고,
  각 소켓은 자신의 role을 대상으로 한 메시지를 구독해 전달 → 워커가 달라도 릴레이 성립.

소켓 객체 자체는 프로세스 로컬(직렬화 불가)이므로 릴레이는 pub/sub로 브리지한다.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from .registry import CallRoom, Participant

logger = logging.getLogger(__name__)

ROOM_TTL_SEC = 3600
LOCK_TIMEOUT_SEC = 10
LOCK_BLOCKING_TIMEOUT_SEC = 5


def redis_url() -> str:
    return (os.getenv("VOIP_REDIS_URL", "") or "").strip()


def is_redis_enabled() -> bool:
    return bool(redis_url())


_client = None


def get_client():
    global _client
    if _client is None:
        import redis.asyncio as aioredis  # lazy import

        _client = aioredis.from_url(redis_url(), encoding="utf-8", decode_responses=True)
    return _client


def _room_key(call_id: str) -> str:
    return f"voip:room:{call_id}"


def _incoming_key(user_id: int) -> str:
    return f"voip:incoming:{user_id}"


def _relay_channel(call_id: str) -> str:
    return f"voip:relay:{call_id}"


def _relay_owner_key(call_id: str, role: str) -> str:
    return f"voip:relay_owner:{call_id}:{role}"


def _room_lock_key(call_id: str) -> str:
    return f"voip:lock:room:{call_id}"


@asynccontextmanager
async def _redis_lock(name: str):
    lock = get_client().lock(
        name,
        timeout=LOCK_TIMEOUT_SEC,
        blocking_timeout=LOCK_BLOCKING_TIMEOUT_SEC,
    )
    acquired = await lock.acquire()
    if not acquired:
        raise TimeoutError(f"Timed out acquiring Redis lock: {name}")
    try:
        yield
    finally:
        try:
            await lock.release()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[VoIP] redis lock release error (%s): %s", name, exc)


class RedisCallStore:
    """CallRegistry와 동일한 비동기 API를 Redis로 구현."""

    async def _load(self, call_id: str) -> Optional[CallRoom]:
        raw = await get_client().get(_room_key(call_id))
        if not raw:
            return None
        return CallRoom.from_dict(json.loads(raw))

    async def _save(self, room: CallRoom) -> None:
        await get_client().set(_room_key(room.call_id), json.dumps(room.to_dict()), ex=ROOM_TTL_SEC)

    async def _update_room(self, call_id: str, mutate) -> Optional[CallRoom]:
        async with _redis_lock(_room_lock_key(call_id)):
            room = await self._load(call_id)
            if room is None:
                return None
            mutate(room)
            await self._save(room)
            return room

    async def create_or_match(
        self,
        *,
        caller_user_id: Optional[int],
        caller_username: Optional[str],
        callee_user_id: Optional[int],
        callee_voice_id: Optional[str],
        session_id: Optional[str],
        mode: str,
        auto_relay: bool,
    ) -> Tuple[CallRoom, str]:
        async with _redis_lock("voip:lock:create_or_match"):
            client = get_client()

            def can_accept(room: CallRoom) -> bool:
                return (
                    room.status == "ringing"
                    and room.callee.user_id == caller_user_id
                    and room.callee.connected_at is None
                    and room.caller.user_id != caller_user_id
                )

            # 1) 내가 callee인 ringing room이 있으면 합류.
            if caller_user_id is not None:
                incoming = await client.smembers(_incoming_key(caller_user_id))
                for cid in incoming:
                    room = await self._load(cid)
                    if room is None:
                        await client.srem(_incoming_key(caller_user_id), cid)
                        continue
                    if not can_accept(room):
                        continue
                    async with _redis_lock(_room_lock_key(cid)):
                        room = await self._load(cid)
                        if room is None:
                            await client.srem(_incoming_key(caller_user_id), cid)
                            continue
                        if not can_accept(room):
                            continue
                        room.callee.username = caller_username
                        room.add_event("accept", "callee", {"user_id": caller_user_id})
                        await self._save(room)
                        await client.srem(_incoming_key(caller_user_id), cid)
                        return room, "callee"

            # 2) 새 통화 생성.
            call_id = "c_" + uuid.uuid4().hex[:12]
            room = CallRoom(
                call_id=call_id,
                status="ringing",
                created_at=round(time.time(), 3),
                caller=Participant(role="caller", user_id=caller_user_id, username=caller_username),
                callee=Participant(role="callee", user_id=callee_user_id, voice_id=callee_voice_id),
                session_id=session_id,
                mode=mode,
                auto_relay=auto_relay,
            )
            room.add_event("initiate", "caller", {
                "user_id": caller_user_id,
                "callee_user_id": callee_user_id,
                "mode": mode,
            })
            await self._save(room)
            if callee_user_id is not None:
                await client.sadd(_incoming_key(callee_user_id), call_id)
                await client.expire(_incoming_key(callee_user_id), ROOM_TTL_SEC)
            return room, "caller"

    async def get(self, call_id: str) -> Optional[CallRoom]:
        return await self._load(call_id)

    async def end(self, call_id: str, role: Optional[str] = None) -> Optional[CallRoom]:
        def mutate(room: CallRoom) -> None:
            room.status = "ended"
            room.add_event("end", role, {})

        return await self._update_room(call_id, mutate)

    async def mark_connected(self, call_id: str, role: str) -> Optional[CallRoom]:
        def mutate(room: CallRoom) -> None:
            participant = room.caller if role == "caller" else room.callee
            participant.connected_at = round(time.time(), 3)
            if room.status == "ringing":
                room.status = "connecting"
            room.add_event("ws_connected", role, {})

        return await self._update_room(call_id, mutate)

    async def add_event(
        self,
        call_id: str,
        event_type: str,
        role: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
        *,
        set_status: Optional[str] = None,
    ) -> None:
        def mutate(room: CallRoom) -> None:
            room.add_event(event_type, role, detail)
            if set_status:
                room.status = set_status

        await self._update_room(call_id, mutate)

    async def clear(self) -> None:
        client = get_client()
        async for key in client.scan_iter("voip:room:*"):
            await client.delete(key)
        async for key in client.scan_iter("voip:incoming:*"):
            await client.delete(key)


# ── 릴레이(시그널링 메시지 전달) ──────────────────────────────────────────────

def _other_role(role: str) -> str:
    return "callee" if role == "caller" else "caller"


class InMemoryRelay:
    """단일 프로세스: 로컬 hub 소켓에 직접 전달(P1 동작)."""

    def __init__(self, hub) -> None:
        self._hub = hub

    async def register(self, call_id: str, role: str, websocket: Any) -> None:
        self._hub.add(call_id, role, websocket)

    async def unregister(self, call_id: str, role: str, websocket: Any) -> None:
        self._hub.remove(call_id, role)

    async def send_to_peer(self, call_id: str, role: str, message: Dict[str, Any]) -> bool:
        return await self._hub.relay(call_id, role, message)

    async def notify_hangup(self, call_id: str) -> None:
        for role in ("caller", "callee"):
            peer = self._hub._rooms.get(call_id, {}).get(role)
            if peer is not None:
                try:
                    await peer.send_json({"type": "hangup", "call_id": call_id})
                except Exception:  # noqa: BLE001
                    pass


class RedisRelay:
    """멀티 워커: pub/sub로 메시지를 브리지. 각 소켓은 자신의 role 대상 메시지를 구독·전달."""

    def __init__(self) -> None:
        # (call_id, role) -> (id(ws), owner_token, pubsub, task)
        self._subs: Dict[Tuple[str, str], Tuple[int, str, Any, asyncio.Task]] = {}
        self._lock = asyncio.Lock()

    async def register(self, call_id: str, role: str, websocket: Any) -> None:
        async with self._lock:
            entry = self._subs.pop((call_id, role), None)
            if entry is not None:
                _, owner_token, pubsub, task = entry
                await self._close_subscription(call_id, role, owner_token, pubsub, task)

            owner_token = uuid.uuid4().hex
            pubsub = get_client().pubsub()
            await pubsub.subscribe(_relay_channel(call_id))
            await get_client().set(_relay_owner_key(call_id, role), owner_token, ex=ROOM_TTL_SEC)
            task = asyncio.create_task(self._listen(pubsub, call_id, role, owner_token, websocket))
            self._subs[(call_id, role)] = (id(websocket), owner_token, pubsub, task)

    async def _listen(self, pubsub, call_id: str, role: str, owner_token: str, websocket: Any) -> None:
        try:
            async for raw in pubsub.listen():
                if raw is None or raw.get("type") != "message":
                    continue
                try:
                    envelope = json.loads(raw["data"])
                except (ValueError, TypeError):
                    continue
                if envelope.get("target_role") != role:
                    continue
                if await get_client().get(_relay_owner_key(call_id, role)) != owner_token:
                    break
                try:
                    await websocket.send_json(envelope.get("payload") or {})
                except Exception:  # noqa: BLE001
                    break
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("[VoIP] redis relay listen error: %s", exc)

    async def unregister(self, call_id: str, role: str, websocket: Any) -> None:
        async with self._lock:
            entry = self._subs.get((call_id, role))
            if entry is None or entry[0] != id(websocket):
                return
            _, owner_token, pubsub, task = self._subs.pop((call_id, role))
        await self._close_subscription(call_id, role, owner_token, pubsub, task)

    async def _close_subscription(
        self,
        call_id: str,
        role: str,
        owner_token: str,
        pubsub: Any,
        task: asyncio.Task,
    ) -> None:
        task.cancel()
        try:
            await pubsub.unsubscribe(_relay_channel(call_id))
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass
        try:
            await get_client().eval(
                "if redis.call('get', KEYS[1]) == ARGV[1] "
                "then return redis.call('del', KEYS[1]) else return 0 end",
                1,
                _relay_owner_key(call_id, role),
                owner_token,
            )
        except Exception:  # noqa: BLE001
            pass
        with suppress(asyncio.CancelledError):
            await task

    async def _publish(self, call_id: str, target_role: str, message: Dict[str, Any]) -> None:
        await get_client().publish(
            _relay_channel(call_id),
            json.dumps({"target_role": target_role, "payload": message}),
        )

    async def send_to_peer(self, call_id: str, role: str, message: Dict[str, Any]) -> bool:
        await self._publish(call_id, _other_role(role), message)
        return True

    async def notify_hangup(self, call_id: str) -> None:
        for role in ("caller", "callee"):
            await self._publish(call_id, role, {"type": "hangup", "call_id": call_id})


# ── 팩토리 ────────────────────────────────────────────────────────────────────

_redis_store: Optional[RedisCallStore] = None
_redis_relay: Optional[RedisRelay] = None


def get_store():
    """활성 통화 스토어 반환(Redis 또는 인메모리)."""
    if is_redis_enabled():
        global _redis_store
        if _redis_store is None:
            _redis_store = RedisCallStore()
        return _redis_store
    from .registry import registry
    return registry


def get_relay():
    """활성 릴레이 반환(Redis pub/sub 또는 인메모리 hub)."""
    if is_redis_enabled():
        global _redis_relay
        if _redis_relay is None:
            _redis_relay = RedisRelay()
        return _redis_relay
    from .signaling import hub
    return InMemoryRelay(hub)
