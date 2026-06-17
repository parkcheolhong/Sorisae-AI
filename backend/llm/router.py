import asyncio
import base64
import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.llm.loader import llm_loader
from backend.llm.voice_gateway import _synthesize_tts

router = APIRouter(prefix="/api/llm", tags=["llm-status"])
logger = logging.getLogger(__name__)


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
    bilingual_mode: bool = False
    lang_a: str | None = None
    lang_b: str | None = None


def _decode_mobile_voice_audio(audio_base64: str) -> bytes:
    try:
        return base64.b64decode(audio_base64, validate=True)
    except Exception as exc:  # pragma: no cover
        raise ValueError("유효한 audio_base64 형식이 아닙니다") from exc


def _transcribe_mobile_voice_audio(
    audio_bytes: bytes,
    language_hint: str | None = None,
    source_lang_hint: str | None = None,
) -> tuple[str, str | None, dict[str, object]]:
    from backend.llm.voice_gateway import (
        _normalize_voice_audio_bytes,
        _normalize_whisper_language_hint,
        classify_voice_relay_stt_trust,
        _run_faster_whisper,
    )

    normalized_audio = _normalize_voice_audio_bytes(audio_bytes)
    hinted_language = _normalize_whisper_language_hint(language_hint)
    source_language = _normalize_whisper_language_hint(source_lang_hint)
    initial_prompt = ""
    attempts: list[str | None] = []
    if hinted_language:
        attempts.append(hinted_language)
    if source_language and source_language not in attempts:
        attempts.append(source_language)
    if None not in attempts:
        attempts.append(None)

    last_error: Exception | None = None
    best_payload: dict[str, object] | None = None
    for attempt_language in attempts:
        try:
            payload = _run_faster_whisper(
                normalized_audio,
                attempt_language,
                initial_prompt,
            )
            transcript = str(payload.get("transcript") or "").strip()
            if not transcript:
                continue
            trust = str(payload.get("stt_trust") or classify_voice_relay_stt_trust(
                transcript,
                float(payload.get("avg_logprob", -5.0)),
                float(payload.get("max_no_speech_prob", 1.0)),
            ))
            if trust == "low":
                continue
            best_payload = payload
            break
        except Exception as exc:
            last_error = exc

    if best_payload is not None:
        transcript = str(best_payload.get("transcript") or "").strip()
        detected = str(best_payload.get("detected_language") or "").strip() or None
        return transcript, detected, best_payload

    if last_error is not None:
        raise RuntimeError(str(last_error)) from last_error
    raise RuntimeError("음성이 감지되지 않았습니다. 다시 말씀해 주세요.")


def _normalize_voice_lang_code(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower().replace("_", "-")
    if not normalized:
        return None
    from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES

    if normalized in SUPPORTED_LANGUAGES:
        return normalized
    base = normalized.split("-")[0]
    return base if base in SUPPORTED_LANGUAGES else None


def _voice_lang_codes_equivalent(left: str | None, right: str | None) -> bool:
    normalized_left = _normalize_voice_lang_code(left)
    normalized_right = _normalize_voice_lang_code(right)
    if not normalized_left or not normalized_right:
        return False
    if normalized_left == normalized_right:
        return True
    return normalized_left.split("-")[0] == normalized_right.split("-")[0]


def _transcribe_bilingual_voice_audio(
    audio_bytes: bytes,
    lang_a: str,
    lang_b: str,
) -> tuple[str, str | None, dict[str, object]]:
    from backend.llm.voice_gateway import (
        _normalize_voice_audio_bytes,
        _normalize_whisper_language_hint,
        classify_voice_relay_stt_trust,
        _run_faster_whisper,
    )

    normalized_audio = _normalize_voice_audio_bytes(audio_bytes)
    attempts: list[str | None] = []
    for lang in (lang_a, lang_b):
        hint = _normalize_whisper_language_hint(lang)
        if hint and hint not in attempts:
            attempts.append(hint)
    if None not in attempts:
        attempts.append(None)

    last_error: Exception | None = None
    best_payload: dict[str, object] | None = None
    best_score = -999.0
    for attempt_language in attempts:
        try:
            payload = _run_faster_whisper(
                normalized_audio,
                attempt_language,
                "",
            )
            transcript = str(payload.get("transcript") or "").strip()
            if not transcript:
                continue
            trust = str(payload.get("stt_trust") or classify_voice_relay_stt_trust(
                transcript,
                float(payload.get("avg_logprob", -5.0)),
                float(payload.get("max_no_speech_prob", 1.0)),
            ))
            if trust == "low":
                continue
            detected = _normalize_voice_lang_code(
                str(payload.get("detected_language") or "").strip() or None,
            )
            match_bonus = 0.0
            if _voice_lang_codes_equivalent(detected, lang_a) or _voice_lang_codes_equivalent(
                detected,
                lang_b,
            ):
                match_bonus = 0.75
            score = float(payload.get("avg_logprob", -5.0)) + match_bonus
            if score > best_score:
                best_score = score
                best_payload = payload
        except Exception as exc:
            last_error = exc

    if best_payload is not None:
        transcript = str(best_payload.get("transcript") or "").strip()
        detected = str(best_payload.get("detected_language") or "").strip() or None
        return transcript, detected, best_payload

    if last_error is not None:
        raise RuntimeError(str(last_error)) from last_error
    raise RuntimeError("음성이 감지되지 않았습니다. 다시 말씀해 주세요.")


def _resolve_bilingual_route(
    *,
    detected_language: str | None,
    transcript: str,
    lang_a: str,
    lang_b: str,
) -> tuple[str, str] | None:
    from backend.designated_language import text_matches_designated_language

    detected = _normalize_voice_lang_code(detected_language)
    if _voice_lang_codes_equivalent(detected, lang_a):
        return lang_a, lang_b
    if _voice_lang_codes_equivalent(detected, lang_b):
        return lang_b, lang_a

    a_matches = text_matches_designated_language(transcript, lang_a, min_match_ratio=0.55)
    b_matches = text_matches_designated_language(transcript, lang_b, min_match_ratio=0.55)
    if a_matches and not b_matches:
        return lang_a, lang_b
    if b_matches and not a_matches:
        return lang_b, lang_a
    return None


def _is_likely_silence_hallucination(transcript: str, source_lang: str) -> bool:
    normalized = " ".join(str(transcript or "").strip().lower().split())
    if not normalized:
        return True
    lang = str(source_lang or "en").strip().lower().split("-")[0] or "en"
    patterns = {
        "en": (
            r"^hello\.?$",
            r"^hi\.?$",
            r"^hey\.?$",
            r"^you\.?$",
            r"^thank you\.?$",
            r"^thanks\.?$",
            r"^ok(?:ay)?\.?$",
            r"^bye\.?$",
            r"^um+\.?$",
            r"^uh+\.?$",
            r"^hmm+\.?$",
        ),
        "ko": (
            r"^안녕(?:하세요|히)?\.?$",
            r"^너\.?$",
            r"^음+\.?$",
            r"^어+\.?$",
        ),
    }.get(lang, ())

    if any(re.fullmatch(pattern, normalized) for pattern in patterns):
        return True
    if lang == "en" and len(normalized) <= 3:
        return True
    return False


_WHISPER_NOISE_SCRIPT_PATTERNS = (
    re.compile(r"[\u10A0-\u10FF]"),  # Georgian
    re.compile(r"[\u0530-\u058F]"),  # Armenian
    re.compile(r"[\u1200-\u137F]"),  # Ethiopic
    re.compile(r"[\u2C00-\u2C5F]"),  # Glagolitic
)

_RELAY_LANG_CHAR_CHECKS: dict[str, re.Pattern[str]] = {
    "ko": re.compile(r"[\uAC00-\uD7A3\u3131-\u318E]"),
    "en": re.compile(r"[A-Za-z]"),
    "ja": re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]"),
    "zh": re.compile(r"[\u4E00-\u9FFF]"),
    "vi": re.compile(r"[\u00C0-\u024FA-Za-z\u1E00-\u1EFF]"),
    "th": re.compile(r"[\u0E00-\u0E7F]"),
    "ar": re.compile(r"[\u0600-\u06FF]"),
    "ru": re.compile(r"[\u0400-\u04FF]"),
}

_RELAY_NEUTRAL_CHAR = re.compile(r"[\s\d\.,!?;:'\"()\[\]{}<>/\\|@#$%^&*+=~`\-—…·]")


def _normalize_relay_lang_code(lang: str | None) -> str:
    return str(lang or "").strip().lower().split("-")[0]


def _char_matches_relay_langs(char: str, langs: set[str]) -> bool:
    if _RELAY_NEUTRAL_CHAR.fullmatch(char):
        return True
    for lang in langs:
        pattern = _RELAY_LANG_CHAR_CHECKS.get(lang)
        if pattern and pattern.search(char):
            return True
        if lang not in _RELAY_LANG_CHAR_CHECKS and re.search(r"[A-Za-z\u00C0-\u024F]", char):
            return True
    return False


_WELSH_HALLUCINATION = re.compile(r"\b(?:rwy'n|rwyf|ddweud|dweud)\b", re.IGNORECASE)


def _contains_unexpected_noise_script(text: str, expected_langs: set[str]) -> bool:
    if expected_langs & {"ka", "hy", "am", "cy"}:
        return False
    if _WELSH_HALLUCINATION.search(text):
        return True
    return any(pattern.search(text) for pattern in _WHISPER_NOISE_SCRIPT_PATTERNS)


def _is_likely_gibberish_relay_transcript(
    transcript: str,
    *expected_langs: str | None,
) -> bool:
    trimmed = str(transcript or "").strip()
    if not trimmed:
        return True
    if "\ufffd" in trimmed:
        return True

    langs = {_normalize_relay_lang_code(lang) for lang in expected_langs if _normalize_relay_lang_code(lang)}
    if not langs:
        langs = {"en"}

    if _contains_unexpected_noise_script(trimmed, langs):
        return True

    compact = _RELAY_NEUTRAL_CHAR.sub("", trimmed)
    if not compact:
        return True
    if re.search(r"(.)\1{3,}", compact):
        return True

    letter_like = [char for char in compact if not _RELAY_NEUTRAL_CHAR.fullmatch(char)]
    if not letter_like:
        return True

    allowed = sum(1 for char in letter_like if _char_matches_relay_langs(char, langs))
    ratio = allowed / len(letter_like)
    # Ratio-only rejection: keep strict for obvious noise, lenient for mixed/natural speech.
    if ratio < 0.35:
        return True
    return False


def _collapse_repeated_relay_phrases(text: str, min_repeat: int = 3) -> str:
    import re

    trimmed = re.sub(r"\s+", " ", str(text or "").strip())
    if not trimmed:
        return ""
    sentence_parts = [
        part.strip().rstrip(".!?。")
        for part in re.split(r"\.\s+", trimmed)
        if part.strip()
    ]
    if len(sentence_parts) >= min_repeat:
        first_norm = sentence_parts[0].casefold()
        if all(part.casefold() == first_norm for part in sentence_parts):
            return sentence_parts[0]
    comma_parts = [part.strip() for part in trimmed.split(", ") if part.strip()]
    if len(comma_parts) >= min_repeat:
        first_norm = comma_parts[0].casefold()
        if all(part.casefold() == first_norm for part in comma_parts):
            return comma_parts[0]
    return trimmed


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
    bilingual_mode = bool(payload.bilingual_mode)
    lang_a = _normalize_voice_lang_code(payload.lang_a or from_lang) or from_lang
    lang_b = _normalize_voice_lang_code(payload.lang_b or to_lang) or to_lang
    if bilingual_mode:
        from_lang = lang_a
        to_lang = lang_b

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
    if bilingual_mode:
        if lang_a == lang_b:
            raise HTTPException(
                status_code=400,
                detail="대면 통역에는 서로 다른 두 언어가 필요합니다.",
            )
        if lang_a not in SUPPORTED_LANGUAGES or lang_b not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail="대면 통역 언어 쌍이 지원 범위를 벗어났습니다.",
            )

    def normalize_voice_lang(value: str | None) -> str | None:
        return _normalize_voice_lang_code(value)

    transcript = (payload.transcript or "").strip()
    detected_language = normalize_voice_lang(
        payload.language,
    ) or normalize_voice_lang(from_lang)
    stt_meta: dict[str, object] = {}
    if not transcript:
        audio_base64 = (payload.audio_base64 or "").strip()
        if not audio_base64:
            raise HTTPException(status_code=400, detail="텍스트 또는 오디오 입력이 필요합니다")
        try:
            audio_bytes = _decode_mobile_voice_audio(audio_base64)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            if bilingual_mode:
                transcript, detected_language, stt_meta = await asyncio.to_thread(
                    _transcribe_bilingual_voice_audio,
                    audio_bytes,
                    lang_a,
                    lang_b,
                )
            else:
                language_hint = payload.language
                if language_hint is None or not str(language_hint).strip() or str(language_hint).strip().lower() == "auto":
                    language_hint = from_lang
                transcript, detected_language, stt_meta = await asyncio.to_thread(
                    _transcribe_mobile_voice_audio,
                    audio_bytes,
                    language_hint,
                    from_lang,
                )
        except Exception as exc:
            message = str(exc)
            status_code = 422 if (
                "너무 짧습니다" in message
                or "음성이 감지되지 않았습니다" in message
            ) else 400
            raise HTTPException(
                status_code=status_code,
                detail=message if status_code == 422 else f"STT 실패: {message}",
            ) from exc

    detected_from_lang = normalize_voice_lang(detected_language)
    if not detected_from_lang:
        detected_from_lang = normalize_voice_lang(from_lang)

    if bilingual_mode:
        routed = _resolve_bilingual_route(
            detected_language=detected_from_lang,
            transcript=transcript,
            lang_a=lang_a,
            lang_b=lang_b,
        )
        if routed is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{lang_a}/{lang_b} 중 하나로 말씀해 주세요. "
                    "감지된 언어가 대면 통역 언어 쌍과 일치하지 않습니다."
                ),
            )
        effective_from_lang, effective_to_lang = routed
    else:
        if detected_from_lang and not _voice_lang_codes_equivalent(detected_from_lang, from_lang):
            logger.warning(
                "[voice-translate] designated language mismatch client_from=%s detected=%s",
                from_lang,
                detected_from_lang,
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    "지정 언어와 다른 언어가 감지되었습니다. "
                    "프로필에서 설정한 언어로만 말씀해 주세요. "
                    "필요하면 설정에서 언어를 변경할 수 있습니다."
                ),
            )
        effective_from_lang = from_lang
        effective_to_lang = to_lang

    # Silence hallucination filtering is applied on mobile for meter-dead / fixed-interval
    # captures only. Backend accepts short natural utterances from real speech segments.

    if _is_likely_gibberish_relay_transcript(
        transcript,
        effective_from_lang,
        effective_to_lang,
        from_lang,
        to_lang,
    ):
        logger.info(
            "[voice-translate] rejected gibberish transcript from=%s to=%s text=%r",
            effective_from_lang,
            effective_to_lang,
            transcript,
        )
        raise HTTPException(
            status_code=422,
            detail="음성이 감지되지 않았습니다. 다시 말씀해 주세요.",
        )

    transcript = _collapse_repeated_relay_phrases(transcript)

    logger.info(
        "[voice-translate] stt from=%s to=%s detected=%s transcript=%r",
        from_lang,
        to_lang,
        detected_from_lang or effective_from_lang,
        (transcript[:120] + "…") if len(transcript) > 120 else transcript,
    )

    try:
        translator = NadoTranslator.get_instance()
        translated = translator.translate(
            transcript,
            from_lang=effective_from_lang,
            to_lang=effective_to_lang,
            region_hint=payload.region_hint,
        )
        translated = _collapse_repeated_relay_phrases(translated)
        if _is_likely_gibberish_relay_transcript(
            translated,
            effective_from_lang,
            effective_to_lang,
            from_lang,
            to_lang,
        ):
            logger.info(
                "[voice-translate] rejected gibberish translation from=%s to=%s text=%r",
                effective_from_lang,
                effective_to_lang,
                translated,
            )
            raise HTTPException(
                status_code=422,
                detail="음성이 감지되지 않았습니다. 다시 말씀해 주세요.",
            )
        logger.info(
            "[voice-translate] translated from=%s to=%s text=%r",
            effective_from_lang,
            effective_to_lang,
            (translated[:120] + "…") if len(translated) > 120 else translated,
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
                effective_to_lang,
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
            "to": effective_to_lang,
            "detected_language": detected_from_lang or effective_from_lang,
            "audio_url": None,
            "audio_base64": audio_base64,
            "audio_format": audio_format,
            "tts_delivery": "server_audio" if audio_base64 else "device_speech",
            "stt_trust": str(stt_meta.get("stt_trust") or "high"),
            "stt_avg_logprob": float(stt_meta.get("avg_logprob", 0.0)) if stt_meta else None,
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
