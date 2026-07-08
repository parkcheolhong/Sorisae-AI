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


def test_partner_click_endpoint_returns_click_ref():
    client = _build_test_client()

    response = client.post(
        "/api/marketplace/nadotongryoksa/lbs/clicks",
        json={"partner_id": "partner-hotel-default", "landing_url": "https://example.com/hotel"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["click_ref"].startswith("CLK-")
    assert payload["partner_id"] == "partner-hotel-default"


def test_booking_lifecycle_start_confirm_complete_chain():
    client = _build_test_client()

    start_response = client.post(
        "/api/marketplace/nadotongryoksa/lbs/bookings/start",
        json={
            "place_id": "hotel-lotte-seoul",
            "customer_name": "홍길동",
            "checkin_date": "2026-05-10",
            "checkout_date": "2026-05-12",
            "guests": 2,
            "room_count": 1,
            "target_lang": "en",
        },
    )
    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["stage"] == "initiated"
    booking_ref = start_payload["booking_ref"]
    assert booking_ref.startswith("BK-")

    confirm_response = client.post(
        f"/api/marketplace/nadotongryoksa/lbs/bookings/{booking_ref}/confirm",
        json={"booking_ref": booking_ref, "status_note": "payment authorized"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["stage"] == "confirmed"

    complete_response = client.post(
        f"/api/marketplace/nadotongryoksa/lbs/bookings/{booking_ref}/complete",
        json={"booking_ref": booking_ref, "status_note": "voucher issued"},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["stage"] == "completed"


def test_commission_settlement_batch_draft_chain():
    client = _build_test_client()

    start_response = client.post(
        "/api/marketplace/nadotongryoksa/lbs/bookings/start",
        json={
            "place_id": "hotel-lotte-seoul",
            "customer_name": "김정산",
            "checkin_date": "2026-06-01",
            "checkout_date": "2026-06-03",
            "guests": 2,
            "room_count": 1,
            "target_lang": "ko",
        },
    )
    assert start_response.status_code == 200
    booking_ref = start_response.json()["booking_ref"]

    complete_response = client.post(
        f"/api/marketplace/nadotongryoksa/lbs/bookings/{booking_ref}/complete",
        json={"booking_ref": booking_ref, "status_note": "settlement ready"},
    )
    assert complete_response.status_code == 200

    dry_run_response = client.post(
        "/api/marketplace/nadotongryoksa/lbs/settlements/commission-batch",
        json={
            "dry_run": True,
            "limit": 50,
            "default_commission_amount": 15.5,
            "commission_rate": 0.1,
            "currency": "usd",
        },
    )
    assert dry_run_response.status_code == 200
    dry_payload = dry_run_response.json()
    assert dry_payload["dry_run"] is True
    assert dry_payload["created"] >= 1
    assert dry_payload["currency"] == "USD"

    execute_response = client.post(
        "/api/marketplace/nadotongryoksa/lbs/settlements/commission-batch",
        json={
            "dry_run": False,
            "limit": 50,
            "default_commission_amount": 15.5,
            "commission_rate": 0.1,
            "currency": "usd",
        },
    )
    assert execute_response.status_code == 200
    execute_payload = execute_response.json()
    assert execute_payload["dry_run"] is False
    assert execute_payload["created"] >= 1

    rerun_response = client.post(
        "/api/marketplace/nadotongryoksa/lbs/settlements/commission-batch",
        json={
            "dry_run": False,
            "limit": 50,
            "default_commission_amount": 15.5,
            "commission_rate": 0.1,
            "currency": "usd",
        },
    )
    assert rerun_response.status_code == 200
    rerun_payload = rerun_response.json()
    assert rerun_payload["created"] == 0
    assert rerun_payload["skipped_existing"] >= 1


def test_booking_cancel_and_refund_chain_updates_stage():
    client = _build_test_client()

    start_response = client.post(
        "/api/marketplace/nadotongryoksa/lbs/bookings/start",
        json={
            "place_id": "hotel-lotte-seoul",
            "customer_name": "환불테스트",
            "checkin_date": "2026-06-11",
            "checkout_date": "2026-06-12",
            "guests": 1,
            "room_count": 1,
            "target_lang": "ko",
        },
    )
    assert start_response.status_code == 200
    booking_ref = start_response.json()["booking_ref"]

    cancel_response = client.post(
        f"/api/marketplace/nadotongryoksa/lbs/bookings/{booking_ref}/cancel",
        json={"booking_ref": booking_ref, "reason": "customer changed plans"},
    )
    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()
    assert cancel_payload["stage"] == "cancelled"
    assert cancel_payload["ledger_adjusted"] is False

    refund_response = client.post(
        f"/api/marketplace/nadotongryoksa/lbs/bookings/{booking_ref}/refund",
        json={"booking_ref": booking_ref, "reason": "full refund approved", "refund_amount": 18.5},
    )
    assert refund_response.status_code == 200
    refund_payload = refund_response.json()
    assert refund_payload["stage"] == "refunded"
    assert refund_payload["ledger_adjusted"] is True
    assert refund_payload["adjustment_amount"] == 18.5


def test_booking_cancel_rejects_mismatched_booking_ref():
    client = _build_test_client()

    start_response = client.post(
        "/api/marketplace/nadotongryoksa/lbs/bookings/start",
        json={
            "place_id": "hotel-lotte-seoul",
            "customer_name": "불일치테스트",
            "checkin_date": "2026-06-21",
            "checkout_date": "2026-06-23",
            "guests": 2,
            "room_count": 1,
            "target_lang": "ko",
        },
    )
    assert start_response.status_code == 200
    booking_ref = start_response.json()["booking_ref"]

    response = client.post(
        f"/api/marketplace/nadotongryoksa/lbs/bookings/{booking_ref}/cancel",
        json={"booking_ref": "BK-MISMATCH", "reason": "invalid request"},
    )
    assert response.status_code == 400
    assert "booking_ref mismatch" in response.json()["detail"]