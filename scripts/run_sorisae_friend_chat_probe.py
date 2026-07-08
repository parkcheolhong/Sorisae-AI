#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Iterable


def main(argv: Iterable[str]) -> int:
    parser = argparse.ArgumentParser(description="Probe the Sorisae friend-chat HTTP endpoint.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--text", default="안녕 소리새, 오늘 여행 준비를 도와줘")
    parser.add_argument("--language", default="ko")
    args = parser.parse_args(list(argv))

    base_url = args.base_url.rstrip("/")
    payload = {
        "transcript": args.text,
        "language": args.language,
        "tts": False,
        "web_search": False,
    }
    request = urllib.request.Request(
        f"{base_url}/api/llm/voice/friend-chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"[sorisae-friend-chat-probe] HTTP {exc.code}: {detail}")
        return 1
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[sorisae-friend-chat-probe] failed: {exc}")
        return 1

    if not str(data.get("response_text") or "").strip():
        print("[sorisae-friend-chat-probe] response_text is empty")
        return 1

    print("[sorisae-friend-chat-probe] passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
