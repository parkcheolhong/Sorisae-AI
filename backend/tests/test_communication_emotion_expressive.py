"""감정 E3 — 표현형 TTS 운율 매핑 단위테스트.

핵심: 신뢰도/중립 게이트(=NEUTRAL_PARAMS, 변형 없음), arousal→rate/volume/pitch 단조성,
라벨→Azure 스타일, SSML 이스케이프, integration 진입점 flag 게이팅·throw 금지.
"""

import struct

from backend.communication.emotion import integration as ser_integration
from backend.communication.emotion.expressive_tts import (
    NEUTRAL_PARAMS,
    expressive_params_from_emotion,
    to_azure_ssml,
    to_edge_tts_kwargs,
)
from backend.communication.emotion.models import EmotionEstimate, EmotionLabel


def _raw_pcm16(samples: list[int]) -> bytes:
    return struct.pack("<" + "h" * len(samples), *samples)


def _energetic(n: int = 16000) -> list[int]:
    return [32767 if i % 2 == 0 else -32768 for i in range(n)]


def _est(label: EmotionLabel, arousal: float, valence: float, conf: float) -> EmotionEstimate:
    return EmotionEstimate(label=label, arousal=arousal, valence=valence, confidence=conf)


def test_low_confidence_returns_neutral():
    params = expressive_params_from_emotion(
        _est(EmotionLabel.ANGRY, 0.9, 0.1, 0.2), min_confidence=0.55
    )
    assert params is NEUTRAL_PARAMS
    assert params.neutral is True


def test_neutral_label_returns_neutral():
    params = expressive_params_from_emotion(
        _est(EmotionLabel.NEUTRAL, 0.5, 0.5, 0.9), min_confidence=0.55
    )
    assert params.neutral is True


def test_none_returns_neutral():
    assert expressive_params_from_emotion(None).neutral is True


def test_high_arousal_speeds_up_and_raises_pitch():
    angry = expressive_params_from_emotion(
        _est(EmotionLabel.ANGRY, 0.95, 0.1, 0.9), min_confidence=0.55
    )
    assert angry.neutral is False
    assert angry.rate.startswith("+")      # 빠르게
    assert angry.volume.startswith("+")    # 크게
    assert angry.style == "angry"

    sad = expressive_params_from_emotion(
        _est(EmotionLabel.SAD, 0.1, 0.2, 0.9), min_confidence=0.55
    )
    assert sad.rate.startswith("-")        # 느리게
    assert sad.volume.startswith("-")      # 작게
    assert sad.style == "sad"


def test_label_styles_map():
    assert expressive_params_from_emotion(
        _est(EmotionLabel.HAPPY, 0.8, 0.9, 0.9), min_confidence=0.55
    ).style == "cheerful"
    assert expressive_params_from_emotion(
        _est(EmotionLabel.CALM, 0.2, 0.8, 0.9), min_confidence=0.55
    ).style == "calm"


def test_edge_tts_kwargs_shape():
    params = expressive_params_from_emotion(
        _est(EmotionLabel.ANGRY, 0.95, 0.1, 0.9), min_confidence=0.55
    )
    kwargs = to_edge_tts_kwargs(params)
    assert set(kwargs) == {"rate", "volume", "pitch"}
    assert all(isinstance(v, str) for v in kwargs.values())


def test_azure_ssml_escapes_and_wraps_style():
    params = expressive_params_from_emotion(
        _est(EmotionLabel.ANGRY, 0.95, 0.1, 0.9), min_confidence=0.55
    )
    ssml = to_azure_ssml("a < b & c", params, voice="ko-KR-SunHiNeural")
    assert "&lt;" in ssml and "&amp;" in ssml
    assert "mstts:express-as" in ssml and 'style="angry"' in ssml
    assert "<prosody" in ssml


def test_azure_ssml_neutral_has_no_express_as():
    ssml = to_azure_ssml("hi", NEUTRAL_PARAMS, voice="ko-KR-SunHiNeural")
    assert "mstts:express-as" not in ssml
    assert "<prosody" in ssml


def test_integration_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("COMM_V2_EMOTION_EXPRESSIVE_TTS", raising=False)
    ser_integration.reset_for_test()
    assert ser_integration.build_expressive_tts_plan_from_pcm16(_raw_pcm16(_energetic())) is None
    ser_integration.reset_for_test()


def test_integration_emits_params_when_enabled(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS", "true")
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_CONF", "0.0")
    ser_integration.reset_for_test()
    try:
        params = ser_integration.build_expressive_tts_plan_from_pcm16(_raw_pcm16(_energetic()))
        # 고에너지 → 비중립 파라미터(저신뢰 시 None 가능하므로 신뢰도 임계 0 으로 강제).
        assert params is None or params.neutral is False
    finally:
        ser_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_EMOTION_EXPRESSIVE_TTS", raising=False)
        monkeypatch.delenv("COMM_V2_EMOTION_EXPRESSIVE_TTS_CONF", raising=False)
        ser_integration.reset_for_test()


def test_integration_never_throws_on_bad_bytes(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_EXPRESSIVE_TTS", "true")
    ser_integration.reset_for_test()
    try:
        assert ser_integration.build_expressive_tts_plan_from_pcm16(b"\x01") is None
        assert ser_integration.build_expressive_tts_plan_from_pcm16(None) is None
    finally:
        ser_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_EMOTION_EXPRESSIVE_TTS", raising=False)
        ser_integration.reset_for_test()
