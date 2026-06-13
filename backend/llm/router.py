import asyncio
import base64

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.llm.loader import llm_loader
from backend.llm.voice_gateway import _synthesize_tts

router = APIRouter(prefix="/api/llm", tags=["llm-status"])


@router.get("/status")
async def get_llm_status():
    return llm_loader.get_status()


# ── WorldLinco 전용 공개 번역 엔드포인트 (인증 불필요, 소리새 독립) ──
class _MobileTranslateRequest(BaseModel):
    text: str
    from_lang: str = "ko"
    to_lang: str = "en"
    region_hint: str | None = None


class _MobileVoiceTranslateRequest(BaseModel):
    audio_base64: str | None = None
    transcript: str | None = None
    from_lang: str = "ko"
    to_lang: str = "en"
    region_hint: str | None = None
    language: str | None = None


def _decode_mobile_voice_audio(audio_base64: str) -> bytes:
    try:
        return base64.b64decode(audio_base64, validate=True)
    except Exception as exc:  # pragma: no cover
        raise ValueError("유효한 audio_base64 형식이 아닙니다") from exc


def _transcribe_mobile_voice_audio(
    audio_bytes: bytes,
    language_hint: str | None = None,
) -> tuple[str, str | None]:
    from backend.llm.voice_gateway import _run_faster_whisper

    transcript, detected_language = _run_faster_whisper(
        audio_bytes,
        language_hint,
    )
    if normalized := str(transcript or "").strip():
        return normalized, str(detected_language or "").strip() or None
    raise RuntimeError("음성 인식 결과가 비어 있습니다")


@router.post("/translate", tags=["mobile-public"])
async def mobile_translate(payload: _MobileTranslateRequest):
    """WorldLinco 모바일 앱 전용 번역 엔드포인트. 소리새와 완전 독립. 50개 언어 지원."""
    from backend.services.nadotongryoksa.translator import (
        NadoTranslator,
        SUPPORTED_LANGUAGES,
    )

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 필수")

    from_lang = payload.from_lang.lower().strip()
    to_lang = payload.to_lang.lower().strip()

    if from_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 출발 언어: {from_lang}",
        )
    if to_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 도착 언어: {to_lang}",
        )

    try:
        translator = NadoTranslator.get_instance()
        translated = translator.translate(
            text,
            from_lang=from_lang,
            to_lang=to_lang,
            region_hint=payload.region_hint,
        )
        return {
            "translated": translated,
            "engine": "nado",
            "from": from_lang,
            "to": to_lang,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"번역 오류: {exc}") from exc


@router.post("/voice-translate", tags=["mobile-public"])
async def mobile_voice_translate(payload: _MobileVoiceTranslateRequest):
    """WorldLinco 모바일 앱 전용 음성 통역 엔드포인트.

    transcript 직접 입력 또는 audio_base64 STT를 지원한다.
    """
    from backend.services.nadotongryoksa.translator import (
        NadoTranslator,
        SUPPORTED_LANGUAGES,
    )

    from_lang = payload.from_lang.lower().strip()
    to_lang = payload.to_lang.lower().strip()

    if from_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 출발 언어: {from_lang}",
        )
    if to_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 도착 언어: {to_lang}",
        )

    def normalize_voice_lang(value: str | None) -> str | None:
        normalized = str(value or "").strip().lower().replace("_", "-")
        if not normalized:
            return None
        if normalized in SUPPORTED_LANGUAGES:
            return normalized
        base = normalized.split("-")[0]
        return base if base in SUPPORTED_LANGUAGES else None

    transcript = (payload.transcript or "").strip()
    detected_language = normalize_voice_lang(
        payload.language,
    ) or normalize_voice_lang(from_lang)
    if not transcript:
        audio_base64 = (payload.audio_base64 or "").strip()
        if not audio_base64:
            raise HTTPException(status_code=400, detail="텍스트 또는 오디오 입력이 필요합니다")
        try:
            audio_bytes = _decode_mobile_voice_audio(audio_base64)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            language_hint = payload.language
            if language_hint is None or not str(language_hint).strip():
                language_hint = from_lang
            elif str(language_hint).strip().lower() == "auto":
                language_hint = None
            transcript = await asyncio.to_thread(
                _transcribe_mobile_voice_audio,
                audio_bytes,
                language_hint,
            )
            transcript, detected_language = transcript
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"STT 실패: {exc}",
            ) from exc

    effective_from_lang = normalize_voice_lang(detected_language) or from_lang

    try:
        translator = NadoTranslator.get_instance()
        translated = translator.translate(
            transcript,
            from_lang=effective_from_lang,
            to_lang=to_lang,
            region_hint=payload.region_hint,
        )
        audio_base64 = None
        audio_format = None
        try:
            (
                synthesized_audio_base64,
                synthesized_audio_format,
            ) = await asyncio.to_thread(
                _synthesize_tts,
                translated,
            )
            if synthesized_audio_base64 and str(
                synthesized_audio_format or ""
            ).startswith("audio/"):
                audio_base64 = synthesized_audio_base64
                audio_format = synthesized_audio_format
        except Exception:
            audio_base64 = None
            audio_format = None
        return {
            "original_text": transcript,
            "translated": translated,
            "engine": "nado-voice",
            "from": effective_from_lang,
            "to": to_lang,
            "detected_language": effective_from_lang,
            "audio_url": None,
            "audio_base64": audio_base64,
            "audio_format": audio_format,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"음성 통역 오류: {exc}",
        ) from exc


@router.get("/translate/languages", tags=["mobile-public"])
async def get_supported_languages():
    """WorldLinco 지원 언어 목록 반환 (50개국어)."""
    from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES

    return {
        "languages": SUPPORTED_LANGUAGES,
        "count": len(SUPPORTED_LANGUAGES),
    }


@router.get("/translate/dialect-profiles", tags=["mobile-public"])
async def get_supported_dialect_profiles():
    from backend.services.nadotongryoksa.translator import (
        SUPPORTED_DIALECT_COUNTRY_PROFILES,
    )

    return {
        "profiles": SUPPORTED_DIALECT_COUNTRY_PROFILES,
        "count": len(SUPPORTED_DIALECT_COUNTRY_PROFILES),
    }
