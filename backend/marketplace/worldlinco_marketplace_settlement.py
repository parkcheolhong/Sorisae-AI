"""WorldLinco marketplace purchase settlement — apply referral/discount/ledger on payment confirm only."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.marketplace.worldlinco_billing_plans import (
    WORLDLINGCO_PLAN_DEFINITIONS,
    resolve_worldlinco_plan_by_amount,
)


def _worldlinco_plan_amounts_minor() -> tuple[int, ...]:
    return tuple(int(row["amount_minor"]) for row in WORLDLINGCO_PLAN_DEFINITIONS.values())


def resolve_worldlinco_purchase_settlement_context(
    *,
    user_id: int,
    payment_amount_minor: int,
    db: Any = None,
) -> Optional[Dict[str, Any]]:
    """Return settlement context when purchase amount maps to a WorldLinco plan (incl. referral discount)."""
    from backend.marketplace.worldlinco_referral import resolve_referral_discount_quote

    paid_minor = int(payment_amount_minor)
    if paid_minor <= 0:
        return None

    original_minor = paid_minor
    matched_plan = resolve_worldlinco_plan_by_amount(paid_minor)
    if matched_plan is None:
        for candidate in _worldlinco_plan_amounts_minor():
            quote_probe = resolve_referral_discount_quote(
                user_id=int(user_id),
                amount_minor=int(candidate),
                db=db,
            )
            if quote_probe.get("eligible") and int(quote_probe.get("final_amount_minor") or 0) == paid_minor:
                original_minor = int(candidate)
                matched_plan = resolve_worldlinco_plan_by_amount(original_minor)
                break

    if matched_plan is None:
        return None

    quote = resolve_referral_discount_quote(
        user_id=int(user_id),
        amount_minor=int(original_minor),
        db=db,
    )
    return {
        "original_amount_minor": int(original_minor),
        "paid_amount_minor": paid_minor,
        "plan_key": str(matched_plan.get("plan_key") or ""),
        "quote": quote,
    }


def apply_confirmed_worldlinco_marketplace_settlements(
    *,
    user_id: int,
    purchase_id: int,
    payment_amount_minor: int,
    transaction_id: str,
    user_country_code: Optional[str] = None,
    currency: str = "KRW",
    db: Any = None,
) -> Dict[str, Any]:
    """Apply referral discount + sales/local revenue ledgers after purchase status is confirmed."""
    ctx = resolve_worldlinco_purchase_settlement_context(
        user_id=int(user_id),
        payment_amount_minor=int(payment_amount_minor),
        db=db,
    )
    if not ctx:
        return {"applied": False, "reason": "not_worldlinco_plan"}

    from backend.marketplace.worldlinco_referral import apply_referral_discount_payment
    from backend.marketplace.worldlinco_sales_commission import record_worldlinco_payment_settlements

    quote = ctx.get("quote") if isinstance(ctx.get("quote"), dict) else {}
    paid_minor = int(ctx.get("paid_amount_minor") or payment_amount_minor)
    original_minor = int(ctx.get("original_amount_minor") or paid_minor)
    referral_applied = None

    if quote.get("eligible") and paid_minor == int(quote.get("final_amount_minor") or 0):
        referral_applied = apply_referral_discount_payment(
            user_id=int(user_id),
            provider="card",
            original_amount_minor=int(quote.get("original_amount_minor") or original_minor),
            final_amount_minor=paid_minor,
            plan_key=str(ctx.get("plan_key") or ""),
            purchase_id=int(purchase_id),
            transaction_id=str(transaction_id or ""),
        )

    settlements = record_worldlinco_payment_settlements(
        user_id=int(user_id),
        payment_amount_minor=paid_minor,
        currency=currency,
        user_country_code=user_country_code,
        provider="card",
        transaction_id=str(transaction_id or ""),
        purchase_id=int(purchase_id),
        plan_key=str(ctx.get("plan_key") or "") or None,
    )

    return {
        "applied": True,
        "plan_key": ctx.get("plan_key"),
        "referral_discount_applied": referral_applied,
        "settlements": settlements,
    }
