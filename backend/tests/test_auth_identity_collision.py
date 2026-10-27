"""Email and username must not select each other's accounts."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ALLOW_UNVERIFIED_SIGNUP", "1")
os.environ.setdefault("SESSION_CACHE_ENABLED", "0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-identity-collision-32")

from backend.auth import (  # noqa: E402
    authenticate_login_identifier,
    create_access_token,
    get_password_hash,
    resolve_user_for_subject,
    set_active_session,
    _resolve_current_user_from_token,
)
from backend.auth_router import router as auth_router  # noqa: E402
from backend.database import Base, get_db  # noqa: E402
import backend.database as database  # noqa: E402
import backend.marketplace.database as marketplace_database  # noqa: E402
from backend.marketplace import models  # noqa: E402


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    database.SessionLocal = factory
    marketplace_database.SessionLocal = factory
    return factory


def _add_user(db: Session, *, username: str, email: str, password: str) -> models.User:
    user = models.User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_token_subject_stays_on_the_email_owner_when_username_collides():
    factory = _session_factory()
    with factory() as db:
        earlier = _add_user(
            db,
            username="alice@good.com",
            email="alice.real@good.com",
            password="victim-pass-123",
        )
        later = _add_user(
            db,
            username="attacker",
            email="alice@good.com",
            password="attacker-pass-123",
        )
        earlier_id = int(earlier.id)
        later_id = int(later.id)

    set_active_session(later_id, "attacker-sid")
    token = create_access_token({"sub": "alice@good.com", "sid": "attacker-sid"})
    resolved = _resolve_current_user_from_token(token)
    assert int(resolved.id) == later_id
    assert resolved.email == "alice@good.com"

    set_active_session(earlier_id, "earlier-sid")
    resolved_after_other_login = _resolve_current_user_from_token(token)
    assert int(resolved_after_other_login.id) == later_id

    with factory() as db:
        by_username_password = authenticate_login_identifier(
            db,
            "alice@good.com",
            "victim-pass-123",
        )
        by_email_password = authenticate_login_identifier(
            db,
            "alice@good.com",
            "attacker-pass-123",
        )
        assert by_username_password is not None
        assert int(by_username_password.id) == earlier_id
        assert by_email_password is not None
        assert int(by_email_password.id) == later_id
        assert int(resolve_user_for_subject(db, "alice.real@good.com").id) == earlier_id
        assert int(resolve_user_for_subject(db, "attacker").id) == later_id


def test_login_me_returns_the_authenticated_account_when_identifiers_collide():
    factory = _session_factory()
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/auth")

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    first = client.post(
        "/api/auth/signup",
        json={
            "username": "alice@good.com",
            "email": "alice.real@good.com",
            "password": "victim-pass-123",
            "preferred_language": "ko",
            "country_code": "KR",
        },
    )
    assert first.status_code == 201, first.text
    second = client.post(
        "/api/auth/signup",
        json={
            "username": "attacker",
            "email": "alice@good.com",
            "password": "attacker-pass-123",
            "preferred_language": "ko",
            "country_code": "KR",
        },
    )
    assert second.status_code == 201, second.text

    logged_in = client.post(
        "/api/auth/login",
        data={"username": "attacker", "password": "attacker-pass-123"},
    )
    assert logged_in.status_code == 200, logged_in.text
    token = logged_in.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "alice@good.com"
    assert me.json()["username"] == "attacker"
    assert me.json()["id"] == second.json()["id"]
