"""WorldLinco 전문 용어집 — knowledge/worldlinco_translation_glossary.json SSOT."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_GLOSSARY_PATH = Path(__file__).resolve().parents[3] / "knowledge" / "worldlinco_translation_glossary.json"
_CACHE_TTL_S = 5.0
_cache_payload: Dict[str, Any] | None = None
_cache_ts: float = 0.0


def _load_glossary() -> Dict[str, Any]:
    global _cache_payload, _cache_ts
    now = time.monotonic()
    if _cache_payload is not None and (now - _cache_ts) < _CACHE_TTL_S:
        return _cache_payload
    if not _GLOSSARY_PATH.is_file():
        _cache_payload = {"domain_hint": "", "pairs": {}}
        _cache_ts = now
        return _cache_payload
    try:
        raw = json.loads(_GLOSSARY_PATH.read_text(encoding="utf-8"))
        _cache_payload = raw if isinstance(raw, dict) else {"domain_hint": "", "pairs": {}}
    except (OSError, json.JSONDecodeError):
        _cache_payload = {"domain_hint": "", "pairs": {}}
    _cache_ts = now
    return _cache_payload


def _pair_key(from_lang: str, to_lang: str) -> str:
    return f"{from_lang.lower().strip()}:{to_lang.lower().strip()}"


def _parse_pair_list(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "").strip()
        target = str(item.get("target") or "").strip()
        if source and target:
            out.append(item)
    return out


def _merge_via_english_pivot(from_lang: str, to_lang: str, pairs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build terminology from ko:en + en:target (or any X:en + en:Y) when direct pair is absent."""
    if from_lang == to_lang or from_lang == "en" or to_lang == "en":
        return []
    src_en = _parse_pair_list(pairs.get(_pair_key(from_lang, "en")))
    en_tgt = _parse_pair_list(pairs.get(_pair_key("en", to_lang)))
    if not src_en or not en_tgt:
        return []
    tgt_by_en = {str(item.get("source") or "").strip().lower(): item for item in en_tgt}
    merged: List[Dict[str, Any]] = []
    for item in src_en:
        en_term = str(item.get("target") or "").strip()
        match = tgt_by_en.get(en_term.lower())
        if not match:
            continue
        merged.append(
            {
                "source": item["source"],
                "target": match["target"],
                "wrong": match.get("wrong") or item.get("wrong") or [],
                "industry": item.get("industry") or match.get("industry"),
            }
        )
    return merged


def get_pair_entries(from_lang: str, to_lang: str) -> List[Dict[str, Any]]:
    pairs = (_load_glossary().get("pairs") or {})
    direct = _parse_pair_list(pairs.get(_pair_key(from_lang, to_lang)))
    if direct:
        return direct
    return _merge_via_english_pivot(from_lang, to_lang, pairs)


def domain_hint() -> str:
    return str(_load_glossary().get("domain_hint") or "").strip()


def build_llm_terminology_block(from_lang: str, to_lang: str, *, max_items: int = 36) -> str:
    entries = get_pair_entries(from_lang, to_lang)[:max_items]
    if not entries:
        return ""
    lines = [f'- "{e["source"]}" → "{e["target"]}"' for e in entries]
    return "Terminology guide (document-standard equivalents; follow strictly):\n" + "\n".join(lines)


def polish_translation(text: str, *, original: str, from_lang: str, to_lang: str) -> str:
    """Post-process: replace known non-standard variants with glossary targets."""
    out = (text or "").strip()
    if not out:
        return out
    entries = get_pair_entries(from_lang, to_lang)
    original_lower = (original or "").lower()
    for entry in entries:
        source = str(entry.get("source") or "")
        target = str(entry.get("target") or "")
        if source and source.lower() in original_lower and target and target not in out:
            wrong = entry.get("wrong") or []
            if isinstance(wrong, list):
                for variant in wrong:
                    v = str(variant or "").strip()
                    if v:
                        out = out.replace(v, target)
        wrong = entry.get("wrong") or []
        if isinstance(wrong, list) and target:
            for variant in wrong:
                v = str(variant or "").strip()
                if v and v in out:
                    out = out.replace(v, target)
    return out


def normalize_source_terms(text: str, from_lang: str, to_lang: str) -> str:
    """Optional pre-pass: unify source-side variants before MT (currently no-op hook)."""
    return text
