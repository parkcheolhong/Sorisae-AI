from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.marketplace.router as marketplace_router_module
from backend.auth import get_current_user


class _FakeDb:
    pass


def _build_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(marketplace_router_module.router, prefix="/api/marketplace")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=11, email="travel@example.com")
    app.dependency_overrides[marketplace_router_module.get_db] = lambda: _FakeDb()
    return TestClient(app)


def test_nearby_places_returns_sorted_lbs_payload():
    client = _build_test_client()

    response = client.get("/api/marketplace/nadotongryoksa/lbs/nearby", params={"lat": 37.5665, "lon": 126.9780, "category": "all", "radius_m": 20000, "target_lang": "en"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["source"] == "nadotongryoksa-lbs"
    assert payload["places"]
    assert payload["places"][0]["distance_m"] <= payload["places"][1]["distance_m"]
    assert payload["places"][0]["google_maps_url"].startswith("https://www.google.com/maps/search/")
    assert payload["places"][0]["maps_reviews_path"].startswith("/api/external-search/maps-reviews")


def test_nearby_places_filters_by_category():
    client = _build_test_client()

    response = client.get("/api/marketplace/nadotongryoksa/lbs/nearby", params={"lat": 37.5665, "lon": 126.9780, "category": "hotel", "radius_m": 15000, "target_lang": "ja"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["requested_category"] == "hotel"
    assert all(item["category"] == "hotel" for item in payload["places"])
    assert all(item["booking_supported"] is True for item in payload["places"])


def test_booking_returns_confirmation_for_hotel_only():
    client = _build_test_client()

    response = client.post("/api/marketplace/nadotongryoksa/lbs/bookings", json={"place_id": "hotel-lotte-seoul", "customer_name": "홍길동", "checkin_date": "2026-05-10", "checkout_date": "2026-05-12", "guests": 2, "room_count": 1, "target_lang": "en"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["confirmation_id"].startswith("NADO-")
    assert payload["place_id"] == "hotel-lotte-seoul"
    assert payload["translated_message"]


def test_booking_rejects_non_hotel_place():
    client = _build_test_client()

    response = client.post("/api/marketplace/nadotongryoksa/lbs/bookings", json={"place_id": "airport-icn-t1", "customer_name": "홍길동", "checkin_date": "2026-05-10", "checkout_date": "2026-05-12", "guests": 1, "room_count": 1, "target_lang": "ko"})

    assert response.status_code == 400
    assert "호텔 카테고리" in response.json()["detail"]