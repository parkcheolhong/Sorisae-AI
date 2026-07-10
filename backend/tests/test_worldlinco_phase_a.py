"""Phase A tests — settlement on confirm + billing policy license gate."""

import json

import pytest

from backend.marketplace import worldlinco_billing_policy as wbp
from backend.marketplace import worldlinco_marketplace_settlement as wms
from backend.marketplace import worldlinco_sales_commission as sc
from backend.marketplace.worldlinco_billing_policy import worldlinco_free_access_grants_license
from backend.marketplace.worldlinco_sales_commission import OfficeBankAccountUpdate


@pytest.fixture
def isolated_billing_policy_path(tmp_path, monkeypatch):
    fake_path = tmp_path / "worldlinco_billing_policy.json"
    fake_path.write_text(
        json.dumps({"version": 1, "access_mode": "free", "billing_collection_paused": False}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(wbp, "WORLDLINGCO_BILLING_POLICY_PATH", fake_path)
    return fake_path


def test_resolve_worldlinco_purchase_context_for_plan_amount():
    ctx = wms.resolve_worldlinco_purchase_settlement_context(
        user_id=1,
        payment_amount_minor=9900,
    )
    assert ctx is not None
    assert ctx["plan_key"] == "voip_lite"
    assert ctx["paid_amount_minor"] == 9900


def test_resolve_worldlinco_purchase_context_skips_non_plan_amount():
    ctx = wms.resolve_worldlinco_purchase_settlement_context(
        user_id=1,
        payment_amount_minor=800000,
    )
    assert ctx is None


def test_apply_confirmed_settlement_only_for_worldlinco_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
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

    skipped = wms.apply_confirmed_worldlinco_marketplace_settlements(
        user_id=701,
        purchase_id=9001,
        payment_amount_minor=250000,
        transaction_id="hotel-txn-1",
        user_country_code="KR",
    )
    assert skipped["applied"] is False

    applied = wms.apply_confirmed_worldlinco_marketplace_settlements(
        user_id=701,
        purchase_id=9002,
        payment_amount_minor=9900,
        transaction_id="wl-txn-1",
        user_country_code="KR",
    )
    assert applied["applied"] is True
    assert applied["settlements"]["local_revenue_event"] is not None
    assert applied["settlements"]["local_revenue_event"]["settlement_status"] == "paid_out"


def test_free_access_grants_license_for_worldlinco_product(isolated_billing_policy_path):
    assert worldlinco_free_access_grants_license("worldlinco-voip-lite") is True
    assert worldlinco_free_access_grants_license("some-other-product") is False


def test_paid_mode_blocks_free_license_bypass(isolated_billing_policy_path):
    from backend.marketplace.worldlinco_billing_policy import (
        WorldlincoBillingPolicyUpdate,
        apply_worldlinco_billing_policy_update,
    )

    apply_worldlinco_billing_policy_update(
        WorldlincoBillingPolicyUpdate(access_mode="paid", billing_collection_paused=False),
        updated_by="admin@test",
    )
    assert worldlinco_free_access_grants_license("worldlinco-voip-lite") is False


def test_billing_collection_paused_grants_free_license_in_paid_mode(isolated_billing_policy_path):
    from backend.marketplace.worldlinco_billing_policy import (
        WorldlincoBillingPolicyUpdate,
        apply_worldlinco_billing_policy_update,
    )

    apply_worldlinco_billing_policy_update(
        WorldlincoBillingPolicyUpdate(access_mode="paid", billing_collection_paused=True),
        updated_by="admin@test",
    )
    assert worldlinco_free_access_grants_license("worldlinco-voip-pro") is True
