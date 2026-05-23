# Sorisae Dispatch Failure Code Standard (2026-05-05)

## Scope
- Endpoint: POST /api/marketplace/sorisae/dispatch
- Router source: backend/marketplace/sorisae_engine_router.py
- Engine source: backend/services/shinsegye/engine_hub.py

## Standard Failure Fields
All failure responses must include these fields.
- error_code: string
- error_message: string
- retryable: boolean
- source: string

Compatibility fields retained.
- status: string
- error: string (same value as error_message)
- result: null
- engine: string

## Error Code Matrix

### Input Validation
- condition: unregistered engine_type
- status: input_validation_error
- error_code: INPUT_ENGINE_TYPE_NOT_REGISTERED
- retryable: false
- source: router_validation
- HTTP: 400

### Module Load Failure
- condition: slot file missing or import error
- status: fallback
- error_code: ENGINE_LOAD_ERROR
- retryable: false
- source: module_loader
- HTTP: 200 (dispatch envelope)

### Runtime Exception
- condition: entry function execution failure
- status: error
- error_code: ENGINE_RUNTIME_ERROR
- retryable: false
- source: engine_runtime
- HTTP: 200 (dispatch envelope)

### Adapter Runtime Exception
- condition: adapter function execution failure
- status: adapter_error
- error_code: ENGINE_ADAPTER_RUNTIME_ERROR
- retryable: false
- source: engine_adapter
- HTTP: 200 (dispatch envelope)

### Flask Proxy Network Failure
- condition: Flask slot container unavailable, DNS/connection error
- status: flask_server_unavailable
- error_code: FLASK_SERVER_NETWORK_ERROR
- retryable: true
- source: flask_proxy
- HTTP: 200 (dispatch envelope)

### Flask Proxy Timeout
- condition: Flask proxy request timeout
- status: flask_server_timeout
- error_code: FLASK_SERVER_TIMEOUT
- retryable: true
- source: flask_proxy
- HTTP: 200 (dispatch envelope)

### Flask Proxy HTTP Failure
- condition: Flask slot returns HTTP error
- status: flask_server_http_error
- error_code: FLASK_SERVER_HTTP_ERROR
- retryable: true only when 5xx
- source: flask_proxy
- HTTP: 200 (dispatch envelope)

### Flask Proxy Unknown Failure
- condition: unexpected proxy exception
- status: flask_proxy_error
- error_code: FLASK_PROXY_ERROR
- retryable: true
- source: flask_proxy
- HTTP: 200 (dispatch envelope)

## Validation Rule
- Same failure scenario must return same error_code and source across two rounds.
- Evidence file: docs/evidence/sorisae-dispatch-failure-code-validation-rounds-20260505.md
