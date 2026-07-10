"""VoIP 섹션 Edge TTS 운율 SSOT — 소리새(face.interpret)와 분리.

media_bridge·voip.* feature_id 경로만 이 모듈을 사용한다.
소리새 +18% 는 backend.llm.voice_gateway 의 face.* 분기에서만 로드.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

from backend.marketplace.worldlinco_section_freeze import frozen_voip_edge_tts_prosody_ko_default

ProsodyTriple = Tuple[str, str, str]

VOICE_EDGE_TTS_PRESET = (os.getenv("VOICE_EDGE_TTS_PRESET", "actress_soft") or "actress_soft").strip().lower()


def _lang2(target_lang: Optional[str]) -> str:
    raw = str(target_lang or "ko").strip().lower().replace("_", "-")
    if raw.startswith("zh"):
        return "zh-tw" if "tw" in raw or "hant" in raw else "zh"
    return raw.split("-")[0] or "ko"


def resolve_voip_edge_tts_prosody(target_lang: Optional[str]) -> ProsodyTriple:
    """VoIP·브리지·릴레이 기본 운율 (+6% freeze). face.interpret 금지."""
    lang = _lang2(target_lang)
    preset = VOICE_EDGE_TTS_PRESET
    if preset == "flat":
        return ("-6%", "+0%", "+0Hz")
    if preset == "actress_soft":
        if lang in {"ko", "ja"}:
            return frozen_voip_edge_tts_prosody_ko_default()
        return ("+4%", "+6%", "+1Hz")
    if preset == "actress_clear":
        if lang in {"ko", "ja"}:
            return ("+5%", "+10%", "+3Hz")
        return ("+8%", "+8%", "+2Hz")
    return ("-6%", "+0%", "+0Hz")
