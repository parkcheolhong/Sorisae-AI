"""P3-A: 디바이스 토큰 저장 + presence(온라인) 추적.

- 디바이스 토큰: 사용자별 FCM 토큰 집합(착신 푸시 대상).
- presence: 최근 활동(디바이스 등록/ws 접속/하트비트) 기반 TTL 키로 온라인 여부 추정.
  정확한 도달성은 FCM 전송 결과에 의존하나, 본 모듈은 "최근 활동" 근사로 callee_app_online을 제공.

저장소: 환경변수 `VOIP_REDIS_URL` 설정 시 Redis(멀티 워커), 미설정 시 인메모리(단일 워커).
"""
from __future__ import annotations

import os
import time
from typing import Dict, List, Optional

from .redis_backend import get_client, is_redis_enabled


def presence_ttl_sec() -> int:
    try:
        return int(os.getenv("VOIP_PRESENCE_TTL_SEC", "120"))
    except ValueError:
        return 120


def device_ttl_sec() -> int:
    try:
        return int(os.getenv("VOIP_DEVICE_TTL_SEC", str(30 * 24 * 3600)))
    except ValueError:
        return 30 * 24 * 3600


def _devices_key(user_id: int) -> str:
    return f"voip:devices:{user_id}"


def _presence_key(user_id: int) -> str:
    return f"voip:presence:{user_id}"


class InMemoryPresence:
    def __init__(self) -> None:
        self._devices: Dict[int, Dict[str, str]] = {}  # user_id -> {token: platform}
        self._presence: Dict[int, float] = {}  # user_id -> expiry epoch

    async def register_device(self, user_id: int, token: str, platform: Optional[str] = None) -> None:
        self._devices.setdefault(user_id, {})[token] = platform or ""

    async def unregister_device(self, user_id: int, token: str) -> None:
        self._devices.get(user_id, {}).pop(token, None)

    async def get_devices(self, user_id: int) -> List[str]:
        return list(self._devices.get(user_id, {}).keys())

    async def mark_online(self, user_id: int) -> None:
        self._presence[user_id] = time.time() + presence_ttl_sec()

    async def is_online(self, user_id: int) -> bool:
        expiry = self._presence.get(user_id)
        return bool(expiry and expiry > time.time())

    async def clear(self) -> None:
        self._devices.clear()
        self._presence.clear()


class RedisPresence:
    async def register_device(self, user_id: int, token: str, platform: Optional[str] = None) -> None:
        client = get_client()
        await client.sadd(_devices_key(user_id), token)
        await client.expire(_devices_key(user_id), device_ttl_sec())

    async def unregister_device(self, user_id: int, token: str) -> None:
        await get_client().srem(_devices_key(user_id), token)

    async def get_devices(self, user_id: int) -> List[str]:
        return list(await get_client().smembers(_devices_key(user_id)))

    async def mark_online(self, user_id: int) -> None:
        await get_client().set(_presence_key(user_id), "1", ex=presence_ttl_sec())

    async def is_online(self, user_id: int) -> bool:
        return bool(await get_client().exists(_presence_key(user_id)))

    async def clear(self) -> None:
        client = get_client()
        for pattern in ("voip:devices:*", "voip:presence:*"):
            async for key in client.scan_iter(pattern):
                await client.delete(key)


_inmem_presence = InMemoryPresence()
_redis_presence = RedisPresence()


def get_presence():
    return _redis_presence if is_redis_enabled() else _inmem_presence
