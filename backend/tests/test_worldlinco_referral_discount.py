"""Tests for WorldLinco referral first-payment discount policy."""

from backend.marketplace import worldlinco_referral as wr
from backend.marketplace.worldlinco_referral import ReferralDiscountPolicyUpdate


def test_discount_policy_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    policy = wr.load_referral_discount_policy()
    assert policy["enabled"] is False
    assert policy["percent"] == 3.0


def test_discount_quote_eligible_for_referred_user(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    wr.apply_referral_discount_policy_update(ReferralDiscountPolicyUpdate(enabled=True, percent=3.0))
    code = wr.ensure_user_referral_code(user_id=10, username="referrer")
    wr.record_referral_signup(
        referral_code=code,
        referred_user_id=20,
        referred_username="guest",
        referred_email="guest@example.com",
    )
    quote = wr.resolve_referral_discount_quote(user_id=20, amount_minor=9900)
    assert quote["eligible"] is True
    assert quote["discount_amount_minor"] == 297
    assert quote["final_amount_minor"] == 9603


def test_discount_apply_once(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    wr.apply_referral_discount_policy_update(ReferralDiscountPolicyUpdate(enabled=True, percent=3.0))
    code = wr.ensure_user_referral_code(user_id=11, username="host")
    wr.record_referral_signup(
        referral_code=code,
        referred_user_id=21,
        referred_username="buyer",
        referred_email="buyer@example.com",
    )
    applied = wr.apply_referral_discount_payment(
        user_id=21,
        provider="google",
        original_amount_minor=9900,
        final_amount_minor=9603,
        plan_key="voip_lite",
        transaction_id="txn-1",
        external_offer_id="referral-first-payment-3pct",
    )
    assert applied is not None
    assert applied["first_payment_provider"] == "google"
    quote = wr.resolve_referral_discount_quote(user_id=21, amount_minor=9900)
    assert quote["eligible"] is False
    assert quote["reason"] == "already_applied"


def test_admin_dashboard_includes_discount_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    wr.apply_referral_discount_policy_update(ReferralDiscountPolicyUpdate(enabled=True, percent=3.0))
    admin = wr.admin_referral_dashboard_payload()
    assert admin["discount_policy"]["enabled"] is True
    assert "discount_applied_count" in admin["discount_stats"]


def test_sales_agent_signup_excluded_from_referral_discount(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    from backend.marketplace import worldlinco_sales_commission as sc
    from backend.marketplace.worldlinco_sales_commission import SalesAgentCreate

    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    wr.apply_referral_discount_policy_update(ReferralDiscountPolicyUpdate(enabled=True, percent=3.0))
    referrer_code = wr.ensure_user_referral_code(user_id=30, username="friend")
    wr.record_referral_signup(
        referral_code=referrer_code,
        referred_user_id=40,
        referred_username="buyer",
        referred_email="buyer@example.com",
    )
    agent = sc.create_sales_agent(SalesAgentCreate(name="Sales", country_code="KR"))
    sc.record_sales_agent_signup(
        sales_agent_code=agent["code"],
        user_id=40,
        username="buyer",
        email="buyer@example.com",
    )
    quote = wr.resolve_referral_discount_quote(user_id=40, amount_minor=9900)
    assert quote["eligible"] is False
    assert quote["reason"] == "sales_agent_signup_excluded"


def test_split_signup_codes_routes_ws_away_from_referral():
    referral, sales = wr.split_signup_attribution_codes("WSABC123", None)
    assert referral is None
    assert sales == "WSABC123"

    referral, sales = wr.split_signup_attribution_codes("WL10ABC", "WSXYZ999")
    assert referral == "WL10ABC"
    assert sales == "WSXYZ999"
