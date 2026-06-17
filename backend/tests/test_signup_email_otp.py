from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth_router import router as auth_router
from backend.database import Base, get_db


def _build_client() -> TestClient:
    os.environ.pop("ALLOW_UNVERIFIED_SIGNUP", None)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
    return TestClient(app)


def test_signup_requires_email_otp_by_default():
    client = _build_client()
    blocked = client.post(
        "/api/auth/signup",
        json={
            "username": "blocked_user",
            "email": "blocked@example.com",
            "password": "password123",
            "preferred_language": "ko",
            "country_code": "KR",
        },
    )
    assert blocked.status_code == 428


def test_signup_confirm_creates_user_after_email_otp():
    client = _build_client()
    start = client.post(
        "/api/auth/signup/request-code",
        json={
            "username": "otp_user",
            "email": "otp_user@example.com",
            "password": "password123",
            "preferred_language": "ja",
            "country_code": "JP",
            "verificationChannel": "email",
        },
    )
    assert start.status_code == 200, start.text
    payload = start.json()
    assert payload.get("devOtpHint")

    confirm = client.post(
        "/api/auth/signup/confirm",
        json={
            "signupSessionToken": payload["signupSessionToken"],
            "verificationCode": payload["devOtpHint"],
            "preferred_language": "ja",
            "country_code": "JP",
        },
    )
    assert confirm.status_code == 201, confirm.text
    body = confirm.json()
    assert body["email"] == "otp_user@example.com"
    assert body["preferred_language"] == "ja"
    assert body["country_code"] == "JP"


def test_signup_confirm_allows_profile_language_country_update_at_verify_step():
    client = _build_client()
    start = client.post(
        "/api/auth/signup/request-code",
        json={
            "username": "otp_profile_user",
            "email": "otp_profile_user@example.com",
            "password": "password123",
            "preferred_language": "ko",
            "country_code": "KR",
            "verificationChannel": "email",
        },
    )
    assert start.status_code == 200, start.text
    payload = start.json()

    confirm = client.post(
        "/api/auth/signup/confirm",
        json={
            "signupSessionToken": payload["signupSessionToken"],
            "verificationCode": payload["devOtpHint"],
            "preferred_language": "fr",
            "country_code": "FR",
        },
    )
    assert confirm.status_code == 201, confirm.text
    body = confirm.json()
    assert body["preferred_language"] == "fr"
    assert body["country_code"] == "FR"


def test_signup_confirm_creates_user_after_phone_otp():
    client = _build_client()
    start = client.post(
        "/api/auth/signup/request-code",
        json={
            "username": "phone_otp_user",
            "email": "phone_otp_user@example.com",
            "password": "password123",
            "preferred_language": "ko",
            "country_code": "KR",
            "phone_number": "+82-10-1234-5678",
            "verificationChannel": "phone",
        },
    )
    assert start.status_code == 200, start.text
    payload = start.json()
    assert payload["verificationChannel"] == "phone"
    assert payload.get("devOtpHint")

    confirm = client.post(
        "/api/auth/signup/confirm",
        json={
            "signupSessionToken": payload["signupSessionToken"],
            "verificationCode": payload["devOtpHint"],
            "preferred_language": "ko",
            "country_code": "KR",
        },
    )
    assert confirm.status_code == 201, confirm.text
    body = confirm.json()
    assert body["email"] == "phone_otp_user@example.com"
    assert body["phone_number"] == "+82-10-1234-5678"


def test_signup_phone_channel_requires_phone_number():
    client = _build_client()
    response = client.post(
        "/api/auth/signup/request-code",
        json={
            "username": "phone_missing_user",
            "email": "phone_missing_user@example.com",
            "password": "password123",
            "preferred_language": "ko",
            "country_code": "KR",
            "verificationChannel": "phone",
        },
    )
    assert response.status_code == 400
    assert "연락처" in response.json()["detail"]
