from __future__ import annotations

try:
    from datetime import datetime, UTC
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc


def create_order(payload: dict | None = None) -> dict:
    request = dict(payload or {})
    return {
        "order_id": request.get("order_id") or "simulated-order",
        "status": request.get("status") or "queued",
        "created_at": datetime.now(UTC).isoformat(),
        "payload": request,
    }