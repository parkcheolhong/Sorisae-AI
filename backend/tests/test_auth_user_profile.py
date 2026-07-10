from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth import create_access_token, get_current_user
from backend.auth_router import router as auth_router
from backend.database import Base, get_db
from backend.marketplace import models


def _build_client() -> tuple[TestClient, FastAPI, sessionmaker[Session]]:
    import os

    os.environ["ALLOW_UNVERIFIED_SIGNUP"] = "1"
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
    return TestClient(app), app, testing_session_local


def test_signup_persists_preferred_language_and_country_code():
    client, _, _ = _build_client()
    response = client.post(
        "/api/auth/signup",
        json={
            "username": "jp_user",
            "email": "jp_user@example.com",
            "password": "password123",
            "preferred_language": "ja",
            "country_code": "JP",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["preferred_language"] == "ja"
    assert payload["country_code"] == "JP"


def test_signup_rejects_unsupported_language():
    client, _, _ = _build_client()
    response = client.post(
        "/api/auth/signup",
        json={
            "username": "bad_lang",
            "email": "bad_lang@example.com",
            "password": "password123",
            "preferred_language": "unsupported",
            "country_code": "KR",
        },
    )
    assert response.status_code == 400


def test_patch_me_updates_profile():
    client, app, testing_session_local = _build_client()
    signup = client.post(
        "/api/auth/signup",
        json={
            "username": "profile_user",
            "email": "profile_user@example.com",
            "password": "password123",
            "preferred_language": "ko",
            "country_code": "KR",
        },
    )
    assert signup.status_code == 201

    with testing_session_local() as db:
        user = (
            db.query(models.User)
            .filter(models.User.email == "profile_user@example.com")
            .first()
        )
        assert user is not None
        app.dependency_overrides[get_current_user] = lambda: user

    token = create_access_token({"sub": "profile_user@example.com"})
    patch = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"preferred_language": "ja", "country_code": "JP"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["preferred_language"] == "ja"
    assert patch.json()["country_code"] == "JP"

    with testing_session_local() as db:
        user = (
            db.query(models.User)
            .filter(models.User.email == "profile_user@example.com")
            .first()
        )
        assert user is not None
        app.dependency_overrides[get_current_user] = lambda: user

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["preferred_language"] == "ja"
    assert me.json()["country_code"] == "JP"
