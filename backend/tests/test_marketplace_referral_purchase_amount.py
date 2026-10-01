"""Referral checkout must keep the discounted price in KRW won.

Project prices and referral quotes are whole won (`amount_minor` 9900 == ₩9,900).
Dividing the eligible quote by 100 stored the first referred purchase at ~1% of
the real price and then confirmed that amount.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

from backend.marketplace import worldlinco_referral as wr
from backend.marketplace.router import PurchaseCreateRequest, create_marketplace_purchase
from backend.marketplace.worldlinco_referral import ReferralDiscountPolicyUpdate


class _EmptyQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class _EmptyDB:
    """No prior purchases or payment events, so the first-payment discount applies."""

    def query(self, *args, **kwargs):
        return _EmptyQuery()


def _enable_referral(tmp_path, monkeypatch, *, referrer_id: int, buyer_id: int) -> None:
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    wr.apply_referral_discount_policy_update(ReferralDiscountPolicyUpdate(enabled=True, percent=3.0))
    code = wr.ensure_user_referral_code(user_id=referrer_id, username="referrer")
    wr.record_referral_signup(
        referral_code=code,
        referred_user_id=buyer_id,
        referred_username="buyer",
        referred_email="buyer@example.com",
    )


def _capture_purchase(monkeypatch, *, price: float):
    import backend.marketplace.router as router_mod

    monkeypatch.setattr(
        router_mod.crud,
        "get_project",
        lambda db, project_id: SimpleNamespace(id=project_id, price=price),
    )
    captured: dict[str, float] = {}

    def _create_purchase(db, project_id, buyer_id, amount, payment_method="card"):
        captured["amount"] = float(amount)
        return SimpleNamespace(
            id=7,
            project_id=project_id,
            buyer_id=buyer_id,
            amount=float(amount),
            status="pending",
            payment_method=payment_method,
            transaction_id=None,
            receipt_url=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

    monkeypatch.setattr(router_mod.payment_service, "create_purchase", _create_purchase)
    return captured


def test_referred_purchase_keeps_discounted_krw_won(tmp_path, monkeypatch):
    _enable_referral(tmp_path, monkeypatch, referrer_id=10, buyer_id=20)
    captured = _capture_purchase(monkeypatch, price=189000.0)

    response = create_marketplace_purchase(
        PurchaseCreateRequest(project_id=1, amount=1.0, payment_method="card"),
        current_user=SimpleNamespace(id=20),
        db=_EmptyDB(),
    )

    assert captured["amount"] == 183330.0
    assert response["amount"] == 183330.0
    assert response["referral_discount"]["final_amount_minor"] == 183330


def test_unreferred_purchase_keeps_catalog_price(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    wr.apply_referral_discount_policy_update(ReferralDiscountPolicyUpdate(enabled=True, percent=3.0))
    captured = _capture_purchase(monkeypatch, price=189000.0)

    response = create_marketplace_purchase(
        PurchaseCreateRequest(project_id=1, amount=1.0, payment_method="card"),
        current_user=SimpleNamespace(id=99),
        db=_EmptyDB(),
    )

    assert captured["amount"] == 189000.0
    assert response["amount"] == 189000.0
    assert "referral_discount" not in response
