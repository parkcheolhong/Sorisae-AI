from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _request_json(
    *,
    method: str,
    url: str,
    token: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
    form: Optional[Dict[str, str]] = None,
    timeout: float = 40.0,
) -> Tuple[int, Dict[str, Any]]:
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

    request = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="replace").strip()
            if not payload:
                return response.status, {}
            return response.status, json.loads(payload)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace").strip()
        try:
            return exc.code, json.loads(raw) if raw else {"detail": raw}
        except json.JSONDecodeError:
            return exc.code, {"detail": raw}


def _login(base_url: str, email: str, password: str) -> str:
    status, payload = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/auth/login",
        form={"username": email, "password": password},
    )
    token = str(payload.get("access_token") or "").strip()
    if status != 200 or not token:
        raise RuntimeError(f"login failed: status={status}, payload={payload}")
    return token


def _run_round(base_url: str, token: str, index: int) -> Dict[str, Any]:
    nearby_qs = urllib.parse.urlencode(
        {
            "lat": "37.5665",
            "lon": "126.9780",
            "category": "hotel",
            "radius_m": "50000",
            "target_lang": "ko",
            "limit": "8",
        }
    )
    s_nearby, p_nearby = _request_json(
        method="GET",
        url=f"{base_url.rstrip('/')}/api/marketplace/nadotongryoksa/lbs/nearby?{nearby_qs}",
    )
    places = p_nearby.get("places") if isinstance(p_nearby, dict) else None
    if s_nearby != 200 or not isinstance(places, list) or not places:
        raise RuntimeError(f"nearby failed: status={s_nearby}, payload={p_nearby}")

    place = places[0]
    trip_session_id = p_nearby.get("trip_session_id")
    recommendation_id = place.get("recommendation_id")
    partner_id = place.get("partner_id") or "partner-hotel-default"

    s_click, p_click = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/marketplace/nadotongryoksa/lbs/clicks",
        token=token,
        body={
            "recommendation_id": recommendation_id,
            "partner_id": partner_id,
            "trip_session_id": trip_session_id,
            "landing_url": "https://example.com/hotel",
        },
    )
    if s_click != 200:
        raise RuntimeError(f"click failed: status={s_click}, payload={p_click}")

    click_ref = p_click.get("click_ref")
    click_event_id = p_click.get("click_event_id")

    s_start, p_start = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/marketplace/nadotongryoksa/lbs/bookings/start",
        token=token,
        body={
            "place_id": place.get("id") or "hotel-lotte-seoul",
            "customer_name": f"Section7 Dummy {index}",
            "checkin_date": "2026-07-10",
            "checkout_date": "2026-07-12",
            "guests": 2,
            "room_count": 1,
            "target_lang": "en",
            "partner_click_ref": click_ref,
            "partner_click_event_id": click_event_id,
        },
    )
    if s_start != 200 or p_start.get("stage") != "initiated":
        raise RuntimeError(f"booking start failed: status={s_start}, payload={p_start}")

    booking_ref = p_start.get("booking_ref")

    s_confirm, p_confirm = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/marketplace/nadotongryoksa/lbs/bookings/{booking_ref}/confirm",
        token=token,
        body={"booking_ref": booking_ref, "status_note": "section7 confirm"},
    )
    if s_confirm != 200 or p_confirm.get("stage") != "confirmed":
        raise RuntimeError(f"booking confirm failed: status={s_confirm}, payload={p_confirm}")

    s_complete, p_complete = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/marketplace/nadotongryoksa/lbs/bookings/{booking_ref}/complete",
        token=token,
        body={"booking_ref": booking_ref, "status_note": "section7 complete"},
    )
    if s_complete != 200 or p_complete.get("stage") != "completed":
        raise RuntimeError(f"booking complete failed: status={s_complete}, payload={p_complete}")

    s_settle, p_settle = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/marketplace/nadotongryoksa/lbs/settlements/commission-batch",
        token=token,
        body={
            "dry_run": False,
            "limit": 100,
            "default_commission_amount": 15.0,
            "commission_rate": 0.1,
            "currency": "USD",
        },
    )
    if s_settle != 200:
        raise RuntimeError(f"settlement failed: status={s_settle}, payload={p_settle}")

    s_refund, p_refund = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/marketplace/nadotongryoksa/lbs/bookings/{booking_ref}/refund",
        token=token,
        body={"booking_ref": booking_ref, "reason": "section7 refund", "refund_amount": 15.0},
    )
    if s_refund != 200 or p_refund.get("stage") != "refunded":
        raise RuntimeError(f"refund failed: status={s_refund}, payload={p_refund}")

    return {
        "round": index,
        "status_codes": {
            "nearby": s_nearby,
            "click": s_click,
            "booking_start": s_start,
            "booking_confirm": s_confirm,
            "booking_complete": s_complete,
            "settlement_batch": s_settle,
            "refund": s_refund,
        },
        "samples": {
            "trip_session_id": trip_session_id,
            "recommendation_id": recommendation_id,
            "partner_id": partner_id,
            "click_ref": click_ref,
            "booking_ref": booking_ref,
            "settlement_created": p_settle.get("created"),
            "refund_adjustment_amount": p_refund.get("adjustment_amount"),
        },
        "passed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Section7 travel partner funnel verification")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", default="119cash@naver.com")
    parser.add_argument("--password", required=True)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument(
        "--output",
        default="evidence/section7-travel-partner-funnel-20260701.json",
    )
    args = parser.parse_args()

    token = _login(args.base_url, args.email, args.password)
    rounds = []
    for i in range(1, args.rounds + 1):
        rounds.append(_run_round(args.base_url, token, i))
        time.sleep(0.2)

    report = {
        "scenario": "section7 travel partner funnel verification",
        "base_url": args.base_url,
        "generated_at": int(time.time()),
        "rounds": rounds,
        "all_passed": all(item.get("passed") for item in rounds),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
