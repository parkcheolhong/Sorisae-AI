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


def test_nearby_places_accepts_app_radius_options_up_to_500km():
    # 앱 RADIUS_OPTIONS 값(20/30/50/100/500km)이 422 없이 허용되어야 한다.
    # (거리·지역 무관 검색 지원: 상한을 100km→500km 로 상향.)
    client = _build_test_client()

    for radius_m in (20000, 30000, 50000, 70000, 100000, 200000, 500000):
        response = client.get(
            "/api/marketplace/nadotongryoksa/lbs/nearby",
            params={"lat": 37.5665, "lon": 126.9780, "category": "all", "radius_m": radius_m, "target_lang": "ko"},
        )
        assert response.status_code == 200, (radius_m, response.status_code, response.text)


def test_nearby_places_rejects_radius_over_cap():
    client = _build_test_client()

    response = client.get(
        "/api/marketplace/nadotongryoksa/lbs/nearby",
        params={"lat": 37.5665, "lon": 126.9780, "category": "all", "radius_m": 500001, "target_lang": "ko"},
    )

    assert response.status_code == 422


def test_nearby_merges_live_provider_results_worldwide(monkeypatch):
    # 정적 카탈로그에 없는 해외/지방 좌표라도 라이브 제공자 결과가 병합되어야 한다.
    import backend.marketplace.nadotongryoksa_lbs_router as lbs

    def _fake_live(lat, lon, category, radius_m, limit, target_lang):
        return [
            {
                "id": "serp-paris-eiffel",
                "category": "attraction",
                "name": "Eiffel Tower",
                "lat": lat + 0.01,
                "lon": lon + 0.01,
                "address": "Champ de Mars, Paris",
                "rating": 4.7,
                "price_tier": "-",
                "booking_supported": False,
                "phone": "+33-892-70-12-39",
                "summary": {"en": "Iconic Paris landmark"},
                "amenities": [],
                "review_query": "Eiffel Tower",
            }
        ]

    monkeypatch.setenv("NADO_LBS_LIVE_PROVIDER", "1")
    monkeypatch.setattr(lbs, "_fetch_live_place_dicts", _fake_live)

    client = _build_test_client()
    # 파리 좌표(정적 카탈로그엔 서울만 있음) → 라이브 결과로 채워져야 함
    response = client.get(
        "/api/marketplace/nadotongryoksa/lbs/nearby",
        params={"lat": 48.8584, "lon": 2.2945, "category": "all", "radius_m": 100000, "target_lang": "en"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    names = [p["name"] for p in payload["places"]]
    assert "Eiffel Tower" in names
    eiffel = next(p for p in payload["places"] if p["name"] == "Eiffel Tower")
    assert eiffel["phone"] == "+33-892-70-12-39"
    assert eiffel["category"] == "attraction"
    assert eiffel["google_maps_url"].startswith("https://www.google.com/maps/search/")


def test_nearby_live_provider_disabled_under_pytest_by_default(monkeypatch):
    # pytest 기본 환경에서는 라이브 제공자가 비활성 → 서울 밖은 0건(정적만).
    import backend.marketplace.nadotongryoksa_lbs_router as lbs

    monkeypatch.delenv("NADO_LBS_LIVE_PROVIDER", raising=False)

    def _boom(*args, **kwargs):  # 호출되면 안 됨
        raise AssertionError("live provider must stay disabled under pytest by default")

    monkeypatch.setattr(lbs, "_fetch_live_place_dicts", _boom)

    client = _build_test_client()
    response = client.get(
        "/api/marketplace/nadotongryoksa/lbs/nearby",
        params={"lat": 48.8584, "lon": 2.2945, "category": "all", "radius_m": 100000, "target_lang": "en"},
    )
    assert response.status_code == 200
    assert response.json()["places"] == []


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