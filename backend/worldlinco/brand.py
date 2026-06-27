"""WorldLinco brand constants and legacy alias matching."""

from __future__ import annotations

WORLDLINGO_BRAND_NAME = "WorldLinco"
WORLDLINGO_BRAND_NAME_KO = "월드링코"
WORLDLINGO_LEGACY_SLUG = "nadotongryoksa"
WORLDLINGO_MARKETPLACE_API_PREFIX = "/api/marketplace/nadotongryoksa"
WORLDLINGO_VOIP_CALLER_ID = "user@worldlinco"

WORLDLINGO_PROJECT_MATCH_TOKENS = (
    "worldlinco",
    "worldlingo",
    "월드링코",
    "nadotongryoksa",
    "나도통역사",
    "통번역 스위트",
    "translation-v1",
    "신세계소리새",
)

WORLDLINGO_APK_FILENAME_PREFIXES = (
    "worldlinco-v",
    "nadotongryoksa-v",
)


def _normalize_search_text(value: object) -> str:
    return str(value or "").strip().lower()


def matches_worldlinco_project_haystack(haystack: str) -> bool:
    normalized = _normalize_search_text(haystack)
    return any(token in normalized for token in WORLDLINGO_PROJECT_MATCH_TOKENS)


def matches_worldlinco_apk_filename(filename: object) -> bool:
    normalized = _normalize_search_text(filename)
    return any(prefix in normalized for prefix in WORLDLINGO_APK_FILENAME_PREFIXES)
