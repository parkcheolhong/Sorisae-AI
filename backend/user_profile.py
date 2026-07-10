"""WorldLinco user profile language/country normalization."""
from __future__ import annotations

from typing import Optional

from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES


def normalize_preferred_language(value: Optional[str]) -> Optional[str]:
    normalized = (value or "").strip().lower()[:16]
    if not normalized:
        return None
    return normalized if normalized in SUPPORTED_LANGUAGES else None


def normalize_country_code(value: Optional[str]) -> Optional[str]:
    normalized = (value or "").strip().upper()[:2]
    if len(normalized) != 2 or not normalized.isalpha():
        return None
    return normalized
