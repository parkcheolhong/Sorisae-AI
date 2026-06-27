"""시뮬레이션 미디어 브리지(T1) — B2BUA 콜 플로우 코어 (전송 무의존).

두 레그의 RTP 프레임을 받아 화자별 세그먼트로 종단(VAD 무음/상한)하고, 세그먼트마다
`BridgePipeline`(STT→MT→TTS)을 실행해 **상대 레그로 통역 오디오를 주입**한다. 실 SIP/RTP
전송은 이 코어를 감싸는 어댑터(FreeSWITCH/Janus 등)가 담당한다(T1 PoC 이후).

설계: half-duplex 가정(한 번에 한 화자). 동시통역(LAAL) 페이싱은 세그먼트 단위 처리로 모사하며,
프레임 단위 스트리밍 인터리브는 실 미디어 서버 통합 단계에서 정밀화한다.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Optional

from .config import TelephonyBridgeConfig, get_telephony_bridge_config
from .models import AudioFrame, BridgeStats, CallLeg
from .pipeline import BridgePipeline


class SimulatedMediaBridge:
    def __init__(
        self,
        pipeline: BridgePipeline,
        config: Optional[TelephonyBridgeConfig] = None,
    ) -> None:
        self._pipeline = pipeline
        self._config = config or get_telephony_bridge_config()
        self._legs: dict[str, CallLeg] = {}
        self._buffer: dict[str, list[int]] = {}
        self._voiced: dict[str, bool] = {}
        self._silence_ms: dict[str, float] = {}
        self._buffered_ms: dict[str, float] = {}
        self._output: dict[str, deque[AudioFrame]] = {}
        self._out_seq: dict[str, int] = {}
        self.stats = BridgeStats()

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def add_leg(self, leg: CallLeg) -> None:
        self._legs[leg.leg_id] = leg
        self._buffer.setdefault(leg.leg_id, [])
        self._voiced.setdefault(leg.leg_id, False)
        self._silence_ms.setdefault(leg.leg_id, 0.0)
        self._buffered_ms.setdefault(leg.leg_id, 0.0)
        self._output.setdefault(leg.leg_id, deque())
        self._out_seq.setdefault(leg.leg_id, 0)

    def _peer_id(self, leg_id: str) -> Optional[str]:
        for other in self._legs:
            if other != leg_id:
                return other
        return None

    def push_frame(self, frame: AudioFrame) -> None:
        """레그 프레임 수신 → 세그먼트 누적 + 종단 판정."""

        leg = self._legs.get(frame.leg_id)
        if leg is None:
            return
        self.stats.frames_in[frame.leg_id] = self.stats.frames_in.get(frame.leg_id, 0) + 1

        frame_ms = (len(frame.samples) / max(1, self._config.sample_rate)) * 1000.0
        self._buffer[frame.leg_id].extend(frame.samples)
        self._buffered_ms[frame.leg_id] += frame_ms

        if frame.is_speech:
            self._voiced[frame.leg_id] = True
            self._silence_ms[frame.leg_id] = 0.0
        else:
            self._silence_ms[frame.leg_id] += frame_ms

        endpoint = (
            self._silence_ms[frame.leg_id] >= self._config.segment_silence_ms
            or self._buffered_ms[frame.leg_id] >= self._config.segment_max_ms
        )
        if endpoint:
            self._flush_segment(frame.leg_id)

    def _flush_segment(self, leg_id: str) -> None:
        samples = self._buffer.get(leg_id) or []
        voiced = self._voiced.get(leg_id, False)
        # 버퍼 리셋(종단마다).
        self._buffer[leg_id] = []
        self._voiced[leg_id] = False
        self._silence_ms[leg_id] = 0.0
        self._buffered_ms[leg_id] = 0.0

        if not voiced or not samples:
            return  # 순수 무음 세그먼트 — 파이프라인 미실행.

        leg = self._legs[leg_id]
        peer_id = self._peer_id(leg_id)
        if peer_id is None:
            self.stats.rejects += 1
            return

        t0 = time.perf_counter()
        try:
            text = self._pipeline.transcribe(samples, language=leg.language)
            if not text or not text.strip():
                self.stats.rejects += 1
                return
            translated = self._pipeline.translate(
                text, from_lang=leg.language, to_lang=leg.peer_language
            )
            synth = self._pipeline.synthesize(translated, language=leg.peer_language)
        except Exception:
            self.stats.rejects += 1
            return
        finally:
            self.stats.pipeline_ms.append((time.perf_counter() - t0) * 1000.0)

        self.stats.segments_bridged[leg_id] = self.stats.segments_bridged.get(leg_id, 0) + 1

        # 통역 오디오를 상대 레그 출력으로 주입.
        seq = self._out_seq[peer_id]
        self._output[peer_id].append(
            AudioFrame(leg_id=peer_id, samples=list(synth), seq=seq, is_speech=True)
        )
        self._out_seq[peer_id] = seq + 1
        self.stats.frames_injected[peer_id] = self.stats.frames_injected.get(peer_id, 0) + 1

    def drain_output(self, leg_id: str) -> list[AudioFrame]:
        """해당 레그로 주입될(=RTP 송출될) 통역 프레임을 빼낸다."""

        out = list(self._output.get(leg_id, deque()))
        if leg_id in self._output:
            self._output[leg_id].clear()
        return out

    def flush_all(self) -> None:
        """남은 버퍼를 모두 종단(통화 종료 시)."""

        for leg_id in list(self._legs):
            if self._buffer.get(leg_id):
                self._flush_segment(leg_id)
