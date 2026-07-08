"""VoIP 50-language locale coverage tests."""

from __future__ import annotations

import re
from pathlib import Path

from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES
from backend.voip_language_locales import (
    EDGE_TTS_NEURAL_VOICES,
    MOBILE_TTS_LOCALES,
    resolve_edge_tts_voice,
    resolve_whisper_language_hint,
    resolve_whisper_initial_prompt,
)

# G6: 모바일 클라이언트 로케일 SSOT 파일(실제 .ts)과 백엔드 SUPPORTED_LANGUAGES 의
# 자동 동기화 가드. 두 SSOT 가 드리프트하면 이 테스트가 실패해 CI 에서 즉시 잡는다.
_MOBILE_LOCALES_TS = (
    Path(__file__).resolve().parents[2]
    / "apps" / "mobile-nadotongryoksa" / "src" / "constants" / "voipLanguageLocales.ts"
)


def _mobile_ts_locale_codes() -> set[str]:
    text = _MOBILE_LOCALES_TS.read_text(encoding="utf-8")
    return set(re.findall(r"^\s+'?([a-z]{2,3}(?:-[a-z]+)?)'?: '", text, re.M))


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


def test_mobile_ts_locale_ssot_matches_backend():
    """G6: 모바일 voipLanguageLocales.ts ↔ 백엔드 SUPPORTED_LANGUAGES 동기화 가드."""
    assert _MOBILE_LOCALES_TS.exists(), f"missing mobile locale SSOT: {_MOBILE_LOCALES_TS}"
    mobile_codes = _mobile_ts_locale_codes()
    backend_codes = set(SUPPORTED_LANGUAGES)
    missing_in_mobile = sorted(backend_codes - mobile_codes)
    extra_in_mobile = sorted(mobile_codes - backend_codes)
    assert not missing_in_mobile, f"mobile TS missing codes vs backend: {missing_in_mobile}"
    assert not extra_in_mobile, f"mobile TS has extra codes vs backend: {extra_in_mobile}"
