"""WorldLinco 사용자 추천(리퍼럴) — QR/링크 홍보 · 가입 attribution · 관리자 집계 SSOT."""
from __future__ import annotations

import io
import json
import secrets
from copy import deepcopy
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field

from backend.marketplace.worldlinco_json_store import (
    STORE_KEY_REFERRALS,
    load_json_document,
    save_json_document,
)
from backend.time_utils import utcnow

REFERRAL_STORE_PATH = Path(__file__).resolve().parent.parent.parent / ".runtime" / "worldlinco_referrals.json"
MAX_REFERRAL_SIGNUPS = 100_000

REFERRAL_DEFAULTS: Dict[str, Any] = {
    "version": 1,
    "updated_at": None,
    "codes_by_user_id": {},
    "codes": {},
    "signups": [],
    "discount_policy": {
        "enabled": False,
        "percent": 3.0,
        "applies_to": "first_payment",
        "target": "referred_user",
        "stripe_coupon_id": None,
        "google_offer_id": "referral-first-payment-3pct",
        "apple_offer_id": "referral-first-payment-3pct",
        "note": "추천 가입자 첫 결제 시 프로그램 비용 할인(기본 3%).",
    },
}


def _load_store() -> Dict[str, Any]:
    return load_json_document(
        store_key=STORE_KEY_REFERRALS,
        defaults=REFERRAL_DEFAULTS,
        file_path=REFERRAL_STORE_PATH,
    )


def _save_store(payload: Dict[str, Any]) -> Dict[str, Any]:
    signups = payload.get("signups") if isinstance(payload.get("signups"), list) else []
    if len(signups) > MAX_REFERRAL_SIGNUPS:
        signups = signups[-MAX_REFERRAL_SIGNUPS:]
    normalized = {
        "version": int(payload.get("version") or 1),
        "updated_at": utcnow().isoformat() + "Z",
        "codes_by_user_id": dict(payload.get("codes_by_user_id") or {}),
        "codes": dict(payload.get("codes") or {}),
        "signups": signups,
        "discount_policy": _normalize_discount_policy(payload.get("discount_policy")),
    }
    save_json_document(
        store_key=STORE_KEY_REFERRALS,
        file_path=REFERRAL_STORE_PATH,
        payload=normalized,
    )
    return normalized


def _normalize_code(raw: Optional[str]) -> Optional[str]:
    code = str(raw or "").strip().upper()
    if len(code) < 4 or len(code) > 32:
        return None
    if not code.startswith("WL"):
        return None
    return code


def split_signup_attribution_codes(
    referral_code: Optional[str],
    sales_agent_code: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """유저 추천(WL)과 영업 QR(WS) 분리. WS는 3% 추천 할인 대상이 아님."""
    referral = _normalize_code(referral_code)
    sales = str(sales_agent_code or "").strip().upper() or None
    raw_referral = str(referral_code or "").strip().upper()
    if raw_referral.startswith("WS"):
        sales = sales or raw_referral
        referral = None
    if sales and not sales.startswith("WS"):
        sales = None
    return referral, sales or None


def _generate_code(user_id: int) -> str:
    suffix = secrets.token_hex(3).upper()
    return f"WL{int(user_id)}{suffix}"


def ensure_user_referral_code(*, user_id: int, username: str) -> str:
    store = _load_store()
    by_user = store.get("codes_by_user_id") if isinstance(store.get("codes_by_user_id"), dict) else {}
    existing = by_user.get(str(int(user_id)))
    if existing:
        code = _normalize_code(existing)
        if code:
            return code

    codes = store.get("codes") if isinstance(store.get("codes"), dict) else {}
    for _ in range(8):
        candidate = _generate_code(user_id)
        if candidate not in codes:
            codes[candidate] = {
                "user_id": int(user_id),
                "username": str(username or "").strip() or f"user-{user_id}",
                "created_at": utcnow().isoformat() + "Z",
            }
            by_user[str(int(user_id))] = candidate
            store["codes"] = codes
            store["codes_by_user_id"] = by_user
            _save_store(store)
            return candidate
    raise RuntimeError("referral_code_generation_failed")


def resolve_referrer_by_code(code: Optional[str]) -> Optional[Dict[str, Any]]:
    normalized = _normalize_code(code)
    if not normalized:
        return None
    store = _load_store()
    codes = store.get("codes") if isinstance(store.get("codes"), dict) else {}
    entry = codes.get(normalized)
    if not isinstance(entry, dict):
        return None
    return {
        "code": normalized,
        "user_id": int(entry.get("user_id") or 0),
        "username": str(entry.get("username") or ""),
    }


def record_referral_signup(
    *,
    referral_code: Optional[str],
    referred_user_id: int,
    referred_username: str,
    referred_email: str,
) -> Optional[Dict[str, Any]]:
    referrer = resolve_referrer_by_code(referral_code)
    if not referrer:
        return None
    if int(referrer["user_id"]) == int(referred_user_id):
        return None

    store = _load_store()
    signups = list(store.get("signups") or [])
    for item in signups:
        if isinstance(item, dict) and int(item.get("referred_user_id") or 0) == int(referred_user_id):
            return item

    record = {
        "id": secrets.token_hex(8),
        "referrer_user_id": int(referrer["user_id"]),
        "referrer_username": str(referrer.get("username") or ""),
        "referrer_code": str(referrer["code"]),
        "referred_user_id": int(referred_user_id),
        "referred_username": str(referred_username or "").strip(),
        "referred_email": str(referred_email or "").strip().lower(),
        "created_at": utcnow().isoformat() + "Z",
    }
    signups.append(record)
    store["signups"] = signups
    _save_store(store)
    return record


def _count_signups_for_user(user_id: int) -> int:
    store = _load_store()
    signups = store.get("signups") if isinstance(store.get("signups"), list) else []
    return sum(
        1
        for item in signups
        if isinstance(item, dict) and int(item.get("referrer_user_id") or 0) == int(user_id)
    )


def build_invite_url(*, api_base: str, code: str) -> str:
    base = str(api_base or "").rstrip("/")
    return f"{base}/api/marketplace/worldlinco/invite/{quote(str(code or '').strip(), safe='')}"


def build_invite_deeplink(code: str) -> str:
    return f"worldlingo://invite?ref={quote(str(code or '').strip(), safe='')}"


def referral_me_payload(*, user_id: int, username: str, api_base: str) -> Dict[str, Any]:
    code = ensure_user_referral_code(user_id=user_id, username=username)
    invite_url = build_invite_url(api_base=api_base, code=code)
    policy = load_referral_discount_policy()
    return {
        "code": code,
        "invite_url": invite_url,
        "deeplink": build_invite_deeplink(code),
        "qr_url": f"{invite_url}/qr.png",
        "signup_count": _count_signups_for_user(user_id),
        "updated_at": utcnow().isoformat() + "Z",
        "discount_policy": {
            "enabled": bool(policy.get("enabled")),
            "percent": float(policy.get("percent") or 0),
            "applies_to": str(policy.get("applies_to") or "first_payment"),
        },
    }


def build_invite_landing_html(*, code: str, api_base: str, referrer_username: str = "") -> str:
    referrer = resolve_referrer_by_code(code)
    if not referrer:
        return (
            "<!doctype html><html><head><meta charset='utf-8'><title>WorldLinco</title></head>"
            "<body style='font-family:sans-serif;padding:24px;'><h1>추천 링크를 찾을 수 없습니다</h1>"
            "<p>코드가 만료되었거나 잘못되었습니다.</p></body></html>"
        )
    canonical_code = _normalize_code(str(referrer.get("code") or code)) or "WORLDLINCO"
    name = escape(str(referrer_username or referrer.get("username") or "친구").strip())
    safe_code = escape(canonical_code)
    invite_url = build_invite_url(api_base=api_base, code=canonical_code)
    deeplink = escape(build_invite_deeplink(canonical_code))
    apk_url = escape(f"{str(api_base).rstrip('/')}/api/marketplace/latest.apk")
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WorldLinco 초대 · {safe_code}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#e3f0ff; margin:0; padding:24px; color:#1a1f36; }}
    .card {{ max-width:420px; margin:0 auto; background:#fff; border-radius:16px; padding:24px; box-shadow:0 8px 24px rgba(30,111,224,.12); }}
    h1 {{ font-size:22px; margin:0 0 8px; }}
    p {{ line-height:1.55; color:#4a5f7f; }}
    .btn {{ display:block; text-align:center; margin-top:14px; padding:14px 16px; border-radius:12px; text-decoration:none; font-weight:800; }}
    .primary {{ background:#1E6FE0; color:#fff; }}
    .secondary {{ background:#f4f7fd; color:#1E6FE0; border:1px solid #cfe0f8; }}
    code {{ background:#f4f7fd; padding:2px 8px; border-radius:8px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>WorldLinco 초대</h1>
    <p><strong>{name}</strong>님이 WorldLinco 앱을 추천했습니다.<br/>50개국 실시간 통번역 채팅·통화 앱입니다.</p>
    <p>추천 코드: <code>{safe_code}</code></p>
    <a class="btn primary" href="{apk_url}">Android APK 설치</a>
    <a class="btn secondary" href="{deeplink}">앱에서 열기 (설치 후)</a>
    <p style="font-size:12px;margin-top:16px;">설치 후 위 버튼을 누르거나, 가입 시 추천 코드 <code>{safe_code}</code>가 자동 적용됩니다.</p>
  </div>
</body>
</html>"""


class ReferralDiscountPolicyUpdate(BaseModel):
    enabled: Optional[bool] = None
    percent: Optional[float] = Field(None, ge=0.0, le=50.0)
    applies_to: Optional[str] = Field(None, max_length=40)
    target: Optional[str] = Field(None, max_length=40)
    stripe_coupon_id: Optional[str] = Field(None, max_length=120)
    google_offer_id: Optional[str] = Field(None, max_length=120)
    apple_offer_id: Optional[str] = Field(None, max_length=120)
    note: Optional[str] = Field(None, max_length=500)


def _normalize_discount_policy(raw: Any) -> Dict[str, Any]:
    defaults = deepcopy(REFERRAL_DEFAULTS["discount_policy"])
    if not isinstance(raw, dict):
        return defaults
    merged = {**defaults, **raw}
    try:
        merged["percent"] = float(merged.get("percent") or defaults["percent"])
    except (TypeError, ValueError):
        merged["percent"] = defaults["percent"]
    merged["enabled"] = bool(merged.get("enabled"))
    merged["applies_to"] = str(merged.get("applies_to") or defaults["applies_to"])
    merged["target"] = str(merged.get("target") or defaults["target"])
    return merged


def load_referral_discount_policy() -> Dict[str, Any]:
    store = _load_store()
    return _normalize_discount_policy(store.get("discount_policy"))


def apply_referral_discount_policy_update(update: ReferralDiscountPolicyUpdate, *, updated_by: str = "admin") -> Dict[str, Any]:
    store = _load_store()
    current = _normalize_discount_policy(store.get("discount_policy"))
    patch = update.model_dump(exclude_unset=True)
    merged = _normalize_discount_policy({**current, **patch})
    store["discount_policy"] = merged
    store["discount_policy"]["updated_by"] = updated_by
    _save_store(store)
    return merged


def find_referral_signup_for_user(user_id: int) -> Optional[Dict[str, Any]]:
    store = _load_store()
    signups = store.get("signups") if isinstance(store.get("signups"), list) else []
    for item in signups:
        if isinstance(item, dict) and int(item.get("referred_user_id") or 0) == int(user_id):
            return item
    return None


def user_has_settled_payment(db: Any, user_id: int) -> bool:
    from backend.marketplace import models as marketplace_models
    from backend.marketplace import subscription_models

    settled_statuses = {"completed", "paid", "success", "approved", "succeeded"}
    purchase = (
        db.query(marketplace_models.Purchase)
        .filter(
            marketplace_models.Purchase.buyer_id == int(user_id),
            marketplace_models.Purchase.status.in_(list(settled_statuses)),
        )
        .first()
    )
    if purchase is not None:
        return True

    event = (
        db.query(subscription_models.PaymentEvent)
        .filter(
            subscription_models.PaymentEvent.user_id == int(user_id),
            subscription_models.PaymentEvent.event_type == "purchase_verified",
        )
        .first()
    )
    return event is not None


def resolve_referral_discount_quote(*, user_id: int, amount_minor: int, db: Any = None) -> Dict[str, Any]:
    policy = load_referral_discount_policy()
    amount = max(0, int(amount_minor))
    base = {
        "eligible": False,
        "enabled": bool(policy.get("enabled")),
        "percent": float(policy.get("percent") or 0),
        "reason": "disabled",
        "original_amount_minor": amount,
        "discount_amount_minor": 0,
        "final_amount_minor": amount,
        "applies_to": str(policy.get("applies_to") or "first_payment"),
        "google_offer_id": policy.get("google_offer_id"),
        "apple_offer_id": policy.get("apple_offer_id"),
        "stripe_coupon_id": policy.get("stripe_coupon_id"),
    }
    if not policy.get("enabled"):
        return base
    try:
        from backend.marketplace.worldlinco_sales_commission import find_sales_attribution_for_user

        if find_sales_attribution_for_user(int(user_id)):
            return {**base, "reason": "sales_agent_signup_excluded"}
    except Exception:
        pass
    signup = find_referral_signup_for_user(user_id)
    if not signup:
        return {**base, "reason": "no_referral_signup"}
    if signup.get("first_payment_discount_applied_at"):
        return {**base, "reason": "already_applied", "referrer_code": signup.get("referrer_code")}
    if db is not None and user_has_settled_payment(db, user_id):
        return {**base, "reason": "prior_payment", "referrer_code": signup.get("referrer_code")}

    percent = float(policy.get("percent") or 0)
    discount_minor = int(round(amount * percent / 100.0))
    final_minor = max(0, amount - discount_minor)
    return {
        **base,
        "eligible": True,
        "reason": "eligible",
        "percent": percent,
        "discount_amount_minor": discount_minor,
        "final_amount_minor": final_minor,
        "referrer_code": signup.get("referrer_code"),
        "referrer_user_id": signup.get("referrer_user_id"),
        "referrer_username": signup.get("referrer_username"),
    }


def apply_referral_discount_payment(
    *,
    user_id: int,
    provider: str,
    original_amount_minor: int,
    final_amount_minor: int,
    plan_key: Optional[str] = None,
    purchase_id: Optional[int] = None,
    transaction_id: Optional[str] = None,
    external_offer_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    quote = resolve_referral_discount_quote(user_id=user_id, amount_minor=original_amount_minor)
    if not quote.get("eligible"):
        return None
    if int(final_amount_minor) != int(quote.get("final_amount_minor") or original_amount_minor):
        return None

    store = _load_store()
    signups = list(store.get("signups") or [])
    updated: Optional[Dict[str, Any]] = None
    for index, item in enumerate(signups):
        if not isinstance(item, dict):
            continue
        if int(item.get("referred_user_id") or 0) != int(user_id):
            continue
        if item.get("first_payment_discount_applied_at"):
            return item
        patched = {
            **item,
            "first_payment_discount_applied_at": utcnow().isoformat() + "Z",
            "first_payment_provider": str(provider or "").strip().lower(),
            "first_payment_original_amount_minor": int(original_amount_minor),
            "first_payment_discount_amount_minor": int(quote.get("discount_amount_minor") or 0),
            "first_payment_final_amount_minor": int(final_amount_minor),
            "first_payment_plan_key": str(plan_key or "").strip() or None,
            "first_payment_purchase_id": purchase_id,
            "first_payment_transaction_id": transaction_id,
            "first_payment_external_offer_id": external_offer_id,
        }
        signups[index] = patched
        updated = patched
        break
    if updated is None:
        return None
    store["signups"] = signups
    _save_store(store)
    return updated


def render_referral_qr_png(invite_url: str) -> bytes:
    import qrcode

    qr = qrcode.QRCode(version=None, box_size=8, border=2)
    qr.add_data(invite_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1E6FE0", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def admin_referral_dashboard_payload() -> Dict[str, Any]:
    store = _load_store()
    signups = store.get("signups") if isinstance(store.get("signups"), list) else []
    by_referrer: Dict[int, Dict[str, Any]] = {}
    for item in signups:
        if not isinstance(item, dict):
            continue
        rid = int(item.get("referrer_user_id") or 0)
        if rid <= 0:
            continue
        bucket = by_referrer.setdefault(
            rid,
            {
                "referrer_user_id": rid,
                "referrer_username": str(item.get("referrer_username") or ""),
                "referrer_code": str(item.get("referrer_code") or ""),
                "signup_count": 0,
                "recent_signups": [],
            },
        )
        bucket["signup_count"] += 1
        bucket["recent_signups"].append(item)

    leaders = sorted(by_referrer.values(), key=lambda row: (-int(row["signup_count"]), int(row["referrer_user_id"])))
    for row in leaders:
        row["recent_signups"] = sorted(
            row.get("recent_signups") or [],
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )[:10]

    signups_list = signups
    applied_count = sum(
        1 for item in signups_list if isinstance(item, dict) and item.get("first_payment_discount_applied_at")
    )
    return {
        "updated_at": store.get("updated_at"),
        "total_signups": len(signups),
        "referrer_count": len(leaders),
        "leaders": leaders,
        "recent_signups": sorted(
            [item for item in signups if isinstance(item, dict)],
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )[:50],
        "discount_policy": load_referral_discount_policy(),
        "discount_stats": {
            "eligible_pending": max(0, len(signups_list) - applied_count),
            "discount_applied_count": applied_count,
        },
    }
