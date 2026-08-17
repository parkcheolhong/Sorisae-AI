from types import SimpleNamespace

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

import backend.marketplace.router as marketplace_router_module
from backend.auth import get_current_user


class _FakeDb:
    pass


def _build_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(marketplace_router_module.router, prefix="/api/marketplace")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7, email="customer@example.com")
    app.dependency_overrides[marketplace_router_module.get_db] = lambda: _FakeDb()
    return TestClient(app)


def test_get_subscription_catalog_returns_service_payload(monkeypatch):
    client = _build_test_client()

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "list_subscription_catalog",
        lambda db, user_id: [
            {
                "product_code": "stock-ai-suite",
                "product_name": "Stock AI Suite",
                "product_description": "주식 AI 분석/리포트 기능군 월정액",
                "product_family": "stock-ai",
                "subscription_status": "none",
                "cancel_at_period_end": False,
                "period_end": None,
                "active_plan": {
                    "plan_code": "stock-ai-monthly",
                    "plan_name": "Monthly",
                    "billing_period": "monthly",
                    "provider": "stripe",
                    "currency": "KRW",
                    "amount_minor": 39000,
                },
                "entitlement_set": ["marketplace.app_family.stock_ai.use"],
            }
        ],
    )

    response = client.get("/api/marketplace/v1/subscription/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload[0]["product_code"] == "stock-ai-suite"
    assert payload[0]["active_plan"]["provider"] == "stripe"


def test_get_my_subscription_returns_service_payload(monkeypatch):
    client = _build_test_client()

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "get_user_subscription_status",
        lambda db, user_id, product_code=None: {
            "user_id": user_id,
            "subscription_status": "active",
            "product_code": product_code or "stock-ai-suite",
            "plan_code": "pro",
            "entitlement_set": ["marketplace.app_family.stock_ai.use"],
            "period_end": None,
            "cancel_at_period_end": False,
            "device_limit": 2,
            "active_device_count": 1,
            "source": "apple",
        },
    )

    response = client.get("/api/marketplace/v1/me/subscription?product_code=stock-ai-suite")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == 7
    assert payload["subscription_status"] == "active"
    assert payload["product_code"] == "stock-ai-suite"
    assert payload["plan_code"] == "pro"


def test_mobile_verify_returns_service_payload(monkeypatch):
    client = _build_test_client()

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "verify_mobile_subscription",
        lambda db, **kwargs: {
            "user_id": kwargs["user_id"],
            "subscription_status": "active",
            "product_code": kwargs["product_code"],
            "plan_code": kwargs["plan_code"],
            "entitlement_set": ["marketplace.app_family.stock_ai.use"],
            "period_end": None,
            "cancel_at_period_end": False,
            "device_limit": 2,
            "active_device_count": 1,
            "source": "google",
            "verified": True,
            "source_original_id": "txn-123",
            "verification_mode": "simulation",
            "verification_simulated": True,
        },
    )

    response = client.post(
        "/api/marketplace/v1/billing/mobile/verify",
        json={
            "platform": "android",
            "product_code": "stock-ai-suite",
            "plan_code": "pro",
            "purchase_token_or_receipt": "receipt-token",
            "transaction_id": "txn-123",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == 7
    assert payload["verified"] is True
    assert payload["verification_mode"] == "simulation"
    assert payload["product_code"] == "stock-ai-suite"


def test_checkout_session_returns_service_payload(monkeypatch):
    client = _build_test_client()

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "create_checkout_session",
        lambda db, **kwargs: {
            "provider": kwargs["provider"],
            "checkout_url": "https://billing.example.com/stripe/checkout?session_id=cs_test_123",
            "session_id": "cs_test_123",
            "expires_in": 1800,
            "verification_mode": "simulation",
            "verification_simulated": True,
        },
    )

    response = client.post(
        "/api/marketplace/v1/billing/checkout/sessions",
        json={
            "provider": "stripe",
            "product_code": "stock-ai-suite",
            "plan_code": "pro",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "stripe"
    assert payload["session_id"] == "cs_test_123"
    assert payload["verification_mode"] == "simulation"


def test_cancel_subscription_returns_service_payload(monkeypatch):
    client = _build_test_client()

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "cancel_subscription",
        lambda db, **kwargs: {
            "user_id": kwargs["user_id"],
            "subscription_status": "active",
            "product_code": kwargs["product_code"] or "stock-ai-suite",
            "plan_code": "pro",
            "entitlement_set": ["marketplace.app_family.stock_ai.use"],
            "period_end": None,
            "cancel_at_period_end": True,
            "device_limit": 2,
            "active_device_count": 1,
            "source": "stripe",
            "applied": True,
            "ignored": False,
            "reason_code": "user_cancel_requested",
        },
    )

    response = client.post(
        "/api/marketplace/v1/me/subscription/cancel",
        json={"product_code": "stock-ai-suite"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["applied"] is True
    assert payload["cancel_at_period_end"] is True
    assert payload["reason_code"] == "user_cancel_requested"


def test_resume_subscription_returns_service_payload(monkeypatch):
    client = _build_test_client()

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "resume_subscription",
        lambda db, **kwargs: {
            "user_id": kwargs["user_id"],
            "subscription_status": "active",
            "product_code": kwargs["product_code"] or "stock-ai-suite",
            "plan_code": "pro",
            "entitlement_set": ["marketplace.app_family.stock_ai.use"],
            "period_end": None,
            "cancel_at_period_end": False,
            "device_limit": 2,
            "active_device_count": 1,
            "source": "stripe",
            "applied": True,
            "ignored": False,
            "reason_code": "user_resume_requested",
        },
    )

    response = client.post(
        "/api/marketplace/v1/me/subscription/resume",
        json={"product_code": "stock-ai-suite"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["applied"] is True
    assert payload["cancel_at_period_end"] is False
    assert payload["reason_code"] == "user_resume_requested"


def test_register_device_returns_service_payload(monkeypatch):
    client = _build_test_client()

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "register_device",
        lambda db, **kwargs: {
            "user_id": kwargs["user_id"],
            "subscription_status": "active",
            "product_code": kwargs["product_code"] or "stock-ai-suite",
            "plan_code": "pro",
            "entitlement_set": ["marketplace.app_family.stock_ai.use"],
            "period_end": None,
            "cancel_at_period_end": False,
            "device_limit": 2,
            "active_device_count": 2,
            "source": "apple",
            "registered": True,
            "device_id": kwargs["device_id"],
            "device_revoked": False,
        },
    )

    response = client.post(
        "/api/marketplace/v1/me/devices/register",
        json={
            "product_code": "stock-ai-suite",
            "device_id": "ios-device-1",
            "device_type": "phone",
            "platform": "ios",
            "app_version": "1.0.0",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["registered"] is True
    assert payload["device_id"] == "ios-device-1"
    assert payload["active_device_count"] == 2


def test_revoke_device_returns_service_payload(monkeypatch):
    client = _build_test_client()

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "revoke_device",
        lambda db, **kwargs: {
            "user_id": kwargs["user_id"],
            "subscription_status": "active",
            "product_code": kwargs["product_code"] or "stock-ai-suite",
            "plan_code": "pro",
            "entitlement_set": ["marketplace.app_family.stock_ai.use"],
            "period_end": None,
            "cancel_at_period_end": False,
            "device_limit": 2,
            "active_device_count": 1,
            "source": "apple",
            "revoked": True,
            "device_id": kwargs["device_id"],
        },
    )

    response = client.post(
        "/api/marketplace/v1/me/devices/revoke",
        json={
            "product_code": "stock-ai-suite",
            "device_id": "ios-device-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["revoked"] is True
    assert payload["device_id"] == "ios-device-1"


def test_webhook_returns_service_payload(monkeypatch):
    client = _build_test_client()

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "process_webhook",
        lambda db, **kwargs: {
            "provider": kwargs["provider"],
            "event_id": kwargs["payload"]["event_id"],
            "processed": True,
            "ignored": False,
            "reason_code": "renewal_succeeded",
            "subscription_status": "active",
            "delivery_attempt_id": 11,
        },
    )

    response = client.post(
        "/api/marketplace/v1/billing/webhooks/stripe",
        json={
            "event_id": "evt_123",
            "event_type": "invoice.paid",
            "user_id": 7,
            "product_code": "stock-ai-suite",
            "plan_code": "pro",
            "payload": {"object": "event"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "stripe"
    assert payload["event_id"] == "evt_123"
    assert payload["processed"] is True
    assert payload["delivery_attempt_id"] == 11


def test_webhook_propagates_apple_pinset_guard_failure(monkeypatch):
    client = _build_test_client()

    def _raise_pinset_guard(db, **kwargs):
        raise HTTPException(status_code=400, detail="Apple root CA 파일을 찾을 수 없습니다")

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "process_webhook",
        _raise_pinset_guard,
    )

    response = client.post(
        "/api/marketplace/v1/billing/webhooks/apple",
        json={
            "event_id": "evt_apple_missing_pinset_file",
            "event_type": "did_renew",
            "payload": {"signedPayload": "x.y.z"},
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert "root ca" in str(payload.get("detail", "")).lower()


def test_webhook_propagates_google_oidc_production_guard_failure(monkeypatch):
    client = _build_test_client()

    def _raise_google_oidc_guard(db, **kwargs):
        raise HTTPException(
            status_code=503,
            detail="운영 환경에서는 MARKETPLACE_GOOGLE_PUBSUB_AUDIENCE 값을 필수로 설정해야 합니다.",
        )

    monkeypatch.setattr(
        marketplace_router_module.subscription_service,
        "process_webhook",
        _raise_google_oidc_guard,
    )

    response = client.post(
        "/api/marketplace/v1/billing/webhooks/google",
        json={
            "event_id": "evt_google_prod_missing_aud",
            "event_type": "renewal_succeeded",
            "payload": {"oidc_token": "header.payload.signature"},
        },
    )

    assert response.status_code == 503
    payload = response.json()
    assert "audience" in str(payload.get("detail", "")).lower()