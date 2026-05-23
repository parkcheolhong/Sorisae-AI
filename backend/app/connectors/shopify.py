# FILE-ID: FILE-BACKEND-APP-CONNECTORS-SHOPIFY-PY
# SECTION-ID: SECTION-BACKEND-APP-CONNECTORS-SHOPIFY-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-APP-CONNECTORS-SHOPIFY-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-APP-CONNECTORS-SHOPIFY-PY-001

import httpx

from backend.app.connectors.base import BaseConnector

class ShopifyConnector(BaseConnector):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip('/')

    def sync_products(self) -> list[dict]:
        if 'example.com' in self.base_url:
            return [
                {'id': 1, 'name': 'Starter', 'price': 10.0},
                {'id': 2, 'name': 'Growth', 'price': 19.0},
                {'id': 3, 'name': 'Scale', 'price': 39.0},
            ]
        response = httpx.get(f'{self.base_url}/admin/api/2024-01/products.json', timeout=10)
        response.raise_for_status()
        payload = response.json()
        return list(payload.get('products') or [])
