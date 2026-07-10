"""Tests for WorldLinco referral QR / signup attribution."""

from backend.marketplace import worldlinco_referral as wr


def test_referral_code_generation_and_lookup(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    code = wr.ensure_user_referral_code(user_id=101, username="alice")
    assert code.startswith("WL101")
    referrer = wr.resolve_referrer_by_code(code)
    assert referrer is not None
    assert referrer["user_id"] == 101
    assert referrer["username"] == "alice"


def test_record_referral_signup_once(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    code = wr.ensure_user_referral_code(user_id=10, username="referrer")
    first = wr.record_referral_signup(
        referral_code=code,
        referred_user_id=20,
        referred_username="newbie",
        referred_email="newbie@example.com",
    )
    assert first is not None
    assert first["referrer_code"] == code
    assert first["referred_user_id"] == 20

    duplicate = wr.record_referral_signup(
        referral_code=code,
        referred_user_id=20,
        referred_username="newbie",
        referred_email="newbie@example.com",
    )
    assert duplicate is not None
    assert duplicate["id"] == first["id"]

    self_ref = wr.record_referral_signup(
        referral_code=code,
        referred_user_id=10,
        referred_username="referrer",
        referred_email="referrer@example.com",
    )
    assert self_ref is None


def test_referral_me_payload_and_admin_dashboard(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    code = wr.ensure_user_referral_code(user_id=55, username="promoter")
    wr.record_referral_signup(
        referral_code=code,
        referred_user_id=99,
        referred_username="guest",
        referred_email="guest@example.com",
    )
    me = wr.referral_me_payload(user_id=55, username="promoter", api_base="https://api.example.com")
    assert me["code"] == code
    assert me["signup_count"] == 1
    assert me["invite_url"].endswith(f"/invite/{code}")
    assert "ref=" in me["deeplink"]

    admin = wr.admin_referral_dashboard_payload()
    assert admin["total_signups"] == 1
    assert admin["referrer_count"] == 1
    assert admin["leaders"][0]["referrer_user_id"] == 55


def test_invite_landing_html_contains_apk_and_deeplink(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "REFERRAL_STORE_PATH", tmp_path / "referrals.json")
    code = wr.ensure_user_referral_code(user_id=7, username="host")
    html = wr.build_invite_landing_html(code=code, api_base="https://api.example.com", referrer_username="host")
    assert code in html
    assert "latest.apk" in html
    assert f"worldlingo://invite?ref={code}" in html


def test_render_referral_qr_png():
    png = wr.render_referral_qr_png("https://api.example.com/api/marketplace/worldlinco/invite/WLTEST")
    assert isinstance(png, bytes)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
