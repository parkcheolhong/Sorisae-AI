# FILE-ID: FILE-BACKEND-SERVICE-APPLICATION-SERVICE-PY
# SECTION-ID: SECTION-BACKEND-SERVICE-APPLICATION-SERVICE-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-SERVICE-APPLICATION-SERVICE-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-SERVICE-APPLICATION-SERVICE-PY-001

from backend.data.provider import list_data_sources
from backend.service.strategy_service import build_strategy_service_overview
from app.order_profile import list_flow_steps

def build_service_overview() -> dict:
    return {
        'sources': list_data_sources(),
        'flow_steps': list_flow_steps(),
        'strategy_service': build_strategy_service_overview(),
        'layer': 'service',
    }
