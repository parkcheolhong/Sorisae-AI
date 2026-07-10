"""WorldLinco V2 — 전화 T1: 미디어 서버 1콜 브리지 PoC (시뮬레이션, additive).

[`TELEPHONY_BRIDGE_DESIGN.md`](../../../docs/worldlinco-v2/TELEPHONY_BRIDGE_DESIGN.md) 경로 B +
[`TELEPHONY_T0_FEASIBILITY.md`](../../../docs/worldlinco-v2/TELEPHONY_T0_FEASIBILITY.md) T1.

**통신사/CPaaS 트렁크 무의존 시뮬레이션.** 실 SIP B2BUA/SFU 연결(번호·트렁크)은 T0 사업 결정
이후 단계다(여기 코드는 캐리어를 부르지 않는다). 본 패키지는 서버측 브리지가 수행할
**콜 플로우 로직** — 두 레그(leg) 관리·세그먼트 종단·교차 통역 주입·LAAL 페이싱 — 을 전송
계층과 분리해 검증한다. 실제 STT/MT/TTS 엔진은 `BridgePipeline` 콜백으로 주입(스텁↔실엔진 교체).
``COMM_V2_TELEPHONY_BRIDGE`` opt-in, 기본 off.
"""

from . import codec
from .config import TelephonyBridgeConfig, get_telephony_bridge_config, is_telephony_bridge_enabled
from .models import CallLeg, LegRole, AudioFrame, BridgeStats
from .pipeline import BridgePipeline, StubPipeline
from .media_bridge import SimulatedMediaBridge
from .engine_pipeline import EnginePipeline, pcm16_to_wav_bytes
from .transport import (
    InboundChunk,
    InMemoryCarrierTransport,
    MediaBridgeRunner,
    MediaTransport,
    RunnerStats,
)
from .twilio_transport import (
    TWILIO_ENCODING,
    TWILIO_SAMPLE_RATE,
    TwilioMediaStreamTransport,
    build_clear_message,
    build_media_message,
    parse_twilio_event,
)
from .twilio_app import (
    TwilioBridgeSessionStore,
    build_stream_connect_twiml,
    create_twilio_router,
    is_twilio_live_enabled,
    mount_twilio_routes,
    run_twilio_media_stream,
)

__all__ = [
    "TelephonyBridgeConfig",
    "get_telephony_bridge_config",
    "is_telephony_bridge_enabled",
    "CallLeg",
    "LegRole",
    "AudioFrame",
    "BridgeStats",
    "BridgePipeline",
    "StubPipeline",
    "SimulatedMediaBridge",
    "EnginePipeline",
    "pcm16_to_wav_bytes",
    "codec",
    "InboundChunk",
    "MediaTransport",
    "MediaBridgeRunner",
    "RunnerStats",
    "InMemoryCarrierTransport",
    "TwilioMediaStreamTransport",
    "TWILIO_ENCODING",
    "TWILIO_SAMPLE_RATE",
    "parse_twilio_event",
    "build_media_message",
    "build_clear_message",
    "build_stream_connect_twiml",
    "run_twilio_media_stream",
    "TwilioBridgeSessionStore",
    "create_twilio_router",
    "mount_twilio_routes",
    "is_twilio_live_enabled",
]
