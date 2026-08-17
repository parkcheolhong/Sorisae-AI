from __future__ import annotations

from typing import List
import re


_WORD_PATTERN = re.compile(r"[A-Za-z0-9가-힣][A-Za-z0-9가-힣_\-]{1,}")
_STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "your",
    "http", "https", "www", "com", "api", "image", "video", "final",
    "preview", "생성", "결과", "프로젝트", "기능", "기본", "요청", "사용",
}


def _normalize_prompt(prompt: str) -> str:
    return re.sub(r"\s+", " ", str(prompt or "")).strip()


def extract_prompt_keywords(prompt: str, limit: int = 8) -> List[str]:
    normalized = _normalize_prompt(prompt)
    if not normalized:
        return []

    seen = set()
    keywords: List[str] = []
    for token in _WORD_PATTERN.findall(normalized.lower()):
        if token in _STOP_WORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def summarize_prompt(prompt: str, max_length: int = 140) -> str:
    normalized = _normalize_prompt(prompt)
    if not normalized:
        return ""
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 1].rstrip() + "…"
