"""
probe_rate_limit.py
===================
IP별 프로브 엔드포인트 rate limiting 공통 헬퍼.
인증 없이 접근 가능한 /face-recognition/status, /ml-detectors/status에
분당 30회 호출 제한을 적용한다.

slowapi(limits 라이브러리 기반)를 사용하며, FastAPI Request 에서
real_ip 헤더(X-Forwarded-For) 우선 → 직접 IP 순으로 키를 결정한다.
"""

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
except Exception:
    import functools
    import inspect
    import threading
    import time
    from fastapi import HTTPException, Request, status

    def get_remote_address(request) -> str:  # type: ignore[no-untyped-def]
        client = getattr(request, "client", None)
        host = getattr(client, "host", None)
        return str(host or "unknown")

    class Limiter:  # type: ignore[override]
        def __init__(self, key_func):  # type: ignore[no-untyped-def]
            self.key_func = key_func
            self._lock = threading.RLock()
            self._hits: dict[str, list[float]] = {}

        @staticmethod
        def _parse_rate_limit(rate_limit: str) -> tuple[int, int]:
            raw = str(rate_limit or "").strip().lower()
            if "/" not in raw:
                return 30, 60
            count_text, window_text = raw.split("/", 1)
            try:
                count = max(1, int(count_text.strip()))
            except Exception:
                count = 30
            if window_text.startswith("sec"):
                return count, 1
            if window_text.startswith("hour"):
                return count, 3600
            return count, 60

        @staticmethod
        def _extract_request(args, kwargs) -> Request | None:  # type: ignore[no-untyped-def]
            request = kwargs.get("request")
            if isinstance(request, Request):
                return request
            for arg in args:
                if isinstance(arg, Request):
                    return arg
            return None

        def _check(self, key: str, limit_count: int, window_sec: int) -> None:
            now = time.time()
            with self._lock:
                bucket = self._hits.setdefault(key, [])
                threshold = now - window_sec
                while bucket and bucket[0] <= threshold:
                    bucket.pop(0)
                if len(bucket) >= limit_count:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests",
                    )
                bucket.append(now)

        def limit(self, rate_limit: str, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            limit_count, window_sec = self._parse_rate_limit(rate_limit)

            def _decorator(func):  # type: ignore[no-untyped-def]
                if inspect.iscoroutinefunction(func):
                    @functools.wraps(func)
                    async def _async_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
                        request = self._extract_request(args, kwargs)
                        key = self.key_func(request) if request is not None else "unknown"
                        self._check(str(key), limit_count, window_sec)
                        return await func(*args, **kwargs)

                    return _async_wrapper

                @functools.wraps(func)
                def _sync_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
                    request = self._extract_request(args, kwargs)
                    key = self.key_func(request) if request is not None else "unknown"
                    self._check(str(key), limit_count, window_sec)
                    return func(*args, **kwargs)

                return _sync_wrapper

            return _decorator

# ---------------------------------------------------------------------------
# 전역 Limiter 인스턴스 (main.py 에서 app.state.limiter 로 등록)
# ---------------------------------------------------------------------------
PROBE_RATE_LIMIT = "30/minute"

limiter = Limiter(key_func=get_remote_address)
