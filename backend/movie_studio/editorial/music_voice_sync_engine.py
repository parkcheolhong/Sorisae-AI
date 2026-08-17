from __future__ import annotations

from typing import Dict


def build_music_voice_sync(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "voice_track": str(payload.get("voice_track") or "voice-over").strip() or "voice-over",
        "music_track": str(payload.get("music_track") or "score").strip() or "score",
        "rules": [
            "dialogue must remain intelligible",
            "music emphasis must not break CTA readability",
        ],
    }
