"""전화 T1 — Twilio Media Streams 어댑터 단위테스트(오프라인 프레이밍).

핵심: start(customParameters.leg)로 streamSid↔leg 매핑, media(b64 μ-law)→InboundChunk,
outbound μ-law→Twilio media JSON, stop→closed, start 전 송신 드롭, DTMF 캡처,
그리고 Twilio 어댑터 + MediaBridgeRunner(ulaw) E2E 통역 송출.
"""

import base64
import json

from backend.communication.telephony import codec
from backend.communication.telephony.config import TelephonyBridgeConfig
from backend.communication.telephony.media_bridge import SimulatedMediaBridge
from backend.communication.telephony.models import CallLeg, LegRole
from backend.communication.telephony.pipeline import StubPipeline
from backend.communication.telephony.transport import MediaBridgeRunner
from backend.communication.telephony.twilio_transport import (
    TWILIO_ENCODING,
    TwilioMediaStreamTransport,
    build_media_message,
    parse_twilio_event,
)


def _legs():
    return [
        CallLeg(leg_id="caller", role=LegRole.CALLER, language="ko", peer_language="en"),
        CallLeg(leg_id="callee", role=LegRole.CALLEE, language="en", peer_language="ko"),
    ]


def _start(sid, leg):
    return {"event": "start", "streamSid": sid,
            "start": {"streamSid": sid, "customParameters": {"leg": leg},
                      "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000}}}


def _media(sid, payload: bytes):
    return {"event": "media", "streamSid": sid,
            "media": {"track": "inbound", "payload": base64.b64encode(payload).decode()}}


def test_parse_twilio_event_robust():
    assert parse_twilio_event('{"event":"media"}')["event"] == "media"
    assert parse_twilio_event(b'{"event":"start"}')["event"] == "start"
    assert parse_twilio_event({"event": "stop"})["event"] == "stop"
    assert parse_twilio_event("not json") == {}


def test_build_media_message_roundtrip():
    msg = json.loads(build_media_message("MZ1", b"\x01\x02\x03"))
    assert msg["event"] == "media" and msg["streamSid"] == "MZ1"
    assert base64.b64decode(msg["media"]["payload"]) == b"\x01\x02\x03"


def test_start_maps_sid_to_leg_and_media_becomes_inbound():
    t = TwilioMediaStreamTransport(_legs())
    t.ingest_message(_start("MZcaller", "caller"))
    assert t.stream_sid_for("caller") == "MZcaller"
    ulaw = codec.pcm16_to_ulaw([1000] * 160)
    t.ingest_message(_media("MZcaller", ulaw))
    chunks = t.poll_inbound()
    assert len(chunks) == 1
    assert chunks[0].leg_id == "caller"
    assert chunks[0].payload == ulaw
    assert t.poll_inbound() == []  # 소비됨


def test_unknown_leg_or_sid_ignored():
    t = TwilioMediaStreamTransport(_legs())
    t.ingest_message(_start("MZx", "ghost"))   # 미등록 leg → 무시
    assert t.stream_sid_for("ghost") is None
    t.ingest_message(_media("MZunknown", codec.pcm16_to_ulaw([1] * 80)))  # 미상 sid
    assert t.poll_inbound() == []


def test_send_outbound_before_start_is_dropped():
    t = TwilioMediaStreamTransport(_legs())
    t.send_outbound("caller", b"\x01\x02")
    assert t.dropped_no_sid == 1
    assert t.pending_outbound_count("caller") == 0


def test_send_outbound_frames_twilio_media_after_start():
    t = TwilioMediaStreamTransport(_legs())
    t.ingest_message(_start("MZcallee", "callee"))
    t.send_outbound("callee", b"\xff\xfe")
    msgs = t.drain_outbound_messages("callee")
    assert len(msgs) == 1
    parsed = json.loads(msgs[0])
    assert parsed["streamSid"] == "MZcallee"
    assert base64.b64decode(parsed["media"]["payload"]) == b"\xff\xfe"
    assert t.drain_outbound_messages("callee") == []


def test_stop_closes_when_all_legs_stopped():
    t = TwilioMediaStreamTransport(_legs())
    t.ingest_message(_start("MZ1", "caller"))
    t.ingest_message(_start("MZ2", "callee"))
    assert t.closed() is False
    t.ingest_message({"event": "stop", "streamSid": "MZ1"})
    assert t.closed() is False
    t.ingest_message({"event": "stop", "streamSid": "MZ2"})
    assert t.closed() is True


def test_dtmf_captured():
    t = TwilioMediaStreamTransport(_legs())
    t.ingest_message(_start("MZ1", "caller"))
    t.ingest_message({"event": "dtmf", "streamSid": "MZ1", "dtmf": {"digit": "5"}})
    assert t.dtmf_events == [{"leg": "caller", "digit": "5"}]


def _cfg(**kw) -> TelephonyBridgeConfig:
    base = dict(enabled=True, sample_rate=16000, frame_ms=20,
                segment_silence_ms=700, segment_max_ms=7000)
    base.update(kw)
    return TelephonyBridgeConfig(**base)


def test_twilio_transport_runner_e2e_bridges_to_peer():
    legs = _legs()
    t = TwilioMediaStreamTransport(legs)
    bridge = SimulatedMediaBridge(StubPipeline(), config=_cfg())
    runner = MediaBridgeRunner(bridge, t, encoding=TWILIO_ENCODING)

    # 두 레그 start → streamSid 매핑.
    t.ingest_message(_start("MZcaller", "caller"))
    t.ingest_message(_start("MZcallee", "callee"))
    # caller 발화: μ-law 8k voiced + 무음 종단.
    voiced = codec.pcm16_to_ulaw([6000] * 800)   # 100ms @8k
    silence = codec.pcm16_to_ulaw([0] * 6400)     # 800ms @8k
    for _ in range(3):
        t.ingest_message(_media("MZcaller", voiced))
    t.ingest_message(_media("MZcaller", silence))
    # 통화 종료.
    t.ingest_message({"event": "stop", "streamSid": "MZcaller"})
    t.ingest_message({"event": "stop", "streamSid": "MZcallee"})

    stats = runner.run()

    assert stats.inbound_chunks == 4
    assert bridge.stats.segments_bridged.get("caller") == 1
    # 통역 오디오가 callee 스트림으로 Twilio media JSON 으로 송출됨.
    msgs = t.drain_outbound_messages("callee")
    assert len(msgs) >= 1
    assert json.loads(msgs[0])["streamSid"] == "MZcallee"
    # caller 쪽은 주입 없음.
    assert t.drain_outbound_messages("caller") == []
