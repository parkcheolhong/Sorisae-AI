"""감정 E2 — EMOTION_PROBE 텔레메트리 emission 단위테스트.

핵심: 플래그 게이팅(`COMM_V2_EMOTION_PROBE`), src(입력 PCM16)↔out(TTS WAV) 추정,
평가 하니스가 요구하는 flat 4필드(src/out_arousal·valence) 보장, throw 금지.
out RIFF/WAV 는 ffmpeg 없이 디코딩(decode_audio_to_pcm16 의 RIFF 숏컷)되므로 CI에서 결정적.
"""

import struct

from backend.communication.emotion import integration as ser_integration
from backend.communication.emotion.audio import decode_audio_to_pcm16


def _raw_pcm16(samples: list[int]) -> bytes:
    return struct.pack("<" + "h" * len(samples), *samples)


def _wav(samples: list[int]) -> bytes:
    # 44-byte RIFF 헤더(내용 무관, 길이만 맞음) + PCM16 → decode 의 RIFF 숏컷이 ffmpeg 없이 언팩.
    return b"RIFF" + b"\x00" * 40 + _raw_pcm16(samples)


def _energetic(n: int = 16000) -> list[int]:
    # 교번 최대진폭 → 높은 arousal.
    return [32767 if i % 2 == 0 else -32768 for i in range(n)]


def _calm(n: int = 16000) -> list[int]:
    # 저진폭 완만 → 낮은 arousal(중립 쪽).
    return [200 if (i // 400) % 2 == 0 else -200 for i in range(n)]


def test_decode_riff_shortcut_no_ffmpeg():
    assert decode_audio_to_pcm16(_wav([100, -100, 200, -200])) == [100, -100, 200, -200]
    assert decode_audio_to_pcm16(b"") == []


def test_probe_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("COMM_V2_EMOTION_PROBE", raising=False)
    ser_integration.reset_for_test()
    assert ser_integration.build_emotion_probe(_raw_pcm16(_energetic()), _wav(_calm())) is None
    ser_integration.reset_for_test()


def test_probe_emits_flat_fields_when_enabled(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_PROBE", "true")
    ser_integration.reset_for_test()
    try:
        probe = ser_integration.build_emotion_probe(_raw_pcm16(_energetic()), _wav(_calm()))
        assert probe is not None
        for k in ("src_arousal", "src_valence", "out_arousal", "out_valence"):
            assert isinstance(probe[k], (int, float))
            assert 0.0 <= float(probe[k]) <= 1.0
        assert "src_label" in probe and "out_label" in probe
    finally:
        ser_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_EMOTION_PROBE", raising=False)
        ser_integration.reset_for_test()


def test_probe_none_when_either_side_missing(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_PROBE", "true")
    ser_integration.reset_for_test()
    try:
        assert ser_integration.build_emotion_probe(None, _wav(_calm())) is None
        assert ser_integration.build_emotion_probe(_raw_pcm16(_energetic()), None) is None
        assert ser_integration.build_emotion_probe(b"", b"") is None
    finally:
        ser_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_EMOTION_PROBE", raising=False)
        ser_integration.reset_for_test()


def test_probe_never_throws_on_bad_bytes(monkeypatch):
    monkeypatch.setenv("COMM_V2_EMOTION_PROBE", "true")
    ser_integration.reset_for_test()
    try:
        # 홀수 길이 raw + 1바이트 out → 디코딩 실패해도 None, 예외 없음.
        assert ser_integration.build_emotion_probe(b"\x01", b"\x01") is None
    finally:
        ser_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_EMOTION_PROBE", raising=False)
        ser_integration.reset_for_test()
