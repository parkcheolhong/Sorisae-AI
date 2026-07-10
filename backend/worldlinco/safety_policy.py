from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "tourism_safety_rules.json"

_DEFAULT_ALLOWLIST = {
    "mofa.go.kr",
    "overseas.mofa.go.kr",
    "travel.state.gov",
    "www.state.gov",
    "gov.uk",
    "www.gov.uk",
    "smarttraveller.gov.au",
    "www.canada.ca",
    "travel.gc.ca",
    "www.diplomatie.gouv.fr",
    "www.auswaertiges-amt.de",
    "www.bmeia.gv.at",
    "www.mofa.go.jp",
    "www.mofa.go.th",
    "www.mfa.gov.sg",
    "www.gov.cn",
    "www.gov.hk",
    "www.gov.mo",
    "www.gov.tw",
}


def _load_policy() -> dict[str, Any]:
    try:
        if _DATA_PATH.exists():
            raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw
    except Exception:
        return {}
    return {}


def trusted_domain_allowlist() -> set[str]:
    policy = _load_policy()
    values = policy.get("trusted_domains")
    if not isinstance(values, list):
        return set(_DEFAULT_ALLOWLIST)
    out: set[str] = set()
    for value in values:
        text = str(value or "").strip().lower()
        if text:
            out.add(text)
    return out or set(_DEFAULT_ALLOWLIST)


def is_domain_trusted(domain: Optional[str]) -> bool:
    text = str(domain or "").strip().lower()
    if not text:
        return False
    allow = trusted_domain_allowlist()
    if text in allow:
        return True
    return any(text.endswith(f".{base}") for base in allow)


def radius_risk_profile(latitude: Optional[float], longitude: Optional[float]) -> dict[str, Any]:
    policy = _load_policy()
    zones = policy.get("zones")
    if not isinstance(zones, list):
        return {
            "level": "none",
            "matched_zone": None,
            "distance_km": None,
            "radius_km": None,
        }

    try:
        lat = float(latitude)  # type: ignore[arg-type]
        lon = float(longitude)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return {
            "level": "none",
            "matched_zone": None,
            "distance_km": None,
            "radius_km": None,
        }

    import math

    def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
        r = 6371.0
        d_lat = math.radians(b_lat - a_lat)
        d_lon = math.radians(b_lon - a_lon)
        s1 = math.sin(d_lat / 2.0)
        s2 = math.sin(d_lon / 2.0)
        x = s1 * s1 + math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat)) * s2 * s2
        c = 2.0 * math.atan2(math.sqrt(x), math.sqrt(1.0 - x))
        return r * c

    best: dict[str, Any] | None = None
    best_distance: float | None = None

    for item in zones:
        if not isinstance(item, dict):
            continue
        center = item.get("center")
        if not isinstance(center, dict):
            continue
        try:
            c_lat = float(center.get("lat"))
            c_lon = float(center.get("lon"))
            radius = float(item.get("radius_km", 0))
        except (TypeError, ValueError):
            continue
        if radius <= 0:
            continue
        d = haversine_km(lat, lon, c_lat, c_lon)
        if d <= radius and (best_distance is None or d < best_distance):
            best = item
            best_distance = d

    if not best:
        return {
            "level": "none",
            "matched_zone": None,
            "distance_km": None,
            "radius_km": None,
        }

    return {
        "level": str(best.get("risk_level") or "high").lower(),
        "matched_zone": str(best.get("name") or "risk-zone"),
        "distance_km": round(float(best_distance or 0.0), 2),
        "radius_km": float(best.get("radius_km", 0.0) or 0.0),
    }
