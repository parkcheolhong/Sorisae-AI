# Evidence: Sorisae Dispatch Failure Code Standardization (2026-05-05)

## Run Context
- Command: PYTHONPATH=. python scripts/validate_sorisae_failure_codes.py
- Base URL: <http://127.0.0.1:8000>
- Auth: /api/auth/login bearer token
- Runtime probe slot: backend/services/shinsegye/engines120/slot999_failure_probe.py

## Registration
- REGISTER|runtime=200|missing=200

## Round 1
- R1|kind=unknown_probe|http=400|status=input_validation_error|error_code=INPUT_ENGINE_TYPE_NOT_REGISTERED|retryable=False|source=router_validation
- R1|kind=missing_probe|http=200|status=fallback|error_code=ENGINE_LOAD_ERROR|retryable=False|source=module_loader
- R1|kind=runtime_probe|http=200|status=error|error_code=ENGINE_RUNTIME_ERROR|retryable=False|source=engine_runtime
- R1|kind=master|http=200|status=flask_server_unavailable|error_code=FLASK_SERVER_NETWORK_ERROR|retryable=True|source=flask_proxy

## Round 2
- R2|kind=unknown_probe|http=400|status=input_validation_error|error_code=INPUT_ENGINE_TYPE_NOT_REGISTERED|retryable=False|source=router_validation
- R2|kind=missing_probe|http=200|status=fallback|error_code=ENGINE_LOAD_ERROR|retryable=False|source=module_loader
- R2|kind=runtime_probe|http=200|status=error|error_code=ENGINE_RUNTIME_ERROR|retryable=False|source=engine_runtime
- R2|kind=master|http=200|status=flask_server_unavailable|error_code=FLASK_SERVER_NETWORK_ERROR|retryable=True|source=flask_proxy

## Timeout Classification Check (Code Path)
- method: mock urllib.request.urlopen with URLError(socket.timeout('timed out'))
- T1|kind=timeout_simulated|status=flask_server_timeout|error_code=FLASK_SERVER_TIMEOUT|retryable=True|source=flask_proxy
- T2|kind=timeout_simulated|status=flask_server_timeout|error_code=FLASK_SERVER_TIMEOUT|retryable=True|source=flask_proxy

## Verdict
- Input validation / load failure / runtime failure / network failure: 2-round consistent codes confirmed
- Timeout classification branch: 2-round deterministic code-path confirmation
