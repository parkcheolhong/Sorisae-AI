"""Voice entrypoint for orchestrator requests.

Supports whisper.cpp-compatible CLIs and a basic TTS bridge.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.llm.model_config import (
    build_ollama_options,
    get_chat_model,
    get_coder_model,
    get_designer_model,
    get_planner_model,
    get_reasoning_model,
    get_reviewer_model,
    get_voice_chat_model,
)
from backend.orchestrator.chat.chat_service import answer_orchestrator_chat as answer_orchestrator_chat_service
from backend.orchestrator.chat.models import OrchestratorChatRequest


router = APIRouter(prefix="/api/llm", tags=["voice"])
logger = logging.getLogger(__name__)
VOICE_OLLAMA_BASE = os.getenv('OLLAMA_BASE', 'http://host.docker.internal:8008/v1')
VOICE_CHAT_REQUEST_MAX_TOKENS = max(128, int(os.getenv('ORCH_CHAT_REQUEST_MAX_TOKENS', '768')))
VOICE_LIGHTWEIGHT_CHAT_MAX_TOKENS = max(64, int(os.getenv('ORCH_LIGHTWEIGHT_CHAT_MAX_TOKENS', '192')))
VOICE_CHAT_AGENT_TIMEOUT_SEC = max(5.0, float(os.getenv('ORCH_CHAT_AGENT_TIMEOUT_SEC', '75')))
VOICE_REASONER_BRIEF_TIMEOUT_SEC = max(5.0, float(os.getenv('ORCH_REASONER_BRIEF_TIMEOUT_SEC', '45')))
VOICE_RELAY_MIN_SEGMENT_MS = max(800, int(os.getenv("VOICE_RELAY_MIN_SEGMENT_MS", "2400")))
VOICE_RELAY_MIN_SEGMENT_TOLERANCE_MS = max(0, int(os.getenv("VOICE_RELAY_MIN_SEGMENT_TOLERANCE_MS", "350")))
VOICE_RELAY_MIN_SPEECH_RMS_DB = float(os.getenv("VOICE_RELAY_MIN_SPEECH_RMS_DB", "-58"))
VOICE_RELAY_PCM_SAMPLE_RATE = 16_000


def _resolve_voice_chat_model(agent_key: str, *, lightweight: bool) -> str:
    normalized = str(agent_key or 'chat').strip().lower()
    if normalized == 'voice_chat':
        return get_voice_chat_model()
    if normalized == 'reasoner':
        return get_reasoning_model()
    if normalized == 'coder':
        return get_coder_model()
    if normalized == 'planner':
        return get_planner_model()
    if normalized == 'reviewer':
        return get_reviewer_model()
    if normalized == 'designer':
        return get_designer_model()
    if lightweight:
        return get_chat_model()
    return get_chat_model()


class VoiceRequest(BaseModel):
    audio_base64: Optional[str] = None
    transcript: Optional[str] = None
    agent_key: str = "reasoner"
    tts: bool = True
    auto_apply: bool = False
    max_tokens: int = 2048
    task: str = ""
    mode: str = "manual_9step"
    manual_mode: bool = True
    companion_mode: str = "hybrid"
    output_dir: Optional[str] = None
    run_id: Optional[str] = None
    conversation: list[dict] = []
    language: Optional[str] = None  # STT 언어 힌트 (zh, ja, ko, en 등)
    detected_language: Optional[str] = None  # Whisper 감지 언어 (zh, ja, ko, en 등)


class VoiceResponse(BaseModel):
    transcript: str
    response_text: str
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = None
    output_dir: Optional[str] = None
    run_id: Optional[str] = None
    conversation: list[dict] = []


def _run_whisper_cpp(audio_bytes: bytes) -> str:
    whisper_bin = os.getenv("WHISPER_CPP_BIN", "")
    whisper_model = os.getenv("WHISPER_CPP_MODEL", "")
    if not whisper_bin or not whisper_model:
        raise RuntimeError("whisper.cpp configuration missing")

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "voice_input.wav"
        output_path = Path(temp_dir) / "voice_output.txt"
        audio_path.write_bytes(audio_bytes)
        proc = subprocess.run(
            [
                whisper_bin,
                "-m",
                whisper_model,
                "-f",
                str(audio_path),
                "-otxt",
                "-of",
                str(output_path.with_suffix("")),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "whisper.cpp failed")
        txt_path = output_path
        if not txt_path.exists():
            raise RuntimeError("whisper.cpp output missing")
        return txt_path.read_text(encoding="utf-8").strip()


def _normalize_whisper_language_hint(language: Optional[str]) -> Optional[str]:
    """앱 LangCode → ISO 639-1 정규화 (zh-tw → zh, auto/빈값 → 자동 감지)."""
    lang_hint = str(language or "").strip().lower().split("-")[0]
    if not lang_hint or lang_hint == "auto":
        return None
    valid_langs = {
        "ko", "en", "zh", "ja", "es", "fr", "de", "pt", "ru", "ar",
        "hi", "it", "tr", "th", "vi", "id", "ms", "nl", "pl",
    }
    return lang_hint if lang_hint in valid_langs else None


def _resolve_whisper_initial_prompt(language: Optional[str]) -> str:
    lang = _normalize_whisper_language_hint(language)
    # Avoid greeting words — they become silence hallucinations on tiny Whisper models.
    prompts = {
        "ko": "회의 통역 문장입니다.",
        "en": "Conversation translation sentence.",
        "ja": "会議の通訳文です。",
        "zh": "会议翻译句子。",
        "vi": "Câu dịch thuật hội thoại.",
        "th": "ประโยคแปลบทสนทนา",
    }
    return prompts.get(lang or "", "")


def _pcm16_mono_rms_db(audio_bytes: bytes, sample_rate: int = VOICE_RELAY_PCM_SAMPLE_RATE) -> float:
    import math
    import struct

    pcm_offset = 44 if audio_bytes[:4] == b"RIFF" else 0
    pcm = audio_bytes[pcm_offset:]
    if len(pcm) < 2:
        return -160.0
    sample_count = len(pcm) // 2
    samples = struct.unpack("<" + "h" * sample_count, pcm[: sample_count * 2])
    if not samples:
        return -160.0
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    rms = math.sqrt(mean_square)
    if rms <= 0:
        return -160.0
    return 20.0 * math.log10(rms / 32768.0)


def _assert_min_voice_energy(normalized_wav: bytes) -> None:
    rms_db = _pcm16_mono_rms_db(normalized_wav)
    if rms_db < VOICE_RELAY_MIN_SPEECH_RMS_DB:
        raise RuntimeError("음성이 감지되지 않았습니다. 다시 말씀해 주세요.")


def _pcm16_mono_duration_ms(audio_bytes: bytes, sample_rate: int = VOICE_RELAY_PCM_SAMPLE_RATE) -> float:
    pcm_offset = 44 if audio_bytes[:4] == b"RIFF" else 0
    pcm_len = max(0, len(audio_bytes) - pcm_offset)
    return (pcm_len / (sample_rate * 2)) * 1000.0


def _assert_min_voice_capture_duration(normalized_wav: bytes) -> None:
    duration_ms = _pcm16_mono_duration_ms(normalized_wav)
    if duration_ms < (VOICE_RELAY_MIN_SEGMENT_MS - VOICE_RELAY_MIN_SEGMENT_TOLERANCE_MS):
        raise RuntimeError(
            "녹음 길이가 너무 짧습니다. "
            f"({duration_ms:.0f}ms / 최소 {VOICE_RELAY_MIN_SEGMENT_MS}ms)"
        )


def _normalize_voice_audio_bytes(audio_bytes: bytes) -> bytes:
    """Expo/모바일 m4a·aac 등을 16kHz mono PCM wav로 정규화 + 음성 대역·잡음 제거."""
    if not audio_bytes:
        raise RuntimeError("오디오 데이터가 비어 있습니다")

    with tempfile.TemporaryDirectory() as temp_dir:
        src = Path(temp_dir) / "voice_input.bin"
        dst = Path(temp_dir) / "voice_normalized.wav"
        src.write_bytes(audio_bytes)
        audio_filter = os.getenv(
            "VOICE_STT_AUDIO_FILTER",
            "highpass=f=80,lowpass=f=4200",
        )
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(src),
                "-af",
                audio_filter,
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(dst),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if proc.returncode != 0 or not dst.exists():
            stderr = (proc.stderr or "").strip()
            raise RuntimeError(stderr or "오디오 정규화에 실패했습니다")
        normalized = dst.read_bytes()
        if not normalized:
            raise RuntimeError("정규화된 오디오가 비어 있습니다")
        _assert_min_voice_capture_duration(normalized)
        _assert_min_voice_energy(normalized)
        return normalized


_WHISPER_MODEL_LOCK = __import__("threading").Lock()


def warmup_faster_whisper_model() -> None:
    """Warm ffmpeg + whisper subprocess path with a tiny silent clip."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            silent = Path(temp_dir) / "warmup.wav"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=16000:cl=mono",
                    "-t",
                    "0.2",
                    str(silent),
                ],
                capture_output=True,
                check=False,
            )
            if silent.exists():
                _run_faster_whisper(silent.read_bytes(), "ko", "")
        logger.info("[voice-stt] faster-whisper warmup complete")
    except Exception as exc:
        logger.warning("[voice-stt] faster-whisper warmup skipped: %s", exc)


VOICE_RELAY_MIN_AVG_LOGPROB = float(os.getenv("VOICE_RELAY_MIN_AVG_LOGPROB", "-0.95"))
VOICE_RELAY_MAX_NO_SPEECH_PROB = float(os.getenv("VOICE_RELAY_MAX_NO_SPEECH_PROB", "0.62"))


def classify_voice_relay_stt_trust(
    transcript: str,
    avg_logprob: float,
    max_no_speech_prob: float,
) -> str:
    if not str(transcript or "").strip():
        return "low"
    if avg_logprob < VOICE_RELAY_MIN_AVG_LOGPROB:
        return "low"
    if max_no_speech_prob > VOICE_RELAY_MAX_NO_SPEECH_PROB:
        return "low"
    return "high"


def _run_faster_whisper(
    audio_bytes: bytes,
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
) -> dict[str, object]:
    """Returns whisper payload including transcript, language, and confidence metrics."""
    model_name = os.getenv("FASTER_WHISPER_MODEL", "tiny")
    device = os.getenv("FASTER_WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8")
    whisper_lang = _normalize_whisper_language_hint(language)
    prompt = str(initial_prompt or _resolve_whisper_initial_prompt(language) or "").strip()

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "voice_input.wav"
        audio_path.write_bytes(audio_bytes)
        script = """
import json
import sys

from faster_whisper import WhisperModel

audio_path = sys.argv[1]
model_name = sys.argv[2]
device = sys.argv[3]
compute_type = sys.argv[4]
lang_hint = sys.argv[5] if len(sys.argv) > 5 else ""
initial_prompt = sys.argv[6] if len(sys.argv) > 6 else ""

model = WhisperModel(model_name, device=device, compute_type=compute_type)
kwargs = {
    "vad_filter": False,
    "condition_on_previous_text": False,
    "no_speech_threshold": 0.45,
    "log_prob_threshold": -1.2,
    "compression_ratio_threshold": 3.2,
    "beam_size": 5,
    "best_of": 3,
    "temperature": 0.0,
}
if lang_hint:
    kwargs["language"] = lang_hint
if initial_prompt:
    kwargs["initial_prompt"] = initial_prompt
segments, info = model.transcribe(audio_path, **kwargs)
segment_rows = list(segments)
transcript = " ".join((seg.text or "").strip() for seg in segment_rows).strip()
detected = getattr(info, "language", None) or ""
avg_logprob = (
    sum(float(getattr(seg, "avg_logprob", -5.0)) for seg in segment_rows) / len(segment_rows)
    if segment_rows
    else -5.0
)
max_no_speech_prob = (
    max(float(getattr(seg, "no_speech_prob", 1.0)) for seg in segment_rows)
    if segment_rows
    else 1.0
)
print(json.dumps({
    "transcript": transcript,
    "detected_language": detected,
    "avg_logprob": avg_logprob,
    "max_no_speech_prob": max_no_speech_prob,
}, ensure_ascii=False))
"""

        cmd = [
            sys.executable,
            "-c",
            script,
            str(audio_path),
            model_name,
            device,
            compute_type,
        ]
        if whisper_lang:
            cmd.append(whisper_lang)
        else:
            cmd.append("")
        cmd.append(prompt)

        with _WHISPER_MODEL_LOCK:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=240,
            )
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            raise RuntimeError(stderr or "faster-whisper subprocess failed")

        payload = json.loads((proc.stdout or "{}").strip())
        transcript = str(payload.get("transcript") or "").strip()
        detected = str(payload.get("detected_language") or "").strip() or None
        avg_logprob = float(payload.get("avg_logprob", -5.0))
        max_no_speech_prob = float(payload.get("max_no_speech_prob", 1.0))
        return {
            "transcript": transcript,
            "detected_language": detected,
            "avg_logprob": avg_logprob,
            "max_no_speech_prob": max_no_speech_prob,
            "stt_trust": classify_voice_relay_stt_trust(
                transcript,
                avg_logprob,
                max_no_speech_prob,
            ),
        }


def _edge_tts_enabled() -> bool:
    flag = os.getenv("VOICE_EDGE_TTS_ENABLED", "1").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def _synthesize_edge_tts(text: str) -> tuple[bytes, str]:
    import edge_tts

    voice = os.getenv("VOICE_EDGE_TTS_VOICE", "ko-KR-SunHiNeural").strip()
    rate = os.getenv("VOICE_EDGE_TTS_RATE", "-6%").strip() or "-6%"

    async def _run() -> bytes:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks)

    audio_bytes = asyncio.run(_run())
    if not audio_bytes:
        raise RuntimeError("edge-tts produced no audio")
    return audio_bytes, "audio/mpeg"


def _synthesize_tts(text: str) -> tuple[Optional[str], Optional[str]]:
    trimmed = str(text or "").strip()
    if not trimmed:
        return None, None

    if _edge_tts_enabled():
        try:
            audio_bytes, audio_format = _synthesize_edge_tts(trimmed)
            return base64.b64encode(audio_bytes).decode("ascii"), audio_format
        except ImportError:
            logger.debug("edge-tts not installed; falling back to VOICE_TTS_COMMAND")
        except Exception as exc:
            logger.warning("edge-tts synthesis failed: %s", exc)

    tts_command = os.getenv("VOICE_TTS_COMMAND", "").strip()
    if tts_command:
        proc = subprocess.run(
            [tts_command, trimmed],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                proc.stderr.decode("utf-8", errors="ignore").strip()
                or "tts failed"
            )
        content_type = "audio/mpeg" if proc.stdout[:3] == b"ID3" or proc.stdout[:2] == b"\xff\xfb" else "audio/wav"
        return base64.b64encode(proc.stdout).decode("ascii"), content_type

    return (
        base64.b64encode(trimmed.encode("utf-8")).decode("ascii"),
        "text/plain",
    )


class VoiceSynthesizeRequest(BaseModel):
    text: str


class VoiceSynthesizeResponse(BaseModel):
    text: str
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = None
    tts_delivery: str = "device_speech"


@router.post("/voice/synthesize", response_model=VoiceSynthesizeResponse)
async def voice_synthesize(request: VoiceSynthesizeRequest):
    """오케스트레이터 응답 TTS — Edge neural 우선, 없으면 device speech."""
    trimmed = str(request.text or "").strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="text가 필요합니다.")
    try:
        audio_base64, audio_format = await asyncio.to_thread(_synthesize_tts, trimmed)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS 실패: {exc}") from exc
    delivery = (
        "server_audio"
        if audio_base64 and str(audio_format or "").startswith("audio/")
        else "device_speech"
    )
    return VoiceSynthesizeResponse(
        text=trimmed,
        audio_base64=audio_base64,
        audio_format=audio_format,
        tts_delivery=delivery,
    )


@router.post("/voice/orchestrate", response_model=VoiceResponse)
async def voice_orchestrate(request_context: Request, request: VoiceRequest):
    transcript = (request.transcript or "").strip()
    detected_language: Optional[str] = None

    if not transcript and request.audio_base64:
        stt_errors: list[str] = []
        try:
            audio_bytes = base64.b64decode(request.audio_base64)
            whisper_bin = os.getenv("WHISPER_CPP_BIN", "").strip()
            whisper_model = os.getenv("WHISPER_CPP_MODEL", "").strip()

            if whisper_bin and whisper_model:
                try:
                    transcript = await asyncio.to_thread(
                        _run_whisper_cpp,
                        audio_bytes,
                    )
                except Exception as exc:
                    stt_errors.append(f"whisper.cpp: {exc}")

            if not transcript:
                try:
                    whisper_payload = await asyncio.to_thread(
                        _run_faster_whisper,
                        audio_bytes,
                        request.language,
                    )
                    transcript = str(whisper_payload.get("transcript") or "").strip()
                    detected_language = whisper_payload.get("detected_language")
                except Exception as exc:
                    stt_errors.append(f"faster-whisper: {exc}")

            # Keep voice flow alive even when audio is silent but STT engine is available.
            if not transcript and not stt_errors:
                transcript = "voice input received"

            if not transcript:
                raise HTTPException(
                    status_code=400,
                    detail=f"STT 실패: {' | '.join(stt_errors) or 'no STT engine configured'}",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"STT 실패: {exc}")

    if not transcript:
        raise HTTPException(status_code=400, detail="텍스트 또는 오디오 입력이 필요합니다")

    output_dir = request.output_dir
    run_id = request.run_id
    conversation: list[dict] = request.conversation or []

    if request.auto_apply:
        from backend.llm.orchestrator import OrchestrationRequest, run_orchestration

        orch_response = await asyncio.to_thread(
            lambda: asyncio.run(
                run_orchestration(
                    OrchestrationRequest(
                        task=transcript,
                        mode=request.mode or "auto",
                        max_tokens=request.max_tokens,
                        auto_apply=request.auto_apply,
                        manual_mode=request.manual_mode,
                        output_dir=request.output_dir,
                        run_id=request.run_id,
                        conversation=conversation,
                    )
                )
            )
        )
        response_text = orch_response.final_output
        output_dir = orch_response.output_dir
        run_id = orch_response.run_id
        conversation = [
            item.model_dump() for item in orch_response.conversation
        ]
    else:
        chat_response = await asyncio.to_thread(
            lambda: asyncio.run(
                answer_orchestrator_chat_service(
                    request_context=request_context,
                    request=OrchestratorChatRequest(
                        task=request.task or transcript,
                        message=transcript,
                        agent_key=request.agent_key or "reasoner",
                        mode=request.mode,
                        manual_mode=request.manual_mode,
                        companion_mode=request.companion_mode,
                        output_dir=request.output_dir,
                        run_id=request.run_id,
                        max_tokens=request.max_tokens,
                        conversation=conversation,
                    ),
                    agent_key=request.agent_key or "reasoner",
                    resolve_chat_model=_resolve_voice_chat_model,
                    build_ollama_options=build_ollama_options,
                    ollama_base=VOICE_OLLAMA_BASE,
                    orch_chat_request_max_tokens=VOICE_CHAT_REQUEST_MAX_TOKENS,
                    orch_lightweight_chat_max_tokens=VOICE_LIGHTWEIGHT_CHAT_MAX_TOKENS,
                    orch_chat_agent_timeout_sec=VOICE_CHAT_AGENT_TIMEOUT_SEC,
                    orch_reasoner_brief_timeout_sec=VOICE_REASONER_BRIEF_TIMEOUT_SEC,
                    logger=logger,
                    re_module=re,
                    session_factory=None,
                )
            )
        )
        response_text = chat_response.reply.content
        output_dir = chat_response.output_dir
        run_id = chat_response.run_id
        conversation = [
            item.model_dump() for item in chat_response.conversation
        ]

    audio_base64 = None
    audio_format = None
    if request.tts:
        try:
            audio_base64, audio_format = await asyncio.to_thread(
                _synthesize_tts,
                response_text,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"TTS 실패: {exc}")

    return VoiceResponse(
        transcript=transcript,
        response_text=response_text,
        audio_base64=audio_base64,
        audio_format=audio_format,
        output_dir=output_dir,
        run_id=run_id,
        conversation=conversation,
        detected_language=detected_language, # pyright: ignore[reportCallIssue]
    )
