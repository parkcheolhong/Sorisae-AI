"""Regression tests for mobile voice-translate STT helpers."""

from __future__ import annotations

import pytest

from backend.llm.voice_gateway import (
    VOICE_RELAY_MIN_SEGMENT_MS,
    _assert_min_voice_capture_duration,
    _assert_min_voice_energy,
    _normalize_voice_audio_bytes,
    _normalize_whisper_language_hint,
    _pcm16_mono_duration_ms,
    _pcm16_mono_rms_db,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ko", "ko"),
        ("KO", "ko"),
        ("zh-tw", "zh"),
        ("auto", None),
        ("", None),
        (None, None),
        ("xx", None),
    ],
)
def test_normalize_whisper_language_hint(raw, expected):
    assert _normalize_whisper_language_hint(raw) == expected


def test_normalize_voice_audio_bytes_rejects_empty():
    with pytest.raises(RuntimeError, match="비어"):
        _normalize_voice_audio_bytes(b"")


def _make_synthetic_wav(duration_ms: float, amplitude: int = 0) -> bytes:
    pcm_len = int(16_000 * 2 * (duration_ms / 1000.0))
    if amplitude <= 0:
        pcm = b"\x00" * pcm_len
    else:
        import struct

        sample_count = pcm_len // 2
        pcm = struct.pack("<" + "h" * sample_count, *([amplitude] * sample_count))
    return b"RIFF" + (b"\x00" * 40) + pcm


def test_assert_min_voice_energy_rejects_silent_segments():
    silent_wav = _make_synthetic_wav(3000, amplitude=0)
    with pytest.raises(RuntimeError, match="감지되지 않았습니다"):
        _assert_min_voice_energy(silent_wav)


def test_assert_min_voice_energy_accepts_speech_like_segments():
    loud_wav = _make_synthetic_wav(3000, amplitude=4000)
    _assert_min_voice_energy(loud_wav)


def test_pcm16_mono_rms_db_estimates_amplitude():
    loud_wav = _make_synthetic_wav(1000, amplitude=4000)
    assert _pcm16_mono_rms_db(loud_wav) > -40.0


def test_pcm16_mono_duration_ms_estimates_payload():
    wav = _make_synthetic_wav(3000)
    assert _pcm16_mono_duration_ms(wav) == pytest.approx(3000.0, rel=0.01)


def test_assert_min_voice_capture_duration_rejects_short_segments():
    short_wav = _make_synthetic_wav(VOICE_RELAY_MIN_SEGMENT_MS - 500)
    with pytest.raises(RuntimeError, match="너무 짧습니다"):
        _assert_min_voice_capture_duration(short_wav)


def test_assert_min_voice_capture_duration_accepts_tolerance_band():
    borderline_wav = _make_synthetic_wav(VOICE_RELAY_MIN_SEGMENT_MS - 150)
    _assert_min_voice_capture_duration(borderline_wav)


def test_assert_min_voice_capture_duration_accepts_aligned_segments():
    long_wav = _make_synthetic_wav(VOICE_RELAY_MIN_SEGMENT_MS + 200)
    _assert_min_voice_capture_duration(long_wav)


def test_is_likely_gibberish_relay_transcript_rejects_georgian_spam():
    from backend.llm.router import _is_likely_gibberish_relay_transcript

    georgian = "ლლლლლლლლლლლლლლლლლლლლლლ: ლლლლლლლლლლლლლლლლლლლლლლ:"
    assert _is_likely_gibberish_relay_transcript(georgian, "ko", "en") is True
    assert _is_likely_gibberish_relay_transcript("고맙습니다", "ko", "en") is False
    assert _is_likely_gibberish_relay_transcript("Thank you.", "ko", "en") is False


def test_voice_lang_codes_equivalent():
    from backend.llm.router import _voice_lang_codes_equivalent

    assert _voice_lang_codes_equivalent("ko", "ko") is True
    assert _voice_lang_codes_equivalent("zh-tw", "zh") is True
    assert _voice_lang_codes_equivalent("ko", "ja") is False


def test_resolve_bilingual_route_detected_and_script():
    from backend.llm.router import _resolve_bilingual_route

    assert _resolve_bilingual_route(
        detected_language="ko",
        transcript="안녕하세요",
        lang_a="ko",
        lang_b="ja",
    ) == ("ko", "ja")
    assert _resolve_bilingual_route(
        detected_language="ja",
        transcript="こんにちは",
        lang_a="ko",
        lang_b="ja",
    ) == ("ja", "ko")
    assert _resolve_bilingual_route(
        detected_language=None,
        transcript="Thank you very much",
        lang_a="ko",
        lang_b="en",
    ) == ("en", "ko")
    assert _resolve_bilingual_route(
        detected_language="fr",
        transcript="bonjour",
        lang_a="ko",
        lang_b="ja",
    ) is None


def test_golden_voice_translate_bilingual_smoke():
    from unittest.mock import patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.llm.router import router as llm_router

    class _FakeJaTranslator:
        def translate(self, text: str, *, from_lang: str, to_lang: str, region_hint=None) -> str:
            return "こんにちは"

    app = FastAPI()
    app.include_router(llm_router)
    client = TestClient(app)

    with patch(
        "backend.services.nadotongryoksa.translator.NadoTranslator.get_instance",
        return_value=_FakeJaTranslator(),
    ):
        response = client.post(
            "/api/llm/voice-translate",
            json={
                "transcript": "안녕하세요",
                "bilingual_mode": True,
                "lang_a": "ko",
                "lang_b": "ja",
                "from_lang": "ko",
                "to_lang": "ja",
            },
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("from") == "ko"
    assert payload.get("to") == "ja"
    assert payload.get("translated") == "こんにちは"


def test_voice_translate_device_tts_skips_server_synthesis():
    from unittest.mock import patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.llm.router import router as llm_router

    class _FakeTranslator:
        def translate(self, text: str, *, from_lang: str, to_lang: str, region_hint=None) -> str:
            return "hello"

    app = FastAPI()
    app.include_router(llm_router)
    client = TestClient(app)

    with patch(
        "backend.services.nadotongryoksa.translator.NadoTranslator.get_instance",
        return_value=_FakeTranslator(),
    ), patch(
        "backend.llm.router._synthesize_tts",
        side_effect=AssertionError("server TTS should be skipped"),
    ):
        response = client.post(
            "/api/llm/voice-translate",
            json={
                "transcript": "안녕",
                "from_lang": "ko",
                "to_lang": "en",
                "device_tts": True,
            },
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("tts_delivery") == "device_speech"
    assert payload.get("audio_base64") is None


def test_transcribe_mobile_voice_audio_prefers_source_lang_hint(monkeypatch):
    from backend.llm import router as llm_router

    attempts: list[str | None] = []

    def fake_whisper(_audio, language, _prompt):
        attempts.append(language)
        if language == "ko":
            return {
                "transcript": "안녕하세요",
                "detected_language": "ko",
                "avg_logprob": -0.2,
                "max_no_speech_prob": 0.1,
                "stt_trust": "high",
            }
        return {
            "transcript": "hello",
            "detected_language": "en",
            "avg_logprob": -0.2,
            "max_no_speech_prob": 0.1,
            "stt_trust": "high",
        }

    monkeypatch.setattr(
        "backend.llm.voice_gateway._run_faster_whisper",
        fake_whisper,
    )
    monkeypatch.setattr(
        "backend.llm.voice_gateway._normalize_voice_audio_bytes",
        lambda payload: payload,
    )
    monkeypatch.setattr(
        "backend.llm.voice_gateway._resolve_whisper_initial_prompt",
        lambda _lang: None,
    )

    transcript, detected, _meta = llm_router._transcribe_mobile_voice_audio(b"audio", "auto", "ko")

    assert transcript == "안녕하세요"
    assert detected == "ko"
    assert attempts[0] == "ko"


def test_classify_voice_relay_stt_trust_rejects_low_confidence():
    from backend.llm.voice_gateway import classify_voice_relay_stt_trust

    assert classify_voice_relay_stt_trust("hello", -1.4, 0.2) == "low"
    assert classify_voice_relay_stt_trust("hello", -0.3, 0.8) == "low"
    assert classify_voice_relay_stt_trust("hello", -0.3, 0.2) == "high"
