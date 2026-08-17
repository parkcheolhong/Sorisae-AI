from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.marketplace import models as marketplace_models
from backend.marketplace import subscription_models
from backend.marketplace.database import Base
from backend.marketplace.subscription_service import subscription_service
from backend.marketplace.subscription_state_machine import SubscriptionStatus


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _seed_subscription(db):
    user = marketplace_models.User(
        email="service-test@example.com",
        username="service_tester",
        hashed_password="not-used",
    )
    db.add(user)
    db.flush()

    product = subscription_models.SubscriptionProduct(
        code="stock-ai-suite",
        name="Stock AI Suite",
        is_active=True,
    )
    db.add(product)
    db.flush()

    plan = subscription_models.SubscriptionPlan(
        product_id=product.id,
        code="pro",
        name="Pro",
        device_limit=2,
        is_active=True,
    )
    db.add(plan)
    db.flush()

    db.add(
        subscription_models.SubscriptionEntitlement(
            plan_id=plan.id,
            entitlement_key="marketplace.app_family.stock_ai.use",
            entitlement_value="true",
        )
    )

    price = subscription_models.SubscriptionPrice(
        product_id=product.id,
        plan_id=plan.id,
        channel="web",
        provider="stripe",
        currency="USD",
        amount_minor=1999,
        external_price_code="price_pro_monthly",
        is_active=True,
    )
    db.add(price)
    db.flush()

    now = _utcnow_naive()
    subscription = subscription_models.UserSubscription(
        user_id=user.id,
        product_id=product.id,
        plan_id=plan.id,
        price_id=price.id,
        status=SubscriptionStatus.ACTIVE.value,
        source="stripe",
        period_start=now,
        period_end=now + timedelta(days=30),
        cancel_at_period_end=False,
        created_at=now,
        updated_at=now,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return {
        "user": user,
        "product": product,
        "plan": plan,
        "price": price,
        "subscription": subscription,
    }


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _fake_rs256_token_with_kid(kid: str) -> str:
    header = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    payload = {"iss": "https://accounts.google.com", "sub": "svc"}
    return f"{_b64url(json.dumps(header, separators=(',', ':'), ensure_ascii=True).encode('utf-8'))}.{_b64url(json.dumps(payload, separators=(',', ':'), ensure_ascii=True).encode('utf-8'))}.sig"


def test_cancel_resume_persists_state_and_transitions(db_session):
    seeded = _seed_subscription(db_session)

    cancel_payload = subscription_service.cancel_subscription(
        db_session,
        user_id=int(seeded["user"].id),
        product_code=str(seeded["product"].code),
    )

    assert cancel_payload["applied"] is True
    assert cancel_payload["cancel_at_period_end"] is True
    assert cancel_payload["reason_code"] == "user_cancel_requested"

    sub_after_cancel = (
        db_session.query(subscription_models.UserSubscription)
        .filter(subscription_models.UserSubscription.id == seeded["subscription"].id)
        .first()
    )
    assert sub_after_cancel is not None
    assert bool(sub_after_cancel.cancel_at_period_end) is True
    assert sub_after_cancel.canceled_at is not None

    resume_payload = subscription_service.resume_subscription(
        db_session,
        user_id=int(seeded["user"].id),
        product_code=str(seeded["product"].code),
    )

    assert resume_payload["applied"] is True
    assert resume_payload["cancel_at_period_end"] is False
    assert resume_payload["reason_code"] == "user_resume_requested"

    sub_after_resume = (
        db_session.query(subscription_models.UserSubscription)
        .filter(subscription_models.UserSubscription.id == seeded["subscription"].id)
        .first()
    )
    assert sub_after_resume is not None
    assert bool(sub_after_resume.cancel_at_period_end) is False
    assert sub_after_resume.canceled_at is None

    payment_events = (
        db_session.query(subscription_models.PaymentEvent)
        .filter(subscription_models.PaymentEvent.subscription_id == seeded["subscription"].id)
        .order_by(subscription_models.PaymentEvent.id.asc())
        .all()
    )
    assert len(payment_events) == 2
    assert payment_events[0].event_type == "cancel_scheduled"
    assert payment_events[1].event_type == "cancel_revoked"

    transitions = (
        db_session.query(subscription_models.SubscriptionStateTransition)
        .filter(subscription_models.SubscriptionStateTransition.subscription_id == seeded["subscription"].id)
        .order_by(subscription_models.SubscriptionStateTransition.id.asc())
        .all()
    )
    assert len(transitions) == 2
    assert transitions[0].reason_code == "user_cancel_requested"
    assert transitions[1].reason_code == "user_resume_requested"


def test_register_and_revoke_device_persists_rows(db_session):
    seeded = _seed_subscription(db_session)
    user_id = int(seeded["user"].id)
    product_code = str(seeded["product"].code)

    first_register = subscription_service.register_device(
        db_session,
        user_id=user_id,
        product_code=product_code,
        device_id="ios-device-001",
        device_type="phone",
        platform="ios",
        app_version="1.0.0",
        os_version="17.4",
        last_ip="127.0.0.1",
    )
    assert first_register["registered"] is True
    assert first_register["active_device_count"] == 1

    second_register = subscription_service.register_device(
        db_session,
        user_id=user_id,
        product_code=product_code,
        device_id="ios-device-001",
        device_type="phone",
        platform="ios",
        app_version="1.0.1",
        os_version="17.5",
        last_ip="127.0.0.2",
    )
    assert second_register["registered"] is True
    assert second_register["active_device_count"] == 1

    device_rows = (
        db_session.query(subscription_models.DeviceSession)
        .filter(
            subscription_models.DeviceSession.user_id == user_id,
            subscription_models.DeviceSession.device_id == "ios-device-001",
        )
        .all()
    )
    assert len(device_rows) == 1
    assert device_rows[0].app_version == "1.0.1"
    assert device_rows[0].revoked_at is None

    revoke_payload = subscription_service.revoke_device(
        db_session,
        user_id=user_id,
        product_code=product_code,
        device_id="ios-device-001",
    )
    assert revoke_payload["revoked"] is True
    assert revoke_payload["active_device_count"] == 0

    revoked_row = (
        db_session.query(subscription_models.DeviceSession)
        .filter(
            subscription_models.DeviceSession.user_id == user_id,
            subscription_models.DeviceSession.device_id == "ios-device-001",
        )
        .first()
    )
    assert revoked_row is not None
    assert revoked_row.revoked_at is not None


def test_process_webhook_uses_adapter_signature_validation(db_session, monkeypatch):
    seeded = _seed_subscription(db_session)
    user_id = int(seeded["user"].id)

    secret = "stripe-signing-secret"
    monkeypatch.setenv("MARKETPLACE_STRIPE_WEBHOOK_SIGNING_SECRET", secret)
    webhook_payload = {
        "type": "invoice.paid",
        "amount": 1999,
    }
    raw_body = json.dumps(webhook_payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    timestamp = int(datetime.now(timezone.utc).timestamp())
    signature = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.{raw_body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    result = subscription_service.process_webhook(
        db_session,
        provider="stripe",
        payload={
            "event_id": "evt_service_1",
            "event_type": "invoice.paid",
            "user_id": user_id,
            "product_code": "stock-ai-suite",
            "plan_code": "pro",
            "external_subscription_id": "sub_123",
            "payload": {
                **webhook_payload,
                "raw_body": raw_body,
                "stripe_signature": f"t={timestamp},v1={signature}",
            },
        },
    )

    assert result["processed"] is True
    assert result["provider"] == "stripe"
    assert result["subscription_status"] == "active"

    payment_event = (
        db_session.query(subscription_models.PaymentEvent)
        .filter(subscription_models.PaymentEvent.provider == "stripe")
        .filter(subscription_models.PaymentEvent.event_id == "evt_service_1")
        .first()
    )
    assert payment_event is not None
    assert payment_event.signature_valid is True
    assert payment_event.event_type == "renewal_succeeded"


def test_process_webhook_rejects_invalid_signature(db_session, monkeypatch):
    _seed_subscription(db_session)
    monkeypatch.setenv("MARKETPLACE_STRIPE_WEBHOOK_SIGNING_SECRET", "stripe-signing-secret")

    with pytest.raises(HTTPException) as exc_info:
        subscription_service.process_webhook(
            db_session,
            provider="stripe",
            payload={
                "event_id": "evt_service_bad_sig",
                "event_type": "invoice.paid",
                "user_id": 1,
                "product_code": "stock-ai-suite",
                "plan_code": "pro",
                "payload": {
                    "type": "invoice.paid",
                    "signature": "invalid-signature",
                },
            },
        )

    assert exc_info.value.status_code == 401
    assert "signature" in str(exc_info.value.detail).lower()

    attempt = (
        db_session.query(subscription_models.WebhookDeliveryAttempt)
        .filter(subscription_models.WebhookDeliveryAttempt.event_id == "evt_service_bad_sig")
        .first()
    )
    assert attempt is not None
    assert attempt.http_status == 401
    assert attempt.result == "retry_scheduled"


def test_process_webhook_signature_failure_retries_then_dead_letter(db_session, monkeypatch):
    _seed_subscription(db_session)
    monkeypatch.setenv("MARKETPLACE_STRIPE_WEBHOOK_SIGNING_SECRET", "stripe-signing-secret")

    for _ in range(3):
        with pytest.raises(HTTPException) as exc_info:
            subscription_service.process_webhook(
                db_session,
                provider="stripe",
                payload={
                    "event_id": "evt_service_retry_dead",
                    "event_type": "invoice.paid",
                    "user_id": 1,
                    "product_code": "stock-ai-suite",
                    "plan_code": "pro",
                    "payload": {
                        "type": "invoice.paid",
                        "stripe_signature": "t=1714286400,v1=invalid",
                        "raw_body": '{"type":"invoice.paid"}',
                    },
                },
            )
        assert exc_info.value.status_code == 401

    attempts = (
        db_session.query(subscription_models.WebhookDeliveryAttempt)
        .filter(subscription_models.WebhookDeliveryAttempt.event_id == "evt_service_retry_dead")
        .order_by(subscription_models.WebhookDeliveryAttempt.attempt_number.asc())
        .all()
    )
    assert len(attempts) == 3
    assert [row.attempt_number for row in attempts] == [1, 2, 3]
    assert attempts[0].result == "retry_scheduled"
    assert attempts[1].result == "retry_scheduled"
    assert attempts[2].result == "dead_letter"
    assert "retry_in_seconds=30" in str(attempts[0].error_message)
    assert "retry_in_seconds=120" in str(attempts[1].error_message)
    assert "dead_letter=true" in str(attempts[2].error_message)


def test_process_webhook_apple_pinset_file_missing_returns_400(db_session, monkeypatch):
    seeded = _seed_subscription(db_session)
    user_id = int(seeded["user"].id)
    monkeypatch.delenv("MARKETPLACE_APPLE_WEBHOOK_SIGNING_SECRET", raising=False)
    monkeypatch.setenv("MARKETPLACE_APPLE_WEBHOOK_ENABLE_X5C_VERIFY", "true")
    monkeypatch.setenv("MARKETPLACE_APPLE_ROOT_CA_PEM_FILE", "C:/__missing__/apple_root_ca.pem")

    with pytest.raises(HTTPException) as exc_info:
        subscription_service.process_webhook(
            db_session,
            provider="apple",
            payload={
                "event_id": "evt_apple_missing_pinset_file",
                "event_type": "did_renew",
                "user_id": user_id,
                "product_code": "stock-ai-suite",
                "plan_code": "pro",
                "payload": {
                    "signedPayload": "x.y.z",
                },
            },
        )

    assert exc_info.value.status_code == 400
    assert "root ca" in str(exc_info.value.detail).lower()


def test_process_webhook_google_oidc_missing_audience_returns_503_in_production(db_session, monkeypatch):
    seeded = _seed_subscription(db_session)
    user_id = int(seeded["user"].id)
    token = _fake_rs256_token_with_kid("svc-kid-1")

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MARKETPLACE_GOOGLE_WEBHOOK_ENABLE_OIDC_VERIFY", "true")
    monkeypatch.delenv("MARKETPLACE_GOOGLE_PUBSUB_AUDIENCE", raising=False)
    monkeypatch.setenv("MARKETPLACE_GOOGLE_PUBSUB_ISSUER", "https://accounts.google.com")
    monkeypatch.setattr(
        "backend.marketplace.provider_adapters.google_billing.GoogleBillingAdapter._fetch_google_jwks",
        classmethod(
            lambda cls, url: {
                "keys": [
                    {
                        "kty": "RSA",
                        "kid": "svc-kid-1",
                        "use": "sig",
                        "alg": "RS256",
                        "n": "AQAB",
                        "e": "AQAB",
                    }
                ]
            }
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        subscription_service.process_webhook(
            db_session,
            provider="google",
            payload={
                "event_id": "evt_google_prod_missing_aud",
                "event_type": "renewal_succeeded",
                "user_id": user_id,
                "product_code": "stock-ai-suite",
                "plan_code": "pro",
                "payload": {
                    "oidc_token": token,
                },
            },
        )

    assert exc_info.value.status_code == 503
    assert "audience" in str(exc_info.value.detail).lower()


def test_list_subscription_catalog_seeds_default_service_groups(db_session):
    seeded = _seed_subscription(db_session)
    catalog = subscription_service.list_subscription_catalog(db_session, user_id=int(seeded["user"].id))

    assert isinstance(catalog, list)
    assert len(catalog) >= 7

    by_code = {str(item["product_code"]): item for item in catalog}
    assert "stock-ai-suite" in by_code
    assert "ai-powerpoint-suite" in by_code
    assert "ai-image-suite" in by_code

    stock = by_code["stock-ai-suite"]
    assert stock["active_plan"] is not None
    assert stock["active_plan"]["provider"] == "stripe"
    assert stock["active_plan"]["billing_period"] == "monthly"