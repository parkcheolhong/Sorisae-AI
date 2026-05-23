import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from backend.marketplace.database import SessionLocal, init_db
from backend.marketplace import subscription_models as sm

BASE = "http://127.0.0.1:8000"
now_tag = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
report_path = Path("reports") / f"step3_subscription_validation_{now_tag}.json"
report_path.parent.mkdir(parents=True, exist_ok=True)

email = f"step3_{uuid.uuid4().hex[:8]}@example.com"
password = "Step3!Pass12345"
product_code = "marketplace-suite"
plan_code = "pro"

init_db()


def req(method, url, **kwargs):
    response = requests.request(method, url, timeout=20, **kwargs)
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text}
    return response.status_code, body


def ensure_subscription_seed():
    db = SessionLocal()
    try:
        product = db.query(sm.SubscriptionProduct).filter(sm.SubscriptionProduct.code == product_code).first()
        if product is None:
            product = sm.SubscriptionProduct(code=product_code, name="Marketplace Suite", is_active=True)
            db.add(product)
            db.flush()

        plan = (
            db.query(sm.SubscriptionPlan)
            .filter(sm.SubscriptionPlan.product_id == product.id, sm.SubscriptionPlan.code == plan_code)
            .first()
        )
        if plan is None:
            plan = sm.SubscriptionPlan(
                product_id=product.id,
                code=plan_code,
                name="Pro",
                device_limit=1,
                is_active=True,
            )
            db.add(plan)
            db.flush()
        else:
            plan.device_limit = 1
            plan.is_active = True

        entitlement = (
            db.query(sm.SubscriptionEntitlement)
            .filter(
                sm.SubscriptionEntitlement.plan_id == plan.id,
                sm.SubscriptionEntitlement.entitlement_key == "marketplace_access",
            )
            .first()
        )
        if entitlement is None:
            db.add(sm.SubscriptionEntitlement(plan_id=plan.id, entitlement_key="marketplace_access"))

        price = (
            db.query(sm.SubscriptionPrice)
            .filter(
                sm.SubscriptionPrice.product_id == product.id,
                sm.SubscriptionPrice.plan_id == plan.id,
                sm.SubscriptionPrice.provider == "google",
                sm.SubscriptionPrice.channel == "mobile",
            )
            .order_by(sm.SubscriptionPrice.id.desc())
            .first()
        )
        if price is None:
            db.add(
                sm.SubscriptionPrice(
                    product_id=product.id,
                    plan_id=plan.id,
                    provider="google",
                    country_code="KR",
                    currency="KRW",
                    amount_minor=9900,
                    billing_period="monthly",
                    channel="mobile",
                    external_price_code="google-pro-monthly",
                    is_active=True,
                )
            )
        else:
            price.is_active = True

        db.commit()
    finally:
        db.close()


def get_status(headers):
    code, body = req(
        "GET",
        f"{BASE}/api/marketplace/v1/me/subscription",
        headers=headers,
        params={"product_code": product_code},
    )
    if code != 200:
        raise RuntimeError(f"status failed: {code} {body}")
    return body


def webhook(headers, event_type, idx, **extra):
    payload = {
        "event_id": f"evt-{event_type}-{idx}-{uuid.uuid4().hex[:8]}",
        "event_type": event_type,
        "product_code": product_code,
        "plan_code": plan_code,
        "event_time": datetime.utcnow().isoformat(),
        "payload": {},
    }
    payload.update(extra)
    code, body = req("POST", f"{BASE}/api/marketplace/v1/billing/webhooks/google", headers=headers, json=payload)
    if code != 200:
        raise RuntimeError(f"webhook {event_type} failed: {code} {body}")
    return body


def cancel_subscription(headers):
    code, body = req(
        "POST",
        f"{BASE}/api/marketplace/v1/me/subscription/cancel",
        headers=headers,
        json={"product_code": product_code},
    )
    if code != 200:
        raise RuntimeError(f"cancel failed: {code} {body}")
    return body


def register_device(headers, device_id):
    payload = {
        "product_code": product_code,
        "device_id": device_id,
        "device_type": "desktop",
        "platform": "windows",
        "app_version": "1.0.0",
        "os_version": "windows-11",
    }
    return req("POST", f"{BASE}/api/marketplace/v1/me/devices/register", headers=headers, json=payload)


def revoke_device(headers, device_id):
    code, body = req(
        "POST",
        f"{BASE}/api/marketplace/v1/me/devices/revoke",
        headers=headers,
        json={"product_code": product_code, "device_id": device_id},
    )
    if code != 200:
        raise RuntimeError(f"revoke failed: {code} {body}")
    return body


def activate_subscription(headers, idx, user_id):
    return webhook(
        headers,
        "purchase_verified",
        idx,
        user_id=user_id,
        period_start=datetime.utcnow().isoformat(),
        period_end=(datetime.utcnow() + timedelta(days=30)).isoformat(),
    )


ensure_subscription_seed()

signup_payload = {
    "username": f"step3_{uuid.uuid4().hex[:8]}",
    "email": email,
    "password": password,
    "full_name": "Step3 Validator",
    "member_type": "individual",
}
scode, sbody = req("POST", f"{BASE}/api/auth/signup", json=signup_payload)
if scode not in (200, 201):
    raise RuntimeError(f"signup failed: {scode} {sbody}")

lcode, lbody = req(
    "POST",
    f"{BASE}/api/auth/login",
    data={"username": email, "password": password},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
if lcode != 200 or "access_token" not in lbody:
    raise RuntimeError(f"login failed: {lcode} {lbody}")

headers = {"Authorization": f"Bearer {lbody['access_token']}"}
user_id = int(sbody["id"])

results = {
    "user": email,
    "executed_at": datetime.utcnow().isoformat(),
    "scenarios": {},
}

s1 = []
for i in (1, 2):
    purchase_result = activate_subscription(headers, i, user_id)
    status_result = get_status(headers)
    if status_result["subscription_status"] != "active":
        raise RuntimeError(f"scenario1 run{i} unexpected status: {status_result}")
    s1.append({"run": i, "reason": purchase_result["reason_code"], "status": status_result["subscription_status"]})
results["scenarios"]["new_subscription_success"] = s1

s2 = []
for i in (1, 2):
    webhook_result = webhook(
        headers,
        "renewal_succeeded",
        i,
        user_id=user_id,
        period_start=datetime.utcnow().isoformat(),
        period_end=(datetime.utcnow() + timedelta(days=30)).isoformat(),
    )
    status_result = get_status(headers)
    if status_result["subscription_status"] != "active":
        raise RuntimeError(f"scenario2 run{i} unexpected status: {status_result}")
    s2.append({"run": i, "reason": webhook_result["reason_code"], "status": status_result["subscription_status"]})
results["scenarios"]["renewal_success"] = s2

s3 = []
for i in (1, 2):
    failed_result = webhook(
        headers,
        "renewal_failed",
        i,
        user_id=user_id,
        grace_until=(datetime.utcnow() + timedelta(days=3)).isoformat(),
    )
    after_failed = get_status(headers)
    if after_failed["subscription_status"] != "grace_period":
        raise RuntimeError(f"scenario3 run{i} failed-step unexpected status: {after_failed}")
    recover_result = webhook(
        headers,
        "renewal_succeeded",
        i,
        user_id=user_id,
        period_start=datetime.utcnow().isoformat(),
        period_end=(datetime.utcnow() + timedelta(days=30)).isoformat(),
    )
    after_recover = get_status(headers)
    if after_recover["subscription_status"] != "active":
        raise RuntimeError(f"scenario3 run{i} recover-step unexpected status: {after_recover}")
    s3.append(
        {
            "run": i,
            "failed_status": after_failed["subscription_status"],
            "recover_status": after_recover["subscription_status"],
            "failed_reason": failed_result["reason_code"],
            "recover_reason": recover_result["reason_code"],
        }
    )
results["scenarios"]["failed_grace_recover"] = s3

s4 = []
for i in (1, 2):
    activate_subscription(headers, 100 + i, user_id)
    cancel_result = cancel_subscription(headers)
    if not cancel_result["cancel_at_period_end"]:
        raise RuntimeError(f"scenario4 run{i} cancel flag missing: {cancel_result}")
    end_result = webhook(
        headers,
        "period_ended",
        i,
        user_id=user_id,
        period_end=datetime.utcnow().isoformat(),
    )
    status_result = get_status(headers)
    if status_result["subscription_status"] != "canceled":
        raise RuntimeError(f"scenario4 run{i} unexpected status: {status_result}")
    s4.append({"run": i, "after_end": status_result["subscription_status"], "reason": end_result["reason_code"]})
results["scenarios"]["cancel_then_period_end"] = s4

s5 = []
for i in (1, 2):
    activate_subscription(headers, 200 + i, user_id)
    refund_result = webhook(headers, "refund_applied", i, user_id=user_id)
    status_refunded = get_status(headers)
    if status_refunded["subscription_status"] != "refunded":
        raise RuntimeError(f"scenario5 run{i} refund-step unexpected status: {status_refunded}")
    webhook(
        headers,
        "subscription_restored",
        i,
        user_id=user_id,
        period_start=datetime.utcnow().isoformat(),
        period_end=(datetime.utcnow() + timedelta(days=30)).isoformat(),
    )
    status_restored = get_status(headers)
    if status_restored["subscription_status"] != "active":
        raise RuntimeError(f"scenario5 run{i} restore-step unexpected status: {status_restored}")
    s5.append({"run": i, "after_refund": "refunded", "after_restore": "active", "reason": refund_result["reason_code"]})
results["scenarios"]["refund_revoke_entitlement"] = s5

s6 = []
activate_subscription(headers, 300, user_id)
for i in (1, 2):
    primary_id = f"device-{i}-a"
    secondary_id = f"device-{i}-b"
    ok_code, _ok_body = register_device(headers, primary_id)
    if ok_code != 200:
        raise RuntimeError(f"scenario6 run{i} primary register failed: {ok_code}")
    blocked_code, blocked_body = register_device(headers, secondary_id)
    if blocked_code != 409:
        raise RuntimeError(f"scenario6 run{i} expected 409, got: {blocked_code} {blocked_body}")
    revoke_device(headers, primary_id)
    s6.append({"run": i, "primary_register": ok_code, "secondary_register": blocked_code, "secondary_detail": blocked_body.get("detail")})
results["scenarios"]["device_limit"] = s6

results["final_status"] = get_status(headers)
report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "report": str(report_path), "user": email}, ensure_ascii=False))

