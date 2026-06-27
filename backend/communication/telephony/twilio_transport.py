"""전화 T1 — Twilio Media Streams provider 어댑터 (`MediaTransport` 구현, 오프라인 프레이밍).

[`TELEPHONY_BRIDGE_DESIGN.md`](../../../docs/worldlinco-v2/TELEPHONY_BRIDGE_DESIGN.md) §4.1.
Twilio **Media Streams** 는 WebSocket 으로 JSON 이벤트를 주고받는다(payload = base64 **G.711
μ-law 8kHz mono**):

- inbound:  `connected` · `start` · `media` · `dtmf` · `mark` · `stop`
- outbound: `media`(payload) · `mark` · `clear`

이 어댑터는 **메시지 프레이밍/라우팅**(JSON ↔ `InboundChunk`/μ-law 바이트, streamSid↔leg 매핑)만
담당한다. 코덱 변환(μ-law 8k ↔ PCM16 16k)은 [`MediaBridgeRunner`](transport.py)(`encoding="ulaw"`)가,
콜 플로우는 [`SimulatedMediaBridge`](media_bridge.py)가 맡는다(관심사 분리).

> ⚠️ **실 WebSocket 연결·인증(Account SID/Auth Token, TwiML `<Connect><Stream>`)·번호는 T0
> 계약 후.** 여기 코드는 캐리어를 부르지 않으며, JSON↔도메인 매핑을 카드 없이 결정적으로 검증한다.
> 한 콜의 두 레그(caller/callee)는 각자의 Media Stream 으로 들어오고, `start` 이벤트의
> `customParameters["leg"]`(TwiML `<Parameter name="leg" value="caller"/>`)로 leg 를 식별한다.
"""

from __future__ import annotations

import base64
import json
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Sequence, Union

from .models import CallLeg
from .transport import InboundChunk

# Twilio Media Streams 미디어 포맷(고정): G.711 μ-law 8kHz mono.
TWILIO_ENCODING = "ulaw"
TWILIO_SAMPLE_RATE = 8000

_Raw = Union[str, bytes, Dict[str, Any]]


# --- 순수 프레이밍 헬퍼(transport 독립, 단위테스트 용이) ----------------------

def parse_twilio_event(raw: _Raw) -> Dict[str, Any]:
    """Twilio WS 프레임(str/bytes/dict) → dict. 파싱 실패 시 ``{}``."""

    if isinstance(raw, dict):
        return raw
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def build_media_message(stream_sid: str, payload: bytes) -> str:
    """μ-law 8k 바이트 → Twilio outbound `media` JSON(base64 payload)."""

    b64 = base64.b64encode(payload).decode("ascii")
    return json.dumps(
        {"event": "media", "streamSid": stream_sid, "media": {"payload": b64}}
    )


def build_clear_message(stream_sid: str) -> str:
    """버퍼된 아웃바운드 오디오 즉시 비움(끼어들기/바지인 시)."""

    return json.dumps({"event": "clear", "streamSid": stream_sid})


def build_mark_message(stream_sid: str, name: str) -> str:
    """재생 완료 추적용 mark."""

    return json.dumps({"event": "mark", "streamSid": stream_sid, "mark": {"name": name}})


# --- MediaTransport 구현 ------------------------------------------------------

class TwilioMediaStreamTransport:
    """두 Twilio Media Stream(leg당 1개)을 한 브리지에 다중화하는 전송 어댑터.

    실 WS 핸들러는 수신 프레임마다 `ingest_message(raw)` 를 호출하고, 송신 시에는
    `drain_outbound_messages(leg_id)` 가 돌려주는 JSON 문자열을 WebSocket 으로 write 한다.
    `MediaBridgeRunner` 의 `send_outbound(leg_id, μ-law bytes)` 가 outbound 큐를 채운다.
    """

    def __init__(self, legs: Sequence[CallLeg]) -> None:
        self._legs: List[CallLeg] = list(legs)
        self._leg_ids = {leg.leg_id for leg in legs}
        self._inbound: Deque[InboundChunk] = deque()
        self._outbound_msgs: Dict[str, List[str]] = {leg.leg_id: [] for leg in legs}
        self._sid_to_leg: Dict[str, str] = {}
        self._leg_to_sid: Dict[str, str] = {}
        self._started: set[str] = set()
        self._stopped: set[str] = set()
        self._dtmf: List[Dict[str, str]] = []
        self._closed = False
        self.dropped_no_sid = 0

    # ---- MediaTransport 인터페이스 -------------------------------------
    def legs(self) -> List[CallLeg]:
        return list(self._legs)

    def poll_inbound(self) -> List[InboundChunk]:
        out = list(self._inbound)
        self._inbound.clear()
        return out

    def send_outbound(self, leg_id: str, payload: bytes) -> None:
        """브리지 통역 오디오(μ-law 8k) → 해당 leg 의 Twilio `media` 메시지로 인큐.

        아직 `start` 미수신(streamSid 미상)이면 프레이밍 불가 → 드롭 카운트.
        """

        sid = self._leg_to_sid.get(leg_id)
        if not sid:
            self.dropped_no_sid += 1
            return
        self._outbound_msgs.setdefault(leg_id, []).append(build_media_message(sid, payload))

    def closed(self) -> bool:
        if self._closed:
            return True
        # 모든 leg 가 start 후 stop 됐으면 종료.
        return bool(self._leg_ids) and self._stopped >= self._leg_ids

    def close(self) -> None:
        self._closed = True

    # ---- Twilio WS 수신 핸들러 ------------------------------------------
    def ingest_message(self, raw: _Raw) -> None:
        evt = parse_twilio_event(raw)
        event = evt.get("event")
        if event == "start":
            self._on_start(evt)
        elif event == "media":
            self._on_media(evt)
        elif event == "stop":
            self._on_stop(evt)
        elif event == "dtmf":
            digit = (evt.get("dtmf") or {}).get("digit")
            sid = evt.get("streamSid")
            if digit is not None:
                self._dtmf.append({"leg": self._sid_to_leg.get(sid, ""), "digit": str(digit)})
        # connected/mark 등은 무시.

    def _on_start(self, evt: Dict[str, Any]) -> None:
        start = evt.get("start") or {}
        sid = start.get("streamSid") or evt.get("streamSid")
        params = start.get("customParameters") or {}
        leg_id = params.get("leg")
        if not sid or leg_id not in self._leg_ids:
            return
        self._sid_to_leg[sid] = leg_id
        self._leg_to_sid[leg_id] = sid
        self._started.add(leg_id)

    def _on_media(self, evt: Dict[str, Any]) -> None:
        media = evt.get("media") or {}
        sid = evt.get("streamSid")
        leg_id = self._sid_to_leg.get(sid)
        payload_b64 = media.get("payload")
        if not leg_id or not payload_b64:
            return
        try:
            payload = base64.b64decode(payload_b64)
        except Exception:
            return
        self._inbound.append(InboundChunk(leg_id=leg_id, payload=payload, is_speech=True))

    def _on_stop(self, evt: Dict[str, Any]) -> None:
        sid = evt.get("streamSid")
        leg_id = self._sid_to_leg.get(sid)
        if leg_id:
            self._stopped.add(leg_id)

    # ---- 송신측(실 WS writer 가 호출) -----------------------------------
    def drain_outbound_messages(self, leg_id: str) -> List[str]:
        """해당 leg 로 WebSocket write 할 Twilio JSON 문자열을 빼낸다."""

        msgs = list(self._outbound_msgs.get(leg_id, []))
        if leg_id in self._outbound_msgs:
            self._outbound_msgs[leg_id].clear()
        return msgs

    def pending_outbound_count(self, leg_id: str) -> int:
        return len(self._outbound_msgs.get(leg_id, []))

    @property
    def dtmf_events(self) -> List[Dict[str, str]]:
        return list(self._dtmf)

    def stream_sid_for(self, leg_id: str) -> Optional[str]:
        return self._leg_to_sid.get(leg_id)
