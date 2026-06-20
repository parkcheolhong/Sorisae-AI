"""backend 테스트 공용 픽스처.

전역 인메모리 보안 쿼터(security_gates) 상태는 프로세스 단위로 누적되므로,
테스트 간 격리를 위해 각 테스트 시작 전에 초기화한다.
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_security_quota():
    try:
        from backend.security_gates import reset_for_test
    except Exception:
        yield
        return
    reset_for_test()
    yield
