from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth import get_password_hash
from backend.auth_router import router as auth_router
from backend.database import Base, get_db
from backend.models import User


def _build_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session_local()
    db.add(
        User(
            username="admin_user",
            email="admin@example.com",
            hashed_password=get_password_hash("oldpassword123"),
            is_admin=True,
            is_active=True,
        )
    )
    db.commit()
    db.close()

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/auth")

    def override_get_db():
        session = testing_session_local()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_admin_recovery_email_otp_and_password_reset():
    os.environ["APP_ENV"] = "dev"
    client = _build_client()

    start = client.post(
        "/api/auth/recovery/start",
        json={
            "scope": "admin",
            "user_hint": "admin@example.com",
            "verification_channel": "email",
        },
    )
    assert start.status_code == 200, start.text
    start_payload = start.json()
    assert start_payload.get("masked_target")
    assert start_payload.get("dev_otp_hint")

    verify = client.post(
        "/api/auth/recovery/verify-identity",
        json={
            "recovery_session_token": start_payload["recovery_session_token"],
            "verification_code": start_payload["dev_otp_hint"],
        },
    )
    assert verify.status_code == 200, verify.text
    reset_token = verify.json()["reset_token"]

    reset = client.post(
        "/api/auth/recovery/reset-password",
        json={
            "scope": "admin",
            "reset_token": reset_token,
            "new_password": "newpassword123",
        },
    )
    assert reset.status_code == 200, reset.text

    login = client.post(
        "/api/auth/login",
        data={"username": "admin@example.com", "password": "newpassword123"},
    )
    assert login.status_code == 200, login.text


def test_passkey_register_requires_recovery_or_password():
    os.environ["APP_ENV"] = "dev"
    client = _build_client()

    blocked = client.post(
        "/api/auth/passkey/register/start",
        json={"email": "admin@example.com", "device_label": "test"},
    )
    assert blocked.status_code == 428

    allowed = client.post(
        "/api/auth/passkey/register/start",
        json={
            "email": "admin@example.com",
            "device_label": "test",
            "password": "oldpassword123",
        },
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json().get("registration_token")
