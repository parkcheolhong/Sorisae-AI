# FILE-ID: FILE-BACKEND-APP-CONNECTORS-SHOPIFY-PY
# SECTION-ID: SECTION-BACKEND-APP-CONNECTORS-SHOPIFY-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-APP-CONNECTORS-SHOPIFY-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-APP-CONNECTORS-SHOPIFY-PY-001

import httpx
import os

from backend.app.connectors.base import BaseConnector
from backend.app.core.url_security import parse_http_base_url

class ShopifyConnector(BaseConnector):
    def __init__(self, base_url: str) -> None:
        allow_private_hosts = str(os.getenv("ALLOW_PRIVATE_SHOPIFY_HOSTS", "false")).strip().lower() in {"1", "true", "yes", "on"}
        parsed = parse_http_base_url(base_url, allow_private_hosts=allow_private_hosts)
        self.base_url = parsed.normalized.rstrip('/')
        self._simulated = parsed.placeholder

    def sync_products(self) -> list[dict]:
        if self._simulated:
            return [
                {'id': 1, 'name': 'Starter', 'price': 10.0},
                {'id': 2, 'name': 'Growth', 'price': 19.0},
                {'id': 3, 'name': 'Scale', 'price': 39.0},
            ]
        response = httpx.get(f'{self.base_url}/admin/api/2024-01/products.json', timeout=10)
        response.raise_for_status()
        payload = response.json()
        return list(payload.get('products') or [])
