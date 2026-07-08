from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import tourism_review_router
from backend.security_gates import require_admin_user


class _FakeReviewStore:
    available = True

    def __init__(self) -> None:
        self.saved_labels = []

    def sample_pois(self, n: int):
        return [{"place_name": "Seoul Tower", "category": "landmark"} for _ in range(n)]

    def sample_retrieval(self, k: int):
        return [{"query": "seoul", "results": [{"place_name": "Seoul Tower", "score": 1.0}]} for _ in range(k)]

    def save_labels(self, labels, reviewer=None):
        self.saved_labels.extend({**label, "reviewer": reviewer} for label in labels)
        return len(labels)

    def stats(self):
        return {"available": True, "total_labels": len(self.saved_labels)}


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(tourism_review_router.router)
    return TestClient(app)


def test_tourism_review_rejects_anonymous_access_before_store_lookup(monkeypatch):
    def fail_if_called():
        raise AssertionError("review store should not be loaded without admin auth")

    monkeypatch.setattr("backend.services.tourism_kb.review.get_review_store", fail_if_called)

    client = _client()

    assert client.get("/api/tourism-review/sample").status_code == 401
    assert client.get("/api/tourism-review/stats").status_code == 401
    assert client.get("/api/tourism-review/console").status_code == 401
    assert (
        client.post(
            "/api/tourism-review/labels",
            json={"reviewer": "attacker", "labels": [{"verdict": "incorrect"}]},
        ).status_code
        == 401
    )


def test_tourism_review_allows_admin_label_submission(monkeypatch):
    store = _FakeReviewStore()
    monkeypatch.setattr("backend.services.tourism_kb.review.get_review_store", lambda: store)

    client = _client()
    client.app.dependency_overrides[require_admin_user] = lambda: SimpleNamespace(
        id=1,
        email="admin@example.com",
        is_admin=True,
    )

    response = client.post(
        "/api/tourism-review/labels",
        json={
            "reviewer": "ops",
            "labels": [
                {
                    "item_type": "poi",
                    "place_name": "Seoul Tower",
                    "verdict": "correct",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"saved": 1}
    assert store.saved_labels == [
        {
            "item_type": "poi",
            "query": None,
            "place_source": None,
            "place_source_id": None,
            "place_name": "Seoul Tower",
            "category": None,
            "verdict": "correct",
            "note": None,
            "reviewer": "ops",
        }
    ]
