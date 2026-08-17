"""
Prometheus 메트릭 수집
"""
import time
from fastapi import Request
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# 메트릭 정의
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'http_active_connections',
    'Active HTTP connections'
)

CACHE_HITS = Counter(
    'cache_hits_total',
    'Cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'cache_misses_total',
    'Cache misses',
    ['cache_type']
)

DB_QUERIES = Counter(
    'db_queries_total',
    'Database queries',
    ['query_type']
)

FILE_UPLOADS = Counter(
    'file_uploads_total',
    'Total file uploads',
    ['file_type']
)

PURCHASES = Counter(
    'purchases_total',
    'Total purchases',
    ['status']
)


class PrometheusMiddleware:
    """Prometheus 메트릭 수집 미들웨어"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """ASGI 미들웨어"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        ACTIVE_CONNECTIONS.inc()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = time.time() - start_time
                status_code = message["status"]
                
                REQUEST_COUNT.labels(
                    method=scope["method"],
                    endpoint=scope["path"],
                    status=status_code
                ).inc()
                
                REQUEST_DURATION.labels(
                    method=scope["method"],
                    endpoint=scope["path"]
                ).observe(duration)
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            ACTIVE_CONNECTIONS.dec()


def record_cache_hit(cache_type: str = "redis"):
    """캐시 히트 기록"""
    CACHE_HITS.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str = "redis"):
    """캐시 미스 기록"""
    CACHE_MISSES.labels(cache_type=cache_type).inc()


def record_db_query(query_type: str):
    """DB 쿼리 기록"""
    DB_QUERIES.labels(query_type=query_type).inc()


def record_file_upload(file_type: str):
    """파일 업로드 기록"""
    FILE_UPLOADS.labels(file_type=file_type).inc()


def record_purchase(status: str):
    """구매 기록"""
    PURCHASES.labels(status=status).inc()


def get_metrics():
    """모든 메트릭 반환"""
    return generate_latest()
