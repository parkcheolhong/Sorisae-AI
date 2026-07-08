#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SNIPPETS: Dict[str, List[str]] = {
    "backend/llm/voice_gateway.py": [
        '@router.post("/voice/friend-chat"',
        "_friend_system_prompt",
        "_friend_fetch_grounding",
        "_friend_is_noise_or_hallucination",
        "_sanitize_friend_reply_for_speech",
        "BUT do NOT fabricate specific local facts",
        "never switch languages or translate",
        "VOICE_FRIEND_MAPS_GROUNDING",
    ],
    "apps/mobile-nadotongryoksa/src/features/sorisae/companionVoiceCall.ts": [
        "COMPANION_VOICE_CALL_IDLE_MS = 180_000",
        "matchCompanionWakeWord",
        "sleepCompanionVoiceCall",
        "companionVoiceCallRemainingMs",
    ],
    "apps/mobile-nadotongryoksa/src/features/sorisae/sorisaeEcho.ts": [
        "normalizeEchoText",
        "echoOverlapRatio",
    ],
}


def main() -> int:
    violations: List[str] = []

    for rel_path, snippets in sorted(REQUIRED_SNIPPETS.items()):
        path = REPO_ROOT / rel_path
        if not path.is_file():
            violations.append(f"{rel_path}: file is missing")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in snippets:
            if snippet not in text:
                violations.append(f"{rel_path}: missing regression lock {snippet!r}")

    if violations:
        print("[sorisae-regression-lock] blocked:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("[sorisae-regression-lock] passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
