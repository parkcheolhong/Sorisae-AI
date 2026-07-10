"""Deprecation-safe UTC time helpers (SSOT).

Python 3.12+ deprecates ``datetime.datetime.utcnow()``. These helpers preserve
the *exact* prior behavior — a **naive** UTC ``datetime`` whose ``isoformat()``
carries no offset — so existing semantics are unchanged:

- DB 컬럼(타임존 없는 naive datetime)과의 비교가 그대로 동작(aware/naive 혼합 TypeError 방지).
- 직렬화 포맷 ``isoformat() + "Z"`` 가 ``...+00:00Z`` 로 깨지지 않고 기존과 동일.
- ``strftime`` / ``timedelta`` 산술 결과 동일.

따라서 ``datetime.utcnow()`` → ``utcnow()`` 단순 치환만으로 경고를 제거하면서
런타임 동작은 보존한다.
"""
from datetime import datetime, timezone

__all__ = ["utcnow"]


def utcnow() -> datetime:
    """Drop-in replacement for the deprecated ``datetime.utcnow()`` (naive UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
