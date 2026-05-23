# FILE-ID: FILE-AI-ROUTER-PY
# SECTION-ID: SECTION-AI-ROUTER-PY-MAIN
# FEATURE-ID: FEATURE-AI-ROUTER-PY-RUNTIME
# CHUNK-ID: CHUNK-AI-ROUTER-PY-001

from fastapi import APIRouter
from ai.schemas import InferenceRequest, TrainingRequest, EvaluationRequest
from ai.train import train_model
from ai.inference import run_inference
from ai.evaluation import evaluate_predictions
from ai.model_registry import get_latest_model

router = APIRouter(prefix='/ai', tags=['ai'])

@router.get('/health')
def ai_health():
    return {'status': 'ok', 'model_registry': get_latest_model(), 'required_endpoints': ['/ai/train', '/ai/inference', '/ai/evaluate']}

@router.post('/train')
def ai_train(request: TrainingRequest):
    return {'status': 'trained', 'model': train_model(request.dataset)}

@router.post('/inference')
def ai_inference(request: InferenceRequest):
    payload = dict(request.features)
    payload['signal_strength'] = request.signal_strength
    return {'status': 'ok', 'result': run_inference(payload)}

@router.post('/evaluate')
def ai_evaluate(request: EvaluationRequest):
    return {'status': 'ok', 'report': evaluate_predictions(request.predictions)}
