"""전화 T1 — Twilio 실 연결 스캐폴드(TwiML + WS 핸들러 + 세션스토어) 단위테스트.

핵심: TwiML `<Connect><Stream>`+leg 파라미터/이스케이프, 세션스토어 call_id 공유,
WS 핸들러가 가짜 ws 스크립트(start/media/stop)로 통역 오디오를 상대 leg 로 송출,
live flag 게이팅. 캐리어 무의존 — 실 WS 트래픽 없이 결정적 검증.
"""

import asyncio
import base64
import json
from xml.etree import ElementTree as ET

from backend.communication.telephony import codec
from backend.communication.telephony.config import TelephonyBridgeConfig
from backend.communication.telephony.pipeline import StubPipeline
from backend.communication.telephony.twilio_app import (
    TwilioBridgeSessionStore,
    build_stream_connect_twiml,
    is_twilio_live_enabled,
    run_twilio_media_stream,
)


def _cfg() -> TelephonyBridgeConfig:
    return TelephonyBridgeConfig(enabled=True, sample_rate=16000, frame_ms=20,
                                 segment_silence_ms=700, segment_max_ms=7000)


def _store() -> TwilioBridgeSessionStore:
    return TwilioBridgeSessionStore(pipeline_factory=lambda: StubPipeline(), config=_cfg())


def test_twiml_structure_and_params():
    xml = build_stream_connect_twiml("wss://x.example/stream", leg="caller",
                                     parameters={"callId": "C1 & 2"})
    root = ET.fromstring(xml)
    stream = root.find("./Connect/Stream")
    assert stream is not None
    assert stream.get("url") == "wss://x.example/stream"
    names = {p.get("name"): p.get("value") for p in stream.findall("Parameter")}
    assert names["leg"] == "caller"
    assert names["callId"] == "C1 & 2"  # XML 이스케이프 왕복


def test_session_store_shares_per_call():
    store = _store()
    t1, r1 = store.get_or_create("callA")
    t2, r2 = store.get_or_create("callA")
    assert t1 is t2 and r1 is r2
    t3, _ = store.get_or_create("callB")
    assert t3 is not t1
    assert store.active_count() == 2
    store.drop("callA")
    assert store.active_count() == 1


def test_live_flag_gating(monkeypatch):
    monkeypatch.delenv("TELEPHONY_TWILIO_ENABLED", raising=False)
    monkeypatch.delenv("COMM_V2_TELEPHONY_BRIDGE", raising=False)
    assert is_twilio_live_enabled() is False
    monkeypatch.setenv("TELEPHONY_TWILIO_ENABLED", "1")
    assert is_twilio_live_enabled() is False  # 브리지 플래그도 필요
    monkeypatch.setenv("COMM_V2_TELEPHONY_BRIDGE", "1")
    assert is_twilio_live_enabled() is True


class _FakeWS:
    """스크립트된 인바운드 메시지를 흘리고, send_text 를 캡처하는 가짜 WebSocket."""

    def __init__(self, inbound):
        self._inbound = list(inbound)
        self.sent = []
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def receive_text(self):
        if not self._inbound:
            raise RuntimeError("disconnect")  # 핸들러가 break 하도록
        return self._inbound.pop(0)

    async def send_text(self, msg):
        self.sent.append(msg)


def _start(sid, leg):
    return json.dumps({"event": "start", "streamSid": sid,
                       "start": {"streamSid": sid, "customParameters": {"leg": leg}}})


def _media(sid, payload: bytes):
    return json.dumps({"event": "media", "streamSid": sid,
                       "media": {"payload": base64.b64encode(payload).decode()}})


def test_ws_handler_bridges_to_peer_outbound():
    store = _store()
    transport, runner = store.get_or_create("callX")
    # caller WS 스크립트: start + voiced*3 + 무음 종단 + stop.
    voiced = codec.pcm16_to_ulaw([6000] * 800)
    silence = codec.pcm16_to_ulaw([0] * 6400)
    # callee 도 start 시켜 streamSid 매핑(아웃바운드 프레이밍 위해).
    transport.ingest_message(_start("MZcallee", "callee"))
    inbound = [
        _start("MZcaller", "caller"),
        _media("MZcaller", voiced),
        _media("MZcaller", voiced),
        _media("MZcaller", voiced),
        _media("MZcaller", silence),
    ]
    ws = _FakeWS(inbound)

    asyncio.run(
        run_twilio_media_stream(ws, transport=transport, runner=runner, leg_id="caller")
    )

    assert ws.accepted is True
    # caller leg WS 로는 (caller 발화에 대한) 주입이 없음 → 통역은 callee 로.
    msgs = transport.drain_outbound_messages("callee")
    assert len(msgs) >= 1
    assert json.loads(msgs[0])["streamSid"] == "MZcallee"
