from __future__ import annotations

import base64
import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth import get_password_hash
from backend.auth_router import router as auth_router
from backend.database import Base, SessionLocal as GlobalSessionLocal, get_db
from backend.marketplace.models import UserActiveSession
from backend.models import PasskeyCredential, User


def _build_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    GlobalSessionLocal.configure(bind=engine)
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

    # Keep this test deterministic regardless of shared session policy state.
    db = next(client.app.dependency_overrides[get_db]())
    try:
        user = db.query(User).filter(User.email == "admin@example.com").first()
        assert user is not None
        db.query(UserActiveSession).filter(UserActiveSession.user_id == int(user.id)).delete()
        db.commit()
    finally:
        db.close()

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


def test_passkey_login_start_returns_409_for_malformed_stored_credential_id():
    os.environ["APP_ENV"] = "dev"
    client = _build_client()

    # Simulate legacy/corrupted credential data that is not valid base64url.
    db = next(client.app.dependency_overrides[get_db]())
    try:
        user = db.query(User).filter(User.email == "admin@example.com").first()
        assert user is not None
        user.passkey_enabled = True
        user.passkey_credential_id = "not-base64url-@@@"
        db.add(user)
        db.commit()
    finally:
        db.close()

    start = client.post(
        "/api/auth/passkey/login/start",
        json={"email": "admin@example.com"},
    )
    assert start.status_code == 409, start.text
    assert "패스키" in start.json().get("detail", "")


def test_passkey_login_start_returns_options_for_valid_credential_id():
    os.environ["APP_ENV"] = "dev"
    client = _build_client()

    db = next(client.app.dependency_overrides[get_db]())
    try:
        user = db.query(User).filter(User.email == "admin@example.com").first()
        assert user is not None
        user.passkey_enabled = True
        user.passkey_credential_id = base64.urlsafe_b64encode(b"cred-123").decode("utf-8").rstrip("=")
        db.add(
            PasskeyCredential(
                user_id=int(user.id),
                credential_id=base64.urlsafe_b64encode(b"cred-123").decode("utf-8").rstrip("="),
                public_key=base64.urlsafe_b64encode(b"pubkey-123").decode("utf-8").rstrip("="),
                device_label="device-a",
                sign_count=0,
                transports="internal",
            )
        )
        db.add(
            PasskeyCredential(
                user_id=int(user.id),
                credential_id=base64.urlsafe_b64encode(b"cred-456").decode("utf-8").rstrip("="),
                public_key=base64.urlsafe_b64encode(b"pubkey-456").decode("utf-8").rstrip("="),
                device_label="device-b",
                sign_count=0,
                transports="internal",
            )
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    start = client.post(
        "/api/auth/passkey/login/start",
        json={"email": "admin@example.com"},
    )
    assert start.status_code == 200, start.text
    payload = start.json()
    options = payload.get("options") or {}
    assert options.get("rpId")
    assert isinstance(options.get("allowCredentials"), list)
    assert len(options.get("allowCredentials")) == 2


def test_passkey_credentials_list_and_delete_roundtrip():
    os.environ["APP_ENV"] = "dev"
    os.environ["AUTH_PASSKEY_ONLY"] = "false"
    client = _build_client()

    login = client.post(
        "/api/auth/login",
        data={"username": "admin@example.com", "password": "oldpassword123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    cred1 = base64.urlsafe_b64encode(b"cred-a").decode("utf-8").rstrip("=")
    cred2 = base64.urlsafe_b64encode(b"cred-b").decode("utf-8").rstrip("=")
    db = next(client.app.dependency_overrides[get_db]())
    try:
        user = db.query(User).filter(User.email == "admin@example.com").first()
        assert user is not None
        user.passkey_enabled = True
        user.passkey_credential_id = cred1
        user.passkey_public_key = base64.urlsafe_b64encode(b"pub-a").decode("utf-8").rstrip("=")
        user.passkey_device_label = "device-a"
        db.add(
            PasskeyCredential(
                user_id=int(user.id),
                credential_id=cred1,
                public_key=base64.urlsafe_b64encode(b"pub-a").decode("utf-8").rstrip("="),
                device_label="device-a",
                sign_count=0,
                transports="internal",
            )
        )
        db.add(
            PasskeyCredential(
                user_id=int(user.id),
                credential_id=cred2,
                public_key=base64.urlsafe_b64encode(b"pub-b").decode("utf-8").rstrip("="),
                device_label="device-b",
                sign_count=0,
                transports="internal",
            )
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    listed = client.get("/api/auth/passkey/credentials", headers=headers)
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    credential_ids = [item["credential_id"] for item in payload.get("credentials", [])]
    assert cred1 in credential_ids
    assert cred2 in credential_ids

    deleted = client.delete(f"/api/auth/passkey/credentials/{cred1}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json().get("deleted") is True
    assert deleted.json().get("remaining_count") == 1

    listed_after = client.get("/api/auth/passkey/credentials", headers=headers)
    assert listed_after.status_code == 200, listed_after.text
    credential_ids_after = [item["credential_id"] for item in listed_after.json().get("credentials", [])]
    assert cred1 not in credential_ids_after
    assert cred2 in credential_ids_after
