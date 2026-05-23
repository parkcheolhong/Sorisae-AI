from __future__ import annotations

import hashlib
import os
import threading
import time
from typing import Any, Dict, List

from fastapi import Request, Response
from fastapi.responses import StreamingResponse

_MARKETPLACE_CATEGORIES_CACHE_TTL_SEC = max(1.0, float(os.getenv("MARKETPLACE_CATEGORIES_CACHE_TTL_SEC", "5")))
_MARKETPLACE_CATEGORIES_CACHE: Dict[str, Any] = {
    "captured_at": 0.0,
    "payload": None,
}
_MARKETPLACE_CATEGORIES_CACHE_LOCK = threading.Lock()
_MARKETPLACE_CATEGORIES_RATE_LIMIT_WINDOW_SEC = max(0.2, float(os.getenv("MARKETPLACE_CATEGORIES_RATE_LIMIT_WINDOW_SEC", "1.0")))
_MARKETPLACE_CATEGORIES_RATE_LIMIT_STATE: Dict[str, float] = {}
_MARKETPLACE_CATEGORIES_RATE_LIMIT_LOCK = threading.Lock()


def _invalidate_marketplace_categories_cache() -> None:
    with _MARKETPLACE_CATEGORIES_CACHE_LOCK:
        _MARKETPLACE_CATEGORIES_CACHE["captured_at"] = 0.0
        _MARKETPLACE_CATEGORIES_CACHE["payload"] = None


def _resolve_marketplace_categories_rate_limit_key(request: Request) -> str:
    forwarded_for = str(request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    client_host = forwarded_for or (request.client.host if request.client else "unknown")
    user_agent = str(request.headers.get("user-agent") or "")
    return f"{client_host}:{hashlib.sha256(user_agent.encode('utf-8')).hexdigest()[:16]}"


def _should_throttle_marketplace_categories(request: Request) -> bool:
    now_ts = time.time()
    rate_limit_key = _resolve_marketplace_categories_rate_limit_key(request)
    with _MARKETPLACE_CATEGORIES_RATE_LIMIT_LOCK:
        last_seen = float(_MARKETPLACE_CATEGORIES_RATE_LIMIT_STATE.get(rate_limit_key) or 0.0)
        _MARKETPLACE_CATEGORIES_RATE_LIMIT_STATE[rate_limit_key] = now_ts
        stale_keys = [
            key
            for key, seen_at in _MARKETPLACE_CATEGORIES_RATE_LIMIT_STATE.items()
            if (now_ts - float(seen_at)) > (_MARKETPLACE_CATEGORIES_RATE_LIMIT_WINDOW_SEC * 20)
        ]
        for stale_key in stale_keys:
            _MARKETPLACE_CATEGORIES_RATE_LIMIT_STATE.pop(stale_key, None)
    return (now_ts - last_seen) < _MARKETPLACE_CATEGORIES_RATE_LIMIT_WINDOW_SEC


def _build_marketplace_categories_degraded_payload(cached_payload: Any = None) -> List[Dict[str, Any]]:
    if isinstance(cached_payload, list):
        return list(cached_payload)
    return []


def _apply_short_marketplace_categories_cache_headers(response: StreamingResponse | Any) -> None:
    ttl = max(1, int(_MARKETPLACE_CATEGORIES_CACHE_TTL_SEC))
    response.headers["Cache-Control"] = f"public, max-age={ttl}, stale-while-revalidate=30"
    response.headers["x-stale-client-mitigation"] = "marketplace-categories-short-cache"


def _apply_marketplace_categories_degraded_headers(response: Response, *, mitigation: str) -> None:
    _apply_short_marketplace_categories_cache_headers(response)
    response.headers["Connection"] = "close"
    response.headers["x-stale-client-mitigation"] = mitigation
    response.headers["x-marketplace-categories-degraded"] = "1"
