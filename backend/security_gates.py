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