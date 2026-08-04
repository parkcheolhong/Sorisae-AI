from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth_router import router as auth_router
import backend.database as database_module
from backend.database import Base, get_db
from backend.marketplace import models


def _build_client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
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
    database_module.SessionLocal = testing_session_local
    return TestClient(app), testing_session_local


def test_social_login_start_redirects_to_app_callback_and_issues_token():
    client, testing_session_local = _build_client()

    response = client.get(
        "/api/auth/social/google/start",
        params={"redirect_uri": "worldlinco://auth/callback"},
        follow_redirects=False,
    )

    assert response.status_code == 302, response.text
    location = response.headers["location"]
    parsed = urlparse(location)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == "worldlinco://auth/callback"

    query = parse_qs(parsed.query)
    assert query["provider"][0] == "google"
    assert query["access_token"][0]
    assert query["refresh_token"][0]
    assert query["id_token"][0]
    assert query["email"][0].endswith("@worldlinco.dev")

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {query['access_token'][0]}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["email"] == query["email"][0]

    with testing_session_local() as db:
        user = db.query(models.User).filter(models.User.email == query["email"][0]).first()
        assert user is not None
        assert user.username


def test_social_login_start_rejects_bad_redirect_uri():
    client, _ = _build_client()

    response = client.get(
        "/api/auth/social/kakao/start",
        params={"redirect_uri": "https://example.com/callback"},
        follow_redirects=False,
    )

    assert response.status_code == 400
