# FILE-ID: FILE-BACKEND-APP-CONNECTORS-PAYMENT-GATEWAY-PY
# SECTION-ID: SECTION-BACKEND-APP-CONNECTORS-PAYMENT-GATEWAY-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-APP-CONNECTORS-PAYMENT-GATEWAY-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-APP-CONNECTORS-PAYMENT-GATEWAY-PY-001

from __future__ import annotations
import os
import time
import httpx

PAYMENT_PROVIDER_URL = os.getenv('PAYMENT_PROVIDER_URL', 'https://payments.example.com')
PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN', 'replace-with-payment-token')

def get_payment_provider_status(retries: int = 2, timeout: float = 5.0) -> dict:
    if not PAYMENT_PROVIDER_URL or 'example.com' in PAYMENT_PROVIDER_URL:
        return {'provider': 'payments', 'reachable': True, 'mode': 'simulated'}
    headers = {'Authorization': f'Bearer {PAYMENT_PROVIDER_TOKEN}'}
    last_error = None
    for attempt in range(retries):
        try:
            response = httpx.get(PAYMENT_PROVIDER_URL.rstrip('/') + '/health', headers=headers, timeout=timeout)
            response.raise_for_status()
            return {'provider': 'payments', 'reachable': True, 'mode': 'live'}
        except Exception as exc:
            last_error = str(exc)
            time.sleep(min(0.2 * (attempt + 1), 0.5))
    return {'provider': 'payments', 'reachable': False, 'mode': 'degraded', 'error': last_error}
