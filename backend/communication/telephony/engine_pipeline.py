"""T2 — 실 STT→MT→TTS 엔진 어댑터를 브리지 파이프라인에 연결.

[`TELEPHONY_T0_FEASIBILITY.md`](../../../docs/worldlinco-v2/TELEPHONY_T0_FEASIBILITY.md) T2:
"기존 STT→MT→TTS 재사용". 시뮬레이션 브리지(`SimulatedMediaBridge`)의 `BridgePipeline`
구현으로, hot path와 **동일한** 엔진을 호출한다:

- STT  → `backend.llm.router._transcribe_mobile_voice_audio`
- MT   → `backend.services.nadotongryoksa.translator.NadoTranslator`
- TTS  → `backend.llm.voice_gateway._synthesize_tts`

설계:
- **지연 import**: 무거운 LLM/STT/TTS 스택을 모듈 로드시 끌어오지 않는다(통신 패키지를
  엔진 없이도 import 가능). 첫 호출 때 import.
- **엔진 주입**: 테스트는 `stt_fn`/`mt_fn`/`tts_fn` 콜러블을 주입해 실엔진 없이 배선만 검증.
- **샘플↔바이트 변환**: 브리지는 PCM16 int 샘플, 엔진은 WAV/base64 바이트를 다룬다.

> 실 STT/MT/TTS는 GPU/Whisper/LLM 스택이 필요하므로 라이브 실행은 운영 서버(RTX 5090)에서.
> 본 어댑터는 그 환경에서 시뮬레이션 브리지를 실엔진으로 구동하기 위한 연결부다.
"""

from __future__ import annotations

import base64
import io
import logging
import struct
import wave
from typing import Callable, Optional

from backend.communication.emotion.audio import pcm16_samples_from_bytes

logger = logging.getLogger(__name__)


def pcm16_to_wav_bytes(samples: list[int], *, sample_rate: int = 16000) -> bytes:
    """PCM16 int 샘플 → WAV(mono 16-bit) 바이트."""

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        clamped = (max(-32768, min(32767, int(s))) for s in samples)
        wf.writeframes(struct.pack("<" + "h" * len(samples), *clamped))
    return buf.getvalue()


class EnginePipeline:
    """실 엔진(또는 주입된 콜러블) 기반 `BridgePipeline` 구현."""

    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        stt_fn: Optional[Callable[..., tuple]] = None,
        mt_fn: Optional[Callable[..., str]] = None,
        tts_fn: Optional[Callable[..., tuple]] = None,
    ) -> None:
        self._sample_rate = sample_rate
        self._stt_fn = stt_fn
        self._mt_fn = mt_fn
        self._tts_fn = tts_fn

    # ---- 엔진 해석(지연 import, 주입 우선) -------------------------------
    def _stt(self):
        if self._stt_fn is not None:
            return self._stt_fn
        from backend.llm.router import _transcribe_mobile_voice_audio
        return _transcribe_mobile_voice_audio

    def _mt(self):
        if self._mt_fn is not None:
            return self._mt_fn
        from backend.services.nadotongryoksa.translator import NadoTranslator
        translator = NadoTranslator.get_instance()
        return lambda text, from_lang, to_lang: translator.translate(
            text, from_lang=from_lang, to_lang=to_lang
        )

    def _tts(self):
        if self._tts_fn is not None:
            return self._tts_fn
        from backend.llm.voice_gateway import _synthesize_tts
        return _synthesize_tts

    # ---- BridgePipeline 인터페이스 --------------------------------------
    def transcribe(self, samples: list[int], *, language: str) -> str:
        wav = pcm16_to_wav_bytes(samples, sample_rate=self._sample_rate)
        result = self._stt()(wav, language, language, True)
        # 엔진은 (transcript, detected_lang, meta) 튜플 반환.
        if isinstance(result, tuple):
            return str(result[0] or "")
        return str(result or "")

    def translate(self, text: str, *, from_lang: str, to_lang: str) -> str:
        return str(self._mt()(text, from_lang, to_lang) or "")

    def synthesize(self, text: str, *, language: str) -> list[int]:
        out = self._tts()(text, language)
        # 엔진은 (base64, format) 반환. base64 → PCM16 샘플.
        b64 = out[0] if isinstance(out, tuple) else out
        if not b64:
            return []
        try:
            audio_bytes = base64.b64decode(b64)
        except Exception:
            logger.debug("[telephony-engine] TTS base64 decode failed", exc_info=True)
            return []
        return pcm16_samples_from_bytes(audio_bytes)
