from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.admin.sorisae_failure_monitor_service import push_sorisae_failure_to_admins


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch Sorisae smoke failure push notifications to admin accounts.")
    parser.add_argument("--result-json-path", required=True, help="Path to smoke_result.json")
    args = parser.parse_args()

    result_path = Path(args.result_json_path).expanduser().resolve()
    if not result_path.exists():
        print(json.dumps({"error": f"result json not found: {result_path}"}, ensure_ascii=False))
        return 1

    try:
        payload = asyncio.run(push_sorisae_failure_to_admins(result_path))
    except Exception as exc:  # noqa: BLE001
        payload = {
            "attempted": False,
            "success": False,
            "classification": "unknown",
            "admin_user_count": 0,
            "success_user_count": 0,
            "failure_user_count": 0,
            "skipped_reason": "helper_exception",
            "error": str(exc),
        }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
