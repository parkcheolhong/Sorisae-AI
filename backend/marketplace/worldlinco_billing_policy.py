"""WorldLinco mobile billing/access policy — admin-controlled free/paid and billing pause."""
from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from backend.time_utils import utcnow


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


WORLDLINGCO_BILLING_POLICY_PATH = _project_root() / "knowledge" / "worldlinco_billing_policy.json"
WORLDLINCO_BILLING_POLICY_SYSTEM_IDENTIFIERS = frozenset({"system", "admin"})

AccessMode = Literal["free", "paid"]


WORLDLINGCO_BILLING_POLICY_DEFAULTS: Dict[str, Any] = {
    "version": 1,
    "updated_at": "2026-07-01T00:00:00Z",
    "updated_by": "system",
    # free: 로그인 사용자 VoIP·노래 무료(베타/프로모). paid: 구매·구독 게이트 적용.
    "access_mode": "free",
    # paid 모드에서도 요금 징수·결제 게이트를 일시 중지(프로모 연장·장애 면제 등).
    "billing_collection_paused": False,
    "promo_label": "베타 무료 기간",
    "promo_starts_at": None,
    "promo_ends_at": None,
    "auto_switch_to_paid_on_promo_end": False,
    "show_pricing_ui": False,
    "note": "관리자 대시보드에서 무료↔유료 전환 및 요금 중지/재개를 제어합니다.",
}


class WorldlincoBillingPolicyUpdate(BaseModel):
    access_mode: Optional[AccessMode] = None
    billing_collection_paused: Optional[bool] = None
    promo_label: Optional[str] = Field(None, max_length=120)
    promo_starts_at: Optional[str] = Field(None, max_length=40)
    promo_ends_at: Optional[str] = Field(None, max_length=40)
    auto_switch_to_paid_on_promo_end: Optional[bool] = None
    show_pricing_ui: Optional[bool] = None
    note: Optional[str] = Field(None, max_length=500)


def _deep_merge_dict(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in patch.items():
        if value is not None or key in patch:
            merged[key] = value
    return merged


def _parse_iso_datetime(raw: Any) -> Optional[datetime]:
    text = str(raw or "").strip()
    if not text:
        return None
    normalized = text if text.endswith("Z") or "+" in text[-6:] else f"{text}Z"
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_effective_access_mode(policy: Dict[str, Any], *, now: Optional[datetime] = None) -> AccessMode:
    mode = str(policy.get("access_mode") or "free").strip().lower()
    if mode not in {"free", "paid"}:
        mode = "free"

    if mode != "free" or not bool(policy.get("auto_switch_to_paid_on_promo_end")):
        return mode  # type: ignore[return-value]

    ends_at = _parse_iso_datetime(policy.get("promo_ends_at"))
    if ends_at is None:
        return mode  # type: ignore[return-value]

    current = now or utcnow()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)

    if current >= ends_at:
        return "paid"
    return "free"


def resolve_worldlinco_billing_access(policy: Dict[str, Any], *, now: Optional[datetime] = None) -> Dict[str, Any]:
    effective_mode = resolve_effective_access_mode(policy, now=now)
    billing_paused = bool(policy.get("billing_collection_paused"))
    free_access_active = effective_mode == "free" or billing_paused
    show_pricing_ui = bool(policy.get("show_pricing_ui"))
    if effective_mode == "free" and not billing_paused:
        show_pricing_ui = bool(policy.get("show_pricing_ui", False))

    return {
        "access_mode": effective_mode,
        "configured_access_mode": str(policy.get("access_mode") or "free"),
        "billing_collection_paused": billing_paused,
        "free_access_active": free_access_active,
        "show_pricing_ui": show_pricing_ui,
        "promo_label": str(policy.get("promo_label") or ""),
        "promo_starts_at": policy.get("promo_starts_at"),
        "promo_ends_at": policy.get("promo_ends_at"),
        "auto_switch_to_paid_on_promo_end": bool(policy.get("auto_switch_to_paid_on_promo_end")),
    }


def load_worldlinco_billing_policy() -> Dict[str, Any]:
    defaults = deepcopy(WORLDLINGCO_BILLING_POLICY_DEFAULTS)
    path = WORLDLINGCO_BILLING_POLICY_PATH
    if not path.is_file():
        return defaults
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return defaults
        merged = _deep_merge_dict(defaults, raw)
        return merged
    except (OSError, json.JSONDecodeError):
        return defaults


def _hash_updated_by_identifier(identifier: str) -> str:
    # Prefix allows consumers to distinguish hashed values from reserved system identifiers.
    return f"hashed:{hashlib.sha256(identifier.encode('utf-8')).hexdigest()}"


def save_worldlinco_billing_policy(payload: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = deepcopy(payload)
    updated_by = str(sanitized.get("updated_by") or "").strip()
    if updated_by and updated_by not in WORLDLINCO_BILLING_POLICY_SYSTEM_IDENTIFIERS:
        sanitized["updated_by"] = _hash_updated_by_identifier(updated_by)

    path = WORLDLINGCO_BILLING_POLICY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2), encoding="utf-8")
    return sanitized


def apply_worldlinco_billing_policy_update(
    update: WorldlincoBillingPolicyUpdate,
    updated_by: str = "admin",
) -> Dict[str, Any]:
    current = load_worldlinco_billing_policy()
    patch = update.model_dump(exclude_unset=True)
    merged = _deep_merge_dict(current, patch)
    merged["updated_at"] = utcnow().replace(microsecond=0).isoformat() + "Z"
    merged["updated_by"] = updated_by
    return save_worldlinco_billing_policy(merged)


def worldlinco_billing_policy_public_payload() -> Dict[str, Any]:
    data = load_worldlinco_billing_policy()
    resolved = resolve_worldlinco_billing_access(data)
    return {
        "version": data.get("version", 1),
        "updated_at": data.get("updated_at"),
        **resolved,
    }


def worldlinco_billing_policy_admin_payload() -> Dict[str, Any]:
    data = load_worldlinco_billing_policy()
    resolved = resolve_worldlinco_billing_access(data)
    return {
        **data,
        "effective": resolved,
    }


def worldlinco_monetization_product_codes() -> frozenset[str]:
    from backend.marketplace.worldlinco_billing_plans import WORLDLINGCO_PLAN_DEFINITIONS

    return frozenset(str(row["product_code"]) for row in WORLDLINGCO_PLAN_DEFINITIONS.values())


def worldlinco_free_access_grants_license(product_code: str, *, now: datetime | None = None) -> bool:
    code = str(product_code or "").strip().lower()
    if not code or code not in {item.lower() for item in worldlinco_monetization_product_codes()}:
        return False
    resolved = resolve_worldlinco_billing_access(load_worldlinco_billing_policy(), now=now)
    return bool(resolved.get("free_access_active"))
