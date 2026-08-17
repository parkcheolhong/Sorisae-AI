from __future__ import annotations

try:
    from datetime import datetime, UTC
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc


def issue_token(payload: dict | None = None) -> dict:
    subject = str((payload or {}).get("subject") or "system-orchestrator")
    return {
        "access_token": f"stub-token-for-{subject}",
        "token_type": "bearer",
        "issued_at": datetime.now(UTC).isoformat(),
    }


def validate_token(payload: dict | None = None) -> dict:
    token = str((payload or {}).get("token") or "").strip()
    return {
        "valid": bool(token),
        "token": token,
    }