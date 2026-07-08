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
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from .registry import CallRoom, Participant

logger = logging.getLogger(__name__)

ROOM_TTL_SEC = 3600


def redis_url() -> str:
    return (os.getenv("VOIP_REDIS_URL", "") or "").strip()


def is_redis_enabled() -> bool:
    return bool(redis_url())


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _sentinel_nodes() -> list[tuple[str, int]]:
    """``VOIP_REDIS_SENTINELS`` = "host1:26379,host2:26379" → [(host, port), …]."""

    raw = (os.getenv("VOIP_REDIS_SENTINELS", "") or "").strip()
    nodes: list[tuple[str, int]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        host, _, port = item.partition(":")
        if host:
            nodes.append((host.strip(), _int_env_value(port, 26379)))
    return nodes


def _int_env_value(raw: str, default: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _common_client_kwargs() -> Dict[str, Any]:
    """풀/헬스/타임아웃 — standalone·sentinel·cluster 공통 연결 옵션(운영 하드닝)."""

    return {
        "decode_responses": True,
        "encoding": "utf-8",
        "health_check_interval": _int_env("VOIP_REDIS_HEALTH_CHECK_INTERVAL", 30),
        "socket_timeout": _float_env("VOIP_REDIS_SOCKET_TIMEOUT", 5.0),
        "socket_connect_timeout": _float_env("VOIP_REDIS_SOCKET_CONNECT_TIMEOUT", 5.0),
        "retry_on_timeout": True,
    }


def _client_plan() -> Tuple[str, Dict[str, Any]]:
    """연결 모드 결정(순수 함수, redis 미설치에도 테스트 가능).

    우선순위: Sentinel(``VOIP_REDIS_SENTINELS``) → Cluster(``VOIP_REDIS_CLUSTER``) → standalone.
    Sentinel은 pub/sub 릴레이 워크로드에 맞는 master/replica failover를 제공한다.
    Cluster는 opt-in(샤딩 pub/sub 제약 주의 — 일반 PUBLISH는 전체 브로드캐스트).
    """

    common = _common_client_kwargs()
    sentinels = _sentinel_nodes()
    if sentinels:
        return "sentinel", {
            "sentinels": sentinels,
            "master": (os.getenv("VOIP_REDIS_SENTINEL_MASTER", "") or "mymaster").strip(),
            "common": common,
        }
    if _bool_env("VOIP_REDIS_CLUSTER"):
        return "cluster", {"url": redis_url(), "common": common}
    return "standalone", {
        "url": redis_url(),
        "common": {**common, "max_connections": _int_env("VOIP_REDIS_MAX_CONNECTIONS", 50)},
    }


_client = None


def get_client():
    """HA 인지 Redis 클라이언트 싱글톤. HA 구성 실패 시 standalone로 안전 폴백."""

    global _client
    if _client is not None:
        return _client

    import redis.asyncio as aioredis  # lazy import

    mode, plan = _client_plan()
    try:
        if mode == "sentinel":
            from redis.asyncio.sentinel import Sentinel

            sentinel = Sentinel(plan["sentinels"], **plan["common"])
            _client = sentinel.master_for(plan["master"], **plan["common"])
            logger.info("[VoIP] Redis sentinel client (master=%s, nodes=%d)",
                        plan["master"], len(plan["sentinels"]))
        elif mode == "cluster":
            from redis.asyncio.cluster import RedisCluster

            _client = RedisCluster.from_url(plan["url"], **plan["common"])
            logger.info("[VoIP] Redis cluster client (caution: pub/sub broadcast semantics)")
        else:
            _client = aioredis.from_url(plan["url"], **plan["common"])
    except Exception as exc:  # noqa: BLE001 - HA 구성 실패 시 standalone 폴백(가용성 우선)
        logger.warning("[VoIP] Redis HA client init failed (%s); falling back to standalone: %s",
                       mode, exc)
        _client = aioredis.from_url(redis_url(), encoding="utf-8", decode_responses=True)
    return _client


def reset_client_for_test() -> None:
    """테스트 전용 — env 토글 후 클라이언트 싱글톤 재생성을 위해 초기화."""

    global _client
    _client = None


def _room_key(call_id: str) -> str:
    return f"voip:room:{call_id}"


def _events_key(call_id: str) -> str:
    return f"voip:events:{call_id}"


def _incoming_key(user_id: int) -> str:
    return f"voip:incoming:{user_id}"


def _relay_channel(call_id: str) -> str:
    return f"voip:relay:{call_id}"


def _now() -> float:
    return round(time.time(), 3)


# 상태 단조 전이(ringing<connecting<connected<ended)를 원자적으로 강제하는 Lua.
# 'ended'가 종단 — 지연된 'connected' 등이 종료 상태를 덮어쓰지 못한다.
_STATUS_LUA = """
local cur = redis.call('HGET', KEYS[1], 'status')
local rank = {ringing=1, connecting=2, connected=3, ended=4}
local nr = rank[ARGV[1]] or 0
local cr = rank[cur] or 0
if cur == false or nr > cr then
  redis.call('HSET', KEYS[1], 'status', ARGV[1])
  return 1
end
return 0
"""


class RedisCallStore:
    """CallRegistry와 동일한 비동기 API를 Redis로 구현.

    동시성: 룸 핵심 필드는 HASH(상태/참가자 — 단일 필드 HSET), 감사 이벤트는 LIST(RPUSH)로 저장해
    여러 코루틴/워커의 read-modify-write 경쟁(상태·이벤트 유실)을 제거한다.
    """

    async def _set_status(self, call_id: str, status: str) -> None:
        """상태를 단조 전이로만 변경(원자적). ended는 종단."""
        await get_client().eval(_STATUS_LUA, 1, _room_key(call_id), status)

    async def _push_event(self, call_id: str, event_type: str, role: Optional[str], detail: Optional[Dict[str, Any]]) -> None:
        client = get_client()
        event = {"ts": _now(), "type": event_type, "role": role, "detail": detail or {}}
        await client.rpush(_events_key(call_id), json.dumps(event))
        await client.expire(_events_key(call_id), ROOM_TTL_SEC)

    async def _load(self, call_id: str) -> Optional[CallRoom]:
        client = get_client()
        data = await client.hgetall(_room_key(call_id))
        if not data:
            return None
        raw_events = await client.lrange(_events_key(call_id), 0, -1)
        events = [json.loads(e) for e in raw_events]
        return CallRoom(
            call_id=call_id,
            status=data.get("status", "ringing"),
            created_at=float(data.get("created_at", _now())),
            caller=Participant(**json.loads(data["caller"])),
            callee=Participant(**json.loads(data["callee"])),
            session_id=data.get("session_id") or None,
            mode=data.get("mode", "voip_full_auto"),
            auto_relay=data.get("auto_relay") == "1",
            events=events,
        )

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
        client = get_client()

        # 1) 내가 callee인 ringing room이 있으면 합류(인덱스에서 원자적으로 꺼냄).
        if caller_user_id is not None:
            while True:
                cid = await client.spop(_incoming_key(caller_user_id))
                if not cid:
                    break
                room = await self._load(cid)
                if room is None:
                    continue
                if (
                    room.status == "ringing"
                    and room.callee.user_id == caller_user_id
                    and room.callee.connected_at is None
                    and room.caller.user_id != caller_user_id
                ):
                    room.callee.username = caller_username
                    await client.hset(_room_key(cid), "callee", json.dumps(vars(room.callee)))
                    await self._push_event(cid, "accept", "callee", {"user_id": caller_user_id})
                    room.events.append({"ts": _now(), "type": "accept", "role": "callee", "detail": {"user_id": caller_user_id}})
                    return room, "callee"

        # 2) 새 통화 생성.
        call_id = "c_" + uuid.uuid4().hex[:12]
        room = CallRoom(
            call_id=call_id,
            status="ringing",
            created_at=_now(),
            caller=Participant(role="caller", user_id=caller_user_id, username=caller_username),
            callee=Participant(role="callee", user_id=callee_user_id, voice_id=callee_voice_id),
            session_id=session_id,
            mode=mode,
            auto_relay=auto_relay,
        )
        await client.hset(_room_key(call_id), mapping={
            "status": room.status,
            "created_at": str(room.created_at),
            "caller": json.dumps(vars(room.caller)),
            "callee": json.dumps(vars(room.callee)),
            "session_id": session_id or "",
            "mode": mode,
            "auto_relay": "1" if auto_relay else "0",
        })
        await client.expire(_room_key(call_id), ROOM_TTL_SEC)
        await self._push_event(call_id, "initiate", "caller", {
            "user_id": caller_user_id, "callee_user_id": callee_user_id, "mode": mode,
        })
        room.events.append({"ts": _now(), "type": "initiate", "role": "caller", "detail": {}})
        if callee_user_id is not None:
            await client.sadd(_incoming_key(callee_user_id), call_id)
            await client.expire(_incoming_key(callee_user_id), ROOM_TTL_SEC)
        return room, "caller"

    async def get(self, call_id: str) -> Optional[CallRoom]:
        return await self._load(call_id)

    async def end(self, call_id: str, role: Optional[str] = None) -> Optional[CallRoom]:
        client = get_client()
        if not await client.exists(_room_key(call_id)):
            return None
        await self._set_status(call_id, "ended")
        await self._push_event(call_id, "end", role, {})
        return await self._load(call_id)

    async def mark_connected(self, call_id: str, role: str) -> Optional[CallRoom]:
        client = get_client()
        field = "caller" if role == "caller" else "callee"
        raw = await client.hget(_room_key(call_id), field)
        if raw is None:
            return None
        participant = json.loads(raw)
        participant["connected_at"] = _now()
        await client.hset(_room_key(call_id), field, json.dumps(participant))
        await self._set_status(call_id, "connecting")  # 단조 전이(연결됨/종료는 미하향)
        await self._push_event(call_id, "ws_connected", role, {})
        return await self._load(call_id)

    async def accept_callee(self, call_id: str, user_id: int, username: Optional[str]) -> Optional[CallRoom]:
        client = get_client()
        raw = await client.hget(_room_key(call_id), "callee")
        status = await client.hget(_room_key(call_id), "status")
        if raw is None or status == "ended":
            return None
        callee = json.loads(raw)
        if callee.get("user_id") not in (None, user_id):
            return None
        callee["user_id"] = user_id
        callee["username"] = username
        await client.hset(_room_key(call_id), "callee", json.dumps(callee))
        await client.srem(_incoming_key(user_id), call_id)
        await self._push_event(call_id, "accept", "callee", {"user_id": user_id, "via": "push"})
        return await self._load(call_id)

    async def add_event(
        self,
        call_id: str,
        event_type: str,
        role: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
        *,
        set_status: Optional[str] = None,
    ) -> None:
        client = get_client()
        if not await client.exists(_room_key(call_id)):
            return
        await self._push_event(call_id, event_type, role, detail)
        if set_status:
            await self._set_status(call_id, set_status)  # 단조 전이로 원자 처리

    async def clear(self) -> None:
        client = get_client()
        for pattern in ("voip:room:*", "voip:events:*", "voip:incoming:*"):
            async for key in client.scan_iter(pattern):
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
        # (call_id, role, id(ws)) -> (pubsub, task)
        self._subs: Dict[Tuple[str, str, int], Tuple[Any, asyncio.Task]] = {}

    async def register(self, call_id: str, role: str, websocket: Any) -> None:
        pubsub = get_client().pubsub()
        await pubsub.subscribe(_relay_channel(call_id))
        task = asyncio.create_task(self._listen(pubsub, role, websocket))
        self._subs[(call_id, role, id(websocket))] = (pubsub, task)

    async def _listen(self, pubsub, role: str, websocket: Any) -> None:
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
                try:
                    await websocket.send_json(envelope.get("payload") or {})
                except Exception:  # noqa: BLE001
                    break
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("[VoIP] redis relay listen error: %s", exc)

    async def unregister(self, call_id: str, role: str, websocket: Any) -> None:
        entry = self._subs.pop((call_id, role, id(websocket)), None)
        if entry is None:
            return
        pubsub, task = entry
        task.cancel()
        try:
            await pubsub.unsubscribe(_relay_channel(call_id))
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass

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
