# FILE-ID: FILE-BACKEND-SERVICE-STRATEGY-SERVICE-PY
# SECTION-ID: SECTION-BACKEND-SERVICE-STRATEGY-SERVICE-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-SERVICE-STRATEGY-SERVICE-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-SERVICE-STRATEGY-SERVICE-PY-001

from app.order_profile import get_order_profile
from ai.features import build_feature_set
from ai.inference import run_inference
from ai.evaluation import evaluate_predictions
from ai.train import train_model
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

def load_model_registry() -> dict:
    profile = get_order_profile()
    latest_model = get_latest_model()
    return {
        'registry_name': 'domain-model-registry',
        'primary_model': latest_model.get('version', profile.get('project_name', 'domain-engine')),
        'version': latest_model.get('version', 'bootstrap'),
    }

def build_engine_core() -> dict:
    features = build_feature_set({DOMAIN_RECORD_KEY: DEFAULT_DOMAIN_RECORDS})
    return {
        'engine-core': True,
        'records': features.get(DOMAIN_RECORD_KEY, []),
        'feature-pipeline': {
            'feature_windows': features.get('feature_windows', []),
            'window_count': features.get('feature_count', 0),
        },
    }

def run_training_pipeline() -> dict:
    model = train_model(DEFAULT_DOMAIN_RECORDS)
    return {
        'status': model.get('status', 'trained'),
        'pipeline': 'engine-core -> feature-pipeline -> training-pipeline',
        'training-pipeline': True,
        'model': model,
    }

def run_inference_runtime(features: dict | None = None) -> dict:
    payload = dict(features or {})
    payload.setdefault(DOMAIN_RECORD_KEY, DEFAULT_DOMAIN_RECORDS)
    inference = run_inference(payload)
    return {
        'decision': inference.get('decision', 'recommend'),
        'score': inference.get('score', 0.0),
        'risk_score': inference.get('risk_score', 0.0),
        'order_action': inference.get('order_action', inference.get('decision', 'HOLD')),
        'broker_status': inference.get('broker_status', 'paper-ready'),
        'model_version': inference.get('model_version', 'bootstrap'),
        'candidate_sets': inference.get('candidate_sets', []),
        'prediction_runs': inference.get('prediction_runs', 0),
        'inference-runtime': True,
        'features': payload,
    }

def build_risk_guard(runtime: dict | None = None) -> dict:
    active_runtime = runtime or run_inference_runtime({DOMAIN_RECORD_KEY: DEFAULT_DOMAIN_RECORDS})
    risk_score = float(active_runtime.get('risk_score', 0.0) or 0.0)
    return {
        'risk-guard': True,
        'risk_score': risk_score,
        'blocked': risk_score > 0.6,
        'limit': 0.6,
    }

def build_order_execution_plan(runtime: dict | None = None) -> dict:
    active_runtime = runtime or run_inference_runtime({DOMAIN_RECORD_KEY: DEFAULT_DOMAIN_RECORDS})
    guard = build_risk_guard(active_runtime)
    order_action = 'HOLD' if guard.get('blocked') else active_runtime.get('order_action', 'HOLD')
    return {
        'order-execution': True,
        'broker-adapter': active_runtime.get('broker_status', 'paper-ready'),
        'order_action': order_action,
        'approved': not bool(guard.get('blocked')),
    }

def build_portfolio_sync(runtime: dict | None = None) -> dict:
    active_runtime = runtime or run_inference_runtime({DOMAIN_RECORD_KEY: DEFAULT_DOMAIN_RECORDS})
    return {
        'portfolio-sync': True,
        'portfolio_action': active_runtime.get('order_action', 'HOLD'),
        'position_delta': 1 if active_runtime.get('order_action') == 'BUY' else -1 if active_runtime.get('order_action') == 'SELL' else 0,
    }

def build_evaluation_report() -> dict:
    runtime = run_inference_runtime({DOMAIN_RECORD_KEY: DEFAULT_DOMAIN_RECORDS})
    evaluation = evaluate_predictions([runtime])
    return {
        'report_name': 'domain-evaluation',
        'metrics': ['candidate_sets', 'average_score', 'quality_gate'],
        'status': evaluation.get('quality_gate', 'needs-data'),
        'prediction-evaluation': evaluation.get('prediction_evaluation', False),
        'evaluation': evaluation,
    }

def build_strategy_service_overview(sample_payload: dict | None = None) -> dict:
    profile = get_order_profile()
    engine_core = build_engine_core()
    training_pipeline = run_training_pipeline()
    inference_runtime = run_inference_runtime(sample_payload or {DOMAIN_RECORD_KEY: DEFAULT_DOMAIN_RECORDS})
    risk_guard = build_risk_guard(inference_runtime)
    order_execution = build_order_execution_plan(inference_runtime)
    portfolio_sync = build_portfolio_sync(inference_runtime)
    evaluation_report = build_evaluation_report()
    return {
        'ai_enabled': bool(profile.get('ai_enabled')),
        'ai_capabilities': list(profile.get('ai_capabilities') or []),
        'mandatory_engine_contracts': list(profile.get('mandatory_engine_contracts') or []),
        'engine-core': engine_core,
        'service-integration': True,
        'risk-guard': risk_guard,
        'order-execution': order_execution,
        'portfolio-sync': portfolio_sync,
        'broker-adapter': order_execution.get('broker-adapter', 'paper-ready'),
        'model_registry': load_model_registry(),
        'training_pipeline': training_pipeline,
        'inference_runtime': inference_runtime,
        'evaluation_report': evaluation_report,
    }
