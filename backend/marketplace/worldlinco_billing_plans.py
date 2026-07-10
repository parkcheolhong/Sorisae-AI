"""WorldLinco mobile monetization plan ↔ subscription catalog SSOT."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

WORLDLINGCO_PLAN_KEYS = ("voip_lite", "voip_pro", "song_pass")

WORLDLINGCO_PLAN_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "voip_lite": {
        "product_code": "worldlinco-voip-lite",
        "plan_code": "worldlinco-voip-lite-monthly",
        "product_name": "WorldLinco VoIP Premium Lite",
        "plan_name": "Monthly",
        "product_family": "worldlinco-voip",
        "amount_minor": 9900,
        "billing_period": "monthly",
        "entitlements": ["worldlinco.voip.lite"],
        "google_product_id": "com.parkcheolhong.worldlinco.voip_lite.monthly",
        "apple_product_id": "com.parkcheolhong.worldlinco.voip_lite.monthly",
        "stripe_price_code": "price_worldlinco_voip_lite_monthly",
    },
    "voip_pro": {
        "product_code": "worldlinco-voip-pro",
        "plan_code": "worldlinco-voip-pro-monthly",
        "product_name": "WorldLinco VoIP Premium Pro",
        "plan_name": "Monthly",
        "product_family": "worldlinco-voip",
        "amount_minor": 19900,
        "billing_period": "monthly",
        "entitlements": ["worldlinco.voip.pro"],
        "google_product_id": "com.parkcheolhong.worldlinco.voip_pro.monthly",
        "apple_product_id": "com.parkcheolhong.worldlinco.voip_pro.monthly",
        "stripe_price_code": "price_worldlinco_voip_pro_monthly",
    },
    "song_pass": {
        "product_code": "worldlinco-song-pass",
        "plan_code": "worldlinco-song-pass-onetime",
        "product_name": "WorldLinco Song Translation Pass",
        "plan_name": "One-time",
        "product_family": "worldlinco-song",
        "amount_minor": 2900,
        "billing_period": "one_time",
        "entitlements": ["worldlinco.song.pass"],
        "google_product_id": "com.parkcheolhong.worldlinco.song_pass",
        "apple_product_id": "com.parkcheolhong.worldlinco.song_pass",
        "stripe_price_code": "price_worldlinco_song_pass",
    },
}


def resolve_worldlinco_plan(plan_key: Optional[str]) -> Optional[Dict[str, Any]]:
    key = str(plan_key or "").strip().lower()
    if key not in WORLDLINGCO_PLAN_DEFINITIONS:
        return None
    return {**WORLDLINGCO_PLAN_DEFINITIONS[key], "plan_key": key}


def resolve_worldlinco_plan_by_amount(amount_minor: int) -> Optional[Dict[str, Any]]:
    for key, row in WORLDLINGCO_PLAN_DEFINITIONS.items():
        if int(row["amount_minor"]) == int(amount_minor):
            return {**row, "plan_key": key}
    return None


def worldlinco_subscription_catalog_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for plan_key, row in WORLDLINGCO_PLAN_DEFINITIONS.items():
        base = {
            "plan_key": plan_key,
            "product_code": row["product_code"],
            "product_name": row["product_name"],
            "product_description": f"WorldLinco {plan_key} plan",
            "product_family": row["product_family"],
            "plan_code": row["plan_code"],
            "plan_name": row["plan_name"],
            "currency": "KRW",
            "amount_minor": int(row["amount_minor"]),
            "billing_period": row["billing_period"],
            "device_limit": 2,
            "entitlements": list(row["entitlements"]),
        }
        items.append({**base, "provider": "stripe", "external_price_code": row["stripe_price_code"]})
        items.append(
            {
                **base,
                "provider": "google",
                "external_price_code": row["google_product_id"],
                "external_product_id": row["google_product_id"],
            }
        )
        items.append(
            {
                **base,
                "provider": "apple",
                "external_price_code": row["apple_product_id"],
                "external_product_id": row["apple_product_id"],
            }
        )
    return items
