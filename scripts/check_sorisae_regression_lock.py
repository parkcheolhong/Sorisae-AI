#!/usr/bin/env python3
"""소리새 경로 회귀 잠금 — 금지 패턴이 다시 들어오면 CI FAIL."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN: list[tuple[str, str]] = [
    (
        "apps/mobile-nadotongryoksa/src/features/sorisae/useVoiceCaptureLoop.ts",
        r"skipSilentForSorisaeWindow",
    ),
    (
        "apps/mobile-nadotongryoksa/src/features/sorisae/useSorisaeVoicePipeline.ts",
        r"sorisaeWindowMicBootstrappedRef\.current = true[\s\S]{0,1500}void startVoiceInput\(",
    ),
    (
        "backend/llm/voice_gateway.py",
        r"voice_input\.bin",
    ),
]

REQUIRED_SNIPPETS: list[tuple[str, str]] = [
    (
        "backend/llm/voice_gateway.py",
        "_guess_audio_input_suffix",
    ),
    (
        "backend/llm/voice_gateway.py",
        "_friend_chat_dedicated_instance",
    ),
    (
        "apps/mobile-nadotongryoksa/src/features/sorisae/useSorisaeVoicePipeline.ts",
        "sorisaeWindowMicBootstrappedRef",
    ),
    (
        "apps/mobile-nadotongryoksa/src/features/sorisae/useVoiceCaptureLoop.ts",
        "shouldDeferSorisaeSegmentStop",
    ),
    (
        "apps/mobile-nadotongryoksa/src/features/sorisae/useVoiceCaptureLoop.ts",
        "silero_speech_end_sorisae",
    ),
]


def main() -> int:
    errors: list[str] = []
    for rel, pattern in FORBIDDEN:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing file: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(pattern, text):
            errors.append(f"forbidden pattern in {rel}: {pattern}")

    for rel, snippet in REQUIRED_SNIPPETS:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing file: {rel}")
            continue
        if snippet not in path.read_text(encoding="utf-8"):
            errors.append(f"required SSOT missing in {rel}: {snippet!r}")

    if errors:
        print("[FAIL] sorisae regression lock")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("[PASS] sorisae regression lock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
