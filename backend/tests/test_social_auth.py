from __future__ import annotations

import os
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth_router import router as auth_router
from backend.database import Base, get_db
from backend.models import User


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self._provider = kwargs.pop("provider", None)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, data=None, headers=None):
        return _FakeResponse({"access_token": "provider-token"})

    async def get(self, url, headers=None):
        provider_profiles = {
            "google": {"id": "google-123", "email": "google.user@example.com", "name": "Google User", "picture": "https://img.example/google.png"},
            "kakao": {"id": 456, "kakao_account": {"email": "kakao.user@example.com", "profile": {"nickname": "Kakao User", "profile_image_url": "https://img.example/kakao.png"}}},
            "naver": {"resultcode": "00", "message": "success", "response": {"id": "naver-789", "email": "naver.user@example.com", "name": "Naver User", "profile_image": "https://img.example/naver.png"}},
        }
        provider = "google"
        if "kakao" in url:
            provider = "kakao"
        elif "naver" in url:
            provider = "naver"
        return _FakeResponse(provider_profiles[provider])


def _build_client():
    os.environ["GOOGLE_CLIENT_ID"] = "google-client"
    os.environ["GOOGLE_CLIENT_SECRET"] = "google-secret"
    os.environ["KAKAO_CLIENT_ID"] = "kakao-client"
    os.environ["KAKAO_CLIENT_SECRET"] = "kakao-secret"
    os.environ["NAVER_CLIENT_ID"] = "naver-client"
    os.environ["NAVER_CLIENT_SECRET"] = "naver-secret"
    os.environ["SOCIAL_AUTH_FRONTEND_CALLBACK_URL"] = "http://frontend.local/auth/social/callback"

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/auth")

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session_local


def test_social_login_start_redirects_to_provider(monkeypatch):
    client, _ = _build_client()
    from backend import auth_router as module
    monkeypatch.setattr(module.httpx, "AsyncClient", _FakeAsyncClient)

    response = client.get("/api/auth/oauth/google/start", params={"return_to": "/marketplace"}, follow_redirects=False)
    assert response.status_code in (302, 307), response.text
    location = response.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    assert query["client_id"][0] == "google-client"
    assert query["response_type"][0] == "code"
    assert query["state"][0]
    assert query["redirect_uri"][0].endswith("/api/auth/oauth/google/callback")


def test_social_login_callback_creates_user_and_redirects(monkeypatch):
    client, testing_session_local = _build_client()
    from backend import auth_router as module
    monkeypatch.setattr(module.httpx, "AsyncClient", _FakeAsyncClient)

    start = client.get(
        "/api/auth/oauth/naver/start",
        params={
            "return_to": "/marketplace/orchestrator",
            "callback_url": "worldlingo://auth/social/callback",
        },
        follow_redirects=False,
    )
    assert start.status_code in (302, 307), start.text
    start_qs = parse_qs(urlparse(start.headers["location"]).query)
    state = start_qs["state"][0]

    callback = client.get("/api/auth/oauth/naver/callback", params={"code": "code-123", "state": state}, follow_redirects=False)
    assert callback.status_code in (302, 307), callback.text
    location = callback.headers["location"]
    assert location.startswith("worldlingo://auth/social/callback#")
    fragment = parse_qs(urlparse(location).fragment)
    assert fragment["provider"][0] == "naver"
    assert fragment["return_to"][0] == "/marketplace/orchestrator"
    assert fragment["access_token"][0]

    db = testing_session_local()
    try:
        user = db.query(User).filter(User.email == "naver.user@example.com").first()
        assert user is not None
        assert user.username
    finally:
        db.close()
