"""PCM16 디코딩 — 순수 파이썬(stdlib only).

VoIP voice-relay 는 16kHz mono **PCM16**(RIFF 헤더 선택적)을 보낸다
(`backend/llm/voice_gateway.py::_pcm16_mono_rms_db` 와 동일 해석). SER 입력용.
"""

from __future__ import annotations

import logging
import struct
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def pcm16_samples_from_bytes(audio_bytes: bytes) -> list[int]:
    """PCM16 mono bytes → int 샘플 리스트. WAV(RIFF) 헤더는 건너뛴다.

    압축 포맷(m4a/aac 등)이면 의미 없는 값이 나올 수 있으므로, 호출부는 designated/VOIP
    (raw PCM16) 경로에서만 사용한다. 실패/짧으면 빈 리스트.
    """

    if not audio_bytes or len(audio_bytes) < 2:
        return []
    pcm_offset = 44 if audio_bytes[:4] == b"RIFF" else 0
    pcm = audio_bytes[pcm_offset:]
    sample_count = len(pcm) // 2
    if sample_count <= 0:
        return []
    return list(struct.unpack("<" + "h" * sample_count, pcm[: sample_count * 2]))


def decode_audio_to_pcm16(
    audio_bytes: bytes,
    *,
    sample_rate: int = 16000,
    timeout_sec: float = 15.0,
) -> list[int]:
    """임의 오디오(예: TTS mp3/edge-tts ``audio/mpeg``) → 16kHz mono PCM16 샘플(best-effort).

    RIFF/WAV 면 ffmpeg 없이 직접 언팩하고, 그 외(mp3/aac 등)는 ffmpeg 로 디코딩한다.
    **음성대역 필터·최소길이 assert 없음**(감정 측정용 원본 보존). ffmpeg 부재/실패/짧으면
    빈 리스트 — **절대 throw 금지**(off-path 텔레메트리 보호).
    """

    if not audio_bytes:
        return []
    # 이미 PCM16/WAV 면 서브프로세스 없이 처리.
    if audio_bytes[:4] == b"RIFF":
        return pcm16_samples_from_bytes(audio_bytes)
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            src = Path(temp_dir) / "emotion_out.bin"
            dst = Path(temp_dir) / "emotion_out.wav"
            src.write_bytes(audio_bytes)
            proc = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(src),
                    "-ar", str(sample_rate), "-ac", "1", "-c:a", "pcm_s16le",
                    str(dst),
                ],
                capture_output=True,
                check=False,
                timeout=timeout_sec,
            )
            if proc.returncode != 0 or not dst.exists():
                return []
            return pcm16_samples_from_bytes(dst.read_bytes())
    except Exception:  # pragma: no cover - ffmpeg 부재/타임아웃 등 방어
        logger.debug("[emotion] decode_audio_to_pcm16 skipped", exc_info=True)
        return []
