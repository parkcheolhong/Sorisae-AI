from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
import base64
import logging
import os

logger = logging.getLogger(__name__)
from urllib.parse import urlparse
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status  # pyright: ignore[reportMissingImports]
from fastapi.security import OAuth2PasswordRequestForm  # pyright: ignore[reportMissingImports]
from fastapi.responses import RedirectResponse  # pyright: ignore[reportMissingImports]
from typing import Any, Optional
import re
from pydantic import BaseModel, ConfigDict, EmailStr  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import Session  # pyright: ignore[reportMissingImports]
from backend.time_utils import utcnow
from backend.secret_store import read_secret_env
from webauthn import (  # pyright: ignore[reportMissingImports]
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (  # pyright: ignore[reportMissingImports]
    PublicKeyCredentialType,
    AuthenticatorTransport,
    AuthenticatorAssertionResponse,
    AuthenticatorAttestationResponse,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    RegistrationCredential,
    AuthenticationCredential,
    UserVerificationRequirement,
    ResidentKeyRequirement,
)

from backend.auth import (
    clear_active_session,
    create_access_token,
    get_current_user,
    get_password_hash,
    oauth2_scheme,
    register_issued_token,
    resolve_token_session_id,
    set_active_session,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from backend.database import get_db
from backend.models import PasskeyCredential, User
from backend.marketplace.models import UserActiveSession
from backend.security_gates import require_login_quota, require_otp_send_quota
from backend.user_profile import normalize_country_code, normalize_preferred_language

router = APIRouter()

DUPLICATE_LOGIN_BLOCK_DETAIL = (
    "이미 다른 기기 또는 세션에서 로그인 상태가 남아 있습니다. "
    "현재 사용 중인 기기가 없다면 계정 복구(본인확인) 후 세션 해제 뒤 다시 시도해 주세요."
)


def _should_issue_non_expiring_session_token(user: User) -> bool:
    # 세션 정책: 사용자 명시 로그아웃 전까지 유지(토큰 만료 미적용).
    # 단일 세션 SID 게이트 + /logout 무효화가 세션 종료 기준이다.
    return True


def _has_active_session_in_db(db: Session, user_id: int) -> bool:
    uid = int(user_id or 0)
    if uid <= 0:
        return False
    try:
        row = (
            db.query(UserActiveSession)
            .filter(UserActiveSession.user_id == uid)
            .first()
        )
        return row is not None
    except Exception as exc:
        logger.warning("[AUTH] 활성 세션 DB 조회 실패 user_id=%s", uid, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="세션 검증을 일시적으로 수행할 수 없습니다. 잠시 후 다시 시도해주세요.",
        ) from exc


def _set_active_session_in_db(db: Session, user_id: int, session_id: str) -> None:
    uid = int(user_id or 0)
    sid = str(session_id or "").strip()
    if uid <= 0 or not sid:
        raise HTTPException(status_code=500, detail="유효한 세션 식별자를 생성하지 못했습니다")

    row = (
        db.query(UserActiveSession)
        .filter(UserActiveSession.user_id == uid)
        .first()
    )
    if row is None:
        db.add(UserActiveSession(user_id=uid, session_id=sid))
    else:
        row.session_id = sid
    db.commit()

    # Redis/session helper 캐시와 동기화를 맞추기 위해 공용 helper도 함께 갱신한다.
    set_active_session(uid, sid)


# ---------- 스키마 ----------
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    member_type: str = "individual"
    business_name: Optional[str] = None
    business_registration_number: Optional[str] = None
    representative_name: Optional[str] = None
    preferred_language: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None


class UserProfileUpdate(BaseModel):
    preferred_language: Optional[str] = None
    country_code: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool = False
    is_superuser: bool = False
    is_active: bool = True
    full_name: Optional[str] = None
    member_type: str = "individual"
    business_name: Optional[str] = None
    business_registration_number: Optional[str] = None
    representative_name: Optional[str] = None
    preferred_language: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class SocialLoginStartResponse(BaseModel):
    provider: str
    authorization_url: str
    callback_url: str


class PasskeyRegistrationStartRequest(BaseModel):
    email: EmailStr
    device_label: str | None = None
    recovery_reset_token: str | None = None
    password: str | None = None


class PasskeyRegistrationStartResponse(BaseModel):
    registration_token: str
    options: dict
    device_label: str | None = None


class PasskeyRegistrationFinishRequest(BaseModel):
    registration_token: str
    credential: dict


class PasskeyLoginStartRequest(BaseModel):
    email: EmailStr


class PasskeyLoginStartResponse(BaseModel):
    options: dict


class PasskeyLoginFinishRequest(BaseModel):
    email: EmailStr
    credential: dict


class PasskeyCredentialItem(BaseModel):
    credential_id: str
    device_label: str | None = None
    created_at: datetime | None = None
    last_used_at: datetime | None = None


class PasskeyCredentialListResponse(BaseModel):
    credentials: list[PasskeyCredentialItem]


_passkey_registration_store: dict[str, dict[str, object]] = {}
_passkey_login_store: dict[str, dict[str, object]] = {}
_default_social_login_providers = ("google", "kakao", "naver")
_social_login_callback_path = "auth/callback"
_social_login_state_store: dict[str, dict[str, object]] = {}


def _resolve_enabled_social_login_providers() -> set[str]:
    raw = str(read_secret_env("SOCIAL_LOGIN_PROVIDERS", "") or "").strip()
    if not raw:
        return set(_default_social_login_providers)
    parsed = {
        token.strip().lower()
        for token in raw.split(",")
        if token and token.strip()
    }
    valid = {"google", "kakao", "naver"}
    enabled = parsed & valid
    if not enabled:
        return set(_default_social_login_providers)
    return enabled


def _user_may_use_admin_portal(user: Any) -> bool:
    if getattr(user, "is_admin", False) or getattr(user, "is_superuser", False):
        return True
    try:
        from backend.marketplace.worldlinco_sales_commission import resolve_regional_manager_for_user

        return resolve_regional_manager_for_user(int(getattr(user, "id", 0) or 0)) is not None
    except Exception:
        return False


def _is_passkey_only_auth_enabled() -> bool:
    raw = str(read_secret_env("AUTH_PASSKEY_ONLY", "true") or "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _load_user_passkey_credentials(db: Session, user_id: int) -> list[PasskeyCredential]:
    return (
        db.query(PasskeyCredential)
        .filter(PasskeyCredential.user_id == int(user_id))
        .order_by(PasskeyCredential.created_at.asc(), PasskeyCredential.id.asc())
        .all()
    )


def _user_has_passkey(db: Session, user: User) -> bool:
    if bool(getattr(user, "passkey_credential_id", None)) and bool(getattr(user, "passkey_enabled", False)):
        return True
    return len(_load_user_passkey_credentials(db, int(user.id))) > 0


def _assert_verified_recovery_reset_token_any_scope(
    reset_token: str,
    *,
    user_id: int | None = None,
) -> tuple[str, dict[str, object]]:
    last_error: HTTPException | None = None
    for scope in ("admin", "user"):
        try:
            return _assert_verified_recovery_reset_token(
                reset_token,
                scope=scope,
                user_id=user_id,
            )
        except HTTPException as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise HTTPException(status_code=404, detail="재설정 토큰을 찾을 수 없습니다")


def _issue_passkey_challenge() -> str:
    return token_urlsafe(24)


def _to_base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode('utf-8').rstrip('=')


def _from_base64url(value: str) -> bytes:
    raw = str(value or "").strip()
    normalized = raw + '=' * ((4 - len(raw) % 4) % 4)
    try:
        return base64.b64decode(normalized.encode('utf-8'), altchars=b"-_", validate=True)
    except Exception as exc:
        raise ValueError("invalid base64url payload") from exc


def _build_registration_credential(payload: dict) -> RegistrationCredential:
    response = payload.get("response") or {}
    return RegistrationCredential(
        id=str(payload.get("id") or ""),
        raw_id=_from_base64url(str(payload.get("rawId") or "")),
        response=AuthenticatorAttestationResponse(
            client_data_json=_from_base64url(str(response.get("clientDataJSON") or "")),
            attestation_object=_from_base64url(str(response.get("attestationObject") or "")),
        ),
        type="public-key",
    )


def _build_authentication_credential(payload: dict) -> AuthenticationCredential:
    response = payload.get("response") or {}
    user_handle = response.get("userHandle")
    return AuthenticationCredential(
        id=str(payload.get("id") or ""),
        raw_id=_from_base64url(str(payload.get("rawId") or "")),
        response=AuthenticatorAssertionResponse(
            client_data_json=_from_base64url(str(response.get("clientDataJSON") or "")),
            authenticator_data=_from_base64url(str(response.get("authenticatorData") or "")),
            signature=_from_base64url(str(response.get("signature") or "")),
            user_handle=_from_base64url(str(user_handle)) if user_handle else None,
        ),
        type="public-key",
    )


def _extract_credential_id_from_auth_payload(payload: dict) -> str:
    return str(payload.get("id") or "").strip()


def _normalize_social_login_provider(provider: str) -> str:
    normalized = str(provider or "").strip().lower()
    enabled_providers = _resolve_enabled_social_login_providers()
    if normalized not in enabled_providers:
        raise HTTPException(status_code=404, detail="지원하지 않는 소셜 로그인 제공자입니다")
    return normalized


def _resolve_social_login_redirect_uri(redirect_uri: str) -> str:
    normalized = str(redirect_uri or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="redirect_uri 가 필요합니다")

    parsed = urlparse(normalized)
    scheme = parsed.scheme.lower()
    resolved_path = f"{parsed.hostname or ''}{parsed.path}".lstrip("/").lower()
    if scheme not in {"worldlinco", "worldlingo", "com.parkcheolhong.worldlinco"} or resolved_path != _social_login_callback_path:
        raise HTTPException(status_code=400, detail="허용되지 않은 redirect_uri 입니다")
    return normalized


def _is_legacy_domain_host(host: str) -> bool:
    normalized = str(host or "").strip().lower()
    if not normalized:
        return False
    base = normalized.split(":", 1)[0]
    return base in {
        "devanalysis114.com",
        "www.devanalysis114.com",
        "xn--114-2p7l635dz3bh5j.com",
        "www.xn--114-2p7l635dz3bh5j.com",
        "개발분석114.com",
        "www.개발분석114.com",
    }


def _resolve_social_callback_base_url(request: Request) -> str:
    configured = str(read_secret_env("SOCIAL_LOGIN_CALLBACK_BASE_URL", "") or "").strip().rstrip("/")
    forwarded_proto = str(request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    forwarded_host = str(request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc or "").split(",")[0].strip()
    request_base_url = (
        f"{forwarded_proto}://{forwarded_host}".rstrip("/")
        if forwarded_host
        else f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    )

    if configured:
        configured_host = _origin_host(configured)
        request_host = _origin_host(request_base_url)
        if (
            configured_host
            and request_host
            and _is_legacy_domain_host(configured_host)
            and not _is_legacy_domain_host(request_host)
            and not _is_loopback_host(request_host)
        ):
            logger.warning(
                "SOCIAL_LOGIN_CALLBACK_BASE_URL uses legacy host '%s'; using request host '%s' instead",
                configured_host,
                request_host,
            )
            return request_base_url
        return configured

    return request_base_url


def _social_provider_config(provider: str) -> dict[str, str]:
    normalized = _normalize_social_login_provider(provider)
    if normalized == "google":
        return {
            "client_id_env": "GOOGLE_CLIENT_ID",
            "client_secret_env": "GOOGLE_CLIENT_SECRET",
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
            "scope": "openid email profile",
        }
    if normalized == "naver":
        return {
            "client_id_env": "NAVER_CLIENT_ID",
            "client_secret_env": "NAVER_CLIENT_SECRET",
            "authorization_url": "https://nid.naver.com/oauth2.0/authorize",
            "token_url": "https://nid.naver.com/oauth2.0/token",
            "userinfo_url": "https://openapi.naver.com/v1/nid/me",
            "scope": "name email profile",
        }
    return {
        "client_id_env": "KAKAO_CLIENT_ID",
        "client_secret_env": "KAKAO_CLIENT_SECRET",
        "authorization_url": "https://kauth.kakao.com/oauth/authorize",
        "token_url": "https://kauth.kakao.com/oauth/token",
        "userinfo_url": "https://kapi.kakao.com/v2/user/me",
        "scope": "account_email profile_nickname profile_image",
    }


def _resolve_social_provider_credentials(provider: str) -> tuple[str, str]:
    config = _social_provider_config(provider)
    client_id = read_secret_env(config["client_id_env"], default="").strip()
    client_secret = read_secret_env(config["client_secret_env"], default="").strip()
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail=f"{provider.upper()} 소셜 로그인 운영값이 없습니다. {config['client_id_env']} / {config['client_secret_env']} 를 설정하세요.",
        )
    return client_id, client_secret


def _build_social_callback_url(request: Request, provider: str) -> str:
    base_url = _resolve_social_callback_base_url(request)
    return f"{base_url}/api/auth/social/{provider}/callback"


def _build_social_authorization_url(provider: str, *, client_id: str, callback_url: str, state: str) -> str:
    config = _social_provider_config(provider)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": callback_url,
        "scope": config["scope"],
        "state": state,
    }
    if provider == "google":
        params["access_type"] = "offline"
        params["prompt"] = "consent"
    return f"{config['authorization_url']}?{urlencode(params)}"


def _store_social_login_state(provider: str, redirect_uri: str, callback_url: str) -> str:
    state = token_urlsafe(24)
    _social_login_state_store[state] = {
        "provider": provider,
        "redirect_uri": redirect_uri,
        "callback_url": callback_url,
        "created_at": utcnow().isoformat(),
    }
    return state


def _pop_social_login_state(state: str) -> dict[str, object]:
    stored = _social_login_state_store.pop(state, None)
    if not stored:
        raise HTTPException(status_code=404, detail="소셜 로그인 state 를 찾을 수 없습니다")
    return stored


def _cleanup_social_login_state_store() -> None:
    if not _social_login_state_store:
        return
    cutoff = utcnow() - timedelta(minutes=15)
    stale_states = []
    for state, payload in _social_login_state_store.items():
        created_raw = str(payload.get("created_at") or "").strip()
        try:
            created_at = datetime.fromisoformat(created_raw)
        except Exception:
            stale_states.append(state)
            continue
        if created_at < cutoff:
            stale_states.append(state)
    for state in stale_states:
        _social_login_state_store.pop(state, None)


def _request_form_encoded(client: httpx.Client, method: str, url: str, data: dict[str, str], headers: dict[str, str]) -> dict[str, Any]:
    response = client.request(method, url, data=data, headers=headers)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="소셜 로그인 provider 응답 형식이 올바르지 않습니다")
    return payload


def _fetch_social_provider_userinfo(provider: str, access_token: str, token_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    config = _social_provider_config(provider)
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get(config["userinfo_url"], headers=headers)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="소셜 로그인 사용자 정보를 해석할 수 없습니다")
    if provider == "naver":
        return dict(payload.get("response") or {})
    if provider == "kakao":
        profile = dict((payload.get("kakao_account") or {}).get("profile") or {})
        account = dict(payload.get("kakao_account") or {})
        return {
            "id": payload.get("id"),
            "email": account.get("email"),
            "name": profile.get("nickname") or profile.get("name") or account.get("profile_nickname"),
            "nickname": profile.get("nickname"),
            "profile_image": profile.get("profile_image_url") or profile.get("thumbnail_image_url"),
        }
    return payload


def _extract_social_identity(provider: str, userinfo: dict[str, Any], token_payload: dict[str, Any]) -> tuple[str, str, str]:
    provider_user_id = str(
        userinfo.get("id")
        or userinfo.get("sub")
        or userinfo.get("response", {}).get("id")
        or token_payload.get("id_token")
        or token_payload.get("access_token")
        or token_urlsafe(8)
    ).strip()
    email = str(
        userinfo.get("email")
        or userinfo.get("response", {}).get("email")
        or f"{provider}.{provider_user_id}@worldlinco.social"
    ).strip().lower()
    display_name = str(
        userinfo.get("name")
        or userinfo.get("nickname")
        or userinfo.get("display_name")
        or userinfo.get("response", {}).get("name")
        or userinfo.get("response", {}).get("nickname")
        or provider_user_id
    ).strip()
    base_username = re.sub(r"[^a-zA-Z0-9_]+", "_", f"{provider}_{provider_user_id or email.split('@')[0]}").strip("_").lower()
    if not base_username:
        base_username = f"{provider}_social_user"
    return email, base_username[:96], display_name


def _get_or_create_social_login_user(
    db: Session,
    provider: str,
    email: str,
    username: str,
    display_name: str,
) -> User:
    user = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if user is None:
        existing_username_count = db.query(User).filter(User.username.like(f"{username}%")).count()
        if existing_username_count:
            username = f"{username}{existing_username_count + 1}"
        user = User(
            email=email,
            username=username,
            full_name=display_name,
            member_type="individual",
            hashed_password=get_password_hash(token_urlsafe(24)),
            is_active=True,
            is_admin=False,
            is_staff=False,
            is_superuser=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    if display_name and not str(user.full_name or "").strip():
        user.full_name = display_name
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _build_social_login_callback_url(
    redirect_uri: str,
    *,
    provider: str,
    access_token: str,
    refresh_token: str,
    id_token: str,
    expires_in: int,
    user: User,
) -> str:
    params = {
        "provider": provider,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "id_token": id_token,
        "expires_in": str(expires_in),
        "email": str(user.email or ""),
        "user_id": str(int(user.id)),
        "username": str(user.username or ""),
        "display_name": str(user.full_name or user.username or provider),
    }
    separator = "&" if "?" in redirect_uri else "?"
    return f"{redirect_uri}{separator}{urlencode(params)}"


@router.get("/social/{provider}/start")
def start_social_login(
    provider: str,
    request: Request,
    redirect_uri: str = Query(...),
    db: Session = Depends(get_db),
):
    normalized_provider = _normalize_social_login_provider(provider)
    normalized_redirect_uri = _resolve_social_login_redirect_uri(redirect_uri)
    client_id, _client_secret = _resolve_social_provider_credentials(normalized_provider)
    callback_url = _build_social_callback_url(request, normalized_provider)
    _cleanup_social_login_state_store()
    state = _store_social_login_state(normalized_provider, normalized_redirect_uri, callback_url)
    authorization_url = _build_social_authorization_url(
        normalized_provider,
        client_id=client_id,
        callback_url=callback_url,
        state=state,
    )
    logger.info("[%s] 소셜 로그인 시작 → %s", normalized_provider, authorization_url)
    return RedirectResponse(url=authorization_url, status_code=status.HTTP_302_FOUND)


@router.get("/social/{provider}/callback")
def finish_social_login(
    provider: str,
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    normalized_provider = _normalize_social_login_provider(provider)
    if error:
        raise HTTPException(status_code=400, detail=f"소셜 로그인 provider 오류: {error_description or error}")
    if not code.strip():
        raise HTTPException(status_code=400, detail="authorization code 가 필요합니다")
    if not state.strip():
        raise HTTPException(status_code=400, detail="state 가 필요합니다")

    state_payload = _pop_social_login_state(state.strip())
    if str(state_payload.get("provider") or "") != normalized_provider:
        raise HTTPException(status_code=400, detail="소셜 로그인 provider state 가 일치하지 않습니다")
    redirect_uri = _resolve_social_login_redirect_uri(str(state_payload.get("redirect_uri") or ""))
    callback_url = str(state_payload.get("callback_url") or "").strip()
    if not callback_url:
        raise HTTPException(status_code=500, detail="소셜 로그인 callback_url 을 찾을 수 없습니다")
    client_id, client_secret = _resolve_social_provider_credentials(normalized_provider)
    provider_config = _social_provider_config(normalized_provider)

    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        token_payload = _request_form_encoded(
            client,
            "POST",
            provider_config["token_url"],
            {
                "grant_type": "authorization_code",
                "code": code.strip(),
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": callback_url,
            },
            {"Content-Type": "application/x-www-form-urlencoded"},
        )

    access_token = str(token_payload.get("access_token") or "").strip()
    if not access_token:
        raise HTTPException(status_code=502, detail="provider access_token 이 비어 있습니다")
    refresh_token = str(token_payload.get("refresh_token") or "").strip()
    id_token = str(token_payload.get("id_token") or "").strip()
    expires_in_raw = token_payload.get("expires_in")
    try:
        expires_in = int(expires_in_raw) if expires_in_raw is not None else ACCESS_TOKEN_EXPIRE_MINUTES * 60
    except Exception:
        expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60

    userinfo = _fetch_social_provider_userinfo(normalized_provider, access_token, token_payload)
    email, username, display_name = _extract_social_identity(normalized_provider, userinfo, token_payload)
    user = _get_or_create_social_login_user(db, normalized_provider, email=email, username=username, display_name=display_name)

    if _has_active_session_in_db(db, int(user.id)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_LOGIN_BLOCK_DETAIL,
        )

    session_id = token_urlsafe(24)
    app_access_token = create_access_token(
        data={"sub": str(user.email or user.username or normalized_provider), "sid": session_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        no_expiry=_should_issue_non_expiring_session_token(user),
    )
    _set_active_session_in_db(db, int(user.id), session_id)
    register_issued_token(app_access_token, str(user.email or user.username or ""))
    final_url = _build_social_login_callback_url(
        redirect_uri,
        provider=normalized_provider,
        access_token=app_access_token,
        refresh_token=refresh_token,
        id_token=id_token,
        expires_in=expires_in,
        user=user,
    )
    logger.info("[%s] 소셜 로그인 완료 → %s", normalized_provider, final_url)
    return RedirectResponse(url=final_url, status_code=status.HTTP_302_FOUND)


def _resolve_passkey_rp_id() -> str:
    requested = str(os.getenv("PASSKEY_RP_ID") or os.getenv("APP_DOMAIN") or os.getenv("PUBLIC_DOMAIN") or "").strip().lower()
    if requested:
        try:
            parsed = urlparse(requested)
            normalized = (parsed.hostname or requested).strip().lower()
            if normalized:
                return normalized
        except Exception:
            pass
        return requested
    return "metanova1004.com"


def _resolve_passkey_rp_name() -> str:
    return str(os.getenv("PASSKEY_RP_NAME") or "DevAnalysis114 Admin").strip() or "DevAnalysis114 Admin"


def _resolve_request_origin(request: Request | None) -> str:
    configured_rp_id = _resolve_passkey_rp_id()
    fallback_origin = str(os.getenv("PASSKEY_EXPECTED_ORIGIN") or f"https://{configured_rp_id}").strip().rstrip("/")
    if request is None:
        return fallback_origin

    explicit_origin = str(request.headers.get("origin") or "").strip().rstrip("/")
    if explicit_origin:
        return explicit_origin

    forwarded_proto = str(request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    forwarded_host = str(request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc or "").split(",")[0].strip()
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
    return fallback_origin


def _origin_host(origin: str) -> str:
    try:
        return str(urlparse(origin).hostname or "").strip().lower()
    except Exception:
        return ""


def _is_loopback_host(host: str) -> bool:
    normalized = str(host or "").strip().lower()
    return normalized in {"localhost", "127.0.0.1", "::1"}


def _normalize_loopback_origin(origin: str) -> str:
    try:
        parsed = urlparse(origin)
        host = str(parsed.hostname or "").strip().lower()
        if host not in {"127.0.0.1", "::1"}:
            return origin
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path or ""
        query = f"?{parsed.query}" if parsed.query else ""
        fragment = f"#{parsed.fragment}" if parsed.fragment else ""
        scheme = parsed.scheme or "http"
        return f"{scheme}://localhost{port}{path}{query}{fragment}".rstrip("/")
    except Exception:
        return origin


def _resolve_passkey_request_context(request: Request | None) -> tuple[str, str]:
    configured_rp_id = _resolve_passkey_rp_id()
    configured_origin = str(os.getenv("PASSKEY_EXPECTED_ORIGIN") or f"https://{configured_rp_id}").strip().rstrip("/")
    request_origin = _resolve_request_origin(request)
    request_host = _origin_host(request_origin)
    configured_host = _origin_host(configured_origin)
    explicit_origin = str(request.headers.get("origin") or "").strip() if request is not None else ""
    forwarded_host = ""
    if request is not None:
        forwarded_host = str(request.headers.get("x-forwarded-host") or "").split(",")[0].strip().lower()

    if _is_loopback_host(request_host):
        normalized_origin = _normalize_loopback_origin(request_origin)
        return "localhost", normalized_origin or "http://localhost"

    if request_host and configured_rp_id in {"", "localhost", "127.0.0.1", "::1"} and (explicit_origin or forwarded_host):
        # Auto-bind RP to the actual non-loopback host when no explicit production RP is configured.
        return request_host, request_origin or f"https://{request_host}"

    if (
        request_host
        and configured_host
        and _is_legacy_domain_host(configured_host)
        and not _is_legacy_domain_host(request_host)
        and not _is_loopback_host(request_host)
    ):
        # When stale legacy domain env values remain, trust the active request host to avoid broken passkey origins.
        return request_host, request_origin or f"https://{request_host}"

    if request_host and (request_host == configured_rp_id or request_host.endswith(f".{configured_rp_id}")):
        return configured_rp_id, request_origin or configured_origin

    return configured_rp_id, configured_origin


class PasswordRecoveryStartRequest(BaseModel):
    scope: str = "admin"
    user_hint: EmailStr
    verification_channel: str = "email"
    phone_number: Optional[str] = None


class PasswordRecoveryStartResponse(BaseModel):
    recovery_session_token: str
    next_action: str
    expires_at: datetime
    masked_target: str
    verification_channel: str
    dev_otp_hint: Optional[str] = None


class PasswordRecoveryVerifyIdentityRequest(BaseModel):
    recovery_session_token: str
    verification_code: str
    identity_session_token: Optional[str] = None


class PasswordRecoveryVerifyIdentityResponse(BaseModel):
    verified: bool
    reset_token: str
    expires_at: datetime


class PasswordRecoveryResetRequest(BaseModel):
    scope: str = "admin"
    reset_token: str
    new_password: str


class PasswordRecoveryResetResponse(BaseModel):
    reset: bool
    must_relogin: bool = True


class PasswordRecoveryClearSessionRequest(BaseModel):
    scope: str = "admin"
    reset_token: str


class PasswordRecoveryClearSessionResponse(BaseModel):
    cleared: bool
    must_relogin: bool = True


class UserPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class UserPasswordChangeResponse(BaseModel):
    changed: bool
    must_relogin: bool = True


class SignupRequestCode(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    member_type: str = "individual"
    business_name: Optional[str] = None
    business_registration_number: Optional[str] = None
    representative_name: Optional[str] = None
    preferred_language: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None
    verificationChannel: str = "email"
    referral_code: Optional[str] = None
    sales_agent_code: Optional[str] = None


class SignupConfirmRequest(BaseModel):
    signupSessionToken: str
    verificationCode: str
    preferred_language: Optional[str] = None
    country_code: Optional[str] = None
    full_name: Optional[str] = None
    referral_code: Optional[str] = None
    sales_agent_code: Optional[str] = None


class SignupRequestCodeResponse(BaseModel):
    signupSessionToken: str
    verificationChannel: str
    maskedTarget: str
    expiresAt: str
    devOtpHint: Optional[str] = None


_password_recovery_store: dict[str, dict[str, object]] = {}


def _issue_recovery_token(prefix: str) -> tuple[str, datetime]:
    from secrets import token_urlsafe

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    return f"{prefix}_{token_urlsafe(24)}", expires_at


def _find_recovery_session_by_reset_token(reset_token: str, *, scope: str) -> tuple[str, dict[str, object]] | None:
    for session_token, session_state in _password_recovery_store.items():
        if session_state.get("reset_token") == reset_token and session_state.get("scope") == scope:
            return session_token, session_state
    return None


def _assert_verified_recovery_reset_token(
    reset_token: str,
    *,
    scope: str,
    user_id: int | None = None,
) -> tuple[str, dict[str, object]]:
    matched = _find_recovery_session_by_reset_token(reset_token, scope=scope)
    if not matched:
        raise HTTPException(status_code=404, detail="재설정 토큰을 찾을 수 없습니다")

    session_token, session_state = matched
    if not session_state.get("verified"):
        raise HTTPException(status_code=403, detail="본인확인이 완료되지 않은 세션입니다")

    reset_expires_at = session_state.get("reset_expires_at")
    if isinstance(reset_expires_at, datetime) and reset_expires_at <= datetime.now(timezone.utc):
        _password_recovery_store.pop(session_token, None)
        raise HTTPException(status_code=410, detail="재설정 토큰이 만료되었습니다")

    if user_id is not None and int(session_state.get("user_id") or 0) != int(user_id):
        raise HTTPException(status_code=403, detail="재설정 토큰이 대상 계정과 일치하지 않습니다")

    return session_token, session_state


def _validate_profile_fields(
    preferred_language: Optional[str],
    country_code: Optional[str],
    *,
    require_both: bool = False,
) -> tuple[Optional[str], Optional[str]]:
    normalized_language = normalize_preferred_language(preferred_language)
    normalized_country = normalize_country_code(country_code)

    if preferred_language is not None and str(preferred_language).strip():
        if normalized_language is None:
            raise HTTPException(
                status_code=400,
                detail="지원하지 않는 preferred_language 입니다",
            )

    if country_code is not None and str(country_code).strip():
        if normalized_country is None:
            raise HTTPException(
                status_code=400,
                detail="country_code 는 2자리 ISO 국가 코드여야 합니다",
            )

    if require_both:
        if normalized_language is None or normalized_country is None:
            raise HTTPException(
                status_code=400,
                detail="preferred_language 와 country_code 는 필수입니다",
            )

    return normalized_language, normalized_country


def _normalize_signup_phone(phone: Optional[str]) -> Optional[str]:
    cleaned = str(phone or "").strip()
    if not cleaned:
        return None
    if not cleaned.startswith("+"):
        raise HTTPException(
            status_code=400,
            detail="전화번호는 +국가번호 형식(E.164)으로 입력하세요",
        )
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) < 10 or len(digits) > 15:
        raise HTTPException(status_code=400, detail="유효하지 않은 전화번호입니다")
    return cleaned


def _create_user_from_signup_payload(payload: UserCreate, db: Session) -> User:
    if len(payload.password or "") < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다")

    member_type = str(payload.member_type or "individual").strip().lower()
    if member_type not in {"individual", "sole_proprietor", "corporation"}:
        raise HTTPException(status_code=400, detail="가입 유형은 individual, sole_proprietor, corporation 중 하나여야 합니다")

    if member_type in {"sole_proprietor", "corporation"}:
        if not str(payload.business_name or "").strip():
            raise HTTPException(status_code=400, detail="사업자명 또는 법인명은 필수입니다")
        if not str(payload.business_registration_number or "").strip():
            raise HTTPException(status_code=400, detail="사업자등록번호는 필수입니다")

    if member_type == "corporation" and not str(payload.representative_name or "").strip():
        raise HTTPException(status_code=400, detail="법인 가입은 대표자명이 필수입니다")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 사용자명입니다")

    normalized_phone = _normalize_signup_phone(payload.phone_number)
    if normalized_phone and db.query(User).filter(User.phone_number == normalized_phone).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 전화번호입니다")

    preferred_language, country_code = _validate_profile_fields(
        payload.preferred_language,
        payload.country_code,
    )

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=(payload.full_name or "").strip() or None,
        member_type=member_type,
        business_name=(payload.business_name or "").strip() or None,
        business_registration_number=(payload.business_registration_number or "").strip() or None,
        representative_name=(payload.representative_name or "").strip() or None,
        hashed_password=get_password_hash(payload.password),
        preferred_language=preferred_language,
        country_code=country_code,
        phone_number=normalized_phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------- 엔드포인트 ----------
@router.post("/signup/request-code", response_model=SignupRequestCodeResponse)
def signup_request_verification_code(
    payload: SignupRequestCode,
    db: Session = Depends(get_db),
    # [보안 보강] OTP 발송 폭탄(비용+스팸) 차단 — IP 단위 분당 발송 제한(기본 5/분).
    _otp_quota: None = Depends(require_otp_send_quota),
):
    from backend.services.contact_verification import (
        ResendCooldownError,
        start_verification_session,
    )

    normalized_phone = _normalize_signup_phone(payload.phone_number)
    verification_channel = str(payload.verificationChannel or "email").strip().lower()
    if verification_channel not in {"email", "phone"}:
        raise HTTPException(status_code=400, detail="verificationChannel 은 email 또는 phone 이어야 합니다")
    if verification_channel == "phone" and not normalized_phone:
        raise HTTPException(status_code=400, detail="전화 인증을 선택한 경우 연락처를 입력하세요")

    signup_payload = UserCreate(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        member_type=payload.member_type,
        business_name=payload.business_name,
        business_registration_number=payload.business_registration_number,
        representative_name=payload.representative_name,
        preferred_language=payload.preferred_language,
        country_code=payload.country_code,
        phone_number=normalized_phone,
    )
    if db.query(User).filter(User.email == signup_payload.email).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")
    if db.query(User).filter(User.username == signup_payload.username).first():
        raise HTTPException(status_code=400, detail="이미 사용 중인 사용자명입니다")
    if len(signup_payload.password or "") < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다")
    _validate_profile_fields(
        signup_payload.preferred_language,
        signup_payload.country_code,
        require_both=True,
    )

    signup_session_payload = signup_payload.model_dump()
    from backend.marketplace.worldlinco_referral import split_signup_attribution_codes

    referral_code, sales_agent_code = split_signup_attribution_codes(
        payload.referral_code,
        payload.sales_agent_code,
    )
    if referral_code:
        signup_session_payload["referral_code"] = referral_code
    if sales_agent_code:
        signup_session_payload["sales_agent_code"] = sales_agent_code

    try:
        session = start_verification_session(
            purpose="signup",
            channel=verification_channel,
            target_email=str(signup_payload.email),
            target_phone=normalized_phone if verification_channel == "phone" else None,
            payload=signup_session_payload,
        )
    except ResendCooldownError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SignupRequestCodeResponse(
        signupSessionToken=session["sessionToken"],
        verificationChannel=session["verificationChannel"],
        maskedTarget=session["maskedTarget"],
        expiresAt=session["expiresAt"],
        devOtpHint=session.get("devOtpHint"),
    )


@router.post("/signup/confirm", response_model=UserResponse, status_code=201)
def signup_confirm_verification(payload: SignupConfirmRequest, db: Session = Depends(get_db)):
    from backend.services.contact_verification import verify_session_code

    try:
        verified_payload = verify_session_code(
            payload.signupSessionToken,
            payload.verificationCode,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if payload.full_name is not None:
        verified_payload["full_name"] = str(payload.full_name).strip() or None
    profile_language = (
        payload.preferred_language
        if payload.preferred_language is not None
        else verified_payload.get("preferred_language")
    )
    profile_country = (
        payload.country_code
        if payload.country_code is not None
        else verified_payload.get("country_code")
    )
    normalized_language, normalized_country = _validate_profile_fields(
        profile_language,
        profile_country,
        require_both=True,
    )
    verified_payload["preferred_language"] = normalized_language
    verified_payload["country_code"] = normalized_country

    verification_meta = verified_payload.pop("_verification", None)
    if isinstance(verification_meta, dict):
        if verification_meta.get("channel") == "phone" and verification_meta.get("phone"):
            verified_payload["phone_number"] = verification_meta["phone"]

    referral_code = (
        str(verified_payload.pop("referral_code", "") or "").strip().upper()
        or str(payload.referral_code or "").strip().upper()
        or None
    )
    sales_agent_code = (
        str(verified_payload.pop("sales_agent_code", "") or "").strip().upper()
        or str(payload.sales_agent_code or "").strip().upper()
        or None
    )
    from backend.marketplace.worldlinco_referral import split_signup_attribution_codes

    referral_code, sales_agent_code = split_signup_attribution_codes(referral_code, sales_agent_code)

    signup_payload = UserCreate(**verified_payload)
    user = _create_user_from_signup_payload(signup_payload, db)
    if referral_code:
        from backend.marketplace.worldlinco_referral import record_referral_signup

        record_referral_signup(
            referral_code=referral_code,
            referred_user_id=int(user.id),
            referred_username=str(user.username or ""),
            referred_email=str(user.email or ""),
        )
    if sales_agent_code:
        from backend.marketplace.worldlinco_sales_commission import record_sales_agent_signup

        record_sales_agent_signup(
            sales_agent_code=sales_agent_code,
            user_id=int(user.id),
            username=str(user.username or ""),
            email=str(user.email or ""),
            user_country_code=str(user.country_code or "") or None,
        )
    return user


@router.post("/signup", response_model=UserResponse, status_code=201)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    from backend.services.contact_verification import allow_unverified_signup

    if not allow_unverified_signup():
        raise HTTPException(
            status_code=428,
            detail="회원가입은 이메일 OTP 인증이 필요합니다. /api/auth/signup/request-code → /confirm 경로를 사용하세요.",
        )
    return _create_user_from_signup_payload(payload, db)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    # [보안 보강] 크리덴셜 스터핑/브루트포스 차단 — IP 단위 분당 로그인 시도 제한(기본 10/분).
    _login_quota: None = Depends(require_login_quota),
):
    """username 필드에 email 또는 username 모두 허용"""
    user = db.query(User).filter(
        (User.email == form_data.username)
        | (User.username == form_data.username)
    ).first()

    if _is_passkey_only_auth_enabled():
        if user and _user_has_passkey(db, user):
            raise HTTPException(
                status_code=428,
                detail="비밀번호 로그인이 비활성화되었습니다. 패스키 로그인(/api/auth/passkey/login/start, /finish)을 사용하세요.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=428,
            detail="비밀번호 로그인이 비활성화되었습니다. 먼저 패스키를 등록하세요(/api/auth/passkey/register/start, /finish).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if _has_active_session_in_db(db, int(user.id)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_LOGIN_BLOCK_DETAIL,
        )

    # 단일 세션 강제: 새 로그인마다 고유 sid 발급 후 활성 세션으로 기록.
    # 이전 단말/웹의 토큰(다른 sid)은 다음 요청부터 401 → 자동 로그아웃된다.
    session_id = token_urlsafe(24)
    token = create_access_token(
        data={"sub": user.email, "sid": session_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        no_expiry=_should_issue_non_expiring_session_token(user),
    )
    _set_active_session_in_db(db, int(user.id), session_id)
    register_issued_token(token, str(user.email or user.username or ""))
    return {"access_token": token, "token_type": "bearer"}


@router.post("/passkey/register/start", response_model=PasskeyRegistrationStartResponse)
def start_passkey_registration(
    request: Request,
    payload: PasskeyRegistrationStartRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        (User.email == payload.email) | (User.username == payload.email)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="패스키를 등록할 계정을 찾을 수 없습니다")

    recovery_session_token: str | None = None
    if payload.recovery_reset_token:
        recovery_session_token, _ = _assert_verified_recovery_reset_token_any_scope(
            payload.recovery_reset_token.strip(),
            user_id=int(user.id),
        )
    elif payload.password:
        # Passkey-only mode disables password login, but password ownership proof can still
        # be used as an enrollment verification path to avoid account lockout.
        if not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다")
    else:
        raise HTTPException(
            status_code=428,
            detail="패스키 등록 전 본인확인이 필요합니다. 비밀번호를 입력하거나 /admin/recovery?intent=passkey 경로에서 인증을 완료하세요.",
        )

    rp_id, expected_origin = _resolve_passkey_request_context(request)
    registration_token = f"pkreg_{token_urlsafe(24)}"
    user_handle = _to_base64url(str(user.id).encode("utf-8"))
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=_resolve_passkey_rp_name(),
        user_id=str(user.id).encode("utf-8"),
        user_name=str(user.email),
        user_display_name=str(user.email),
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    _passkey_registration_store[registration_token] = {
        "user_id": int(user.id),
        "challenge": _to_base64url(options.challenge),
        "device_label": str(payload.device_label or "이 기기 패스키").strip() or "이 기기 패스키",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "user_handle": user_handle,
        "rp_id": rp_id,
        "expected_origin": expected_origin,
        "recovery_session_token": recovery_session_token,
    }
    return {
        "registration_token": registration_token,
        "options": __import__('json').loads(options_to_json(options)),
        "device_label": _passkey_registration_store[registration_token]["device_label"],
    }


@router.post("/passkey/register/finish")
def finish_passkey_registration(
    request: Request,
    payload: PasskeyRegistrationFinishRequest,
    db: Session = Depends(get_db),
):
    state = _passkey_registration_store.get(payload.registration_token)
    if not state:
        raise HTTPException(status_code=404, detail="패스키 등록 세션을 찾을 수 없습니다")

    expires_at = state.get("expires_at")
    if not isinstance(expires_at, datetime) or expires_at <= datetime.now(timezone.utc):
        _passkey_registration_store.pop(payload.registration_token, None)
        raise HTTPException(status_code=410, detail="패스키 등록 세션이 만료되었습니다")

    user = db.query(User).filter(User.id == state.get("user_id")).first()
    if user is None:
        _passkey_registration_store.pop(payload.registration_token, None)
        raise HTTPException(status_code=404, detail="패스키 등록 대상 계정을 찾을 수 없습니다")

    rp_id = str(state.get("rp_id") or _resolve_passkey_request_context(request)[0])
    expected_origin = str(state.get("expected_origin") or _resolve_passkey_request_context(request)[1])
    try:
        verification = verify_registration_response(
            credential=_build_registration_credential(payload.credential),
            expected_challenge=_from_base64url(str(state.get("challenge") or "")),
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
            require_user_verification=False,
        )
    except Exception as exc:
        logger.warning("패스키 등록 검증 실패: %s", exc)
        raise HTTPException(status_code=401, detail="패스키 등록 검증에 실패했습니다")

    credential_id = _to_base64url(verification.credential_id)
    public_key = _to_base64url(verification.credential_public_key)
    device_label = str(state.get("device_label") or "이 기기 패스키")
    sign_count = int(verification.sign_count)
    now = utcnow()

    existing_credential = (
        db.query(PasskeyCredential)
        .filter(PasskeyCredential.credential_id == credential_id)
        .first()
    )
    if existing_credential is None:
        db.add(
            PasskeyCredential(
                user_id=int(user.id),
                credential_id=credential_id,
                public_key=public_key,
                device_label=device_label,
                sign_count=sign_count,
                transports="hybrid,internal,usb,nfc,ble",
                created_at=now,
            )
        )
    else:
        existing_credential.user_id = int(user.id)
        existing_credential.public_key = public_key
        existing_credential.device_label = device_label
        existing_credential.sign_count = sign_count

    # Legacy compatibility mirror (kept until old user-level columns are fully retired)
    user.passkey_enabled = True
    user.passkey_credential_id = credential_id
    user.passkey_public_key = public_key
    user.passkey_device_label = device_label
    user.passkey_sign_count = sign_count
    user.passkey_registered_at = now
    db.add(user)
    db.commit()
    recovery_session_token = state.get("recovery_session_token")
    if isinstance(recovery_session_token, str) and recovery_session_token:
        _password_recovery_store.pop(recovery_session_token, None)
    _passkey_registration_store.pop(payload.registration_token, None)
    return {
        "registered": True,
        "device_label": user.passkey_device_label,
    }


@router.post("/passkey/login/start", response_model=PasskeyLoginStartResponse)
def start_passkey_login(
    request: Request,
    payload: PasskeyLoginStartRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        (User.email == payload.email) | (User.username == payload.email)
    ).first()
    if user is None:
        raise HTTPException(status_code=404, detail="등록된 패스키가 없습니다")

    credential_rows = _load_user_passkey_credentials(db, int(user.id))
    if not credential_rows and bool(getattr(user, "passkey_credential_id", None)):
        # Legacy fallback for users registered before multi-device table.
        credential_rows = [
            PasskeyCredential(
                user_id=int(user.id),
                credential_id=str(user.passkey_credential_id or ""),
                public_key=str(user.passkey_public_key or ""),
                device_label=str(user.passkey_device_label or "") or None,
                sign_count=int(getattr(user, "passkey_sign_count", 0) or 0),
            )
        ]
    if not credential_rows:
        raise HTTPException(status_code=404, detail="등록된 패스키가 없습니다")

    rp_id, expected_origin = _resolve_passkey_request_context(request)
    allow_credentials: list[PublicKeyCredentialDescriptor] = []
    for credential in credential_rows:
        raw_credential_id = str(credential.credential_id or "").strip()
        try:
            decoded_credential_id = _from_base64url(raw_credential_id)
        except Exception:
            logger.warning(
                "패스키 로그인 시작 스킵: credential_id 디코딩 오류 user_id=%s credential_id=%s",
                getattr(user, "id", None),
                raw_credential_id,
            )
            continue

        if not decoded_credential_id:
            continue

        allow_credentials.append(
            PublicKeyCredentialDescriptor(
                id=decoded_credential_id,
                type=PublicKeyCredentialType.PUBLIC_KEY,
                transports=[
                    AuthenticatorTransport.HYBRID,
                    AuthenticatorTransport.INTERNAL,
                    AuthenticatorTransport.USB,
                    AuthenticatorTransport.NFC,
                    AuthenticatorTransport.BLE,
                ],
            )
        )

    if not allow_credentials:
        raise HTTPException(
            status_code=409,
            detail="저장된 패스키 자격 증명 형식이 올바르지 않습니다. 패스키를 다시 등록해 주세요.",
        )

    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    _passkey_login_store[str(user.email)] = {
        "challenge": _to_base64url(options.challenge),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "credential_ids": [str(row.credential_id or "") for row in credential_rows],
        "rp_id": rp_id,
        "expected_origin": expected_origin,
    }
    return {
        "options": __import__('json').loads(options_to_json(options)),
    }


@router.post("/passkey/login/finish", response_model=Token)
def finish_passkey_login(
    request: Request,
    payload: PasskeyLoginFinishRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        (User.email == payload.email) | (User.username == payload.email)
    ).first()
    if user is None or not _user_has_passkey(db, user):
        raise HTTPException(status_code=404, detail="패스키 로그인 대상 계정을 찾을 수 없습니다")

    state = _passkey_login_store.get(str(user.email))
    if not state:
        raise HTTPException(status_code=404, detail="패스키 로그인 세션을 찾을 수 없습니다")

    expires_at = state.get("expires_at")
    if not isinstance(expires_at, datetime) or expires_at <= datetime.now(timezone.utc):
        _passkey_login_store.pop(str(user.email), None)
        raise HTTPException(status_code=410, detail="패스키 로그인 세션이 만료되었습니다")

    rp_id = str(state.get("rp_id") or _resolve_passkey_request_context(request)[0])
    expected_origin = str(state.get("expected_origin") or _resolve_passkey_request_context(request)[1])

    submitted_credential_id = _extract_credential_id_from_auth_payload(payload.credential)
    user_credentials = _load_user_passkey_credentials(db, int(user.id))
    selected_credential = None
    for row in user_credentials:
        if str(row.credential_id or "") == submitted_credential_id:
            selected_credential = row
            break

    # Legacy fallback for users who still only have user-level credential columns.
    if selected_credential is None and submitted_credential_id and str(user.passkey_credential_id or "") == submitted_credential_id:
        selected_credential = PasskeyCredential(
            user_id=int(user.id),
            credential_id=str(user.passkey_credential_id or ""),
            public_key=str(user.passkey_public_key or ""),
            device_label=str(user.passkey_device_label or "") or None,
            sign_count=int(getattr(user, "passkey_sign_count", 0) or 0),
        )

    if selected_credential is None:
        raise HTTPException(status_code=401, detail="등록되지 않은 패스키 자격 증명입니다")

    try:
        verification = verify_authentication_response(
            credential=_build_authentication_credential(payload.credential),
            expected_challenge=_from_base64url(str(state.get("challenge") or "")),
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
            credential_public_key=_from_base64url(str(selected_credential.public_key or "")),
            credential_current_sign_count=int(getattr(selected_credential, "sign_count", 0) or 0),
            require_user_verification=False,
        )
    except Exception as exc:
        logger.warning("패스키 로그인 검증 실패: %s", exc)
        raise HTTPException(status_code=401, detail="패스키 로그인 검증에 실패했습니다")

    if _has_active_session_in_db(db, int(user.id)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_LOGIN_BLOCK_DETAIL,
        )

    session_id = token_urlsafe(24)
    token = create_access_token(
        data={"sub": user.email, "sid": session_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        no_expiry=_should_issue_non_expiring_session_token(user),
    )
    _set_active_session_in_db(db, int(user.id), session_id)
    register_issued_token(token, str(user.email or user.username or ""))
    new_sign_count = int(verification.new_sign_count)
    if isinstance(selected_credential, PasskeyCredential) and getattr(selected_credential, "id", None) is not None:
        selected_credential.sign_count = new_sign_count
        selected_credential.last_used_at = utcnow()
        db.add(selected_credential)

    # Legacy mirror for compatibility with existing code paths.
    user.passkey_enabled = True
    user.passkey_credential_id = str(selected_credential.credential_id or user.passkey_credential_id or "")
    user.passkey_public_key = str(selected_credential.public_key or user.passkey_public_key or "")
    user.passkey_device_label = str(selected_credential.device_label or user.passkey_device_label or "") or None
    user.passkey_sign_count = new_sign_count
    user.passkey_registered_at = user.passkey_registered_at or utcnow()
    db.add(user)
    db.commit()
    _passkey_login_store.pop(str(user.email), None)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/passkey/credentials", response_model=PasskeyCredentialListResponse)
def list_passkey_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = _load_user_passkey_credentials(db, int(current_user.id))
    items = [
        {
            "credential_id": str(row.credential_id),
            "device_label": row.device_label,
            "created_at": row.created_at,
            "last_used_at": row.last_used_at,
        }
        for row in rows
    ]

    if not items and bool(getattr(current_user, "passkey_credential_id", None)):
        items.append(
            {
                "credential_id": str(current_user.passkey_credential_id),
                "device_label": current_user.passkey_device_label,
                "created_at": current_user.passkey_registered_at,
                "last_used_at": None,
            }
        )

    return {"credentials": items}


@router.delete("/passkey/credentials/{credential_id}")
def delete_passkey_credential(
    credential_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    normalized = str(credential_id or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="삭제할 credential_id 가 필요합니다")

    row = (
        db.query(PasskeyCredential)
        .filter(
            PasskeyCredential.user_id == int(current_user.id),
            PasskeyCredential.credential_id == normalized,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="삭제할 패스키 자격 증명을 찾을 수 없습니다")

    db.delete(row)
    db.flush()

    remaining = _load_user_passkey_credentials(db, int(current_user.id))
    if remaining:
        latest = remaining[-1]
        current_user.passkey_enabled = True
        current_user.passkey_credential_id = latest.credential_id
        current_user.passkey_public_key = latest.public_key
        current_user.passkey_device_label = latest.device_label
        current_user.passkey_sign_count = int(latest.sign_count or 0)
        current_user.passkey_registered_at = latest.created_at
    else:
        current_user.passkey_enabled = False
        current_user.passkey_credential_id = None
        current_user.passkey_public_key = None
        current_user.passkey_device_label = None
        current_user.passkey_sign_count = 0
        current_user.passkey_registered_at = None

    db.add(current_user)
    db.commit()
    return {"deleted": True, "credential_id": normalized, "remaining_count": len(remaining)}


@router.put("/extend", response_model=Token)
def extend_access_token(current_user: User = Depends(get_current_user)):
    subject = current_user.email or current_user.username
    # 세션 연장: 동일 단말이 토큰만 갱신. sid 를 회전하고 활성 세션으로 재기록해
    # 단일 세션을 유지(이 단말이 계속 유일한 활성 세션).
    session_id = token_urlsafe(24)
    token = create_access_token(
        data={"sub": subject, "sid": session_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        no_expiry=_should_issue_non_expiring_session_token(current_user),
    )
    set_active_session(int(current_user.id), session_id)
    register_issued_token(token, str(subject or ""))
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
):
    token_sid = resolve_token_session_id(token)
    clear_active_session(int(current_user.id), expected_session_id=token_sid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.preferred_language is None and payload.country_code is None:
        raise HTTPException(
            status_code=400,
            detail="수정할 preferred_language 또는 country_code 가 필요합니다",
        )

    preferred_language, country_code = _validate_profile_fields(
        payload.preferred_language,
        payload.country_code,
    )

    if payload.preferred_language is not None:
        current_user.preferred_language = preferred_language
    if payload.country_code is not None:
        current_user.country_code = country_code

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/recovery/start", response_model=PasswordRecoveryStartResponse)
def start_password_recovery(
    payload: PasswordRecoveryStartRequest,
    db: Session = Depends(get_db),
    # [보안 보강] 복구 코드 발송 폭탄(비용+스팸) 차단 — IP 단위 분당 발송 제한(기본 5/분).
    _otp_quota: None = Depends(require_otp_send_quota),
):
    from backend.services.contact_verification import (
        ResendCooldownError,
        start_verification_session,
    )

    user = db.query(User).filter(
        (User.email == payload.user_hint)
        | (User.username == payload.user_hint)
    ).first()

    if user is None:
        raise HTTPException(status_code=404, detail="일치하는 계정을 찾을 수 없습니다")

    if payload.scope == "admin" and not (getattr(user, "is_admin", False) or getattr(user, "is_superuser", False)):
        raise HTTPException(status_code=403, detail="관리자 계정만 이 복구 경로를 사용할 수 있습니다")

    verification_channel = str(payload.verification_channel or "email").strip().lower()
    phone_number = str(payload.phone_number or getattr(user, "phone_number", None) or "").strip() or None
    if verification_channel == "phone" and not phone_number:
        raise HTTPException(
            status_code=400,
            detail="전화 인증을 위해 phone_number가 필요합니다. 계정에 등록된 번호가 없으면 번호를 입력해주세요.",
        )

    try:
        recovery_purpose = "admin_recovery" if payload.scope == "admin" else "user_recovery"
        otp_session = start_verification_session(
            purpose=recovery_purpose,
            channel=verification_channel,
            target_email=str(user.email),
            target_phone=phone_number if verification_channel == "phone" else None,
            payload={"user_id": int(user.id), "scope": payload.scope},
        )
    except ResendCooldownError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    expires_at = datetime.fromisoformat(str(otp_session["expiresAt"]))
    return {
        "recovery_session_token": str(otp_session["sessionToken"]),
        "next_action": "verification_code_required",
        "expires_at": expires_at,
        "masked_target": str(otp_session["maskedTarget"]),
        "verification_channel": str(otp_session["verificationChannel"]),
        "dev_otp_hint": otp_session.get("devOtpHint"),
    }


@router.post("/recovery/verify-identity", response_model=PasswordRecoveryVerifyIdentityResponse)
def verify_password_recovery_identity(payload: PasswordRecoveryVerifyIdentityRequest):
    from backend.services.contact_verification import verify_session_code

    try:
        verified_payload = verify_session_code(
            payload.recovery_session_token,
            payload.verification_code,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="인증 세션을 찾을 수 없습니다") from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=410, detail="인증 세션이 만료되었습니다") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = int(verified_payload.get("user_id") or 0)
    scope = str(verified_payload.get("scope") or "admin")
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="복구 세션 정보가 올바르지 않습니다")

    reset_token, reset_expires_at = _issue_recovery_token("reset")
    _password_recovery_store[payload.recovery_session_token] = {
        "user_id": user_id,
        "scope": scope,
        "verified": True,
        "reset_token": reset_token,
        "reset_expires_at": reset_expires_at,
    }
    return {
        "verified": True,
        "reset_token": reset_token,
        "expires_at": reset_expires_at,
    }


@router.post("/recovery/reset-password", response_model=PasswordRecoveryResetResponse)
def reset_password_via_recovery(
    payload: PasswordRecoveryResetRequest,
    db: Session = Depends(get_db),
):
    if len(payload.new_password or "") < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다")

    session_token, session_state = _assert_verified_recovery_reset_token(
        payload.reset_token,
        scope=payload.scope,
    )

    user_id = session_state.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        _password_recovery_store.pop(session_token, None)
        raise HTTPException(status_code=404, detail="대상 계정을 찾을 수 없습니다")

    user.hashed_password = get_password_hash(payload.new_password)
    db.add(user)
    db.commit()
    # [보안 보강] 비밀번호 재설정 시 기존 모든 세션 무효화 — 활성 sid 를 새 값으로 회전하면
    # 이전에 발급된 모든 토큰(다른 sid)은 다음 요청부터 401 처리된다(계정탈취 복구의 핵심).
    set_active_session(int(user.id), token_urlsafe(24))
    _password_recovery_store.pop(session_token, None)
    return {
        "reset": True,
        "must_relogin": True,
    }


@router.post("/recovery/clear-active-session", response_model=PasswordRecoveryClearSessionResponse)
def clear_active_session_via_recovery(
    payload: PasswordRecoveryClearSessionRequest,
    db: Session = Depends(get_db),
):
    session_token, session_state = _assert_verified_recovery_reset_token(
        payload.reset_token,
        scope=payload.scope,
    )

    user_id = int(session_state.get("user_id") or 0)
    if user_id <= 0:
        _password_recovery_store.pop(session_token, None)
        raise HTTPException(status_code=400, detail="복구 세션 정보가 올바르지 않습니다")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        _password_recovery_store.pop(session_token, None)
        raise HTTPException(status_code=404, detail="대상 계정을 찾을 수 없습니다")

    cleared = clear_active_session(int(user.id))
    if not cleared:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="세션 해제를 완료하지 못했습니다. 잠시 후 다시 시도해주세요.",
        )

    _password_recovery_store.pop(session_token, None)
    return {
        "cleared": True,
        "must_relogin": True,
    }


@router.post("/password/change", response_model=UserPasswordChangeResponse)
def change_user_password(
    payload: UserPasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(payload.new_password or "") < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="새 비밀번호는 현재 비밀번호와 달라야 합니다")

    stored_hash = str(getattr(current_user, "hashed_password", "") or "")
    if not stored_hash or not verify_password(payload.current_password, stored_hash):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다")

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()
    # [보안 보강] 비밀번호 변경 시 기존 모든 세션 무효화(현재 세션 포함) — 활성 sid 회전.
    # 응답이 must_relogin=True 이므로 클라는 재로그인한다(유출 비밀번호 기반 토큰 무력화).
    set_active_session(int(current_user.id), token_urlsafe(24))
    return {
        "changed": True,
        "must_relogin": True,
    }
