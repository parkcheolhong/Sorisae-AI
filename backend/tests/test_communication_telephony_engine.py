"""T2 — 실 엔진 어댑터(EnginePipeline) 배선 단위테스트.

실 STT/MT/TTS 스택 없이 콜러블 주입으로 배선·샘플↔바이트 변환을 검증한다.
"""

import base64

import pytest  # pyright: ignore[reportMissingImports]

from backend.communication.telephony.engine_pipeline import EnginePipeline, pcm16_to_wav_bytes
from backend.communication.telephony.media_bridge import SimulatedMediaBridge
from backend.communication.telephony.models import AudioFrame, CallLeg, LegRole
from backend.communication.telephony.config import TelephonyBridgeConfig
from backend.communication.emotion.audio import pcm16_samples_from_bytes


def test_pcm16_to_wav_roundtrip():
    samples = [0, 1000, -1000, 32767, -32768, 5]
    wav = pcm16_to_wav_bytes(samples, sample_rate=16000)
    assert wav[:4] == b"RIFF"
    # WAV(RIFF) 헤더를 건너뛰고 다시 디코딩하면 원 샘플 복원.
    assert pcm16_samples_from_bytes(wav) == samples


def test_transcribe_packs_wav_and_unwraps_tuple():
    captured = {}

    def fake_stt(audio_bytes, lang_hint, src_hint, lock):
        captured["bytes_is_wav"] = audio_bytes[:4] == b"RIFF"
        captured["lang"] = lang_hint
        captured["lock"] = lock
        return ("안녕하세요", "ko", {})

    eng = EnginePipeline(stt_fn=fake_stt)
    text = eng.transcribe([1, 2, 3, 4], language="ko")
    assert text == "안녕하세요"
    assert captured["bytes_is_wav"] is True
    assert captured["lang"] == "ko" and captured["lock"] is True


def test_translate_delegates():
    eng = EnginePipeline(mt_fn=lambda text, f, t: f"{t}:{text}")
    assert eng.translate("hi", from_lang="en", to_lang="ko") == "ko:hi"


def test_synthesize_decodes_base64_pcm():
    samples = [10, -10, 20, -20]
    wav_b64 = base64.b64encode(pcm16_to_wav_bytes(samples)).decode("ascii")
    eng = EnginePipeline(tts_fn=lambda text, lang: (wav_b64, "audio/wav"))
    out = eng.synthesize("hello", language="en")
    assert out == samples


def test_synthesize_empty_returns_empty():
    eng = EnginePipeline(tts_fn=lambda text, lang: (None, None))
    assert eng.synthesize("x", language="en") == []


def test_synthesize_bad_base64_contained():
    eng = EnginePipeline(tts_fn=lambda text, lang: ("!!!notbase64!!!", "audio/wav"))
    # 디코드 실패해도 throw 없이 빈 리스트.
    assert eng.synthesize("x", language="en") == []


def test_bridge_end_to_end_with_engine_adapter():
    # 실엔진 대신 결정적 페이크로 전체 콜 플로우 구동.
    def fake_stt(audio_bytes, lang_hint, src_hint, lock):
        n = pcm16_samples_from_bytes(audio_bytes)
        return (f"utt-{len(n)}", lang_hint, {})

    def fake_mt(text, f, t):
        return f"{t}<-{f}:{text}"

    def fake_tts(text, lang):
        # 텍스트 길이에 비례한 PCM을 WAV base64로.
        pcm = [100] * (len(text) * 4)
        return base64.b64encode(pcm16_to_wav_bytes(pcm)).decode("ascii"), "audio/wav"

    eng = EnginePipeline(stt_fn=fake_stt, mt_fn=fake_mt, tts_fn=fake_tts)
    cfg = TelephonyBridgeConfig(enabled=True, sample_rate=16000, segment_silence_ms=700)
    bridge = SimulatedMediaBridge(eng, config=cfg)
    bridge.add_leg(CallLeg(leg_id="A", role=LegRole.CALLER, language="ko", peer_language="en"))
    bridge.add_leg(CallLeg(leg_id="B", role=LegRole.CALLEE, language="en", peer_language="ko"))

    for _ in range(5):
        bridge.push_frame(AudioFrame(leg_id="A", samples=[1000] * 320, is_speech=True))
    bridge.push_frame(AudioFrame(leg_id="A", samples=[0] * (320 * 40), is_speech=False))

    injected = bridge.drain_output("B")
    assert len(injected) == 1
    assert len(injected[0].samples) > 0          # TTS PCM 주입됨
    assert bridge.stats.segments_bridged.get("A") == 1
