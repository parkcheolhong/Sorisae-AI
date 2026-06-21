"""감정 E1 — register(존댓말/어휘) 제어 단위테스트.

핵심: 감정→지시문 매핑(언어 인지), PCM16 디코딩, integration 플래그 게이팅·throw 금지,
중립/저신뢰 no-op(기존 MT 동작 보존).
"""

import struct

import pytest  # pyright: ignore[reportMissingImports]

from backend.communication.emotion.models import EmotionEstimate, EmotionLabel
from backend.communication.emotion.register import (
    register_directive_from_emotion,
    compose_hint,
)
from backend.communication.emotion.audio import pcm16_samples_from_bytes
from backend.communication.emotion import integration as ser_integration


def _est(label: EmotionLabel, conf: float, arousal=0.7, valence=0.3) -> EmotionEstimate:
    return EmotionEstimate(label=label, arousal=arousal, valence=valence, confidence=conf)


def test_directive_angry_korean_uses_honorific():
    d = register_directive_from_emotion(_est(EmotionLabel.ANGRY, 0.8), target_lang="ko")
    assert d is not None and "감정 인지 어조" in d
    assert "존댓말" in d


def test_directive_angry_english_uses_tone_only():
    d = register_directive_from_emotion(_est(EmotionLabel.ANGRY, 0.8), target_lang="en")
    assert d is not None and "de-escalating" in d.lower()


def test_directive_neutral_returns_none():
    assert register_directive_from_emotion(_est(EmotionLabel.NEUTRAL, 0.9), target_lang="ko") is None


def test_directive_low_confidence_returns_none():
    assert register_directive_from_emotion(
        _est(EmotionLabel.ANGRY, 0.3), target_lang="ko", min_confidence=0.5) is None


def test_directive_none_estimate_returns_none():
    assert register_directive_from_emotion(None, target_lang="ko") is None


def test_compose_hint_skips_none_and_empty():
    assert compose_hint(None, "", "  ") is None
    assert compose_hint("a", None, "b") == "a b"
    assert compose_hint(None, "only") == "only"


def test_pcm16_decode_riff_and_raw():
    raw = struct.pack("<4h", 100, -100, 200, -200)
    assert pcm16_samples_from_bytes(raw) == [100, -100, 200, -200]
    riff = b"RIFF" + b"\x00" * 40 + raw  # 44-byte header then PCM
    assert pcm16_samples_from_bytes(riff) == [100, -100, 200, -200]
    assert pcm16_samples_from_bytes(b"") == []
    assert pcm16_samples_from_bytes(b"\x01") == []


def _square_pcm16(n: int = 16000) -> bytes:
    # 교번 최대진폭 → 높은 arousal·낮은 valence(ANGRY) + 충분 신뢰도.
    samples = [32767 if i % 2 == 0 else -32768 for i in range(n)]
    return struct.pack("<" + "h" * n, *samples)


def test_register_integration_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("COMM_V2_EMOTION_REGISTER", raising=False)
    ser_integration.reset_for_test()
    assert ser_integration.build_register_hint_from_pcm16(_square_pcm16(), target_lang="ko") is None
    ser_integration.reset_for_test()


def test_register_integration_emits_directive_when_enabled(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_REGISTER", "true")
    ser_integration.reset_for_test()
    try:
        hint = ser_integration.build_register_hint_from_pcm16(_square_pcm16(), target_lang="ko")
        assert hint is not None and "감정 인지 어조" in hint
    finally:
        ser_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_EMOTION_REGISTER", raising=False)
        ser_integration.reset_for_test()


def test_register_integration_independent_of_ser_telemetry_flag(monkeypatch):
    # SER 텔레메트리는 꺼져 있어도 register만 켜면 동작해야 한다(독립 opt-in).
    monkeypatch.delenv("COMM_V2_EMOTION_SER", raising=False)
    monkeypatch.setenv("COMM_V2_EMOTION_REGISTER", "true")
    ser_integration.reset_for_test()
    try:
        assert ser_integration.estimate_from_samples([0.9] * 16000) is None  # 텔레메트리 off
        hint = ser_integration.build_register_hint_from_pcm16(_square_pcm16(), target_lang="ko")
        assert hint is not None
    finally:
        ser_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_EMOTION_REGISTER", raising=False)
        ser_integration.reset_for_test()


def test_register_integration_never_throws(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_REGISTER", "true")
    ser_integration.reset_for_test()
    try:
        assert ser_integration.build_register_hint_from_pcm16(None, target_lang="ko") is None
        assert ser_integration.build_register_hint_from_pcm16(b"\x01", target_lang="ko") is None
    finally:
        ser_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_EMOTION_REGISTER", raising=False)
        ser_integration.reset_for_test()
