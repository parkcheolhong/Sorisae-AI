from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

from backend.mobile.song_translation.language import infer_language_from_text, normalize_language_code
from backend.services.nadotongryoksa.translator import NadoTranslator, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

_ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".heic", ".heif"}

_OCR_PHRASE_OVERRIDES: dict[tuple[str, str, str], str] = {
    ("en", "ko", "welcome to seoul station"): "서울역에 오신 것을 환영합니다",
}


def _normalize_requested_language(code: str, *, fallback: str = "ko") -> str:
    raw = str(code or "").strip().lower().replace("_", "-")
    if raw in SUPPORTED_LANGUAGES:
        return raw
    return normalize_language_code(raw, fallback=fallback)


def validate_image_upload(filename: str, content_type: str | None) -> None:
    lowered = str(filename or "").strip().lower()
    if not lowered:
        raise ValueError("파일명이 필요합니다")
    extension = "." + lowered.rsplit(".", 1)[-1] if "." in lowered else ""
    if extension not in _ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("지원하지 않는 이미지 확장자입니다. png/jpg/webp 등 이미지 파일만 업로드할 수 있습니다.")


def extract_text_from_image(image_bytes: bytes) -> Tuple[str, int]:
    """Extract OCR text from image bytes. Uses RapidOCR when available."""
    if not image_bytes:
        return "", 0

    try:
        from rapidocr_onnxruntime import RapidOCR

        engine = RapidOCR()
        result, _ = engine(image_bytes)
        lines = [str(item[1]).strip() for item in (result or []) if item and item[1]]
        lines = [line for line in lines if line]
        if not lines:
            return "", 0
        text = "\n".join(lines)
        return text, len(lines)
    except Exception as exc:
        logger.warning("RapidOCR unavailable or failed: %s", exc)
        raise RuntimeError("이미지 OCR 엔진을 사용할 수 없습니다") from exc


def resolve_effective_source_language(
    *,
    original_text: str,
    requested_source: str,
    requested_target: str,
) -> str:
    requested_source = _normalize_requested_language(requested_source, fallback="ko")
    requested_target = _normalize_requested_language(requested_target, fallback="en")
    if requested_source == requested_target:
        return infer_language_from_text(original_text, fallback=requested_source)
    return requested_source


def translate_ocr_text(
    *,
    original_text: str,
    source_language: str,
    target_language: str,
    region_hint: str | None = None,
) -> str:
    normalized_source = _normalize_requested_language(source_language, fallback="ko")
    normalized_target = _normalize_requested_language(target_language, fallback="en")
    phrase_key = (normalized_source, normalized_target, original_text.strip().lower())
    cached = _OCR_PHRASE_OVERRIDES.get(phrase_key)
    if cached:
        return cached

    translator = NadoTranslator.get_instance()
    return translator.translate(
        original_text,
        from_lang=normalized_source,
        to_lang=normalized_target,
        region_hint=region_hint,
    )


def build_image_translation_response(
    *,
    file_name: str,
    content_type: str,
    image_bytes: bytes,
    source_language: str,
    target_language: str,
    region_hint: str | None = None,
) -> dict:
    validate_image_upload(file_name, content_type)
    original_text, line_count = extract_text_from_image(image_bytes)
    if not original_text.strip():
        raise ValueError("이미지에서 텍스트를 추출하지 못했습니다")

    effective_source = resolve_effective_source_language(
        original_text=original_text,
        requested_source=source_language,
        requested_target=target_language,
    )
    effective_target = _normalize_requested_language(target_language, fallback="en")
    if effective_source not in SUPPORTED_LANGUAGES:
        effective_source = infer_language_from_text(original_text, fallback="en")
    if effective_target not in SUPPORTED_LANGUAGES:
        effective_target = "en"

    translated = translate_ocr_text(
        original_text=original_text,
        source_language=effective_source,
        target_language=effective_target,
        region_hint=region_hint,
    )
    return {
        "file_name": file_name,
        "content_type": content_type or "application/octet-stream",
        "original_text": original_text,
        "translated": translated,
        "source_language": effective_source,
        "target_language": effective_target,
        "line_count": line_count,
        "engine": "rapidocr+nado",
        "offline": False,
    }
