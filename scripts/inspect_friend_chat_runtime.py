#!/usr/bin/env python3
"""Inspect Sorisae friend-chat runtime diagnostics from backend API.

Usage:
  python scripts/inspect_friend_chat_runtime.py --base-url http://127.0.0.1:8000 --token <JWT>
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect /api/llm/voice/friend-chat/diagnostics")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--token", default="", help="Bearer token for protected endpoint")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    url = f"{base_url}/api/llm/voice/friend-chat/diagnostics"

    req = urllib.request.Request(url)
    if args.token.strip():
        req.add_header("Authorization", f"Bearer {args.token.strip()}")

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            payload = response.read().decode("utf-8", errors="replace")
            data = json.loads(payload)
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code} {exc.reason}")
        if body:
            print(body)
        if exc.code in (401, 403):
            print("Hint: pass --token with a valid admin/staff JWT.")
        return 1
    except urllib.error.URLError as exc:
        print(f"Connection error: {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON response: {exc}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
