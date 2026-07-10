from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.tourism_review_router import router
from backend.security_gates import get_current_user


class _FakeReviewStore:
    available = True

    def __init__(self) -> None:
        self.saved_labels: list[dict] = []

    def save_labels(self, labels: list[dict], *, reviewer: str | None = None) -> int:
        self.saved_labels.extend({**label, "reviewer": label.get("reviewer") or reviewer} for label in labels)
        return len(labels)

    def sample_pois(self, n: int = 20) -> list[dict]:
        return []

    def sample_retrieval(self, k: int = 5) -> list[dict]:
        return []

    def stats(self) -> dict:
        return {"available": True, "total_labels": len(self.saved_labels)}


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_tourism_review_labels_rejects_unauthenticated_requests(monkeypatch):
    monkeypatch.setenv("TOURISM_REVIEW_ENABLED", "1")
    client = _build_client()

    response = client.post(
        "/api/tourism-review/labels",
        json={"reviewer": "attacker", "labels": [{"verdict": "incorrect", "place_name": "poison"}]},
    )

    assert response.status_code == 401


def test_tourism_review_labels_rejects_non_admin_users(monkeypatch):
    monkeypatch.setenv("TOURISM_REVIEW_ENABLED", "1")
    client = _build_client()
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=2,
        email="user@example.com",
        is_admin=False,
        is_superuser=False,
    )

    response = client.post(
        "/api/tourism-review/labels",
        json={"reviewer": "user", "labels": [{"verdict": "incorrect", "place_name": "poison"}]},
    )

    assert response.status_code == 403


def test_tourism_review_labels_allows_admin_users(monkeypatch):
    monkeypatch.setenv("TOURISM_REVIEW_ENABLED", "1")
    fake_store = _FakeReviewStore()

    import backend.services.tourism_kb.review as review_module

    monkeypatch.setattr(review_module, "get_review_store", lambda: fake_store)
    client = _build_client()
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        email="admin@example.com",
        is_admin=True,
        is_superuser=False,
    )

    response = client.post(
        "/api/tourism-review/labels",
        json={"reviewer": "admin", "labels": [{"verdict": "correct", "place_name": "safe"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"saved": 1}
    assert fake_store.saved_labels == [{"verdict": "correct", "place_name": "safe", "reviewer": "admin", "item_type": "poi", "query": None, "place_source": None, "place_source_id": None, "category": None, "note": None}]
