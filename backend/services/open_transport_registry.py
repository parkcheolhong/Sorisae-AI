from __future__ import annotations

import csv
import io
import json
import os
import base64
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.services.realtime_cache import cached_fetch


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


OPEN_TRANSPORT_REGISTRY_PATH = _project_root() / "knowledge" / "open_transport_feed_registry.json"
GTFS_JP_FIXED_URL_CSV = "https://raw.githubusercontent.com/tshimada291/gtfs-jp-list-datecheck/main/GTFS_fixedURL.csv"

_STOP_QUERY_ALIASES: dict[str, list[str]] = {
    "신주쿠": ["新宿"],
    "다이몬": ["大門"],
    "도에이": ["都営"],
}

_JP_AUTO_FEED_PREFERENCES = (
    ("東京都交通局　都営バス", "https://api-public.odpt.org/api/v4/files/Toei/data/ToeiBus-GTFS.zip"),
    ("台東区コミュニティバス", "https://api-public.odpt.org/api/v4/files/odpt/TokyoTaitoCity/megurinCCBY40.zip?date=latest"),
    ("西東京市はなバス", "https://api-public.odpt.org/api/v4/files/odpt/NishitokyoCity/AllLines.zip?date=latest"),
)
_JP_AUTO_FEED_PREFCODES = {"12", "13"}
_JP_AUTO_FEED_KEYWORDS = ("鉄道", "Train", "バス", "Bus", "コミュニティ", "都営", "Tokyo", "京成")
_JP_AUTO_FEED_MAX_ITEMS = 8


@dataclass
class TransportScheduleOption:
    provider_id: str
    provider_label: str
    route_label: str
    origin_stop: str
    destination_stop: str
    departure_local: str
    arrival_local: str
    trip_headsign: str
    source_url: str


def load_open_transport_registry() -> dict[str, Any]:
    defaults: dict[str, Any] = {"version": 1, "feeds": []}
    if not OPEN_TRANSPORT_REGISTRY_PATH.is_file():
        return defaults
    try:
        raw = json.loads(OPEN_TRANSPORT_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(raw, dict):
        return defaults
    feeds = raw.get("feeds")
    if not isinstance(feeds, list):
        raw["feeds"] = []
    return {**defaults, **raw}


def _normalize_country_code(value: Optional[str]) -> Optional[str]:
    code = str(value or "").strip().upper()
    return code if len(code) == 2 and code.isalpha() else None


def _resolve_feed_url(feed: dict[str, Any]) -> str:
    direct = str(feed.get("feed_url") or "").strip()
    if direct:
        return direct
    env_name = str(feed.get("feed_url_env") or "").strip()
    if not env_name:
        return ""
    return str(os.getenv(env_name, "")).strip()


def list_transport_feeds(country_code: Optional[str]) -> list[dict[str, Any]]:
    code = _normalize_country_code(country_code)
    if code is None:
        return []
    registry = load_open_transport_registry()
    feeds = registry.get("feeds") if isinstance(registry.get("feeds"), list) else []
    out: list[dict[str, Any]] = []
    for raw in feeds:
        if not isinstance(raw, dict):
            continue
        if _normalize_country_code(raw.get("country_code")) != code:
            continue
        merged = dict(raw)
        merged["resolved_feed_url"] = _resolve_feed_url(raw)
        out.append(merged)
    if code == "JP":
        existing_urls = {str(item.get("resolved_feed_url") or "").strip() for item in out}
        for feed in _load_public_gtfs_jp_auto_feeds(max_items=_JP_AUTO_FEED_MAX_ITEMS):
            url = str(feed.get("resolved_feed_url") or "").strip()
            if not url or url in existing_urls:
                continue
            existing_urls.add(url)
            out.append(feed)
    return out


def _load_public_gtfs_jp_auto_feeds(max_items: int = _JP_AUTO_FEED_MAX_ITEMS) -> list[dict[str, Any]]:
    def _fetch() -> str:
        request = urllib.request.Request(
            GTFS_JP_FIXED_URL_CSV,
            headers={"User-Agent": "SorisaeAI/1.0 (open transport registry)"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8-sig", errors="replace")

    try:
        csv_text = cached_fetch("web", ("gtfs-jp-fixed-url", GTFS_JP_FIXED_URL_CSV), _fetch, ttl=86400)
    except Exception:
        return []
    if not isinstance(csv_text, str) or not csv_text.strip():
        return []

    reader = csv.DictReader(io.StringIO(csv_text))
    candidates: list[dict[str, Any]] = []
    for row in reader:
        prefcode = str(row.get("prefcode") or "").strip()
        label = str(row.get("label") or "").strip()
        url = str(row.get("fixed_current_url") or "").strip()
        license_name = str(row.get("license_name") or "").strip()
        if prefcode not in _JP_AUTO_FEED_PREFCODES or not url:
            continue
        if not (license_name.startswith("CC") or "オープンデータ" in license_name):
            continue
        candidates.append({
            "prefcode": prefcode,
            "label": label,
            "url": url,
        })

    out: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for preferred_label, fallback_url in _JP_AUTO_FEED_PREFERENCES:
        matched = next((row for row in candidates if preferred_label in str(row.get("label") or "")), None)
        chosen_url = str((matched or {}).get("url") or fallback_url).strip()
        if not chosen_url or chosen_url in seen_urls:
            continue
        seen_urls.add(chosen_url)
        out.append(
            {
                "id": f"jp-auto-{len(out) + 1}",
                "country_code": "JP",
                "label": preferred_label,
                "provider": "gtfs_schedule",
                "mode": "rail_bus_ferry",
                "resolved_feed_url": chosen_url,
                "website": "https://tshimada291.github.io/gtfs-jp-list-datecheck/GTFS_fixedURL_LastModified.csv",
                "timezone": "Asia/Tokyo",
            }
        )
        if len(out) >= max_items:
            break

    if len(out) < max_items:
        ranked = sorted(
            candidates,
            key=lambda row: (
                0 if any(keyword in str(row.get("label") or "") for keyword in _JP_AUTO_FEED_KEYWORDS) else 1,
                str(row.get("prefcode") or ""),
                str(row.get("label") or ""),
            ),
        )
        for row in ranked:
            chosen_url = str(row.get("url") or "").strip()
            label = str(row.get("label") or "").strip()
            if not chosen_url or chosen_url in seen_urls:
                continue
            seen_urls.add(chosen_url)
            out.append(
                {
                    "id": f"jp-auto-{len(out) + 1}",
                    "country_code": "JP",
                    "label": label,
                    "provider": "gtfs_schedule",
                    "mode": "rail_bus_ferry",
                    "resolved_feed_url": chosen_url,
                    "website": "https://tshimada291.github.io/gtfs-jp-list-datecheck/GTFS_fixedURL_LastModified.csv",
                    "timezone": "Asia/Tokyo",
                }
            )
            if len(out) >= max_items:
                break
    return out


def _read_feed_bytes(feed_url: str) -> bytes:
    def _fetch() -> str:
        if feed_url.startswith(("http://", "https://")):
            request = urllib.request.Request(
                feed_url,
                headers={"User-Agent": "SorisaeAI/1.0 (open transport registry)"},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = response.read()
        else:
            payload = Path(feed_url).read_bytes()
        return base64.b64encode(payload).decode("ascii")

    encoded = cached_fetch("transport", (feed_url,), _fetch, ttl=1800)
    if isinstance(encoded, str):
        return base64.b64decode(encoded.encode("ascii"))
    if isinstance(encoded, bytes):
        return encoded
    return b""


def _read_gtfs_table(archive_bytes: bytes, filename: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
        try:
            raw = zf.read(filename)
        except KeyError:
            return []
    text = raw.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def _service_active_today(
    service_id: str,
    calendar_rows: list[dict[str, str]],
    calendar_date_rows: list[dict[str, str]],
    today: date,
) -> bool:
    ymd = today.strftime("%Y%m%d")
    for row in calendar_date_rows:
        if str(row.get("service_id") or "") != service_id:
            continue
        if str(row.get("date") or "") != ymd:
            continue
        if str(row.get("exception_type") or "") == "1":
            return True
        if str(row.get("exception_type") or "") == "2":
            return False

    weekday_key = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][today.weekday()]
    for row in calendar_rows:
        if str(row.get("service_id") or "") != service_id:
            continue
        start = str(row.get("start_date") or "")
        end = str(row.get("end_date") or "")
        if start and ymd < start:
            return False
        if end and ymd > end:
            return False
        return str(row.get(weekday_key) or "0") == "1"
    return not calendar_rows


def _seconds_from_gtfs_time(value: str) -> Optional[int]:
    parts = str(value or "").strip().split(":")
    if len(parts) != 3:
        return None
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _find_stop_ids(stops: list[dict[str, str]], query: str) -> list[str]:
    norm = str(query or "").strip().lower()
    if not norm:
        return []
    variants = {norm}
    for alias in _STOP_QUERY_ALIASES.get(norm, []):
        variants.add(alias.lower())
    if norm.endswith("역") and len(norm) > 1:
        variants.add(norm[:-1])
    exact_ids: list[str] = []
    fuzzy_ids: list[str] = []
    for row in stops:
        stop_name = str(row.get("stop_name") or "").strip().lower()
        stop_id = str(row.get("stop_id") or "").strip()
        if not stop_name or not stop_id:
            continue
        if stop_name in variants:
            exact_ids.append(stop_id)
            continue
        if any(variant and variant in stop_name for variant in variants):
            fuzzy_ids.append(stop_id)
    return exact_ids or fuzzy_ids


def _format_hhmm(seconds_value: int) -> str:
    hours = (seconds_value // 3600) % 24
    minutes = (seconds_value % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def _resolve_feed_timezone(name: str) -> Optional[ZoneInfo]:
    zone_name = str(name or "").strip()
    if not zone_name:
        return None
    try:
        return ZoneInfo(zone_name)
    except ZoneInfoNotFoundError:
        return None


def _load_feed_tables(feed: dict[str, Any]) -> Optional[dict[str, Any]]:
    feed_url = str(feed.get("resolved_feed_url") or "").strip()
    if not feed_url:
        return None
    try:
        archive_bytes = _read_feed_bytes(feed_url)
    except Exception:
        return None

    stops = _read_gtfs_table(archive_bytes, "stops.txt")
    routes = _read_gtfs_table(archive_bytes, "routes.txt")
    trips = _read_gtfs_table(archive_bytes, "trips.txt")
    stop_times = _read_gtfs_table(archive_bytes, "stop_times.txt")
    calendar_rows = _read_gtfs_table(archive_bytes, "calendar.txt")
    calendar_date_rows = _read_gtfs_table(archive_bytes, "calendar_dates.txt")
    if not stops or not trips or not stop_times:
        return None

    route_map = {str(row.get("route_id") or ""): row for row in routes}
    trip_map = {str(row.get("trip_id") or ""): row for row in trips}
    stop_map = {str(row.get("stop_id") or ""): row for row in stops}
    grouped_times: dict[str, list[dict[str, str]]] = {}
    route_stop_ids: dict[str, set[str]] = {}
    for row in stop_times:
        trip_id = str(row.get("trip_id") or "").strip()
        if not trip_id:
            continue
        grouped_times.setdefault(trip_id, []).append(row)
    for rows in grouped_times.values():
        rows.sort(key=lambda row: int(str(row.get("stop_sequence") or "0") or 0))
    for trip_id, rows in grouped_times.items():
        trip = trip_map.get(trip_id)
        if not isinstance(trip, dict):
            continue
        route_id = str(trip.get("route_id") or "").strip()
        if not route_id:
            continue
        bucket = route_stop_ids.setdefault(route_id, set())
        for row in rows:
            stop_id = str(row.get("stop_id") or "").strip()
            if stop_id:
                bucket.add(stop_id)

    return {
        "stops": stops,
        "route_map": route_map,
        "trip_map": trip_map,
        "stop_map": stop_map,
        "grouped_times": grouped_times,
        "route_stop_ids": route_stop_ids,
        "calendar_rows": calendar_rows,
        "calendar_date_rows": calendar_date_rows,
    }


def _route_label(route: dict[str, str], trip: dict[str, str]) -> str:
    return str(route.get("route_long_name") or route.get("route_short_name") or trip.get("trip_headsign") or "교통편").strip()


def _iter_direct_trip_options(
    *,
    feed: dict[str, Any],
    tables: dict[str, Any],
    origin_ids: set[str],
    destination_ids: set[str],
    current_secs: int,
    today: date,
    route_id_filter: Optional[str] = None,
) -> list[TransportScheduleOption]:
    results: list[TransportScheduleOption] = []
    for trip_id, stop_rows in tables["grouped_times"].items():
        trip = tables["trip_map"].get(trip_id)
        if not isinstance(trip, dict):
            continue
        route_id = str(trip.get("route_id") or "").strip()
        if route_id_filter and route_id != route_id_filter:
            continue
        service_id = str(trip.get("service_id") or "")
        if service_id and not _service_active_today(service_id, tables["calendar_rows"], tables["calendar_date_rows"], today):
            continue

        origin_row = None
        dest_row = None
        for row in stop_rows:
            stop_id = str(row.get("stop_id") or "").strip()
            if origin_row is None and stop_id in origin_ids:
                origin_row = row
            if stop_id in destination_ids:
                dest_row = row
            if origin_row is not None and dest_row is not None:
                try:
                    if int(str(dest_row.get("stop_sequence") or "0")) > int(str(origin_row.get("stop_sequence") or "0")):
                        break
                except ValueError:
                    break
        if origin_row is None or dest_row is None:
            continue
        try:
            if int(str(dest_row.get("stop_sequence") or "0")) <= int(str(origin_row.get("stop_sequence") or "0")):
                continue
        except ValueError:
            continue

        dep_secs = _seconds_from_gtfs_time(str(origin_row.get("departure_time") or ""))
        arr_secs = _seconds_from_gtfs_time(str(dest_row.get("arrival_time") or ""))
        if dep_secs is None or arr_secs is None or dep_secs < current_secs:
            continue

        route = tables["route_map"].get(route_id, {})
        origin_stop_name = str(tables["stop_map"].get(str(origin_row.get("stop_id") or ""), {}).get("stop_name") or "").strip()
        dest_stop_name = str(tables["stop_map"].get(str(dest_row.get("stop_id") or ""), {}).get("stop_name") or "").strip()
        route_label = _route_label(route, trip)
        results.append(
            TransportScheduleOption(
                provider_id=str(feed.get("id") or "gtfs"),
                provider_label=str(feed.get("label") or "GTFS feed"),
                route_label=route_label,
                origin_stop=origin_stop_name,
                destination_stop=dest_stop_name,
                departure_local=_format_hhmm(dep_secs),
                arrival_local=_format_hhmm(arr_secs),
                trip_headsign=str(trip.get("trip_headsign") or route_label).strip(),
                source_url=str(feed.get("website") or feed.get("resolved_feed_url") or "").strip(),
            )
        )
    return results


def list_route_schedule_options(
    *,
    country_code: Optional[str],
    origin_query: str,
    destination_query: str,
    now: Optional[datetime] = None,
    limit: int = 3,
) -> list[TransportScheduleOption]:
    code = _normalize_country_code(country_code)
    if code is None:
        return []
    feeds = list_transport_feeds(code)
    if not feeds:
        return []

    results: list[TransportScheduleOption] = []
    for feed in feeds:
        if str(feed.get("provider") or "gtfs_schedule") != "gtfs_schedule":
            continue
        tables = _load_feed_tables(feed)
        if not tables:
            continue
        origin_ids = set(_find_stop_ids(tables["stops"], origin_query))
        destination_ids = set(_find_stop_ids(tables["stops"], destination_query))
        if not origin_ids or not destination_ids:
            continue

        timezone_name = str(feed.get("timezone") or "UTC")
        current_dt = now
        if current_dt is None:
            tzinfo = _resolve_feed_timezone(timezone_name)
            current_dt = datetime.now(tzinfo) if tzinfo is not None else datetime.utcnow()
        current_secs = current_dt.hour * 3600 + current_dt.minute * 60 + current_dt.second
        today = current_dt.date()

        direct = _iter_direct_trip_options(
            feed=feed,
            tables=tables,
            origin_ids=origin_ids,
            destination_ids=destination_ids,
            current_secs=current_secs,
            today=today,
        )
        results.extend(direct)
        if direct:
            continue

        origin_route_ids: set[str] = set()
        destination_route_ids: set[str] = set()
        for trip_id, stop_rows in tables["grouped_times"].items():
            trip = tables["trip_map"].get(trip_id)
            if not isinstance(trip, dict):
                continue
            route_id = str(trip.get("route_id") or "").strip()
            if not route_id:
                continue
            stop_ids = {str(row.get("stop_id") or "").strip() for row in stop_rows}
            if stop_ids & origin_ids:
                origin_route_ids.add(route_id)
            if stop_ids & destination_ids:
                destination_route_ids.add(route_id)

        for origin_route_id in origin_route_ids:
            for destination_route_id in destination_route_ids:
                if origin_route_id == destination_route_id:
                    continue
                transfer_ids = tables["route_stop_ids"].get(origin_route_id, set()) & tables["route_stop_ids"].get(destination_route_id, set())
                if not transfer_ids:
                    continue
                first_leg = _iter_direct_trip_options(
                    feed=feed,
                    tables=tables,
                    origin_ids=origin_ids,
                    destination_ids=set(transfer_ids),
                    current_secs=current_secs,
                    today=today,
                    route_id_filter=origin_route_id,
                )
                if not first_leg:
                    continue
                first = first_leg[0]
                transfer_stop_ids = _find_stop_ids(tables["stops"], first.destination_stop)
                second_leg = _iter_direct_trip_options(
                    feed=feed,
                    tables=tables,
                    origin_ids=set(transfer_stop_ids),
                    destination_ids=destination_ids,
                    current_secs=_seconds_from_gtfs_time(f"{first.arrival_local}:00") or current_secs,
                    today=today,
                    route_id_filter=destination_route_id,
                )
                if not second_leg:
                    continue
                second = second_leg[0]
                results.append(
                    TransportScheduleOption(
                        provider_id=first.provider_id,
                        provider_label=first.provider_label,
                        route_label=f"{first.route_label} -> {second.route_label}",
                        origin_stop=first.origin_stop,
                        destination_stop=second.destination_stop,
                        departure_local=first.departure_local,
                        arrival_local=second.arrival_local,
                        trip_headsign=f"환승 {first.destination_stop}",
                        source_url=first.source_url or second.source_url,
                    )
                )
                break
            if results:
                break

    results.sort(key=lambda item: item.departure_local)
    return results[: max(1, limit)]


def build_route_schedule_grounding(
    *,
    country_code: Optional[str],
    origin_query: str,
    destination_query: str,
    language: str,
    limit: int = 3,
) -> str:
    options = list_route_schedule_options(
        country_code=country_code,
        origin_query=origin_query,
        destination_query=destination_query,
        limit=limit,
    )
    if not options:
        return ""
    lang = str(language or "ko").lower()
    lines = ["[공개 GTFS 시간표 기반 경로 근거]"]
    for option in options:
        if lang.startswith("en"):
            lines.append(
                f"- {option.provider_label} | route: {option.route_label} | depart {option.origin_stop} {option.departure_local} | arrive {option.destination_stop} {option.arrival_local} | headsign: {option.trip_headsign}"
            )
        else:
            lines.append(
                f"- {option.provider_label} | 노선: {option.route_label} | 출발 {option.origin_stop} {option.departure_local} | 도착 {option.destination_stop} {option.arrival_local} | 행선지: {option.trip_headsign}"
            )
        if option.source_url:
            lines.append(f"  - 웹: {option.source_url}")
    return "\n".join(lines)