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
            username="regular_user",
            email="user@example.com",
            hashed_password=get_password_hash("oldpassword123"),
            is_admin=False,
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


def test_user_recovery_email_otp_and_password_reset():
    os.environ["APP_ENV"] = "dev"
    client = _build_client()

    start = client.post(
        "/api/auth/recovery/start",
        json={
            "scope": "user",
            "user_hint": "user@example.com",
            "verification_channel": "email",
        },
    )
    assert start.status_code == 200, start.text
    start_payload = start.json()
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
            "scope": "user",
            "reset_token": reset_token,
            "new_password": "newpassword456",
        },
    )
    assert reset.status_code == 200, reset.text

    login_old = client.post(
        "/api/auth/login",
        data={"username": "user@example.com", "password": "oldpassword123"},
    )
    assert login_old.status_code == 401

    login_new = client.post(
        "/api/auth/login",
        data={"username": "user@example.com", "password": "newpassword456"},
    )
    assert login_new.status_code == 200, login_new.text
