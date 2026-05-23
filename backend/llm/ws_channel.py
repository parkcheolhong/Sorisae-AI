import asyncio
import logging
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketProgressChannel:
    def __init__(self):
        self._connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self._connections.discard(websocket)

    async def publish(self, event_type: str, payload: Dict[str, Any]):
        if not self._connections:
            return

        message = {"event": event_type, **payload}
        stale_connections = []
        for websocket in list(self._connections):
            try:
                await websocket.send_json(message)
            except Exception as exc:
                logger.warning("[WARN] websocket publish failed: %s", exc)
                stale_connections.append(websocket)

        for websocket in stale_connections:
            self.disconnect(websocket)

    def publish_sync(self, event_type: str, payload: Dict[str, Any]):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("[DEBUG] websocket publish skipped: no running loop")
            return

        loop.create_task(self.publish(event_type, payload))


ws_channel = WebSocketProgressChannel()
