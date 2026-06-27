#!/usr/bin/env python3
"""Admin system-settings integration probe for Windows/local Docker."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.admin_router import _build_admin_integration_checks, _build_admin_system_settings_payload  # noqa: E402


def probe_http(url: str) -> dict:
    try:
        with urlopen(url, timeout=8) as response:
            return {"ok": 200 <= int(response.status) < 400, "status": int(response.status), "url": url}
    except URLError as exc:
        return {"ok": False, "status": None, "url": url, "error": str(exc.reason)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "status": None, "url": url, "error": str(exc)}


def main() -> int:
    api_base = os.getenv("LOCAL_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    checks = {
        "health": probe_http(f"{api_base}/api/health"),
        "swagger_docs": probe_http(f"{api_base}/docs"),
        "openapi_json": probe_http(f"{api_base}/openapi.json"),
    }

    payload = _build_admin_system_settings_payload()
    integration = payload.get("integration_checks") or {}
    report = {
        "api_base": api_base,
        "direct_probes": checks,
        "integration_checks": integration,
        "summary": payload.get("summary"),
        "empty_field_count": payload.get("empty_field_count"),
        "recommended_env_updates_count": len(payload.get("recommended_env_updates") or {}),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    direct_ok = all(item.get("ok") for item in checks.values())
    integration_ok = bool(integration.get("all_connected"))
    return 0 if direct_ok and integration_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
