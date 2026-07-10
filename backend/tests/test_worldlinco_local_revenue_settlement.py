"""Tests for WorldLinco local-currency full local revenue settlement."""

from backend.marketplace import worldlinco_sales_commission as sc
from backend.marketplace.worldlinco_sales_commission import (
    COMMISSION_LEDGER_ONLY_STATUS,
    LocalRevenueSettlementPolicyUpdate,
    OfficeBankAccountUpdate,
    SalesAgentCreate,
    SalesCommissionPolicyUpdate,
)


def test_local_revenue_full_payout_thailand(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")

    sc.upsert_office_bank_account(
        OfficeBankAccountUpdate(
            country_code="TH",
            region_code="TH",
            office_name="Bangkok Office",
            bank_name="Bangkok Bank",
            account_number="1234567890",
            account_holder="WorldLinco Thailand",
            currency="THB",
        ),
        updated_by="admin@test",
    )
    agent = sc.create_sales_agent(SalesAgentCreate(name="TH Sales", country_code="TH", region_code="TH"))
    sc.record_sales_agent_signup(
        sales_agent_code=agent["code"],
        user_id=501,
        username="th_user",
        email="th@example.com",
        user_country_code="TH",
    )

    result = sc.record_worldlinco_payment_settlements(
        user_id=501,
        payment_amount_minor=29900,
        currency="THB",
        user_country_code="TH",
        provider="google",
        transaction_id="th-txn-1",
        plan_key="voip_lite",
    )
    commission = result["commission_event"]
    revenue = result["local_revenue_event"]

    assert commission is not None
    assert commission["settlement_status"] == COMMISSION_LEDGER_ONLY_STATUS
    assert commission["commission_amount_minor"] == 8970

    assert revenue is not None
    assert revenue["revenue_amount_minor"] == 29900
    assert revenue["currency"] == "THB"
    assert revenue["country_code"] == "TH"
    assert revenue["settlement_status"] == "paid_out"
    assert revenue.get("transfer_reference")

    dashboard = sc.admin_sales_commission_dashboard_payload()
    assert dashboard["stats"]["paid_out_local_revenue_minor"] == 29900
    assert dashboard["stats"]["paid_out_commission_minor"] == 0
    assert len(dashboard["recent_local_revenue_payouts"]) >= 1
    assert dashboard["recent_local_revenue_payouts"][0]["currency"] == "THB"


def test_local_revenue_routes_by_user_country_without_sales_attribution(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    sc.upsert_office_bank_account(
        OfficeBankAccountUpdate(
            country_code="JP",
            bank_name="MUFG",
            account_number="111122223333",
            account_holder="WorldLinco Japan",
            currency="JPY",
        ),
        updated_by="admin@test",
    )

    revenue = sc.record_local_revenue_on_payment(
        user_id=777,
        payment_amount_minor=120000,
        currency="JPY",
        user_country_code="JP",
        provider="apple",
        transaction_id="jp-direct-1",
    )
    assert revenue is not None
    assert revenue["country_code"] == "JP"
    assert revenue["currency"] == "JPY"
    assert revenue["settlement_status"] == "paid_out"


def test_local_revenue_falls_back_to_kr_hq_when_local_bank_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    sc.upsert_office_bank_account(
        OfficeBankAccountUpdate(
            country_code="KR",
            region_code="KR",
            bank_name="KB국민은행",
            account_number="123456789012",
            account_holder="WorldLinco HQ",
            currency="KRW",
        ),
        updated_by="admin@test",
    )

    revenue = sc.record_local_revenue_on_payment(
        user_id=888,
        payment_amount_minor=150000,
        currency="VND",
        user_country_code="VN",
        provider="google",
        transaction_id="vn-fallback-1",
    )
    assert revenue is not None
    assert revenue["country_code"] == "VN"
    assert revenue["currency"] == "VND"
    assert revenue["settlement_status"] == "paid_out"
    assert revenue.get("hq_fallback") is True
    assert revenue.get("payout_bank_country_code") == "KR"

    dashboard = sc.admin_sales_commission_dashboard_payload()
    payout = dashboard["recent_local_revenue_payouts"][0]
    assert payout.get("hq_fallback") is True
    assert payout.get("payout_bank_country_code") == "KR"
    assert payout.get("country_code") == "VN"


def test_local_revenue_prefers_local_bank_over_hq_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    sc.upsert_office_bank_account(
        OfficeBankAccountUpdate(
            country_code="KR",
            region_code="KR",
            bank_name="KB국민은행",
            account_number="123456789012",
            account_holder="WorldLinco HQ",
            currency="KRW",
        ),
        updated_by="admin@test",
    )
    sc.upsert_office_bank_account(
        OfficeBankAccountUpdate(
            country_code="TH",
            region_code="TH",
            bank_name="Bangkok Bank",
            account_number="9988776655",
            account_holder="WorldLinco Thailand",
            currency="THB",
        ),
        updated_by="admin@test",
    )

    revenue = sc.record_local_revenue_on_payment(
        user_id=889,
        payment_amount_minor=29900,
        currency="THB",
        user_country_code="TH",
        provider="google",
        transaction_id="th-local-1",
    )
    assert revenue is not None
    assert revenue.get("hq_fallback") is not True
    assert revenue.get("payout_bank_country_code") in {None, "TH"}


def test_local_revenue_awaiting_when_no_local_and_no_hq_bank(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    revenue = sc.record_local_revenue_on_payment(
        user_id=890,
        payment_amount_minor=9900,
        currency="USD",
        user_country_code="US",
        provider="apple",
        transaction_id="us-no-bank-1",
    )
    assert revenue is not None
    assert revenue["settlement_status"] == "awaiting_bank_account"


def test_commission_only_mode_when_local_revenue_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    sc.apply_local_revenue_settlement_policy_update(
        LocalRevenueSettlementPolicyUpdate(enabled=False),
        updated_by="admin@test",
    )
    sc.upsert_office_bank_account(
        OfficeBankAccountUpdate(
            country_code="KR",
            region_code="KR",
            bank_name="KB국민은행",
            account_number="123456789012",
            account_holder="WorldLinco Korea",
            currency="KRW",
        ),
        updated_by="admin@test",
    )
    agent = sc.create_sales_agent(SalesAgentCreate(name="KR Sales", country_code="KR"))
    sc.record_sales_agent_signup(
        sales_agent_code=agent["code"],
        user_id=601,
        username="kr_user",
        email="kr@example.com",
    )
    event = sc.record_sales_commission_on_payment(
        user_id=601,
        payment_amount_minor=9900,
        provider="google",
        transaction_id="kr-only-commission",
    )
    assert event is not None
    assert event["settlement_status"] == "paid_out"

    revenue = sc.record_local_revenue_on_payment(
        user_id=601,
        payment_amount_minor=9900,
        currency="KRW",
        user_country_code="KR",
        provider="google",
        transaction_id="kr-only-commission",
    )
    assert revenue is None
