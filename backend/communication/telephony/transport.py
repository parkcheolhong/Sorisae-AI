"""전화 T1 실통화 준비 — 미디어 전송 어댑터 경계 + 브리지 러너.

[`TELEPHONY_BRIDGE_DESIGN.md`](../../../docs/worldlinco-v2/TELEPHONY_BRIDGE_DESIGN.md) T1/T2 +
[`TELEPHONY_T0_FEASIBILITY.md`](../../../docs/worldlinco-v2/TELEPHONY_T0_FEASIBILITY.md).

`SimulatedMediaBridge`(콜 플로우 코어)는 전송 무의존이다. 실 캐리어/CPaaS(Twilio Media
Streams·SIP/RTP·Janus 등)를 붙이려면 **(1) 캐리어 프레임을 엔진 PCM16으로 올려 브리지에
push, (2) 브리지가 주입한 통역 PCM16을 캐리어 코덱으로 내려 송출** 하는 어댑터가 필요하다.

이 모듈은 그 경계를 `MediaTransport` 프로토콜로 고정하고, 코덱(`codec.py`) 변환·드레인
루프를 `MediaBridgeRunner` 가 담당한다. `InMemoryCarrierTransport` 는 캐리어 무의존
시뮬레이션 구현(테스트·PoC). 실 provider 어댑터는 이 프로토콜만 구현하면 코어 변경 없이
교체된다(strangler-fig). ``COMM_V2_TELEPHONY_BRIDGE`` opt-in 게이트 하에서만 사용.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Protocol, Sequence

from . import codec
from .media_bridge import SimulatedMediaBridge
from .models import AudioFrame, CallLeg


@dataclass
class InboundChunk:
    """캐리어 → 브리지로 들어오는 1프레임(레그 화자 오디오, 캐리어 코덱 바이트)."""

    leg_id: str
    payload: bytes              # 캐리어 코덱(μ-law/A-law) 바이트
    is_speech: bool = True      # VAD voiced(없으면 caller/SBC가 보수적으로 True)


class MediaTransport(Protocol):
    """실 캐리어/CPaaS 미디어 전송 어댑터 경계.

    구현체는 두 레그(caller/callee)의 RTP/미디어스트림을 이 인터페이스로 노출한다.
    """

    def legs(self) -> List[CallLeg]: ...

    def poll_inbound(self) -> List[InboundChunk]:
        """누적된 인바운드 프레임을 반환·소비(논블로킹)."""
        ...

    def send_outbound(self, leg_id: str, payload: bytes) -> None:
        """브리지가 만든 통역 오디오(캐리어 코덱 바이트)를 해당 레그로 송출."""
        ...

    def closed(self) -> bool:
        """통화 종료(양 레그 BYE) 여부."""
        ...

    def close(self) -> None: ...


@dataclass
class RunnerStats:
    inbound_chunks: int = 0
    outbound_chunks: int = 0
    engine_samples_in: int = 0
    carrier_bytes_out: int = 0
    iterations: int = 0

    def to_dict(self) -> dict:
        return {
            "inbound_chunks": self.inbound_chunks,
            "outbound_chunks": self.outbound_chunks,
            "engine_samples_in": self.engine_samples_in,
            "carrier_bytes_out": self.carrier_bytes_out,
            "iterations": self.iterations,
        }


_DECODERS = {
    "ulaw": codec.ulaw_to_pcm16,
    "pcmu": codec.ulaw_to_pcm16,
    "alaw": codec.alaw_to_pcm16,
    "pcma": codec.alaw_to_pcm16,
}
_ENCODERS = {
    "ulaw": codec.pcm16_to_ulaw,
    "pcmu": codec.pcm16_to_ulaw,
    "alaw": codec.pcm16_to_alaw,
    "pcma": codec.pcm16_to_alaw,
}


class MediaBridgeRunner:
    """전송 어댑터 ↔ `SimulatedMediaBridge` 를 잇는 코덱/드레인 루프.

    인바운드: 캐리어 코덱 8kHz → PCM16 16kHz → `bridge.push_frame`.
    아웃바운드: `bridge.drain_output` PCM16 16kHz → 캐리어 코덱 8kHz → `transport.send_outbound`.
    """

    def __init__(
        self,
        bridge: SimulatedMediaBridge,
        transport: MediaTransport,
        *,
        encoding: str = "ulaw",
        carrier_rate: int = codec.CARRIER_RATE,
        engine_rate: int = codec.ENGINE_RATE,
    ) -> None:
        enc = encoding.lower()
        if enc not in _DECODERS:
            raise ValueError(f"unsupported carrier encoding: {encoding}")
        self._bridge = bridge
        self._transport = transport
        self._decode_codec = _DECODERS[enc]
        self._encode_codec = _ENCODERS[enc]
        self._carrier_rate = carrier_rate
        self._engine_rate = engine_rate
        self._in_seq: Dict[str, int] = {}
        self.stats = RunnerStats()
        for leg in transport.legs():
            self._bridge.add_leg(leg)

    def _to_engine(self, payload: bytes) -> List[int]:
        return codec.resample_pcm16(
            self._decode_codec(payload), self._carrier_rate, self._engine_rate
        )

    def _to_carrier(self, samples: Sequence[int]) -> bytes:
        return self._encode_codec(
            codec.resample_pcm16(samples, self._engine_rate, self._carrier_rate)
        )

    def pump_once(self) -> int:
        """인바운드 1배치 처리 + 모든 레그 아웃바운드 드레인. 처리한 인바운드 수 반환."""

        chunks = self._transport.poll_inbound()
        for chunk in chunks:
            samples = self._to_engine(chunk.payload)
            seq = self._in_seq.get(chunk.leg_id, 0)
            self._in_seq[chunk.leg_id] = seq + 1
            self._bridge.push_frame(
                AudioFrame(
                    leg_id=chunk.leg_id,
                    samples=samples,
                    seq=seq,
                    is_speech=chunk.is_speech,
                )
            )
            self.stats.inbound_chunks += 1
            self.stats.engine_samples_in += len(samples)

        for leg in list(self._bridge._legs):  # noqa: SLF001 — 코어 레그 목록
            for frame in self._bridge.drain_output(leg):
                payload = self._to_carrier(frame.samples)
                self._transport.send_outbound(leg, payload)
                self.stats.outbound_chunks += 1
                self.stats.carrier_bytes_out += len(payload)

        self.stats.iterations += 1
        return len(chunks)

    def run(self, *, max_iterations: int = 100_000) -> RunnerStats:
        """통화 종료(transport.closed())까지 펌프 루프(동기 PoC)."""

        for _ in range(max_iterations):
            processed = self.pump_once()
            if self._transport.closed() and processed == 0:
                break
        return self.finalize()

    def finalize(self) -> RunnerStats:
        """통화 종료 시 잔여 세그먼트 종단 후 마지막 드레인(WS 핸들러 teardown 용)."""

        self._bridge.flush_all()
        self.pump_once()
        return self.stats


class InMemoryCarrierTransport:
    """캐리어 무의존 시뮬레이션 전송(테스트·PoC).

    `feed()` 로 인바운드 프레임을 적재하고, `send_outbound` 가 받은 통역 오디오를
    레그별로 캡처한다. 실 provider 어댑터(Twilio/SIP)는 이 클래스를 대체한다.
    """

    def __init__(self, legs: Sequence[CallLeg]) -> None:
        self._legs: List[CallLeg] = list(legs)
        self._inbound: Deque[InboundChunk] = deque()
        self._outbound: Dict[str, List[bytes]] = {leg.leg_id: [] for leg in legs}
        self._closed = False

    def legs(self) -> List[CallLeg]:
        return list(self._legs)

    def feed(self, leg_id: str, payload: bytes, *, is_speech: bool = True) -> None:
        self._inbound.append(InboundChunk(leg_id=leg_id, payload=payload, is_speech=is_speech))

    def poll_inbound(self) -> List[InboundChunk]:
        out = list(self._inbound)
        self._inbound.clear()
        return out

    def send_outbound(self, leg_id: str, payload: bytes) -> None:
        self._outbound.setdefault(leg_id, []).append(payload)

    def outbound_payload(self, leg_id: str) -> bytes:
        return b"".join(self._outbound.get(leg_id, []))

    def outbound_chunks(self, leg_id: str) -> List[bytes]:
        return list(self._outbound.get(leg_id, []))

    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True
