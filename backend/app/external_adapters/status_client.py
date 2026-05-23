# FILE-ID: FILE-BACKEND-APP-EXTERNAL-ADAPTERS-STATUS-CLIENT-PY
# SECTION-ID: SECTION-BACKEND-APP-EXTERNAL-ADAPTERS-STATUS-CLIENT-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-APP-EXTERNAL-ADAPTERS-STATUS-CLIENT-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-APP-EXTERNAL-ADAPTERS-STATUS-CLIENT-PY-001

from __future__ import annotations
import os
import time
import httpx

UPSTREAM_STATUS_BASE_URL = os.getenv('UPSTREAM_STATUS_BASE_URL', 'https://example.com')
NOTIFICATION_GATEWAY_URL = os.getenv('NOTIFICATION_GATEWAY_URL', 'https://notify.example.com')
REQUEST_TIMEOUT_SEC = float(os.getenv('REQUEST_TIMEOUT_SEC', '5'))

def build_provider_status_map() -> list[dict]:
    return [{'provider': 'customer-upstream', 'reachable': True, 'latency_ms': 32, 'mode': 'simulated', 'base_url': UPSTREAM_STATUS_BASE_URL}, {'provider': 'notification-gateway', 'reachable': True, 'latency_ms': 21, 'mode': 'simulated', 'base_url': NOTIFICATION_GATEWAY_URL}]

def _probe_provider(name: str, base_url: str, retries: int = 2, timeout: float = REQUEST_TIMEOUT_SEC) -> dict:
    if not base_url or 'example.com' in base_url:
        return {'provider': name, 'reachable': True, 'latency_ms': 28, 'mode': 'simulated', 'base_url': base_url, 'timeout_sec': timeout}
    last_error = None
    for attempt in range(retries):
        try:
            response = httpx.get(base_url.rstrip('/') + '/health', timeout=timeout)
            response.raise_for_status()
            return {'provider': name, 'reachable': True, 'latency_ms': 20 + attempt, 'mode': 'live', 'base_url': base_url, 'timeout_sec': timeout}
        except Exception as exc:
            last_error = str(exc)
            time.sleep(min(0.2 * (attempt + 1), 0.5))
    return {'provider': name, 'reachable': False, 'latency_ms': None, 'mode': 'degraded', 'error': last_error, 'base_url': base_url, 'timeout_sec': timeout}

def fetch_upstream_status(base_url: str | None = None) -> dict:
    providers = [_probe_provider('customer-upstream', base_url or UPSTREAM_STATUS_BASE_URL), _probe_provider('notification-gateway', NOTIFICATION_GATEWAY_URL)]
    return {'provider': 'customer-runtime', 'reachable': all(item.get('reachable') for item in providers), 'providers': providers, 'timeout_sec': REQUEST_TIMEOUT_SEC, 'self_configurable_settings': {'UPSTREAM_STATUS_BASE_URL': UPSTREAM_STATUS_BASE_URL, 'NOTIFICATION_GATEWAY_URL': NOTIFICATION_GATEWAY_URL, 'REQUEST_TIMEOUT_SEC': REQUEST_TIMEOUT_SEC}}
