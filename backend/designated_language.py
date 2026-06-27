"""Strict designated-language checks for WorldLinco VoIP and chat."""
from __future__ import annotations

import re
from typing import Optional

from backend.user_profile import normalize_preferred_language

_RELAY_NEUTRAL_CHAR = re.compile(
    r"[\s\d.,!?;:'\"()\[\]{}<>/\\|@#$%^&*+=~`\-—…·]"
)
_RELAY_LANG_CHAR_CHECKS: dict[str, re.Pattern[str]] = {
    "ko": re.compile(r"[\uAC00-\uD7A3\u3131-\u318E]"),
    "en": re.compile(r"[A-Za-z]"),
    "ja": re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]"),
    "zh": re.compile(r"[\u4E00-\u9FFF]"),
    "zh-tw": re.compile(r"[\u4E00-\u9FFF]"),
    "vi": re.compile(r"[\u00C0-\u024FA-Za-z\u1E00-\u1EFF]"),
    "th": re.compile(r"[\u0E00-\u0E7F]"),
    "ar": re.compile(r"[\u0600-\u06FF]"),
    "ru": re.compile(r"[\u0400-\u04FF]"),
}

DESIGNATED_LANGUAGE_MISMATCH_DETAIL = (
    "지정 언어와 다른 언어가 감지되었습니다. "
    "프로필에서 설정한 언어로만 말씀하거나 입력해 주세요. "
    "필요하면 설정에서 언어를 변경할 수 있습니다."
)


def _normalize_designated_language(value: Optional[str]) -> Optional[str]:
    normalized = normalize_preferred_language(value)
    if not normalized:
        return None
    return normalized.split("-")[0]


def _char_matches_designated_language(char: str, designated_lang: str) -> bool:
    if _RELAY_NEUTRAL_CHAR.fullmatch(char):
        return True
    pattern = _RELAY_LANG_CHAR_CHECKS.get(designated_lang)
    if pattern and pattern.search(char):
        return True
    if designated_lang not in _RELAY_LANG_CHAR_CHECKS and re.search(
        r"[A-Za-z\u00C0-\u024F]", char
    ):
        return True
    return False


def text_matches_designated_language(
    text: str,
    designated_lang: Optional[str],
    *,
    min_match_ratio: float = 0.70,
) -> bool:
    normalized_lang = _normalize_designated_language(designated_lang)
    trimmed = str(text or "").strip()
    if not trimmed:
        return False
    if not normalized_lang:
        return True

    compact = _RELAY_NEUTRAL_CHAR.sub("", trimmed)
    if not compact:
        return True

    letter_like = [
        char for char in compact if not _RELAY_NEUTRAL_CHAR.fullmatch(char)
    ]
    if not letter_like:
        return True

    allowed = sum(
        1
        for char in letter_like
        if _char_matches_designated_language(char, normalized_lang)
    )
    return (allowed / len(letter_like)) >= min_match_ratio


def detected_language_matches_designated(
    detected_lang: Optional[str],
    designated_lang: Optional[str],
) -> bool:
    normalized_detected = _normalize_designated_language(detected_lang)
    normalized_designated = _normalize_designated_language(designated_lang)
    if not normalized_designated:
        return True
    if not normalized_detected:
        return True
    return normalized_detected == normalized_designated
