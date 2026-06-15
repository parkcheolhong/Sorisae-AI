from __future__ import annotations

import argparse
import json
import random
import re
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.worldlinco.brand import WORLDLINGO_PROJECT_MATCH_TOKENS


API_BASE_DEFAULT = "https://metanova1004.com"
DEMO_EMAIL_DOMAIN = "instant-demo.worldlinco.dev"
FALLBACK_PROJECT_ID = 38
SEOUL_LAT = "37.5665"
SEOUL_LON = "126.9780"


def _now_iso_local() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _build_demo_credentials(seed: str) -> Dict[str, str]:
    normalized = re.sub(r"[^a-z0-9]+", "", seed.lower())[:10] or "guestdemo"
    return {
        "email": f"instant-{normalized}@{DEMO_EMAIL_DOMAIN}",
        "username": f"instant_{normalized}",
        "password": f"WorldLinco!{normalized}A1",
    }


def _request_json(
    *,
    method: str,
    url: str,
    token: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
    form: Optional[Dict[str, str]] = None,
    timeout: float = 60.0,
) -> Tuple[int, Any]:
    headers: Dict[str, str] = {}
    data: Optional[bytes] = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw.strip() else {"detail": raw}
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def _signup_and_login(base_url: str, attempt: int) -> str:
    seed = f"{int(time.time() * 1000):x}{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}{attempt}"
    creds = _build_demo_credentials(seed)
    signup_status, _ = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/auth/signup",
        body={
            "username": creds["username"],
            "email": creds["email"],
            "password": creds["password"],
            "preferred_language": "ko",
            "country_code": "KR",
            "full_name": "WorldLinco Demo",
            "member_type": "individual",
        },
    )
    if signup_status >= 400:
        raise RuntimeError(f"signup failed ({signup_status})")

    login_status, login_payload = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/auth/login",
        form={"username": creds["email"], "password": creds["password"]},
    )
    token = str((login_payload or {}).get("access_token") or "").strip()
    if login_status >= 400 or not token:
        raise RuntimeError(f"login failed ({login_status}): {login_payload}")
    return token


def _resolve_project_id(base_url: str) -> int:
    status, payload = _request_json(
        method="GET",
        url=f"{base_url.rstrip('/')}/api/marketplace/projects?skip=0&limit=200",
    )
    if status != 200:
        return FALLBACK_PROJECT_ID
    projects = payload if isinstance(payload, list) else (payload or {}).get("projects") or []
    if not isinstance(projects, list):
        return FALLBACK_PROJECT_ID
    for project in projects:
        haystack = " ".join(
            str((project or {}).get(key) or "")
            for key in ("title", "description", "github_url", "file_key")
        ).lower()
        if any(token in haystack for token in WORLDLINGO_PROJECT_MATCH_TOKENS):
            project_id = (project or {}).get("id")
            if isinstance(project_id, int) and project_id > 0:
                return project_id
    return FALLBACK_PROJECT_ID


def _pick_bookable_place(places: List[Dict[str, Any]], *, prefer_airport: bool) -> Optional[Dict[str, Any]]:
    bookable = [
        place
        for place in places
        if (place or {}).get("booking_supported")
        and str((place or {}).get("category") or "") in {"hotel", "airport"}
    ]
    if not bookable:
        return None
    if prefer_airport:
        for place in bookable:
            if str(place.get("category")) == "airport":
                return place
    for place in bookable:
        if str(place.get("category")) == "hotel":
            return place
    return bookable[0]


def _run_round(*, base_url: str, round_index: int) -> Dict[str, Any]:
    started_at = _now_iso_local()
    checkin = (datetime.now().date() + timedelta(days=7)).isoformat()
    checkout = (datetime.now().date() + timedelta(days=9)).isoformat()

    nearby_query = urllib.parse.urlencode(
        {
            "lat": SEOUL_LAT,
            "lon": SEOUL_LON,
            "category": "all",
            "radius_m": "50000",
            "target_lang": "ko",
            "limit": "8",
        }
    )
    nearby_status, nearby_payload = _request_json(
        method="GET",
        url=f"{base_url.rstrip('/')}/api/marketplace/nadotongryoksa/lbs/nearby?{nearby_query}",
    )
    places = (nearby_payload or {}).get("places") if isinstance(nearby_payload, dict) else None
    places_list = places if isinstance(places, list) else []
    nearby_ok = nearby_status == 200 and len(places_list) > 0

    selected = _pick_bookable_place(places_list, prefer_airport=(round_index % 2 == 0))
    map_select_ok = bool(selected)
    place_id = str((selected or {}).get("id") or "hotel-lotte-seoul")

    token = _signup_and_login(base_url, round_index)

    booking_status, booking_payload = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/marketplace/nadotongryoksa/lbs/bookings",
        token=token,
        body={
            "place_id": place_id,
            "customer_name": f"M2-6 Demo {round_index}",
            "checkin_date": checkin,
            "checkout_date": checkout,
            "guests": 2,
            "room_count": 1,
            "note": f"M2-6 E2E round {round_index}",
            "target_lang": "en",
        },
        timeout=120.0,
    )
    confirmation_id = str((booking_payload or {}).get("confirmation_id") or "").strip()
    booking_ok = booking_status == 200 and confirmation_id.startswith("NADO-")

    project_id = _resolve_project_id(base_url)
    nights = max(1, (datetime.fromisoformat(checkout) - datetime.fromisoformat(checkin)).days)
    amount = nights * 1 * 80000

    purchase_status, purchase_payload = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/marketplace/purchase",
        token=token,
        body={"project_id": project_id, "amount": amount, "payment_method": "card"},
    )
    purchase_id = (purchase_payload or {}).get("id")
    purchase_ok = purchase_status == 200 and isinstance(purchase_id, int)

    payment_url = ""
    pay_status = 0
    if purchase_ok:
        pay_status, pay_payload = _request_json(
            method="POST",
            url=f"{base_url.rstrip('/')}/api/marketplace/purchase/{purchase_id}/pay",
            token=token,
        )
        payment_url = str((pay_payload or {}).get("payment_url") or "").strip()
    pay_ok = pay_status == 200 and payment_url.startswith("http")

    passed = all([nearby_ok, map_select_ok, booking_ok, purchase_ok, pay_ok])

    return {
        "round": round_index,
        "started_at": started_at,
        "finished_at": _now_iso_local(),
        "checks": {
            "nearby_200": nearby_ok,
            "map_book_place_select": map_select_ok,
            "booking_confirmation": booking_ok,
            "purchase_create": purchase_ok,
            "payment_url": pay_ok,
        },
        "samples": {
            "place_id": place_id,
            "place_name": (selected or {}).get("name") if selected else None,
            "confirmation_id": confirmation_id,
            "purchase_id": purchase_id,
            "payment_url_prefix": payment_url[:80] if payment_url else "",
            "project_id": project_id,
            "checkin_date": checkin,
            "checkout_date": checkout,
        },
        "status_codes": {
            "nearby": nearby_status,
            "booking": booking_status,
            "purchase": purchase_status,
            "pay": pay_status,
        },
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M2-6 WorldLinco travel booking E2E (2 rounds)")
    parser.add_argument("--base-url", default=API_BASE_DEFAULT)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[2] / "evidence" / "m2-6-booking-e2e-20260530.json"),
    )
    args = parser.parse_args()

    rounds = [_run_round(base_url=args.base_url, round_index=i) for i in range(1, args.rounds + 1)]
    report = {
        "scenario": "M2-6 travel booking E2E",
        "api_base": args.base_url,
        "flow": "nearby -> map-select place -> booking -> purchase -> payment_url",
        "generated_at": _now_iso_local(),
        "rounds": rounds,
        "all_passed": all(item.get("passed") for item in rounds),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
