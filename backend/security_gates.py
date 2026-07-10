import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from backend.auth import get_current_user


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except (TypeError, ValueError):
        return default


@dataclass
class _QuotaWindow:
    started_at: float
    count: int


class _InMemoryQuotaGate:
    def __init__(
        self,
        *,
        scope: str,
        max_requests_env: str,
        window_seconds_env: str,
        default_max_requests: int,
        default_window_seconds: float,
    ) -> None:
        self.scope = scope
        self.max_requests_env = max_requests_env
        self.window_seconds_env = window_seconds_env
        self.default_max_requests = default_max_requests
        self.default_window_seconds = default_window_seconds
        self._state: dict[str, _QuotaWindow] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> int | None:
        max_requests = max(0, _int_env(self.max_requests_env, self.default_max_requests))
        window_seconds = max(0.1, _float_env(self.window_seconds_env, self.default_window_seconds))
        if max_requests <= 0:
            return None

        now_ts = time.monotonic()
        scoped_key = f"{self.scope}:{key}"
        with self._lock:
            window = self._state.get(scoped_key)
            if window is None or (now_ts - window.started_at) >= window_seconds:
                self._state[scoped_key] = _QuotaWindow(started_at=now_ts, count=1)
                self._prune(now_ts, window_seconds)
                return None
            if window.count >= max_requests:
                return max(1, int(window_seconds - (now_ts - window.started_at)))
            window.count += 1
            return None

    def reset(self) -> None:
        with self._lock:
            self._state.clear()

    def _prune(self, now_ts: float, window_seconds: float) -> None:
        stale_after = window_seconds * 4
        stale_keys = [
            key
            for key, window in self._state.items()
            if (now_ts - window.started_at) > stale_after
        ]
        for key in stale_keys:
            self._state.pop(key, None)


_LLM_MUTATION_QUOTA = _InMemoryQuotaGate(
    scope="llm-mutation",
    max_requests_env="LLM_MUTATION_QUOTA_MAX_REQUESTS",
    window_seconds_env="LLM_MUTATION_QUOTA_WINDOW_SEC",
    default_max_requests=60,
    default_window_seconds=60.0,
)

_IMAGE_MUTATION_QUOTA = _InMemoryQuotaGate(
    scope="image-mutation",
    max_requests_env="IMAGE_MUTATION_QUOTA_MAX_REQUESTS",
    window_seconds_env="IMAGE_MUTATION_QUOTA_WINDOW_SEC",
    default_max_requests=12,
    default_window_seconds=60.0,
)

_ADMIN_MUTATION_QUOTA = _InMemoryQuotaGate(
    scope="admin-mutation",
    max_requests_env="ADMIN_MUTATION_QUOTA_MAX_REQUESTS",
    window_seconds_env="ADMIN_MUTATION_QUOTA_WINDOW_SEC",
    default_max_requests=120,
    default_window_seconds=60.0,
)

# [V2 보안 STRIDE-D] 통화 개시는 방 생성 + 콜리 푸시를 유발하므로 남용 시 푸시 스팸/룸 고갈 위험.
# 사용자/클라이언트 단위로 분당 개시 횟수를 제한한다(기본 20/분, 0 설정 시 비활성).
_VOIP_CALL_QUOTA = _InMemoryQuotaGate(
    scope="voip-call",
    max_requests_env="VOIP_CALL_QUOTA_MAX_REQUESTS",
    window_seconds_env="VOIP_CALL_QUOTA_WINDOW_SEC",
    default_max_requests=20,
    default_window_seconds=60.0,
)

# [보안 보강] 아래 게이트들은 '무인증'으로 열려 있는 고비용/민감 엔드포인트를 IP 단위로 제한한다.
# 모바일 클라가 이 경로들에 Authorization 헤더를 보내지 않으므로(앱 호환), 하드 인증 대신
# 클라이언트 IP 키 레이트리밋으로 비용 증폭/DoS·브루트포스·OTP 폭탄을 1차 차단한다.
# (완전한 인증 도입은 모바일 토큰 첨부 + APK 재배포가 동반되는 별도 작업으로 분리.)

# LBS 주변검색: live 시 SerpApi(유료)·Overpass 팬아웃 → 비용 증폭 차단(기본 40/분).
_LBS_SEARCH_QUOTA = _InMemoryQuotaGate(
    scope="lbs-search",
    max_requests_env="LBS_SEARCH_QUOTA_MAX_REQUESTS",
    window_seconds_env="LBS_SEARCH_QUOTA_WINDOW_SEC",
    default_max_requests=40,
    default_window_seconds=60.0,
)

# 이미지 번역(OCR): 업로드 + RapidOCR(CPU) → 연산/메모리 DoS 차단(기본 12/분).
_PUBLIC_IMAGE_QUOTA = _InMemoryQuotaGate(
    scope="public-image",
    max_requests_env="PUBLIC_IMAGE_QUOTA_MAX_REQUESTS",
    window_seconds_env="PUBLIC_IMAGE_QUOTA_WINDOW_SEC",
    default_max_requests=12,
    default_window_seconds=60.0,
)

# 로그인: bcrypt 검증을 무제한 호출하는 크리덴셜 스터핑 차단(기본 10/분/IP).
_AUTH_LOGIN_QUOTA = _InMemoryQuotaGate(
    scope="auth-login",
    max_requests_env="AUTH_LOGIN_QUOTA_MAX_REQUESTS",
    window_seconds_env="AUTH_LOGIN_QUOTA_WINDOW_SEC",
    default_max_requests=10,
    default_window_seconds=60.0,
)

# OTP/복구 코드 발송: SMS·메일 폭탄(비용+스팸) 차단(기본 5/분/IP).
_AUTH_OTP_QUOTA = _InMemoryQuotaGate(
    scope="auth-otp",
    max_requests_env="AUTH_OTP_QUOTA_MAX_REQUESTS",
    window_seconds_env="AUTH_OTP_QUOTA_WINDOW_SEC",
    default_max_requests=5,
    default_window_seconds=60.0,
)


def _identity_key(request: Request, current_user: Any) -> str:
    user_key = (
        getattr(current_user, "id", None)
        or getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or "unknown-user"
    )
    client_host = getattr(getattr(request, "client", None), "host", None) or "unknown-client"
    return f"user={user_key}|client={client_host}"


def _enforce_quota(
    *,
    quota_gate: _InMemoryQuotaGate,
    request: Request,
    current_user: Any,
) -> Any:
    retry_after = quota_gate.check(_identity_key(request, current_user))
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="요청 쿼터를 초과했습니다. 잠시 후 다시 시도해주세요.",
            headers={"Retry-After": str(retry_after)},
        )
    return current_user


def _client_key(request: Request) -> str:
    """무인증 엔드포인트용 IP 키. 프록시(nginx) 뒤이면 X-Forwarded-For 의 첫 IP 를 신뢰한다."""
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return f"ip={forwarded}"
    client_host = getattr(getattr(request, "client", None), "host", None) or "unknown-client"
    return f"ip={client_host}"


def _enforce_quota_public(*, quota_gate: _InMemoryQuotaGate, request: Request) -> None:
    """current_user 없이 IP 키로만 제한하는 무인증 엔드포인트 전용 게이트."""
    retry_after = quota_gate.check(_client_key(request))
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
            headers={"Retry-After": str(retry_after)},
        )


def require_admin_user(current_user: Any = Depends(get_current_user)) -> Any:
    if not (
        bool(getattr(current_user, "is_admin", False))
        or bool(getattr(current_user, "is_superuser", False))
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    return current_user


def require_llm_mutation_quota(
    request: Request,
    current_user: Any = Depends(get_current_user),
) -> Any:
    return _enforce_quota(
        quota_gate=_LLM_MUTATION_QUOTA,
        request=request,
        current_user=current_user,
    )


def require_image_mutation_quota(
    request: Request,
    current_user: Any = Depends(get_current_user),
) -> Any:
    return _enforce_quota(
        quota_gate=_IMAGE_MUTATION_QUOTA,
        request=request,
        current_user=current_user,
    )


def require_admin_mutation_quota(
    request: Request,
    current_user: Any = Depends(require_admin_user),
) -> Any:
    return _enforce_quota(
        quota_gate=_ADMIN_MUTATION_QUOTA,
        request=request,
        current_user=current_user,
    )


def require_voip_call_quota(
    request: Request,
    current_user: Any = Depends(get_current_user),
) -> Any:
    return _enforce_quota(
        quota_gate=_VOIP_CALL_QUOTA,
        request=request,
        current_user=current_user,
    )


# ── 무인증(IP 키) 게이트 — 모바일 호환 유지하면서 비용/DoS·브루트포스 1차 차단 ──

def require_lbs_search_quota(request: Request) -> None:
    _enforce_quota_public(quota_gate=_LBS_SEARCH_QUOTA, request=request)


def require_public_image_quota(request: Request) -> None:
    _enforce_quota_public(quota_gate=_PUBLIC_IMAGE_QUOTA, request=request)


def require_login_quota(request: Request) -> None:
    _enforce_quota_public(quota_gate=_AUTH_LOGIN_QUOTA, request=request)


def require_otp_send_quota(request: Request) -> None:
    _enforce_quota_public(quota_gate=_AUTH_OTP_QUOTA, request=request)


def reset_for_test() -> None:
    """테스트 격리용: 프로세스 전역 인메모리 쿼터 상태를 초기화한다."""
    for gate in (
        _LLM_MUTATION_QUOTA,
        _IMAGE_MUTATION_QUOTA,
        _ADMIN_MUTATION_QUOTA,
        _VOIP_CALL_QUOTA,
        _LBS_SEARCH_QUOTA,
        _PUBLIC_IMAGE_QUOTA,
        _AUTH_LOGIN_QUOTA,
        _AUTH_OTP_QUOTA,
    ):
        gate.reset()