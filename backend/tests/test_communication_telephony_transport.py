"""전화 T1 실통화 준비 — 코덱 + 전송 어댑터/러너 단위테스트.

핵심: G.711 μ-law/A-law 왕복(양자화 오차 한계 내), 8k↔16k 리샘플 길이/안정성,
MediaBridgeRunner 가 캐리어 코덱 ↔ 엔진 PCM16 경계를 넘어 통역 오디오를 상대 레그로 송출.
"""

from backend.communication.telephony import codec
from backend.communication.telephony.config import TelephonyBridgeConfig
from backend.communication.telephony.media_bridge import SimulatedMediaBridge
from backend.communication.telephony.models import CallLeg, LegRole
from backend.communication.telephony.pipeline import StubPipeline
from backend.communication.telephony.transport import (
    InMemoryCarrierTransport,
    MediaBridgeRunner,
)


def _cfg(**kw) -> TelephonyBridgeConfig:
    base = dict(enabled=True, sample_rate=16000, frame_ms=20,
                segment_silence_ms=700, segment_max_ms=7000)
    base.update(kw)
    return TelephonyBridgeConfig(**base)


# --- 코덱 ---------------------------------------------------------------------

def _max_err(samples, decoded):
    return max(abs(a - b) for a, b in zip(samples, decoded))


def test_ulaw_roundtrip_within_quantization():
    samples = list(range(-32000, 32000, 137))
    decoded = codec.ulaw_to_pcm16(codec.pcm16_to_ulaw(samples))
    assert len(decoded) == len(samples)
    # μ-law 로그 양자화: 진폭 비례 오차(최근접 코드). 바닥 64 + 10%.
    for a, b in zip(samples, decoded):
        assert abs(a - b) <= max(64, abs(a) * 0.10)


def test_alaw_roundtrip_within_quantization():
    samples = list(range(-32000, 32000, 211))
    decoded = codec.alaw_to_pcm16(codec.pcm16_to_alaw(samples))
    assert len(decoded) == len(samples)
    for a, b in zip(samples, decoded):
        assert abs(a - b) <= max(96, abs(a) * 0.12)


def test_ulaw_silence_near_zero():
    decoded = codec.ulaw_to_pcm16(codec.pcm16_to_ulaw([0, 0, 0]))
    assert all(abs(v) <= 16 for v in decoded)


def test_ulaw_byte_length_matches_samples():
    assert len(codec.pcm16_to_ulaw([1, 2, 3, 4])) == 4
    assert len(codec.ulaw_to_pcm16(b"\x00\x11\x22")) == 3


def test_resample_lengths_and_identity():
    src = [100, 200, 300, 400, 500, 600, 700, 800]
    assert codec.resample_pcm16(src, 8000, 8000) == src
    up = codec.resample_pcm16(src, 8000, 16000)
    assert abs(len(up) - 2 * len(src)) <= 1
    down = codec.resample_pcm16(src, 16000, 8000)
    assert abs(len(down) - len(src) // 2) <= 1


def test_resample_constant_signal_stays_constant():
    out = codec.resample_pcm16([5000] * 80, 8000, 16000)
    assert all(abs(v - 5000) <= 1 for v in out)


def test_carrier_helpers_rate_conversion():
    ulaw = codec.pcm16_to_ulaw([3000] * 80)  # 80 bytes @8k = 10ms
    engine = codec.ulaw8k_to_pcm16_engine(ulaw)
    assert abs(len(engine) - 160) <= 1   # 10ms @16k
    back = codec.pcm16_engine_to_ulaw8k(engine)
    assert abs(len(back) - 80) <= 1


def test_runner_rejects_unknown_encoding():
    legs = [CallLeg(leg_id="A", role=LegRole.CALLER, language="ko", peer_language="en")]
    transport = InMemoryCarrierTransport(legs)
    bridge = SimulatedMediaBridge(StubPipeline(), config=_cfg())
    try:
        MediaBridgeRunner(bridge, transport, encoding="opus")
        raised = False
    except ValueError:
        raised = True
    assert raised


# --- 러너 E2E -----------------------------------------------------------------

def _legs():
    return [
        CallLeg(leg_id="A", role=LegRole.CALLER, language="ko", peer_language="en"),
        CallLeg(leg_id="B", role=LegRole.CALLEE, language="en", peer_language="ko"),
    ]


def test_runner_bridges_carrier_audio_to_peer():
    legs = _legs()
    transport = InMemoryCarrierTransport(legs)
    bridge = SimulatedMediaBridge(StubPipeline(), config=_cfg())
    runner = MediaBridgeRunner(bridge, transport, encoding="ulaw")

    # A(ko 화자) 발화: μ-law 8k voiced 프레임들 + 무음 종단(>700ms).
    voiced = codec.pcm16_to_ulaw([6000] * 800)   # 100ms @8k
    silence = codec.pcm16_to_ulaw([0] * 6400)    # 800ms @8k → 무음 종단
    for _ in range(3):
        transport.feed("A", voiced, is_speech=True)
    transport.feed("A", silence, is_speech=False)
    transport.close()

    stats = runner.run()

    assert stats.inbound_chunks == 4
    assert bridge.stats.segments_bridged.get("A") == 1
    # 통역 오디오가 상대(B) 레그로 캐리어 코덱(μ-law)으로 송출됨.
    out_b = transport.outbound_payload("B")
    assert len(out_b) > 0
    # A 쪽으로는 주입 없음(단방향 발화).
    assert transport.outbound_payload("A") == b""
    assert stats.outbound_chunks >= 1


def test_runner_pump_once_no_input_is_noop():
    legs = _legs()
    transport = InMemoryCarrierTransport(legs)
    bridge = SimulatedMediaBridge(StubPipeline(), config=_cfg())
    runner = MediaBridgeRunner(bridge, transport)
    assert runner.pump_once() == 0
    assert transport.outbound_payload("A") == b""
    assert transport.outbound_payload("B") == b""
