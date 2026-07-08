"""소리새 friend-chat SSOT 회귀 게이트 — CI 필수.

보호 대상:
- m4a ffmpeg 정규화 (_run_faster_whisper 진입)
- 무음/환각 422 (400 STT 실패 아님)
- 짧은 한국어 발화 low-trust 완화
- 180자 초과 Whisper 환각 차단
"""
from __future__ import annotations

import struct
import wave
from io import BytesIO
from pathlib import Path

import pytest

from backend.llm.voice_gateway import (
    _friend_accept_despite_low_stt_trust,
    _friend_is_noise_or_hallucination,
    _friend_is_tourism_guide_query,
    _normalize_friend_reply_output_language,
    _resolve_friend_reply_language,
    _resolve_friend_reply_budget,
    _trim_friend_reply_for_speed,
    _guess_audio_input_suffix,
    _normalize_voice_audio_bytes,
    _voice_stt_exc_http_status,
)


def _minimal_wav(duration_sec: float = 3.0, amplitude: int = 8000) -> bytes:
    sr = 16000
    n = int(sr * duration_sec)
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            v = amplitude if (i // 200) % 2 == 0 else -amplitude
            frames.extend(struct.pack("<h", v))
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def test_guess_audio_suffix_m4a_and_wav():
    assert _guess_audio_input_suffix(b"RIFFxxxx") == ".wav"
    assert _guess_audio_input_suffix(b"\x00\x00\x00\x18ftypM4A ") == ".m4a"


def test_normalize_rejects_too_short_wav():
    short = _minimal_wav(0.5, 0)
    with pytest.raises(RuntimeError, match="너무 짧습니다|음성이 감지되지 않았습니다"):
        _normalize_voice_audio_bytes(short)


def test_voice_stt_exc_http_status_maps_silent_to_422():
    assert _voice_stt_exc_http_status("음성이 감지되지 않았습니다. 다시 말씀해 주세요.") == 422
    assert _voice_stt_exc_http_status("STT 실패: boom") == 400


def test_friend_noise_rejects_whisper_hallucination_length():
    long_garbage = " ".join(["감사합니다"] * 80)
    assert _friend_is_noise_or_hallucination(long_garbage) is True
    assert _friend_is_noise_or_hallucination("춘천 맛집 알려줘") is False


def test_friend_accept_korean_short_despite_low_trust():
    assert _friend_accept_despite_low_stt_trust(
        "춘천 맛집 추천해줘",
        "ko",
        0.98,
        "low",
    ) is True
    assert _friend_accept_despite_low_stt_trust(
        "춘천 맛집 추천해줘",
        "nn",
        0.45,
        "low",
    ) is True
    assert _friend_accept_despite_low_stt_trust(
        "x",
        "nn",
        0.3,
        "low",
    ) is False


def test_tourism_guide_budget_tier3_not_one_liner():
    budget = _resolve_friend_reply_budget(
        "춘천 역사 탐방이랑 맛집 숙소 소개해줘",
        {"tourism_guide_tier": 3, "friend_reply_max_tokens": 360, "friend_realtime_max_tokens": 280},
    )
    assert budget["is_guide_query"] is True
    assert int(budget["max_len_ko"]) >= 800
    sample = (
        "춘천은 호수와 산세가 어우러진 도시야. "
        "닭갈비와 막국수가 대표 음식이고, 구봉순대도 유명해. "
        "소양강 스카이워크와 남이섬은 역사·자연을 함께 즐기기 좋아. "
        "숙소는 시내 중심이나 소양강 근처가 동선이 편해."
    )
    trimmed = _trim_friend_reply_for_speed(sample, "ko", "춘천 역사 탐방이랑 맛집 숙소 소개해줘")
    assert len(trimmed) >= 80


def test_friend_reply_output_language_normalizes_residual_hangul_for_japanese(monkeypatch: pytest.MonkeyPatch):
    class _FakeTranslator:
        def translate(self, text: str, from_lang: str = "ko", to_lang: str = "ja", **_: object) -> str:
            assert text == "안녕하세요 반가워요"
            assert from_lang == "ko"
            assert to_lang == "ja"
            return "こんにちは、うれしいよ"

    class _FakeTranslatorFacade:
        @staticmethod
        def get_instance() -> _FakeTranslator:
            return _FakeTranslator()

    monkeypatch.setattr(
        "backend.services.nadotongryoksa.translator.NadoTranslator",
        _FakeTranslatorFacade,
    )

    normalized = _normalize_friend_reply_output_language("안녕하세요 반가워요", "ja")
    assert normalized == "こんにちは、うれしいよ"


def test_friend_reply_language_stays_on_profile_language_when_designated():
    resolved = _resolve_friend_reply_language(
        profile_language="ja",
        detected_language="ko",
        language_probability=0.99,
        transcript="안녕하세요",
        min_lang_prob=0.60,
    )
    assert resolved == "ja"


@pytest.mark.skipif(
    not Path("/usr/bin/ffmpeg").exists() and not __import__("shutil").which("ffmpeg"),
    reason="ffmpeg not available",
)
def test_m4a_bytes_normalize_to_wav():
    try:
        __import__("faster_whisper")
    except Exception as exc:
        pytest.skip(f"faster_whisper unavailable in this environment: {exc}")
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        wav_in = Path(temp_dir) / "in.wav"
        m4a_out = Path(temp_dir) / "out.m4a"
        wav_in.write_bytes(_minimal_wav(3.0))
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_in), "-c:a", "aac", "-b:a", "64k", str(m4a_out)],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if proc.returncode != 0:
            pytest.skip("ffmpeg m4a encode unavailable in CI")
        normalized = _normalize_voice_audio_bytes(m4a_out.read_bytes())
        assert normalized[:4] == b"RIFF"
        assert len(normalized) > 5000
