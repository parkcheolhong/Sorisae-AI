# FILE-ID: FILE-BACKEND-SERVICE-DOMAIN-ADAPTER-SERVICE-PY
# SECTION-ID: SECTION-BACKEND-SERVICE-DOMAIN-ADAPTER-SERVICE-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-SERVICE-DOMAIN-ADAPTER-SERVICE-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-SERVICE-DOMAIN-ADAPTER-SERVICE-PY-001

from ai.adapters import resolve_adapter
from ai.features import build_feature_set

def build_domain_adapter_summary(payload: dict | None = None) -> dict:
    adapter = resolve_adapter()
    features = build_feature_set(payload or {})
    return {'adapter': adapter, 'model_endpoint': adapter.get('model_endpoint'), 'features': features, 'build_domain_adapter_summary': True}
