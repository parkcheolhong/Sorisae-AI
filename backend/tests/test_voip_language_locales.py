"""VoIP 50-language locale coverage tests."""

from __future__ import annotations

from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES
from backend.voip_language_locales import (
    EDGE_TTS_NEURAL_VOICES,
    MOBILE_TTS_LOCALES,
    resolve_edge_tts_voice,
    resolve_whisper_language_hint,
    resolve_whisper_initial_prompt,
)


def test_all_supported_languages_have_mobile_and_edge_locales():
    assert len(SUPPORTED_LANGUAGES) == 50
    assert set(MOBILE_TTS_LOCALES) == set(SUPPORTED_LANGUAGES)
    assert set(EDGE_TTS_NEURAL_VOICES) == set(SUPPORTED_LANGUAGES)


def test_whisper_hint_covers_all_supported_languages():
    for code in SUPPORTED_LANGUAGES:
        assert resolve_whisper_language_hint(code) is not None


def test_whisper_special_remaps():
    assert resolve_whisper_language_hint("zh-tw") == "zh"
    assert resolve_whisper_language_hint("fil") == "tl"


def test_edge_tts_voice_per_target_lang():
    assert resolve_edge_tts_voice("ja").startswith("ja-JP-")
    assert resolve_edge_tts_voice("uk").startswith("uk-UA-")
    assert resolve_edge_tts_voice("ko").endswith("Neural")


def test_whisper_initial_prompt_non_empty_for_all():
    for code in SUPPORTED_LANGUAGES:
        assert resolve_whisper_initial_prompt(code).strip()
