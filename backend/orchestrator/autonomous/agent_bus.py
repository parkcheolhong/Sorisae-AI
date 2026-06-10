"""에이전트 간 메시지 교환 버스 (Redis Pub/Sub 기반)"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    from_agent: str
    to_agent: str
    msg_type: str  # request, response, review, revision, broadcast
    content: str
    run_id: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AgentMessageBus:
    """에이전트 간 메시지 라우팅.

    Redis가 사용 가능하면 Pub/Sub, 아니면 인메모리 큐 사용.
    """

    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable]] = {}
        self._message_log: List[AgentMessage] = []
        self._redis = None

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            return None
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            await self._redis.ping()
            return self._redis
        except Exception as exc:
            logger.debug("Redis unavailable for agent bus: %s", exc)
            self._redis = None
            return None

    async def send(self, message: AgentMessage) -> None:
        self._message_log.append(message)
        redis_client = await self._get_redis()
        if redis_client:
            try:
                channel = f"agent:{message.to_agent}"
                await redis_client.publish(channel, json.dumps(message.to_dict(), ensure_ascii=False))
            except Exception as exc:
                logger.debug("Redis publish failed: %s", exc)

        notified: set = set()
        for callback in self._listeners.get(message.to_agent, []):
            cb_id = id(callback)
            if cb_id in notified:
                continue
            notified.add(cb_id)
            try:
                result = callback(message)
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:
                logger.warning("Agent listener error: %s", exc)

        if message.to_agent != "*":
            for callback in self._listeners.get("*", []):
                cb_id = id(callback)
                if cb_id in notified:
                    continue
                notified.add(cb_id)
                try:
                    result = callback(message)
                    if hasattr(result, "__await__"):
                        await result
                except Exception as exc:
                    logger.warning("Broadcast listener error: %s", exc)

    async def broadcast(self, from_agent: str, content: str, run_id: str, **kwargs) -> None:
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent="*",
            msg_type="broadcast",
            content=content,
            run_id=run_id,
            **kwargs,
        )
        await self.send(msg)

    def subscribe(self, agent_id: str, callback: Callable) -> None:
        self._listeners.setdefault(agent_id, []).append(callback)

    def get_message_log(self, run_id: str) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._message_log if m.run_id == run_id]

    def clear_run(self, run_id: str) -> None:
        self._message_log = [m for m in self._message_log if m.run_id != run_id]
