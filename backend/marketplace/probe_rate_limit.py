"""
probe_rate_limit.py
===================
IP별 프로브 엔드포인트 rate limiting 공통 헬퍼.
인증 없이 접근 가능한 /face-recognition/status, /ml-detectors/status에
분당 30회 호출 제한을 적용한다.

slowapi(limits 라이브러리 기반)를 사용하며, FastAPI Request 에서
real_ip 헤더(X-Forwarded-For) 우선 → 직접 IP 순으로 키를 결정한다.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# ---------------------------------------------------------------------------
# 전역 Limiter 인스턴스 (main.py 에서 app.state.limiter 로 등록)
# ---------------------------------------------------------------------------
PROBE_RATE_LIMIT = "30/minute"

limiter = Limiter(key_func=get_remote_address)
