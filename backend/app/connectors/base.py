# FILE-ID: FILE-BACKEND-APP-CONNECTORS-BASE-PY
# SECTION-ID: SECTION-BACKEND-APP-CONNECTORS-BASE-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-APP-CONNECTORS-BASE-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-APP-CONNECTORS-BASE-PY-001

from dataclasses import dataclass

@dataclass
class CatalogConnectorResult:
    provider: str
    synced_count: int
    reachable: bool

class BaseConnector:
    provider_name = 'customer-runtime'
    request_timeout_sec = 5.0

    def sync_products(self) -> list[dict]:
        raise NotImplementedError('sync_products must be implemented by a customer connector')

    def build_sync_summary(self, synced_count: int, reachable: bool = True) -> CatalogConnectorResult:
        return CatalogConnectorResult(provider=self.provider_name, synced_count=synced_count, reachable=reachable)
