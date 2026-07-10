"""Shared helpers for admin bulk in-app announcements."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES, translate
from backend.user_profile import normalize_country_code, normalize_preferred_language

# Mobile countryLanguage.ts 와 정합 — 국가별 안내 번역 타겟 언어.
COUNTRY_LANG_MAP: Dict[str, str] = {
    "KR": "ko",
    "US": "en", "GB": "en", "AU": "en", "CA": "en", "NZ": "en", "IE": "en", "SG": "en", "PH": "en",
    "IN": "en", "MY": "en", "LK": "en", "KE": "en", "TZ": "en", "UG": "en",
    "NG": "en", "ZA": "en", "GH": "en", "JM": "en", "MT": "en", "CY": "en",
    "BE": "en", "CH": "en", "LU": "en", "NL": "en",
    "CN": "zh", "TW": "zh-tw", "HK": "zh-hk", "MO": "zh-hk",
    "JP": "ja",
    "ES": "es", "MX": "es", "AR": "es", "CL": "es", "CO": "es", "PE": "es",
    "FR": "fr", "DE": "de", "AT": "de", "PT": "pt", "BR": "pt",
    "RU": "ru", "SA": "ar", "AE": "ar", "EG": "ar", "QA": "ar", "KW": "ar",
    "IT": "it", "TR": "tr", "VN": "vi", "TH": "th", "ID": "id",
    "PL": "pl", "UA": "uk", "SE": "sv", "NO": "no", "DK": "da", "FI": "fi",
    "CZ": "cs", "RO": "ro", "MD": "ro", "HU": "hu", "GR": "el", "IL": "he",
    "BG": "bg", "HR": "hr", "RS": "sr", "BA": "sr", "ME": "sr",
    "SK": "sk", "SI": "sl", "LT": "lt", "LV": "lv", "EE": "et",
    "IR": "fa", "AF": "fa", "PK": "ur", "BD": "bn", "ET": "am",
}

MAX_ANNOUNCEMENT_BODY_LEN = 480
MAX_RECIPIENTS_PER_CAMPAIGN = 500


def normalize_source_lang(value: Optional[str]) -> str:
    normalized = normalize_preferred_language(value) or "ko"
    return normalized if normalized in SUPPORTED_LANGUAGES else "ko"


def resolve_user_notify_language(*, preferred_language: Optional[str], country_code: Optional[str]) -> str:
    preferred = normalize_preferred_language(preferred_language)
    if preferred:
        return preferred
    country = normalize_country_code(country_code)
    if country and country in COUNTRY_LANG_MAP:
        return COUNTRY_LANG_MAP[country]
    return "en"


def translate_for_lang(source_text: str, source_lang: str, target_lang: str, cache: Dict[str, str]) -> str:
    if target_lang == source_lang:
        return source_text
    if target_lang in cache:
        return cache[target_lang]
    try:
        translated = translate(source_text, from_lang=source_lang, to_lang=target_lang)
    except Exception:
        translated = source_text
    cache[target_lang] = translated
    return translated


def query_recipient_users(
    db: Session,
    *,
    active_only: bool,
    country_codes: Optional[Sequence[str]],
) -> List[Any]:
    from backend.marketplace.models import User

    query = db.query(User)
    if active_only:
        query = query.filter(User.is_active.is_(True))
    if country_codes:
        normalized_countries = {
            code
            for code in (normalize_country_code(item) for item in country_codes)
            if code
        }
        if normalized_countries:
            query = query.filter(User.country_code.in_(sorted(normalized_countries)))
    return query.order_by(User.id.asc()).all()


def summarize_recipients_by_language(recipients: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    for item in recipients:
        lang = str(item.get("language") or "en")
        bucket = buckets.setdefault(lang, {
            "language": lang,
            "language_label": SUPPORTED_LANGUAGES.get(lang, lang),
            "count": 0,
            "sample_body": str(item.get("body") or ""),
            "countries": set(),
        })
        bucket["count"] += 1
        country = item.get("country_code")
        if country:
            bucket["countries"].add(str(country))
    summary = []
    for lang in sorted(buckets.keys()):
        entry = buckets[lang]
        summary.append({
            "language": entry["language"],
            "language_label": entry["language_label"],
            "count": entry["count"],
            "sample_body": entry["sample_body"],
            "countries": sorted(entry["countries"]),
        })
    return summary
