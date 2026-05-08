import importlib
import sys
import types
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


class _FakeQuery:
    def __init__(self, user):
        self._user = user

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._user


class _FakeDB:
    def __init__(self, user):
        self._user = user
        self.added = []
        self.committed = False

    def query(self, model):
        return _FakeQuery(self._user)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.committed = True


def _load_auth_router(monkeypatch):
    sys.modules.pop("backend.auth_router", None)

    fake_database = types.ModuleType("backend.database")
    fake_database.get_db = lambda: None

    fake_models = types.ModuleType("backend.models")

    class _StubUser:
        id = "id"
        email = "email"
        username = "username"

    fake_models.User = _StubUser

    monkeypatch.setitem(sys.modules, "backend.database", fake_database)
    monkeypatch.setitem(sys.modules, "backend.models", fake_models)
    return importlib.import_module("backend.auth_router")


def test_admin_tokens_expire_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_NON_EXPIRING_ADMIN_TOKENS", raising=False)
    auth_router = _load_auth_router(monkeypatch)
    admin_user = SimpleNamespace(is_admin=True, is_superuser=False)

    assert auth_router._should_issue_non_expiring_admin_token(admin_user) is False

    monkeypatch.setenv("ALLOW_NON_EXPIRING_ADMIN_TOKENS", "true")
    auth_router = _load_auth_router(monkeypatch)
    assert auth_router._should_issue_non_expiring_admin_token(admin_user) is True


def test_start_password_recovery_uses_random_verification_code(monkeypatch):
    auth_router = _load_auth_router(monkeypatch)
    auth_router._password_recovery_store.clear()
    monkeypatch.setattr(auth_router, "randbelow", lambda upper_bound: 123456)
    db = _FakeDB(SimpleNamespace(id=7, is_admin=True, is_superuser=False))

    response = auth_router.start_password_recovery(
        auth_router.PasswordRecoveryStartRequest(
            scope="admin",
            user_hint="admin@example.com",
        ),
        db,
    )

    session_state = auth_router._password_recovery_store[response["recovery_session_token"]]
    assert session_state["verification_code"] == "123456"
    assert session_state["verification_code"] != "000000"


def test_password_recovery_verify_identity_limits_failed_attempts(monkeypatch):
    auth_router = _load_auth_router(monkeypatch)
    auth_router._password_recovery_store.clear()
    recovery_session_token = "recovery_test"
    auth_router._password_recovery_store[recovery_session_token] = {
        "user_id": 1,
        "scope": "admin",
        "verified": False,
        "verification_code": "654321",
        "verification_attempts": 0,
        "expires_at": datetime.utcnow() + timedelta(minutes=5),
    }
    payload = auth_router.PasswordRecoveryVerifyIdentityRequest(
        recovery_session_token=recovery_session_token,
        identity_session_token="identity-proof",
        verification_code="000000",
    )

    for _ in range(auth_router._PASSWORD_RECOVERY_MAX_VERIFY_ATTEMPTS - 1):
        with pytest.raises(HTTPException) as exc_info:
            auth_router.verify_password_recovery_identity(payload)
        assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        auth_router.verify_password_recovery_identity(payload)
    assert exc_info.value.status_code == 429
    assert recovery_session_token not in auth_router._password_recovery_store


def test_reset_password_requires_verified_identity(monkeypatch):
    auth_router = _load_auth_router(monkeypatch)
    auth_router._password_recovery_store.clear()
    auth_router._password_recovery_store["recovery_test"] = {
        "user_id": 1,
        "scope": "admin",
        "verified": False,
        "reset_token": "reset_token",
        "reset_expires_at": datetime.utcnow() + timedelta(minutes=5),
        "expires_at": datetime.utcnow() + timedelta(minutes=5),
    }

    with pytest.raises(HTTPException) as exc_info:
        auth_router.reset_password_via_recovery(
            auth_router.PasswordRecoveryResetRequest(
                scope="admin",
                reset_token="reset_token",
                new_password="new-password-123",
            ),
            _FakeDB(SimpleNamespace(id=1, hashed_password="old")),
        )

    assert exc_info.value.status_code == 403


def test_reset_password_updates_hash_and_clears_session(monkeypatch):
    auth_router = _load_auth_router(monkeypatch)
    auth_router._password_recovery_store.clear()
    user = SimpleNamespace(id=1, hashed_password="old")
    db = _FakeDB(user)
    auth_router._password_recovery_store["recovery_test"] = {
        "user_id": 1,
        "scope": "admin",
        "verified": True,
        "identity_session_token": "identity-proof",
        "reset_token": "reset_token",
        "reset_expires_at": datetime.utcnow() + timedelta(minutes=5),
        "expires_at": datetime.utcnow() + timedelta(minutes=5),
    }

    response = auth_router.reset_password_via_recovery(
        auth_router.PasswordRecoveryResetRequest(
            scope="admin",
            reset_token="reset_token",
            new_password="new-password-123",
        ),
        db,
    )

    assert response == {"reset": True, "must_relogin": True}
    assert user.hashed_password != "old"
    assert db.committed is True
    assert "recovery_test" not in auth_router._password_recovery_store
