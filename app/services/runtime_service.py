# FILE-ID: FILE-APP-SERVICES-RUNTIME-SERVICE-PY
# SECTION-ID: SECTION-APP-SERVICES-RUNTIME-SERVICE-PY-MAIN
# FEATURE-ID: FEATURE-APP-SERVICES-RUNTIME-SERVICE-PY-RUNTIME
# CHUNK-ID: CHUNK-APP-SERVICES-RUNTIME-SERVICE-PY-001

from datetime import datetime
from app.runtime import build_runtime_context, describe_runtime_profile
from app.order_profile import get_order_profile, get_flow_step, list_flow_steps
from backend.core.database import ensure_database_ready, get_database_settings
from backend.core.auth import create_access_token, get_auth_settings
from backend.core.ops_logging import record_ops_log
from backend.service.domain_adapter_service import build_domain_adapter_summary
from backend.service.strategy_service import build_strategy_service_overview
from ai.schemas import InferenceRequest, TrainingRequest, EvaluationRequest
from ai.train import train_model
from ai.inference import run_inference
from ai.evaluation import evaluate_predictions
from ai.model_registry import get_latest_model

DEFAULT_DOMAIN_RECORDS = [
  {
    "job_name": "catalog-sync",
    "automation_score": 0.74,
    "queue_action": "queue"
  },
  {
    "job_name": "report-rollup",
    "automation_score": 0.69,
    "queue_action": "schedule"
  },
  {
    "job_name": "ops-alert",
    "automation_score": 0.55,
    "queue_action": "review"
  }
]
MANDATORY_ENGINE_CONTRACTS = ["engine-core", "feature-pipeline", "training-pipeline", "inference-runtime", "evaluation-report", "service-integration"]
DOMAIN_RECORD_KEY = 'jobs'

def build_feature_matrix() -> list[dict]:
    return [{'flow_id': item['flow_id'], 'step_number': item.get('step_number'), 'step_id': item['step_id'], 'action': item['action'], 'trace_id': item.get('trace_id'), 'title': item['title'], 'state': 'ready'} for item in list_flow_steps()]

def build_trace_lookup(step_id: str = 'FLOW-001-1') -> dict:
    return get_flow_step(step_id) or {'step_id': step_id, 'missing': True}

def build_domain_snapshot() -> dict:
    profile = get_order_profile()
    return {'profile_id': profile['profile_id'], 'entities': profile['entities'], 'requested_outcomes': profile['requested_outcomes'], 'ui_modules': profile['ui_modules'], 'mandatory_engine_contracts': list(profile.get('mandatory_engine_contracts') or [])}

def build_ai_runtime_contract() -> dict:
    train_request = TrainingRequest(dataset=DEFAULT_DOMAIN_RECORDS)
    inference_request = InferenceRequest(signal_strength=0.7, features={DOMAIN_RECORD_KEY: DEFAULT_DOMAIN_RECORDS})
    model = train_model(train_request.dataset)
    database = ensure_database_ready()
    inference_payload = dict(inference_request.features)
    inference_payload['signal_strength'] = inference_request.signal_strength
    prediction = run_inference(inference_payload)
    evaluation = evaluate_predictions([prediction])
    strategy_service = build_strategy_service_overview(inference_payload)
    access_token = create_access_token('system-orchestrator')
    return {
        'mandatory_engine_contracts': list(MANDATORY_ENGINE_CONTRACTS),
        'engine-core': strategy_service.get('engine-core'),
        'feature-pipeline': strategy_service.get('engine-core', {}).get('feature-pipeline'),
        'training-pipeline': strategy_service.get('training_pipeline'),
        'inference-runtime': strategy_service.get('inference_runtime'),
        'evaluation-report': strategy_service.get('evaluation_report'),
        'service-integration': strategy_service.get('service-integration', True),
        'schemas': ['TrainingRequest', 'InferenceRequest', 'EvaluationRequest'],
        'endpoints': ['/ai/health', '/ai/train', '/ai/inference', '/ai/evaluate'],
        'model_registry': get_latest_model(),
        'training_pipeline': model,
        'inference_runtime': prediction,
        'evaluation_report': evaluation,
        'domain_adapter': build_domain_adapter_summary(inference_payload),
        'database': database,
        'auth': get_auth_settings(),
        'token_preview': access_token[:16],
        DOMAIN_RECORD_KEY: DEFAULT_DOMAIN_RECORDS,
        'prediction_runs': prediction.get('prediction_runs', 0),
        'candidate_sets': prediction.get('candidate_sets', []),
        'validation': {'ok': bool(model.get('status')) and bool(prediction.get('candidate_sets')) and evaluation.get('quality_gate') == 'pass', 'checked_via': ['/health', '/report']},
    }

def build_runtime_payload(runtime_mode: str = 'default') -> dict:
    profile = get_order_profile()
    runtime_context = build_runtime_context()
    record_ops_log('runtime_payload_built', {'runtime_mode': runtime_mode, 'profile_id': profile['profile_id']})
    return {'service': 'customer-order-generator', 'runtime_mode': runtime_mode, 'started_at': datetime.utcnow().isoformat(), 'order_profile': profile, 'active_trace': build_trace_lookup(), 'feature_matrix': build_feature_matrix(), 'domain_snapshot': build_domain_snapshot(), 'runtime_context': runtime_context, 'profile': describe_runtime_profile(), 'mandatory_engine_contracts': list(profile.get('mandatory_engine_contracts') or []), 'ai_runtime_contract': build_ai_runtime_contract()}

def list_endpoints() -> list[str]:
    endpoints = ['/', '/runtime', '/health', '/config', '/order-profile', '/flow-map', '/flow-map/{step_id}', '/workspace', '/report', '/diagnose']
    endpoints.extend(['/ai/health', '/ai/train', '/ai/inference', '/ai/evaluate'])
    return endpoints

def summarize_health() -> dict:
    payload = build_runtime_payload(runtime_mode='health')
    payload['status'] = 'ok'
    payload['checks'] = {'profile_loaded': True, 'flow_bound': True, 'delivery_ready': True, 'ai_contract_ready': bool(payload.get('ai_runtime_contract', {}).get('validation', {}).get('ok'))}
    return payload
