#!/usr/bin/env python3
"""Edge neural TTS — stdout에 MP3 바이트 출력 (VOICE_TTS_COMMAND용).

Usage:
  python scripts/edge_tts_speak.py "안녕하세요, 오케스트레이터입니다."
  echo "..." | python scripts/edge_tts_speak.py -
"""
from __future__ import annotations

import asyncio
import os
import sys


async def _synthesize(text: str) -> bytes:
    import edge_tts

    voice = os.getenv("VOICE_EDGE_TTS_VOICE", "ko-KR-SunHiNeural").strip()
    rate = os.getenv("VOICE_EDGE_TTS_RATE", "-6%").strip() or "-6%"
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


def main() -> int:
    arg = " ".join(sys.argv[1:]).strip()
    if arg == "-":
        text = sys.stdin.read().strip()
    else:
        text = arg
    if not text:
        print("usage: edge_tts_speak.py <text|-", file=sys.stderr)
        return 2
    audio = asyncio.run(_synthesize(text))
    if not audio:
        print("edge-tts produced no audio", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(audio)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
