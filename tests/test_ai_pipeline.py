# FILE-ID: FILE-TESTS-TEST-AI-PIPELINE-PY
# SECTION-ID: SECTION-TESTS-TEST-AI-PIPELINE-PY-MAIN
# FEATURE-ID: FEATURE-TESTS-TEST-AI-PIPELINE-PY-RUNTIME
# CHUNK-ID: CHUNK-TESTS-TEST-AI-PIPELINE-PY-001

from app.services import build_ai_runtime_contract
from backend.service.strategy_service import build_strategy_service_overview

def test_ai_pipeline_runs():
    contract = build_ai_runtime_contract()
    strategy = build_strategy_service_overview()
    assert contract['mandatory_engine_contracts']
    assert contract['training-pipeline']
    assert contract['inference-runtime']
    assert contract['evaluation-report']
    assert contract['candidate_sets']
    assert contract['validation']['ok'] is True
    assert strategy['service-integration'] is True
