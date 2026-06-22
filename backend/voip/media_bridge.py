"""서버 미디어 브리지(MCU) + 스트리밍 동시통역 AI 탭.

체크리스트 §13 / 기술서 §0.24. "무전기" 근본 제거를 위한 키스톤 모듈.

설계 요지(§13.2):
- 두 폰(A/B)이 **서버**와 각각 WebRTC(sendrecv)로 연결된다(P2P 아님).
- 서버는 A 업링크를 B 다운링크로, B 업링크를 A 다운링크로 **연속 포워딩**한다
  → 양쪽이 상대 실제 목소리를 끊김 없이 청취(라이브 경로, ≤300ms, 거리 무관).
- 동시에 각 레그 업링크를 **AI 탭**으로 복제 → 16k 리샘플 → VAD/endpoint →
  STT → 번역 → 상대 레그로 자막(+추후 TTS 트랙)을 전달(통역 오버레이, 라이브와 분리).

독립 서비스 원칙(§12.5):
- aiortc/av/numpy 는 **lazy import 가드**. 미설치 환경에서도 본 모듈 import 는 깨지지 않으며,
  `is_available()` 가 False 면 호출측이 기존 P2P 경로로 폴백한다.
- STT/번역/TTS 는 호출형으로 분리(`backend.llm.voice_gateway`, `backend.services.nadotongryoksa.translator`).
  추후 독립 GPU 서비스로 빼도 본 모듈 구조는 불변(엔드포인트만 환경변수로 교체).

v1 한계(의도적):
- 포워딩은 renegotiation-free 를 위해 **paced queue 트랙**으로 구현(언더런 시 무음 삽입).
  대규모 동시호출 시 MediaRelay/외부 SFU(mediasoup/Janus)로 승격(§13.5). 코드 경계는 동일.
- endpointer 는 에너지+무음갭 기반 세그먼트(스트리밍 부분결과는 §13.5 후속).
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import time
import wave
from fractions import Fraction
from typing import Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy / guarded heavy deps. 미설치 시 본 모듈 import 는 성공하되 is_available()==False.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - 환경 의존
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover
    _np = None  # type: ignore

try:  # pragma: no cover - 환경 의존
    import av  # type: ignore
    from aiortc import (  # type: ignore
        RTCConfiguration,
        RTCIceServer,
        RTCPeerConnection,
        RTCSessionDescription,
    )
    from aiortc.mediastreams import MediaStreamError, MediaStreamTrack  # type: ignore

    _AIORTC_IMPORT_ERROR: Optional[str] = None
except Exception as _exc:  # pragma: no cover
    av = None  # type: ignore
    RTCConfiguration = RTCIceServer = RTCPeerConnection = RTCSessionDescription = None  # type: ignore
    MediaStreamTrack = object  # type: ignore
    MediaStreamError = Exception  # type: ignore
    _AIORTC_IMPORT_ERROR = str(_exc)


# 통화 오디오 평면 상수.
FORWARD_RATE = 48000          # 다운링크(포워딩) 샘플레이트(Opus 친화).
FORWARD_FRAME_SAMPLES = 960   # 20ms @ 48k.
ASR_RATE = 16000              # STT 입력 샘플레이트(Whisper).

# endpointer 튜닝(환경변수 오버라이드 가능).
def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except Exception:
        return default


SEG_SILENCE_GAP_MS = _f("VOIP_BRIDGE_SILENCE_GAP_MS", 600.0)   # 발화 종료로 간주할 무음 길이.
SEG_MIN_SPEECH_MS = _f("VOIP_BRIDGE_MIN_SPEECH_MS", 350.0)     # 최소 발화 길이(노이즈 컷).
SEG_MAX_SPEECH_MS = _f("VOIP_BRIDGE_MAX_SPEECH_MS", 8000.0)    # 강제 절단(지연 상한).
SEG_RMS_GATE = _f("VOIP_BRIDGE_RMS_GATE", 280.0)               # s16 RMS 발화 게이트.
TTS_GUARD_TAIL_MS = _f("VOIP_BRIDGE_TTS_GUARD_TAIL_MS", 500.0)  # TTS 재생 후 탭 억제 꼬리.


def _bridge_tts_enabled() -> bool:
    """번역 음성(TTS) 트랙 주입 활성 여부(기본 ON). 자막만 원하면 0."""
    return os.getenv("VOIP_BRIDGE_TTS", "1").strip().lower() in ("1", "true", "yes", "on")


def is_available() -> bool:
    """aiortc/av/numpy 가 모두 설치되어 서버 미디어 브리지를 쓸 수 있는가."""
    return av is not None and RTCPeerConnection is not None and _np is not None


def server_bridge_enabled() -> bool:
    """플래그(VOIP_SERVER_MEDIA_BRIDGE) + 의존성 가용성 동시 충족 시에만 브리지 모드."""
    flag = os.getenv("VOIP_SERVER_MEDIA_BRIDGE", "").strip().lower() in ("1", "true", "yes", "on")
    return flag and is_available()


# 자막/통역 결과를 상대 레그로 보내는 콜백 타입.
#   emit(call_id, target_role, payload) -> awaitable
SubtitleEmitter = Callable[[str, str, dict], Awaitable[None]]


# ===========================================================================
# Paced queue 다운링크 트랙 — renegotiation-free 포워딩.
# ===========================================================================
class _QueueAudioTrack(MediaStreamTrack):  # type: ignore[misc]
    """상대 레그에서 들어온 프레임을 큐에 받아 20ms 페이싱으로 송출.

    언더런(상대 무음/지연) 시 무음 프레임을 넣어 타임라인을 유지한다.
    """

    kind = "audio"

    def __init__(self, label: str) -> None:
        super().__init__()
        self._label = label
        self._queue: "asyncio.Queue" = asyncio.Queue(maxsize=50)
        self._timestamp = 0
        self._start: Optional[float] = None
        self._silence = None  # lazy

    async def push(self, frame) -> None:
        """소스 레그의 (48k mono s16) 프레임을 다운링크 큐에 적재."""
        try:
            self._queue.put_nowait(frame)
        except asyncio.QueueFull:
            # 가장 오래된 것 버리고 최신 유지(라이브 우선, 누적 지연 방지).
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(frame)
            except Exception:
                pass

    def _make_silence(self):
        if self._silence is None:
            arr = _np.zeros((1, FORWARD_FRAME_SAMPLES), dtype=_np.int16)
            self._silence = arr
        frame = av.AudioFrame.from_ndarray(self._silence, format="s16", layout="mono")
        frame.sample_rate = FORWARD_RATE
        return frame

    async def recv(self):
        # 20ms 슬롯 페이싱.
        if self._start is None:
            self._start = time.time()
            self._timestamp = 0
        else:
            self._timestamp += FORWARD_FRAME_SAMPLES
            target = self._start + self._timestamp / FORWARD_RATE
            delay = target - time.time()
            if delay > 0:
                await asyncio.sleep(delay)

        try:
            frame = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            frame = self._make_silence()

        frame.pts = self._timestamp
        frame.time_base = Fraction(1, FORWARD_RATE)
        return frame


# ===========================================================================
# 레그 상태.
# ===========================================================================
class _LegState:
    def __init__(self, role: str) -> None:
        self.role = role
        self.pc = None                       # RTCPeerConnection
        self.downlink: Optional[_QueueAudioTrack] = None  # 서버→이 폰 송출 트랙.
        self.consume_task: Optional[asyncio.Task] = None  # 업링크 소비 루프.
        self.language: Optional[str] = None  # 이 레그 화자의 지정 언어.
        self.tts_guard_until: float = 0.0    # 이 레그에 TTS 주입 중이면 탭 억제(에코 방지).


# ===========================================================================
# 통화 브리지.
# ===========================================================================
class CallMediaBridge:
    """단일 call_id 에 대한 2-레그(caller/callee) 서버 미디어 브리지.

    사용:
        bridge = CallMediaBridge(call_id, emit_subtitle, ice_servers)
        answer_sdp = await bridge.handle_offer(role, offer_sdp)
        await bridge.add_ice_candidate(role, candidate, mid, mline_index)
        ... 통화 ...
        await bridge.close()
    """

    def __init__(
        self,
        call_id: str,
        emit_subtitle: SubtitleEmitter,
        ice_servers: Optional[list] = None,
        leg_languages: Optional[Dict[str, str]] = None,
    ) -> None:
        if not is_available():
            raise RuntimeError(
                f"media bridge deps unavailable: aiortc/av/numpy "
                f"(import_error={_AIORTC_IMPORT_ERROR})"
            )
        self.call_id = call_id
        self._emit = emit_subtitle
        self._ice_servers = ice_servers or []
        self._legs: Dict[str, _LegState] = {
            "caller": _LegState("caller"),
            "callee": _LegState("callee"),
        }
        langs = leg_languages or {}
        for role, leg in self._legs.items():
            leg.language = langs.get(role)
        self._closed = False

    def _other(self, role: str) -> str:
        return "callee" if role == "caller" else "caller"

    def _new_pc(self):
        ice = []
        for s in self._ice_servers:
            try:
                if getattr(s, "username", None) and getattr(s, "credential", None):
                    ice.append(RTCIceServer(urls=s.urls, username=s.username, credential=s.credential))
                else:
                    ice.append(RTCIceServer(urls=s.urls))
            except Exception:
                continue
        config = RTCConfiguration(iceServers=ice) if ice else RTCConfiguration(iceServers=[])
        return RTCPeerConnection(configuration=config)

    async def handle_offer(self, role: str, offer_sdp: str) -> str:
        """해당 레그의 offer 를 받아 sendrecv 로 종단하고 answer SDP 를 반환."""
        role = "caller" if role == "caller" else "callee"
        leg = self._legs[role]

        if leg.pc is not None:
            try:
                await leg.pc.close()
            except Exception:
                pass

        pc = self._new_pc()
        leg.pc = pc
        self._wire_leg(pc, leg, role)

        # 답변자(answerer): 먼저 remote(offer) 적용 → 그 다음 다운링크 트랙 부착(offer 의
        # 오디오 트랜시버에 바인딩되어 m-line 정합). addTrack 을 setRemoteDescription 보다
        # 먼저 호출하면 별도 트랜시버가 생겨 m-line 불일치로 미디어가 깨질 수 있다.
        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))
        downlink = _QueueAudioTrack(label=f"{self.call_id}:{role}")
        leg.downlink = downlink
        pc.addTrack(downlink)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        # 비-트리클: ICE 수집 완료까지 대기 → answer SDP 에 서버 후보 포함(폰이 즉시 사용).
        await self._wait_ice_complete(pc)
        return pc.localDescription.sdp

    async def create_offer_for(self, role: str) -> str:
        """서버가 해당 레그(주로 callee)에 **offer 를 보내는** 경로.

        P2P 습관상 callee 는 offer 를 받아 answer 하므로(스스로 offer 하지 않음),
        MCU 에서 callee 를 서버에 연결하려면 서버가 offer 를 만들어 보낸다.
        caller 는 기존대로 자기 offer 를 보내고 서버가 answer(handle_offer)한다.
        """
        role = "caller" if role == "caller" else "callee"
        leg = self._legs[role]
        if leg.pc is not None:
            try:
                await leg.pc.close()
            except Exception:
                pass
        pc = self._new_pc()
        leg.pc = pc
        self._wire_leg(pc, leg, role)
        # 제안자(offerer): 트랙을 먼저 부착(sendrecv) → offer 에 오디오 송수신 m-line 포함.
        downlink = _QueueAudioTrack(label=f"{self.call_id}:{role}")
        leg.downlink = downlink
        pc.addTrack(downlink)
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await self._wait_ice_complete(pc)
        return pc.localDescription.sdp

    async def handle_answer(self, role: str, answer_sdp: str) -> None:
        """create_offer_for 로 보낸 offer 에 대한 폰의 answer 적용."""
        role = "caller" if role == "caller" else "callee"
        leg = self._legs.get(role)
        if not leg or leg.pc is None:
            return
        try:
            await leg.pc.setRemoteDescription(
                RTCSessionDescription(sdp=answer_sdp, type="answer")
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("[bridge] handle_answer failed | call_id=%s | role=%s | %s",
                           self.call_id, role, exc)

    def _wire_leg(self, pc, leg, role: str) -> None:
        """레그 PC 공통 이벤트 배선(연결상태 로그 + 업링크 track 소비)."""

        @pc.on("connectionstatechange")
        async def _on_state():  # pragma: no cover - 런타임 콜백
            logger.info(
                "[bridge] leg state | call_id=%s | role=%s | state=%s",
                self.call_id, role, pc.connectionState,
            )

        @pc.on("track")
        def _on_track(track):  # pragma: no cover - 런타임 콜백
            if track.kind != "audio":
                return
            logger.info("[bridge] uplink track | call_id=%s | role=%s", self.call_id, role)
            leg.consume_task = asyncio.ensure_future(self._consume_uplink(role, track))

    @staticmethod
    async def _wait_ice_complete(pc, timeout: float = 3.0) -> None:
        if pc.iceGatheringState == "complete":
            return
        loop = asyncio.get_event_loop()
        fut = loop.create_future()

        @pc.on("icegatheringstatechange")
        def _on_gather():  # pragma: no cover - 런타임 콜백
            if pc.iceGatheringState == "complete" and not fut.done():
                fut.set_result(None)

        try:
            await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            logger.warning("[bridge] ICE gather timeout (sending partial SDP)")
        except Exception:
            pass

    async def add_ice_candidate(self, role, candidate, sdp_mid, sdp_mline_index) -> None:
        leg = self._legs.get("caller" if role == "caller" else "callee")
        if not leg or leg.pc is None:
            return
        try:
            from aiortc.sdp import candidate_from_sdp  # type: ignore
            raw = candidate or ""
            if raw.startswith("candidate:"):
                raw = raw[len("candidate:"):]
            cand = candidate_from_sdp(raw)
            cand.sdpMid = sdp_mid
            cand.sdpMLineIndex = sdp_mline_index
            await leg.pc.addIceCandidate(cand)
        except Exception as exc:
            logger.debug("[bridge] ice add failed | call_id=%s | %s", self.call_id, exc)

    async def _consume_uplink(self, role: str, track) -> None:
        """소스 레그 업링크 소비: (1) 상대 다운링크 포워딩, (2) AI 탭으로 STT/번역."""
        other = self._other(role)
        src_lang = self._legs[role].language
        tgt_lang = self._legs[other].language
        # 포워딩용 48k mono 리샘플러 + STT용 16k mono 리샘플러(별도, 상태 분리).
        fwd_resampler = av.AudioResampler(format="s16", layout="mono", rate=FORWARD_RATE)
        asr_resampler = av.AudioResampler(format="s16", layout="mono", rate=ASR_RATE)

        # 라이브 원음 포워딩 여부(§13, 사장님 확정):
        #  - 같은 언어(또는 미지정) → 원음 그대로 전달(육성 통화, TTS 없음).
        #  - 다른 언어(통번역 통화) → 원음 차단. 상대는 번역 음성(TTS)+자막만 듣는다
        #    (알아듣지 못하는 원어 육성과 번역음이 겹치는 것을 방지).
        cross_language = _is_cross_language(src_lang, tgt_lang)
        forward_live = not cross_language
        logger.info(
            "[bridge] leg media policy | call_id=%s | %s→%s | src=%s tgt=%s | "
            "cross_language=%s forward_live=%s",
            self.call_id, role, other, src_lang, tgt_lang, cross_language, forward_live,
        )

        tap = _InterpretTap(
            call_id=self.call_id,
            source_role=role,
            target_role=other,
            source_lang=src_lang,
            target_lang=tgt_lang,
            emit=self._emit,
            tts_sink=self._inject_tts,
            guard_check=lambda: time.time() < self._legs[role].tts_guard_until,
        )

        try:
            while not self._closed:
                try:
                    frame = await track.recv()
                except MediaStreamError:
                    break

                # (1) 라이브 포워딩 A→상대 (같은 언어일 때만; 통번역 통화는 원음 차단).
                if forward_live:
                    down = self._legs[other].downlink
                    if down is not None:
                        for f in _safe_resample(fwd_resampler, frame):
                            await down.push(f)

                # (2) AI 탭(블로킹 STT 는 tap 내부에서 executor 로).
                for f in _safe_resample(asr_resampler, frame):
                    await tap.feed(f)
        except Exception as exc:  # pragma: no cover
            logger.warning("[bridge] uplink loop error | call_id=%s | role=%s | %s",
                           self.call_id, role, exc)
        finally:
            await tap.flush()

    async def _inject_tts(self, target_role: str, text: str, lang: Optional[str]) -> None:
        """번역 텍스트를 TTS 합성 → 48k mono 프레임으로 상대 레그 다운링크에 주입(멀티트랙).

        echo 가드: 주입 중 + 꼬리 구간 동안 해당 레그의 업링크 탭을 억제(자기 TTS 재전사 방지).
        """
        if not _bridge_tts_enabled():
            return
        down = self._legs[target_role].downlink
        if down is None:
            return
        loop = asyncio.get_event_loop()

        def _tts():
            from backend.llm.voice_gateway import _synthesize_tts
            return _synthesize_tts(text, lang)

        try:
            b64, fmt = await loop.run_in_executor(None, _tts)
        except Exception as exc:  # pragma: no cover
            logger.debug("[bridge] tts synth failed | call_id=%s | %s", self.call_id, exc)
            return
        if not b64 or not fmt or fmt == "text/plain":
            return
        import base64
        try:
            audio_bytes = base64.b64decode(b64)
        except Exception:
            return

        frames = await loop.run_in_executor(None, _decode_to_48k_mono_frames, audio_bytes)
        if not frames:
            return

        # 에코 가드 설정: 재생 길이(프레임수*20ms) + 꼬리.
        play_ms = len(frames) * (FORWARD_FRAME_SAMPLES / FORWARD_RATE) * 1000.0
        self._legs[target_role].tts_guard_until = time.time() + (play_ms + TTS_GUARD_TAIL_MS) / 1000.0

        for f in frames:
            if self._closed:
                break
            await down.push(f)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for leg in self._legs.values():
            if leg.consume_task is not None:
                leg.consume_task.cancel()
            if leg.pc is not None:
                try:
                    await leg.pc.close()
                except Exception:
                    pass
        logger.info("[bridge] closed | call_id=%s", self.call_id)


def _lang_primary(lang: Optional[str]) -> str:
    """언어 코드를 기본 서브태그로 정규화('ko-KR'→'ko', 'EN_us'→'en', 'auto'/빈값→'')."""
    if not lang:
        return ""
    s = str(lang).strip().lower()
    if s in ("auto", "und", "unknown"):
        return ""
    for sep in ("-", "_"):
        if sep in s:
            s = s.split(sep, 1)[0]
    return s.strip()


def _is_cross_language(src: Optional[str], tgt: Optional[str]) -> bool:
    """두 레그가 **확실히 다른 언어**일 때만 True(통번역 통화).

    한쪽이라도 미지정(auto)이면 다른 언어라고 단정할 수 없으므로 False(원음 통화로 안전 폴백) —
    무음/끊김보다 원음 전달이 안전.
    """
    a = _lang_primary(src)
    b = _lang_primary(tgt)
    if not a or not b:
        return False
    return a != b


def _safe_resample(resampler, frame):
    """av 리샘플러 버전차(단일 프레임/리스트 반환) 흡수."""
    try:
        out = resampler.resample(frame)
    except Exception:
        return []
    if out is None:
        return []
    return out if isinstance(out, list) else [out]


# ===========================================================================
# AI 탭 — endpointer + STT + 번역 → 상대 자막 emit.
# ===========================================================================
class _InterpretTap:
    """16k mono 프레임을 받아 무음갭 기반 세그먼트로 잘라 STT→번역→상대 자막."""

    def __init__(
        self,
        call_id,
        source_role,
        target_role,
        source_lang,
        target_lang,
        emit,
        tts_sink=None,
        guard_check=None,
    ):
        self.call_id = call_id
        self.source_role = source_role
        self.target_role = target_role
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._emit = emit
        self._tts_sink = tts_sink
        self._guard_check = guard_check
        self._buf = []                # list[np.ndarray int16]
        self._buf_ms = 0.0
        self._silence_ms = 0.0
        self._has_speech = False

    async def feed(self, frame) -> None:
        # 에코 가드: 이 레그에 우리가 TTS 를 재생 중이면 업링크(=마이크가 그 TTS 를 주워올 수 있음)를
        # 전사하지 않는다(자기 번역음의 재통역 루프 차단).
        if self._guard_check is not None and self._guard_check():
            self._reset()
            return
        try:
            samples = frame.to_ndarray()  # shape (1, n) s16 mono @16k
        except Exception:
            return
        if samples.size == 0:
            return
        mono = samples.reshape(-1).astype(_np.int16)
        dur_ms = (mono.shape[0] / ASR_RATE) * 1000.0
        rms = float(_np.sqrt(_np.mean((mono.astype(_np.float32)) ** 2))) if mono.size else 0.0

        voiced = rms >= SEG_RMS_GATE
        if voiced:
            self._has_speech = True
            self._silence_ms = 0.0
        else:
            self._silence_ms += dur_ms

        # 발화 중이거나 발화 직후의 짧은 무음은 버퍼에 포함(자연스러운 경계).
        if self._has_speech:
            self._buf.append(mono)
            self._buf_ms += dur_ms

        # 종료 조건: 충분한 무음갭 또는 최대 길이 초과.
        if self._has_speech and (
            self._silence_ms >= SEG_SILENCE_GAP_MS or self._buf_ms >= SEG_MAX_SPEECH_MS
        ):
            await self._finalize_segment()

    async def flush(self) -> None:
        if self._has_speech and self._buf_ms >= SEG_MIN_SPEECH_MS:
            await self._finalize_segment()

    def _reset(self) -> None:
        self._buf = []
        self._buf_ms = 0.0
        self._silence_ms = 0.0
        self._has_speech = False

    async def _finalize_segment(self) -> None:
        if self._buf_ms < SEG_MIN_SPEECH_MS or not self._buf:
            self._reset()
            return
        pcm = _np.concatenate(self._buf)
        self._reset()
        wav_bytes = _pcm16_to_wav(pcm, ASR_RATE)
        try:
            await self._run_pipeline(wav_bytes)
        except Exception as exc:  # pragma: no cover
            logger.warning("[bridge] interpret pipeline error | call_id=%s | %s",
                           self.call_id, exc)

    async def _run_pipeline(self, wav_bytes: bytes) -> None:
        loop = asyncio.get_event_loop()

        # STT (블로킹 → executor).
        def _stt():
            from backend.llm.voice_gateway import _run_faster_whisper
            return _run_faster_whisper(wav_bytes, self.source_lang, None)

        stt = await loop.run_in_executor(None, _stt)
        transcript = str((stt or {}).get("transcript") or "").strip()
        detected = (stt or {}).get("detected_language") or self.source_lang
        if not transcript:
            return

        # 번역 (블로킹 → executor).
        from_lang = (self.source_lang or detected or "auto")
        to_lang = (self.target_lang or "en")

        def _mt():
            from backend.services.nadotongryoksa.translator import translate
            return translate(transcript, from_lang=from_lang, to_lang=to_lang)

        translated = ""
        if to_lang and from_lang != to_lang:
            try:
                translated = await loop.run_in_executor(None, _mt)
            except Exception:
                translated = ""

        payload = {
            "type": "voice_translation",
            "call_id": self.call_id,
            "from_role": self.source_role,
            "transcript": transcript,
            "translated_text": translated or transcript,
            "source_lang": from_lang,
            "target_lang": to_lang,
            "origin": "server_bridge",
        }
        # 상대 레그로 자막 전달(라이브 음성과 분리된 통역 오버레이).
        await self._emit(self.call_id, self.target_role, payload)
        logger.info(
            "[bridge] interpret emit | call_id=%s | %s→%s | %s→%s",
            self.call_id, self.source_role, self.target_role, from_lang, to_lang,
        )

        # MB-4: 번역 음성(TTS)을 상대 레그 다운링크에 주입(원음+번역 멀티트랙).
        # 같은 언어(ko=ko)면 라이브 육성이 이미 그대로 전달되므로 TTS 재합성은 중복(에코) →
        # 번역이 실제로 일어난 경우(언어 상이 + 번역 결과 존재)에만 주입한다.
        should_inject_tts = (
            self._tts_sink is not None
            and bool(translated)
            and from_lang != to_lang
        )
        if should_inject_tts:
            try:
                await self._tts_sink(self.target_role, translated, to_lang)
            except Exception as exc:  # pragma: no cover
                logger.debug("[bridge] tts inject failed | call_id=%s | %s", self.call_id, exc)


def _pcm16_to_wav(pcm, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.astype("<i2").tobytes())
    return buf.getvalue()


def _decode_to_48k_mono_frames(audio_bytes: bytes):
    """TTS 오디오(mp3/wav 등)를 디코드 → 48k mono s16 → 20ms `av.AudioFrame` 리스트.

    블로킹(디코드/리샘플)이므로 호출측에서 executor 로 실행한다.
    """
    if av is None or _np is None:
        return []
    frames_out = []
    try:
        container = av.open(io.BytesIO(audio_bytes))
        resampler = av.AudioResampler(format="s16", layout="mono", rate=FORWARD_RATE)
        pcm_chunks = []
        for frame in container.decode(audio=0):
            for rf in _safe_resample(resampler, frame):
                arr = rf.to_ndarray().reshape(-1).astype(_np.int16)
                if arr.size:
                    pcm_chunks.append(arr)
        container.close()
    except Exception:
        return []
    if not pcm_chunks:
        return []

    pcm = _np.concatenate(pcm_chunks)
    # 20ms(960 샘플) 프레임으로 분할(언더필 마지막은 무음 패딩).
    total = pcm.shape[0]
    for start in range(0, total, FORWARD_FRAME_SAMPLES):
        chunk = pcm[start:start + FORWARD_FRAME_SAMPLES]
        if chunk.shape[0] < FORWARD_FRAME_SAMPLES:
            pad = _np.zeros(FORWARD_FRAME_SAMPLES - chunk.shape[0], dtype=_np.int16)
            chunk = _np.concatenate([chunk, pad])
        af = av.AudioFrame.from_ndarray(chunk.reshape(1, -1), format="s16", layout="mono")
        af.sample_rate = FORWARD_RATE
        frames_out.append(af)
    return frames_out
