"""오케스트레이터 산출물 검증기 / semantic-gate (orchestrator.py 에서 분리).

생성 산출물 매니페스트에 대한 정적 검증(필수파일·임포트링크·정규화·AI구현·파이썬소스·프로파일
정합성)과 종합 semantic-gate 판정을 담당하는 순수 함수 모음. 외부 의존은 typing 과
orchestrator_scaffold_generators._strip_generated_id_headers 뿐 — orchestrator 와 순환 import 없음.
"""
from __future__ import annotations

from typing import Dict, List

from backend.llm.orchestrator_scaffold_generators import _strip_generated_id_headers

AI_ROUTER_PATH = "ai/router.py"


def _compat_build_manifest_lookup(manifest: List[Dict[str, str]]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for item in manifest:
        normalized_path = str(item.get("path") or "").strip().replace("\\", "/")
        if not normalized_path:
            continue
        lookup[normalized_path] = str(item.get("content") or "")
    return lookup


def _compat_domain_required_files(order_profile: Dict[str, Any], validation_profile: str) -> List[str]:
    if validation_profile == "nextjs_app":
        required = [
            "README.md",
            "package.json",
            "tsconfig.json",
            "next-env.d.ts",
            "app/page.tsx",
            "app/layout.tsx",
            "configs/app.env.example",
            "scripts/check.sh",
            "docs/architecture.md",
            "docs/order_profile.md",
            "docs/flow_map.md",
            "docs/flow_registry.json",
            "docs/usage.md",
            "docs/runtime.md",
            "docs/deployment.md",
            "docs/testing.md",
            "docs/scaffold_inventory.md",
            "docs/stage_progress.md",
            "docs/stage_progress.json",
        ]
    else:
        required = [
            "README.md",
            "requirements.txt",
            "pyproject.toml",
            "Dockerfile",
            "Makefile",
            "app/main.py",
            "app/routes.py",
            "app/services/__init__.py",
            "app/services/runtime_service.py",
            "app/runtime.py",
            "app/diagnostics.py",
            "app/order_profile.py",
            "backend/main.py",
            "backend/core/runtime.py",
            "backend/core/flow_registry.py",
            "backend/api/router.py",
            "backend/data/provider.py",
            "backend/service/application_service.py",
            "frontend/app/page.tsx",
            "frontend/components/order-summary.tsx",
            "frontend/components/runtime-shell.tsx",
            "frontend/lib/api-client.ts",
            "configs/app.env.example",
            "configs/logging.yml",
            "scripts/dev.sh",
            "scripts/check.sh",
            "infra/README.md",
            "infra/docker-compose.override.yml",
            "docs/architecture.md",
            "docs/order_profile.md",
            "docs/flow_map.md",
            "docs/flow_registry.json",
            "docs/usage.md",
            "docs/runtime.md",
            "docs/deployment.md",
            "docs/testing.md",
            "docs/scaffold_inventory.md",
            "docs/stage_progress.md",
            "docs/stage_progress.json",
            "tests/conftest.py",
            "tests/test_health.py",
            "tests/test_routes.py",
            "tests/test_runtime.py",
        ]
    profile_id = str(order_profile.get("profile_id") or "").strip()
    ai_enabled = bool(order_profile.get("ai_enabled"))
    if validation_profile == "python_fastapi" and profile_id in {"commerce_platform", "autonomous_multimall_platform"}:
        required.extend([
            "backend/app/external_adapters/status_client.py",
            "backend/app/connectors/base.py",
            "backend/app/connectors/shopify.py",
        ])
    if validation_profile == "python_fastapi" and profile_id == "deployment_kit_program":
        required.extend([
            "app/auth_routes.py",
            "app/ops_routes.py",
            "backend/app/external_adapters/status_client.py",
            "backend/app/connectors/base.py",
            "backend/app/connectors/payment_gateway.py",
            "backend/core/auth.py",
            "backend/core/security.py",
            "backend/service/catalog_service.py",
            "backend/service/order_workflow_service.py",
            "backend/service/operations_service.py",
            "tests/test_catalog_flow.py",
            "tests/test_order_workflow.py",
            "tests/test_publish_payload.py",
            "tests/test_security_runtime.py",
            "docs/runbook.md",
            "infra/prometheus.yml",
            "infra/deploy/security.md",
        ])
    if validation_profile == "python_fastapi" and profile_id in {"customer_program", "website_builder", "automation_service", "admin_console", "crm_suite", "booking_platform", "education_lms", "healthcare_portal", "analytics_platform", "lottery_prediction_system"}:
        required.extend([
            "app/auth_routes.py",
            "app/ops_routes.py",
            "backend/core/auth.py",
            "backend/core/security.py",
            "tests/test_security_runtime.py",
            "docs/runbook.md",
            "infra/prometheus.yml",
            "infra/deploy/security.md",
            "backend/app/external_adapters/status_client.py",
            "backend/app/connectors/base.py",
        ])
    if validation_profile == "python_fastapi" and profile_id == "trading_system":
        if ai_enabled:
            required.extend([
                "app/auth_routes.py",
                "app/ops_routes.py",
                "ai/adapters.py",
                "ai/schemas.py",
                AI_ROUTER_PATH,
                "tests/conftest.py",
                "backend/service/strategy_service.py",
                "backend/service/domain_adapter_service.py",
                "backend/core/__init__.py",
                "backend/core/database.py",
                "backend/core/models.py",
                "backend/core/auth.py",
                "backend/core/security.py",
                "backend/core/ops_logging.py",
                "tests/test_ai_pipeline.py",
                "tests/test_security_runtime.py",
                "docs/runbook.md",
                "infra/prometheus.yml",
                "infra/deploy/security.md",
            ])
    elif validation_profile == "python_fastapi" and ai_enabled:
        required.extend([
            "app/auth_routes.py",
            "app/ops_routes.py",
            "ai/adapters.py",
            "ai/schemas.py",
            AI_ROUTER_PATH,
            "backend/service/strategy_service.py",
            "backend/service/domain_adapter_service.py",
            "backend/core/__init__.py",
            "backend/core/database.py",
            "backend/core/models.py",
            "backend/core/auth.py",
            "backend/core/security.py",
            "backend/core/ops_logging.py",
            "tests/test_ai_pipeline.py",
            "tests/test_security_runtime.py",
            "docs/runbook.md",
            "infra/prometheus.yml",
            "infra/deploy/security.md",
        ])
    return list(dict.fromkeys(required))


def _compat_validate_runtime_completeness(
    manifest_lookup: Dict[str, str],
    order_profile: Dict[str, Any],
) -> List[str]:
    findings: List[str] = []
    if "package.json" in manifest_lookup:
        completeness_markers = {
            "README.md": ["Next.js 타입스크립트 기반 주문형 홈페이지 빌더 산출물", "npm run build", "npm run start"],
            "package.json": ["next", "react", '"build"'],
            "tsconfig.json": ["compilerOptions", "jsx"],
            "next-env.d.ts": ["reference types='next'"],
            "app/layout.tsx": ["RootLayout", "<html", "<body>"],
            "app/page.tsx": ["orderProfile.project_name", "요청 결과"],
            "docs/usage.md": ["사용 가이드"],
            "docs/runtime.md": ["requested_stack:"],
            "docs/deployment.md": ["npm run build", "npm run start"],
            "docs/testing.md": ["npm run build"],
            "configs/app.env.example": ["NEXT_PUBLIC_API_BASE_URL", "NODE_ENV=production"],
            "scripts/check.sh": ["npm run build"],
            "docs/order_profile.md": ["profile_id:", "mandatory_engine_contracts"],
            "docs/flow_map.md": ["flow map", "FLOW-001"],
            "docs/flow_registry.json": ["FLOW-001-1", "INTAKE"],
            "docs/scaffold_inventory.md": ["backend/main.py", "frontend/app/page.tsx"],
            "docs/stage_progress.md": ["stage progress", "tracking_id:"],
            "docs/stage_progress.json": ["current_stage", "stage_chain"],
        }
    else:
        completeness_markers = {
            "README.md": ["Included Runtime", "app/main.py", "backend/core", "frontend/app/page.tsx"],
            "requirements.txt": ["fastapi", "uvicorn", "pytest"],
            "pyproject.toml": ["[project]", "dependencies=["],
            "Dockerfile": ["FROM python:3.11-slim", "RUN pip install --no-cache-dir -r requirements.txt"],
            "Makefile": ["run:", "test:"],
            "app/main.py": ["FastAPI", "app.include_router(router)", "@app.get('/runtime')"],
            "app/routes.py": ["@router.get('/health')", "@router.get('/order-profile')", "@router.get('/report')"],
            "app/services/__init__.py": ["from app.services.runtime_service import", "build_runtime_payload", "__all__"],
            "app/services/runtime_service.py": ["build_feature_matrix", "build_domain_snapshot", "build_runtime_payload"],
            "app/runtime.py": ["build_runtime_context", "describe_runtime_profile"],
            "app/diagnostics.py": ["list_diagnostic_checks", "validate_runtime_payload", "build_diagnostic_report"],
            "app/order_profile.py": ["ORDER_PROFILE", "get_order_profile", "list_flow_steps"],
            "backend/core/runtime.py": ["build_scaffold_runtime"],
            "backend/core/flow_registry.py": ["FLOW_REGISTRY", "list_registered_steps"],
            "backend/data/provider.py": ["list_data_sources"],
            "backend/service/application_service.py": ["build_service_overview", "flow_steps", "layer"],
            "backend/api/router.py": ["get_router_snapshot", "trace_lookup"],
            "frontend/app/page.tsx": ["orderProfile.project_name", "orderProfile.summary"],
            "frontend/components/order-summary.tsx": ["export function OrderSummary", "items.map"],
            "frontend/components/runtime-shell.tsx": ["export function RuntimeShell", "summary"],
            "frontend/lib/api-client.ts": ["fetch(`${baseUrl}/runtime`", "runtime fetch failed"],
            "docs/order_profile.md": ["profile_id:", "mandatory_engine_contracts"],
            "docs/flow_map.md": ["flow map", "FLOW-001"],
            "docs/flow_registry.json": ["FLOW-001-1", "INTAKE"],
            "docs/usage.md": ["사용 가이드"],
            "docs/runtime.md": ["requested_stack:"],
            "docs/deployment.md": ["container run"],
            "docs/testing.md": ["pytest -q"],
            "docs/scaffold_inventory.md": ["backend/main.py", "frontend/app/page.tsx"],
            "docs/stage_progress.md": ["stage progress", "tracking_id:"],
            "docs/stage_progress.json": ["current_stage", "stage_chain"],
            "configs/app.env.example": ["APP_ENV=dev", "DATABASE_URL=", "JWT_SECRET=", "ALLOWED_HOSTS=", "CORS_ALLOW_ORIGINS=", "REQUEST_TIMEOUT_SEC=", "MODEL_REGISTRY_PATH=", "OPS_LOG_PATH=", "UPSTREAM_STATUS_BASE_URL=", "NOTIFICATION_GATEWAY_URL="],
            "configs/logging.yml": ["version: 1"],
            "scripts/dev.sh": ["uvicorn app.main:create_application --factory --reload"],
            "scripts/check.sh": ["pytest -q -s", "requirements.delivery.lock.txt"],
            "infra/README.md": ["deployment notes"],
            "infra/docker-compose.override.yml": ["services:", "uvicorn app.main:create_application --factory", "JWT_SECRET:", "healthcheck:"],
            "backend/core/auth.py": ["JWT_SECRET", "JWT_ALGORITHM", "JWT_EXPIRE_MINUTES", "scopes"],
            "backend/core/security.py": ["ALLOWED_HOSTS", "CORS_ALLOW_ORIGINS", "https_only", "REQUEST_TIMEOUT_SEC"],
            "backend/app/external_adapters/status_client.py": ["UPSTREAM_STATUS_BASE_URL", "NOTIFICATION_GATEWAY_URL", "REQUEST_TIMEOUT_SEC", "fetch_upstream_status"],
            "app/auth_routes.py": ["@auth_router.get('/settings')", "@auth_router.post('/token')"],
            "app/ops_routes.py": ["@ops_router.get('/status')", "@ops_router.get('/health')", "@ops_router.get('/metrics'"],
            "tests/conftest.py": ["PROJECT_ROOT", "sys.path.insert"],
            "tests/test_health.py": ["TestClient(app)", "client.get('/health')"],
            "tests/test_routes.py": ["client.get('/order-profile')", "client.get('/report')"],
            "tests/test_runtime.py": ["build_runtime_payload", "payload['service'] == 'customer-order-generator'"],
        }
    for path, markers in completeness_markers.items():
        content = _strip_generated_id_headers(manifest_lookup.get(path, ""))
        if not content:
            findings.append(f"runtime completeness missing file: {path}")
            continue
        for marker in markers:
            if marker not in content:
                findings.append(f"{path} missing runtime marker: {marker}")
    if "package.json" not in manifest_lookup and not bool(order_profile.get("ai_enabled")):
        frontend_page = manifest_lookup.get("frontend/app/page.tsx", "")
        for marker in ["Primary entities", "Requested outcomes", "Flow registry"]:
            if marker not in frontend_page:
                findings.append(f"frontend/app/page.tsx missing non-AI presentation marker: {marker}")
    return findings


def _compat_validate_import_links(manifest_lookup: Dict[str, str]) -> List[str]:
    findings: List[str] = []
    for path, content in manifest_lookup.items():
        if not path.endswith(".py"):
            continue
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line.startswith("from ") or " import " not in line:
                continue
            module_name = line[len("from "):].split(" import ", 1)[0].strip()
            if not module_name or module_name.startswith(("fastapi", "pydantic", "typing", "json", "datetime", "uvicorn", "pathlib", "sys", "__future__", "sqlalchemy", "jose", "os", "collections", "dataclasses", "functools", "backend.core")):
                continue
            module_path = module_name.replace('.', '/')
            candidate_paths = [
                f"{module_path}.py",
                f"{module_path}/__init__.py",
            ]
            if not any(candidate in manifest_lookup for candidate in candidate_paths):
                if module_name == "app.services":
                    preferred_target = "app/services/__init__.py"
                elif module_name.startswith("app.services."):
                    preferred_target = f"{module_path}.py"
                else:
                    preferred_target = candidate_paths[0]
                findings.append(f"{path}: missing import target {preferred_target}")
    return findings


def _compat_validate_required_files(manifest_lookup: Dict[str, str], required_files: List[str]) -> List[str]:
    missing = [path for path in required_files if path not in manifest_lookup]
    return [f"missing required file: {path}" for path in missing]


def _resolve_customer_common_required_files() -> List[str]:
    return _compat_domain_required_files(
        {
            "profile_id": "customer_program",
            "ai_enabled": False,
        },
        "python_fastapi",
    )


def _compat_validate_implementation_normalization(
    order_profile: Dict[str, Any],
    manifest_lookup: Dict[str, str],
    validation_profile: str,
) -> List[str]:
    findings: List[str] = []
    if validation_profile != "python_fastapi":
        return findings
    if not bool(order_profile.get("ai_enabled")):
        return findings

    profile_id = str(order_profile.get("profile_id") or "").strip()
    strategy_service = str(manifest_lookup.get("backend/service/strategy_service.py") or "")
    runtime_service = str(manifest_lookup.get("app/services/runtime_service.py") or "")
    ai_router = str(manifest_lookup.get(AI_ROUTER_PATH) or "")

    if profile_id == "document_writer_suite":
        document_lifecycle_markers = [
            "document lifecycle state",
            "document_state",
            "document-state",
            "document status",
            "document_status",
        ]
        if not any(marker in strategy_service or marker in runtime_service for marker in document_lifecycle_markers):
            findings.append("document lifecycle state marker missing")

        document_router_markers = [
            "DocumentInferenceRequest",
            "DocumentEvaluationRequest",
            "document typed ai router",
            "document_router",
            "document inference",
        ]
        if not any(marker in ai_router for marker in document_router_markers):
            findings.append("document typed AI router marker missing")

    if profile_id == "trading_system":
        trading_markers = [
            "build_risk_guard",
            "build_order_execution_plan",
            "build_portfolio_sync",
            "risk-guard",
            "order-execution",
            "portfolio-sync",
            "signals",
            "ai_runtime_contract",
        ]
        combined_sources = "\n".join(
            [
                strategy_service,
                runtime_service,
                ai_router,
                str(manifest_lookup.get("backend/app/connectors/broker.py") or ""),
            ]
        )
        broker_sources = str(manifest_lookup.get("backend/app/connectors/broker.py") or "")
        broker_markers = ["provider_contracts", "BROKER_LIVE_ACK_TOKEN", "live broker", "broker-adapter"]
        if not any(marker in broker_sources or marker.replace("-", "_") in broker_sources for marker in broker_markers):
            findings.append("trading implementation marker missing: broker-adapter")
        missing_trading_markers = [
            marker for marker in trading_markers
            if marker not in combined_sources and marker.replace("-", "_") not in combined_sources
        ]
        if missing_trading_markers:
            findings.extend([f"trading implementation marker missing: {marker}" for marker in missing_trading_markers])

    return findings


def _compat_validate_ai_implementation(
    order_profile: Dict[str, Any],
    manifest_lookup: Dict[str, str],
    validation_profile: str,
    required_files: List[str],
) -> List[str]:
    findings: List[str] = []
    if not bool(order_profile.get("ai_enabled")):
        return findings
    if validation_profile != "python_fastapi":
        return findings
    profile_id = str(order_profile.get("profile_id") or "").strip()
    mandatory_engine_contracts = [
        str(item).strip()
        for item in (order_profile.get("mandatory_engine_contracts") or [])
        if str(item).strip()
    ]
    strategy_service_required = "backend/service/strategy_service.py" in required_files
    if not strategy_service_required:
        return findings
    strategy_service = manifest_lookup.get("backend/service/strategy_service.py", "")
    if not strategy_service:
        findings.append("AI profile requires backend/service/strategy_service.py")
        return findings
    required_markers = [
        "build_strategy_service_overview",
        "load_model_registry",
        "run_training_pipeline",
        "run_inference_runtime",
        "build_evaluation_report",
        "ai_capabilities",
        "inference_runtime",
        "training_pipeline",
        "evaluation_report",
    ]
    for marker in required_markers:
        if marker not in strategy_service:
            findings.append(f"backend/service/strategy_service.py missing AI marker: {marker}")
    if "placeholder" in strategy_service.lower():
        findings.append("backend/service/strategy_service.py contains placeholder AI implementation")
    adapters_module = manifest_lookup.get("ai/adapters.py", "")
    adapter_markers = ["resolve_adapter", "decision_key", "default_decision"]
    for marker in adapter_markers:
        if marker not in adapters_module:
            findings.append(f"ai/adapters.py missing adapter marker: {marker}")
    domain_adapter_service = manifest_lookup.get("backend/service/domain_adapter_service.py", "")
    for marker in ["build_domain_adapter_summary", "resolve_adapter", "build_feature_set"]:
        if marker not in domain_adapter_service:
            findings.append(f"backend/service/domain_adapter_service.py missing domain adapter marker: {marker}")
    app_services = "\n".join([
        manifest_lookup.get("app/services/__init__.py", ""),
        manifest_lookup.get("app/services/runtime_service.py", ""),
    ])
    if "build_feature_matrix" not in app_services or "build_domain_snapshot" not in app_services:
        findings.append("app/services/__init__.py + app/services/runtime_service.py missing runtime/service bridge markers")
    api_router = manifest_lookup.get("backend/api/router.py", "")
    api_router_markers = [
        "get_ai_runtime_snapshot",
        "model_registry",
        "training_pipeline",
        "inference_runtime",
        "evaluation_report",
    ]
    for marker in api_router_markers:
        if marker not in api_router:
            findings.append(f"backend/api/router.py missing AI API marker: {marker}")
    app_main = manifest_lookup.get("app/main.py", "")
    app_main_markers = ["from ai.router import router as ai_router", "app.include_router(ai_router)"]
    app_main_markers.extend(["from app.auth_routes import auth_router", "from app.ops_routes import ops_router", "app.include_router(auth_router)", "app.include_router(ops_router)"])
    for marker in app_main_markers:
        if marker not in app_main:
            findings.append(f"app/main.py missing AI router binding marker: {marker}")
    ai_router = manifest_lookup.get(AI_ROUTER_PATH, "")
    ai_router_markers = [
        "router = APIRouter(prefix='/ai'",
        "@router.get('/health')",
        "@router.post('/train')",
        "@router.post('/inference')",
        "@router.post('/evaluate')",
        "InferenceRequest",
        "TrainingRequest",
        "EvaluationRequest",
    ]
    for marker in ai_router_markers:
        if marker not in ai_router:
            findings.append(f"{AI_ROUTER_PATH} missing AI endpoint marker: {marker}")
    ai_schemas = manifest_lookup.get("ai/schemas.py", "")
    ai_schema_markers = ["class InferenceRequest", "class TrainingRequest", "class EvaluationRequest"]
    for marker in ai_schema_markers:
        if marker not in ai_schemas:
            findings.append(f"ai/schemas.py missing schema marker: {marker}")
    tests_routes = manifest_lookup.get("tests/test_routes.py", "")
    route_test_markers = ["get_ai_runtime_snapshot", "test_ai_fastapi_endpoints", "/ai/health", "/ai/inference", "/ai/evaluate"]
    for marker in route_test_markers:
        if marker not in tests_routes:
            findings.append(f"tests/test_routes.py missing AI route marker: {marker}")
    tests_health = manifest_lookup.get("tests/test_health.py", "")
    if "ai_contract_ready" not in tests_health:
        findings.append("tests/test_health.py missing ai_contract_ready assertion")
    tests_runtime = manifest_lookup.get("tests/test_runtime.py", "")
    if "ai_runtime_contract" not in tests_runtime:
        findings.append("tests/test_runtime.py missing ai_runtime_contract assertion")
    diagnostics = manifest_lookup.get("app/diagnostics.py", "")
    diagnostics_markers = ["ai-runtime-contract-ready", "ai-health-report-validated", "ai_validation"]
    for marker in diagnostics_markers:
        if marker not in diagnostics:
            findings.append(f"app/diagnostics.py missing AI report marker: {marker}")
    for core_file, core_markers in {
        "backend/core/database.py": ["get_database_settings", "DB_SETTINGS"],
        "backend/core/models.py": ["class RuntimeEvent", "class ModelRegistryEntry"],
        "backend/core/auth.py": ["get_auth_settings", "AUTH_SETTINGS"],
        "backend/core/ops_logging.py": ["record_ops_log", "list_ops_logs"],
    }.items():
        content = manifest_lookup.get(core_file, "")
        for marker in core_markers:
            if marker not in content:
                findings.append(f"{core_file} missing core contract marker: {marker}")
    app_services = "\n".join([
        manifest_lookup.get("app/services/__init__.py", ""),
        manifest_lookup.get("app/services/runtime_service.py", ""),
    ])
    contract_markers = [
        "build_ai_runtime_contract",
        "InferenceRequest",
        "TrainingRequest",
        "EvaluationRequest",
        "ai_runtime_contract",
        "/ai/health",
        "/ai/train",
        "/ai/inference",
        "/ai/evaluate",
        "get_database_settings",
        "get_auth_settings",
        "record_ops_log",
        "build_domain_adapter_summary",
        "ensure_database_ready",
        "create_access_token",
    ]
    for marker in contract_markers:
        if marker not in app_services:
            findings.append(f"app/services/__init__.py + app/services/runtime_service.py missing AI contract marker: {marker}")
    if "checked_via': ['/health', '/report']" not in app_services and 'checked_via": ["/health", "/report"]' not in app_services:
        findings.append("app/services/__init__.py + app/services/runtime_service.py missing /health and /report validation trace")
    if "ai_runtime_snapshot" not in tests_routes and "get_ai_runtime_snapshot" not in tests_routes:
        findings.append("tests/test_routes.py missing AI runtime route coverage marker")
    frontend_page = manifest_lookup.get("frontend/app/page.tsx", "")
    frontend_markers = ["AI 상태 패널", "model_registry", "training_pipeline", "inference_runtime", "evaluation_report"]
    for marker in frontend_markers:
        if marker not in frontend_page:
            findings.append(f"frontend/app/page.tsx missing AI UI marker: {marker}")
    for deploy_file, deploy_markers in {
        "infra/prometheus.yml": ["scrape_configs", "targets"],
        "infra/deploy/security.md": ["JWT_SECRET", "DATABASE_URL", "TLS"],
    }.items():
        content = manifest_lookup.get(deploy_file, "")
        for marker in deploy_markers:
            if marker not in content:
                findings.append(f"{deploy_file} missing deployment marker: {marker}")
    if "AI 상태 패널" not in frontend_page and "ai_capabilities" not in frontend_page and "model_registry" not in frontend_page:
        findings.append("frontend/app/page.tsx missing AI presentation markers")
    if mandatory_engine_contracts:
        order_profile_doc = manifest_lookup.get("docs/order_profile.md", "")
        for marker in mandatory_engine_contracts:
            if marker not in order_profile_doc:
                findings.append(f"docs/order_profile.md missing mandatory engine contract marker: {marker}")
        for marker in mandatory_engine_contracts:
            normalized_marker = marker.replace("-", "_")
            if marker not in app_services and normalized_marker not in app_services:
                findings.append(f"app/services/__init__.py + app/services/runtime_service.py missing mandatory engine contract marker: {marker}")
        if profile_id == "lottery_prediction_system":
            lottery_markers = [
                "draw_histories",
                "prediction_runs",
                "candidate_sets",
                "candidate-number-generator",
                "prediction-evaluation",
            ]
            for marker in lottery_markers:
                normalized_marker = marker.replace("-", "_")
                if (
                    marker not in app_services
                    and normalized_marker not in app_services
                    and marker not in strategy_service
                    and normalized_marker not in strategy_service
                ):
                    findings.append(f"lottery prediction engine missing marker: {marker}")
        if profile_id == "trading_system":
            trading_markers = [
                "signal-ingestion",
                "risk-guard",
                "order-execution",
                "portfolio-sync",
                "broker-adapter",
            ]
            trading_sources = [
                strategy_service,
                manifest_lookup.get("ai/features.py", ""),
                manifest_lookup.get("ai/inference.py", ""),
                manifest_lookup.get("app/services/__init__.py", ""),
                manifest_lookup.get("app/services/runtime_service.py", ""),
            ]
            for marker in trading_markers:
                normalized_marker = marker.replace("-", "_")
                if not any(
                    marker in source or normalized_marker in source
                    for source in trading_sources
                ):
                    findings.append(f"trading engine missing marker: {marker}")
            for marker in ["build_risk_guard", "build_order_execution_plan", "build_portfolio_sync"]:
                if marker not in strategy_service:
                    findings.append(f"backend/service/strategy_service.py missing trading marker: {marker}")
    return findings


def _compat_validate_python_sources(manifest_lookup: Dict[str, str]) -> List[str]:
    findings: List[str] = []
    for path, content in manifest_lookup.items():
        if not path.endswith(".py"):
            continue
        if any(path.startswith(prefix) for prefix in ["app/", "backend/", "tests/"]) and "package.json" in manifest_lookup:
            continue
        normalized = str(content or "")
        if not normalized.strip():
            if not path.endswith("__init__.py"):
                findings.append(f"{path} is empty python source")
            continue
        if "compat generated file" in normalized:
            findings.append(f"{path} contains placeholder compat content")
            continue
        try:
            compile(normalized, path, "exec")
        except SyntaxError as exc:
            findings.append(f"{path} has syntax error: {exc.msg}")
    return findings


def _compat_validate_profile_alignment(
    task: str,
    project_name: str,
    order_profile: Dict[str, Any],
) -> List[str]:
    task_text = str(task or "").lower()
    project_name_text = str(project_name or "").lower()
    source_text = f"{task_text}\n{project_name_text}"
    profile_id = str(order_profile.get("profile_id") or "").strip()
    findings: List[str] = []
    explicit_task_domains = [
        (
            "autonomous_multimall_platform",
            ["멀티 쇼핑몰", "멀티쇼핑몰", "multimall", "multi mall", "tenant", "fulfillment", "캠페인", "campaign"],
        ),
        (
            "trading_system",
            ["자동매매", "트레이딩", "주식", "매매", "trading", "stock", "portfolio", "signal"],
        ),
    ]
    for expected_profile_id, markers in explicit_task_domains:
        if any(marker.lower() in task_text for marker in markers):
            if profile_id != expected_profile_id:
                findings.append(
                    f"profile mismatch: expected {expected_profile_id} for task/project context, got {profile_id or 'unknown'}"
                )
            return findings
    domain_markers = [
        (
            "autonomous_multimall_platform",
            ["멀티 쇼핑몰", "멀티쇼핑몰", "multimall", "multi mall", "tenant", "fulfillment", "campaign"],
        ),
        (
            "commerce_platform",
            ["쇼핑몰", "마켓플레이스", "이커머스", "커머스", "commerce", "marketplace", "store"],
        ),
        (
            "trading_system",
            ["자동매매", "트레이딩", "주식", "trading", "stock", "portfolio"],
        ),
    ]
    for expected_profile_id, markers in domain_markers:
        if any(marker in source_text for marker in markers) and profile_id != expected_profile_id:
            findings.append(
                f"profile mismatch: expected {expected_profile_id} for task/project context, got {profile_id or 'unknown'}"
            )
            break
    return findings


def _compat_run_semantic_gate(
    task: str,
    project_name: str,
    order_profile: Dict[str, Any],
    validation_profile: str,
    manifest: List[Dict[str, str]],
) -> Dict[str, Any]:
    manifest_lookup = _compat_build_manifest_lookup(manifest)
    required_files = _compat_domain_required_files(order_profile, validation_profile)
    findings: List[str] = []
    findings.extend(_compat_validate_required_files(manifest_lookup, required_files))
    findings.extend(_compat_validate_import_links(manifest_lookup))
    findings.extend(_compat_validate_python_sources(manifest_lookup))
    findings.extend(_compat_validate_runtime_completeness(manifest_lookup, order_profile))
    findings.extend(_compat_validate_profile_alignment(task, project_name, order_profile))
    findings.extend(_compat_validate_implementation_normalization(order_profile, manifest_lookup, validation_profile))
    findings.extend(_compat_validate_ai_implementation(order_profile, manifest_lookup, validation_profile, required_files))
    packaging_targets = [
        "README.md",
        "docs/usage.md",
        "docs/runtime.md",
        "docs/deployment.md",
        "docs/testing.md",
        "configs/app.env.example",
    ]
    for packaging_path in packaging_targets:
        if packaging_path not in manifest_lookup:
            findings.append(f"missing packaging file: {packaging_path}")
    unique_findings = list(dict.fromkeys(findings))
    ok = len(unique_findings) == 0
    score = 100 if ok else max(0, 100 - (len(unique_findings) * 18))
    summary = "semantic gate passed" if ok else "; ".join(unique_findings[:6])
    return {
        "ok": ok,
        "score": score,
        "summary": summary,
        "checklist": unique_findings,
        "checklist_items": [
            {
                "title": finding,
                "status": "passed" if ok else "failed",
                "detail": finding,
            }
            for finding in unique_findings
        ],
        "required_files": required_files,
    }
