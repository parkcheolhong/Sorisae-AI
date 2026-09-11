"""Unauthenticated marketplace payment callback must not complete purchases."""

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.marketplace.router as marketplace_router_module
from backend.auth import get_current_user


class _FakeDb:
    pass


def _build_client(*, user: SimpleNamespace | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(marketplace_router_module.router, prefix="/api/marketplace")
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[marketplace_router_module.get_db] = lambda: _FakeDb()
    return TestClient(app)


def _pending_purchase(*, purchase_id: int = 42, buyer_id: int = 11) -> SimpleNamespace:
    return SimpleNamespace(
        id=purchase_id,
        buyer_id=buyer_id,
        amount=9900.0,
        status="pending",
        transaction_id=None,
    )


def _patch_payment(monkeypatch, purchase: SimpleNamespace):
    calls: list[dict] = []

    def _get_purchase(_db, purchase_id: int):
        if int(purchase_id) != int(purchase.id):
            return None
        return purchase

    def _finalize(*, db, purchase, buyer_id, transaction_id, user_country_code=None):
        calls.append(
            {
                "buyer_id": int(buyer_id),
                "transaction_id": str(transaction_id),
                "user_country_code": user_country_code,
            }
        )
        purchase.status = "completed"
        purchase.transaction_id = str(transaction_id)
        return {
            "purchase": purchase,
            "settlement": {"applied": True},
            "payment_mode": "simulated",
            "payment_provider": "marketplace_legacy",
            "payment_simulation": True,
            "payment_message": "결제가 확정되었습니다.",
        }

    monkeypatch.setattr(
        marketplace_router_module.payment_service,
        "get_purchase_by_id",
        _get_purchase,
    )
    monkeypatch.setattr(
        marketplace_router_module,
        "_finalize_confirmed_marketplace_purchase",
        _finalize,
    )
    return calls


def test_payment_callback_rejects_unauthenticated_completion(monkeypatch):
    purchase = _pending_purchase()
    calls = _patch_payment(monkeypatch, purchase)
    client = _build_client()

    response = client.post(
        "/api/marketplace/payment/callback",
        params={"order_id": purchase.id, "transaction_id": "TXN_attacker"},
    )

    assert response.status_code == 401
    assert calls == []
    assert purchase.status == "pending"
    assert purchase.transaction_id is None


def test_payment_callback_rejects_other_buyers_purchase(monkeypatch):
    purchase = _pending_purchase(buyer_id=99)
    calls = _patch_payment(monkeypatch, purchase)
    client = _build_client(user=SimpleNamespace(id=11, email="buyer@example.com"))

    response = client.post(
        "/api/marketplace/payment/callback",
        params={"order_id": purchase.id, "transaction_id": "TXN_other"},
    )

    assert response.status_code == 403
    assert calls == []
    assert purchase.status == "pending"


def test_payment_callback_allows_authenticated_owner(monkeypatch):
    purchase = _pending_purchase(buyer_id=11)
    calls = _patch_payment(monkeypatch, purchase)
    client = _build_client(
        user=SimpleNamespace(id=11, email="buyer@example.com", country_code="KR")
    )

    response = client.post(
        "/api/marketplace/payment/callback",
        params={"order_id": purchase.id, "transaction_id": "TXN_owner12"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["purchase_id"] == 42
    assert payload["transaction_id"] == "TXN_owner12"
    assert calls == [
        {
            "buyer_id": 11,
            "transaction_id": "TXN_owner12",
            "user_country_code": "KR",
        }
    ]
