import importlib
import sys
import types

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


def test_start_password_recovery_delegates_to_otp_service(monkeypatch):
    """복구 시작은 OTP 서비스(contact_verification)에 위임한다.

    검증코드 난수성(secrets.randbelow)·시도 제한은 OTP 서비스 SSOT가 담당하므로
    auth_router는 (1) 세션 위임 (2) verification_code_required 다음 단계 반환만 책임진다.
    """
    auth_router = _load_auth_router(monkeypatch)
    auth_router._password_recovery_store.clear()

    import backend.services.contact_verification as cv

    captured: dict = {}

    def _fake_start(**kwargs):
        captured.update(kwargs)
        return {
            "sessionToken": "sess-recovery-1",
            "expiresAt": "2099-01-01T00:00:00",
            "maskedTarget": "a***@example.com",
            "verificationChannel": "email",
            "devOtpHint": None,
        }

    monkeypatch.setattr(cv, "start_verification_session", _fake_start)
    db = _FakeDB(
        SimpleNamespace(
            id=7, email="admin@example.com", username="admin",
            is_admin=True, is_superuser=False, phone_number=None,
        )
    )

    response = auth_router.start_password_recovery(
        auth_router.PasswordRecoveryStartRequest(
            scope="admin",
            user_hint="admin@example.com",
        ),
        db,
    )

    assert response["recovery_session_token"] == "sess-recovery-1"
    assert response["next_action"] == "verification_code_required"
    assert captured["purpose"] == "admin_recovery"


def test_password_recovery_verify_identity_maps_rate_limit_to_429(monkeypatch):
    """OTP 서비스가 시도 초과(PermissionError)를 올리면 429로, 코드 불일치(ValueError)는 401로 매핑."""
    auth_router = _load_auth_router(monkeypatch)
    auth_router._password_recovery_store.clear()

    import backend.services.contact_verification as cv

    payload = auth_router.PasswordRecoveryVerifyIdentityRequest(
        recovery_session_token="recovery_test",
        identity_session_token="identity-proof",
        verification_code="000000",
    )

    def _raise_bad_code(token, code):
        raise ValueError("인증 코드가 일치하지 않습니다")

    monkeypatch.setattr(cv, "verify_session_code", _raise_bad_code)
    with pytest.raises(HTTPException) as exc_info:
        auth_router.verify_password_recovery_identity(payload)
    assert exc_info.value.status_code == 401

    def _raise_rate_limited(token, code):
        raise PermissionError("인증 시도 횟수를 초과했습니다")

    monkeypatch.setattr(cv, "verify_session_code", _raise_rate_limited)
    with pytest.raises(HTTPException) as exc_info:
        auth_router.verify_password_recovery_identity(payload)
    assert exc_info.value.status_code == 429


def test_reset_password_requires_verified_identity(monkeypatch):
    auth_router = _load_auth_router(monkeypatch)
    auth_router._password_recovery_store.clear()
    auth_router._password_recovery_store["recovery_test"] = {
        "user_id": 1,
        "scope": "admin",
        "verified": False,
        "reset_token": "reset_token",

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
