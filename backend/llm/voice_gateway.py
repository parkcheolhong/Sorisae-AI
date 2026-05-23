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


def _run_faster_whisper(audio_bytes: bytes, language: Optional[str] = None) -> tuple[str, Optional[str]]:
    """Returns (transcript, detected_language). language hint prevents CJK misidentification."""
    model_name = os.getenv("FASTER_WHISPER_MODEL", "tiny")
    device = os.getenv("FASTER_WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8")

    # 앱에서 전달한 LangCode → ISO 639-1 정규화 (zh-tw → zh 등)
    lang_hint = language.split("-")[0].lower() if language else ""
    valid_langs = {
        "ko", "en", "zh", "ja", "es", "fr", "de", "pt", "ru", "ar",
        "hi", "it", "tr", "th", "vi", "id", "ms", "nl", "pl",
    }
    whisper_lang = lang_hint if lang_hint in valid_langs else None

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

model = WhisperModel(model_name, device=device, compute_type=compute_type)
kwargs = {}
if lang_hint:
    kwargs["language"] = lang_hint
segments, info = model.transcribe(audio_path, **kwargs)
transcript = " ".join((seg.text or "").strip() for seg in segments).strip()
detected = getattr(info, "language", None) or ""
print(json.dumps({"transcript": transcript, "detected_language": detected}, ensure_ascii=False))
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
        return (
            str(payload.get("transcript") or "").strip(),
            str(payload.get("detected_language") or "").strip() or None,
        )


def _synthesize_tts(text: str) -> tuple[Optional[str], Optional[str]]:
    tts_command = os.getenv("VOICE_TTS_COMMAND", "").strip()
    if not tts_command:
        return (
            base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "text/plain",
        )

    proc = subprocess.run(
        [tts_command, text],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.decode("utf-8", errors="ignore").strip()
            or "tts failed"
        )
    return base64.b64encode(proc.stdout).decode("ascii"), "audio/wav"


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
                    transcript, detected_language = await asyncio.to_thread(
                        _run_faster_whisper,
                        audio_bytes,
                        request.language,
                    )
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
