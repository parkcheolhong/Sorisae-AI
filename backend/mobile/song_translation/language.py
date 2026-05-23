# FILE-ID: FILE-BACKEND-MOBILE-SONG-TRANSLATION-LANGUAGE-PY
# SECTION-ID: SECTION-BACKEND-MOBILE-SONG-TRANSLATION-LANGUAGE-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-SONG-TRANSLATION-LANGUAGE-NORMALIZATION
# CHUNK-ID: CHUNK-BACKEND-MOBILE-SONG-TRANSLATION-LANGUAGE-001

from __future__ import annotations

from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES


WHISPER_LANG_MAP: dict[str, str] = {
    "chinese": "zh",
    "mandarin": "zh",
    "zh": "zh",
    "japanese": "ja",
    "ja": "ja",
    "korean": "ko",
    "ko": "ko",
    "english": "en",
    "en": "en",
    "spanish": "es",
    "es": "es",
    "french": "fr",
    "fr": "fr",
    "german": "de",
    "de": "de",
    "portuguese": "pt",
    "pt": "pt",
    "russian": "ru",
    "ru": "ru",
    "arabic": "ar",
    "ar": "ar",
    "hindi": "hi",
    "hi": "hi",
    "italian": "it",
    "it": "it",
    "turkish": "tr",
    "tr": "tr",
    "thai": "th",
    "th": "th",
    "vietnamese": "vi",
    "vi": "vi",
    "indonesian": "id",
    "id": "id",
    "malay": "ms",
    "ms": "ms",
    "dutch": "nl",
    "nl": "nl",
    "polish": "pl",
    "pl": "pl",
    "ukrainian": "uk",
    "uk": "uk",
    "swedish": "sv",
    "sv": "sv",
    "norwegian": "no",
    "no": "no",
    "danish": "da",
    "da": "da",
}


def normalize_language_code(value: object, *, allow_auto: bool = False, fallback: str = "ko") -> str:
    raw_value = str(value or "").strip().lower().replace("_", "-")
    if allow_auto and raw_value in {"", "auto"}:
        return "auto"
    compact = raw_value.split()[0].split(",")[0].split(";")[0].split("/")[0] if raw_value else ""
    base = compact.split("-")[0] if compact else ""
    resolved = WHISPER_LANG_MAP.get(compact) or WHISPER_LANG_MAP.get(base) or compact or fallback
    return resolved if resolved in SUPPORTED_LANGUAGES else fallback


def infer_language_from_text(text: str, fallback: str = "en") -> str:
    if any("\uac00" <= char <= "\ud7a3" for char in text):
        return "ko"
    if any("\u3040" <= char <= "\u30ff" for char in text):
        return "ja"
    if any("\u4e00" <= char <= "\u9fff" for char in text):
        return "zh"
    if any("\u0600" <= char <= "\u06ff" for char in text):
        return "ar"
    if any("\u0900" <= char <= "\u097f" for char in text):
        return "hi"
    if any("\u0400" <= char <= "\u04ff" for char in text):
        return "ru"
    if any("\u0e00" <= char <= "\u0e7f" for char in text):
        return "th"
    if any(char.isalpha() and char.isascii() for char in text):
        return "en"
    return normalize_language_code(fallback, fallback="en")
