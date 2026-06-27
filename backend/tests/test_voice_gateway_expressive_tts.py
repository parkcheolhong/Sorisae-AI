"""감정 E3 — voice_gateway 표현형 TTS 운율 배선 단위테스트.

핵심: `_synthesize_edge_tts(expressive=...)` 가 감정 운율(rate/volume/pitch)을 edge-tts
`Communicate` 로 전달하고, expressive 없을 때는 기존 기본값(제품 baseline rate, +0)으로
동작함을 보장. 실 네트워크 없이 가짜 edge_tts 모듈을 주입해 결정적으로 검증.
"""

import sys
import types

from backend.communication.emotion.expressive_tts import ExpressiveTTSParams
from backend.llm.voice_gateway import _synthesize_edge_tts, edge_tts_base_rate_pct


def _install_fake_edge_tts(monkeypatch):
    captured: dict = {}

    class _FakeCommunicate:
        def __init__(self, text, voice, *, rate="+0%", volume="+0%", pitch="+0Hz"):
            captured.update(
                {"text": text, "voice": voice, "rate": rate, "volume": volume, "pitch": pitch}
            )

        async def stream(self):
            yield {"type": "audio", "data": b"\x00\x01\x02\x03"}

    fake = types.ModuleType("edge_tts")
    fake.Communicate = _FakeCommunicate
    monkeypatch.setitem(sys.modules, "edge_tts", fake)
    return captured


def test_base_rate_pct_parsing(monkeypatch):
    monkeypatch.delenv("VOICE_EDGE_TTS_RATE", raising=False)
    assert edge_tts_base_rate_pct() == -6.0
    monkeypatch.setenv("VOICE_EDGE_TTS_RATE", "+10%")
    assert edge_tts_base_rate_pct() == 10.0
    monkeypatch.setenv("VOICE_EDGE_TTS_RATE", "garbage")
    assert edge_tts_base_rate_pct() == -6.0


def test_non_expressive_uses_baseline(monkeypatch):
    captured = _install_fake_edge_tts(monkeypatch)
    monkeypatch.setenv("VOICE_EDGE_TTS_RATE", "-6%")
    audio, fmt = _synthesize_edge_tts("안녕하세요", "ko")
    assert audio == b"\x00\x01\x02\x03"
    assert fmt == "audio/mpeg"
    # 기본 경로: baseline rate 유지, volume/pitch 무변경.
    assert captured["rate"] == "-6%"
    assert captured["volume"] == "+0%"
    assert captured["pitch"] == "+0Hz"


def test_expressive_params_threaded_to_communicate(monkeypatch):
    captured = _install_fake_edge_tts(monkeypatch)
    params = ExpressiveTTSParams(
        rate="+12%", volume="+9%", pitch="+11Hz", style="angry", neutral=False
    )
    _synthesize_edge_tts("화났어요", "ko", expressive=params)
    assert captured["rate"] == "+12%"
    assert captured["volume"] == "+9%"
    assert captured["pitch"] == "+11Hz"
