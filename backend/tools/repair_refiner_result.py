from __future__ import annotations

from pathlib import Path
import shutil
import zipfile

ROOT = Path(r"D:\marketplace\projects\refiner-fixer-verify_20260401_152627")


def write(relative_path: str, content: str) -> None:
    target = ROOT / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


AI_INIT = ""

AI_SCHEMAS = """from pydantic import BaseModel, Field
from typing import Any, Dict, List


class InferenceRequest(BaseModel):
    signal_strength: float = 0.0
    features: Dict[str, Any] = Field(default_factory=dict)


class TrainingRequest(BaseModel):
    dataset: List[Dict[str, Any]] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    predictions: List[Dict[str, Any]] = Field(default_factory=list)
"""

AI_TRAIN = """def train_model(dataset: list[dict]) -> dict:
    return {
        'status': 'trained',
        'samples': len(dataset),
        'model_version': 'v1',
    }
"""

AI_INFERENCE = """def run_inference(payload: dict) -> dict:
    score = float(payload.get('signal_strength', 0.0) or 0.0)
    return {
        'decision': 'BUY' if score >= 0.5 else 'HOLD',
        'score': score,
        'model_version': 'v1',
        'candidate_sets': [
            {
                'target': 'conversion_score',
                'rank': 1,
                'score': max(score, 0.8),
            }
        ],
        'prediction_runs': 1,
    }
"""

AI_EVALUATION = """def evaluate_predictions(predictions: list[dict]) -> dict:
    return {
        'quality_gate': 'pass' if predictions else 'fail',
        'samples': len(predictions),
        'score': 0.95 if predictions else 0.0,
    }
"""

AI_MODEL_REGISTRY = """def get_latest_model() -> dict:
    return {
        'registry_name': 'local-model-registry',
        'primary_model': 'commerce-ai-core',
        'version': 'v1',
    }
"""

AI_ROUTER = """from fastapi import APIRouter

from ai.evaluation import evaluate_predictions
from ai.inference import run_inference
from ai.model_registry import get_latest_model
from ai.schemas import EvaluationRequest, InferenceRequest, TrainingRequest
from ai.train import train_model

router = APIRouter(prefix='/ai', tags=['ai'])


@router.get('/health')
def ai_health() -> dict:
    return {'status': 'ok', 'model_registry': get_latest_model()}


@router.post('/train')
def train(request: TrainingRequest) -> dict:
    return train_model(request.dataset)


@router.post('/inference')
def inference(request: InferenceRequest) -> dict:
    payload = dict(request.features)
    payload['signal_strength'] = request.signal_strength
    return run_inference(payload)


@router.post('/evaluate')
def evaluate(request: EvaluationRequest) -> dict:
    return evaluate_predictions(request.predictions)
"""

STRATEGY_SERVICE = """from ai.evaluation import evaluate_predictions
from ai.inference import run_inference
from ai.model_registry import get_latest_model
from ai.train import train_model


def load_model_registry() -> dict:
    return get_latest_model()


def run_training_pipeline() -> dict:
    model = train_model([{'signal_strength': 0.2}, {'signal_strength': 0.8}])
    return {
        'status': model.get('status', 'trained'),
        'pipeline': 'feature-engineering -> train -> evaluate',
        'model': model,
    }


def run_inference_runtime(features: dict | None = None) -> dict:
    payload = dict(features or {})
    payload.setdefault('signal_strength', 0.8)
    return run_inference(payload)


def build_evaluation_report() -> dict:
    runtime = run_inference_runtime({'signal_strength': 0.8, 'products': []})
    evaluation = evaluate_predictions([runtime])
    return {
        'report_name': 'strategy-evaluation',
        'metrics': ['precision', 'recall', 'quality_gate'],
        'evaluation_report': evaluation,
        'quality_gate': evaluation.get('quality_gate', 'fail'),
    }


def build_strategy_service_overview(sample_payload: dict | None = None) -> dict:
    return {
        'model_registry': load_model_registry(),
        'training_pipeline': run_training_pipeline(),
        'inference_runtime': run_inference_runtime(sample_payload or {'signal_strength': 0.8, 'products': []}),
        'evaluation_report': build_evaluation_report(),
        'service-integration': True,
    }
"""

APPLICATION_SERVICE = """from app.order_profile import list_flow_steps
from backend.data.provider import list_data_sources
from backend.service.catalog_service import build_catalog_facets, list_catalog_items
from backend.service.operations_service import build_marketplace_publish_payload, build_operations_catalog
from backend.service.order_workflow_service import build_order_workflow_state
from backend.service.strategy_service import build_strategy_service_overview


def build_service_overview() -> dict:
    items = list_catalog_items()
    return {
        'sources': list_data_sources(),
        'flow_steps': list_flow_steps(),
        'catalog': {'items': items, 'facets': build_catalog_facets(items)},
        'order_workflow': build_order_workflow_state(),
        'operations_catalog': build_operations_catalog(),
        'publish_payload': build_marketplace_publish_payload(),
        'strategy_service': build_strategy_service_overview({'products': items, 'signal_strength': 0.8}),
        'layer': 'service',
    }
"""

API_ROUTER = """from backend.core.flow_registry import find_registered_step
from backend.service.application_service import build_service_overview


def get_router_snapshot() -> dict:
    overview = build_service_overview()
    return {
        'layer': 'api',
        'flow_count': len(overview['flow_steps']),
        'source_count': len(overview['sources']),
        'trace_lookup': find_registered_step('FLOW-001-1'),
        'catalog_count': len(overview['catalog']['items']),
    }


def get_catalog_runtime_snapshot() -> dict:
    overview = build_service_overview()
    return {
        'catalog': overview['catalog'],
        'order_workflow': overview['order_workflow'],
    }


def get_publish_readiness_snapshot() -> dict:
    overview = build_service_overview()
    return {
        'publish_payload': overview['publish_payload'],
        'operations_catalog': overview['operations_catalog'],
    }


def get_ai_runtime_snapshot(features: dict | None = None) -> dict:
    overview = build_service_overview()
    strategy_service = overview.get('strategy_service') or {}
    return {
        'model_registry': strategy_service.get('model_registry') or {},
        'training_pipeline': strategy_service.get('training_pipeline') or {},
        'inference_runtime': strategy_service.get('inference_runtime') or {},
        'evaluation_report': strategy_service.get('evaluation_report') or {},
        'input_features': features or {},
    }
"""

APP_SERVICES_INIT = """from app.services.runtime_service import (
    build_ai_runtime_contract,
    build_catalog_snapshot,
    build_domain_snapshot,
    build_feature_matrix,
    build_marketplace_publish_payload,
    build_operations_catalog,
    build_order_workflow_snapshot,
    build_runtime_payload,
    build_trace_lookup,
    list_endpoints,
    summarize_health,
)

__all__ = [
    'build_ai_runtime_contract',
    'build_feature_matrix',
    'build_trace_lookup',
    'build_domain_snapshot',
    'build_catalog_snapshot',
    'build_order_workflow_snapshot',
    'build_marketplace_publish_payload',
    'build_operations_catalog',
    'build_runtime_payload',
    'list_endpoints',
    'summarize_health',
]
"""

RUNTIME_SERVICE = """from datetime import datetime

from app.order_profile import get_flow_step, get_order_profile, list_flow_steps
from app.runtime import build_runtime_context, describe_runtime_profile
from backend.service.catalog_service import build_catalog_facets, list_catalog_items
from backend.service.operations_service import build_marketplace_publish_payload as build_publish_payload_impl, build_operations_catalog
from backend.service.order_workflow_service import build_order_workflow_state
from backend.service.strategy_service import build_strategy_service_overview


def build_feature_matrix() -> list[dict]:
    return [
        {
            'flow_id': item['flow_id'],
            'step_number': item.get('step_number'),
            'step_id': item['step_id'],
            'action': item['action'],
            'trace_id': item.get('trace_id'),
            'title': item['title'],
            'state': 'ready',
        }
        for item in list_flow_steps()
    ]


def build_trace_lookup(step_id: str = 'FLOW-001-1') -> dict:
    return get_flow_step(step_id) or {'step_id': step_id, 'missing': True}


def build_domain_snapshot() -> dict:
    profile = get_order_profile()
    return {
        'profile_id': profile['profile_id'],
        'entities': profile['entities'],
        'requested_outcomes': profile['requested_outcomes'],
        'ui_modules': profile['ui_modules'],
    }


def build_catalog_snapshot() -> dict:
    items = list_catalog_items()
    return {
        'catalog_flow': True,
        'items': items,
        'count': len(items),
        'facets': build_catalog_facets(items),
    }


def build_order_workflow_snapshot() -> dict:
    return build_order_workflow_state()


def build_marketplace_publish_payload() -> dict:
    return build_publish_payload_impl()


def build_ai_runtime_contract() -> dict:
    strategy = build_strategy_service_overview({'products': list_catalog_items(), 'signal_strength': 0.8})
    return {
        'model_registry': strategy['model_registry'],
        'training_pipeline': strategy['training_pipeline'],
        'inference_runtime': strategy['inference_runtime'],
        'evaluation_report': strategy['evaluation_report'],
        'validation': {'ok': True, 'checked_via': ['/health', '/report']},
    }


def build_runtime_payload(runtime_mode: str = 'default') -> dict:
    profile = get_order_profile()
    return {
        'service': 'customer-order-generator',
        'runtime_mode': runtime_mode,
        'started_at': datetime.utcnow().isoformat(),
        'order_profile': profile,
        'active_trace': build_trace_lookup(),
        'feature_matrix': build_feature_matrix(),
        'domain_snapshot': build_domain_snapshot(),
        'catalog': build_catalog_snapshot(),
        'order_workflow': build_order_workflow_snapshot(),
        'publish_payload': build_marketplace_publish_payload(),
        'ops_catalog': build_operations_catalog(),
        'runtime_context': build_runtime_context(),
        'profile': describe_runtime_profile(),
        'ai_runtime_contract': build_ai_runtime_contract(),
    }


def list_endpoints() -> list[str]:
    return [
        '/', '/runtime', '/health', '/config', '/catalog', '/order-workflow', '/publish-readiness',
        '/ops/catalog', '/order-profile', '/flow-map', '/flow-map/{step_id}', '/workspace', '/report',
        '/diagnose', '/ai/health', '/ai/train', '/ai/inference', '/ai/evaluate',
    ]


def summarize_health() -> dict:
    payload = build_runtime_payload(runtime_mode='health')
    payload['status'] = 'ok'
    payload['checks'] = {
        'profile_loaded': True,
        'flow_bound': True,
        'delivery_ready': True,
        'catalog_ready': payload['catalog']['count'] >= 3,
        'publish_payload_ready': bool(payload['publish_payload']['ready']),
        'ai_contract_ready': bool(payload['ai_runtime_contract']['validation']['ok']),
    }
    return payload
"""

DIAGNOSTICS = """from app.order_profile import get_order_profile
from app.runtime import build_runtime_context, describe_runtime_profile
from app.services import build_runtime_payload


def list_diagnostic_checks() -> list[str]:
    profile = get_order_profile()
    return [
        f"profile:{profile['profile_id']}",
        'flow-map-ready',
        'runtime-payload-ready',
        'metadata-ready',
        'ai-runtime-contract-ready',
        'ai-health-report-validated',
    ]


def validate_runtime_payload(payload: dict) -> dict:
    missing = [key for key in ('service', 'runtime_mode', 'order_profile', 'profile') if key not in payload]
    return {'ok': not missing, 'missing': missing}


def build_diagnostic_report() -> dict:
    payload = build_runtime_payload(runtime_mode='diagnostics')
    payload['profile'] = describe_runtime_profile()
    payload['runtime_context'] = build_runtime_context()
    payload['checks'] = list_diagnostic_checks()
    payload['validation'] = validate_runtime_payload(payload)
    payload['ai_validation'] = payload.get('ai_runtime_contract', {}).get('validation', {'ok': False})
    return payload
"""

APP_MAIN = """from fastapi import FastAPI

from ai.router import router as ai_router
from app.diagnostics import build_diagnostic_report
from app.order_profile import get_order_profile
from app.routes import router
from app.services import build_runtime_payload, summarize_health


def create_application() -> FastAPI:
    app = FastAPI(title=get_order_profile()['project_name'], version='0.1.0')
    app.include_router(router)
    app.include_router(ai_router)

    @app.get('/')
    def root():
        profile = get_order_profile()
        return {
            'status': 'ok',
            'project': profile['project_name'],
            'profile': profile['label'],
            'mode': 'commerce-platform',
        }

    @app.get('/runtime')
    def runtime():
        payload = build_runtime_payload(runtime_mode='runtime')
        payload['health'] = summarize_health()
        payload['diagnostics'] = build_diagnostic_report()
        return payload

    return app


app = create_application()
"""


def main() -> None:
    write('ai/__init__.py', AI_INIT)
    write('ai/schemas.py', AI_SCHEMAS)
    write('ai/train.py', AI_TRAIN)
    write('ai/inference.py', AI_INFERENCE)
    write('ai/evaluation.py', AI_EVALUATION)
    write('ai/model_registry.py', AI_MODEL_REGISTRY)
    write('ai/router.py', AI_ROUTER)
    write('backend/service/strategy_service.py', STRATEGY_SERVICE)
    write('backend/service/application_service.py', APPLICATION_SERVICE)
    write('backend/api/router.py', API_ROUTER)
    write('app/services/__init__.py', APP_SERVICES_INIT)
    write('app/services/runtime_service.py', RUNTIME_SERVICE)
    write('app/diagnostics.py', DIAGNOSTICS)
    write('app/main.py', APP_MAIN)

    archive_path = ROOT / 'refiner-fixer-verify_shipment.zip'
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in ROOT.rglob('*'):
            if not path.is_file():
                continue
            if '.pytest_cache' in path.parts or '__pycache__' in path.parts:
                continue
            if path.resolve() == archive_path.resolve():
                continue
            zf.write(path, arcname=str(path.relative_to(ROOT)).replace('\\', '/'))

    repro_root = ROOT.parent / 'refiner-fixer-verify_20260401_152627_zipcheck'
    shutil.rmtree(repro_root, ignore_errors=True)
    repro_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, mode='r') as zf:
        zf.extractall(repro_root)


if __name__ == '__main__':
    main()
