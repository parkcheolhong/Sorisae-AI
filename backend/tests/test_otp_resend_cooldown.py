"""per-계정(대상) OTP/복구 코드 재발송 쿨다운 + 시간당 상한 회귀 테스트.

IP 키 레이트리밋(security_gates)이 1차 방어선이라면, 이쪽은 '분산 IP 가 한 피해자에게'
코드를 폭탄 발송하지 못하게 막는 대상 단위 2차 방어선이다.
"""
from __future__ import annotations

import pytest

from backend.services import contact_verification as cv


@pytest.fixture(autouse=True)
def _reset() -> None:
    cv.reset_for_test()
    yield
    cv.reset_for_test()


def test_resend_cooldown_blocks_immediate_repeat(monkeypatch) -> None:
    monkeypatch.setenv("OTP_RESEND_COOLDOWN_SEC", "60")
    monkeypatch.setenv("OTP_MAX_SENDS_PER_TARGET", "5")

    cv._enforce_target_send_quota("signup", "email", "victim@example.com")
    with pytest.raises(cv.ResendCooldownError) as excinfo:
        cv._enforce_target_send_quota("signup", "email", "victim@example.com")
    assert excinfo.value.retry_after >= 1


def test_resend_cooldown_isolates_distinct_targets(monkeypatch) -> None:
    monkeypatch.setenv("OTP_RESEND_COOLDOWN_SEC", "60")

    cv._enforce_target_send_quota("signup", "email", "a@example.com")
    # 다른 대상은 별도 윈도우 — 막히지 않는다.
    cv._enforce_target_send_quota("signup", "email", "b@example.com")


def test_resend_target_case_insensitive(monkeypatch) -> None:
    monkeypatch.setenv("OTP_RESEND_COOLDOWN_SEC", "60")

    cv._enforce_target_send_quota("signup", "email", "Victim@Example.com")
    with pytest.raises(cv.ResendCooldownError):
        cv._enforce_target_send_quota("signup", "email", "victim@example.com")


def test_hourly_cap_blocks_after_max(monkeypatch) -> None:
    # 쿨다운은 끄고(0) 시간당 상한만 검증.
    monkeypatch.setenv("OTP_RESEND_COOLDOWN_SEC", "0")
    monkeypatch.setenv("OTP_MAX_SENDS_PER_TARGET", "3")
    monkeypatch.setenv("OTP_TARGET_SEND_WINDOW_SEC", "3600")

    for _ in range(3):
        cv._enforce_target_send_quota("user_recovery", "phone", "+8210123")
    with pytest.raises(cv.ResendCooldownError) as excinfo:
        cv._enforce_target_send_quota("user_recovery", "phone", "+8210123")
    assert excinfo.value.retry_after >= 1


def test_disabled_when_both_thresholds_zero(monkeypatch) -> None:
    monkeypatch.setenv("OTP_RESEND_COOLDOWN_SEC", "0")
    monkeypatch.setenv("OTP_MAX_SENDS_PER_TARGET", "0")

    for _ in range(20):
        cv._enforce_target_send_quota("signup", "email", "spammable@example.com")
