"""Tests for WorldLinco regional sales commission auto bank settlement."""

from backend.marketplace import worldlinco_sales_commission as sc
from backend.marketplace.worldlinco_sales_commission import (
    COMMISSION_LEDGER_ONLY_STATUS,
    OfficeBankAccountUpdate,
    SalesAgentCreate,
    SalesCommissionPolicyUpdate,
    LocalRevenueSettlementPolicyUpdate,
)


def test_commission_policy_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    policy = sc.load_sales_commission_policy()
    assert policy["enabled"] is True
    assert policy["initial_sale_percent"] == 30.0
    assert policy["recurring_user_fee_percent"] == 10.0
    assert policy["settlement_mode"] == "auto_bank_transfer"
    assert policy["approval_required"] is False
    assert policy["auto_settle_on_accrual"] is True


def test_sales_agent_signup_awaiting_bank_without_account(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    agent = sc.create_sales_agent(SalesAgentCreate(name="Kim Sales", country_code="KR", office_name="Seoul HQ"))
    code = agent["code"]
    assert code.startswith("WS")

    sc.record_sales_agent_signup(
        sales_agent_code=code,
        user_id=100,
        username="buyer1",
        email="buyer1@example.com",
        user_country_code="KR",
    )
    event = sc.record_sales_commission_on_payment(
        user_id=100,
        payment_amount_minor=9900,
        provider="google",
        transaction_id="txn-sales-1",
        plan_key="voip_lite",
    )
    assert event is not None
    assert event["commission_type"] == "initial_sale"
    assert event["commission_amount_minor"] == 2970
    assert event["settlement_status"] == COMMISSION_LEDGER_ONLY_STATUS

    revenue = sc.record_local_revenue_on_payment(
        user_id=100,
        payment_amount_minor=9900,
        currency="KRW",
        user_country_code="KR",
        provider="google",
        transaction_id="txn-sales-1",
    )
    assert revenue is not None
    assert revenue["settlement_status"] == "awaiting_bank_account"


def test_auto_payout_to_office_bank_account(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    sc.upsert_office_bank_account(
        OfficeBankAccountUpdate(
            country_code="KR",
            region_code="KR",
            office_name="Seoul HQ",
            bank_name="KB국민은행",
            account_number="123456789012",
            account_holder="WorldLinco Korea",
        ),
        updated_by="admin@test",
    )
    agent = sc.create_sales_agent(SalesAgentCreate(name="Kim Sales", country_code="KR", office_name="Seoul HQ"))
    sc.record_sales_agent_signup(
        sales_agent_code=agent["code"],
        user_id=101,
        username="buyer2",
        email="buyer2@example.com",
    )
    event = sc.record_worldlinco_payment_settlements(
        user_id=101,
        payment_amount_minor=9900,
        currency="KRW",
        user_country_code="KR",
        provider="google",
        transaction_id="txn-auto-1",
    )["commission_event"]
    assert event is not None
    assert event["settlement_status"] == COMMISSION_LEDGER_ONLY_STATUS
    assert event.get("transfer_reference") is None

    dashboard = sc.admin_sales_commission_dashboard_payload()
    assert dashboard["stats"]["paid_out_commission_minor"] == 0
    assert dashboard["stats"]["paid_out_local_revenue_minor"] == 9900
    assert len(dashboard["recent_local_revenue_payouts"]) >= 1


def test_recurring_commission_after_initial(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    sc.upsert_office_bank_account(
        OfficeBankAccountUpdate(
            country_code="JP",
            bank_name="MUFG",
            account_number="9988776655",
            account_holder="WorldLinco Japan",
        ),
        updated_by="admin@test",
    )
    agent = sc.create_sales_agent(SalesAgentCreate(name="Lee Sales", country_code="JP"))
    sc.record_sales_agent_signup(
        sales_agent_code=agent["code"],
        user_id=102,
        username="buyer3",
        email="buyer3@example.com",
    )
    sc.record_worldlinco_payment_settlements(
        user_id=102,
        payment_amount_minor=9900,
        currency="JPY",
        user_country_code="JP",
        provider="card",
        transaction_id="txn-initial",
    )
    recurring = sc.record_worldlinco_payment_settlements(
        user_id=102,
        payment_amount_minor=9900,
        currency="JPY",
        user_country_code="JP",
        provider="card",
        transaction_id="txn-recurring",
    )["commission_event"]
    assert recurring is not None
    assert recurring["commission_type"] == "recurring_user_fee"
    assert recurring["percent"] == 10.0
    assert recurring["commission_amount_minor"] == 990
    assert recurring["settlement_status"] == COMMISSION_LEDGER_ONLY_STATUS

    dashboard = sc.admin_sales_commission_dashboard_payload()
    assert dashboard["stats"]["paid_out_local_revenue_minor"] == 9900 * 2


def test_run_auto_settlement_all(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    sc.apply_local_revenue_settlement_policy_update(
        LocalRevenueSettlementPolicyUpdate(enabled=False),
        updated_by="admin@test",
    )
    sc.apply_sales_commission_policy_update(
        SalesCommissionPolicyUpdate(auto_settle_on_accrual=False),
        updated_by="admin@test",
    )
    sc.upsert_office_bank_account(
        OfficeBankAccountUpdate(
            country_code="US",
            bank_name="Chase",
            account_number="555566667777",
            account_holder="WorldLinco US",
        ),
        updated_by="admin@test",
    )
    agent = sc.create_sales_agent(SalesAgentCreate(name="Park Sales", country_code="US"))
    sc.record_sales_agent_signup(
        sales_agent_code=agent["code"],
        user_id=103,
        username="buyer4",
        email="buyer4@example.com",
    )
    event = sc.record_sales_commission_on_payment(
        user_id=103,
        payment_amount_minor=10000,
        provider="apple",
        transaction_id="txn-us-1",
    )
    assert event["settlement_status"] == "pending"

    result = sc.run_auto_settlement_all(triggered_by="scheduler")
    assert result["paid_count"] == 1
    assert result["total_commission_minor"] == 3000

    dashboard = sc.admin_sales_commission_dashboard_payload()
    assert dashboard["stats"]["paid_out_commission_minor"] == 3000


def test_admin_dashboard_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    sc.apply_sales_commission_policy_update(
        SalesCommissionPolicyUpdate(enabled=True, initial_sale_percent=30, recurring_user_fee_percent=10)
    )
    sc.create_sales_agent(SalesAgentCreate(name="Agent A", country_code="KR"))
    payload = sc.admin_sales_commission_dashboard_payload()
    assert payload["commission_policy"]["initial_sale_percent"] == 30.0
    assert payload["stats"]["agent_count"] == 1
    assert "office_bank_accounts" in payload
