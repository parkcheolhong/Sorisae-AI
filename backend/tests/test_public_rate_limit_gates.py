"""무인증(IP 키) 레이트리밋 게이트 회귀 테스트.

HIGH 보안 보강: LBS /nearby, image-translation(OCR), login, OTP/복구 코드 발송은
인증 없이 열려 있어 비용 증폭/브루트포스/SMS·메일 폭탄에 노출됐다. 모바일 호환을 위해
하드 인증 대신 클라이언트 IP 단위 레이트리밋으로 1차 차단한다 — 이 동작을 고정한다.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend import security_gates


def _req(host: str = "203.0.113.7", xff: str | None = None) -> Request:
    headers = []
    if xff is not None:
        headers.append((b"x-forwarded-for", xff.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "client": (host, 54321),
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def _reset_quota() -> None:
    security_gates.reset_for_test()
    yield
    security_gates.reset_for_test()


@pytest.mark.parametrize(
    "dep,max_env,win_env",
    [
        (security_gates.require_lbs_search_quota, "LBS_SEARCH_QUOTA_MAX_REQUESTS", "LBS_SEARCH_QUOTA_WINDOW_SEC"),
        (security_gates.require_public_image_quota, "PUBLIC_IMAGE_QUOTA_MAX_REQUESTS", "PUBLIC_IMAGE_QUOTA_WINDOW_SEC"),
        (security_gates.require_login_quota, "AUTH_LOGIN_QUOTA_MAX_REQUESTS", "AUTH_LOGIN_QUOTA_WINDOW_SEC"),
        (security_gates.require_otp_send_quota, "AUTH_OTP_QUOTA_MAX_REQUESTS", "AUTH_OTP_QUOTA_WINDOW_SEC"),
    ],
)
def test_public_gate_blocks_after_limit(monkeypatch, dep, max_env, win_env) -> None:
    monkeypatch.setenv(max_env, "1")
    monkeypatch.setenv(win_env, "60")
    security_gates.reset_for_test()

    req = _req()
    assert dep(req) is None  # 1st request within quota

    with pytest.raises(HTTPException) as excinfo:
        dep(req)  # 2nd request exceeds quota
    assert excinfo.value.status_code == 429
    assert excinfo.value.headers.get("Retry-After")


def test_public_gate_isolates_distinct_clients(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_LOGIN_QUOTA_MAX_REQUESTS", "1")
    monkeypatch.setenv("AUTH_LOGIN_QUOTA_WINDOW_SEC", "60")
    security_gates.reset_for_test()

    security_gates.require_login_quota(_req(host="198.51.100.1"))
    # 다른 IP 는 별도 윈도우 — 한 클라이언트 초과가 타 클라이언트를 막지 않는다.
    assert security_gates.require_login_quota(_req(host="198.51.100.2")) is None


def test_public_gate_uses_forwarded_for_when_behind_proxy(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_OTP_QUOTA_MAX_REQUESTS", "1")
    monkeypatch.setenv("AUTH_OTP_QUOTA_WINDOW_SEC", "60")
    security_gates.reset_for_test()

    # 동일 프록시(client host)지만 XFF 가 다르면 서로 다른 실사용자 → 격리되어야 한다.
    security_gates.require_otp_send_quota(_req(host="10.0.0.9", xff="203.0.113.50"))
    assert security_gates.require_otp_send_quota(_req(host="10.0.0.9", xff="203.0.113.51")) is None

    # 같은 XFF(동일 실사용자)면 두 번째는 차단된다.
    security_gates.require_otp_send_quota(_req(host="10.0.0.9", xff="203.0.113.99"))
    with pytest.raises(HTTPException) as excinfo:
        security_gates.require_otp_send_quota(_req(host="10.0.0.9", xff="203.0.113.99"))
    assert excinfo.value.status_code == 429


def test_public_gate_disabled_when_max_is_zero(monkeypatch) -> None:
    monkeypatch.setenv("LBS_SEARCH_QUOTA_MAX_REQUESTS", "0")
    security_gates.reset_for_test()

    req = _req()
    for _ in range(50):
        assert security_gates.require_lbs_search_quota(req) is None
