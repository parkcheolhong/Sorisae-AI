"""VoIP MCU(media_bridge) 전용 STT/TTS I/O — voice_gateway 직접 import 금지 SSOT.

소리새 friend-chat·face.interpret 경로와 코드 결합을 끊기 위해
media_bridge 는 이 어댑터만 호출한다.
"""
from __future__ import annotations

from typing import Any, Optional

from backend.llm.correlation import FEATURE_IDS


def bridge_synthesize_tts(text: str, lang: str) -> tuple[str, str]:
    from backend.llm.voice_gateway import _synthesize_tts

    return _synthesize_tts(
        text,
        lang,
        feature_id=FEATURE_IDS["voip_voice_relay"],
    )


def bridge_run_faster_whisper(
    wav_bytes: bytes,
    source_lang: str,
    *,
    min_segment_ms: int,
) -> dict[str, Any]:
    from backend.llm.voice_gateway import _run_faster_whisper

    return _run_faster_whisper(
        wav_bytes,
        source_lang,
        None,
        min_segment_ms=min_segment_ms,
    )
