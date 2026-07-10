"""Tests for WorldLinco regional manager scoped dashboard."""

from backend.marketplace import worldlinco_sales_commission as sc
from backend.marketplace.worldlinco_sales_commission import (
    RegionalManagerCreate,
    SalesAgentCreate,
    create_regional_manager,
)


def test_regional_manager_scope_and_users(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")

    agent_kr = sc.create_sales_agent(SalesAgentCreate(name="KR Agent", country_code="KR", region_code="KR"))
    agent_jp = sc.create_sales_agent(SalesAgentCreate(name="JP Agent", country_code="JP", region_code="JP"))

    sc.record_sales_agent_signup(
        sales_agent_code=agent_kr["code"],
        user_id=201,
        username="kr_user",
        email="kr@example.com",
        user_country_code="KR",
    )
    sc.record_sales_agent_signup(
        sales_agent_code=agent_jp["code"],
        user_id=202,
        username="jp_user",
        email="jp@example.com",
        user_country_code="JP",
    )
    sc.record_sales_commission_on_payment(
        user_id=201,
        payment_amount_minor=10000,
        provider="card",
        transaction_id="kr-txn-1",
    )

    create_regional_manager(
        RegionalManagerCreate(user_id=9001, name="KR Manager", country_code="KR", region_code="KR"),
        created_by="admin@test",
    )

    scope = sc.resolve_regional_scope_for_access(is_admin=False, user_id=9001)
    assert scope["country_code"] == "KR"
    assert scope["region_code"] == "KR"

    dashboard = sc.regional_manager_dashboard_payload(country_code="KR", region_code="KR")
    assert dashboard["stats"]["attributed_users"] == 1
    assert dashboard["stats"]["paying_users"] == 1

    users = sc.regional_manager_users_payload(country_code="KR", region_code="KR")
    assert users["total"] == 1
    assert users["users"][0]["user_id"] == 201
    assert users["users"][0]["payment_count"] == 1

    jp_users = sc.regional_manager_users_payload(country_code="JP", region_code="JP")
    assert jp_users["total"] == 1
    assert jp_users["users"][0]["user_id"] == 202


def test_regional_manager_user_assignment_conflict(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    create_regional_manager(
        RegionalManagerCreate(user_id=42, name="Manager A", country_code="KR", region_code="KR"),
        created_by="admin@test",
    )
    try:
        create_regional_manager(
            RegionalManagerCreate(user_id=42, name="Manager B", country_code="US", region_code="US"),
            created_by="admin@test",
        )
        assert False, "expected duplicate assignment error"
    except ValueError as exc:
        assert str(exc) == "regional_manager_user_already_assigned"


def test_admin_scope_requires_country_code(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    try:
        sc.resolve_regional_scope_for_access(is_admin=True, user_id=1, country_code=None)
        assert False, "expected country_code_required"
    except ValueError as exc:
        assert str(exc) == "country_code_required"

    scope = sc.resolve_regional_scope_for_access(is_admin=True, user_id=1, country_code="KR", region_code="KR")
    assert scope["scope"] == "admin"
    assert scope["country_code"] == "KR"


def test_regional_manager_may_use_admin_portal_passkey(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SALES_COMMISSION_STORE_PATH", tmp_path / "sales_commission.json")
    from backend.auth_router import _user_may_use_admin_portal

    sc.create_regional_manager(
        RegionalManagerCreate(user_id=42, name="Regional Mgr", country_code="KR", region_code="KR"),
        created_by="admin@test",
    )

    class FakeUser:
        id = 42
        is_admin = False
        is_superuser = False

    class FakeAdmin:
        id = 1
        is_admin = True
        is_superuser = False

    assert _user_may_use_admin_portal(FakeUser()) is True
    assert _user_may_use_admin_portal(FakeAdmin()) is True
    assert _user_may_use_admin_portal(type("U", (), {"id": 999, "is_admin": False, "is_superuser": False})()) is False
