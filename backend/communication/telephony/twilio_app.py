"""전화 T1 — Twilio 실 연결 스캐폴드: TwiML `<Connect><Stream>` + WS 브리지 핸들러.

[`TELEPHONY_BRIDGE_DESIGN.md`](../../../docs/worldlinco-v2/TELEPHONY_BRIDGE_DESIGN.md) §4.1 잔여
항목("실 WS 연결·시그널링/번호")의 **코드 측 준비**. 실제 라이브는 T0 계약(번호·트렁크·
Account SID/Auth Token) 후 라우터를 앱에 마운트하면 동작한다.

구성:
- `build_stream_connect_twiml(...)`  : 인바운드 콜 웹훅 응답 TwiML(양방향 Media Stream + leg 파라미터).
- `run_twilio_media_stream(ws, ...)` : 한 leg WebSocket 을 브리지에 연결하는 비동기 핸들러
   (덕타이핑 ws: `accept`/`receive_text`/`send_text`). 코덱·콜플로우는 `MediaBridgeRunner`+브리지.
- `TwilioBridgeSessionStore`          : call_id 별로 두 leg 가 공유하는 transport/runner 수명 관리.
- `create_twilio_router()` / `mount_twilio_routes(app)` : FastAPI 라우터(웹훅 + WS). **기본 미마운트**
   — `COMM_V2_TELEPHONY_BRIDGE` + `TELEPHONY_TWILIO_ENABLED` opt-in, T0 후 명시적으로 마운트.

> ⚠️ 캐리어 무의존: 본 모듈은 카드를 부르지 않는다. WS 핸들러/프레이밍/TwiML 은 가짜 ws·
> 단위테스트로 검증되며, 실 트래픽은 라이브 환경에서만 흐른다.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Callable, Dict, Optional, Tuple
from xml.sax.saxutils import quoteattr

from .config import TelephonyBridgeConfig, get_telephony_bridge_config, is_telephony_bridge_enabled
from .engine_pipeline import EnginePipeline
from .media_bridge import SimulatedMediaBridge
from .models import CallLeg, LegRole
from .pipeline import BridgePipeline
from .transport import MediaBridgeRunner
from .twilio_transport import TWILIO_ENCODING, TwilioMediaStreamTransport

logger = logging.getLogger(__name__)


# --- 설정 --------------------------------------------------------------------

def is_twilio_live_enabled() -> bool:
    """Twilio 실 라우터 마운트/동작 스위치(기본 off). 브리지 플래그 + Twilio 플래그 동시 on."""

    flag = os.getenv("TELEPHONY_TWILIO_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    return flag and is_telephony_bridge_enabled()


def twilio_ws_url(default: str = "") -> str:
    """TwiML `<Stream url=...>` 에 넣을 wss URL(`TELEPHONY_TWILIO_WS_URL`)."""

    return os.getenv("TELEPHONY_TWILIO_WS_URL", default).strip()


# --- TwiML 빌더 --------------------------------------------------------------

def build_stream_connect_twiml(
    ws_url: str,
    *,
    leg: str = "caller",
    parameters: Optional[Dict[str, str]] = None,
) -> str:
    """인바운드 콜 웹훅 응답 TwiML — 양방향 Media Stream 연결.

    Twilio 는 `<Connect><Stream>` 으로 **양방향**(수신+송신) 오디오를 WebSocket 으로 브리지한다.
    `<Parameter name="leg" value="...">` 로 통역 브리지 leg 를 식별(어댑터 streamSid↔leg 매핑).
    """

    params = {"leg": leg}
    if parameters:
        params.update({str(k): str(v) for k, v in parameters.items()})
    param_xml = "".join(
        f"<Parameter name={quoteattr(k)} value={quoteattr(v)}/>" for k, v in params.items()
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Connect>"
        f"<Stream url={quoteattr(ws_url)}>{param_xml}</Stream>"
        "</Connect></Response>"
    )


# --- leg 언어 결정 -----------------------------------------------------------

def _legs_for_call(caller_lang: str, callee_lang: str) -> list[CallLeg]:
    return [
        CallLeg(leg_id="caller", role=LegRole.CALLER, language=caller_lang, peer_language=callee_lang),
        CallLeg(leg_id="callee", role=LegRole.CALLEE, language=callee_lang, peer_language=caller_lang),
    ]


# --- 세션 스토어(call_id 별 공유 transport/runner) ---------------------------

class TwilioBridgeSessionStore:
    """call_id 당 두 leg(caller/callee)가 공유하는 transport+runner 수명 관리(단일 프로세스).

    멀티 프로세스/노드 배포 시에는 sticky 라우팅(call_id 해시, [`nginx.conf`])으로 같은 인스턴스에
    고정하거나 외부 미디어 서버로 일원화한다(설계 §4.1).
    """

    def __init__(
        self,
        *,
        pipeline_factory: Optional[Callable[[], BridgePipeline]] = None,
        config: Optional[TelephonyBridgeConfig] = None,
    ) -> None:
        self._pipeline_factory = pipeline_factory or (lambda: EnginePipeline())
        self._config = config or get_telephony_bridge_config()
        self._sessions: Dict[str, Tuple[TwilioMediaStreamTransport, MediaBridgeRunner]] = {}
        self._lock = threading.Lock()

    def get_or_create(
        self, call_id: str, *, caller_lang: str = "ko", callee_lang: str = "en"
    ) -> Tuple[TwilioMediaStreamTransport, MediaBridgeRunner]:
        with self._lock:
            existing = self._sessions.get(call_id)
            if existing is not None:
                return existing
            legs = _legs_for_call(caller_lang, callee_lang)
            transport = TwilioMediaStreamTransport(legs)
            bridge = SimulatedMediaBridge(self._pipeline_factory(), config=self._config)
            runner = MediaBridgeRunner(bridge, transport, encoding=TWILIO_ENCODING)
            self._sessions[call_id] = (transport, runner)
            return transport, runner

    def drop(self, call_id: str) -> None:
        with self._lock:
            self._sessions.pop(call_id, None)

    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)


# --- WS 브리지 핸들러(덕타이핑 ws) -------------------------------------------

async def run_twilio_media_stream(
    ws,
    *,
    transport: TwilioMediaStreamTransport,
    runner: MediaBridgeRunner,
    leg_id: str,
    accept: bool = True,
    max_messages: int = 10_000_000,
) -> None:
    """한 leg 의 Twilio Media Stream WebSocket 을 브리지에 연결.

    수신 프레임마다 transport 인제스트 → runner 펌프 → 이 leg 아웃바운드 메시지 송출.
    연결 종료/통화 종료 시 잔여 드레인 후 반환. ws 는 `accept/receive_text/send_text` 만 요구.
    """

    if accept:
        try:
            await ws.accept()
        except Exception:  # pragma: no cover - 일부 ws 는 accept 불필요
            pass

    received = 0
    try:
        while received < max_messages:
            try:
                msg = await ws.receive_text()
            except Exception:  # 연결 종료(WebSocketDisconnect 등)
                break
            if msg is None:
                break
            received += 1
            transport.ingest_message(msg)
            runner.pump_once()
            for out in transport.drain_outbound_messages(leg_id):
                await ws.send_text(out)
            if transport.closed():
                break
    finally:
        try:
            runner.finalize()
            for out in transport.drain_outbound_messages(leg_id):
                await ws.send_text(out)
        except Exception:  # pragma: no cover - teardown 보호
            logger.debug("[twilio-ws] finalize drain skipped", exc_info=True)


# --- FastAPI 라우터(기본 미마운트, T0 후 opt-in) -----------------------------

def create_twilio_router(store: Optional[TwilioBridgeSessionStore] = None):
    """웹훅(TwiML) + Media Stream WS 엔드포인트 APIRouter. 마운트는 T0 후 명시적으로."""

    from fastapi import APIRouter, Request, WebSocket
    from fastapi.responses import Response

    session_store = store or TwilioBridgeSessionStore()
    router = APIRouter(prefix="/telephony/twilio", tags=["telephony-twilio"])

    @router.post("/voice")
    async def twilio_voice_webhook(request: Request):  # pragma: no cover - 라이브 경로
        # 인바운드 콜 → 양방향 Media Stream 으로 연결하는 TwiML 반환.
        ws_url = twilio_ws_url()
        params = dict(request.query_params)
        leg = params.pop("leg", "caller")
        twiml = build_stream_connect_twiml(ws_url, leg=leg, parameters=params)
        return Response(content=twiml, media_type="application/xml")

    @router.websocket("/stream/{call_id}/{leg}")
    async def twilio_stream(websocket: WebSocket, call_id: str, leg: str):  # pragma: no cover
        if not is_twilio_live_enabled():
            await websocket.close(code=1008)
            return
        transport, runner = session_store.get_or_create(call_id)
        try:
            await run_twilio_media_stream(
                websocket, transport=transport, runner=runner, leg_id=leg
            )
        finally:
            if transport.closed():
                session_store.drop(call_id)

    return router


def mount_twilio_routes(app, *, force: bool = False) -> bool:
    """앱에 Twilio 라우터를 마운트(opt-in). flag off 이고 force 아니면 마운트 생략.

    Returns: 마운트 여부. **기본적으로 `backend/main.py` 에서 자동 호출하지 않는다**(T0 후 수동).
    """

    if not force and not is_twilio_live_enabled():
        logger.info("[twilio] routes not mounted (TELEPHONY_TWILIO_ENABLED/bridge off)")
        return False
    app.include_router(create_twilio_router(), prefix="/api")
    logger.info("[twilio] media-stream routes mounted at /api/telephony/twilio")
    return True
