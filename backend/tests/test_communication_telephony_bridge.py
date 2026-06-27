"""전화 브리지(T1) 시뮬레이션 PoC 단위테스트.

핵심: 세그먼트 종단(무음/상한) → 파이프라인 실행 → 상대 레그 주입, 순수 무음 미실행,
화자 교대 양방향 통역, PoC 실행 가능.
"""

import pytest  # pyright: ignore[reportMissingImports]

from backend.communication.telephony.config import TelephonyBridgeConfig
from backend.communication.telephony.media_bridge import SimulatedMediaBridge
from backend.communication.telephony.models import AudioFrame, CallLeg, LegRole
from backend.communication.telephony.pipeline import StubPipeline
from backend.communication.telephony.poc import run_one_call_poc


def _cfg(**kw) -> TelephonyBridgeConfig:
    base = dict(enabled=True, sample_rate=16000, frame_ms=20,
                segment_silence_ms=700, segment_max_ms=7000)
    base.update(kw)
    return TelephonyBridgeConfig(**base)


def _bridge(pipeline=None, cfg=None):
    b = SimulatedMediaBridge(pipeline or StubPipeline(), config=cfg or _cfg())
    b.add_leg(CallLeg(leg_id="A", role=LegRole.CALLER, language="ko", peer_language="en"))
    b.add_leg(CallLeg(leg_id="B", role=LegRole.CALLEE, language="en", peer_language="ko"))
    return b


def _voiced(leg, samples=320):
    return AudioFrame(leg_id=leg, samples=[1000] * samples, is_speech=True)


def _silence(leg, samples=320 * 40):
    return AudioFrame(leg_id=leg, samples=[0] * samples, is_speech=False)


def test_silence_endpoint_triggers_bridge_and_injects_to_peer():
    b = _bridge()
    for _ in range(5):
        b.push_frame(_voiced("A"))
    # 아직 종단 전 → 주입 없음.
    assert b.drain_output("B") == []
    b.push_frame(_silence("A"))  # 무음 누적 → 종단
    injected = b.drain_output("B")
    assert len(injected) == 1
    assert b.stats.segments_bridged.get("A") == 1
    assert injected[0].leg_id == "B" and len(injected[0].samples) > 0


def test_pure_silence_segment_not_bridged():
    b = _bridge()
    b.push_frame(_silence("A"))
    assert b.drain_output("B") == []
    assert b.stats.segments_bridged.get("A") is None


def test_translation_direction_uses_speaker_to_peer_lang():
    captured = {}

    def translate_fn(text, from_lang, to_lang):
        captured["from"] = from_lang
        captured["to"] = to_lang
        return f"{to_lang}:{text}"

    b = _bridge(pipeline=StubPipeline(translate_fn=translate_fn))
    for _ in range(5):
        b.push_frame(_voiced("A"))
    b.push_frame(_silence("A"))
    # A(ko 화자) → 상대(en)로 번역.
    assert captured == {"from": "ko", "to": "en"}


def test_max_duration_forces_flush_without_silence():
    b = _bridge(cfg=_cfg(segment_max_ms=100))  # 100ms 상한
    # 20ms 프레임 6개 = 120ms > 100ms → 강제 종단.
    for _ in range(6):
        b.push_frame(_voiced("A"))
    assert b.stats.segments_bridged.get("A") == 1


def test_empty_transcript_is_rejected():
    b = _bridge(pipeline=StubPipeline(transcribe_fn=lambda s, lang: "   "))
    for _ in range(5):
        b.push_frame(_voiced("A"))
    b.push_frame(_silence("A"))
    assert b.drain_output("B") == []
    assert b.stats.rejects == 1


def test_pipeline_exception_is_contained():
    def boom(s, lang):
        raise RuntimeError("stt down")

    b = _bridge(pipeline=StubPipeline(transcribe_fn=boom))
    for _ in range(5):
        b.push_frame(_voiced("A"))
    b.push_frame(_silence("A"))  # 예외 나도 브리지는 죽지 않음
    assert b.stats.rejects == 1
    assert b.drain_output("B") == []


def test_unknown_leg_frame_ignored():
    b = _bridge()
    b.push_frame(AudioFrame(leg_id="ghost", samples=[1] * 320, is_speech=True))
    assert b.stats.frames_in.get("ghost") is None


def test_flush_all_drains_remaining():
    b = _bridge()
    for _ in range(5):
        b.push_frame(_voiced("A"))  # 종단 전 버퍼 잔존
    b.flush_all()
    assert b.stats.segments_bridged.get("A") == 1


def test_poc_runs_bidirectional():
    report = run_one_call_poc(turns=3)
    assert report["turns"] == 3
    # 양방향 각 턴마다 1건씩 주입.
    assert sum(report["injection_counts"]["caller_to_callee"]) == 3
    assert sum(report["injection_counts"]["callee_to_caller"]) == 3
    assert report["stats"]["segments_bridged"]["leg-caller"] == 3
    assert report["stats"]["segments_bridged"]["leg-callee"] == 3
