from __future__ import annotations

try:
    from datetime import datetime, UTC
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

from backend.app.external_adapters.status_client import fetch_upstream_status


def get_health_payload() -> dict:
    upstream = fetch_upstream_status()
    return {
        "status": "ok",
        "service": "customer-order-generator",
        "checked_at": datetime.now(UTC).isoformat(),
        "provider_status": upstream,
    }