"""국가별·GPS 반경 관광 홍보 + 사용자(UGC) 홍보 게시판 SSOT."""
from __future__ import annotations

import json
import math
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from backend.time_utils import utcnow


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


TOURISM_COUNTRY_PROMO_PATH = _project_root() / "knowledge" / "tourism_country_promo.json"
USER_TOURISM_PROMO_PATH = _project_root() / ".runtime" / "worldlinco_user_tourism_promo.json"

DEFAULT_SPOT_RADIUS_KM = 50.0
MAX_USER_TOURISM_PROMO_ITEMS = 5000
USER_TOURISM_PROMO_DEFAULTS: Dict[str, Any] = {
    "version": 1,
    "updated_at": None,
    "posts": [],
}

TOURISM_COUNTRY_PROMO_DEFAULTS: Dict[str, Any] = {
    "version": 2,
    "updated_at": "2026-07-01T00:00:00Z",
    "updated_by": "system",
    "note": "GPS 국가 + 50km 반경 spot 만 노출. 문구는 i18n(사용자 프로그램 언어).",
    "default_radius_km": DEFAULT_SPOT_RADIUS_KM,
    "entries": {},
}


class TourismPromoEntryUpdate(BaseModel):
    enabled: Optional[bool] = None
    title: Optional[str] = Field(None, max_length=120)
    subtitle: Optional[str] = Field(None, max_length=160)
    body: Optional[str] = Field(None, max_length=800)
    cta_label: Optional[str] = Field(None, max_length=60)
    cta_action: Optional[str] = Field(None, max_length=40)
    accent_color: Optional[str] = Field(None, max_length=16)
    image_url: Optional[str] = Field(None, max_length=500)


class TourismCountryPromoUpdate(BaseModel):
    note: Optional[str] = Field(None, max_length=500)
    entries: Optional[Dict[str, TourismPromoEntryUpdate]] = None


class UserTourismPromoCreate(BaseModel):
    """로그인 사용자 홍보 게시 — 프로그램 사용자 누구나 등록 가능."""
    title: str = Field(..., min_length=1, max_length=120)
    subtitle: Optional[str] = Field(None, max_length=160)
    body: str = Field(..., min_length=1, max_length=800)
    cta_label: Optional[str] = Field(None, max_length=60)
    cta_action: Optional[str] = Field(None, max_length=500)
    country_code: str = Field(..., min_length=2, max_length=2)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    language: Optional[str] = Field(None, max_length=16)


def _deep_merge_dict(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        elif value is not None or key in patch:
            merged[key] = value
    return merged


def load_tourism_country_promo() -> Dict[str, Any]:
    path = TOURISM_COUNTRY_PROMO_PATH
    defaults = deepcopy(TOURISM_COUNTRY_PROMO_DEFAULTS)
    if not path.is_file():
        return defaults
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return defaults
        entries = raw.get("entries")
        if not isinstance(entries, dict):
            raw["entries"] = defaults["entries"]
        return _deep_merge_dict(defaults, raw)
    except (OSError, json.JSONDecodeError):
        return defaults


def save_tourism_country_promo(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = TOURISM_COUNTRY_PROMO_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def apply_tourism_country_promo_update(update: TourismCountryPromoUpdate, updated_by: str = "admin") -> Dict[str, Any]:
    current = load_tourism_country_promo()
    patch = update.model_dump(exclude_none=True)
    entries_patch = patch.pop("entries", None)
    if isinstance(entries_patch, dict):
        current_entries = dict(current.get("entries") or {})
        for country_code, entry_update in entries_patch.items():
            code = str(country_code or "").strip().upper() or "DEFAULT"
            base_entry = dict(current_entries.get(code) or {})
            if isinstance(entry_update, dict):
                base_entry.update({k: v for k, v in entry_update.items() if v is not None or k in entry_update})
            current_entries[code] = base_entry
        current["entries"] = current_entries
    merged = _deep_merge_dict(current, patch)
    merged["updated_at"] = utcnow().isoformat() + "Z"
    merged["updated_by"] = updated_by
    return save_tourism_country_promo(merged)


def _normalize_country_code(raw: Optional[str]) -> Optional[str]:
    code = str(raw or "").strip().upper()
    if len(code) == 2 and code.isalpha():
        return code
    return None


def _normalize_lang(raw: Optional[str]) -> str:
    lang = str(raw or "").strip().lower().replace("_", "-")
    if not lang:
        return "ko"
    return lang


def _lang_fallback_chain(lang: str) -> List[str]:
    chain: List[str] = []
    if lang:
        chain.append(lang)
    if "-" in lang:
        base = lang.split("-", 1)[0]
        if base and base not in chain:
            chain.append(base)
    for fallback in ("en", "ko"):
        if fallback not in chain:
            chain.append(fallback)
    return chain


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lon / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _promo_osm_map_url(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    try:
        la = float(lat)
        lo = float(lon)
    except (TypeError, ValueError):
        return None
    return f"https://www.openstreetmap.org/?mlat={la:.6f}&mlon={lo:.6f}#map=17/{la:.6f}/{lo:.6f}"


def _pick_i18n_block(i18n: Any, lang: str) -> Dict[str, str]:
    if not isinstance(i18n, dict):
        return {}
    for candidate in _lang_fallback_chain(lang):
        block = i18n.get(candidate)
        if isinstance(block, dict) and str(block.get("title") or "").strip():
            return {k: str(v or "").strip() for k, v in block.items()}
    for block in i18n.values():
        if isinstance(block, dict) and str(block.get("title") or "").strip():
            return {k: str(v or "").strip() for k, v in block.items()}
    return {}


def _legacy_entry_as_i18n(entry: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    if isinstance(entry.get("i18n"), dict):
        return entry["i18n"]
    title = str(entry.get("title") or "").strip()
    if not title:
        return {}
    block = {
        "title": title,
        "subtitle": str(entry.get("subtitle") or "").strip(),
        "body": str(entry.get("body") or "").strip(),
        "cta_label": str(entry.get("cta_label") or "").strip(),
    }
    return {"ko": block}


def _parse_spots(entry: Dict[str, Any], default_radius_km: float) -> List[Dict[str, Any]]:
    spots_raw = entry.get("spots")
    if not isinstance(spots_raw, list):
        return []
    parsed: List[Dict[str, Any]] = []
    for item in spots_raw:
        if not isinstance(item, dict):
            continue
        try:
            lat = float(item.get("lat"))
            lon = float(item.get("lon"))
        except (TypeError, ValueError):
            continue
        radius = item.get("radius_km", default_radius_km)
        try:
            radius_km = float(radius)
        except (TypeError, ValueError):
            radius_km = default_radius_km
        parsed.append(
            {
                "id": str(item.get("id") or "").strip() or f"{lat:.4f},{lon:.4f}",
                "lat": lat,
                "lon": lon,
                "radius_km": max(1.0, radius_km),
                "i18n": item.get("i18n") if isinstance(item.get("i18n"), dict) else {},
            }
        )
    return parsed


def _find_nearest_spot(
    spots: List[Dict[str, Any]],
    lat: float,
    lon: float,
) -> Optional[Tuple[Dict[str, Any], float]]:
    best: Optional[Tuple[Dict[str, Any], float]] = None
    for spot in spots:
        distance_km = _haversine_km(lat, lon, spot["lat"], spot["lon"])
        if distance_km > spot["radius_km"]:
            continue
        if best is None or distance_km < best[1]:
            best = (spot, distance_km)
    return best


def _disabled_payload(
    *,
    country_code: Optional[str],
    lang: str,
    reason: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "enabled": False,
        "reason": reason,
        "country_code": country_code,
        "language": lang,
        "version": data.get("version", 1),
        "updated_at": data.get("updated_at"),
        "title": "",
        "subtitle": "",
        "body": "",
        "cta_label": "",
        "cta_action": "none",
        "accent_color": "#1E6FE0",
        "image_url": None,
        "spot_id": None,
        "distance_km": None,
        "radius_km": None,
    }


def resolve_tourism_promo_nearby(
    *,
    country_code: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    language: Optional[str] = None,
) -> Dict[str, Any]:
    data = load_tourism_country_promo()
    lang = _normalize_lang(language)
    code = _normalize_country_code(country_code)

    if code is None:
        return _disabled_payload(country_code=None, lang=lang, reason="gps_country_required", data=data)

    if latitude is None or longitude is None:
        return _disabled_payload(country_code=code, lang=lang, reason="gps_coordinates_required", data=data)

    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return _disabled_payload(country_code=code, lang=lang, reason="gps_coordinates_invalid", data=data)

    entries = data.get("entries") if isinstance(data.get("entries"), dict) else {}
    entry = entries.get(code)
    if not isinstance(entry, dict):
        return _disabled_payload(country_code=code, lang=lang, reason="country_not_configured", data=data)

    if not bool(entry.get("enabled", True)):
        return _disabled_payload(country_code=code, lang=lang, reason="country_disabled", data=data)

    default_radius = float(data.get("default_radius_km") or DEFAULT_SPOT_RADIUS_KM)
    spots = _parse_spots(entry, default_radius)
    if not spots:
        return _disabled_payload(country_code=code, lang=lang, reason="no_spots_for_country", data=data)

    nearest = _find_nearest_spot(spots, lat, lon)
    if nearest is None:
        return _disabled_payload(country_code=code, lang=lang, reason="outside_radius", data=data)

    spot, distance_km = nearest
    text, resolved_lang = _resolve_spot_text(entry, spot, lang)
    if not text.get("title"):
        return _disabled_payload(country_code=code, lang=lang, reason="missing_translation", data=data)

    return {
        "enabled": True,
        "reason": None,
        "country_code": code,
        "language": resolved_lang,
        "version": data.get("version", 1),
        "updated_at": data.get("updated_at"),
        "title": text.get("title", ""),
        "subtitle": text.get("subtitle", ""),
        "body": text.get("body", ""),
        "cta_label": text.get("cta_label", ""),
        "cta_action": str(entry.get("cta_action") or "face_interpretation").strip(),
        "accent_color": str(entry.get("accent_color") or "#1E6FE0").strip(),
        "image_url": str(entry.get("image_url") or "").strip() or None,
        "spot_id": spot.get("id"),
        "distance_km": round(distance_km, 2),
        "radius_km": spot.get("radius_km"),
    }


def _resolve_spot_text(
    entry: Dict[str, Any],
    spot: Dict[str, Any],
    lang: str,
) -> Tuple[Dict[str, str], str]:
    i18n_root = _legacy_entry_as_i18n(entry)
    spot_i18n = spot.get("i18n") if isinstance(spot.get("i18n"), dict) else {}
    merged_i18n = {**i18n_root, **spot_i18n} if spot_i18n else i18n_root
    text = _pick_i18n_block(merged_i18n, lang)
    if not text.get("title"):
        text = _pick_i18n_block(i18n_root, lang)
    resolved_lang = lang
    for candidate in _lang_fallback_chain(lang):
        block = merged_i18n.get(candidate) or i18n_root.get(candidate)
        if isinstance(block, dict) and str(block.get("title") or "").strip() == text.get("title"):
            resolved_lang = candidate
            break
    return text, resolved_lang


def load_user_tourism_promos() -> Dict[str, Any]:
    path = USER_TOURISM_PROMO_PATH
    defaults = deepcopy(USER_TOURISM_PROMO_DEFAULTS)
    if not path.is_file():
        return defaults
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return defaults
        posts = raw.get("posts")
        if not isinstance(posts, list):
            raw["posts"] = []
        return _deep_merge_dict(defaults, raw)
    except (OSError, json.JSONDecodeError):
        return defaults


def save_user_tourism_promos(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = USER_TOURISM_PROMO_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    posts = payload.get("posts") if isinstance(payload.get("posts"), list) else []
    if len(posts) > MAX_USER_TOURISM_PROMO_ITEMS:
        posts = posts[-MAX_USER_TOURISM_PROMO_ITEMS:]
    normalized = {
        "version": int(payload.get("version") or 1),
        "updated_at": utcnow().isoformat() + "Z",
        "posts": posts,
    }
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def create_user_tourism_promo(
    *,
    user_id: int,
    author_username: str,
    payload: UserTourismPromoCreate,
) -> Dict[str, Any]:
    code = _normalize_country_code(payload.country_code)
    if code is None:
        raise ValueError("country_code_invalid")

    lat: Optional[float] = None
    lon: Optional[float] = None
    if payload.latitude is not None and payload.longitude is not None:
        try:
            lat = float(payload.latitude)
            lon = float(payload.longitude)
        except (TypeError, ValueError) as exc:
            raise ValueError("coordinates_invalid") from exc

    source_lang = _normalize_lang(payload.language)
    post = {
        "id": uuid.uuid4().hex,
        "user_id": int(user_id),
        "author_username": str(author_username or "").strip() or f"user-{user_id}",
        "country_code": code,
        "latitude": lat,
        "longitude": lon,
        "source_language": source_lang,
        "title": str(payload.title or "").strip(),
        "subtitle": str(payload.subtitle or "").strip(),
        "body": str(payload.body or "").strip(),
        "cta_label": str(payload.cta_label or "").strip(),
        "cta_action": str(payload.cta_action or "none").strip() or "none",
        "accent_color": "#E07C1E",
        "created_at": utcnow().isoformat() + "Z",
        "active": True,
    }
    if not post["title"] or not post["body"]:
        raise ValueError("title_body_required")

    current = load_user_tourism_promos()
    posts = list(current.get("posts") or [])
    posts.append(post)
    save_user_tourism_promos({**current, "posts": posts})
    return post


def _user_post_board_item(
    post: Dict[str, Any],
    *,
    viewer_lat: Optional[float],
    viewer_lon: Optional[float],
    radius_km: float,
) -> Dict[str, Any]:
    lat = post.get("latitude")
    lon = post.get("longitude")
    distance_km: Optional[float] = None
    nearby = False
    try:
        if viewer_lat is not None and viewer_lon is not None and lat is not None and lon is not None:
            distance_km = round(_haversine_km(viewer_lat, viewer_lon, float(lat), float(lon)), 2)
            nearby = distance_km <= radius_km
    except (TypeError, ValueError):
        pass

    return {
        "spot_id": None,
        "post_id": str(post.get("id") or ""),
        "source": "user",
        "author_username": str(post.get("author_username") or ""),
        "author_user_id": post.get("user_id"),
        "title": str(post.get("title") or ""),
        "subtitle": str(post.get("subtitle") or ""),
        "body": str(post.get("body") or ""),
        "cta_label": str(post.get("cta_label") or ""),
        "cta_action": str(post.get("cta_action") or "none"),
        "accent_color": str(post.get("accent_color") or "#E07C1E"),
        "image_url": None,
        "distance_km": distance_km,
        "radius_km": radius_km,
        "nearby": nearby,
        "language": str(post.get("source_language") or "ko"),
        "created_at": post.get("created_at"),
    }


def _list_user_board_items(
    country_code: str,
    *,
    viewer_lat: Optional[float],
    viewer_lon: Optional[float],
    radius_km: float,
) -> List[Dict[str, Any]]:
    data = load_user_tourism_promos()
    posts = data.get("posts") if isinstance(data.get("posts"), list) else []
    items: List[Dict[str, Any]] = []
    for raw in posts:
        if not isinstance(raw, dict) or not bool(raw.get("active", True)):
            continue
        if _normalize_country_code(raw.get("country_code")) != country_code:
            continue
        items.append(
            _user_post_board_item(
                raw,
                viewer_lat=viewer_lat,
                viewer_lon=viewer_lon,
                radius_km=radius_km,
            )
        )
    items.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return items


def _list_admin_board_items(
    code: str,
    lang: str,
    *,
    viewer_lat: Optional[float],
    viewer_lon: Optional[float],
    default_radius: float,
) -> List[Dict[str, Any]]:
    data = load_tourism_country_promo()
    entries = data.get("entries") if isinstance(data.get("entries"), dict) else {}
    entry = entries.get(code)
    if not isinstance(entry, dict) or not bool(entry.get("enabled", True)):
        return []

    spots = _parse_spots(entry, default_radius)
    items: List[Dict[str, Any]] = []
    for spot in spots:
        text, resolved_lang = _resolve_spot_text(entry, spot, lang)
        if not text.get("title"):
            continue
        distance_km: Optional[float] = None
        nearby = False
        if viewer_lat is not None and viewer_lon is not None:
            distance_km = round(_haversine_km(viewer_lat, viewer_lon, spot["lat"], spot["lon"]), 2)
            nearby = distance_km <= float(spot["radius_km"])
        items.append(
            {
                "spot_id": spot.get("id"),
                "post_id": None,
                "source": "admin",
                "author_username": None,
                "author_user_id": None,
                "title": text.get("title", ""),
                "subtitle": text.get("subtitle", ""),
                "body": text.get("body", ""),
                "cta_label": text.get("cta_label", ""),
                "cta_action": str(entry.get("cta_action") or "face_interpretation").strip(),
                "accent_color": str(entry.get("accent_color") or "#1E6FE0").strip(),
                "image_url": str(entry.get("image_url") or "").strip() or None,
                "distance_km": distance_km,
                "radius_km": spot.get("radius_km"),
                "nearby": nearby,
                "language": resolved_lang,
                "created_at": data.get("updated_at"),
            }
        )
    return items


def resolve_tourism_promo_board(
    *,
    country_code: Optional[str],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """GPS 국가 홍보 게시판 — 사용자 UGC + (선택) 관리자 spot. 좌표 있으면 거리·근접 표시."""
    data = load_tourism_country_promo()
    lang = _normalize_lang(language)
    code = _normalize_country_code(country_code)
    default_radius = float(data.get("default_radius_km") or DEFAULT_SPOT_RADIUS_KM)

    base: Dict[str, Any] = {
        "enabled": False,
        "reason": None,
        "country_code": code,
        "language": lang,
        "version": data.get("version", 1),
        "updated_at": utcnow().isoformat() + "Z",
        "user_can_post": True,
        "items": [],
    }

    if code is None:
        base["reason"] = "gps_country_required"
        return base

    viewer_lat: Optional[float] = None
    viewer_lon: Optional[float] = None
    if latitude is not None and longitude is not None:
        try:
            viewer_lat = float(latitude)
            viewer_lon = float(longitude)
        except (TypeError, ValueError):
            viewer_lat = None
            viewer_lon = None

    user_items = _list_user_board_items(
        code,
        viewer_lat=viewer_lat,
        viewer_lon=viewer_lon,
        radius_km=default_radius,
    )
    admin_items = _list_admin_board_items(
        code,
        lang,
        viewer_lat=viewer_lat,
        viewer_lon=viewer_lon,
        default_radius=default_radius,
    )

    # 사용자 홍보를 먼저, 그다음 관리자 spot(거리순).
    items = list(user_items)
    if viewer_lat is not None and viewer_lon is not None:
        admin_items.sort(key=lambda row: row["distance_km"] if row["distance_km"] is not None else 1e9)
    else:
        admin_items.sort(key=lambda row: str(row.get("spot_id") or ""))
    items.extend(admin_items)

    base["enabled"] = True
    base["items"] = items
    if not items:
        base["reason"] = "empty_board"
    return base


def _infer_promo_grounding_category(*parts: Optional[str]) -> str:
    text = " ".join(str(part or "").lower() for part in parts)
    if any(token in text for token in ("호텔", "숙소", "료칸", "게스트하우스", "hotel", "hostel", "lodging", "stay")):
        return "lodging"
    if any(token in text for token in ("마사지", "스파", "테라피", "massage", "spa", "therapy")):
        return "attraction"
    if any(token in text for token in ("카페", "커피", "cafe", "coffee")):
        return "cafe"
    if any(token in text for token in ("맛집", "식당", "음식", "restaurant", "food", "ramen", "sushi")):
        return "food"
    if any(token in text for token in ("명소", "관광", "투어", "attraction", "tour", "landmark")):
        return "attraction"
    return "promo"


def list_tourism_promo_grounding_rows(
    *,
    country_code: Optional[str],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    language: Optional[str] = None,
    radius_km: Optional[float] = None,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    code = _normalize_country_code(country_code)
    if code is None:
        return []

    lang = _normalize_lang(language)
    effective_radius = max(1.0, float(radius_km or DEFAULT_SPOT_RADIUS_KM))
    viewer_lat: Optional[float] = None
    viewer_lon: Optional[float] = None
    if latitude is not None and longitude is not None:
        try:
            viewer_lat = float(latitude)
            viewer_lon = float(longitude)
        except (TypeError, ValueError):
            viewer_lat = None
            viewer_lon = None

    rows: List[Dict[str, Any]] = []

    user_data = load_user_tourism_promos()
    user_posts = user_data.get("posts") if isinstance(user_data.get("posts"), list) else []
    for raw in user_posts:
        if not isinstance(raw, dict) or not bool(raw.get("active", True)):
            continue
        if _normalize_country_code(raw.get("country_code")) != code:
            continue
        lat = raw.get("latitude")
        lon = raw.get("longitude")
        distance_km: Optional[float] = None
        if viewer_lat is not None and viewer_lon is not None and lat is not None and lon is not None:
            try:
                distance_km = round(_haversine_km(viewer_lat, viewer_lon, float(lat), float(lon)), 2)
            except (TypeError, ValueError):
                distance_km = None
            if distance_km is not None and distance_km > effective_radius:
                continue
        rows.append(
            {
                "name": str(raw.get("title") or "").strip(),
                "address": str(raw.get("subtitle") or raw.get("body") or "").strip(),
                "distance": f"{distance_km}km" if distance_km is not None else "",
                "type": _infer_promo_grounding_category(raw.get("title"), raw.get("subtitle"), raw.get("body")),
                "source": "promo-user",
                "map_url": _promo_osm_map_url(lat, lon),
                "website": str(raw.get("cta_action") or "").strip() if str(raw.get("cta_action") or "").strip().startswith(("http://", "https://")) else "",
                "created_at": str(raw.get("created_at") or ""),
            }
        )

    country_data = load_tourism_country_promo()
    entries = country_data.get("entries") if isinstance(country_data.get("entries"), dict) else {}
    entry = entries.get(code)
    default_radius = float(country_data.get("default_radius_km") or DEFAULT_SPOT_RADIUS_KM)
    if isinstance(entry, dict) and bool(entry.get("enabled", True)):
        for spot in _parse_spots(entry, default_radius):
            text, _resolved_lang = _resolve_spot_text(entry, spot, lang)
            if not text.get("title"):
                continue
            distance_km: Optional[float] = None
            if viewer_lat is not None and viewer_lon is not None:
                distance_km = round(_haversine_km(viewer_lat, viewer_lon, spot["lat"], spot["lon"]), 2)
                if distance_km > min(float(spot.get("radius_km") or default_radius), effective_radius):
                    continue
            rows.append(
                {
                    "name": text.get("title", "").strip(),
                    "address": str(text.get("subtitle") or text.get("body") or "").strip(),
                    "distance": f"{distance_km}km" if distance_km is not None else "",
                    "type": _infer_promo_grounding_category(text.get("title"), text.get("subtitle"), text.get("body")),
                    "source": "promo-admin",
                    "map_url": _promo_osm_map_url(spot.get("lat"), spot.get("lon")),
                    "website": str(entry.get("cta_action") or "").strip() if str(entry.get("cta_action") or "").strip().startswith(("http://", "https://")) else "",
                    "created_at": str(country_data.get("updated_at") or ""),
                }
            )

    rows.sort(key=lambda row: row.get("distance") or "999999km")
    return [row for row in rows if str(row.get("name") or "").strip()][: max(1, limit)]


def tourism_country_promo_public_payload(
    country_code: Optional[str] = None,
    *,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    language: Optional[str] = None,
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    if str(mode or "").strip().lower() == "board":
        return resolve_tourism_promo_board(
            country_code=country_code,
            latitude=latitude,
            longitude=longitude,
            language=language,
        )
    return resolve_tourism_promo_nearby(
        country_code=country_code,
        latitude=latitude,
        longitude=longitude,
        language=language,
    )


def tourism_country_promo_admin_payload() -> Dict[str, Any]:
    return load_tourism_country_promo()


def list_tourism_promo_country_codes() -> List[str]:
    data = load_tourism_country_promo()
    entries = data.get("entries") if isinstance(data.get("entries"), dict) else {}
    codes = sorted(str(k).upper() for k in entries.keys() if str(k).upper() != "DEFAULT")
    return codes
