# FILE-ID: FILE-BACKEND-APP-CONNECTORS-PAYMENT-GATEWAY-PY
# SECTION-ID: SECTION-BACKEND-APP-CONNECTORS-PAYMENT-GATEWAY-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-APP-CONNECTORS-PAYMENT-GATEWAY-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-APP-CONNECTORS-PAYMENT-GATEWAY-PY-001

from __future__ import annotations
import os
import time
import httpx
from backend.app.core.url_security import parse_http_base_url

PAYMENT_PROVIDER_URL = os.getenv('PAYMENT_PROVIDER_URL', 'https://payments.example.com')
PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN', 'replace-with-payment-token')

def get_payment_provider_status(retries: int = 2, timeout: float = 5.0) -> dict:
    allow_private_hosts = str(os.getenv("ALLOW_PRIVATE_PAYMENT_PROVIDER_HOSTS", "false")).strip().lower() in {"1", "true", "yes", "on"}
    try:
        parsed = parse_http_base_url(PAYMENT_PROVIDER_URL, allow_private_hosts=allow_private_hosts)
    except ValueError as exc:
        return {'provider': 'payments', 'reachable': False, 'mode': 'degraded', 'error': str(exc)}
    if parsed.placeholder:
        return {'provider': 'payments', 'reachable': True, 'mode': 'simulated'}
    headers = {'Authorization': f'Bearer {PAYMENT_PROVIDER_TOKEN}'}
    last_error = None
    for attempt in range(retries):
        try:
            response = httpx.get(parsed.normalized.rstrip('/') + '/health', headers=headers, timeout=timeout)
            response.raise_for_status()
            return {'provider': 'payments', 'reachable': True, 'mode': 'live'}
        except Exception as exc:
            last_error = str(exc)
            time.sleep(min(0.2 * (attempt + 1), 0.5))
    return {'provider': 'payments', 'reachable': False, 'mode': 'degraded', 'error': last_error}
