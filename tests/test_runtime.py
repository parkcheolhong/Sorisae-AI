# FILE-ID: FILE-TESTS-TEST-RUNTIME-PY
# SECTION-ID: SECTION-TESTS-TEST-RUNTIME-PY-MAIN
# FEATURE-ID: FEATURE-TESTS-TEST-RUNTIME-PY-RUNTIME
# CHUNK-ID: CHUNK-TESTS-TEST-RUNTIME-PY-001

from app.services import build_runtime_payload

def test_runtime_payload_contains_order_profile():
    payload = build_runtime_payload(runtime_mode='test')
    assert payload['service'] == 'customer-order-generator'
    assert payload['order_profile']['profile_id']
    assert payload['mandatory_engine_contracts']
    assert payload['ai_runtime_contract']['validation']['ok'] is True
    assert payload['ai_runtime_contract']['candidate_sets']
