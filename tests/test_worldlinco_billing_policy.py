import json
import hashlib
from datetime import datetime, timezone

import pytest  # pyright: ignore[reportMissingImports]

from backend.marketplace import worldlinco_billing_policy as wbp
from backend.marketplace.worldlinco_billing_policy import (
    WorldlincoBillingPolicyUpdate,
    apply_worldlinco_billing_policy_update,
    load_worldlinco_billing_policy,
    resolve_worldlinco_billing_access,
    worldlinco_billing_policy_public_payload,
)


@pytest.fixture
def isolated_billing_policy_path(tmp_path, monkeypatch):
    fake_path = tmp_path / "worldlinco_billing_policy.json"
    fake_path.write_text(
        json.dumps({"version": 1, "access_mode": "free", "billing_collection_paused": False}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(wbp, "WORLDLINGCO_BILLING_POLICY_PATH", fake_path)
    return fake_path


def test_billing_policy_defaults_free_access():
    payload = load_worldlinco_billing_policy()
    assert payload["access_mode"] == "free"
    resolved = resolve_worldlinco_billing_access(payload)
    assert resolved["free_access_active"] is True
    assert resolved["show_pricing_ui"] is False


def test_billing_policy_paid_mode_requires_purchase_gate():
    policy = {
        "access_mode": "paid",
        "billing_collection_paused": False,
        "show_pricing_ui": True,
    }
    resolved = resolve_worldlinco_billing_access(policy)
    assert resolved["access_mode"] == "paid"
    assert resolved["free_access_active"] is False
    assert resolved["show_pricing_ui"] is True


def test_billing_collection_paused_grants_free_access_in_paid_mode():
    policy = {
        "access_mode": "paid",
        "billing_collection_paused": True,
        "show_pricing_ui": False,
    }
    resolved = resolve_worldlinco_billing_access(policy)
    assert resolved["access_mode"] == "paid"
    assert resolved["free_access_active"] is True


def test_auto_switch_to_paid_after_promo_end():
    policy = {
        "access_mode": "free",
        "billing_collection_paused": False,
        "auto_switch_to_paid_on_promo_end": True,
        "promo_ends_at": "2026-01-01T00:00:00Z",
    }
    after_end = datetime(2026, 6, 1, tzinfo=timezone.utc)
    resolved = resolve_worldlinco_billing_access(policy, now=after_end)
    assert resolved["access_mode"] == "paid"
    assert resolved["free_access_active"] is False


def test_billing_policy_update_persists(isolated_billing_policy_path):
    updated = apply_worldlinco_billing_policy_update(
        WorldlincoBillingPolicyUpdate(access_mode="paid", show_pricing_ui=True),
        updated_by="test-admin",
    )
    expected_hash = f"hashed:{hashlib.sha256('test-admin'.encode('utf-8')).hexdigest()[:32]}"
    assert updated["access_mode"] == "paid"
    assert updated["show_pricing_ui"] is True
    assert updated["updated_by"] == expected_hash
    persisted = json.loads(isolated_billing_policy_path.read_text(encoding="utf-8"))
    assert persisted["access_mode"] == "paid"
    assert persisted["updated_by"] == expected_hash


@pytest.mark.parametrize("updated_by", ["system", "admin"])
def test_billing_policy_system_admin_updated_by_not_hashed(isolated_billing_policy_path, updated_by):
    updated = apply_worldlinco_billing_policy_update(
        WorldlincoBillingPolicyUpdate(access_mode="paid"),
        updated_by=updated_by,
    )
    assert updated["updated_by"] == updated_by
    persisted = json.loads(isolated_billing_policy_path.read_text(encoding="utf-8"))
    assert persisted["updated_by"] == updated_by


def test_billing_policy_public_payload():
    public = worldlinco_billing_policy_public_payload()
    assert "free_access_active" in public
    assert "note" not in public
    assert "updated_by" not in public
