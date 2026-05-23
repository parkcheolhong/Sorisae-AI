from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from backend.services.auth_identity_provider import IdentityProviderConfigurationError, resolve_identity_provider
from backend.secret_store import read_secret_env

router = APIRouter()
_identity_session_store: dict[str, dict[str, Any]] = {}


def _resolve_identity_provider_name() -> str:
    requested = str(read_secret_env("IDENTITY_PROVIDER", "mock-carrier") or "").strip().lower()
    return resolve_identity_provider(requested).provider_name


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class IdentityStartRequest(BaseModel):
    scope: str = "admin"
    purpose: str = "password_reset"
    user_hint: EmailStr


class IdentityStartResponse(BaseModel):
    session_token: str
    provider: str
    redirect_url: str
    expires_at: datetime
    callback_url: str
    request_payload: Dict[str, Any]


class IdentityCompleteRequest(BaseModel):
    session_token: str
    verification_code: str
    phone: str | None = None
    name: str | None = None
    birth: str | None = None


class IdentityCompleteResponse(BaseModel):
    verified: bool
    scope: str
    purpose: str
    provider: str
    ci_hash: str
    di_hash: str
    phone_last4: str
    provider_result_payload: Dict[str, Any]


@router.post("/start", response_model=IdentityStartResponse)
def start_identity_verification(payload: IdentityStartRequest):
    provider = resolve_identity_provider(_resolve_identity_provider_name())
    try:
        started = provider.start_verification(
            scope=payload.scope,
            purpose=payload.purpose,
            user_hint=payload.user_hint,
        )
    except IdentityProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _identity_session_store[started.session_token] = {
        "scope": payload.scope,
        "purpose": payload.purpose,
        "user_hint": payload.user_hint,
        "verification_code": started.verification_code,
        "expires_at": started.expires_at,
        "provider": _resolve_identity_provider_name(),
        "request_payload": started.request_payload,
        "callback_url": started.callback_url,
    }
    return {
        "session_token": started.session_token,
        "provider": str(_identity_session_store[started.session_token].get("provider") or started.provider),
        "redirect_url": started.redirect_url,
        "expires_at": started.expires_at,
        "callback_url": started.callback_url,
        "request_payload": started.request_payload,
    }


@router.post("/complete", response_model=IdentityCompleteResponse)
def complete_identity_verification(payload: IdentityCompleteRequest):
    state = _identity_session_store.get(payload.session_token)
    if not state:
        raise HTTPException(status_code=404, detail="본인확인 세션을 찾을 수 없습니다")

    expires_at = state.get("expires_at")
    if not isinstance(expires_at, datetime) or expires_at <= datetime.utcnow():
        _identity_session_store.pop(payload.session_token, None)
        raise HTTPException(status_code=410, detail="본인확인 세션이 만료되었습니다")

    expected_code = str(state.get("verification_code") or "")
    if payload.verification_code.strip() != expected_code:
        raise HTTPException(status_code=401, detail="본인확인 코드가 올바르지 않습니다")

    provider = resolve_identity_provider(str(state.get("provider") or _resolve_identity_provider_name()))
    try:
        completed = provider.complete_verification(payload.model_dump())
    except IdentityProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "verified": completed.verified,
        "scope": str(state.get("scope") or "admin"),
        "purpose": str(state.get("purpose") or "password_reset"),
        "provider": completed.provider,
        "ci_hash": _sha256(completed.ci),
        "di_hash": _sha256(completed.di),
        "phone_last4": completed.phone[-4:],
        "provider_result_payload": completed.provider_result_payload,
    }
