"""Tests for GPS-radius tourism promo resolution."""

from backend.marketplace import worldlinco_tourism_promo as wtp
from backend.marketplace.worldlinco_tourism_promo import (
    UserTourismPromoCreate,
    create_user_tourism_promo,
    resolve_tourism_promo_board,
    resolve_tourism_promo_nearby,
)


def test_promo_requires_gps_country():
    payload = resolve_tourism_promo_nearby(
        country_code=None,
        latitude=40.7128,
        longitude=-74.006,
        language="en",
    )
    assert payload["enabled"] is False
    assert payload["reason"] == "gps_country_required"


def test_promo_requires_coordinates():
    payload = resolve_tourism_promo_nearby(
        country_code="US",
        latitude=None,
        longitude=None,
        language="en",
    )
    assert payload["enabled"] is False
    assert payload["reason"] == "gps_coordinates_required"


def test_promo_us_nyc_within_50km_english():
    payload = resolve_tourism_promo_nearby(
        country_code="US",
        latitude=40.73,
        longitude=-73.99,
        language="en",
    )
    assert payload["enabled"] is True
    assert payload["spot_id"] == "us-nyc"
    assert payload["language"] == "en"
    assert "New York" in payload["title"]
    assert payload["distance_km"] is not None
    assert payload["distance_km"] <= 50


def test_promo_us_outside_radius_hidden():
    payload = resolve_tourism_promo_nearby(
        country_code="US",
        latitude=41.8781,
        longitude=-87.6298,
        language="en",
    )
    assert payload["enabled"] is False
    assert payload["reason"] == "outside_radius"


def test_promo_user_language_korean_in_japan():
    payload = resolve_tourism_promo_nearby(
        country_code="JP",
        latitude=35.68,
        longitude=139.76,
        language="ko",
    )
    assert payload["enabled"] is True
    assert payload["language"] == "ko"
    assert "도쿄" in payload["title"]


def test_promo_no_profile_country_fallback():
    payload = resolve_tourism_promo_nearby(
        country_code="KR",
        latitude=37.56,
        longitude=126.98,
        language="ko",
    )
    assert payload["enabled"] is True
    assert payload["country_code"] == "KR"


def test_promo_board_lists_country_spots_in_user_language():
    payload = resolve_tourism_promo_board(
        country_code="JP",
        latitude=35.68,
        longitude=139.76,
        language="ko",
    )
    assert payload["enabled"] is True
    assert len(payload["items"]) >= 1
    assert payload["items"][0]["title"]
    assert payload["language"] == "ko"


def test_promo_board_without_coordinates_still_lists():
    payload = resolve_tourism_promo_board(
        country_code="US",
        language="en",
    )
    assert payload["enabled"] is True
    assert payload["user_can_post"] is True
    assert len(payload["items"]) >= 1


def test_user_promo_on_board_without_admin_config(tmp_path, monkeypatch):
    monkeypatch.setattr(wtp, "USER_TOURISM_PROMO_PATH", tmp_path / "user_promo.json")
    create_user_tourism_promo(
        user_id=42,
        author_username="traveler",
        payload=UserTourismPromoCreate(
            title="로컬 맛집 홍보",
            body="저녁 특선 할인 중입니다.",
            country_code="ZZ",
            language="ko",
        ),
    )
    payload = resolve_tourism_promo_board(country_code="ZZ", language="ko")
    assert payload["enabled"] is True
    assert len(payload["items"]) == 1
    assert payload["items"][0]["source"] == "user"
    assert payload["items"][0]["author_username"] == "traveler"
    assert payload["items"][0]["title"] == "로컬 맛집 홍보"
