# FILE-ID: FILE-APP-AUTH-ROUTES-PY
# SECTION-ID: SECTION-APP-AUTH-ROUTES-PY-MAIN
# FEATURE-ID: FEATURE-APP-AUTH-ROUTES-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-AUTH-ROUTES-PY-001

from datetime import timedelta
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token as create_user_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from backend.core.auth import (
    create_access_token as create_runtime_access_token,
    decode_access_token,
    get_auth_settings,
)
from backend.database import get_db
from backend.models import User

auth_router = APIRouter(tags=['auth'])


class CompatSignupPayload(BaseModel):
    username: str | None = None
    email: str
    password: str
    full_name: str | None = None
    member_type: str | None = 'individual'
    business_name: str | None = None
    business_registration_number: str | None = None
    representative_name: str | None = None


def _normalize_user_identity(value: str | None) -> str:
    return str(value or '').strip()


def _derive_username(email: str, username: str | None) -> str:
    normalized_username = _normalize_user_identity(username)
    if normalized_username:
        return normalized_username
    email_prefix = _normalize_user_identity(email).split('@', 1)[0].strip()
    return email_prefix or 'marketplace-user'


def _serialize_user(user: User) -> dict:
    return {
        'id': int(getattr(user, 'id', 0) or 0),
        'username': str(getattr(user, 'username', '') or ''),
        'email': str(getattr(user, 'email', '') or ''),
        'full_name': getattr(user, 'full_name', None),
        'member_type': str(getattr(user, 'member_type', 'individual') or 'individual'),
        'business_name': getattr(user, 'business_name', None),
        'business_registration_number': getattr(user, 'business_registration_number', None),
        'representative_name': getattr(user, 'representative_name', None),
        'avatar_url': getattr(user, 'avatar_url', None),
        'credit_balance': int(getattr(user, 'credit_balance', 0) or 0),
        'is_active': bool(getattr(user, 'is_active', False)),
        'is_admin': bool(getattr(user, 'is_admin', False)),
        'is_superuser': bool(getattr(user, 'is_superuser', False)),
    }


def _issue_marketplace_login_response(user: User) -> dict:
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_user_access_token(
        data={'sub': user.email},
        expires_delta=expires_delta,
    )
    return {
        'access_token': access_token,
        'token_type': 'bearer',
        'user': _serialize_user(user),
    }


@auth_router.get('/auth/settings')
def auth_settings():
    return get_auth_settings()


@auth_router.post('/auth/token')
def issue_token(payload: dict | None = None):
    subject = str((payload or {}).get('subject') or 'automation_service-operator')
    scopes = list((payload or {}).get('scopes') or get_auth_settings().get('scopes') or [])
    return {'access_token': create_runtime_access_token(subject, scopes=scopes), 'token_type': 'bearer', 'scopes': scopes}


@auth_router.post('/auth/validate')
def validate_token(payload: dict | None = None):
    token = str((payload or {}).get('token') or '').strip()
    if not token:
        raise HTTPException(status_code=400, detail='token is required')
    return decode_access_token(token)


@auth_router.post('/api/auth/signup', status_code=status.HTTP_201_CREATED)
def compat_signup(payload: CompatSignupPayload, db: Session = Depends(get_db)):
    email = _normalize_user_identity(payload.email).lower()
    password = str(payload.password or '')
    username = _derive_username(email, payload.username)
    member_type = _normalize_user_identity(payload.member_type or 'individual').lower() or 'individual'

    if not email:
        raise HTTPException(status_code=400, detail='이메일은 필수입니다.')
    if not password:
        raise HTTPException(status_code=400, detail='비밀번호는 필수입니다.')
    if member_type not in {'individual', 'sole_proprietor', 'corporation'}:
        raise HTTPException(status_code=400, detail='가입 유형은 individual, sole_proprietor, corporation 중 하나여야 합니다.')

    duplicate_user = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if duplicate_user is not None:
        duplicate_field = 'email' if _normalize_user_identity(getattr(duplicate_user, 'email', '')).lower() == email else 'username'
        detail = '이미 가입된 이메일입니다.' if duplicate_field == 'email' else '이미 사용 중인 사용자 이름입니다.'
        raise HTTPException(status_code=400, detail=detail)

    user = User(
        email=email,
        username=username,
        full_name=_normalize_user_identity(payload.full_name) or None,
        member_type=member_type,
        business_name=_normalize_user_identity(payload.business_name) or None,
        business_registration_number=_normalize_user_identity(payload.business_registration_number) or None,
        representative_name=_normalize_user_identity(payload.representative_name) or None,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_staff=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@auth_router.post('/api/auth/login')
async def compat_login(request: Request, db: Session = Depends(get_db)):
    raw_body = (await request.body()).decode('utf-8', errors='ignore')
    form_payload = parse_qs(raw_body, keep_blank_values=True)
    identity = _normalize_user_identity((form_payload.get('username') or [''])[0])
    password = str((form_payload.get('password') or [''])[0] or '')
    if not identity or not password:
        raise HTTPException(status_code=400, detail='이메일과 비밀번호를 입력하세요.')

    user = db.query(User).filter((User.email == identity) | (User.username == identity)).first()
    if user is None or not verify_password(password, str(getattr(user, 'hashed_password', '') or '')):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='이메일 또는 비밀번호가 올바르지 않습니다')
    if not bool(getattr(user, 'is_active', False)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='비활성화된 계정입니다.')

    return _issue_marketplace_login_response(user)


@auth_router.get('/api/auth/me')
def compat_me(current_user: User = Depends(get_current_user)):
    return _serialize_user(current_user)


@auth_router.put('/api/auth/extend')
def compat_extend(current_user: User = Depends(get_current_user)):
    return _issue_marketplace_login_response(current_user)
