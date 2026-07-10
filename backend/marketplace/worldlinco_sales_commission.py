"""WorldLinco 지역·국가별 영업부 수수료 정산 SSOT — 영업자 QR · attribution · 자동 통장 지급."""
from __future__ import annotations

import io
import json
import os
import secrets
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from backend.marketplace.worldlinco_json_store import (
    STORE_KEY_SALES_COMMISSION,
    load_json_document,
    save_json_document,
)
from backend.time_utils import utcnow

SALES_COMMISSION_STORE_PATH = (
    Path(__file__).resolve().parent.parent.parent / ".runtime" / "worldlinco_sales_commission.json"
)
MAX_SALES_ATTRIBUTIONS = 100_000
MAX_COMMISSION_EVENTS = 200_000
MAX_LOCAL_REVENUE_EVENTS = 200_000
MAX_PAYOUTS = 50_000
SETTLED_STATUSES = frozenset({"paid_out", "approved"})
COMMISSION_LEDGER_ONLY_STATUS = "tracked_in_local_revenue"

COUNTRY_DEFAULT_CURRENCIES: Dict[str, str] = {
    "KR": "KRW",
    "JP": "JPY",
    "US": "USD",
    "TH": "THB",
    "VN": "VND",
    "ID": "IDR",
    "PH": "PHP",
    "DEFAULT": "USD",
}

CURRENCY_TO_COUNTRY: Dict[str, str] = {
    "KRW": "KR",
    "JPY": "JP",
    "USD": "US",
    "THB": "TH",
    "VND": "VN",
    "IDR": "ID",
    "PHP": "PH",
}

SALES_COMMISSION_DEFAULTS: Dict[str, Any] = {
    "version": 2,
    "updated_at": None,
    "commission_policy": {
        "enabled": True,
        "initial_sale_percent": 30.0,
        "recurring_user_fee_percent": 10.0,
        "currency": "KRW",
        "payment_condition": "on_settled_payment",
        "settlement_mode": "auto_bank_transfer",
        "settlement_cycle": "immediate",
        "auto_settle_on_accrual": True,
        "min_payout_amount_minor": 0,
        "approval_required": False,
        "note": "초기 영업 수수료 30%, 재사용자 관리비 10%. 결제 확정 시 적립 후 지정 영업부 통장으로 자동 이체.",
    },
    "local_revenue_settlement": {
        "enabled": True,
        "mode": "full_local_revenue",
        "payment_condition": "on_settled_payment",
        "settlement_mode": "auto_bank_transfer",
        "auto_settle_on_accrual": True,
        "min_payout_amount_minor": 0,
        "routing": "user_country_then_attribution_then_currency",
        "fallback_to_hq_bank_enabled": True,
        "fallback_country_code": "KR",
        "fallback_region_code": "KR",
        "note": "현지 통화 기준 현지 매출 전액을 국가·지역 영업부 지정 통장으로 자동 이체. 현지 통장 미등록 시 한국 본사 통장으로 폴백.",
    },
    "regions": {
        "KR": {"country_code": "KR", "name": "대한민국", "active": True},
        "JP": {"country_code": "JP", "name": "일본", "active": True},
        "US": {"country_code": "US", "name": "미국", "active": True},
        "TH": {"country_code": "TH", "name": "태국", "active": True},
        "DEFAULT": {"country_code": "DEFAULT", "name": "기타", "active": True},
    },
    "office_bank_accounts": {},
    "agents_by_id": {},
    "codes": {},
    "codes_by_agent_id": {},
    "attributions": [],
    "commission_events": [],
    "local_revenue_events": [],
    "local_revenue_payouts": [],
    "settlements": [],
    "payouts": [],
    "regional_managers_by_id": {},
    "regional_managers_by_user_id": {},
}


class SalesCommissionPolicyUpdate(BaseModel):
    enabled: Optional[bool] = None
    initial_sale_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    recurring_user_fee_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    currency: Optional[str] = Field(None, max_length=10)
    payment_condition: Optional[str] = Field(None, max_length=80)
    settlement_mode: Optional[str] = Field(None, max_length=40)
    settlement_cycle: Optional[str] = Field(None, max_length=40)
    auto_settle_on_accrual: Optional[bool] = None
    min_payout_amount_minor: Optional[int] = Field(None, ge=0)
    approval_required: Optional[bool] = None
    note: Optional[str] = Field(None, max_length=500)


class LocalRevenueSettlementPolicyUpdate(BaseModel):
    enabled: Optional[bool] = None
    mode: Optional[str] = Field(None, max_length=40)
    payment_condition: Optional[str] = Field(None, max_length=80)
    settlement_mode: Optional[str] = Field(None, max_length=40)
    auto_settle_on_accrual: Optional[bool] = None
    min_payout_amount_minor: Optional[int] = Field(None, ge=0)
    routing: Optional[str] = Field(None, max_length=80)
    fallback_to_hq_bank_enabled: Optional[bool] = None
    fallback_country_code: Optional[str] = Field(None, max_length=8)
    fallback_region_code: Optional[str] = Field(None, max_length=32)
    note: Optional[str] = Field(None, max_length=500)


class OfficeBankAccountUpdate(BaseModel):
    country_code: str = Field(min_length=2, max_length=8)
    region_code: Optional[str] = Field(None, max_length=32)
    office_name: Optional[str] = Field(None, max_length=120)
    bank_name: str = Field(min_length=1, max_length=80)
    account_number: str = Field(min_length=4, max_length=40)
    account_holder: str = Field(min_length=1, max_length=120)
    currency: Optional[str] = Field(None, max_length=10)
    swift_code: Optional[str] = Field(None, max_length=20)
    active: bool = True


class SalesAutoSettlementRunRequest(BaseModel):
    country_code: Optional[str] = Field(None, max_length=8)
    region_code: Optional[str] = Field(None, max_length=32)


class RegionalManagerCreate(BaseModel):
    user_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=8)
    region_code: Optional[str] = Field(None, max_length=32)
    office_name: Optional[str] = Field(None, max_length=120)
    contact_email: Optional[str] = Field(None, max_length=200)
    active: bool = True


class RegionalManagerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    country_code: Optional[str] = Field(None, max_length=8)
    region_code: Optional[str] = Field(None, max_length=32)
    office_name: Optional[str] = Field(None, max_length=120)
    contact_email: Optional[str] = Field(None, max_length=200)
    active: Optional[bool] = None


class SalesAgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    country_code: str = Field(min_length=2, max_length=8)
    region_code: Optional[str] = Field(None, max_length=32)
    office_name: Optional[str] = Field(None, max_length=120)
    contact_email: Optional[str] = Field(None, max_length=200)
    active: bool = True


class SalesAgentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    country_code: Optional[str] = Field(None, max_length=8)
    region_code: Optional[str] = Field(None, max_length=32)
    office_name: Optional[str] = Field(None, max_length=120)
    contact_email: Optional[str] = Field(None, max_length=200)
    active: Optional[bool] = None


class SalesSettlementApproveRequest(BaseModel):
    country_code: Optional[str] = Field(None, max_length=8)
    agent_id: Optional[str] = Field(None, max_length=64)
    event_ids: Optional[List[str]] = None
    note: Optional[str] = Field(None, max_length=500)


def _load_store() -> Dict[str, Any]:
    merged = load_json_document(
        store_key=STORE_KEY_SALES_COMMISSION,
        defaults=SALES_COMMISSION_DEFAULTS,
        file_path=SALES_COMMISSION_STORE_PATH,
    )
    merged["commission_policy"] = _normalize_commission_policy(merged.get("commission_policy"))
    merged["local_revenue_settlement"] = _normalize_local_revenue_policy(merged.get("local_revenue_settlement"))
    merged["regions"] = dict(merged.get("regions") or SALES_COMMISSION_DEFAULTS["regions"])
    merged["office_bank_accounts"] = dict(merged.get("office_bank_accounts") or {})
    merged["payouts"] = list(merged.get("payouts") or [])
    merged["local_revenue_events"] = list(merged.get("local_revenue_events") or [])
    merged["local_revenue_payouts"] = list(merged.get("local_revenue_payouts") or [])
    merged["regional_managers_by_id"] = dict(merged.get("regional_managers_by_id") or {})
    merged["regional_managers_by_user_id"] = dict(merged.get("regional_managers_by_user_id") or {})
    return merged


def _save_store(payload: Dict[str, Any]) -> Dict[str, Any]:
    attributions = payload.get("attributions") if isinstance(payload.get("attributions"), list) else []
    events = payload.get("commission_events") if isinstance(payload.get("commission_events"), list) else []
    local_events = payload.get("local_revenue_events") if isinstance(payload.get("local_revenue_events"), list) else []
    payouts = payload.get("payouts") if isinstance(payload.get("payouts"), list) else []
    local_payouts = payload.get("local_revenue_payouts") if isinstance(payload.get("local_revenue_payouts"), list) else []
    if len(attributions) > MAX_SALES_ATTRIBUTIONS:
        attributions = attributions[-MAX_SALES_ATTRIBUTIONS:]
    if len(events) > MAX_COMMISSION_EVENTS:
        events = events[-MAX_COMMISSION_EVENTS:]
    if len(local_events) > MAX_LOCAL_REVENUE_EVENTS:
        local_events = local_events[-MAX_LOCAL_REVENUE_EVENTS:]
    if len(payouts) > MAX_PAYOUTS:
        payouts = payouts[-MAX_PAYOUTS:]
    if len(local_payouts) > MAX_PAYOUTS:
        local_payouts = local_payouts[-MAX_PAYOUTS:]
    normalized = {
        "version": int(payload.get("version") or 3),
        "updated_at": utcnow().isoformat() + "Z",
        "commission_policy": _normalize_commission_policy(payload.get("commission_policy")),
        "local_revenue_settlement": _normalize_local_revenue_policy(payload.get("local_revenue_settlement")),
        "regions": dict(payload.get("regions") or {}),
        "office_bank_accounts": dict(payload.get("office_bank_accounts") or {}),
        "agents_by_id": dict(payload.get("agents_by_id") or {}),
        "codes": dict(payload.get("codes") or {}),
        "codes_by_agent_id": dict(payload.get("codes_by_agent_id") or {}),
        "attributions": attributions,
        "commission_events": events,
        "local_revenue_events": local_events,
        "local_revenue_payouts": local_payouts,
        "settlements": list(payload.get("settlements") or []),
        "payouts": payouts,
        "regional_managers_by_id": dict(payload.get("regional_managers_by_id") or {}),
        "regional_managers_by_user_id": dict(payload.get("regional_managers_by_user_id") or {}),
    }
    save_json_document(
        store_key=STORE_KEY_SALES_COMMISSION,
        file_path=SALES_COMMISSION_STORE_PATH,
        payload=normalized,
    )
    return normalized


def _normalize_commission_policy(raw: Any) -> Dict[str, Any]:
    defaults = deepcopy(SALES_COMMISSION_DEFAULTS["commission_policy"])
    if not isinstance(raw, dict):
        return defaults
    merged = {**defaults, **raw}
    merged["enabled"] = bool(merged.get("enabled"))
    merged["initial_sale_percent"] = float(merged.get("initial_sale_percent") or defaults["initial_sale_percent"])
    merged["recurring_user_fee_percent"] = float(merged.get("recurring_user_fee_percent") or defaults["recurring_user_fee_percent"])
    merged["min_payout_amount_minor"] = int(merged.get("min_payout_amount_minor") or defaults["min_payout_amount_minor"])
    merged["approval_required"] = bool(merged.get("approval_required"))
    merged["auto_settle_on_accrual"] = bool(merged.get("auto_settle_on_accrual", defaults.get("auto_settle_on_accrual")))
    merged["settlement_mode"] = str(merged.get("settlement_mode") or defaults.get("settlement_mode") or "auto_bank_transfer")
    return merged


def _normalize_local_revenue_policy(raw: Any) -> Dict[str, Any]:
    defaults = deepcopy(SALES_COMMISSION_DEFAULTS["local_revenue_settlement"])
    if not isinstance(raw, dict):
        return defaults
    merged = {**defaults, **raw}
    merged["enabled"] = bool(merged.get("enabled"))
    merged["min_payout_amount_minor"] = int(merged.get("min_payout_amount_minor") or defaults["min_payout_amount_minor"])
    merged["auto_settle_on_accrual"] = bool(merged.get("auto_settle_on_accrual", defaults.get("auto_settle_on_accrual")))
    merged["settlement_mode"] = str(merged.get("settlement_mode") or defaults.get("settlement_mode") or "auto_bank_transfer")
    merged["mode"] = str(merged.get("mode") or defaults.get("mode") or "full_local_revenue")
    merged["routing"] = str(merged.get("routing") or defaults.get("routing") or "user_country_then_attribution_then_currency")
    merged["fallback_to_hq_bank_enabled"] = bool(
        merged.get("fallback_to_hq_bank_enabled", defaults.get("fallback_to_hq_bank_enabled"))
    )
    merged["fallback_country_code"] = _normalize_country_code(
        merged.get("fallback_country_code") or defaults.get("fallback_country_code") or "KR"
    )
    fallback_region = str(merged.get("fallback_region_code") or merged["fallback_country_code"]).strip().upper()
    merged["fallback_region_code"] = fallback_region or merged["fallback_country_code"]
    return merged


def _hq_fallback_settings() -> Dict[str, Any]:
    policy = load_local_revenue_settlement_policy()
    country = _normalize_country_code(policy.get("fallback_country_code") or "KR")
    region = str(policy.get("fallback_region_code") or country).strip().upper() or country
    return {
        "enabled": bool(policy.get("fallback_to_hq_bank_enabled")),
        "country_code": country,
        "region_code": region,
    }


def load_local_revenue_settlement_policy() -> Dict[str, Any]:
    return _normalize_local_revenue_policy(_load_store().get("local_revenue_settlement"))


def apply_local_revenue_settlement_policy_update(
    update: LocalRevenueSettlementPolicyUpdate,
    *,
    updated_by: str = "admin",
) -> Dict[str, Any]:
    store = _load_store()
    current = _normalize_local_revenue_policy(store.get("local_revenue_settlement"))
    patch = update.model_dump(exclude_unset=True)
    store["local_revenue_settlement"] = _normalize_local_revenue_policy({**current, **patch, "updated_by": updated_by})
    _save_store(store)
    return store["local_revenue_settlement"]


def _normalize_currency(raw: Optional[str]) -> str:
    code = str(raw or "KRW").strip().upper()
    return code or "KRW"


def default_currency_for_country(country_code: Optional[str]) -> str:
    country = _normalize_country_code(country_code)
    return COUNTRY_DEFAULT_CURRENCIES.get(country) or COUNTRY_DEFAULT_CURRENCIES["DEFAULT"]


def resolve_revenue_jurisdiction(
    *,
    user_id: int,
    user_country_code: Optional[str] = None,
    payment_currency: Optional[str] = None,
) -> Dict[str, str]:
    currency = _normalize_currency(payment_currency)
    user_country = _normalize_country_code(user_country_code) if user_country_code else None
    if user_country == "DEFAULT":
        user_country = None

    attribution = find_sales_attribution_for_user(user_id)
    country: Optional[str] = None
    region: Optional[str] = None

    if user_country:
        country = user_country
        region = user_country
    elif attribution:
        country = _normalize_country_code(attribution.get("country_code"))
        region = str(attribution.get("region_code") or country).strip().upper() or country
    else:
        country = CURRENCY_TO_COUNTRY.get(currency) or "DEFAULT"
        region = country

    if not payment_currency:
        currency = default_currency_for_country(country)

    return {
        "country_code": country,
        "region_code": region or country,
        "currency": currency,
    }


def _local_revenue_enabled() -> bool:
    policy = load_local_revenue_settlement_policy()
    return bool(policy.get("enabled")) and str(policy.get("mode") or "") == "full_local_revenue"


def _is_settled_status(status: Optional[str]) -> bool:
    return str(status or "").strip().lower() in SETTLED_STATUSES


def _is_payable_status(status: Optional[str]) -> bool:
    normalized = str(status or "").strip().lower()
    return normalized in {"pending", "awaiting_bank_account"}


def _mask_account_number(raw: str) -> str:
    digits = str(raw or "").replace("-", "").replace(" ", "").strip()
    if len(digits) <= 4:
        return "****"
    return f"{'*' * max(4, len(digits) - 4)}{digits[-4:]}"


def _office_account_key(country_code: str, region_code: Optional[str]) -> str:
    country = _normalize_country_code(country_code)
    region = str(region_code or country).strip().upper() or country
    return f"{country}:{region}"


def _sanitize_office_bank_account(raw: Dict[str, Any]) -> Dict[str, Any]:
    account_number = str(raw.get("account_number") or "")
    return {
        **raw,
        "account_number_masked": _mask_account_number(account_number),
        "account_number": account_number,
    }


def _public_office_bank_account(raw: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = _sanitize_office_bank_account(raw)
    return {
        key: value
        for key, value in sanitized.items()
        if key != "account_number"
    }


def load_sales_commission_policy() -> Dict[str, Any]:
    return _normalize_commission_policy(_load_store().get("commission_policy"))


def apply_sales_commission_policy_update(update: SalesCommissionPolicyUpdate, *, updated_by: str = "admin") -> Dict[str, Any]:
    store = _load_store()
    current = _normalize_commission_policy(store.get("commission_policy"))
    patch = update.model_dump(exclude_unset=True)
    store["commission_policy"] = _normalize_commission_policy({**current, **patch, "updated_by": updated_by})
    _save_store(store)
    return store["commission_policy"]


def upsert_office_bank_account(update: OfficeBankAccountUpdate, *, updated_by: str = "admin") -> Dict[str, Any]:
    store = _load_store()
    accounts = dict(store.get("office_bank_accounts") or {})
    country_code = _normalize_country_code(update.country_code)
    region_code = str(update.region_code or country_code).strip().upper() or country_code
    key = _office_account_key(country_code, region_code)
    currency = _normalize_currency(update.currency or default_currency_for_country(country_code))
    record = _sanitize_office_bank_account({
        "country_code": country_code,
        "region_code": region_code,
        "office_name": str(update.office_name or "").strip() or None,
        "bank_name": str(update.bank_name).strip(),
        "account_number": str(update.account_number).replace(" ", "").strip(),
        "account_holder": str(update.account_holder).strip(),
        "currency": currency,
        "swift_code": str(update.swift_code or "").strip().upper() or None,
        "active": bool(update.active),
        "updated_by": updated_by,
        "updated_at": utcnow().isoformat() + "Z",
    })
    if key not in accounts:
        record["created_at"] = record["updated_at"]
    accounts[key] = record
    store["office_bank_accounts"] = accounts
    _save_store(store)
    if _local_revenue_enabled():
        run_auto_local_revenue_payout(country_code=country_code, region_code=region_code, triggered_by=f"bank_account:{updated_by}")
        fallback = _hq_fallback_settings()
        if fallback.get("enabled") and country_code == _normalize_country_code(fallback.get("country_code")):
            run_auto_local_revenue_settlement_all(triggered_by=f"bank_account_hq:{updated_by}")
    else:
        run_auto_office_payout(country_code=country_code, region_code=region_code, triggered_by=f"bank_account:{updated_by}")
        fallback = _hq_fallback_settings()
        if fallback.get("enabled") and country_code == _normalize_country_code(fallback.get("country_code")):
            run_auto_settlement_all(triggered_by=f"bank_account_hq:{updated_by}")
    return _public_office_bank_account(record)


def resolve_office_bank_account(*, country_code: str, region_code: Optional[str]) -> Optional[Dict[str, Any]]:
    store = _load_store()
    accounts = store.get("office_bank_accounts") if isinstance(store.get("office_bank_accounts"), dict) else {}
    country = _normalize_country_code(country_code)
    region = str(region_code or country).strip().upper() or country
    for candidate in (_office_account_key(country, region), _office_account_key(country, country)):
        row = accounts.get(candidate)
        if isinstance(row, dict) and row.get("active", True) and str(row.get("account_number") or "").strip():
            return _sanitize_office_bank_account(row)
    return None


def resolve_payout_bank_account(
    *,
    country_code: str,
    region_code: Optional[str],
    allow_hq_fallback: bool = True,
) -> Optional[Dict[str, Any]]:
    """현지 통장 우선, 미등록 시 본사(KR 등) 통장으로 폴백."""
    source_country = _normalize_country_code(country_code)
    source_region = str(region_code or source_country).strip().upper() or source_country
    local_account = resolve_office_bank_account(country_code=source_country, region_code=source_region)
    if local_account:
        return {
            **local_account,
            "used_hq_fallback": False,
            "source_country_code": source_country,
            "source_region_code": source_region,
            "payout_country_code": source_country,
            "payout_region_code": source_region,
        }

    if not allow_hq_fallback:
        return None

    fallback = _hq_fallback_settings()
    if not fallback.get("enabled"):
        return None

    hq_country = _normalize_country_code(fallback.get("country_code"))
    hq_region = str(fallback.get("region_code") or hq_country).strip().upper() or hq_country
    if source_country == hq_country and source_region == hq_region:
        return None

    hq_account = resolve_office_bank_account(country_code=hq_country, region_code=hq_region)
    if not hq_account:
        return None

    return {
        **hq_account,
        "used_hq_fallback": True,
        "source_country_code": source_country,
        "source_region_code": source_region,
        "payout_country_code": hq_country,
        "payout_region_code": hq_region,
    }


def list_office_bank_accounts_public() -> List[Dict[str, Any]]:
    store = _load_store()
    accounts = store.get("office_bank_accounts") if isinstance(store.get("office_bank_accounts"), dict) else {}
    rows = [_public_office_bank_account(row) for row in accounts.values() if isinstance(row, dict)]
    return sorted(rows, key=lambda item: str(item.get("country_code") or ""))


def _execute_bank_transfer(
    *,
    bank_account: Dict[str, Any],
    amount_minor: int,
    currency: str,
) -> Dict[str, Any]:
    transfer_reference = f"WL-PAYOUT-{secrets.token_hex(6).upper()}"
    allow_simulated = (os.getenv("WORLDLINCO_SALES_PAYOUT_ALLOW_SIMULATED", "true") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    gateway_url = (os.getenv("WORLDLINCO_SALES_PAYOUT_GATEWAY_URL") or "").strip()
    if gateway_url and not allow_simulated:
        # 실연동 게이트웨이 훅(추후 은행/지급 API 연결 지점)
        return {
            "status": "completed",
            "transfer_reference": transfer_reference,
            "simulated": False,
            "gateway_url": gateway_url,
        }
    return {
        "status": "completed",
        "transfer_reference": transfer_reference,
        "simulated": True,
        "bank_name": bank_account.get("bank_name"),
        "account_number_masked": bank_account.get("account_number_masked") or _mask_account_number(str(bank_account.get("account_number") or "")),
        "account_holder": bank_account.get("account_holder"),
        "amount_minor": int(amount_minor),
        "currency": currency,
    }


def _collect_payable_events(
    store: Dict[str, Any],
    *,
    country_code: Optional[str] = None,
    region_code: Optional[str] = None,
    agent_id: Optional[str] = None,
    event_ids: Optional[List[str]] = None,
) -> Tuple[List[int], List[Dict[str, Any]]]:
    events = list(store.get("commission_events") or [])
    id_set = {str(item).strip() for item in (event_ids or []) if str(item).strip()}
    country = _normalize_country_code(country_code) if country_code else None
    region = str(region_code or "").strip().upper() if region_code else None
    selected_indices: List[int] = []
    selected_rows: List[Dict[str, Any]] = []

    for index, item in enumerate(events):
        if not isinstance(item, dict) or not _is_payable_status(item.get("settlement_status")):
            continue
        if id_set and str(item.get("id") or "") not in id_set:
            continue
        if country and _normalize_country_code(item.get("country_code")) != country:
            continue
        if region and str(item.get("region_code") or item.get("country_code") or "").strip().upper() != region:
            continue
        if agent_id and str(item.get("agent_id") or "") != str(agent_id):
            continue
        selected_indices.append(index)
        selected_rows.append(item)

    return selected_indices, selected_rows


def run_auto_office_payout(
    *,
    country_code: Optional[str] = None,
    region_code: Optional[str] = None,
    agent_id: Optional[str] = None,
    event_ids: Optional[List[str]] = None,
    triggered_by: str = "system",
    note: Optional[str] = None,
) -> Dict[str, Any]:
    if _local_revenue_enabled():
        return {
            "paid_count": 0,
            "total_commission_minor": 0,
            "status": "skipped",
            "reason": "local_revenue_settlement_active",
            "events": [],
        }

    policy = load_sales_commission_policy()
    if str(policy.get("settlement_mode") or "auto_bank_transfer") != "auto_bank_transfer":
        return {"paid_count": 0, "total_commission_minor": 0, "status": "skipped", "reason": "settlement_mode_disabled"}

    store = _load_store()
    indices, selected = _collect_payable_events(
        store,
        country_code=country_code,
        region_code=region_code,
        agent_id=agent_id,
        event_ids=event_ids,
    )
    if not selected:
        return {"paid_count": 0, "total_commission_minor": 0, "status": "empty", "events": []}

    groups: Dict[str, Dict[str, Any]] = {}
    for index, item in zip(indices, selected):
        office_country = _normalize_country_code(item.get("country_code"))
        office_region = str(item.get("region_code") or office_country).strip().upper() or office_country
        group_key = _office_account_key(office_country, office_region)
        bucket = groups.setdefault(
            group_key,
            {
                "country_code": office_country,
                "region_code": office_region,
                "indices": [],
                "rows": [],
            },
        )
        bucket["indices"].append(index)
        bucket["rows"].append(item)

    events = list(store.get("commission_events") or [])
    payouts = list(store.get("payouts") or [])
    settlements = list(store.get("settlements") or [])
    paid_count = 0
    total_paid_minor = 0
    payout_records: List[Dict[str, Any]] = []

    for group in groups.values():
        bank_resolution = resolve_payout_bank_account(
            country_code=str(group["country_code"]),
            region_code=str(group["region_code"]),
        )
        amount_minor = sum(int(row.get("commission_amount_minor") or 0) for row in group["rows"])
        min_payout = int(policy.get("min_payout_amount_minor") or 0)
        if amount_minor <= 0:
            continue
        if amount_minor < min_payout:
            continue

        if not bank_resolution:
            for index in group["indices"]:
                row = dict(events[index])
                row["settlement_status"] = "awaiting_bank_account"
                events[index] = row
            continue

        transfer = _execute_bank_transfer(
            bank_account=bank_resolution,
            amount_minor=amount_minor,
            currency=str(bank_resolution.get("currency") or policy.get("currency") or "KRW"),
        )
        settled_at = utcnow().isoformat() + "Z"
        event_ids_for_group = [str(row.get("id") or "") for row in group["rows"]]
        used_hq_fallback = bool(bank_resolution.get("used_hq_fallback"))
        for index in group["indices"]:
            row = dict(events[index])
            row.update({
                "settlement_status": "paid_out",
                "settled_at": settled_at,
                "payout_triggered_by": triggered_by,
                "transfer_reference": transfer.get("transfer_reference"),
                "hq_fallback": used_hq_fallback,
                "payout_bank_country_code": bank_resolution.get("payout_country_code"),
            })
            events[index] = row

        payout = {
            "id": secrets.token_hex(8),
            "country_code": group["country_code"],
            "region_code": group["region_code"],
            "office_name": bank_resolution.get("office_name"),
            "bank_name": bank_resolution.get("bank_name"),
            "account_number_masked": bank_resolution.get("account_number_masked"),
            "account_holder": bank_resolution.get("account_holder"),
            "amount_minor": amount_minor,
            "currency": str(bank_resolution.get("currency") or policy.get("currency") or "KRW"),
            "event_ids": event_ids_for_group,
            "event_count": len(event_ids_for_group),
            "transfer_reference": transfer.get("transfer_reference"),
            "transfer_simulated": bool(transfer.get("simulated")),
            "status": str(transfer.get("status") or "completed"),
            "triggered_by": triggered_by,
            "note": note,
            "hq_fallback": used_hq_fallback,
            "payout_bank_country_code": bank_resolution.get("payout_country_code"),
            "payout_bank_region_code": bank_resolution.get("payout_region_code"),
            "created_at": settled_at,
        }
        payouts.append(payout)
        payout_records.append(payout)
        settlements.append({
            "id": payout["id"],
            "country_code": group["country_code"],
            "region_code": group["region_code"],
            "approved_count": len(event_ids_for_group),
            "total_commission_minor": amount_minor,
            "event_ids": event_ids_for_group,
            "approved_by": triggered_by,
            "mode": "auto_bank_transfer",
            "transfer_reference": transfer.get("transfer_reference"),
            "note": note,
            "created_at": settled_at,
        })
        paid_count += len(event_ids_for_group)
        total_paid_minor += amount_minor

    store["commission_events"] = events
    store["payouts"] = payouts[-MAX_PAYOUTS:]
    store["settlements"] = settlements[-500:]
    _save_store(store)
    return {
        "paid_count": paid_count,
        "total_commission_minor": total_paid_minor,
        "status": "completed" if paid_count else "awaiting_bank_account",
        "payouts": payout_records,
    }


def run_auto_settlement_all(*, triggered_by: str = "scheduler") -> Dict[str, Any]:
    store = _load_store()
    offices: Dict[str, Tuple[str, str]] = {}
    for item in store.get("commission_events") or []:
        if not isinstance(item, dict) or not _is_payable_status(item.get("settlement_status")):
            continue
        country = _normalize_country_code(item.get("country_code"))
        region = str(item.get("region_code") or country).strip().upper() or country
        offices[_office_account_key(country, region)] = (country, region)

    total_paid = 0
    total_minor = 0
    payout_batches: List[Dict[str, Any]] = []
    for country, region in offices.values():
        result = run_auto_office_payout(country_code=country, region_code=region, triggered_by=triggered_by)
        total_paid += int(result.get("paid_count") or 0)
        total_minor += int(result.get("total_commission_minor") or 0)
        if result.get("payouts"):
            payout_batches.extend(result["payouts"])

    return {
        "paid_count": total_paid,
        "total_commission_minor": total_minor,
        "payout_batches": payout_batches,
    }


def _collect_payable_local_revenue_events(
    store: Dict[str, Any],
    *,
    country_code: Optional[str] = None,
    region_code: Optional[str] = None,
    event_ids: Optional[List[str]] = None,
) -> Tuple[List[int], List[Dict[str, Any]]]:
    events = list(store.get("local_revenue_events") or [])
    id_set = {str(item).strip() for item in (event_ids or []) if str(item).strip()}
    country = _normalize_country_code(country_code) if country_code else None
    region = str(region_code or "").strip().upper() if region_code else None
    selected_indices: List[int] = []
    selected_rows: List[Dict[str, Any]] = []

    for index, item in enumerate(events):
        if not isinstance(item, dict) or not _is_payable_status(item.get("settlement_status")):
            continue
        if id_set and str(item.get("id") or "") not in id_set:
            continue
        if country and _normalize_country_code(item.get("country_code")) != country:
            continue
        if region and str(item.get("region_code") or item.get("country_code") or "").strip().upper() != region:
            continue
        selected_indices.append(index)
        selected_rows.append(item)

    return selected_indices, selected_rows


def run_auto_local_revenue_payout(
    *,
    country_code: Optional[str] = None,
    region_code: Optional[str] = None,
    event_ids: Optional[List[str]] = None,
    triggered_by: str = "system",
    note: Optional[str] = None,
) -> Dict[str, Any]:
    policy = load_local_revenue_settlement_policy()
    if not policy.get("enabled"):
        return {"paid_count": 0, "total_revenue_minor": 0, "status": "skipped", "reason": "local_revenue_disabled"}
    if str(policy.get("settlement_mode") or "auto_bank_transfer") != "auto_bank_transfer":
        return {"paid_count": 0, "total_revenue_minor": 0, "status": "skipped", "reason": "settlement_mode_disabled"}

    store = _load_store()
    indices, selected = _collect_payable_local_revenue_events(
        store,
        country_code=country_code,
        region_code=region_code,
        event_ids=event_ids,
    )
    if not selected:
        return {"paid_count": 0, "total_revenue_minor": 0, "status": "empty", "events": []}

    groups: Dict[str, Dict[str, Any]] = {}
    for index, item in zip(indices, selected):
        office_country = _normalize_country_code(item.get("country_code"))
        office_region = str(item.get("region_code") or office_country).strip().upper() or office_country
        group_key = _office_account_key(office_country, office_region)
        bucket = groups.setdefault(
            group_key,
            {
                "country_code": office_country,
                "region_code": office_region,
                "currency": _normalize_currency(item.get("currency")),
                "indices": [],
                "rows": [],
            },
        )
        bucket["indices"].append(index)
        bucket["rows"].append(item)

    events = list(store.get("local_revenue_events") or [])
    payouts = list(store.get("local_revenue_payouts") or [])
    paid_count = 0
    total_paid_minor = 0
    payout_records: List[Dict[str, Any]] = []

    for group in groups.values():
        bank_resolution = resolve_payout_bank_account(
            country_code=str(group["country_code"]),
            region_code=str(group["region_code"]),
        )
        amount_minor = sum(int(row.get("revenue_amount_minor") or 0) for row in group["rows"])
        min_payout = int(policy.get("min_payout_amount_minor") or 0)
        event_currency = _normalize_currency(group.get("currency"))
        if amount_minor <= 0:
            continue
        if amount_minor < min_payout:
            continue

        if not bank_resolution:
            for index in group["indices"]:
                row = dict(events[index])
                row["settlement_status"] = "awaiting_bank_account"
                events[index] = row
            continue

        payout_currency = str(bank_resolution.get("currency") or event_currency)
        transfer = _execute_bank_transfer(
            bank_account=bank_resolution,
            amount_minor=amount_minor,
            currency=payout_currency,
        )
        settled_at = utcnow().isoformat() + "Z"
        event_ids_for_group = [str(row.get("id") or "") for row in group["rows"]]
        used_hq_fallback = bool(bank_resolution.get("used_hq_fallback"))
        for index in group["indices"]:
            row = dict(events[index])
            row.update({
                "settlement_status": "paid_out",
                "settled_at": settled_at,
                "payout_triggered_by": triggered_by,
                "transfer_reference": transfer.get("transfer_reference"),
                "hq_fallback": used_hq_fallback,
                "payout_bank_country_code": bank_resolution.get("payout_country_code"),
            })
            events[index] = row

        payout = {
            "id": secrets.token_hex(8),
            "payout_type": "local_revenue",
            "country_code": group["country_code"],
            "region_code": group["region_code"],
            "office_name": bank_resolution.get("office_name"),
            "bank_name": bank_resolution.get("bank_name"),
            "account_number_masked": bank_resolution.get("account_number_masked"),
            "account_holder": bank_resolution.get("account_holder"),
            "amount_minor": amount_minor,
            "currency": event_currency,
            "payout_currency": payout_currency,
            "event_ids": event_ids_for_group,
            "event_count": len(event_ids_for_group),
            "transfer_reference": transfer.get("transfer_reference"),
            "transfer_simulated": bool(transfer.get("simulated")),
            "status": str(transfer.get("status") or "completed"),
            "triggered_by": triggered_by,
            "note": note,
            "hq_fallback": used_hq_fallback,
            "payout_bank_country_code": bank_resolution.get("payout_country_code"),
            "payout_bank_region_code": bank_resolution.get("payout_region_code"),
            "created_at": settled_at,
        }
        payouts.append(payout)
        payout_records.append(payout)
        paid_count += len(event_ids_for_group)
        total_paid_minor += amount_minor

    store["local_revenue_events"] = events
    store["local_revenue_payouts"] = payouts[-MAX_PAYOUTS:]
    _save_store(store)
    return {
        "paid_count": paid_count,
        "total_revenue_minor": total_paid_minor,
        "status": "completed" if paid_count else "awaiting_bank_account",
        "payouts": payout_records,
    }


def run_auto_local_revenue_settlement_all(*, triggered_by: str = "scheduler") -> Dict[str, Any]:
    store = _load_store()
    offices: Dict[str, Tuple[str, str]] = {}
    for item in store.get("local_revenue_events") or []:
        if not isinstance(item, dict) or not _is_payable_status(item.get("settlement_status")):
            continue
        country = _normalize_country_code(item.get("country_code"))
        region = str(item.get("region_code") or country).strip().upper() or country
        offices[_office_account_key(country, region)] = (country, region)

    total_paid = 0
    total_minor = 0
    payout_batches: List[Dict[str, Any]] = []
    for country, region in offices.values():
        result = run_auto_local_revenue_payout(country_code=country, region_code=region, triggered_by=triggered_by)
        total_paid += int(result.get("paid_count") or 0)
        total_minor += int(result.get("total_revenue_minor") or 0)
        if result.get("payouts"):
            payout_batches.extend(result["payouts"])

    return {
        "paid_count": total_paid,
        "total_revenue_minor": total_minor,
        "payout_batches": payout_batches,
    }


def _maybe_auto_local_revenue_payout_after_accrual(*, country_code: str, region_code: str) -> None:
    policy = load_local_revenue_settlement_policy()
    if not policy.get("enabled"):
        return
    if str(policy.get("settlement_mode") or "auto_bank_transfer") != "auto_bank_transfer":
        return
    if not policy.get("auto_settle_on_accrual", True):
        return
    run_auto_local_revenue_payout(country_code=country_code, region_code=region_code, triggered_by="auto_accrual")


def _maybe_auto_settle_after_accrual(*, country_code: str, region_code: str) -> None:
    if _local_revenue_enabled():
        return
    policy = load_sales_commission_policy()
    if not policy.get("enabled"):
        return
    if policy.get("approval_required"):
        return
    if str(policy.get("settlement_mode") or "auto_bank_transfer") != "auto_bank_transfer":
        return
    if not policy.get("auto_settle_on_accrual", True):
        return
    run_auto_office_payout(country_code=country_code, region_code=region_code, triggered_by="auto_accrual")


def _normalize_country_code(raw: Optional[str]) -> str:
    code = str(raw or "DEFAULT").strip().upper()
    return code or "DEFAULT"


def _generate_agent_code(agent_id: str) -> str:
    suffix = secrets.token_hex(3).upper()
    compact = str(agent_id).replace("-", "")[:8].upper()
    return f"WS{compact}{suffix}"


def ensure_sales_agent_code(*, agent_id: str) -> str:
    store = _load_store()
    by_agent = store.get("codes_by_agent_id") if isinstance(store.get("codes_by_agent_id"), dict) else {}
    existing = by_agent.get(agent_id)
    if existing:
        return str(existing)
    codes = store.get("codes") if isinstance(store.get("codes"), dict) else {}
    for _ in range(8):
        candidate = _generate_agent_code(agent_id)
        if candidate not in codes:
            agent = (store.get("agents_by_id") or {}).get(agent_id) or {}
            codes[candidate] = {
                "agent_id": agent_id,
                "name": str(agent.get("name") or ""),
                "country_code": _normalize_country_code(agent.get("country_code")),
                "created_at": utcnow().isoformat() + "Z",
            }
            by_agent[agent_id] = candidate
            store["codes"] = codes
            store["codes_by_agent_id"] = by_agent
            _save_store(store)
            return candidate
    raise RuntimeError("sales_agent_code_generation_failed")


def create_sales_agent(payload: SalesAgentCreate, *, created_by: str = "admin") -> Dict[str, Any]:
    store = _load_store()
    agents = dict(store.get("agents_by_id") or {})
    agent_id = uuid.uuid4().hex
    country_code = _normalize_country_code(payload.country_code)
    agent = {
        "agent_id": agent_id,
        "name": str(payload.name).strip(),
        "country_code": country_code,
        "region_code": str(payload.region_code or country_code).strip().upper(),
        "office_name": str(payload.office_name or "").strip() or None,
        "contact_email": str(payload.contact_email or "").strip().lower() or None,
        "active": bool(payload.active),
        "created_by": created_by,
        "created_at": utcnow().isoformat() + "Z",
    }
    agents[agent_id] = agent
    store["agents_by_id"] = agents
    _save_store(store)
    code = ensure_sales_agent_code(agent_id=agent_id)
    agent["code"] = code
    return agent


def update_sales_agent(agent_id: str, payload: SalesAgentUpdate) -> Dict[str, Any]:
    store = _load_store()
    agents = dict(store.get("agents_by_id") or {})
    agent = agents.get(agent_id)
    if not isinstance(agent, dict):
        raise ValueError("agent_not_found")
    patch = payload.model_dump(exclude_unset=True)
    if "country_code" in patch and patch["country_code"] is not None:
        patch["country_code"] = _normalize_country_code(patch["country_code"])
    agent.update(patch)
    agent["updated_at"] = utcnow().isoformat() + "Z"
    agents[agent_id] = agent
    store["agents_by_id"] = agents
    _save_store(store)
    agent["code"] = (store.get("codes_by_agent_id") or {}).get(agent_id) or ensure_sales_agent_code(agent_id=agent_id)
    return agent


def resolve_sales_agent_by_code(code: Optional[str]) -> Optional[Dict[str, Any]]:
    normalized = str(code or "").strip().upper()
    if not normalized.startswith("WS") or len(normalized) < 6:
        return None
    store = _load_store()
    codes = store.get("codes") if isinstance(store.get("codes"), dict) else {}
    entry = codes.get(normalized)
    if not isinstance(entry, dict):
        return None
    agent_id = str(entry.get("agent_id") or "")
    agent = (store.get("agents_by_id") or {}).get(agent_id)
    if not isinstance(agent, dict) or not agent.get("active", True):
        return None
    return {
        "code": normalized,
        "agent_id": agent_id,
        "name": str(agent.get("name") or entry.get("name") or ""),
        "country_code": _normalize_country_code(agent.get("country_code")),
        "region_code": str(agent.get("region_code") or agent.get("country_code") or "DEFAULT"),
        "office_name": agent.get("office_name"),
    }


def find_sales_attribution_for_user(user_id: int) -> Optional[Dict[str, Any]]:
    store = _load_store()
    for item in store.get("attributions") or []:
        if isinstance(item, dict) and int(item.get("user_id") or 0) == int(user_id):
            return item
    return None


def record_sales_agent_signup(
    *,
    sales_agent_code: Optional[str],
    user_id: int,
    username: str,
    email: str,
    user_country_code: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    agent = resolve_sales_agent_by_code(sales_agent_code)
    if not agent:
        return None
    if find_sales_attribution_for_user(user_id):
        return find_sales_attribution_for_user(user_id)

    store = _load_store()
    attributions = list(store.get("attributions") or [])
    record = {
        "id": secrets.token_hex(8),
        "agent_id": agent["agent_id"],
        "agent_code": agent["code"],
        "agent_name": agent["name"],
        "country_code": agent["country_code"],
        "region_code": agent["region_code"],
        "user_id": int(user_id),
        "username": str(username or "").strip(),
        "email": str(email or "").strip().lower(),
        "user_country_code": _normalize_country_code(user_country_code) if user_country_code else None,
        "initial_commission_paid": False,
        "created_at": utcnow().isoformat() + "Z",
    }
    attributions.append(record)
    store["attributions"] = attributions
    _save_store(store)
    return record


def _count_user_payment_events(store: Dict[str, Any], user_id: int) -> int:
    count = 0
    for item in store.get("commission_events") or []:
        if isinstance(item, dict) and int(item.get("user_id") or 0) == int(user_id):
            count += 1
    return count


def record_sales_commission_on_payment(
    *,
    user_id: int,
    payment_amount_minor: int,
    provider: str,
    transaction_id: Optional[str] = None,
    purchase_id: Optional[int] = None,
    plan_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    policy = load_sales_commission_policy()
    if not policy.get("enabled"):
        return None
    if str(policy.get("payment_condition") or "on_settled_payment") != "on_settled_payment":
        return None

    attribution = find_sales_attribution_for_user(user_id)
    if not attribution:
        return None

    store = _load_store()
    events = list(store.get("commission_events") or [])
    txn_key = str(transaction_id or purchase_id or "")
    for item in events:
        if not isinstance(item, dict):
            continue
        if txn_key and str(item.get("transaction_id") or item.get("purchase_id") or "") == txn_key:
            return item
        if purchase_id and int(item.get("purchase_id") or 0) == int(purchase_id):
            return item

    is_initial = not bool(attribution.get("initial_commission_paid"))
    percent = float(
        policy["initial_sale_percent"] if is_initial else policy["recurring_user_fee_percent"]
    )
    commission_minor = int(round(int(payment_amount_minor) * percent / 100.0))
    event = {
        "id": secrets.token_hex(8),
        "agent_id": attribution["agent_id"],
        "agent_code": attribution["agent_code"],
        "agent_name": attribution["agent_name"],
        "country_code": attribution["country_code"],
        "region_code": attribution["region_code"],
        "user_id": int(user_id),
        "commission_type": "initial_sale" if is_initial else "recurring_user_fee",
        "percent": percent,
        "payment_amount_minor": int(payment_amount_minor),
        "commission_amount_minor": commission_minor,
        "currency": str(policy.get("currency") or "KRW"),
        "provider": str(provider or "").strip().lower(),
        "transaction_id": transaction_id,
        "purchase_id": purchase_id,
        "plan_key": plan_key,
        "settlement_status": "pending",
        "settled_at": None,
        "created_at": utcnow().isoformat() + "Z",
    }
    events.append(event)
    store["commission_events"] = events

    for index, item in enumerate(store.get("attributions") or []):
        if isinstance(item, dict) and int(item.get("user_id") or 0) == int(user_id):
            if is_initial:
                item["initial_commission_paid"] = True
                item["initial_commission_event_id"] = event["id"]
            store["attributions"][index] = item
            break

    _save_store(store)
    if _local_revenue_enabled():
        store = _load_store()
        events = list(store.get("commission_events") or [])
        for index, item in enumerate(events):
            if isinstance(item, dict) and str(item.get("id") or "") == str(event["id"]):
                row = dict(item)
                row["settlement_status"] = COMMISSION_LEDGER_ONLY_STATUS
                events[index] = row
                event = row
                break
        store["commission_events"] = events
        _save_store(store)
    else:
        _maybe_auto_settle_after_accrual(
            country_code=str(attribution["country_code"]),
            region_code=str(attribution["region_code"]),
        )
    refreshed = _load_store()
    for item in refreshed.get("commission_events") or []:
        if isinstance(item, dict) and str(item.get("id") or "") == str(event["id"]):
            return item
    return event


def record_local_revenue_on_payment(
    *,
    user_id: int,
    payment_amount_minor: int,
    currency: Optional[str] = None,
    user_country_code: Optional[str] = None,
    provider: str,
    transaction_id: Optional[str] = None,
    purchase_id: Optional[int] = None,
    plan_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    policy = load_local_revenue_settlement_policy()
    if not policy.get("enabled"):
        return None
    if str(policy.get("payment_condition") or "on_settled_payment") != "on_settled_payment":
        return None
    if str(policy.get("mode") or "") != "full_local_revenue":
        return None
    if int(payment_amount_minor) <= 0:
        return None

    jurisdiction = resolve_revenue_jurisdiction(
        user_id=int(user_id),
        user_country_code=user_country_code,
        payment_currency=currency,
    )
    store = _load_store()
    events = list(store.get("local_revenue_events") or [])
    txn_key = str(transaction_id or purchase_id or "")
    for item in events:
        if not isinstance(item, dict):
            continue
        if txn_key and str(item.get("transaction_id") or item.get("purchase_id") or "") == txn_key:
            return item
        if purchase_id and int(item.get("purchase_id") or 0) == int(purchase_id):
            return item

    attribution = find_sales_attribution_for_user(user_id)
    event = {
        "id": secrets.token_hex(8),
        "user_id": int(user_id),
        "country_code": jurisdiction["country_code"],
        "region_code": jurisdiction["region_code"],
        "revenue_amount_minor": int(payment_amount_minor),
        "currency": jurisdiction["currency"],
        "provider": str(provider or "").strip().lower(),
        "transaction_id": transaction_id,
        "purchase_id": purchase_id,
        "plan_key": plan_key,
        "agent_id": attribution.get("agent_id") if attribution else None,
        "agent_code": attribution.get("agent_code") if attribution else None,
        "user_country_code": _normalize_country_code(user_country_code) if user_country_code else None,
        "settlement_status": "pending",
        "settled_at": None,
        "created_at": utcnow().isoformat() + "Z",
    }
    events.append(event)
    store["local_revenue_events"] = events
    _save_store(store)
    _maybe_auto_local_revenue_payout_after_accrual(
        country_code=str(jurisdiction["country_code"]),
        region_code=str(jurisdiction["region_code"]),
    )
    refreshed = _load_store()
    for item in refreshed.get("local_revenue_events") or []:
        if isinstance(item, dict) and str(item.get("id") or "") == str(event["id"]):
            return item
    return event


def record_worldlinco_payment_settlements(
    *,
    user_id: int,
    payment_amount_minor: int,
    currency: Optional[str] = None,
    user_country_code: Optional[str] = None,
    provider: str,
    transaction_id: Optional[str] = None,
    purchase_id: Optional[int] = None,
    plan_key: Optional[str] = None,
) -> Dict[str, Any]:
    commission_event = record_sales_commission_on_payment(
        user_id=user_id,
        payment_amount_minor=payment_amount_minor,
        provider=provider,
        transaction_id=transaction_id,
        purchase_id=purchase_id,
        plan_key=plan_key,
    )
    revenue_event = record_local_revenue_on_payment(
        user_id=user_id,
        payment_amount_minor=payment_amount_minor,
        currency=currency,
        user_country_code=user_country_code,
        provider=provider,
        transaction_id=transaction_id,
        purchase_id=purchase_id,
        plan_key=plan_key,
    )
    return {
        "commission_event": commission_event,
        "local_revenue_event": revenue_event,
    }


def approve_sales_settlement(
    *,
    country_code: Optional[str] = None,
    agent_id: Optional[str] = None,
    event_ids: Optional[List[str]] = None,
    approved_by: str = "admin",
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """레거시 Admin 승인 엔드포인트 — 자동 통장 지급으로 위임."""
    result = run_auto_office_payout(
        country_code=country_code,
        agent_id=agent_id,
        event_ids=event_ids,
        triggered_by=approved_by,
        note=note,
    )
    return {
        "approved_count": int(result.get("paid_count") or 0),
        "total_commission_minor": int(result.get("total_commission_minor") or 0),
        "events": result.get("payouts") or [],
        "mode": "auto_bank_transfer",
        "status": result.get("status"),
    }


def build_sales_invite_url(*, api_base: str, code: str) -> str:
    base = str(api_base or "").rstrip("/")
    return f"{base}/api/marketplace/worldlinco/sales/invite/{code}"


def build_sales_invite_deeplink(code: str) -> str:
    return f"worldlingo://sales?ref={code}"


def build_sales_invite_landing_html(*, code: str, api_base: str) -> str:
    agent = resolve_sales_agent_by_code(code)
    if not agent:
        return (
            "<!doctype html><html><head><meta charset='utf-8'><title>WorldLinco</title></head>"
            "<body style='font-family:sans-serif;padding:24px;'><h1>영업 QR을 찾을 수 없습니다</h1></body></html>"
        )
    name = str(agent.get("name") or "영업 담당")
    office = str(agent.get("office_name") or agent.get("country_code") or "")
    invite_url = build_sales_invite_url(api_base=api_base, code=code)
    deeplink = build_sales_invite_deeplink(code)
    apk_url = f"{str(api_base).rstrip('/')}/api/marketplace/latest.apk"
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>WorldLinco 영업 초대 · {code}</title></head>
<body style="font-family:sans-serif;background:#eef5ff;padding:24px;">
<div style="max-width:420px;margin:0 auto;background:#fff;border-radius:16px;padding:24px;">
<h1>WorldLinco 영업 초대</h1>
<p><strong>{name}</strong>{f' · {office}' if office else ''} 담당 QR입니다.</p>
<p>코드: <code>{code}</code></p>
<a href="{apk_url}" style="display:block;margin-top:12px;padding:14px;background:#1E6FE0;color:#fff;text-align:center;border-radius:12px;text-decoration:none;font-weight:700;">Android APK 설치</a>
<a href="{deeplink}" style="display:block;margin-top:10px;padding:14px;background:#f4f7fd;color:#1E6FE0;text-align:center;border-radius:12px;text-decoration:none;font-weight:700;">앱에서 열기</a>
</div></body></html>"""


def render_sales_qr_png(invite_url: str) -> bytes:
    import qrcode

    qr = qrcode.QRCode(version=None, box_size=8, border=2)
    qr.add_data(invite_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0B6FB0", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def sales_agent_admin_payload(*, agent_id: str, api_base: str) -> Dict[str, Any]:
    store = _load_store()
    agent = (store.get("agents_by_id") or {}).get(agent_id)
    if not isinstance(agent, dict):
        raise ValueError("agent_not_found")
    code = ensure_sales_agent_code(agent_id=agent_id)
    invite_url = build_sales_invite_url(api_base=api_base, code=code)
    user_ids = {
        int(item.get("user_id") or 0)
        for item in (store.get("attributions") or [])
        if isinstance(item, dict) and str(item.get("agent_id") or "") == agent_id
    }
    pending_minor = sum(
        int(item.get("commission_amount_minor") or 0)
        for item in (store.get("commission_events") or [])
        if isinstance(item, dict)
        and str(item.get("agent_id") or "") == agent_id
        and _is_payable_status(item.get("settlement_status"))
    )
    paid_out_minor = sum(
        int(item.get("commission_amount_minor") or 0)
        for item in (store.get("commission_events") or [])
        if isinstance(item, dict)
        and str(item.get("agent_id") or "") == agent_id
        and _is_settled_status(item.get("settlement_status"))
    )
    return {
        **agent,
        "code": code,
        "invite_url": invite_url,
        "deeplink": build_sales_invite_deeplink(code),
        "qr_url": f"{invite_url}/qr.png",
        "attributed_users": len(user_ids),
        "pending_commission_minor": pending_minor,
        "paid_out_commission_minor": paid_out_minor,
        "approved_commission_minor": paid_out_minor,
    }


def admin_sales_commission_dashboard_payload() -> Dict[str, Any]:
    store = _load_store()
    policy = load_sales_commission_policy()
    events = [item for item in (store.get("commission_events") or []) if isinstance(item, dict)]
    by_country: Dict[str, Dict[str, Any]] = {}
    by_agent: Dict[str, Dict[str, Any]] = {}

    for event in events:
        country = _normalize_country_code(event.get("country_code"))
        agent_id = str(event.get("agent_id") or "")
        amount = int(event.get("commission_amount_minor") or 0)
        status = str(event.get("settlement_status") or "pending")

        bucket = by_country.setdefault(
            country,
            {
                "country_code": country,
                "pending_minor": 0,
                "paid_out_minor": 0,
                "approved_minor": 0,
                "awaiting_bank_minor": 0,
                "event_count": 0,
            },
        )
        bucket["event_count"] += 1
        if _is_settled_status(status):
            bucket["paid_out_minor"] += amount
            bucket["approved_minor"] += amount
        elif status == "awaiting_bank_account":
            bucket["awaiting_bank_minor"] += amount
        else:
            bucket["pending_minor"] += amount

        agent_bucket = by_agent.setdefault(
            agent_id,
            {
                "agent_id": agent_id,
                "agent_name": event.get("agent_name"),
                "agent_code": event.get("agent_code"),
                "country_code": country,
                "pending_minor": 0,
                "paid_out_minor": 0,
                "approved_minor": 0,
                "awaiting_bank_minor": 0,
                "event_count": 0,
            },
        )
        agent_bucket["event_count"] += 1
        if _is_settled_status(status):
            agent_bucket["paid_out_minor"] += amount
            agent_bucket["approved_minor"] += amount
        elif status == "awaiting_bank_account":
            agent_bucket["awaiting_bank_minor"] += amount
        else:
            agent_bucket["pending_minor"] += amount

    agents = []
    for agent_id, agent in (store.get("agents_by_id") or {}).items():
        if not isinstance(agent, dict):
            continue
        agents.append({
            **agent,
            "code": (store.get("codes_by_agent_id") or {}).get(agent_id),
        })

    return {
        "updated_at": store.get("updated_at"),
        "commission_policy": policy,
        "local_revenue_settlement": load_local_revenue_settlement_policy(),
        "regions": store.get("regions") or {},
        "office_bank_accounts": list_office_bank_accounts_public(),
        "agents": sorted(agents, key=lambda row: str(row.get("country_code") or "")),
        "country_settlements": sorted(by_country.values(), key=lambda row: -int(row["pending_minor"] + row["awaiting_bank_minor"])),
        "agent_ledgers": sorted(by_agent.values(), key=lambda row: -int(row["pending_minor"] + row["awaiting_bank_minor"])),
        "recent_events": sorted(events, key=lambda row: str(row.get("created_at") or ""), reverse=True)[:100],
        "recent_local_revenue_events": sorted(
            [item for item in (store.get("local_revenue_events") or []) if isinstance(item, dict)],
            key=lambda row: str(row.get("created_at") or ""),
            reverse=True,
        )[:100],
        "recent_settlements": list(reversed((store.get("settlements") or [])[-20:])),
        "recent_payouts": list(reversed((store.get("payouts") or [])[-30:])),
        "recent_local_revenue_payouts": list(reversed((store.get("local_revenue_payouts") or [])[-30:])),
        "stats": {
            "agent_count": len(agents),
            "attribution_count": len(store.get("attributions") or []),
            "pending_commission_minor": sum(int(row["pending_minor"]) for row in by_country.values()),
            "awaiting_bank_commission_minor": sum(int(row["awaiting_bank_minor"]) for row in by_country.values()),
            "paid_out_commission_minor": sum(int(row["paid_out_minor"]) for row in by_country.values()),
            "approved_commission_minor": sum(int(row["paid_out_minor"]) for row in by_country.values()),
            "payout_count": len(store.get("payouts") or []),
            ** _local_revenue_dashboard_stats(store),
        },
    }


def _local_revenue_dashboard_stats(store: Dict[str, Any]) -> Dict[str, Any]:
    events = [item for item in (store.get("local_revenue_events") or []) if isinstance(item, dict)]
    pending_minor = sum(
        int(item.get("revenue_amount_minor") or 0)
        for item in events
        if not _is_settled_status(item.get("settlement_status"))
        and str(item.get("settlement_status") or "") != "awaiting_bank_account"
    )
    awaiting_bank_minor = sum(
        int(item.get("revenue_amount_minor") or 0)
        for item in events
        if str(item.get("settlement_status") or "") == "awaiting_bank_account"
    )
    paid_out_minor = sum(
        int(item.get("revenue_amount_minor") or 0)
        for item in events
        if _is_settled_status(item.get("settlement_status"))
    )
    return {
        "local_revenue_event_count": len(events),
        "pending_local_revenue_minor": pending_minor,
        "awaiting_bank_local_revenue_minor": awaiting_bank_minor,
        "paid_out_local_revenue_minor": paid_out_minor,
        "local_revenue_payout_count": len(store.get("local_revenue_payouts") or []),
    }


def _matches_regional_scope(
    *,
    country_code: str,
    region_code: str,
    item_country: Optional[str],
    item_region: Optional[str],
) -> bool:
    if _normalize_country_code(item_country) != _normalize_country_code(country_code):
        return False
    target_region = str(region_code or country_code).strip().upper()
    item_region_norm = str(item_region or item_country or country_code).strip().upper()
    return item_region_norm == target_region


def resolve_regional_manager_for_user(user_id: int) -> Optional[Dict[str, Any]]:
    store = _load_store()
    by_user = store.get("regional_managers_by_user_id") if isinstance(store.get("regional_managers_by_user_id"), dict) else {}
    manager_id = by_user.get(str(int(user_id)))
    if not manager_id:
        return None
    manager = (store.get("regional_managers_by_id") or {}).get(str(manager_id))
    if not isinstance(manager, dict):
        return None
    if not manager.get("active", True):
        return None
    return manager


def create_regional_manager(payload: RegionalManagerCreate, *, created_by: str = "admin") -> Dict[str, Any]:
    store = _load_store()
    by_id = dict(store.get("regional_managers_by_id") or {})
    by_user = dict(store.get("regional_managers_by_user_id") or {})
    user_key = str(int(payload.user_id))
    if user_key in by_user:
        raise ValueError("regional_manager_user_already_assigned")

    manager_id = uuid.uuid4().hex
    country_code = _normalize_country_code(payload.country_code)
    region_code = str(payload.region_code or country_code).strip().upper() or country_code
    manager = {
        "manager_id": manager_id,
        "user_id": int(payload.user_id),
        "name": str(payload.name).strip(),
        "country_code": country_code,
        "region_code": region_code,
        "office_name": str(payload.office_name or "").strip() or None,
        "contact_email": str(payload.contact_email or "").strip().lower() or None,
        "active": bool(payload.active),
        "created_by": created_by,
        "created_at": utcnow().isoformat() + "Z",
    }
    by_id[manager_id] = manager
    by_user[user_key] = manager_id
    store["regional_managers_by_id"] = by_id
    store["regional_managers_by_user_id"] = by_user
    _save_store(store)
    return manager


def update_regional_manager(manager_id: str, payload: RegionalManagerUpdate) -> Dict[str, Any]:
    store = _load_store()
    by_id = dict(store.get("regional_managers_by_id") or {})
    manager = by_id.get(manager_id)
    if not isinstance(manager, dict):
        raise ValueError("regional_manager_not_found")
    patch = payload.model_dump(exclude_unset=True)
    if "country_code" in patch and patch["country_code"] is not None:
        patch["country_code"] = _normalize_country_code(patch["country_code"])
    if "region_code" in patch and patch["region_code"] is not None:
        patch["region_code"] = str(patch["region_code"]).strip().upper()
    manager.update(patch)
    manager["updated_at"] = utcnow().isoformat() + "Z"
    by_id[manager_id] = manager
    store["regional_managers_by_id"] = by_id
    _save_store(store)
    return manager


def list_regional_managers_public() -> List[Dict[str, Any]]:
    store = _load_store()
    rows = [row for row in (store.get("regional_managers_by_id") or {}).values() if isinstance(row, dict)]
    return sorted(rows, key=lambda item: (str(item.get("country_code") or ""), str(item.get("region_code") or "")))


def resolve_regional_scope_for_access(
    *,
    is_admin: bool,
    user_id: int,
    country_code: Optional[str] = None,
    region_code: Optional[str] = None,
) -> Dict[str, str]:
    if is_admin:
        if not country_code:
            raise ValueError("country_code_required")
        country = _normalize_country_code(country_code)
        region = str(region_code or country).strip().upper() or country
        return {"country_code": country, "region_code": region, "scope": "admin"}

    manager = resolve_regional_manager_for_user(user_id)
    if not manager:
        raise ValueError("regional_manager_not_authorized")
    return {
        "country_code": _normalize_country_code(manager.get("country_code")),
        "region_code": str(manager.get("region_code") or manager.get("country_code")).strip().upper(),
        "scope": "regional_manager",
        "manager_id": str(manager.get("manager_id") or ""),
        "manager_name": str(manager.get("name") or ""),
    }


def regional_manager_dashboard_payload(
    *,
    country_code: str,
    region_code: str,
    scope_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    store = _load_store()
    country = _normalize_country_code(country_code)
    region = str(region_code or country).strip().upper() or country

    attributions = [
        item
        for item in (store.get("attributions") or [])
        if isinstance(item, dict)
        and _matches_regional_scope(
            country_code=country,
            region_code=region,
            item_country=item.get("country_code"),
            item_region=item.get("region_code"),
        )
    ]
    events = [
        item
        for item in (store.get("commission_events") or [])
        if isinstance(item, dict)
        and _matches_regional_scope(
            country_code=country,
            region_code=region,
            item_country=item.get("country_code"),
            item_region=item.get("region_code"),
        )
    ]
    payouts = [
        item
        for item in (store.get("payouts") or [])
        if isinstance(item, dict)
        and _matches_regional_scope(
            country_code=country,
            region_code=region,
            item_country=item.get("country_code"),
            item_region=item.get("region_code"),
        )
    ]
    local_revenue_events = [
        item
        for item in (store.get("local_revenue_events") or [])
        if isinstance(item, dict)
        and _matches_regional_scope(
            country_code=country,
            region_code=region,
            item_country=item.get("country_code"),
            item_region=item.get("region_code"),
        )
    ]
    local_revenue_payouts = [
        item
        for item in (store.get("local_revenue_payouts") or [])
        if isinstance(item, dict)
        and _matches_regional_scope(
            country_code=country,
            region_code=region,
            item_country=item.get("country_code"),
            item_region=item.get("region_code"),
        )
    ]
    agents = [
        item
        for item in (store.get("agents_by_id") or {}).values()
        if isinstance(item, dict)
        and _matches_regional_scope(
            country_code=country,
            region_code=region,
            item_country=item.get("country_code"),
            item_region=item.get("region_code"),
        )
    ]

    pending_minor = sum(
        int(item.get("commission_amount_minor") or 0)
        for item in events
        if not _is_settled_status(item.get("settlement_status"))
        and str(item.get("settlement_status") or "") != "awaiting_bank_account"
    )
    awaiting_bank_minor = sum(
        int(item.get("commission_amount_minor") or 0)
        for item in events
        if str(item.get("settlement_status") or "") == "awaiting_bank_account"
    )
    paid_out_minor = sum(
        int(item.get("commission_amount_minor") or 0)
        for item in events
        if _is_settled_status(item.get("settlement_status"))
    )
    local_pending_minor = sum(
        int(item.get("revenue_amount_minor") or 0)
        for item in local_revenue_events
        if not _is_settled_status(item.get("settlement_status"))
        and str(item.get("settlement_status") or "") != "awaiting_bank_account"
    )
    local_awaiting_bank_minor = sum(
        int(item.get("revenue_amount_minor") or 0)
        for item in local_revenue_events
        if str(item.get("settlement_status") or "") == "awaiting_bank_account"
    )
    local_paid_out_minor = sum(
        int(item.get("revenue_amount_minor") or 0)
        for item in local_revenue_events
        if _is_settled_status(item.get("settlement_status"))
    )
    initial_paid_users = sum(1 for item in attributions if item.get("initial_commission_paid"))

    bank_account = resolve_office_bank_account(country_code=country, region_code=region)
    by_agent: Dict[str, Dict[str, Any]] = {}
    for event in events:
        agent_id = str(event.get("agent_id") or "")
        bucket = by_agent.setdefault(
            agent_id,
            {
                "agent_id": agent_id,
                "agent_name": event.get("agent_name"),
                "agent_code": event.get("agent_code"),
                "attributed_users": 0,
                "paid_out_minor": 0,
                "pending_minor": 0,
            },
        )
        amount = int(event.get("commission_amount_minor") or 0)
        if _is_settled_status(event.get("settlement_status")):
            bucket["paid_out_minor"] += amount
        else:
            bucket["pending_minor"] += amount

    for attr in attributions:
        agent_id = str(attr.get("agent_id") or "")
        bucket = by_agent.setdefault(
            agent_id,
            {
                "agent_id": agent_id,
                "agent_name": attr.get("agent_name"),
                "agent_code": attr.get("agent_code"),
                "attributed_users": 0,
                "paid_out_minor": 0,
                "pending_minor": 0,
            },
        )
        bucket["attributed_users"] += 1

    return {
        "scope": scope_meta or {"country_code": country, "region_code": region},
        "country_code": country,
        "region_code": region,
        "office_bank_account": _public_office_bank_account(bank_account) if bank_account else None,
        "stats": {
            "attributed_users": len(attributions),
            "paying_users": initial_paid_users,
            "agent_count": len(agents),
            "commission_event_count": len(events),
            "pending_commission_minor": pending_minor,
            "awaiting_bank_commission_minor": awaiting_bank_minor,
            "paid_out_commission_minor": paid_out_minor,
            "payout_count": len(payouts),
            "local_revenue_event_count": len(local_revenue_events),
            "pending_local_revenue_minor": local_pending_minor,
            "awaiting_bank_local_revenue_minor": local_awaiting_bank_minor,
            "paid_out_local_revenue_minor": local_paid_out_minor,
            "local_revenue_payout_count": len(local_revenue_payouts),
        },
        "agent_summaries": sorted(by_agent.values(), key=lambda row: -int(row.get("attributed_users") or 0)),
        "recent_events": sorted(events, key=lambda row: str(row.get("created_at") or ""), reverse=True)[:50],
        "recent_local_revenue_events": sorted(
            local_revenue_events,
            key=lambda row: str(row.get("created_at") or ""),
            reverse=True,
        )[:50],
        "recent_payouts": sorted(payouts, key=lambda row: str(row.get("created_at") or ""), reverse=True)[:20],
        "recent_local_revenue_payouts": sorted(
            local_revenue_payouts,
            key=lambda row: str(row.get("created_at") or ""),
            reverse=True,
        )[:20],
    }


def regional_manager_users_payload(
    *,
    country_code: str,
    region_code: str,
    skip: int = 0,
    limit: int = 50,
    db_user_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    store = _load_store()
    country = _normalize_country_code(country_code)
    region = str(region_code or country).strip().upper() or country

    attributions = [
        item
        for item in (store.get("attributions") or [])
        if isinstance(item, dict)
        and _matches_regional_scope(
            country_code=country,
            region_code=region,
            item_country=item.get("country_code"),
            item_region=item.get("region_code"),
        )
    ]
    attributions.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    total = len(attributions)
    page = attributions[max(0, int(skip)) : max(0, int(skip)) + max(1, min(int(limit), 200))]

    events_by_user: Dict[int, List[Dict[str, Any]]] = {}
    for event in store.get("commission_events") or []:
        if not isinstance(event, dict):
            continue
        if not _matches_regional_scope(
            country_code=country,
            region_code=region,
            item_country=event.get("country_code"),
            item_region=event.get("region_code"),
        ):
            continue
        uid = int(event.get("user_id") or 0)
        if uid > 0:
            events_by_user.setdefault(uid, []).append(event)

    db_by_id = {int(row["id"]): row for row in (db_user_rows or []) if isinstance(row, dict) and row.get("id")}

    users: List[Dict[str, Any]] = []
    for attr in page:
        uid = int(attr.get("user_id") or 0)
        user_events = events_by_user.get(uid, [])
        paid_minor = sum(
            int(item.get("commission_amount_minor") or 0)
            for item in user_events
            if _is_settled_status(item.get("settlement_status"))
        )
        pending_minor = sum(
            int(item.get("commission_amount_minor") or 0)
            for item in user_events
            if not _is_settled_status(item.get("settlement_status"))
        )
        db_row = db_by_id.get(uid) or {}
        users.append({
            **attr,
            "user_id": uid,
            "username": db_row.get("username") or attr.get("username"),
            "email": db_row.get("email") or attr.get("email"),
            "full_name": db_row.get("full_name"),
            "country_code_user": db_row.get("country_code") or attr.get("user_country_code"),
            "preferred_language": db_row.get("preferred_language"),
            "is_active": db_row.get("is_active"),
            "user_created_at": db_row.get("created_at"),
            "payment_count": len(user_events),
            "paid_commission_minor": paid_minor,
            "pending_commission_minor": pending_minor,
            "has_initial_payment": bool(attr.get("initial_commission_paid")),
        })

    return {
        "country_code": country,
        "region_code": region,
        "users": users,
        "total": total,
        "skip": int(skip),
        "limit": int(limit),
    }
