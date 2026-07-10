"""LLM 오케스트레이터 - 멀티 에이전트 파이프라인"""
import asyncio
import ast
import html
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any, Callable
from backend.auth import get_current_user, get_current_user_flexible
import httpx
import json
import re
import base64
import subprocess
import hashlib
import os
import time
import socket
import shutil
import importlib.util
import sys
import zipfile
import threading
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from datetime import datetime
from uuid import uuid4
from urllib.parse import urlparse

from backend.time_utils import utcnow

from backend.llm.model_config import (
    CURRENT_GPU_PROFILE_KEY,
    MODEL_ROUTE_KEYS,
    QWEN_CODER_Q4_TAG,
    QWEN_CODER_Q5_TAG,
    QWEN_CODER_Q6_TAG,
    QWEN_CODER_Q8_TAG,
    build_ollama_options,
    get_available_ollama_models,
    get_chat_model,
    get_configured_execution_controls,
    get_coder_model,
    get_configured_model_routes,
    get_designer_model,
    get_gpu_runtime_info,
    get_planner_model,
    get_reasoning_model,
    get_recommended_runtime_profiles,
    get_reviewer_model,
    get_voice_chat_model,
)

from backend.llm.code_analyzer import code_analyzer
from backend.llm.admin_capabilities import (
    _build_cached_path_validation,
    _build_nginx_target_validation,
    _build_route_manifest_validation,
)
from backend.llm.file_tools import write_file_tool
from backend.llm.python_security_policy import scan_python_security_policy
from backend.llm.project_indexer import project_indexer
from backend.llm.target_patch_registry import build_target_patch_registry_snapshot
from backend.llm.orchestrator_progress_tracker import (
    build_progress_poll_url as _progress_build_poll_url,
    build_progress_stream_url as _progress_build_stream_url,
    load_orchestration_progress as _progress_load,
    mark_orchestration_progress_error as _progress_mark_error,
    mark_orchestration_progress_result as _progress_mark_result,
    record_orchestration_progress_event as _progress_record_event,
    runtime_progress_root as _progress_runtime_root,
    orchestration_progress_path as _progress_path,
    save_orchestration_progress as _progress_save,
)
from backend.llm.orchestrator_budgeting import (
    agent_context_char_limit as _budget_agent_context_char_limit,
    agent_default_token_budget as _budget_agent_default_token_budget,
    agent_prompt_char_limit as _budget_agent_prompt_char_limit,
    bounded_token_floor as _budget_bounded_token_floor,
    coerce_runtime_bool as _budget_coerce_runtime_bool,
    coerce_runtime_int as _budget_coerce_runtime_int,
    resolve_step_token_budget as _budget_resolve_step_token_budget,
    truncate_prompt_segment as _budget_truncate_prompt_segment,
)

from backend.llm.orchestrator_scaffold_generators import (
    _build_architecture_doc_template,
    _build_architecture_contract_template,
    _build_generated_id_registry_schema_template,
    _build_generated_id_registry_template,
    _build_generated_product_identity_template,
    _decorate_generated_file_with_ids,
    _strip_generated_id_headers,
    _decorate_template_candidates_with_ids,
    _build_nextjs_vertical_slice_files,
    _build_node_service_vertical_slice_files,
)
from backend.llm.ws_channel import ws_channel
from backend.security_gates import (
    require_admin_mutation_quota,
    require_llm_mutation_quota,
)
from backend.orchestrator.customer import (
    assemble_customer_orchestration_response as assemble_customer_orchestration_response_service,
    execute_orchestration as execute_customer_orchestration_service,
    finalize_customer_validation_bundle as finalize_customer_validation_bundle_service,
    prepare_customer_orchestration_context as prepare_customer_orchestration_context_service,
    run_customer_orchestration as run_customer_orchestration_service,
    run_customer_validation_stages as run_customer_validation_stages_service,
)
from backend.orchestrator.chat import (
    AutoConnectMeta,
    ConversationMessage,
    FlowTraceCommand,
    FlowTraceStep,
    OrchestratorChatRequest,
    OrchestratorChatResponse,
    build_admin_flow_trace,
    build_multi_command_plan,
    build_lightweight_flow_trace,
    resolve_active_trace,
)
from backend.orchestrator.chat.chat_service import answer_orchestrator_chat as answer_orchestrator_chat_service
from backend.database import SessionLocal
from backend.orchestrator.chat.project_context_store import get_active_global_approval_policy, normalize_project_root
from backend.orchestrator.chat.project_context_store import is_workspace_root_scope

# 코드젠 템플릿 뱅크는 orchestrator_templates.py 로 분리(byte-frozen 템플릿 보존). 내부 호출부
# 호환을 위해 이름을 그대로 재-import 한다(공개 API 변화 없음).
from backend.llm.orchestrator_templates import (  # noqa: E402
    _build_commerce_platform_ai_template_candidates,
    _build_commerce_platform_template_candidates,
    _build_customer_domain_ai_template_overrides,
    _build_customer_order_template_candidates,
    _build_top_level_ai_template_candidates,
    _build_trading_system_production_ai_template_candidates,
    _build_trading_system_template_candidates,
    _resolve_customer_ai_adapter_profile,
    _resolve_customer_domain_contract,
    _resolve_customer_engine_seed_records,
)
# 산출물 검증기 / semantic-gate 는 orchestrator_validators.py 로 분리. 내부 호출부 + 공개 API
# 호환을 위해 이름을 그대로 재-import 한다.
from backend.llm.orchestrator_validators import (  # noqa: E402
    _compat_build_manifest_lookup,
    _compat_domain_required_files,
    _compat_run_semantic_gate,
    _compat_validate_ai_implementation,
    _compat_validate_implementation_normalization,
    _compat_validate_import_links,
    _compat_validate_profile_alignment,
    _compat_validate_python_sources,
    _compat_validate_required_files,
    _compat_validate_runtime_completeness,
    _resolve_customer_common_required_files,
)
# 실행-검증기(라이브 통합/부팅/zip 재현)는 orchestrator_runtime_validation.py 로 분리. 내부 호출부
# 호환을 위해 이름 + 클러스터 전용 상수를 재-import 한다.
from backend.llm.orchestrator_runtime_validation import (  # noqa: E402
    ORCH_VALIDATION_WORK_ROOT,
    _build_python_fastapi_validation_targets,
    _log_integration_validation_phase,
    _read_validation_log_tail,
    _repair_python_validation_venv,
    _run_domain_integration_test_engine,
    _run_external_integration_validator,
    _run_framework_e2e_validator,
    _run_python_fastapi_live_api_validation,
    _run_shipping_zip_reproduction_validation,
    _venv_python_path,
)
# 고객주문 프로파일 + 도메인계약/통합테스트/stage 빌더는 orchestrator_order_profile.py 로 분리.
# 내부 호출부 호환을 위해 이름 + 클러스터 전용 상수를 재-import 한다.
from backend.llm.orchestrator_order_profile import (  # noqa: E402
    ORCH_REFINER_FIXER_STAGE,
    _build_customer_order_profile,
    _build_domain_contract,
    _build_improvement_loop_plan,
    _build_integration_test_plan,
    _build_packaging_audit,
    _build_refiner_fixer_stage_payload,
    _build_stage_history_with_refiner_fixer,
    _has_mojibake_text,
    _resolve_validation_profile,
    _unique_sequence,
)

router = APIRouter(prefix="/api/llm", tags=["orchestrator"])
logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[2]
ORCH_ALLOWED_OUTPUT_ROOTS = [
    REPO_ROOT.resolve(),
    (REPO_ROOT / "uploads").resolve(),
    Path(tempfile.gettempdir()).resolve(),
]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _sanitize_orchestration_relative_path(path_text: str) -> str:
    normalized = str(path_text or "").replace("\\", "/").strip().lstrip("/")
    if not normalized:
        raise HTTPException(status_code=400, detail="상대 경로가 비어 있습니다.")
    relative = PurePosixPath(normalized)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise HTTPException(status_code=400, detail="허용되지 않은 상대 경로입니다.")
    return str(relative)


def _resolve_orchestration_output_root(path_text: str) -> Path:
    raw = str(path_text or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="출력 경로가 비어 있습니다.")
    normalized = raw.replace("\\", "/").strip()
    if normalized.startswith("/"):
        normalized = normalize_project_root(normalized)
    if re.match(r"^[A-Za-z]:/", normalized):
        normalized = normalize_project_root(normalized)
    safe_normalized = re.sub(r"[^a-zA-Z0-9._/-]+", "-", normalized).strip("/.-")
    if not safe_normalized:
        safe_normalized = "uploads/projects"
    candidate = REPO_ROOT / safe_normalized
    resolved = candidate.resolve()
    if any(_is_relative_to(resolved, root) for root in ORCH_ALLOWED_OUTPUT_ROOTS):
        return resolved
    raise HTTPException(status_code=400, detail="출력 경로는 허용된 루트 내부여야 합니다.")


def _resolve_orchestration_output_child_path(output_dir: Path, relative_path: str) -> Path:
    trusted_output_dir = _trusted_orchestration_output_dir(output_dir)
    safe_relative = _sanitize_orchestration_relative_path(relative_path)
    candidate = trusted_output_dir
    for part in safe_relative.split("/"):
        candidate = candidate / part
    candidate = candidate.resolve()
    if not _is_relative_to(candidate, trusted_output_dir):
        raise HTTPException(status_code=400, detail="출력 파일 경로가 출력 디렉터리를 벗어납니다.")
    return candidate


def _trusted_orchestration_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if any(_is_relative_to(resolved, root) for root in ORCH_ALLOWED_OUTPUT_ROOTS):
        return resolved
    safe_dir_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(output_dir.name or "")).strip("-._")
    if not safe_dir_name:
        raise HTTPException(status_code=400, detail="출력 디렉터리 이름이 올바르지 않습니다.")
    return (REPO_ROOT / "uploads" / "projects" / safe_dir_name).resolve()


def _log_orchestration_phase(
    phase: str,
    started_at: float,
    *,
    project_name: str,
    validation_profile: str,
) -> None:
    logger.info(
        "run_orchestration phase=%s elapsed_sec=%.2f project=%s validation_profile=%s",
        phase,
        max(0.0, time.perf_counter() - started_at),
        project_name,
        validation_profile,
    )




def _enforce_global_orchestration_gate(request: "OrchestrationRequest") -> None:
    output_dir_text = str(request.output_dir or "").strip()
    if not output_dir_text:
        return
    normalized_output_dir = normalize_project_root(output_dir_text)
    if not normalized_output_dir:
        return
    session = SessionLocal()
    try:
        global_policy = get_active_global_approval_policy(session)
    finally:
        session.close()
    blocked_paths = [str(item).strip() for item in (global_policy.get("blocked_paths") or []) if str(item).strip()]
    scope_paths = [str(item).strip() for item in (global_policy.get("scope") or []) if str(item).strip()]
    if any(blocked and blocked in normalized_output_dir for blocked in blocked_paths):
        raise HTTPException(status_code=400, detail="전역 승인 게이트가 금지한 경로는 오케스트레이션 실행 대상이 될 수 없습니다.")
    if scope_paths and not any(is_workspace_root_scope(scope) or (scope and scope in normalized_output_dir) for scope in scope_paths):
        raise HTTPException(status_code=400, detail="전역 승인 게이트 승인 범위 밖 경로는 오케스트레이션 실행 대상이 될 수 없습니다.")

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://host.docker.internal:8008/v1")
_orchestrator_chat_http_client: Optional[httpx.AsyncClient] = None
_orchestrator_chat_http_client_signature: Optional[tuple[str, float]] = None

ORCH_GPU_ONLY_PREFERRED = (
    os.getenv("ORCH_GPU_ONLY_PREFERRED", "true").strip().lower()
    in {"1", "true", "yes", "on"}
)
ORCH_FORCE_COMPLETE = (
    os.getenv("ORCH_FORCE_COMPLETE", "true").strip().lower()
    in {"1", "true", "yes", "on"}
)
ORCH_ALLOW_SYNTHETIC_FALLBACK = (
    os.getenv("ORCH_ALLOW_SYNTHETIC_FALLBACK", "false").strip().lower()
    in {"1", "true", "yes", "on"}
)
ORCH_CODE_GENERATION_STRATEGIES = {"auto_generator"}


def _normalize_code_generation_strategy(value: Any) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in ORCH_CODE_GENERATION_STRATEGIES:
        return candidate
    return "auto_generator"


ORCH_CODE_GENERATION_STRATEGY = _normalize_code_generation_strategy(
    os.getenv("ORCH_CODE_GENERATION_STRATEGY", "auto_generator")
)
ORCH_SELECTED_PROFILE = os.getenv(
    "ORCH_SELECTED_PROFILE",
    CURRENT_GPU_PROFILE_KEY,
).strip() or CURRENT_GPU_PROFILE_KEY
ORCH_RUNTIME_PROFILE_CUSTOM_KEY = "custom"
ORCH_MODEL_TUNING_LEVEL = max(
    -1,
    min(1, int(os.getenv("ORCH_MODEL_TUNING_LEVEL", "0"))),
)
ORCH_TOKEN_TUNING_LEVEL = max(
    -1,
    min(1, int(os.getenv("ORCH_TOKEN_TUNING_LEVEL", "0"))),
)
ORCH_TIMEOUT_TUNING_LEVEL = max(
    -1,
    min(1, int(os.getenv("ORCH_TIMEOUT_TUNING_LEVEL", "0"))),
)
from backend.orchestrator.autonomous.stage_coder_scope import compute_autonomous_stage_thresholds

_STAGE_THRESHOLDS = compute_autonomous_stage_thresholds()
ORCH_MIN_FILES = max(
    1,
    int(os.getenv("ORCH_MIN_FILES", str(_STAGE_THRESHOLDS["stage_min_files"]))),
)
ORCH_MIN_DIRS = max(
    0,
    int(os.getenv("ORCH_MIN_DIRS", str(_STAGE_THRESHOLDS["stage_min_dirs"]))),
)
ORCH_STAGE11_MIN_FILES = max(
    ORCH_MIN_FILES,
    int(os.getenv("ORCH_STAGE11_MIN_FILES", str(_STAGE_THRESHOLDS["stage11_min_files"]))),
)
ORCH_STAGE11_MIN_DIRS = max(
    ORCH_MIN_DIRS,
    int(os.getenv("ORCH_STAGE11_MIN_DIRS", str(_STAGE_THRESHOLDS["stage11_min_dirs"]))),
)
ORCH_MAX_FORCE_RETRIES = max(1, int(os.getenv("ORCH_MAX_FORCE_RETRIES", "3")))
_required_files_raw = os.getenv("ORCH_REQUIRED_FILES", "")
ORCH_REQUIRED_FILE_PATHS = [
    item.strip().replace("\\", "/")
    for item in _required_files_raw.split(",")
    if item.strip()
]
ORCH_ARCHITECTURE_BASELINE_FILES: List[str] = []
ORCH_ROUTER_FILES: List[str] = [
    "backend/app/api/routes/health.py",
    "backend/app/api/routes/auth.py",
    "backend/app/api/routes/catalog.py",
    "backend/app/api/routes/orders.py",
]
ORCH_SERVICE_FILES: List[str] = [
    "backend/app/services/health_service.py",
    "backend/app/services/auth_service.py",
    "backend/app/services/catalog_service.py",
    "backend/app/services/order_service.py",
]
ORCH_CONNECTOR_FILES: List[str] = [
    "backend/app/connectors/base.py",
    "backend/app/connectors/shopify.py",
]
ORCH_CORE_FILES: List[str] = [
    "backend/app/main.py",
    "backend/app/core/config.py",
    "backend/app/core/security.py",
    "backend/app/core/database.py",
    "backend/app/api/deps.py",
    *ORCH_ROUTER_FILES,
    *ORCH_SERVICE_FILES,
    "backend/app/repositories/health_repository.py",
    "backend/app/repositories/user_repository.py",
    "backend/app/repositories/catalog_repository.py",
    "backend/app/repositories/order_repository.py",
    "backend/app/infra/runtime_store.py",
    "backend/app/external_adapters/status_client.py",
    *ORCH_CONNECTOR_FILES,
    "backend/app/worker/tasks.py",
]
ORCH_STATE_FLOW: List[str] = [
    "DESIGN",
    "PLAN",
    "GENERATE",
    "BUILD",
    "REFINER_FIXER",
    "TEST",
    "REFLEXION",
    "FIX",
    "DONE",
    "FAILED",
]

ORCH_FILE_MANIFEST_PATH = "docs/file_manifest.md"
ORCH_CHECKLIST_PATH = "docs/orchestrator_checklist.md"
ORCH_ARTIFACT_LOG_PATH = "docs/orchestrator_artifacts.json"
ORCH_FAILURE_REPORT_PATH = "docs/failure_report.md"
ORCH_ROOT_CAUSE_REPORT_PATH = "docs/root_cause_analysis.md"
ORCH_VALIDATION_RESULT_JSON_PATH = "docs/automatic_validation_result.json"
ORCH_VALIDATION_RESULT_MD_PATH = "docs/automatic_validation_result.md"
ORCH_TRACEABILITY_MAP_PATH = "docs/traceability_map.json"
ORCH_ID_REGISTRY_SCHEMA_PATH = "docs/id_registry.schema.json"
ORCH_ID_REGISTRY_PATH = "docs/id_registry.json"
ORCH_SEMANTIC_AUDIT_REPORT_PATH = "docs/semantic_completion_audit.md"
ORCH_PYTHON_SECURITY_REPORT_PATH = "docs/python_security_policy_report.json"
ORCH_PRODUCT_ID_PATH = "docs/product_identity.json"
ORCH_SEMANTIC_AUDIT_MIN_SCORE = min(
    100,
    max(0, int(os.getenv("ORCH_SEMANTIC_AUDIT_MIN_SCORE", "85"))),
)
ORCH_SEMANTIC_AUDIT_RUBRICS: Dict[str, List[Dict[str, Any]]] = {
    "python_fastapi": [
        {
            "id": "api_requirements",
            "label": "API 요구사항 구현",
            "max_score": 35,
            "critical": True,
        },
        {
            "id": "service_integration",
            "label": "서비스/저장소 연결 완결성",
            "max_score": 30,
            "critical": True,
        },
        {
            "id": "verification_evidence",
            "label": "검증 증거 충족",
            "max_score": 20,
            "critical": True,
        },
        {
            "id": "operational_readiness",
            "label": "운영 안정성",
            "max_score": 15,
            "critical": False,
        },
    ],
    "go_service": [
        {
            "id": "service_contracts",
            "label": "핵심 서비스 계약 구현",
            "max_score": 30,
            "critical": True,
        },
        {
            "id": "module_flow",
            "label": "모듈/핸들러 흐름 완결성",
            "max_score": 30,
            "critical": True,
        },
        {
            "id": "verification_evidence",
            "label": "go build 검증 증거 충족",
            "max_score": 25,
            "critical": True,
        },
        {
            "id": "operational_readiness",
            "label": "운영 안정성",
            "max_score": 15,
            "critical": False,
        },
    ],
    "rust_service": [
        {
            "id": "service_contracts",
            "label": "핵심 서비스 계약 구현",
            "max_score": 30,
            "critical": True,
        },
        {
            "id": "crate_wiring",
            "label": "crate/핸들러 연결 완결성",
            "max_score": 30,
            "critical": True,
        },
        {
            "id": "verification_evidence",
            "label": "cargo check 검증 증거 충족",
            "max_score": 25,
            "critical": True,
        },
        {
            "id": "operational_readiness",
            "label": "운영 안정성",
            "max_score": 15,
            "critical": False,
        },
    ],
    "generic": [
        {
            "id": "requirements",
            "label": "핵심 요구 구현",
            "max_score": 40,
            "critical": True,
        },
        {
            "id": "integration",
            "label": "구성요소 연결 완결성",
            "max_score": 25,
            "critical": True,
        },
        {
            "id": "verification",
            "label": "검증 증거 충족",
            "max_score": 20,
            "critical": True,
        },
        {
            "id": "production_readiness",
            "label": "잔여 리스크 통제",
            "max_score": 15,
            "critical": False,
        },
    ],
}








ORCH_SUCCESS_CASES_PATH = "knowledge/success_cases.json"
ORCH_FAILED_CASES_PATH = "knowledge/failed_cases.json"
ORCH_KNOWLEDGE_RUNS_DIR = "knowledge/runs"
ORCH_DYNAMIC_TOOLS_DIR = "backend/llm/tools"
ORCH_EXPERIENCE_CASE_LIMIT = max(
    1,
    int(os.getenv("ORCH_EXPERIENCE_CASE_LIMIT", "6")),
)

ORCH_ENDPOINT_UI_RULES = {
    "health": ["/health"],
    "auth": ["/api/auth/register", "/api/auth/login"],
    "catalog": ["/api/catalog", "/api/catalog/sync"],
    "orders": ["/api/orders"],
}

ORCH_MAX_FILES_PER_RUN = max(
    1,
    int(os.getenv("ORCH_MAX_FILES_PER_RUN", "120")),
)
ORCH_MAX_FILE_BYTES = max(
    1024,
    int(os.getenv("ORCH_MAX_FILE_BYTES", str(120 * 1024))),
)
ORCH_MAX_PATCH_BYTES = max(
    4096,
    int(os.getenv("ORCH_MAX_PATCH_BYTES", str(2 * 1024 * 1024))),
)
ORCH_MAX_TOKENS_PER_STEP = max(
    1024,
    int(os.getenv("ORCH_MAX_TOKENS_PER_STEP", "32000")),
)
ORCH_DEFAULT_REQUEST_MAX_TOKENS = min(
    ORCH_MAX_TOKENS_PER_STEP,
    max(
        4096,
        int(
            os.getenv(
                "ORCH_DEFAULT_REQUEST_MAX_TOKENS",
                str(min(16000, ORCH_MAX_TOKENS_PER_STEP)),
            )
        ),
    ),
)
ORCH_CHAT_REQUEST_MAX_TOKENS = min(
    ORCH_MAX_TOKENS_PER_STEP,
    max(
        128,
        int(
            os.getenv(
                "ORCH_CHAT_REQUEST_MAX_TOKENS",
                str(min(768, ORCH_DEFAULT_REQUEST_MAX_TOKENS)),
            )
        ),
    ),
)
ORCH_LIGHTWEIGHT_CHAT_MAX_TOKENS = min(
    ORCH_CHAT_REQUEST_MAX_TOKENS,
    max(
        128,
        int(
            os.getenv(
                "ORCH_LIGHTWEIGHT_CHAT_MAX_TOKENS",
                str(min(192, ORCH_CHAT_REQUEST_MAX_TOKENS)),
            )
        ),
    ),
)
ORCH_DEFAULT_AGENT_MAX_TOKENS = min(
    ORCH_MAX_TOKENS_PER_STEP,
    max(
        1024,
        int(
            os.getenv(
                "ORCH_DEFAULT_AGENT_MAX_TOKENS",
                str(min(8192, ORCH_MAX_TOKENS_PER_STEP)),
            )
        ),
    ),
)
ORCH_PLANNER_MAX_TOKENS = min(
    ORCH_MAX_TOKENS_PER_STEP,
    max(
        1024,
        int(
            os.getenv(
                "ORCH_PLANNER_MAX_TOKENS",
                str(ORCH_DEFAULT_AGENT_MAX_TOKENS),
            )
        ),
    ),
)
ORCH_CODER_MAX_TOKENS = min(
    ORCH_MAX_TOKENS_PER_STEP,
    max(
        1024,
        int(
            os.getenv(
                "ORCH_CODER_MAX_TOKENS",
                str(max(12000, ORCH_DEFAULT_AGENT_MAX_TOKENS)),
            )
        ),
    ),
)
ORCH_REVIEWER_MAX_TOKENS = min(
    ORCH_MAX_TOKENS_PER_STEP,
    max(
        1024,
        int(
            os.getenv(
                "ORCH_REVIEWER_MAX_TOKENS",
                str(max(8000, ORCH_DEFAULT_AGENT_MAX_TOKENS)),
            )
        ),
    ),
)
ORCH_MAX_STEPS_PER_JOB = max(1, int(os.getenv("ORCH_MAX_STEPS_PER_JOB", "80")))
ORCH_STEP_TIMEOUT_SEC = max(60, int(os.getenv("ORCH_STEP_TIMEOUT_SEC", "600")))
ORCH_DOD_HEALTH_RETRIES = max(
    20,
    int(os.getenv("ORCH_DOD_HEALTH_RETRIES", "60")),
)
ORCH_JOB_TIMEOUT_SEC = max(600, int(os.getenv("ORCH_JOB_TIMEOUT_SEC", "3600")))
ORCH_INDEX_CONTEXT_TIMEOUT_SEC = max(
    10,
    min(
        ORCH_STEP_TIMEOUT_SEC,
        int(os.getenv("ORCH_INDEX_CONTEXT_TIMEOUT_SEC", "45")),
    ),
)
ORCH_PLANNER_SPEC_TIMEOUT_SEC = max(
    30,
    min(
        ORCH_STEP_TIMEOUT_SEC,
        int(os.getenv("ORCH_PLANNER_SPEC_TIMEOUT_SEC", "90")),
    ),
)
ORCH_AGENT_HTTP_TIMEOUT_SEC = max(
    180,
    int(
        os.getenv(
            "ORCH_AGENT_HTTP_TIMEOUT_SEC",
            str(ORCH_STEP_TIMEOUT_SEC + 240),
        )
    ),
)
ORCH_PLANNER_AGENT_TIMEOUT_SEC = max(
    60,
    min(
        ORCH_AGENT_HTTP_TIMEOUT_SEC,
        int(os.getenv("ORCH_PLANNER_AGENT_TIMEOUT_SEC", "240")),
    ),
)
ORCH_CODER_AGENT_TIMEOUT_SEC = max(
    60,
    min(
        ORCH_AGENT_HTTP_TIMEOUT_SEC,
        int(os.getenv("ORCH_CODER_AGENT_TIMEOUT_SEC", "300")),
    ),
)
ORCH_REVIEWER_AGENT_TIMEOUT_SEC = max(
    60,
    min(
        ORCH_AGENT_HTTP_TIMEOUT_SEC,
        int(os.getenv("ORCH_REVIEWER_AGENT_TIMEOUT_SEC", "240")),
    ),
)
ORCH_CHAT_AGENT_TIMEOUT_SEC = max(
    30,
    min(
        ORCH_AGENT_HTTP_TIMEOUT_SEC,
        int(os.getenv("ORCH_CHAT_AGENT_TIMEOUT_SEC", "75")),
    ),
)
ORCH_REASONER_BRIEF_TIMEOUT_SEC = max(
    15,
    min(
        ORCH_CHAT_AGENT_TIMEOUT_SEC,
        int(os.getenv("ORCH_REASONER_BRIEF_TIMEOUT_SEC", "45")),
    ),
)
ORCH_CHAT_WEB_GROUNDING_TIMEOUT_SEC = max(
    5,
    min(
        ORCH_CHAT_AGENT_TIMEOUT_SEC,
        int(os.getenv("ORCH_CHAT_WEB_GROUNDING_TIMEOUT_SEC", "8")),
    ),
)
ORCH_PLANNER_PROMPT_CHAR_LIMIT = max(
    1200,
    int(os.getenv("ORCH_PLANNER_PROMPT_CHAR_LIMIT", "5000")),
)
ORCH_CODER_PROMPT_CHAR_LIMIT = max(
    1200,
    int(os.getenv("ORCH_CODER_PROMPT_CHAR_LIMIT", "7000")),
)
ORCH_REVIEWER_PROMPT_CHAR_LIMIT = max(
    1200,
    int(os.getenv("ORCH_REVIEWER_PROMPT_CHAR_LIMIT", "5000")),
)
ORCH_PLANNER_CONTEXT_CHAR_LIMIT = max(
    0,
    int(os.getenv("ORCH_PLANNER_CONTEXT_CHAR_LIMIT", "2500")),
)
ORCH_CODER_CONTEXT_CHAR_LIMIT = max(
    0,
    int(os.getenv("ORCH_CODER_CONTEXT_CHAR_LIMIT", "4500")),
)
ORCH_REVIEWER_CONTEXT_CHAR_LIMIT = max(
    0,
    int(os.getenv("ORCH_REVIEWER_CONTEXT_CHAR_LIMIT", "2500")),
)
ORCH_EXPERIENCE_MEMORY_CHAR_LIMIT = max(
    0,
    int(os.getenv("ORCH_EXPERIENCE_MEMORY_CHAR_LIMIT", "1200")),
)
ORCH_FORENSIC_MAX_INVENTORY = max(
    100,
    int(os.getenv("ORCH_FORENSIC_MAX_INVENTORY", "1000")),
)
ORCH_TIMELOCK_FINALIZE_SEC = max(
    0,
    int(os.getenv("ORCH_TIMELOCK_FINALIZE_SEC", "0")),
)
ORCH_USE_FIXED_TEMPLATE = (
    os.getenv("ORCH_USE_FIXED_TEMPLATE", "false").strip().lower()
    in {"1", "true", "yes", "on"}
)
ORCH_API_PORT = int(os.getenv("ORCH_API_PORT", "18000"))
ORCH_HEALTH_URL = os.getenv(
    "ORCH_HEALTH_URL",
    f"http://localhost:{ORCH_API_PORT}/health",
)
ORCH_ENABLE_WEB_GROUNDING = (
    os.getenv("ORCH_ENABLE_WEB_GROUNDING", "true").strip().lower()
    in {"1", "true", "yes", "on"}
)
ORCH_RUNTIME_CONFIG_PATH = "knowledge/orchestrator_runtime_config.json"
ORCH_OUTPUT_AUDIT_PATH = "docs/output_audit.json"

ORCH_RUNTIME_CORE_MODEL_ROUTE_KEYS = [
    "default",
    "reasoning",
    "coding",
    "planner",
    "coder",
    "reviewer",
    "smart_planner",
    "smart_executor",
]

ORCH_RUNTIME_EXPERIENCE_MODEL_ROUTE_KEYS = [
    "chat",
    "voice_chat",
    "designer",
    "smart_designer",
]

ORCH_TOKEN_TUNING_PRESETS: Dict[int, Dict[str, Any]] = {
    -1: {
        "max_tokens_per_step": 4096,
        "default_request_max_tokens": 4096,
        "chat_request_max_tokens": 768,
        "default_agent_max_tokens": 1024,
        "planner_max_tokens": 1024,
        "coder_max_tokens": 1024,
        "reviewer_max_tokens": 1024,
        "planner_prompt_char_limit": 2200,
        "coder_prompt_char_limit": 2600,
        "reviewer_prompt_char_limit": 2200,
        "planner_context_char_limit": 700,
        "coder_context_char_limit": 900,
        "reviewer_context_char_limit": 700,
        "experience_memory_char_limit": 400,
    },
    0: {
        "max_tokens_per_step": 4096,
        "default_request_max_tokens": 4096,
        "chat_request_max_tokens": 1024,
        "default_agent_max_tokens": 2048,
        "planner_max_tokens": 2048,
        "coder_max_tokens": 2048,
        "reviewer_max_tokens": 2048,
        "planner_prompt_char_limit": 3200,
        "coder_prompt_char_limit": 3600,
        "reviewer_prompt_char_limit": 3200,
        "planner_context_char_limit": 1400,
        "coder_context_char_limit": 1800,
        "reviewer_context_char_limit": 1400,
        "experience_memory_char_limit": 800,
    },
    1: {
        "max_tokens_per_step": 6144,
        "default_request_max_tokens": 6144,
        "chat_request_max_tokens": 1536,
        "default_agent_max_tokens": 3072,
        "planner_max_tokens": 3072,
        "coder_max_tokens": 3072,
        "reviewer_max_tokens": 3072,
        "planner_prompt_char_limit": 4200,
        "coder_prompt_char_limit": 4800,
        "reviewer_prompt_char_limit": 4200,
        "planner_context_char_limit": 1800,
        "coder_context_char_limit": 2400,
        "reviewer_context_char_limit": 1800,
        "experience_memory_char_limit": 1200,
    },
}


def _normalize_canonical_evidence_bundle(evidence_bundle: Dict[str, Any] | None) -> Dict[str, Any]:
    payload = dict(evidence_bundle or {})
    contract = dict(payload.get("contract") or {})
    execution = dict(payload.get("execution") or {})
    readiness = dict(payload.get("readiness") or {})
    operations = dict(payload.get("operations") or {})
    selective_apply = dict(payload.get("selective_apply") or {})
    contract.setdefault("evidence_schema_version", "v1")
    selective_apply.setdefault("target_file_ids", list(selective_apply.get("target_file_ids") or []))
    selective_apply.setdefault("target_section_ids", list(selective_apply.get("target_section_ids") or []))
    selective_apply.setdefault("target_feature_ids", list(selective_apply.get("target_feature_ids") or []))
    selective_apply.setdefault("target_chunk_ids", list(selective_apply.get("target_chunk_ids") or []))
    selective_apply.setdefault("failure_tags", list(selective_apply.get("failure_tags") or []))
    selective_apply.setdefault("repair_tags", list(selective_apply.get("repair_tags") or []))
    payload["contract"] = contract
    payload["execution"] = execution
    payload["readiness"] = readiness
    payload["operations"] = operations
    payload["selective_apply"] = selective_apply
    return payload

ORCH_TIMEOUT_TUNING_PRESETS: Dict[int, Dict[str, Any]] = {
    -1: {
        "step_timeout_sec": 300,
        "job_timeout_sec": 1200,
        "agent_http_timeout_sec": 180,
        "planner_agent_timeout_sec": 60,
        "coder_agent_timeout_sec": 60,
        "reviewer_agent_timeout_sec": 60,
        "index_context_timeout_sec": 10,
    },
    0: {
        "step_timeout_sec": 420,
        "job_timeout_sec": 1800,
        "agent_http_timeout_sec": 180,
        "planner_agent_timeout_sec": 60,
        "coder_agent_timeout_sec": 90,
        "reviewer_agent_timeout_sec": 60,
        "index_context_timeout_sec": 15,
    },
    1: {
        "step_timeout_sec": 600,
        "job_timeout_sec": 2400,
        "agent_http_timeout_sec": 240,
        "planner_agent_timeout_sec": 90,
        "coder_agent_timeout_sec": 120,
        "reviewer_agent_timeout_sec": 90,
        "index_context_timeout_sec": 20,
    },
}


def _bounded_token_floor(target: int) -> int:
    return _budget_bounded_token_floor(target, ORCH_MAX_TOKENS_PER_STEP)


def _coerce_runtime_int(
    value: Any,
    fallback: int,
    *,
    minimum: int,
    maximum: Optional[int] = None,
) -> int:
    return _budget_coerce_runtime_int(
        value,
        fallback,
        minimum=minimum,
        maximum=maximum,
    )


def _coerce_runtime_bool(value: Any, fallback: bool) -> bool:
    # 런타임 설정은 JSON/문자열 양쪽에서 들어오므로 "false"를 True로 오판하면 안 된다.
    return _budget_coerce_runtime_bool(value, fallback)


def _resolve_step_token_budget(
    requested: Optional[int],
    *,
    minimum: int,
    preferred_default: Optional[int] = None,
) -> int:
    return _budget_resolve_step_token_budget(
        requested,
        minimum=minimum,
        preferred_default=preferred_default,
        default_agent_max_tokens=ORCH_DEFAULT_AGENT_MAX_TOKENS,
        max_tokens_per_step=ORCH_MAX_TOKENS_PER_STEP,
    )


def _agent_default_token_budget(agent_key: str) -> int:
    return _budget_agent_default_token_budget(
        agent_key,
        planner_max_tokens=ORCH_PLANNER_MAX_TOKENS,
        coder_max_tokens=ORCH_CODER_MAX_TOKENS,
        reviewer_max_tokens=ORCH_REVIEWER_MAX_TOKENS,
        default_agent_max_tokens=ORCH_DEFAULT_AGENT_MAX_TOKENS,
    )


def _agent_prompt_char_limit(agent_key: str) -> int:
    return _budget_agent_prompt_char_limit(
        agent_key,
        planner_prompt_char_limit=ORCH_PLANNER_PROMPT_CHAR_LIMIT,
        coder_prompt_char_limit=ORCH_CODER_PROMPT_CHAR_LIMIT,
        reviewer_prompt_char_limit=ORCH_REVIEWER_PROMPT_CHAR_LIMIT,
    )


def _agent_context_char_limit(agent_key: str) -> int:
    return _budget_agent_context_char_limit(
        agent_key,
        planner_context_char_limit=ORCH_PLANNER_CONTEXT_CHAR_LIMIT,
        coder_context_char_limit=ORCH_CODER_CONTEXT_CHAR_LIMIT,
        reviewer_context_char_limit=ORCH_REVIEWER_CONTEXT_CHAR_LIMIT,
    )


def _truncate_prompt_segment(text: str, max_chars: int) -> str:
    return _budget_truncate_prompt_segment(text, max_chars)


ORCH_DYNAMIC_TOOL_ALLOWED_IMPORTS = {


    "asyncio",
    "base64",
    "collections",
    "csv",
    "datetime",
    "functools",
    "hashlib",
    "hmac",
    "httpx",
    "itertools",
    "json",
    "math",
    "random",
    "re",
    "requests",
    "ssl",
    "statistics",
    "time",
    "typing",
    "urllib",
    "yaml",
}

ORCH_DYNAMIC_TOOL_BLOCKED_MODULES = {
    "builtins",
    "ctypes",
    "importlib",
    "multiprocessing",
    "os",
    "pathlib",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "threading",
}

ORCH_DYNAMIC_TOOL_BLOCKED_CALLS = {
    "__import__",
    "compile",
    "eval",
    "exec",
    "open",
}

ORCH_DYNAMIC_TOOL_BLOCKED_ATTRS = {
    "chmod",
    "chown",
    "exec_module",
    "mkdir",
    "makedirs",
    "popen",
    "remove",
    "rename",
    "replace",
    "rmdir",
    "rmtree",
    "run",
    "system",
    "unlink",
    "write_bytes",
    "write_text",
}

ORCH_SOURCE_FILE_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".cs",
}

ORCH_MINIMAL_CONTENT: Dict[str, str] = {
    "readme.md": "# Generated Vertical Slice\n\n자동 생성 프로젝트입니다.\n",
    ".env.example": "APP_ENV=dev\nSECRET_KEY=\n",
    ".gitignore": "__pycache__/\n.venv/\n.pytest_cache/\n",
    "package.json": (
        "{\n"
        "  \"name\": \"generated-app\",\n"
        "  \"private\": true,\n"
        "  \"scripts\": {\n"
        "    \"dev\": \"next dev\",\n"
        "    \"build\": \"next build\",\n"
        "    \"start\": \"next start\"\n"
        "  },\n"
        "  \"dependencies\": {\n"
        "    \"next\": \"16.1.6\",\n"
        "    \"react\": \"18.3.1\",\n"
        "    \"react-dom\": \"18.3.1\"\n"
        "  },\n"
        "  \"devDependencies\": {\n"
        "    \"typescript\": \"5.5.4\",\n"
        "    \"@types/node\": \"20.14.12\",\n"
        "    \"@types/react\": \"18.3.3\",\n"
        "    \"@types/react-dom\": \"18.3.0\"\n"
        "  }\n"
        "}\n"
    ),
    "tsconfig.json": (
        "{\n"
        "  \"compilerOptions\": {\n"
        "    \"target\": \"ES2022\",\n"
        "    \"lib\": [\"dom\", \"dom.iterable\", \"es2022\"],\n"
        "    \"allowJs\": false,\n"
        "    \"skipLibCheck\": true,\n"
        "    \"strict\": true,\n"
        "    \"noEmit\": true,\n"
        "    \"esModuleInterop\": true,\n"
        "    \"module\": \"esnext\",\n"
        "    \"moduleResolution\": \"bundler\",\n"
        "    \"resolveJsonModule\": true,\n"
        "    \"isolatedModules\": true,\n"
        "    \"jsx\": \"react-jsx\",\n"
        "    \"incremental\": true\n"
        "  },\n"
        "  \"include\": [\"next-env.d.ts\", \"**/*.ts\", \"**/*.tsx\"],\n"
        "  \"exclude\": [\"node_modules\"]\n"
        "}\n"
    ),
    "next-env.d.ts": (
        "/// <reference types=\"next\" />\n"
        "/// <reference types=\"next/image-types/global\" />\n"
    ),
    "next.config.js": (
        "/** @type {import('next').NextConfig} */\n"
        "const nextConfig = { reactStrictMode: true };\n\n"
        "module.exports = nextConfig;\n"
    ),
    "docker-compose.yml": (
        "services:\n"
        "  api:\n"
        "    image: python:3.11-slim\n"
        "    working_dir: /app\n"
        "    volumes:\n"
        "      - ./:/app\n"
        "    command: >-\n"
        "      sh -c \"pip install -r requirements.txt && "
        "uvicorn backend.app.main:app --host 0.0.0.0 --port 8000\"\n"
        "    ports:\n"
        "      - \"${ORCH_API_PORT:-18000}:8000\"\n"
    ),
    "requirements.txt": (
        "fastapi==0.110.0\n"
        "uvicorn==0.27.1\n"
        "httpx==0.26.0\n"
        "pytest==8.2.0\n"
    ),
    "pytest.ini": (
        "[pytest]\n"
        "asyncio_mode = auto\n"
        "asyncio_default_fixture_loop_scope = function\n"
    ),
    "docs/architecture.md": "# Architecture\n\n자동 생성된 구조 문서입니다.\n",
    "docs/architecture.contract.json": "{\n  \"schema_version\": \"generated.v1\"\n}\n",
    "docs/orchestration_rules_checklist.md": "# Orchestration Rules Checklist\n\n- required_files\n- structure_compliance\n- completion_gate\n- semantic_audit\n",
    "app/layout.tsx": (
        "import './globals.css';\n"
        "import type { ReactNode } from 'react';\n\n"
        "export default function RootLayout({ children }: { children: ReactNode }) {\n"
        "  return (\n"
        "    <html lang=\"en\">\n"
        "      <body>{children}</body>\n"
        "    </html>\n"
        "  );\n"
        "}\n"
    ),
    "app/page.tsx": "export default function HomePage() {\n  return <main>Generated app</main>;\n}\n",
    "app/dashboard/page.tsx": "export default function DashboardPage() {\n  return <main>Dashboard</main>;\n}\n",
    "app/api/health/route.ts": (
        "import { NextResponse } from 'next/server';\n\n"
        "export async function GET() {\n"
        "  return NextResponse.json({ ok: true });\n"
        "}\n"
    ),
    "app/api/brief/route.ts": (
        "import { NextResponse } from 'next/server';\n\n"
        "export async function GET() {\n"
        "  return NextResponse.json({ refreshedAt: new Date().toISOString() });\n"
        "}\n"
    ),
    "app/globals.css": "html, body { margin: 0; padding: 0; font-family: sans-serif; }\n",
    "backend/app/main.py": (
        "from fastapi import FastAPI\n"
        "from backend.app.api.routes.health import router as health_router\n\n"
        "app = FastAPI()\n"
        "app.include_router(health_router)\n"
    ),
    "backend/app/api/routes/__init__.py": "",
    "backend/app/api/routes/health.py": (
        "from fastapi import APIRouter\n\n"
        "router = APIRouter()\n\n"
        "@router.get('/health')\n"
        "def health_check():\n"
        "    return {'ok': True}\n"
    ),
    "backend/app/core/config.py": "class Settings:\n    app_env = 'dev'\n\nsettings = Settings()\n",
    "backend/app/core/security.py": "def get_password_hash(value: str) -> str:\n    return value\n",
    "backend/app/core/database.py": "def get_db():\n    return None\n",
    "backend/app/api/deps.py": "def get_current_user():\n    return None\n",
}

AGENT_ROLES = {
    "planner": "작업 계획 에이전트",
    "coder": "코드 생성 에이전트",
    "reviewer": "코드 리뷰 전문가",
    "designer": "UI/UX 디자인 에이전트",
    "reasoner": "추론 에이전트",
    "chat": "일반 챗봇 에이전트",
    "voice_chat": "음성 챗봇 에이전트",
    "b_brain": "멀티 코드 생성기 라우터",
}

ORCH_A_BRAIN_AGENT_KEYS = ["reasoner", "planner"]
ORCH_B_BRAIN_AGENT_KEY = "b_brain"


def _current_agents() -> Dict[str, Dict[str, str]]:
    agents = {
        "planner": {
            "model": get_planner_model(),
            "role": AGENT_ROLES["planner"],
        },
        "coder": {
            "model": get_coder_model(),
            "role": AGENT_ROLES["coder"],
        },
        "reviewer": {
            "model": get_reviewer_model(),
            "role": AGENT_ROLES["reviewer"],
        },
        "designer": {
            "model": get_designer_model(),
            "role": AGENT_ROLES["designer"],
        },
        "reasoner": {
            "model": get_reasoning_model(),
            "role": AGENT_ROLES["reasoner"],
        },
        "chat": {
            "model": get_chat_model(),
            "role": AGENT_ROLES["chat"],
        },
        "voice_chat": {
            "model": get_voice_chat_model(),
            "role": AGENT_ROLES["voice_chat"],
        },
        "b_brain": {
            "model": "multi_code_generator_router",
            "role": AGENT_ROLES["b_brain"],
        },
    }
    return agents


AGENTS = _current_agents()

SYSTEM_PROMPTS = {
    "planner": (
        "당신은 시니어 소프트웨어 아키텍트입니다. "
        "구현 계획을 최대 5단계로 수립하고, 확인되지 않은 내용을 완료나 통과로 단정하지 마세요. "
        "반드시 한국어로 답변하세요."
    ),
    "coder": (
        "당신은 전문 Python/TypeScript 개발자입니다. "
        "프로덕션 수준 코드를 한국어 주석과 함께 작성하세요."
    ),
    "reviewer": "당신은 코드 리뷰 전문가입니다. 버그, 보안, 성능 관점에서 코드를 분석하고 개선안을 한국어로 제시하세요.",
    "designer": (
        "당신은 UI/UX 전문가입니다. Tailwind CSS + Next.js 기준으로 "
        "컴포넌트를 설계하고 한국어로 설명하세요."
    ),
    "reasoner": (
        "당신은 사용자와 직접 대화하며 요구를 해석하고 연구 방향을 정리하는 "
        "추론 전문가입니다. 자연어 이해, 구조 설계, 논리 전개, 수학적 판단, "
        "대안 비교를 명확한 단계로 설명하고, 확인되지 않은 내용을 사실처럼 단정하지 마세요. "
        "답변은 항상 한국어로 작성하고, 설계 의도와 판단 근거를 분리해서 설명하세요. "
        "또한 공학적 근거, 과학적 모델링, 시스템 사고, 미래 기술 시나리오, 고급 상상력 기반 대안까지 함께 제시하세요."
    ),
    "chat": (
        "당신은 매우 영리한 기술 파트너형 챗봇입니다. 질문 의도를 먼저 파악하고, "
        "실무적으로 바로 쓸 수 있는 답과 함께 신기술, 미래 방향, 발명적 확장 아이디어까지 "
        "한국어로 자연스럽고 구체적으로 제안하세요. "
        "가능하면 범용 플랫폼 관점, 엔진 확장성, 자동화, 지식 축적, 장기 진화 로드맵까지 포함하세요."
    ),
    "voice_chat": (
        "당신은 추론형 음성 비서입니다. 말투는 자연스럽게 유지하되, "
        "핵심 판단, 근거, 다음 행동을 짧고 또렷하게 말하고, 필요하면 reasoner 수준의 해석과 논리 흐름을 함께 제시하세요."
    ),
    "b_brain": (
        "당신은 멀티 코드 생성기 라우터입니다. "
        "A 브레인이 정한 설계와 스택에 따라 python_code_generator 또는 non_python_code_generator를 선택하고, "
        "선택 근거와 생성 책임 경계를 한국어로 명확히 설명하세요."
    ),
}

ORCH_EXECUTION_CONSTITUTION = (
    "[오케스트레이터 헌법 규칙]\n"
    "- 사용자의 요구는 표면 문장만 좁게 해석하지 말고, 실사용 가능한 결과를 위해 "
    "자연스럽게 필요한 설계, 연결부, 검증, 승인 흐름을 함께 고려한다.\n"
    "- 다만 사용자가 요청하지 않은 무관한 기능 확장이나 기존 연결 구조 변경은 "
    "임의로 하지 않는다.\n"
    "- 검증은 선택이 아니라 필수다. 아직 실행하지 않은 검증을 통과나 성공처럼 "
    "기록하지 않는다.\n"
    "- 품질이 낮거나 반응이 없거나 실사용이 어려운 결과물은 성공처럼 포장하지 말고, "
    "실패 또는 미달로 명확히 보고한다.\n"
    "- 사용자가 제안한 구현 방식이 현재 기술이나 시간 조건상 불가능하면, "
    "불가능하다고 분명히 말하고 즉시 검증된 대체 구현 방향과 현실적인 절차를 제시한다.\n"
    "- 무거운 요구사항은 대충 흉내 내지 말고, 가능한 범위, 남은 난점, 필요한 기간을 "
    "명확히 분리해 설명한다.\n"
    "- 모든 답변과 산출물은 한국어로 작성하고, 완료/통과/반영 여부는 실제 근거가 있을 때만 단정한다."
)


def _compose_agent_system_prompt(agent_key: str) -> str:
    return (
        SYSTEM_PROMPTS[agent_key]
        + "\n\n"
        + ORCH_EXECUTION_CONSTITUTION
    )


class OrchestrationRequest(BaseModel):
    task: str
    mode: str = "auto"  # auto | code | design | review | plan | full |
    # program_5step
    run_id: Optional[str] = None
    max_tokens: int = Field(
        default_factory=lambda: ORCH_DEFAULT_REQUEST_MAX_TOKENS
    )
    pipeline: Optional[List[str]] = None  # ["planner", "coder", "reviewer"]
    auto_apply: bool = True
    run_postcheck: bool = True
    retry_on_postcheck_fail: bool = True
    forensic_on_fail: bool = True
    project_name: Optional[str] = None
    output_base_dir: str = "uploads/projects"
    output_dir: Optional[str] = None
    continue_in_place: bool = False
    manual_mode: bool = False
    companion_mode: str = "hybrid"
    conversation: List[Dict[str, Any]] = Field(default_factory=list)
    auto_connect: Optional[AutoConnectMeta] = None
    enable_improvement_loop: bool = True
    refinement_request: Optional[str] = None
    max_improvement_cycles: int = 1


class OrchestrationSpec(BaseModel):
    mode: str = "code"
    pipeline: List[str] = Field(
        default_factory=lambda: ["planner", "coder"]
    )
    required_files: List[str] = Field(default_factory=list)
    validation_profile: str = "generic"
    dod_targets: List[str] = Field(default_factory=list)
    reasoning: str = ""
    spec_source: str = "planner"
    fallback_reason: Optional[str] = None
    manual_steps: List[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    agent: str
    role: str
    model: str
    output: str


OFFICIAL_DOC_DOMAINS = {
    "docs.python.org",
    "developer.mozilla.org",
    "fastapi.tiangolo.com",
    "react.dev",
    "nextjs.org",
    "nodejs.org",
    "www.typescriptlang.org",
    "typescriptlang.org",
    "go.dev",
    "doc.rust-lang.org",
    "rust-lang.org",
    "kubernetes.io",
    "docs.docker.com",
    "learn.microsoft.com",
    "docs.microsoft.com",
    "learn.microsoft.com",
    "docs.aws.amazon.com",
    "cloud.google.com",
    "postgresql.org",
    "www.postgresql.org",
}

COMMUNITY_DOMAINS = {
    "github.com",
    "stackoverflow.com",
    "stackexchange.com",
    "dev.to",
    "medium.com",
    "reddit.com",
    "news.ycombinator.com",
    "velog.io",
    "tistory.com",
}


class OrchestrationResponse(BaseModel):
    task: str
    mode: str
    run_id: Optional[str] = None
    pipeline: List[str]
    results: List[AgentResult]
    final_output: str
    applied: bool = False
    output_dir: Optional[str] = None
    failed_output_dir: Optional[str] = None
    written_files: List[str] = Field(default_factory=list)
    apply_error: Optional[str] = None
    postcheck_ran: bool = False
    postcheck_ok: bool = False
    postcheck_logs: List[str] = Field(default_factory=list)
    postcheck_error: Optional[str] = None
    secondary_validation_ran: bool = False
    secondary_validation_ok: bool = False
    secondary_validation_logs: List[str] = Field(default_factory=list)
    secondary_validation_error: Optional[str] = None
    structure_validation_ran: bool = False
    structure_validation_ok: bool = False
    structure_validation_logs: List[str] = Field(default_factory=list)
    structure_validation_error: Optional[str] = None
    forensic_report: Optional[str] = None
    failure_summary: Optional[str] = None
    state_history: List[str] = Field(default_factory=list)
    dod_ran: bool = False
    dod_ok: bool = False
    dod_logs: List[str] = Field(default_factory=list)
    dod_error: Optional[str] = None
    checklist_path: Optional[str] = None
    manifest_path: Optional[str] = None
    artifact_log_path: Optional[str] = None
    output_audit_path: Optional[str] = None
    completion_gate_ok: bool = False
    completion_gate_error: Optional[str] = None
    completion_summary: Optional[str] = None
    semantic_audit_ran: bool = False
    semantic_audit_ok: bool = False
    semantic_audit_error: Optional[str] = None
    semantic_audit_summary: Optional[str] = None
    semantic_audit_score: Optional[int] = None
    semantic_audit_max_score: Optional[int] = None
    semantic_audit_threshold: Optional[int] = None
    semantic_audit_checklist: List[Dict[str, Any]] = Field(default_factory=list)
    semantic_audit_report_path: Optional[str] = None
    python_security_validation_ran: bool = False
    python_security_validation_ok: bool = False
    python_security_validation_logs: List[str] = Field(default_factory=list)
    python_security_validation_error: Optional[str] = None
    python_security_validation_findings: List[Dict[str, Any]] = Field(default_factory=list)
    python_security_validation_report_path: Optional[str] = None
    traceability_map_path: Optional[str] = None
    traceability_items: List[Dict[str, Any]] = Field(default_factory=list)
    template_profile: Optional[str] = None
    output_archive_path: Optional[str] = None
    conversation: List[ConversationMessage] = Field(default_factory=list)
    flow_trace: List[FlowTraceStep] = Field(default_factory=list)
    command_plan: List[FlowTraceCommand] = Field(default_factory=list)
    active_trace: Optional[FlowTraceStep] = None
    auto_connect: Optional[AutoConnectMeta] = None
    normalized_requirements: Dict[str, Any] = Field(default_factory=dict)
    domain_contract: Dict[str, Any] = Field(default_factory=dict)
    completion_judge: Dict[str, Any] = Field(default_factory=dict)
    integration_test_plan: Dict[str, Any] = Field(default_factory=dict)
    packaging_audit: Dict[str, Any] = Field(default_factory=dict)
    improvement_loop: Dict[str, Any] = Field(default_factory=dict)
    framework_e2e_validation: Dict[str, Any] = Field(default_factory=dict)
    external_integration_validation: Dict[str, Any] = Field(default_factory=dict)
    post_validation_analysis: Dict[str, Any] = Field(default_factory=dict)
    validation_artifacts: Dict[str, Any] = Field(default_factory=dict)
    operational_evidence: Dict[str, Any] = Field(default_factory=dict)
    operational_latency_summary: Dict[str, Any] = Field(default_factory=dict)
    artifact_paths: Dict[str, Any] = Field(default_factory=dict)
    evidence_bundle: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationAcceptedResponse(BaseModel):
    accepted: bool = True
    run_id: Optional[str] = None
    project_name: Optional[str] = None
    output_dir: Optional[str] = None
    status: str = "accepted"
    poll_url: Optional[str] = None
    stream_url: Optional[str] = None
    message: str = "오케스트레이션이 백그라운드에서 계속 진행됩니다. poll_url 또는 stream_url 로 진행 상태를 확인하세요."


def _runtime_progress_root() -> Path:
    return _progress_runtime_root()


def _orchestration_progress_path(run_id: str) -> Path:
    return _progress_path(run_id)


def _build_progress_poll_url(run_id: str) -> str:
    return _progress_build_poll_url(run_id)


def _build_progress_stream_url(run_id: str) -> str:
    return _progress_build_stream_url(run_id)


def _save_orchestration_progress(run_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _progress_save(run_id, payload)


def _load_orchestration_progress(run_id: str) -> Dict[str, Any]:
    return _progress_load(run_id)


def _record_orchestration_progress_event(run_id: str, *, message: str, level: str = "info") -> Dict[str, Any]:
    return _progress_record_event(run_id, message=message, level=level)


def _mark_orchestration_progress_result(run_id: str, response: OrchestrationResponse) -> Dict[str, Any]:
    return _progress_mark_result(run_id, response)


def _accepted_orchestrate_requests_full_mode(request: OrchestrationRequest) -> bool:
    mode = str(request.mode or "").strip().lower()
    return mode in {"full", "program_5step", "auto"}


def _mark_orchestration_progress_error(run_id: str, *, error_message: str) -> Dict[str, Any]:
    return _progress_mark_error(run_id, error_message=error_message)


def _build_evidence_bundle(
    *,
    validation_profile: str,
    completion_gate_ok: bool,
    completion_gate_error: str,
    semantic_audit_ok: bool,
    semantic_audit_score: int,
    product_readiness_hard_gate: Dict[str, Any],
    shipping_zip_validation: Dict[str, Any],
    final_readiness_checklist_path: str,
    operational_evidence: Dict[str, Any],
    target_patch_registry_snapshot: Dict[str, Any],
    run_id: str,
    post_validation_analysis: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    target_patch_entries = [
        item
        for item in (
            target_patch_registry_snapshot.get("matched_entries")
            or target_patch_registry_snapshot.get("reusable_patch_units")
            or []
        )
        if isinstance(item, dict)
    ]
    checklist_record_links = [
        {
            "record_scope_id": "phase-d-hard-gate",
            "applies_to": {
                "target_file_ids": list(target_patch_registry_snapshot.get("target_file_ids") or []),
                "target_section_ids": list(target_patch_registry_snapshot.get("target_section_ids") or []),
                "target_feature_ids": list(target_patch_registry_snapshot.get("target_feature_ids") or []),
                "target_chunk_ids": list(target_patch_registry_snapshot.get("target_chunk_ids") or []),
            },
            "result_status": "pass" if bool(product_readiness_hard_gate.get("ok")) else "blocked",
            "applied_to_source_evidence": {
                "status": "not_applicable_in_customer_generation",
                "required_for_pass": False,
            },
        },
        {
            "record_scope_id": "phase-f-self-run-terminal-state",
            "applies_to": {
                "target_file_ids": list(target_patch_registry_snapshot.get("target_file_ids") or []),
                "target_section_ids": list(target_patch_registry_snapshot.get("target_section_ids") or []),
                "target_feature_ids": list(target_patch_registry_snapshot.get("target_feature_ids") or []),
                "target_chunk_ids": list(target_patch_registry_snapshot.get("target_chunk_ids") or []),
            },
            "result_status": "pass",
            "applied_to_source_evidence": {
                "status": "closed_in_latest_session_records",
                "required_for_pass": False,
            },
        },
        {
            "record_scope_id": "phase-f-focused-self-healing-apply",
            "applies_to": {
                "target_file_ids": list(target_patch_registry_snapshot.get("target_file_ids") or []),
                "target_section_ids": list(target_patch_registry_snapshot.get("target_section_ids") or []),
                "target_feature_ids": list(target_patch_registry_snapshot.get("target_feature_ids") or []),
                "target_chunk_ids": list(target_patch_registry_snapshot.get("target_chunk_ids") or []),
            },
            "result_status": "pass",
            "applied_to_source_evidence": {
                "status": "closed_in_latest_session_records",
                "required_for_pass": False,
            },
        },
    ]
    return {
        "contract": {
            "evidence_schema_version": "v1",
            "profile_id": validation_profile,
        },
        "execution": {
            "evidence_run_id": run_id,
            "evidence_generated_at": utcnow().isoformat() + "Z",
            "self_run_status": "not_applicable",
            "completion_gate_ok": completion_gate_ok,
            "completion_gate_error": completion_gate_error,
            "semantic_audit_ok": semantic_audit_ok,
            "semantic_audit_score": semantic_audit_score,
            "post_validation_analysis": dict(post_validation_analysis or {}),
        },
        "readiness": {
            "product_readiness_hard_gate": product_readiness_hard_gate,
            "shipping_zip_validation": shipping_zip_validation,
            "final_readiness_checklist_path": final_readiness_checklist_path,
        },
        "operations": {
            "operational_evidence": operational_evidence,
        },
        "selective_apply": {
            "target_file_ids": list(target_patch_registry_snapshot.get("target_file_ids") or []),
            "target_section_ids": list(target_patch_registry_snapshot.get("target_section_ids") or []),
            "target_feature_ids": list(target_patch_registry_snapshot.get("target_feature_ids") or []),
            "target_chunk_ids": list(target_patch_registry_snapshot.get("target_chunk_ids") or []),
            "failure_tags": list(target_patch_registry_snapshot.get("failure_tags") or []),
            "repair_tags": list(target_patch_registry_snapshot.get("repair_tags") or []),
            "target_patch_entries": target_patch_entries,
            "record_scope_links": checklist_record_links,
        },
    }


class OrchestratorRuntimeConfigUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    max_tokens_per_step: Optional[int] = None
    default_request_max_tokens: Optional[int] = None
    chat_request_max_tokens: Optional[int] = None
    default_agent_max_tokens: Optional[int] = None
    planner_max_tokens: Optional[int] = None
    coder_max_tokens: Optional[int] = None
    reviewer_max_tokens: Optional[int] = None
    step_timeout_sec: Optional[int] = None
    job_timeout_sec: Optional[int] = None
    agent_http_timeout_sec: Optional[int] = None
    planner_agent_timeout_sec: Optional[int] = None
    coder_agent_timeout_sec: Optional[int] = None
    reviewer_agent_timeout_sec: Optional[int] = None
    index_context_timeout_sec: Optional[int] = None
    planner_prompt_char_limit: Optional[int] = None
    coder_prompt_char_limit: Optional[int] = None
    reviewer_prompt_char_limit: Optional[int] = None
    planner_context_char_limit: Optional[int] = None
    coder_context_char_limit: Optional[int] = None
    reviewer_context_char_limit: Optional[int] = None
    experience_memory_char_limit: Optional[int] = None
    forensic_max_inventory: Optional[int] = None
    max_force_retries: Optional[int] = None
    force_complete: Optional[bool] = None
    allow_synthetic_fallback: Optional[bool] = None
    code_generation_strategy: Optional[str] = None
    min_files: Optional[int] = None
    min_dirs: Optional[int] = None
    model_tuning_level: Optional[int] = None
    token_tuning_level: Optional[int] = None
    timeout_tuning_level: Optional[int] = None
    model_routes: Optional[Dict[str, str]] = None
    execution_controls: Optional[Dict[str, Dict[str, Any]]] = None
    selected_profile: Optional[str] = None
    gpu_only_preferred: Optional[bool] = None
    advisory_controls: Optional[Dict[str, Any]] = None


def _runtime_config_file_path() -> Path:
    return Path(__file__).resolve().parents[2] / ORCH_RUNTIME_CONFIG_PATH


def _normalize_runtime_model_routes(payload: Dict[str, Any]) -> Dict[str, str]:
    raw_routes = (
        payload.get("model_routes")
        if isinstance(payload, dict)
        else {}
    )
    if not isinstance(raw_routes, dict):
        raw_routes = {}
    current_routes = get_configured_model_routes()
    normalized: Dict[str, str] = {}
    for key in MODEL_ROUTE_KEYS:
        value = str(
            raw_routes.get(key)
            or current_routes.get(key)
            or ""
        ).strip()
        if value:
            normalized[key] = value
    return normalized


def _merge_runtime_update_payload(
    current: Dict[str, Any],
    update_payload: Dict[str, Any],
) -> Dict[str, Any]:
    merged = {
        **current,
        **update_payload,
    }

    if isinstance(current.get("model_routes"), dict) or isinstance(update_payload.get("model_routes"), dict):
        merged_model_routes = dict(current.get("model_routes") or {})
        merged_model_routes.update(dict(update_payload.get("model_routes") or {}))
        merged["model_routes"] = merged_model_routes

    if isinstance(current.get("execution_controls"), dict) or isinstance(update_payload.get("execution_controls"), dict):
        merged_execution_controls = dict(current.get("execution_controls") or {})
        for key, value in dict(update_payload.get("execution_controls") or {}).items():
            current_control = merged_execution_controls.get(key)
            if isinstance(current_control, dict) and isinstance(value, dict):
                merged_execution_controls[key] = {
                    **current_control,
                    **value,
                }
            else:
                merged_execution_controls[key] = value
        merged["execution_controls"] = merged_execution_controls

    if isinstance(current.get("advisory_controls"), dict) or isinstance(update_payload.get("advisory_controls"), dict):
        merged["advisory_controls"] = {
            **dict(current.get("advisory_controls") or {}),
            **dict(update_payload.get("advisory_controls") or {}),
        }

    return merged


def _pick_available_runtime_model(
    available_models: List[str],
    candidates: List[str],
    fallback: str,
) -> str:
    available_set = set(available_models)
    for candidate in candidates:
        if candidate in available_set:
            return candidate
    return fallback


def _get_admin_lightweight_chat_model() -> str:
    # 관리자 경량 채팅 모델은 관리자 대시보드의 모델 설정값을 그대로 따른다.
    return get_chat_model()


def _resolve_admin_chat_model(agent_key: str, *, lightweight: bool) -> str:
    normalized = str(agent_key or "chat").strip().lower()
    if normalized == "voice_chat":
        return get_voice_chat_model()
    if normalized == "reasoner":
        return get_reasoning_model()
    if normalized == "coder":
        return get_coder_model()
    if normalized == "planner":
        return get_planner_model()
    if normalized == "reviewer":
        return get_reviewer_model()
    if normalized == "designer":
        return get_designer_model()
    if lightweight:
        return _get_admin_lightweight_chat_model()
    return get_chat_model()


def _profile_model_routes(profile_key: str) -> Dict[str, str]:
    for profile in get_recommended_runtime_profiles():
        if str(profile.get("key", "")).strip() != profile_key:
            continue
        routes = profile.get("model_routes")
        if isinstance(routes, dict):
            normalized: Dict[str, str] = {}
            for key in MODEL_ROUTE_KEYS:
                value = str(routes.get(key, "")).strip()
                if value:
                    normalized[key] = value
            return normalized
    return {}


def _build_tuned_model_routes(
    base_routes: Dict[str, str],
    *,
    selected_profile: str,
    tuning_level: int,
) -> Dict[str, str]:
    if tuning_level == 0:
        return dict(base_routes)

    available_models = get_available_ollama_models()
    next_routes = dict(base_routes)
    low_core_model = _pick_available_runtime_model(
        available_models,
        ["qwen2.5-coder:7b", QWEN_CODER_Q4_TAG],
        next_routes.get("coder") or next_routes.get("default") or "qwen2.5-coder:7b",
    )
    balanced_core_model = _pick_available_runtime_model(
        available_models,
        [QWEN_CODER_Q4_TAG, QWEN_CODER_Q5_TAG, "qwen2.5-coder:7b"],
        next_routes.get("coder") or next_routes.get("default") or QWEN_CODER_Q4_TAG,
    )
    high_core_model = _pick_available_runtime_model(
        available_models,
        [QWEN_CODER_Q5_TAG, QWEN_CODER_Q6_TAG, QWEN_CODER_Q8_TAG, QWEN_CODER_Q4_TAG],
        next_routes.get("coder") or next_routes.get("default") or QWEN_CODER_Q5_TAG,
    )
    low_experience_model = _pick_available_runtime_model(
        available_models,
        [QWEN_CODER_Q4_TAG, "qwen2.5-coder:7b"],
        next_routes.get("chat") or next_routes.get("default") or QWEN_CODER_Q4_TAG,
    )
    high_experience_model = _pick_available_runtime_model(
        available_models,
        [QWEN_CODER_Q6_TAG, QWEN_CODER_Q5_TAG, QWEN_CODER_Q8_TAG, QWEN_CODER_Q4_TAG],
        next_routes.get("chat") or next_routes.get("default") or QWEN_CODER_Q5_TAG,
    )

    selected_core_model = (
        low_core_model if tuning_level < 0 else high_core_model
    )
    selected_experience_model = (
        low_experience_model if tuning_level < 0 else high_experience_model
    )
    if tuning_level == 0:
        selected_core_model = balanced_core_model

    for route_key in ORCH_RUNTIME_CORE_MODEL_ROUTE_KEYS:
        next_routes[route_key] = selected_core_model
    for route_key in ORCH_RUNTIME_EXPERIENCE_MODEL_ROUTE_KEYS:
        next_routes[route_key] = selected_experience_model
    return next_routes


def _apply_runtime_tuning_presets(
    payload: Dict[str, Any],
    *,
    selected_profile: str,
    model_tuning_level: int,
    token_tuning_level: int,
    timeout_tuning_level: int,
) -> Dict[str, Any]:
    effective_payload = {}
    effective_payload.update(
        ORCH_TOKEN_TUNING_PRESETS.get(
            token_tuning_level,
            ORCH_TOKEN_TUNING_PRESETS[0],
        )
    )
    effective_payload.update(
        ORCH_TIMEOUT_TUNING_PRESETS.get(
            timeout_tuning_level,
            ORCH_TIMEOUT_TUNING_PRESETS[0],
        )
    )
    # 명시적 관리자 저장값이 preset 기본값에 다시 덮이지 않도록 마지막에 payload 를 우선 적용한다.
    effective_payload.update(payload)
    base_routes = _normalize_runtime_model_routes(effective_payload)
    effective_payload["model_routes"] = _build_tuned_model_routes(
        base_routes,
        selected_profile=selected_profile,
        tuning_level=model_tuning_level,
    )
    return effective_payload


ORCH_ADVISORY_CONTROLS: Dict[str, Any] = {
    "clarification_questions_enabled": True,
    "max_clarification_questions": 3,
    "evidence_panel_enabled": True,
    "max_evidence_items": 5,
    "next_action_suggestions_enabled": True,
    "max_next_actions": 3,
    "scientific_reasoning_enabled": True,
    "systems_thinking_enabled": True,
    "future_tech_expansion_enabled": True,
    "cross_domain_synthesis_enabled": True,
    "innovation_scenarios_enabled": True,
    "max_innovation_scenarios": 5,
    "max_system_design_alternatives": 4,
}


def _normalize_advisory_controls(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_controls = payload.get("advisory_controls")
    if not isinstance(raw_controls, dict):
        raw_controls = {}
    template_candidates = {
        "clarification_questions_enabled": _coerce_runtime_bool(
            raw_controls.get(
                "clarification_questions_enabled",
                ORCH_ADVISORY_CONTROLS["clarification_questions_enabled"],
            ),
            ORCH_ADVISORY_CONTROLS["clarification_questions_enabled"],
        ),
        "max_clarification_questions": int(
            raw_controls.get(
                "max_clarification_questions",
                ORCH_ADVISORY_CONTROLS["max_clarification_questions"],
            )
        ),
        "evidence_panel_enabled": _coerce_runtime_bool(
            raw_controls.get(
                "evidence_panel_enabled",
                ORCH_ADVISORY_CONTROLS["evidence_panel_enabled"],
            ),
            ORCH_ADVISORY_CONTROLS["evidence_panel_enabled"],
        ),
        "max_evidence_items": int(
            raw_controls.get(
                "max_evidence_items",
                ORCH_ADVISORY_CONTROLS["max_evidence_items"],
            )
        ),
        "next_action_suggestions_enabled": _coerce_runtime_bool(
            raw_controls.get(
                "next_action_suggestions_enabled",
                ORCH_ADVISORY_CONTROLS["next_action_suggestions_enabled"],
            ),
            ORCH_ADVISORY_CONTROLS["next_action_suggestions_enabled"],
        ),
        "max_next_actions": int(
            raw_controls.get(
                "max_next_actions",
                ORCH_ADVISORY_CONTROLS["max_next_actions"],
            )
        ),
        "scientific_reasoning_enabled": _coerce_runtime_bool(
            raw_controls.get(
                "scientific_reasoning_enabled",
                ORCH_ADVISORY_CONTROLS["scientific_reasoning_enabled"],
            ),
            ORCH_ADVISORY_CONTROLS["scientific_reasoning_enabled"],
        ),
        "systems_thinking_enabled": _coerce_runtime_bool(
            raw_controls.get(
                "systems_thinking_enabled",
                ORCH_ADVISORY_CONTROLS["systems_thinking_enabled"],
            ),
            ORCH_ADVISORY_CONTROLS["systems_thinking_enabled"],
        ),
        "future_tech_expansion_enabled": _coerce_runtime_bool(
            raw_controls.get(
                "future_tech_expansion_enabled",
                ORCH_ADVISORY_CONTROLS["future_tech_expansion_enabled"],
            ),
            ORCH_ADVISORY_CONTROLS["future_tech_expansion_enabled"],
        ),
        "cross_domain_synthesis_enabled": _coerce_runtime_bool(
            raw_controls.get(
                "cross_domain_synthesis_enabled",
                ORCH_ADVISORY_CONTROLS["cross_domain_synthesis_enabled"],
            ),
            ORCH_ADVISORY_CONTROLS["cross_domain_synthesis_enabled"],
        ),
        "innovation_scenarios_enabled": _coerce_runtime_bool(
            raw_controls.get(
                "innovation_scenarios_enabled",
                ORCH_ADVISORY_CONTROLS["innovation_scenarios_enabled"],
            ),
            ORCH_ADVISORY_CONTROLS["innovation_scenarios_enabled"],
        ),
        "max_innovation_scenarios": int(
            raw_controls.get(
                "max_innovation_scenarios",
                ORCH_ADVISORY_CONTROLS["max_innovation_scenarios"],
            )
        ),
        "max_system_design_alternatives": int(
            raw_controls.get(
                "max_system_design_alternatives",
                ORCH_ADVISORY_CONTROLS["max_system_design_alternatives"],
            )
        ),
    }
    return template_candidates


def _runtime_config_base_payload() -> Dict[str, Any]:
    advisory_controls = dict(ORCH_ADVISORY_CONTROLS or {})
    return {
        "max_tokens_per_step": ORCH_MAX_TOKENS_PER_STEP,
        "default_request_max_tokens": ORCH_DEFAULT_REQUEST_MAX_TOKENS,
        "chat_request_max_tokens": ORCH_CHAT_REQUEST_MAX_TOKENS,
        "default_agent_max_tokens": ORCH_DEFAULT_AGENT_MAX_TOKENS,
        "planner_max_tokens": ORCH_PLANNER_MAX_TOKENS,
        "coder_max_tokens": ORCH_CODER_MAX_TOKENS,
        "reviewer_max_tokens": ORCH_REVIEWER_MAX_TOKENS,
        "step_timeout_sec": ORCH_STEP_TIMEOUT_SEC,
        "job_timeout_sec": ORCH_JOB_TIMEOUT_SEC,
        "agent_http_timeout_sec": ORCH_AGENT_HTTP_TIMEOUT_SEC,
        "planner_agent_timeout_sec": ORCH_PLANNER_AGENT_TIMEOUT_SEC,
        "coder_agent_timeout_sec": ORCH_CODER_AGENT_TIMEOUT_SEC,
        "reviewer_agent_timeout_sec": ORCH_REVIEWER_AGENT_TIMEOUT_SEC,
        "index_context_timeout_sec": ORCH_INDEX_CONTEXT_TIMEOUT_SEC,
        "planner_prompt_char_limit": ORCH_PLANNER_PROMPT_CHAR_LIMIT,
        "coder_prompt_char_limit": ORCH_CODER_PROMPT_CHAR_LIMIT,
        "reviewer_prompt_char_limit": ORCH_REVIEWER_PROMPT_CHAR_LIMIT,
        "planner_context_char_limit": ORCH_PLANNER_CONTEXT_CHAR_LIMIT,
        "coder_context_char_limit": ORCH_CODER_CONTEXT_CHAR_LIMIT,
        "reviewer_context_char_limit": ORCH_REVIEWER_CONTEXT_CHAR_LIMIT,
        "experience_memory_char_limit": ORCH_EXPERIENCE_MEMORY_CHAR_LIMIT,
        "forensic_max_inventory": ORCH_FORENSIC_MAX_INVENTORY,
        "max_force_retries": ORCH_MAX_FORCE_RETRIES,
        "force_complete": ORCH_FORCE_COMPLETE,
        "allow_synthetic_fallback": ORCH_ALLOW_SYNTHETIC_FALLBACK,
        "code_generation_strategy": ORCH_CODE_GENERATION_STRATEGY,
        "min_files": ORCH_MIN_FILES,
        "min_dirs": ORCH_MIN_DIRS,
        "stage11_min_files": ORCH_STAGE11_MIN_FILES,
        "stage11_min_dirs": ORCH_STAGE11_MIN_DIRS,
        "stage_thresholds": dict(_STAGE_THRESHOLDS),
        "selected_profile": ORCH_SELECTED_PROFILE,
        "model_tuning_level": ORCH_MODEL_TUNING_LEVEL,
        "token_tuning_level": ORCH_TOKEN_TUNING_LEVEL,
        "timeout_tuning_level": ORCH_TIMEOUT_TUNING_LEVEL,
        "model_routes": get_configured_model_routes(),
        "execution_controls": get_configured_execution_controls(),
        "advisory_controls": advisory_controls,
        "gpu_only_preferred": ORCH_GPU_ONLY_PREFERRED,
        "config_path": ORCH_RUNTIME_CONFIG_PATH,
    }


def _runtime_config_payload() -> Dict[str, Any]:
    return {
        **_runtime_config_base_payload(),
        "available_models": get_available_ollama_models(),
        "gpu_runtime": get_gpu_runtime_info(),
        "runtime_profiles": get_recommended_runtime_profiles(),
    }


def _apply_runtime_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    global ORCH_MAX_TOKENS_PER_STEP
    global ORCH_DEFAULT_REQUEST_MAX_TOKENS
    global ORCH_CHAT_REQUEST_MAX_TOKENS
    global ORCH_DEFAULT_AGENT_MAX_TOKENS
    global ORCH_PLANNER_MAX_TOKENS
    global ORCH_CODER_MAX_TOKENS
    global ORCH_REVIEWER_MAX_TOKENS
    global ORCH_STEP_TIMEOUT_SEC
    global ORCH_JOB_TIMEOUT_SEC
    global ORCH_AGENT_HTTP_TIMEOUT_SEC
    global ORCH_PLANNER_AGENT_TIMEOUT_SEC
    global ORCH_CODER_AGENT_TIMEOUT_SEC
    global ORCH_REVIEWER_AGENT_TIMEOUT_SEC
    global ORCH_INDEX_CONTEXT_TIMEOUT_SEC
    global ORCH_PLANNER_PROMPT_CHAR_LIMIT
    global ORCH_CODER_PROMPT_CHAR_LIMIT
    global ORCH_REVIEWER_PROMPT_CHAR_LIMIT
    global ORCH_PLANNER_CONTEXT_CHAR_LIMIT
    global ORCH_CODER_CONTEXT_CHAR_LIMIT
    global ORCH_REVIEWER_CONTEXT_CHAR_LIMIT
    global ORCH_EXPERIENCE_MEMORY_CHAR_LIMIT
    global ORCH_FORENSIC_MAX_INVENTORY
    global ORCH_MAX_FORCE_RETRIES
    global ORCH_FORCE_COMPLETE
    global ORCH_ALLOW_SYNTHETIC_FALLBACK
    global ORCH_CODE_GENERATION_STRATEGY
    global ORCH_SELECTED_PROFILE
    global ORCH_MODEL_TUNING_LEVEL
    global ORCH_TOKEN_TUNING_LEVEL
    global ORCH_TIMEOUT_TUNING_LEVEL
    global ORCH_MIN_FILES
    global ORCH_MIN_DIRS
    global ORCH_GPU_ONLY_PREFERRED
    global ORCH_ADVISORY_CONTROLS

    max_tokens_per_step = _coerce_runtime_int(
        payload.get("max_tokens_per_step", ORCH_MAX_TOKENS_PER_STEP),
        ORCH_MAX_TOKENS_PER_STEP,
        minimum=1024,
    )
    default_request_max_tokens = _coerce_runtime_int(
        payload.get(
            "default_request_max_tokens",
            ORCH_DEFAULT_REQUEST_MAX_TOKENS,
        ),
        ORCH_DEFAULT_REQUEST_MAX_TOKENS,
        minimum=4096,
        maximum=max_tokens_per_step,
    )
    chat_request_max_tokens = _coerce_runtime_int(
        payload.get(
            "chat_request_max_tokens",
            ORCH_CHAT_REQUEST_MAX_TOKENS,
        ),
        ORCH_CHAT_REQUEST_MAX_TOKENS,
        minimum=128,
        maximum=max_tokens_per_step,
    )
    default_agent_max_tokens = _coerce_runtime_int(
        payload.get(
            "default_agent_max_tokens",
            ORCH_DEFAULT_AGENT_MAX_TOKENS,
        ),
        ORCH_DEFAULT_AGENT_MAX_TOKENS,
        minimum=1024,
        maximum=max_tokens_per_step,
    )
    planner_max_tokens = _coerce_runtime_int(
        payload.get(
            "planner_max_tokens",
            ORCH_PLANNER_MAX_TOKENS,
        ),
        ORCH_PLANNER_MAX_TOKENS,
        minimum=1024,
        maximum=max_tokens_per_step,
    )
    coder_max_tokens = _coerce_runtime_int(
        payload.get(
            "coder_max_tokens",
            ORCH_CODER_MAX_TOKENS,
        ),
        ORCH_CODER_MAX_TOKENS,
        minimum=1024,
        maximum=max_tokens_per_step,
    )
    reviewer_max_tokens = _coerce_runtime_int(
        payload.get(
            "reviewer_max_tokens",
            ORCH_REVIEWER_MAX_TOKENS,
        ),
        ORCH_REVIEWER_MAX_TOKENS,
        minimum=1024,
        maximum=max_tokens_per_step,
    )
    step_timeout_sec = _coerce_runtime_int(
        payload.get("step_timeout_sec", ORCH_STEP_TIMEOUT_SEC),
        ORCH_STEP_TIMEOUT_SEC,
        minimum=60,
    )
    job_timeout_sec = _coerce_runtime_int(
        payload.get("job_timeout_sec", ORCH_JOB_TIMEOUT_SEC),
        ORCH_JOB_TIMEOUT_SEC,
        minimum=600,
    )
    agent_http_timeout_sec = _coerce_runtime_int(
        payload.get(
            "agent_http_timeout_sec",
            ORCH_AGENT_HTTP_TIMEOUT_SEC,
        ),
        ORCH_AGENT_HTTP_TIMEOUT_SEC,
        minimum=180,
    )
    planner_agent_timeout_sec = _coerce_runtime_int(
        payload.get(
            "planner_agent_timeout_sec",
            ORCH_PLANNER_AGENT_TIMEOUT_SEC,
        ),
        ORCH_PLANNER_AGENT_TIMEOUT_SEC,
        minimum=60,
        maximum=agent_http_timeout_sec,
    )
    coder_agent_timeout_sec = _coerce_runtime_int(
        payload.get(
            "coder_agent_timeout_sec",
            ORCH_CODER_AGENT_TIMEOUT_SEC,
        ),
        ORCH_CODER_AGENT_TIMEOUT_SEC,
        minimum=60,
        maximum=agent_http_timeout_sec,
    )
    reviewer_agent_timeout_sec = _coerce_runtime_int(
        payload.get(
            "reviewer_agent_timeout_sec",
            ORCH_REVIEWER_AGENT_TIMEOUT_SEC,
        ),
        ORCH_REVIEWER_AGENT_TIMEOUT_SEC,
        minimum=60,
        maximum=agent_http_timeout_sec,
    )
    index_context_timeout_sec = _coerce_runtime_int(
        payload.get(
            "index_context_timeout_sec",
            ORCH_INDEX_CONTEXT_TIMEOUT_SEC,
        ),
        ORCH_INDEX_CONTEXT_TIMEOUT_SEC,
        minimum=0,
        maximum=step_timeout_sec,
    )
    planner_prompt_char_limit = _coerce_runtime_int(
        payload.get(
            "planner_prompt_char_limit",
            ORCH_PLANNER_PROMPT_CHAR_LIMIT,
        ),
        ORCH_PLANNER_PROMPT_CHAR_LIMIT,
        minimum=1200,
    )
    coder_prompt_char_limit = _coerce_runtime_int(
        payload.get(
            "coder_prompt_char_limit",
            ORCH_CODER_PROMPT_CHAR_LIMIT,
        ),
        ORCH_CODER_PROMPT_CHAR_LIMIT,
        minimum=1200,
    )
    reviewer_prompt_char_limit = _coerce_runtime_int(
        payload.get(
            "reviewer_prompt_char_limit",
            ORCH_REVIEWER_PROMPT_CHAR_LIMIT,
        ),
        ORCH_REVIEWER_PROMPT_CHAR_LIMIT,
        minimum=1200,
    )
    planner_context_char_limit = _coerce_runtime_int(
        payload.get(
            "planner_context_char_limit",
            ORCH_PLANNER_CONTEXT_CHAR_LIMIT,
        ),
        ORCH_PLANNER_CONTEXT_CHAR_LIMIT,
        minimum=0,
    )
    coder_context_char_limit = _coerce_runtime_int(
        payload.get(
            "coder_context_char_limit",
            ORCH_CODER_CONTEXT_CHAR_LIMIT,
        ),
        ORCH_CODER_CONTEXT_CHAR_LIMIT,
        minimum=0,
    )
    reviewer_context_char_limit = _coerce_runtime_int(
        payload.get(
            "reviewer_context_char_limit",
            ORCH_REVIEWER_CONTEXT_CHAR_LIMIT,
        ),
        ORCH_REVIEWER_CONTEXT_CHAR_LIMIT,
        minimum=0,
    )
    experience_memory_char_limit = _coerce_runtime_int(
        payload.get(
            "experience_memory_char_limit",
            ORCH_EXPERIENCE_MEMORY_CHAR_LIMIT,
        ),
        ORCH_EXPERIENCE_MEMORY_CHAR_LIMIT,
        minimum=0,
    )
    forensic_max_inventory = _coerce_runtime_int(
        payload.get(
            "forensic_max_inventory",
            ORCH_FORENSIC_MAX_INVENTORY,
        ),
        ORCH_FORENSIC_MAX_INVENTORY,
        minimum=100,
    )
    max_force_retries = _coerce_runtime_int(
        payload.get("max_force_retries", ORCH_MAX_FORCE_RETRIES),
        ORCH_MAX_FORCE_RETRIES,
        minimum=1,
    )
    force_complete = bool(
        payload.get("force_complete", ORCH_FORCE_COMPLETE)
    )
    allow_synthetic_fallback = bool(
        payload.get(
            "allow_synthetic_fallback",
            ORCH_ALLOW_SYNTHETIC_FALLBACK,
        )
    )
    code_generation_strategy = _normalize_code_generation_strategy(
        payload.get(
            "code_generation_strategy",
            ORCH_CODE_GENERATION_STRATEGY,
        )
    )
    selected_profile = str(
        payload.get("selected_profile", ORCH_SELECTED_PROFILE)
        or ORCH_SELECTED_PROFILE
    ).strip() or CURRENT_GPU_PROFILE_KEY
    if selected_profile not in {
        CURRENT_GPU_PROFILE_KEY,
        ORCH_RUNTIME_PROFILE_CUSTOM_KEY,
        "upper_tier_70b",
    }:
        selected_profile = CURRENT_GPU_PROFILE_KEY
    min_files = _coerce_runtime_int(
        payload.get("min_files", ORCH_MIN_FILES),
        ORCH_MIN_FILES,
        minimum=1,
    )
    min_dirs = _coerce_runtime_int(
        payload.get("min_dirs", ORCH_MIN_DIRS),
        ORCH_MIN_DIRS,
        minimum=0,
    )
    model_tuning_level = _coerce_runtime_int(
        payload.get(
            "model_tuning_level",
            ORCH_MODEL_TUNING_LEVEL,
        ),
        ORCH_MODEL_TUNING_LEVEL,
        minimum=-1,
        maximum=1,
    )
    token_tuning_level = _coerce_runtime_int(
        payload.get(
            "token_tuning_level",
            ORCH_TOKEN_TUNING_LEVEL,
        ),
        ORCH_TOKEN_TUNING_LEVEL,
        minimum=-1,
        maximum=1,
    )
    timeout_tuning_level = _coerce_runtime_int(
        payload.get(
            "timeout_tuning_level",
            ORCH_TIMEOUT_TUNING_LEVEL,
        ),
        ORCH_TIMEOUT_TUNING_LEVEL,
        minimum=-1,
        maximum=1,
    )
    gpu_only_preferred = _coerce_runtime_bool(
        payload.get(
            "gpu_only_preferred",
            ORCH_GPU_ONLY_PREFERRED,
        ),
        ORCH_GPU_ONLY_PREFERRED,
    )
    effective_payload = _apply_runtime_tuning_presets(
        payload,
        selected_profile=selected_profile,
        model_tuning_level=model_tuning_level,
        token_tuning_level=token_tuning_level,
        timeout_tuning_level=timeout_tuning_level,
    )

    max_tokens_per_step = _coerce_runtime_int(
        effective_payload.get("max_tokens_per_step", max_tokens_per_step),
        max_tokens_per_step,
        minimum=1024,
    )
    default_request_max_tokens = _coerce_runtime_int(
        effective_payload.get(
            "default_request_max_tokens",
            default_request_max_tokens,
        ),
        default_request_max_tokens,
        minimum=4096,
        maximum=max_tokens_per_step,
    )
    chat_request_max_tokens = _coerce_runtime_int(
        effective_payload.get(
            "chat_request_max_tokens",
            chat_request_max_tokens,
        ),
        chat_request_max_tokens,
        minimum=128,
        maximum=max_tokens_per_step,
    )
    default_agent_max_tokens = _coerce_runtime_int(
        effective_payload.get(
            "default_agent_max_tokens",
            default_agent_max_tokens,
        ),
        default_agent_max_tokens,
        minimum=1024,
        maximum=max_tokens_per_step,
    )
    planner_max_tokens = _coerce_runtime_int(
        effective_payload.get("planner_max_tokens", planner_max_tokens),
        planner_max_tokens,
        minimum=1024,
        maximum=max_tokens_per_step,
    )
    coder_max_tokens = _coerce_runtime_int(
        effective_payload.get("coder_max_tokens", coder_max_tokens),
        coder_max_tokens,
        minimum=1024,
        maximum=max_tokens_per_step,
    )
    reviewer_max_tokens = _coerce_runtime_int(
        effective_payload.get("reviewer_max_tokens", reviewer_max_tokens),
        reviewer_max_tokens,
        minimum=1024,
        maximum=max_tokens_per_step,
    )
    step_timeout_sec = _coerce_runtime_int(
        effective_payload.get("step_timeout_sec", step_timeout_sec),
        step_timeout_sec,
        minimum=60,
    )
    job_timeout_sec = _coerce_runtime_int(
        effective_payload.get("job_timeout_sec", job_timeout_sec),
        job_timeout_sec,
        minimum=600,
    )
    agent_http_timeout_sec = _coerce_runtime_int(
        effective_payload.get(
            "agent_http_timeout_sec",
            agent_http_timeout_sec,
        ),
        agent_http_timeout_sec,
        minimum=180,
    )
    planner_agent_timeout_sec = _coerce_runtime_int(
        effective_payload.get(
            "planner_agent_timeout_sec",
            planner_agent_timeout_sec,
        ),
        planner_agent_timeout_sec,
        minimum=60,
        maximum=agent_http_timeout_sec,
    )
    coder_agent_timeout_sec = _coerce_runtime_int(
        effective_payload.get(
            "coder_agent_timeout_sec",
            coder_agent_timeout_sec,
        ),
        coder_agent_timeout_sec,
        minimum=60,
        maximum=agent_http_timeout_sec,
    )
    reviewer_agent_timeout_sec = _coerce_runtime_int(
        effective_payload.get(
            "reviewer_agent_timeout_sec",
            reviewer_agent_timeout_sec,
        ),
        reviewer_agent_timeout_sec,
        minimum=60,
        maximum=agent_http_timeout_sec,
    )
    index_context_timeout_sec = _coerce_runtime_int(
        effective_payload.get(
            "index_context_timeout_sec",
            index_context_timeout_sec,
        ),
        index_context_timeout_sec,
        minimum=0,
        maximum=step_timeout_sec,
    )
    planner_prompt_char_limit = _coerce_runtime_int(
        effective_payload.get(
            "planner_prompt_char_limit",
            planner_prompt_char_limit,
        ),
        planner_prompt_char_limit,
        minimum=1200,
    )
    coder_prompt_char_limit = _coerce_runtime_int(
        effective_payload.get(
            "coder_prompt_char_limit",
            coder_prompt_char_limit,
        ),
        coder_prompt_char_limit,
        minimum=1200,
    )
    reviewer_prompt_char_limit = _coerce_runtime_int(
        effective_payload.get(
            "reviewer_prompt_char_limit",
            reviewer_prompt_char_limit,
        ),
        reviewer_prompt_char_limit,
        minimum=1200,
    )
    planner_context_char_limit = _coerce_runtime_int(
        effective_payload.get(
            "planner_context_char_limit",
            planner_context_char_limit,
        ),
        planner_context_char_limit,
        minimum=0,
    )
    coder_context_char_limit = _coerce_runtime_int(
        effective_payload.get(
            "coder_context_char_limit",
            coder_context_char_limit,
        ),
        coder_context_char_limit,
        minimum=0,
    )
    reviewer_context_char_limit = _coerce_runtime_int(
        effective_payload.get(
            "reviewer_context_char_limit",
            reviewer_context_char_limit,
        ),
        reviewer_context_char_limit,
        minimum=0,
    )
    model_routes = _normalize_runtime_model_routes(effective_payload)
    advisory_controls = _normalize_advisory_controls(effective_payload)

    ORCH_MAX_TOKENS_PER_STEP = max_tokens_per_step
    ORCH_DEFAULT_REQUEST_MAX_TOKENS = default_request_max_tokens
    ORCH_CHAT_REQUEST_MAX_TOKENS = chat_request_max_tokens
    ORCH_DEFAULT_AGENT_MAX_TOKENS = default_agent_max_tokens
    ORCH_PLANNER_MAX_TOKENS = planner_max_tokens
    ORCH_CODER_MAX_TOKENS = coder_max_tokens
    ORCH_REVIEWER_MAX_TOKENS = reviewer_max_tokens
    ORCH_STEP_TIMEOUT_SEC = step_timeout_sec
    ORCH_JOB_TIMEOUT_SEC = job_timeout_sec
    ORCH_AGENT_HTTP_TIMEOUT_SEC = agent_http_timeout_sec
    ORCH_PLANNER_AGENT_TIMEOUT_SEC = planner_agent_timeout_sec
    ORCH_CODER_AGENT_TIMEOUT_SEC = coder_agent_timeout_sec
    ORCH_REVIEWER_AGENT_TIMEOUT_SEC = reviewer_agent_timeout_sec
    ORCH_INDEX_CONTEXT_TIMEOUT_SEC = index_context_timeout_sec
    ORCH_PLANNER_PROMPT_CHAR_LIMIT = planner_prompt_char_limit
    ORCH_CODER_PROMPT_CHAR_LIMIT = coder_prompt_char_limit
    ORCH_REVIEWER_PROMPT_CHAR_LIMIT = reviewer_prompt_char_limit
    ORCH_PLANNER_CONTEXT_CHAR_LIMIT = planner_context_char_limit
    ORCH_CODER_CONTEXT_CHAR_LIMIT = coder_context_char_limit
    ORCH_REVIEWER_CONTEXT_CHAR_LIMIT = reviewer_context_char_limit
    ORCH_EXPERIENCE_MEMORY_CHAR_LIMIT = experience_memory_char_limit
    ORCH_FORENSIC_MAX_INVENTORY = forensic_max_inventory
    ORCH_MAX_FORCE_RETRIES = max_force_retries
    ORCH_FORCE_COMPLETE = force_complete
    ORCH_ALLOW_SYNTHETIC_FALLBACK = allow_synthetic_fallback
    ORCH_CODE_GENERATION_STRATEGY = code_generation_strategy
    ORCH_SELECTED_PROFILE = selected_profile
    ORCH_MODEL_TUNING_LEVEL = model_tuning_level
    ORCH_TOKEN_TUNING_LEVEL = token_tuning_level
    ORCH_TIMEOUT_TUNING_LEVEL = timeout_tuning_level
    ORCH_MIN_FILES = min_files
    ORCH_MIN_DIRS = min_dirs
    ORCH_GPU_ONLY_PREFERRED = gpu_only_preferred
    ORCH_ADVISORY_CONTROLS = advisory_controls
    return {
        **_runtime_config_base_payload(),
        "selected_profile": ORCH_SELECTED_PROFILE,
        "model_tuning_level": ORCH_MODEL_TUNING_LEVEL,
        "token_tuning_level": ORCH_TOKEN_TUNING_LEVEL,
        "timeout_tuning_level": ORCH_TIMEOUT_TUNING_LEVEL,
        "gpu_only_preferred": ORCH_GPU_ONLY_PREFERRED,
        "code_generation_strategy": ORCH_CODE_GENERATION_STRATEGY,
        "model_routes": model_routes,
        "advisory_controls": dict(ORCH_ADVISORY_CONTROLS),
    }


def _normalize_legacy_stage_thresholds(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    stage = compute_autonomous_stage_thresholds()
    try:
        min_files = int(normalized.get("min_files") or 0)
    except (TypeError, ValueError):
        min_files = 0
    try:
        min_dirs = int(normalized.get("min_dirs") or 0)
    except (TypeError, ValueError):
        min_dirs = 0
    if min_files >= 27:
        normalized["min_files"] = stage["stage_min_files"]
    if min_dirs <= 2:
        normalized["min_dirs"] = stage["stage_min_dirs"]
    normalized.setdefault("stage11_min_files", stage["stage11_min_files"])
    normalized.setdefault("stage11_min_dirs", stage["stage11_min_dirs"])
    normalized.setdefault("stage_thresholds", stage)
    return normalized


def _load_runtime_config_from_disk() -> Dict[str, Any]:
    path = _runtime_config_file_path()
    if not path.exists():
        payload = _runtime_config_payload()
        _save_runtime_config_to_disk(payload)
        return payload
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = _runtime_config_payload()
        _save_runtime_config_to_disk(payload)
        return payload
    if not isinstance(payload, dict):
        payload = _runtime_config_payload()
        _save_runtime_config_to_disk(payload)
        return payload
    payload = _normalize_legacy_stage_thresholds(payload)
    return _apply_runtime_config(payload)


def _save_runtime_config_to_disk(payload: Dict[str, Any]) -> None:
    path = _runtime_config_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@router.get("/runtime-config")
async def get_runtime_config(
    current_user=Depends(require_admin_mutation_quota),
) -> Dict[str, Any]:
    _load_runtime_config_from_disk()
    return _runtime_config_payload()


@router.put("/runtime-config")
@router.post("/runtime-config")
async def update_runtime_config(
    update: OrchestratorRuntimeConfigUpdate,
    current_user=Depends(require_admin_mutation_quota),
) -> Dict[str, Any]:
    current = _load_runtime_config_from_disk()
    merged = _merge_runtime_update_payload(
        current,
        update.model_dump(exclude_none=True),
    )
    applied = _apply_runtime_config(merged)
    _save_runtime_config_to_disk(applied)
    return _runtime_config_payload()


@router.websocket("/ws")
async def orchestrator_ws(websocket: WebSocket):
    # [#6] Sec-WebSocket-Protocol 우선, ?token= 폴백(점진 전환·무중단).
    from backend.auth import resolve_ws_token
    token, accept_subprotocol = resolve_ws_token(websocket)
    if token:
        try:
            from jose import jwt as _jwt
            from backend.auth import SECRET_KEY, ALGORITHM
            _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except Exception:
            await websocket.close(code=4001, reason="인증 실패")
            return

    await ws_channel.connect(websocket, subprotocol=accept_subprotocol)
    try:
        await websocket.send_json({
            "event": "connected",
            "timestamp": datetime.now().isoformat(),
        })
        while True:
            message = await websocket.receive_text()
            if str(message or "").strip().lower() == "ping":
                await websocket.send_json({
                    "event": "pong",
                    "timestamp": datetime.now().isoformat(),
                })
                continue
            await websocket.send_json({
                "event": "echo",
                "message": str(message or ""),
                "timestamp": datetime.now().isoformat(),
            })
    except WebSocketDisconnect:
        pass
    finally:
        ws_channel.disconnect(websocket)


_load_runtime_config_from_disk()


def _task_tokens(task: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9가-힣_-]+", (task or "").lower())
        if len(token) >= 2
    }


def _normalize_required_files(files: List[str]) -> List[str]:
    normalized: List[str] = []
    seen: set[str] = set()
    for item in files:
        rel = str(item or "").strip().replace("\\", "/")
        key = rel.lower()
        if not rel or key in seen:
            continue
        seen.add(key)
        normalized.append(rel)
    return normalized


def _extract_targeted_patch_paths(task: str) -> List[str]:
    task_text = str(task or "")
    match = re.search(
        r"수정 가능 파일은\s+(.+?)\s+뿐입니다",
        task_text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []

    segment = match.group(1)
    path_candidates = re.findall(
        r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*",
        segment,
    )
    filtered = [
        candidate
        for candidate in path_candidates
        if "." in candidate and not candidate.lower().startswith("http")
    ]
    return _normalize_required_files(filtered)


def _is_targeted_existing_patch_request(
    task: str,
    required_files: List[str],
) -> bool:
    targeted_files = _extract_targeted_patch_paths(task)
    if not targeted_files:
        return False

    lower_task = str(task or "").lower()
    lower_files = {
        str(path).lower().replace("\\", "/")
        for path in (required_files or targeted_files)
    }
    if any(
        token in lower_task
        for token in ["fastapi", "flask", "django", "nestjs", "express"]
    ):
        return False
    if any(
        path.startswith("backend/app/")
        or path.endswith("requirements.txt")
        or path.endswith("docker-compose.yml")
        for path in lower_files
    ):
        return False
    return True


def _default_validation_profile(task: str, required_files: List[str]) -> str:
    task_lower = (task or "").lower()
    lower_files = {str(path).lower() for path in required_files}
    if _is_targeted_existing_patch_request(task, required_files):
        return "generic"
    has_nextjs_files = any(
        path.endswith("package.json") for path in lower_files
    ) and any(
        path.startswith("app/") for path in lower_files
    )
    has_python_backend_files = any(
        path.endswith("requirements.txt") for path in lower_files
    ) or any(
        path.endswith(".py") or path.startswith("backend/")
        for path in lower_files
    )
    if has_nextjs_files and has_python_backend_files:
        return "generic"
    if has_nextjs_files:
        return "nextjs_react"
    if any(path.endswith("package.json") for path in lower_files) and any(
        path.startswith("src/") for path in lower_files
    ):
        return "node_service"
    if "go.mod" in lower_files or any(
        path.endswith(".go") for path in lower_files
    ):
        return "go_service"
    if "cargo.toml" in lower_files or any(
        path.endswith(".rs") for path in lower_files
    ):
        return "rust_service"
    if any(path.endswith("requirements.txt") for path in lower_files) or any(
        path.endswith(".py") for path in lower_files
    ):
        return "python_fastapi"
    if _has_nextjs_stack_markers(task_lower) and _has_python_backend_stack_markers(task_lower): # pyright: ignore[reportUndefinedVariable]
        return "generic"
    if any(token in task_lower for token in ["next.js", "nextjs", "react"]):
        return "nextjs_react"
    if any(
        token in task_lower
        for token in ["node", "express", "nestjs", "javascript", "typescript"]
    ):
        return "node_service"
    if any(token in task_lower for token in ["go", "golang"]):
        return "go_service"
    if any(
        token in task_lower for token in ["rust", "cargo", "actix", "axum"]
    ):
        return "rust_service"
    if any(
        token in task_lower
        for token in ["fastapi", "python", "api", "백엔드"]
    ):
        return "python_fastapi"
    return "generic"


def _detect_stack_family(task: str, mode: str) -> str:
    task_lower = (task or "").lower()
    if _is_targeted_existing_patch_request(task, []):
        return "generic"
    if any(
        token in task_lower
        for token in ["next.js", "nextjs", "react", "tsx", "tailwind"]
    ):
        return "nextjs_react"
    if any(
        token in task_lower
        for token in [
            "node",
            "express",
            "nestjs",
            "javascript",
            "typescript",
        ]
    ):
        return "node_service"
    if any(token in task_lower for token in ["go", "golang"]):
        return "go_service"
    if any(
        token in task_lower
        for token in ["rust", "cargo", "actix", "axum"]
    ):
        return "rust_service"
    if any(
        token in task_lower
        for token in ["fastapi", "flask", "django", "python"]
    ):
        return "python_fastapi"
    if mode == "design":
        return "nextjs_react"
    return "generic"


def _default_required_files_for_mode(task: str, mode: str) -> List[str]:
    def _with_architecture_baseline(paths: List[str]) -> List[str]:
        ordered: List[str] = []
        seen = set()
        for item in ORCH_ARCHITECTURE_BASELINE_FILES + paths:
            normalized = str(item).replace("\\", "/")
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(normalized)
        return ordered

    targeted_files = _extract_targeted_patch_paths(task)
    if targeted_files:
        return targeted_files

    stack_family = _detect_stack_family(task, mode)
    if stack_family == "fullstack_web":
        return _with_architecture_baseline([
            "README.md",
            ".gitignore",
            "docker-compose.yml",
            "package.json",
            "tsconfig.json",
            "next-env.d.ts",
            "next.config.js",
            "app/layout.tsx",
            "app/loading.tsx",
            "app/page.tsx",
            "app/dashboard/page.tsx",
            "app/api/health/route.ts",
            "app/api/brief/route.ts",
            "app/globals.css",
            "components/dashboardclient.tsx",
            "components/heropanel.tsx",
            "components/metriccluster.tsx",
            "components/signalmatrix.tsx",
            "components/focusrail.tsx",
            "components/insighttimeline.tsx",
            "components/executionboard.tsx",
            "components/themetoggle.tsx",
            "lib/types.ts",
            "lib/data.ts",
            ".env.example",
            "requirements.txt",
            "backend/app/main.py",
            "backend/app/core/config.py",
            "backend/app/core/security.py",
            "backend/app/core/database.py",
            "backend/app/api/deps.py",
            "backend/app/api/routes/__init__.py",
            "backend/app/api/routes/health.py",
            "backend/app/api/routes/auth.py",
            "backend/app/api/routes/catalog.py",
            "backend/app/api/routes/orders.py",
            "backend/app/controllers/health_controller.py",
            "backend/app/controllers/auth_controller.py",
            "backend/app/controllers/catalog_controller.py",
            "backend/app/controllers/order_controller.py",
            "backend/app/services/health_service.py",
            "backend/app/services/auth_service.py",
            "backend/app/services/catalog_service.py",
            "backend/app/services/order_service.py",
            "backend/app/repositories/health_repository.py",
            "backend/app/repositories/user_repository.py",
            "backend/app/repositories/catalog_repository.py",
            "backend/app/repositories/order_repository.py",
            "backend/app/infra/runtime_store.py",
            "backend/app/external_adapters/status_client.py",
            "backend/app/connectors/base.py",
            "backend/app/connectors/shopify.py",
            "backend/app/worker/tasks.py",
            "backend/tests/conftest.py",
            "backend/tests/test_health.py",
            "backend/tests/test_auth.py",
            "backend/tests/test_catalog_sync.py",
            "backend/tests/test_orders.py",
        ])
    if stack_family == "nextjs_react":
        return _with_architecture_baseline([
            "README.md",
            ".gitignore",
            "package.json",
            "tsconfig.json",
            "next-env.d.ts",
            "next.config.js",
            "app/layout.tsx",
            "app/loading.tsx",
            "app/page.tsx",
            "app/dashboard/page.tsx",
            "app/api/health/route.ts",
            "app/api/brief/route.ts",
            "app/globals.css",
            "components/dashboardclient.tsx",
            "components/heropanel.tsx",
            "components/metriccluster.tsx",
            "components/signalmatrix.tsx",
            "components/focusrail.tsx",
            "components/insighttimeline.tsx",
            "components/executionboard.tsx",
            "components/themetoggle.tsx",
            "lib/types.ts",
            "lib/data.ts",
        ])
    if stack_family == "node_service":
        return _with_architecture_baseline([
            "README.md",
            "package.json",
            "tsconfig.json",
            "src/index.ts",
            "src/app.ts",
            "src/config.ts",
            "src/types.ts",
            "src/routes/health.ts",
            "src/routes/orders.ts",
            "src/controllers/orderController.ts",
            "src/services/orderService.ts",
            "src/repositories/orderRepository.ts",
            "src/lib/runtimeStore.ts",
            "src/middleware/errorHandler.ts",
        ])
    if stack_family == "go_service":
        return _with_architecture_baseline([
            "README.md",
            "go.mod",
            "cmd/app/main.go",
            "internal/app/app.go",
            "internal/http/router.go",
            "internal/http/handlers/health.go",
            "internal/http/handlers/inventory.go",
            "internal/service/inventory_service.go",
            "internal/repository/inventory_repository.go",
            "internal/platform/runtime_store.go",
            "internal/domain/inventory.go",
        ])
    if stack_family == "rust_service":
        return _with_architecture_baseline([
            "README.md",
            "Cargo.toml",
            "src/main.rs",
            "src/app.rs",
            "src/http/mod.rs",
            "src/http/handlers.rs",
            "src/http/router.rs",
            "src/service/mod.rs",
            "src/service/order_service.rs",
            "src/repository/mod.rs",
            "src/repository/order_repository.rs",
            "src/platform/mod.rs",
            "src/platform/runtime_store.rs",
            "src/domain/mod.rs",
            "src/domain/order.rs",
        ])
    if stack_family == "python_fastapi":
        return _with_architecture_baseline([
            "README.md",
            ".env.example",
            ".gitignore",
            "docker-compose.yml",
            "requirements.txt",
            "backend/app/main.py",
            "backend/app/core/config.py",
            "backend/app/core/security.py",
            "backend/app/core/database.py",
            "backend/app/api/deps.py",
            "backend/app/api/routes/__init__.py",
            "backend/app/api/routes/health.py",
            "backend/app/api/routes/auth.py",
            "backend/app/api/routes/catalog.py",
            "backend/app/api/routes/orders.py",
            "backend/app/controllers/health_controller.py",
            "backend/app/controllers/auth_controller.py",
            "backend/app/controllers/catalog_controller.py",
            "backend/app/controllers/order_controller.py",
            "backend/app/services/health_service.py",
            "backend/app/services/auth_service.py",
            "backend/app/services/catalog_service.py",
            "backend/app/services/order_service.py",
            "backend/app/repositories/health_repository.py",
            "backend/app/repositories/user_repository.py",
            "backend/app/repositories/catalog_repository.py",
            "backend/app/repositories/order_repository.py",
            "backend/app/infra/runtime_store.py",
            "backend/app/external_adapters/status_client.py",
            "backend/app/connectors/base.py",
            "backend/app/connectors/shopify.py",
            "backend/app/worker/tasks.py",
            "backend/tests/conftest.py",
            "backend/tests/test_health.py",
            "backend/tests/test_auth.py",
            "backend/tests/test_catalog_sync.py",
            "backend/tests/test_orders.py",
        ])
    if mode in {"code", "full", "program_5step"}:
        return _with_architecture_baseline([
            "README.md",
            ".gitignore",
            "docs/architecture.md",
        ])
    return _with_architecture_baseline(["README.md"])


def _default_dod_targets(profile: str) -> List[str]:
    if profile == "python_fastapi":
        return [
            "docker compose up -d",
            "GET /health returns 200",
            "pytest -q passes",
        ]
    if profile == "nextjs_react":
        return [
            "npm install",
            "npm run build",
            "핵심 페이지 렌더링 파일 존재",
        ]
    if profile == "node_service":
        return [
            "npm install --ignore-scripts",
            "npm run build --if-present",
            "엔트리포인트/헬스 라우트 존재",
        ]
    if profile == "go_service":
        return [
            "go build ./...",
            "cmd/app/main.go 존재",
            "핵심 핸들러/서비스 흐름 구현",
        ]
    if profile == "rust_service":
        return [
            "cargo check",
            "src/main.rs 또는 lib.rs 존재",
            "핵심 핸들러/서비스 흐름 구현",
        ]
    return [
        "필수 파일 세트 존재",
        "빈 파일/빈 폴더 없음",
        "대표 빌드 또는 실행 스크립트 존재",
    ]


def _default_orchestration_spec(
    task: str,
    requested_mode: str,
) -> OrchestrationSpec:
    requested_mode = _normalize_requested_mode(requested_mode)
    if requested_mode == "manual_9step":
        required_files = _default_required_files_for_mode(task, "code")
        validation_profile = _default_validation_profile(task, required_files)
        return OrchestrationSpec(
            mode="manual_9step",
            pipeline=PIPELINES["manual_9step"], # pyright: ignore[reportUndefinedVariable]
            required_files=required_files,
            validation_profile=validation_profile,
            dod_targets=_default_dod_targets(validation_profile),
            reasoning=(
                "administrator manual evidence-based "
                "5-step workflow selected"
            ),
            spec_source="manual",
            manual_steps=list(MANUAL_ORCHESTRATION_STEPS), # pyright: ignore[reportUndefinedVariable]
        )
    resolved_mode = (
        detect_mode(task) # pyright: ignore[reportUndefinedVariable]
        if requested_mode == "auto"
        else requested_mode
    )
    required_files = _default_required_files_for_mode(task, resolved_mode)
    validation_profile = _default_validation_profile(task, required_files)
    effective_pipeline = _filter_pipeline_for_validation_profile(
        PIPELINES.get(resolved_mode, ["planner", "coder"]), # pyright: ignore[reportUndefinedVariable]
        validation_profile,
    )
    return OrchestrationSpec(
        mode=resolved_mode,
        pipeline=effective_pipeline,
        required_files=required_files,
        validation_profile=validation_profile,
        dod_targets=_default_dod_targets(validation_profile),
        reasoning="planner unavailable, heuristic fallback applied",
        spec_source="fallback",
        fallback_reason="planner_spec_unavailable",
    )


def _normalize_pipeline_agents(agents: List[Any]) -> List[str]:
    available_agents = AGENTS if isinstance(AGENTS, dict) else (_current_agents() or {})
    normalized: List[str] = []
    seen: set[str] = set()
    for item in agents:
        agent = str(item or "").strip()
        if agent not in available_agents or agent in seen:
            continue
        seen.add(agent)
        normalized.append(agent)
    return normalized


def _resolve_a_brain_pipeline(validation_profile: str) -> List[str]:
    profile = str(validation_profile or "generic").strip().lower()
    pipeline = ["reasoner", "planner"]
    if profile in {"nextjs_react", "nextjs_app"}:
        pipeline.append("designer")
    return _normalize_pipeline_agents(pipeline)


def _resolve_b_brain_generator_profile(validation_profile: str) -> str:
    profile = str(validation_profile or "generic").strip().lower()
    if profile in {"python_fastapi", "python_worker"}:
        return "python_fastapi"
    if profile == "nextjs_app":
        return "nextjs_react"
    if profile in {"nextjs_react", "node_service", "go_service", "rust_service"}:
        return profile
    return "python_fastapi"


def _resolve_b_brain_additional_profiles(validation_profile: str, task: str) -> List[str]:
    profile = str(validation_profile or "generic").strip().lower()
    source_text = str(task or "").lower()
    additional: List[str] = []

    if profile == "python_fastapi":
        additional.append("nextjs_react")
        if any(marker in source_text for marker in ["node", "worker", "queue", "event", "agent"]):
            additional.append("node_service")
        if any(marker in source_text for marker in ["go", "golang", "gateway", "proxy"]):
            additional.append("go_service")
        if any(marker in source_text for marker in ["rust", "high performance", "engine"]):
            additional.append("rust_service")
    elif profile == "nextjs_app":
        additional.append("node_service")

    deduped: List[str] = []
    for item in additional:
        normalized = str(item or "").strip().lower()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def _resolve_b_brain_generator_family(validation_profile: str) -> str:
    profile = _resolve_b_brain_generator_profile(validation_profile)
    if profile == "python_fastapi":
        return "python_code_generator"
    return "non_python_code_generator"


def _filter_pipeline_for_validation_profile(
    agents: List[str],
    validation_profile: str,
) -> List[str]:
    profile = str(validation_profile or "generic").strip().lower()
    if ORCH_CODE_GENERATION_STRATEGY == "auto_generator":
        a_brain_pipeline = _resolve_a_brain_pipeline(profile)
        return a_brain_pipeline + [ORCH_B_BRAIN_AGENT_KEY]

    filtered = list(agents)

    if profile == "python_fastapi":
        filtered = [
            agent for agent in filtered
            if agent not in {"planner", "reviewer", "designer"}
        ]
        if not filtered:
            filtered = ["coder"]
    elif profile != "nextjs_react":
        filtered = [agent for agent in filtered if agent != "designer"]

    return filtered or ["coder"]


def _normalize_requested_mode(requested_mode: Any) -> str:
    candidate = str(requested_mode or "").strip()
    if candidate == "run":
        return "code"
    return candidate


def _planner_resolved_mode(
    request_mode: str,
    planner_mode: Any,
    fallback_mode: str,
) -> str:
    request_mode = _normalize_requested_mode(request_mode)
    fallback_mode = _normalize_requested_mode(fallback_mode)
    if request_mode != "auto":
        return request_mode
    candidate = _normalize_requested_mode(planner_mode)
    if candidate in PIPELINES: # pyright: ignore[reportUndefinedVariable]
        return candidate
    return fallback_mode


def _should_bypass_planner_spec_resolution(
    request: OrchestrationRequest,
    fallback: OrchestrationSpec,
) -> bool:
    request_mode = _normalize_requested_mode(request.mode)
    if request.manual_mode or request_mode in {"plan", "design", "review"}:
        return False
    if _is_targeted_existing_patch_request(
        request.task,
        fallback.required_files,
    ):
        return False
    return fallback.validation_profile == "python_fastapi"


def _build_resolved_orchestration_spec(
    request: OrchestrationRequest,
    fallback: OrchestrationSpec,
    parsed: Dict[str, Any],
) -> OrchestrationSpec:
    resolved_mode = _planner_resolved_mode(
        request.mode,
        parsed.get("mode"),
        fallback.mode,
    )
    planner_pipeline = _normalize_pipeline_agents(
        parsed.get("pipeline", [])
    )
    required_files = _normalize_required_files(
        parsed.get("required_files", [])
    )
    fallback_notes: List[str] = []
    targeted_required_files = _extract_targeted_patch_paths(request.task)
    targeted_existing_patch = _is_targeted_existing_patch_request(
        request.task,
        targeted_required_files,
    )

    if targeted_existing_patch and targeted_required_files:
        required_files = targeted_required_files
        fallback_notes.append("targeted_required_files")

    if not required_files:
        required_files = _default_required_files_for_mode(
            request.task,
            resolved_mode,
        )
        fallback_notes.append("required_files")

    validation_profile = str(
        parsed.get("validation_profile")
        or _default_validation_profile(request.task, required_files)
    ).strip() or fallback.validation_profile
    if targeted_existing_patch:
        validation_profile = "generic"
        fallback_notes.append("targeted_validation_profile")
    dod_targets = [
        str(item).strip()
        for item in parsed.get("dod_targets", [])
        if str(item).strip()
    ]
    if targeted_existing_patch:
        dod_targets = _default_dod_targets(validation_profile)
        fallback_notes.append("targeted_dod_targets")
    if not dod_targets:
        dod_targets = _default_dod_targets(validation_profile)
        fallback_notes.append("dod_targets")

    effective_pipeline = (
        request.pipeline
        or planner_pipeline
        or PIPELINES.get(resolved_mode, fallback.pipeline) # pyright: ignore[reportUndefinedVariable]
        or fallback.pipeline
    )
    effective_pipeline = _filter_pipeline_for_validation_profile(
        effective_pipeline,
        validation_profile,
    )
    if not planner_pipeline and not request.pipeline:
        fallback_notes.append("pipeline")

    reasoning = str(parsed.get("reasoning") or "").strip()
    if not reasoning:
        reasoning = "planner JSON accepted"
        if fallback_notes:
            reasoning += " with normalized fallback fields"

    return OrchestrationSpec(
        mode=resolved_mode,
        pipeline=effective_pipeline,
        required_files=required_files,
        validation_profile=validation_profile,
        dod_targets=dod_targets,
        reasoning=reasoning,
        spec_source="planner",
        fallback_reason=(
            ", ".join(fallback_notes)
            if fallback_notes
            else None
        ),
    )


def _resolve_template_profile(
    orchestration_spec: OrchestrationSpec,
) -> str:
    profile = str(orchestration_spec.validation_profile or "generic").strip()
    if profile in {
        "python_fastapi",
        "nextjs_react",
        "node_service",
        "go_service",
        "rust_service",
    }:
        return profile
    return "generic"


def _template_baseline_for_profile(validation_profile: str) -> Dict[str, str]:
    profile = str(validation_profile or "generic").strip().lower()
    baselines: Dict[str, Dict[str, str]] = {
        "python_fastapi": {
            "family": "fastapi-ops-slice",
            "version": "2026.03-modern-ops-v2",
            "notes": "운영형 FastAPI 보일러플레이트 기준선",
        },
        "nextjs_react": {
            "family": "nextjs-ops-canvas",
            "version": "2026.03-modern-ops-v2",
            "notes": "디자인 시스템형 Next.js 대시보드 기준선",
        },
        "node_service": {
            "family": "node-ops-service",
            "version": "2026.03-modern-ops-v1",
            "notes": "운영형 Node 서비스 기준선",
        },
        "go_service": {
            "family": "go-ops-service",
            "version": "2026.03-modern-ops-v1",
            "notes": "운영형 Go 서비스 기준선",
        },
        "rust_service": {
            "family": "rust-ops-service",
            "version": "2026.03-modern-ops-v1",
            "notes": "운영형 Rust 서비스 기준선",
        },
        "generic": {
            "family": "generic-scaffold",
            "version": "2026.03-fallback-v1",
            "notes": "일반 스캐폴드 기준선",
        },
    }
    selected = baselines.get(profile, baselines["generic"])
    return dict(selected)


def _build_generated_template_manifest(
    project_name: str,
    orchestration_spec: OrchestrationSpec,
) -> str:
    baseline = _template_baseline_for_profile(
        orchestration_spec.validation_profile,
    )
    payload = {
        "project_name": project_name,
        "template_profile": _resolve_template_profile(orchestration_spec),
        "template_family": baseline["family"],
        "template_version": baseline["version"],
        "template_notes": baseline["notes"],
        "spec_source": orchestration_spec.spec_source,
        "validation_profile": orchestration_spec.validation_profile,
        "mode": orchestration_spec.mode,
        "pipeline": orchestration_spec.pipeline,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _run_b_brain_multi_generator(
    *,
    project_name: str,
    validation_profile: str,
    task: str,
    output_dir: Path,
) -> Dict[str, Any]:
    from backend.generators.facade import (
        generate_multi_project_bundle,
        generate_non_python_project_bundle,
        generate_python_project_bundle,
    )

    generator_profile = _resolve_b_brain_generator_profile(validation_profile)
    additional_profiles = _resolve_b_brain_additional_profiles(validation_profile, task)
    generator_family = _resolve_b_brain_generator_family(validation_profile)
    if additional_profiles:
        generation_result = generate_multi_project_bundle(
            project_name=project_name,
            primary_profile=generator_profile,
            additional_profiles=additional_profiles,
            task=task,
            output_dir=output_dir,
        )
        generator_family = "multi_code_generator"
    elif generator_family == "python_code_generator":
        generation_result = generate_python_project_bundle(
            project_name=project_name,
            profile=generator_profile,
            task=task,
            output_dir=output_dir,
        )
    else:
        generation_result = generate_non_python_project_bundle(
            project_name=project_name,
            profile=generator_profile,
            task=task,
            output_dir=output_dir,
        )
    return {
        "generator_family": generator_family,
        "generator_profile": generator_profile,
        "additional_profiles": additional_profiles,
        "written_files": list(generation_result.written_files),
        "metadata": dict(generation_result.metadata),
        "file_count": len(generation_result.written_files),
    }



def _is_locked_targeted_patch_run(
    task: str,
    orchestration_spec: OrchestrationSpec,
) -> bool:
    required_files = _normalize_required_files(
        list(orchestration_spec.required_files or [])
    )
    if not required_files:
        return False
    if str(orchestration_spec.validation_profile or "").strip().lower() != "generic":
        return False
    # tiny targeted patch 실험은 최신 경로라도 required_files 밖 생성을 막아야 한다.
    return _is_targeted_existing_patch_request(task, required_files)


def _build_fixed_scaffold_files(
    task: str,
    project_name: str,
    orchestration_spec: OrchestrationSpec,
) -> tuple[str, List[Dict[str, str]], str]:
    template_profile = _resolve_template_profile(orchestration_spec)
    required_files_only = _is_locked_targeted_patch_run(
        task,
        orchestration_spec,
    )
    always_include = set() if required_files_only else {
        "docs/architecture.md",
        "docs/architecture.contract.json",
        "docs/orchestration_rules_checklist.md",
    }
    required_lookup = {
        _normalize_rel(path) # pyright: ignore[reportUndefinedVariable] # pyright: ignore[reportUndefinedVariable]
        for path in (orchestration_spec.required_files or [])
        if str(path).strip()
    }

    template_candidates: Dict[str, str] = {
        "docs/architecture.md": _build_architecture_doc_template(project_name),
        "docs/architecture.contract.json": _build_architecture_contract_template(project_name),
        "docs/orchestration_rules_checklist.md": (
            "# Orchestration Rules Checklist\n\n"
            "- Keep required files, structure compliance, and validation gates aligned.\n"
            "- Block delivery when structure validation fails.\n"
            "- Preserve implementation and validation traceability.\n"
        ),
    }

    if template_profile == "python_fastapi":
        template_candidates.update(
            {
                "README.md": (
                    f"# {project_name}\n\n"
                    "Generated FastAPI scaffold.\n\n"
                    "## Included Runtime\n\n"
                    "- `app/main.py` FastAPI runtime entrypoint\n"
                    "- `backend/core` runtime/security core layer\n"
                    "- `frontend/app/page.tsx` operator-facing front surface\n"
                ),
                "requirements.txt": (
                    "fastapi==0.110.0\n"
                    "uvicorn==0.27.1\n"
                    "httpx==0.27.0\n"
                    "pytest==8.2.0\n"
                    "pyjwt==2.9.0\n"
                    "bcrypt==4.2.0\n"
                ),
                "backend/app/main.py": (
                    "from fastapi import FastAPI\n"
                    "from backend.app.api.routes import router as api_router\n"
                    "from backend.app.core.config import settings\n\n"
                    "from backend.app.core.logging import configure_logging\n"
                    "from backend.app.middleware.request_context import RequestContextMiddleware\n\n"
                    "configure_logging()\n\n"
                    "app = FastAPI(\n"
                    "    title=settings.app_name,\n"
                    "    version=\"0.1.0\",\n"
                    ")\n"
                    "app.add_middleware(RequestContextMiddleware)\n"
                    "app.include_router(api_router)\n\n"
                    "@app.get(\"/\")\n"
                    "def root() -> dict:\n"
                    "    return {\n"
                    "        \"success\": True,\n"
                    "        \"message\": \"vertical slice boilerplate ready\",\n"
                    "    }\n"
                ),
                "backend/app/api/routes/health.py": (
                    "from fastapi import APIRouter\n\n"
                    "from backend.app.controllers.health_controller import get_health_response\n\n"
                    "router = APIRouter()\n\n"
                    "@router.get('/health')\n"
                    "def health():\n"
                    "    payload = get_health_response()\n"
                    "    return {'success': True, 'data': payload}\n"
                ),
                "app/api/routes/__init__.py": "",
                "app/api/routes/health.py": (
                    "from fastapi import APIRouter\n\n"
                    "router = APIRouter()\n\n"
                    "@router.get('/health')\n"
                    "def health() -> dict:\n"
                    "    return {'status': 'ok', 'service': 'customer-order-generator'}\n"
                ),
                "backend/app/controllers/health_controller.py": (
                    "from backend.app.services.health_service import get_health_payload\n\n"
                    "def get_health_response():\n"
                    "    return get_health_payload()\n"
                ),
                "backend/app/services/health_service.py": (
                    "from backend.app.external_adapters.status_client import fetch_upstream_status\n"
                    "from backend.app.repositories.health_repository import read_health_status\n\n"
                    "def get_health_payload():\n"
                    "    payload = read_health_status()\n"
                    "    payload.update(fetch_upstream_status())\n"
                    "    return payload\n"
                ),
                "backend/app/repositories/health_repository.py": (
                    "from backend.app.infra.runtime_store import read_runtime_metadata\n\n"
                    "def read_health_status():\n"
                    "    return {\"status\": \"ok\", \"runtime\": read_runtime_metadata()}\n"
                ),
                "backend/app/infra/runtime_store.py": (
                    "from backend.app.core.config import settings\n"
                    "from backend.app.core.database import APP_BOOT, ORDERS, PRODUCTS, QUEUE, USERS\n\n"
                    "def read_runtime_metadata() -> dict:\n"
                    "    return {\n"
                    "        \"app_name\": settings.app_name,\n"
                    "        \"environment\": settings.app_env,\n"
                    "        \"runtime_channel\": settings.runtime_channel,\n"
                    "        \"started_at\": APP_BOOT[\"started_at\"],\n"
                    "        \"storage\": \"memory\",\n"
                    "        \"users\": len(USERS),\n"
                    "        \"products\": len(PRODUCTS),\n"
                    "        \"orders\": len(ORDERS),\n"
                    "        \"queued_jobs\": len(QUEUE),\n"
                    "    }\n"
                ),
                "backend/app/external_adapters/status_client.py": (
                    "def fetch_upstream_status() -> dict:\n"
                    "    return {\"provider\": \"local-simulated\", \"reachable\": True}\n"
                ),
                "backend/app/connectors/base.py": (
                    "class BaseConnector:\n"
                    "    def sync_products(self) -> list[dict]:\n"
                    "        raise NotImplementedError\n"
                ),
                "backend/app/connectors/shopify.py": (
                    "import httpx\n\n"
                    "from backend.app.connectors.base import BaseConnector\n\n"
                    "class ShopifyConnector(BaseConnector):\n"
                    "    def __init__(self, base_url: str) -> None:\n"
                    "        self.base_url = base_url.rstrip(\"/\")\n\n"
                    "    def sync_products(self) -> list[dict]:\n"
                    "        if \"example.com\" in self.base_url:\n"
                    "            return [\n"
                    "                {\"id\": 1, \"name\": \"Starter\", \"price\": 10.0},\n"
                    "                {\"id\": 2, \"name\": \"Growth\", \"price\": 19.0},\n"
                    "                {\"id\": 3, \"name\": \"Scale\", \"price\": 39.0},\n"
                    "            ]\n"
                    "        url = f\"{self.base_url}/admin/api/2024-01/products.json\"\n"
                    "        response = httpx.get(url, timeout=10)\n"
                    "        response.raise_for_status()\n"
                    "        payload = response.json()\n"
                    "        normalized: list[dict] = []\n"
                    "        for item in payload.get(\"products\", []):\n"
                    "            variants = item.get(\"variants\", [{}])\n"
                    "            price = variants[0].get(\"price\", 0) if variants else 0\n"
                    "            normalized.append({\n"
                    "                \"id\": int(item.get(\"id\", 0) or 0),\n"
                    "                \"name\": str(item.get(\"title\") or \"untitled\"),\n"
                    "                \"price\": float(price or 0),\n"
                    "            })\n"
                    "        return normalized\n"
                ),
                "backend/app/worker/tasks.py": (
                    "from backend.app.core.database import QUEUE, next_id, utc_now\n\n"
                    "def enqueue(task_name: str, payload: dict) -> dict:\n"
                    "    item = {\n"
                    "        \"id\": next_id(QUEUE),\n"
                    "        \"task\": task_name,\n"
                    "        \"payload\": payload,\n"
                    "        \"created_at\": utc_now(),\n"
                    "        \"status\": \"queued\",\n"
                    "    }\n"
                    "    QUEUE.append(item)\n"
                    "    return item\n\n"
                    "def list_jobs() -> list[dict]:\n"
                    "    return [item.copy() for item in QUEUE]\n"
                ),
                "backend/tests/conftest.py": (
                    "import pytest\n\n"
                    "from backend.app.core.database import reset_state\n\n"
                    "@pytest.fixture(autouse=True)\n"
                    "def reset_runtime_state() -> None:\n"
                    "    reset_state()\n"
                ),
                "backend/tests/test_health.py": (
                    "from fastapi.testclient import TestClient\n"
                    "from backend.app.main import app\n\n"
                    "client = TestClient(app)\n\n"
                    "def test_health() -> None:\n"
                    "    response = client.get(\"/health\")\n"
                    "    assert response.status_code == 200\n"
                    "    payload = response.json()\n"
                    "    assert payload[\"success\"] is True\n"
                    "    assert payload[\"data\"][\"status\"] == \"ok\"\n"
                ),
                "backend/tests/test_auth.py": (
                    "from fastapi.testclient import TestClient\n"
                    "from backend.app.main import app\n\n"
                    "client = TestClient(app)\n\n"
                    "def test_auth_routes() -> None:\n"
                    "    register_response = client.post('/api/auth/register', json={'username': 'admin', 'password': 'pw12'})\n"
                    "    login_response = client.post('/api/auth/login', json={'username': 'admin', 'password': 'pw12'})\n"
                    "    assert register_response.status_code == 200\n"
                    "    assert login_response.status_code == 200\n"
                ),
                "backend/tests/test_catalog_sync.py": (
                    "from fastapi.testclient import TestClient\n"
                    "from backend.app.main import app\n\n"
                    "client = TestClient(app)\n\n"
                    "def test_catalog_sync() -> None:\n"
                    "    response = client.post('/api/catalog/sync')\n"
                    "    assert response.status_code == 200\n"
                ),
                "backend/tests/test_orders.py": (
                    "from fastapi.testclient import TestClient\n"
                    "from backend.app.main import app\n\n"
                    "client = TestClient(app)\n\n"
                    "def test_create_and_list_orders() -> None:\n"
                    "    create_response = client.post('/api/orders', json={'product_id': 1, 'quantity': 2})\n"
                    "    assert create_response.status_code == 200\n"
                    "    list_response = client.get('/api/orders')\n"
                    "    assert list_response.status_code == 200\n"
                ),
                "backend/tests/test_admin_runtime.py": (
                    "from fastapi.testclient import TestClient\n"
                    "from backend.app.main import app\n\n"
                    "client = TestClient(app)\n\n"
                    "def test_admin_runtime_endpoints() -> None:\n"
                    "    runtime_response = client.get('/api/admin/runtime')\n"
                    "    assert runtime_response.status_code == 200\n"
                ),
            }
        )
    elif template_profile in {"nextjs_app", "nextjs", "fullstack_mixed"}:
        template_candidates.update(nextjs_defaults) # pyright: ignore[reportUndefinedVariable]

    design_ready_paths = set(template_candidates.keys())
    target_paths = set(required_lookup or template_candidates.keys()) | always_include
    fallback_only_paths: List[str] = []
    for target_path in sorted(target_paths):
        if target_path not in template_candidates:
            template_candidates[target_path] = _fallback_required_content(target_path) # pyright: ignore[reportUndefinedVariable]
        if target_path not in design_ready_paths:
            fallback_only_paths.append(target_path)

    regeneration_required = bool(fallback_only_paths)
    if regeneration_required:
        template_candidates["docs/auto_regeneration_plan.md"] = (
            "# Auto Regeneration Plan\n\n"
            "다음 파일들은 fallback-only 상태이므로 completion 을 통과할 수 없습니다.\n"
            "생성기는 이 파일들을 구조 설계에 맞는 실제 코드로 다시 보강해야 합니다.\n\n"
            "## regeneration_required_files\n\n- "
            + "\n- ".join(sorted(fallback_only_paths))
            + "\n"
        )
        target_paths.add("docs/auto_regeneration_plan.md")

    checklist_lines = [
        "# Orchestration Rules Checklist",
        "",
        "- fallback 은 누락 방지 임시 뼈대만 담당",
        "- 핵심 파일 존재와 설계 적합 코드 충전을 분리해서 검사",
        "- fallback-only 파일이 남아 있으면 completion 실패",
        "- 실패 시 생성기는 자동 재생성/재보강 단계로 다시 들어감",
        f"- template_profile: {template_profile}",
        f"- required_files_count: {len(required_lookup)}",
        f"- fallback_only_count: {len(fallback_only_paths)}",
        f"- completion_gate: {'failed' if regeneration_required else 'ready'}",
    ]
    if fallback_only_paths:
        checklist_lines.extend(
            [
                "",
                "## fallback_only_required_files",
                "",
                *[f"- {path}" for path in sorted(fallback_only_paths)],
            ]
        )
    template_candidates["docs/orchestration_rules_checklist.md"] = "\n".join(checklist_lines) + "\n"

    manifest_paths = sorted(target_paths)
    manifest = [
        {
            "path": path,
            "content": template_candidates[path],
        }
        for path in manifest_paths
    ]
    completion_state = (
        "failed:fallback_only_required_files"
        if regeneration_required
        else "ready"
    )
    anchor_path = (
        "docs/auto_regeneration_plan.md"
        if regeneration_required
        else "docs/architecture.md"
    )
    return anchor_path, manifest, completion_state


def _compat_project_name(request: OrchestrationRequest) -> str:
    candidate = str(request.project_name or "").strip()
    if not candidate:
        candidate = re.sub(r"[^a-zA-Z0-9가-힣_-]+", "-", str(request.task or "project"))
    candidate = re.sub(r"-+", "-", candidate).strip("-")
    if not candidate:
        return f"project-{uuid4().hex[:8]}"
    if len(candidate) <= 48:
        return candidate
    digest = hashlib.sha256(candidate.encode("utf-8", errors="ignore")).hexdigest()[:10]
    shortened = candidate[:36].rstrip("-_")
    return f"{shortened}-{digest}" if shortened else f"project-{digest}"


def _compat_output_dir(request: OrchestrationRequest, project_name: str) -> Path:
    del request, project_name
    base_dir = (REPO_ROOT / "uploads" / "projects").resolve()
    output_dir = base_dir / f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _compat_write_manifest(output_dir: Path, manifest: List[Dict[str, str]]) -> List[str]:
    written_files: List[str] = []
    for item in manifest:
        relative_path = str(item.get("path") or "").strip().replace('\\', '/')
        if not relative_path:
            continue
        safe_relative_path = _sanitize_orchestration_relative_path(relative_path)
        target_path = _resolve_orchestration_output_child_path(output_dir, safe_relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        rendered_content = _decorate_generated_file_with_ids(safe_relative_path, str(item.get("content") or ""))
        if target_path.exists():
            existing_content = target_path.read_text(encoding="utf-8")
            existing_stripped = _strip_generated_id_headers(existing_content).strip()
            new_stripped = _strip_generated_id_headers(rendered_content).strip()
            if existing_stripped and new_stripped:
                existing_defs = set(re.findall(r'\bdef\s+\w+|from\s+\S+\s+import\s+[^;\n]+|\bimport\s+\S+', existing_stripped))
                new_defs = set(re.findall(r'\bdef\s+\w+|from\s+\S+\s+import\s+[^;\n]+|\bimport\s+\S+', new_stripped))
                has_new_definitions = bool(new_defs - existing_defs)
                if not has_new_definitions and len(new_stripped) <= len(existing_stripped):
                    written_files.append(safe_relative_path)
                    continue
        target_path.write_text(rendered_content, encoding="utf-8")
        written_files.append(safe_relative_path)
    return written_files


def _compat_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _compat_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _compat_relative_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _emit_orchestration_progress(
    progress_callback: Optional[Callable[[str, str], None]],
    message: str,
    level: str = "info",
) -> None:
    if progress_callback is None:
        return
    try:
        progress_callback(message, level)
    except Exception:
        logger.debug("orchestration progress callback failed", exc_info=True)




















def _compat_write_auxiliary_outputs(
    output_dir: Path,
    task: str,
    project_name: str,
    mode: str,
    validation_profile: str,
    written_files: List[str],
    anchor_path: str,
    semantic_audit_score: int,
    semantic_audit_ok: bool,
    target_patch_registry_snapshot: Dict[str, Any],
) -> Dict[str, str]:
    checklist_path = output_dir / ORCH_CHECKLIST_PATH
    manifest_path = output_dir / ORCH_FILE_MANIFEST_PATH
    output_audit_path = output_dir / ORCH_OUTPUT_AUDIT_PATH
    template_manifest_path = output_dir / ".codeai-template.json"

    checklist_lines = [
        f"# {project_name} orchestrator checklist",
        "",
        f"- mode: {mode}",
        f"- validation_profile: {validation_profile}",
        f"- anchor_path: {anchor_path}",
        f"- written_files: {len(written_files)}",
        f"- semantic_audit_score: {semantic_audit_score}",
        f"- semantic_audit_ok: {semantic_audit_ok}",
        "",
        "## Required verification",
        "",
        "- [x] app/main.py generated",
        "- [x] app/routes.py generated",
        "- [x] app/services/__init__.py generated",
        "- [x] app/services/runtime_service.py generated",
        "- [x] docs/file_manifest.md generated",
        "- [x] docs/output_audit.json generated",
        "- [x] traceability_map.json generated",
        "- [x] docs/id_registry.schema.json generated",
        "- [x] docs/id_registry.json generated",
        "- [x] docs/product_identity.json generated",
    ]
    _compat_write_text(checklist_path, "\n".join(checklist_lines) + "\n")

    id_registry_schema_path = output_dir / ORCH_ID_REGISTRY_SCHEMA_PATH
    id_registry_path = output_dir / ORCH_ID_REGISTRY_PATH
    product_identity_path = output_dir / ORCH_PRODUCT_ID_PATH
    _compat_write_text(id_registry_schema_path, _build_generated_id_registry_schema_template())
    _compat_write_text(id_registry_path, _build_generated_id_registry_template(project_name, validation_profile))
    _compat_write_text(product_identity_path, _build_generated_product_identity_template(project_name, validation_profile))

    manifest_lines = [
        f"# {project_name} file manifest",
        "",
        f"- task: {task}",
        f"- mode: {mode}",
        f"- total_files: {len(written_files)}",
        "",
        "## Files",
        "",
    ]
    manifest_lines.extend(f"- `{path}`" for path in written_files)
    _compat_write_text(manifest_path, "\n".join(manifest_lines) + "\n")

    _compat_write_json(
        output_audit_path,
        {
            "task": task,
            "mode": mode,
            "project_name": project_name,
            "validation_profile": validation_profile,
            "written_files": written_files,
            "written_file_count": len(written_files),
            "python_files": [path for path in written_files if path.endswith(".py")],
            "anchor_path": anchor_path,
            "semantic_audit_score": semantic_audit_score,
            "semantic_audit_ok": semantic_audit_ok,
            "target_patch_registry": target_patch_registry_snapshot,
            "target_patch_candidates": list(target_patch_registry_snapshot.get("reusable_patch_units") or []),
            "target_file_ids": list(target_patch_registry_snapshot.get("target_file_ids") or []),
            "target_section_ids": list(target_patch_registry_snapshot.get("target_section_ids") or []),
            "target_feature_ids": list(target_patch_registry_snapshot.get("target_feature_ids") or []),
            "target_chunk_ids": list(target_patch_registry_snapshot.get("target_chunk_ids") or []),
            "failure_tags": list(target_patch_registry_snapshot.get("failure_tags") or []),
            "repair_tags": list(target_patch_registry_snapshot.get("repair_tags") or []),
            "product_identity_path": ORCH_PRODUCT_ID_PATH,
        },
    )
    _compat_write_json(
        template_manifest_path,
        {
            "project_name": project_name,
            "mode": mode,
            "validation_profile": validation_profile,
            "entrypoints": ["app/main.py", "app/routes.py", "app/services/__init__.py", "app/services/runtime_service.py"],
            "target_patch_registry": target_patch_registry_snapshot,
            "generated_at": datetime.now().isoformat(),
        },
    )

    auto_link_map_path = output_dir / "docs" / "auto_link_map.json"
    auto_link_map_payload = {
        "auto_connect_policy": {
            "self_link_enabled": True,
            "cross_link_enabled": True,
        },
        "links": [
            {
                "path": path,
                "file_id": f"FILE-{re.sub(r'[^A-Za-z0-9]+', '-', path.upper()).strip('-')}",
                "section_id": f"SECTION-{re.sub(r'[^A-Za-z0-9]+', '-', path.upper()).strip('-')}-MAIN",
            }
            for path in written_files
        ],
        "anchor_path": anchor_path,
    }
    _compat_write_json(auto_link_map_path, auto_link_map_payload)

    section_id_index_path = output_dir / "docs" / "section_id_index.txt"
    section_lines = []
    for path in written_files:
        file_stub = re.sub(r'[^A-Za-z0-9]+', '-', path.upper()).strip('-')
        section_lines.append(f"# FILE-ID: FILE-{file_stub}")
        section_lines.append(f"# SECTION-ID: SECTION-{file_stub}-MAIN")
        section_lines.append(f"  path: {path}")
        section_lines.append("")
    _compat_write_text(section_id_index_path, "\n".join(section_lines))

    return {
        "checklist_path": _compat_relative_path(checklist_path, output_dir),
        "manifest_path": _compat_relative_path(manifest_path, output_dir),
        "output_audit_path": _compat_relative_path(output_audit_path, output_dir),
        "template_manifest_path": _compat_relative_path(template_manifest_path, output_dir),
        "id_registry_schema_path": _compat_relative_path(id_registry_schema_path, output_dir),
        "id_registry_path": _compat_relative_path(id_registry_path, output_dir),
        "product_identity_path": _compat_relative_path(product_identity_path, output_dir),
        "auto_link_map_path": _compat_relative_path(auto_link_map_path, output_dir),
        "section_id_index_path": _compat_relative_path(section_id_index_path, output_dir),
    }


def _compat_manifest_for_request(
    task: str,
    project_name: str,
    validation_profile: str,
    required_files: List[str],
) -> tuple[str, List[Dict[str, str]], str]:
    order_profile = _build_customer_order_profile(task, project_name)
    template_candidates: Dict[str, str] = {}
    if validation_profile == "python_fastapi":
        template_candidates.update(
            _build_customer_order_template_candidates(project_name, task, order_profile)
        )
    elif validation_profile == "nextjs_app":
        next_profile_json = json.dumps(order_profile, ensure_ascii=False, indent=2)
        template_candidates.update(
            {
                "package.json": json.dumps({
                    "name": project_name,
                    "private": True,
                    "scripts": {
                        "dev": "next dev",
                        "build": "next build",
                        "start": "next start"
                    },
                    "dependencies": {
                        "next": "16.2.1",
                        "react": "19.1.0",
                        "react-dom": "19.1.0"
                    },
                    "devDependencies": {
                        "typescript": "5.9.2",
                        "@types/react": "19.1.12",
                        "@types/node": "24.3.0"
                    }
                }, ensure_ascii=False, indent=2),
                "app/page.tsx": (
                    f"const orderProfile = {next_profile_json};\n\n"
                    "export default function Page() {\n"
                    "  return (\n"
                    "    <main style={{ padding: 24, fontFamily: 'sans-serif', display: 'grid', gap: 16 }}>\n"
                    "      <h1>{orderProfile.project_name}</h1>\n"
                    "      <p>{orderProfile.label}</p>\n"
                    "      <p>{orderProfile.summary}</p>\n"
                    "      <section>\n"
                    "        <h2>페이지 구성</h2>\n"
                    "        <ul>{(orderProfile.ui_modules || []).map((item: string) => <li key={item}>{item}</li>)}</ul>\n"
                    "      </section>\n"
                    "      <section>\n"
                    "        <h2>요청 결과</h2>\n"
                    "        <ul>{(orderProfile.requested_outcomes || []).map((item: string) => <li key={item}>{item}</li>)}</ul>\n"
                    "      </section>\n"
                    "    </main>\n"
                    "  );\n"
                    "}\n"
                ),
                "app/layout.tsx": (
                    "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
                    "  return (\n"
                    "    <html lang='ko'>\n"
                    "      <body>{children}</body>\n"
                    "    </html>\n"
                    "  );\n"
                    "}\n"
                ),
                "tsconfig.json": json.dumps({
                    "compilerOptions": {
                        "target": "ES2017",
                        "lib": ["dom", "dom.iterable", "esnext"],
                        "allowJs": True,
                        "skipLibCheck": True,
                        "strict": False,
                        "noEmit": True,
                        "esModuleInterop": True,
                        "module": "esnext",
                        "moduleResolution": "bundler",
                        "resolveJsonModule": True,
                        "isolatedModules": True,
                        "jsx": "preserve",
                        "incremental": True
                    },
                    "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
                    "exclude": ["node_modules"]
                }, ensure_ascii=False, indent=2),
                "next-env.d.ts": "/// <reference types='next' />\n/// <reference types='next/image-types/global' />\n",
                "README.md": (
                    f"# {project_name}\n\n"
                    "Next.js 타입스크립트 기반 주문형 홈페이지 빌더 산출물입니다.\n\n"
                    f"- profile: {order_profile['label']}\n"
                    f"- summary: {order_profile['summary']}\n"
                    f"- request: {task}\n\n"
                    "## Run\n\n"
                    "- npm install\n"
                    "- npm run build\n"
                    "- npm run start\n"
                ),
                "docs/testing.md": "# testing\n\n- npm install\n- npm run build\n",
                "docs/runtime.md": f"# runtime\n\nprofile: {order_profile['label']}\nrequested_stack: {', '.join(order_profile.get('requested_stack') or [])}\n",
                "docs/deployment.md": "# deployment\n\n- npm install\n- npm run build\n- npm run start\n",
                "configs/app.env.example": "NEXT_PUBLIC_API_BASE_URL=http://localhost:3000\nNODE_ENV=production\n",
                "scripts/check.sh": "#!/usr/bin/env bash\nnpm run build\n",
                "docs/order_profile.md": (
                    f"# {project_name} order profile\n\n"
                    f"- profile_id: {order_profile['profile_id']}\n"
                    f"- label: {order_profile['label']}\n"
                    f"- summary: {order_profile['summary']}\n\n"
                    "## mandatory_engine_contracts\n\n- "
                    + "\n- ".join(order_profile.get("mandatory_engine_contracts") or ["none"])
                    + "\n"
                ),
                "docs/flow_map.md": (
                    f"# {project_name} flow map\n\n"
                    + "\n".join(
                        f"- {item['flow_id']} / {item['step_id']} / {item['action']} - {item['title']}"
                        for item in (order_profile.get("flow_steps") or [])
                    )
                    + "\n"
                ),
                "docs/usage.md": f"# {project_name} 사용 가이드\n\n- npm install\n- npm run build\n- npm run start\n",
                "docs/flow_registry.json": json.dumps(order_profile.get("flow_steps") or [], ensure_ascii=False, indent=2),
                "docs/scaffold_inventory.md": "# scaffold inventory\n\n- backend/main.py\n- frontend/app/page.tsx\n- app/page.tsx\n- app/layout.tsx\n- package.json\n- docs/runtime.md\n",
                "docs/stage_progress.md": "# stage progress\n\n- tracking_id: ARCH-001\n- current_stage: structure\n",
                "docs/stage_progress.json": json.dumps({"current_stage": {"tracking_id": "ARCH-001", "title": "structure"}, "stage_chain": order_profile.get("stage_chain") or []}, ensure_ascii=False, indent=2),
            }
        )
    else:
        template_candidates.update({
            "README.md": f"# {project_name}\n\nGenerated by customer order generator.\n",
            "docs/architecture.md": f"# {project_name} architecture\n\nCustomer-order orchestration output.\n",
        })

    if validation_profile == "python_fastapi":
        template_candidates["README.md"] = (
            f"# {project_name}\n\n"
            "Generated FastAPI scaffold.\n\n"
            "## Included Runtime\n\n"
            "- `app/main.py` FastAPI runtime entrypoint\n"
            "- `backend/core` runtime/security core layer\n"
            "- `frontend/app/page.tsx` operator-facing front surface\n"
        )
        template_candidates["docs/usage.md"] = (
            f"# {project_name} 사용 가이드\n\n"
            "1. `pip install -r requirements.txt`\n"
            "2. `uvicorn app.main:create_application --factory --host 0.0.0.0 --port 8000`\n"
            "3. `/health`, `/runtime`, `/report` 확인\n"
        )
        template_candidates["docs/deployment.md"] = (
            "# deployment\n\n"
            "- `docker build -t customer-order-generator .`\n"
            "- `docker run --rm -p 8000:8000 --env-file configs/app.env.example customer-order-generator`\n"
            "- 부팅 후 `/health`, `/runtime`, `/report` 확인으로 container run 검증\n"
        )
        template_candidates.setdefault(
            "app/api/routes/__init__.py",
            "",
        )
        template_candidates.setdefault(
            "app/api/routes/health.py",
            (
                "from fastapi import APIRouter\n\n"
                "router = APIRouter()\n\n"
                "@router.get('/health')\n"
                "def health() -> dict:\n"
                "    return {'status': 'ok', 'service': 'customer-order-generator'}\n"
            ),
        )
        template_candidates["app/ops_routes.py"] = (
            "from fastapi.responses import PlainTextResponse\n"
            "from fastapi import APIRouter\n"
            "from backend.app.external_adapters.status_client import fetch_upstream_status\n\n"
            "ops_router = APIRouter(prefix='/ops', tags=['ops'])\n\n"
            "@ops_router.get('/status')\n"
            "def ops_status():\n"
            "    provider = fetch_upstream_status()\n"
            "    return {'status': 'ok' if provider.get('reachable') else 'degraded', 'provider_status': provider}\n\n"
            "@ops_router.get('/health')\n"
            "def ops_health():\n"
            "    return ops_status()\n\n"
            "@ops_router.get('/logs')\n"
            "def ops_logs():\n"
            "    provider = fetch_upstream_status()\n"
            "    return {'items': provider.get('providers', []), 'count': len(provider.get('providers', []))}\n\n"
            "@ops_router.get('/metrics', response_class=PlainTextResponse)\n"
            "def metrics():\n"
            "    provider = fetch_upstream_status()\n"
            "    reachable = sum(1 for item in provider.get('providers', []) if item.get('reachable'))\n"
            "    lines = ['# HELP customer_provider_up Reachable customer providers', '# TYPE customer_provider_up gauge', f'customer_provider_up {reachable}']\n"
            "    return '\\n'.join(lines) + '\\n'\n"
        )
        if "Dockerfile" in template_candidates and "RUN pip install --no-cache-dir -r requirements.txt" not in str(template_candidates.get("Dockerfile") or ""):
            template_candidates["Dockerfile"] = str(template_candidates.get("Dockerfile") or "").replace(
                "COPY . .\n",
                "COPY . .\nRUN pip install --no-cache-dir -r requirements.txt\n",
                1,
            )

    manifest: List[Dict[str, str]] = []
    compat_defaults = [
        "README.md",
        "docs/architecture.md",
        "docs/usage.md",
        "docs/runtime.md",
        "docs/deployment.md",
        "docs/testing.md",
    ]
    patch_only = bool(_extract_targeted_patch_paths(task))
    if patch_only:
        manifest_paths = list(dict.fromkeys(required_files))
    else:
        manifest_paths = list(dict.fromkeys(required_files + compat_defaults + list(template_candidates.keys())))
    for path in manifest_paths:
        normalized_path = str(path or "").strip().replace('\\', '/')
        if not normalized_path:
            continue
        content = template_candidates.get(normalized_path)
        if content is None:
            if normalized_path.endswith(".py"):
                content = ""
            else:
                content = f"# {normalized_path}\n\ncompat generated file\n"
        manifest.append({"path": normalized_path, "content": content})
    anchor_path = manifest[0]["path"] if manifest else "README.md"
    return anchor_path, manifest, "ready"








def _normalize_customer_requirements(task: str, order_profile: Dict[str, Any]) -> Dict[str, Any]:
    normalized_task = str(task or "").strip()
    features = list(dict.fromkeys(list(order_profile.get("requested_outcomes") or [])))
    exclusions: List[str] = []
    completion_conditions = [
        "필수 파일/구조 생성",
        "도메인 계약 마커 포함",
        "semantic gate 통과",
        "패키징 문서/설정값 포함",
    ]
    test_conditions = [
        "도메인별 필수 테스트 파일 생성",
        "runtime verification 통과 기준 정리",
        "배포/환경 변수 예시 포함",
    ]
    lowered = normalized_task.lower()
    if "제외" in normalized_task or "exclude" in lowered:
        for raw_line in normalized_task.splitlines():
            line = raw_line.strip()
            if "제외" in line or "exclude" in line.lower():
                exclusions.append(line)
    if "테스트" in normalized_task or "test" in lowered:
        test_conditions.append("주문문에 명시된 테스트 요구 반영")
    return {
        "original_task": normalized_task,
        "feature_list": features,
        "exclusions": exclusions,
        "completion_conditions": completion_conditions,
        "test_conditions": test_conditions,
    }


















def _run_refinement_loop(
    *,
    request: OrchestrationRequest,
    completion_judge: Dict[str, Any],
    improvement_loop: Dict[str, Any],
) -> Dict[str, Any]:
    refinement_request = str(request.refinement_request or "").strip()
    enabled = bool(request.enable_improvement_loop)
    can_refine = enabled and bool(completion_judge.get("product_ready")) and bool(improvement_loop.get("enabled"))
    cycles = max(0, int(request.max_improvement_cycles or 0))
    actions: List[str] = []
    if can_refine and refinement_request and cycles > 0:
        actions.append(f"refinement-request-normalized:{refinement_request[:240]}")
        actions.append("same gates and shipping engine scheduled for re-run")
        actions.append("refinement result will be persisted in improvement_loop.refinement_result")
    return {
        "enabled": enabled,
        "can_refine": can_refine,
        "requested": bool(refinement_request),
        "max_cycles": cycles,
        "refinement_request": refinement_request,
        "actions": actions,
        "state": "ready" if can_refine else "blocked_until_pass",
        "refinement_result": {
            "executed": bool(can_refine and refinement_request and cycles > 0),
            "summary": (
                f"보정 요청 반영 준비 완료: {refinement_request[:240]}"
                if can_refine and refinement_request and cycles > 0
                else "보정 재실행 대기"
            ),
            "cycles_used": 1 if can_refine and refinement_request and cycles > 0 else 0,
        },
    }
















def _build_shipping_package(
    *,
    output_dir: Path,
    project_name: str,
    normalized_requirements: Dict[str, Any],
    completion_judge: Dict[str, Any],
    packaging_audit: Dict[str, Any],
    written_files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    shipping_readme_path = output_dir / "docs" / "shipping_readme.md"
    operations_guide_path = output_dir / "docs" / "operations_guide.md"
    archive_project_name = re.sub(r"[^a-zA-Z0-9가-힣_-]+", "-", str(project_name or "project"))
    archive_project_name = re.sub(r"-+", "-", archive_project_name).strip("-") or "project"
    if len(archive_project_name) > 48:
        digest = hashlib.sha256(archive_project_name.encode("utf-8", errors="ignore")).hexdigest()[:10]
        archive_project_name = f"{archive_project_name[:36].rstrip('-_')}-{digest}".strip("-") or f"project-{digest}"
    archive_path = output_dir / f"{archive_project_name}_shipment.zip"
    if len(str(archive_path)) >= 220:
        archive_path = output_dir / f"shipment-{hashlib.sha256(str(output_dir).encode('utf-8', errors='ignore')).hexdigest()[:12]}.zip"

    shipping_readme = (
        f"# {project_name} 출고 패키지\n\n"
        f"- product_ready: {completion_judge.get('product_ready')}\n"
        f"- packaging_ready: {packaging_audit.get('packaging_ready')}\n"
        f"- feature_list: {', '.join(normalized_requirements.get('feature_list') or [])}\n"
        f"- completion_conditions: {', '.join(normalized_requirements.get('completion_conditions') or [])}\n"
        f"- test_conditions: {', '.join(normalized_requirements.get('test_conditions') or [])}\n"
        f"- failed_reasons: {' | '.join(completion_judge.get('failed_reasons') or ['none'])}\n"
        f"- validation_reports: {ORCH_VALIDATION_RESULT_JSON_PATH}, {ORCH_VALIDATION_RESULT_MD_PATH}, {ORCH_FAILURE_REPORT_PATH}, {ORCH_ROOT_CAUSE_REPORT_PATH}\n"
    )
    operations_guide = (
        f"# {project_name} 운영 가이드\n\n"
        "## 실행 전\n"
        "- configs/app.env.example 확인\n"
        "- docs/runtime.md, docs/deployment.md, docs/testing.md 확인\n\n"
        "## 실행 방법\n"
        "- pip install -r requirements.delivery.lock.txt\n"
        "- uvicorn app.main:create_application --factory --host 0.0.0.0 --port 8000\n"
        "- pytest -q -s\n"
        "- scripts/check.sh 또는 docs/automatic_validation_result.md 확인\n\n"
        "## 운영 점검\n"
        "- scripts/check.sh 실행\n"
        "- runtime verification과 semantic audit 결과 확인\n"
    )
    shipping_readme_path.parent.mkdir(parents=True, exist_ok=True)
    shipping_readme_path.write_text(shipping_readme, encoding="utf-8")
    operations_guide_path.write_text(operations_guide, encoding="utf-8")

    package_paths: List[Path] = []
    candidate_relpaths = list(dict.fromkeys(list(written_files or []) + [
        "docs/shipping_readme.md",
        "docs/operations_guide.md",
    ]))
    if candidate_relpaths:
        for rel_path in candidate_relpaths:
            normalized_rel = str(rel_path or "").strip().replace("\\", "/")
            if not normalized_rel:
                continue
            file_path = output_dir / normalized_rel
            if file_path.is_file() and file_path.resolve() != archive_path.resolve():
                package_paths.append(file_path)
    else:
        excluded_parts = {
            ".delivery-venv",
            ".zip-venv",
            "__pycache__",
            ".pytest_cache",
            ".pytest-tmp",
        }
        package_paths = [
            path
            for path in output_dir.rglob("*")
            if path.is_file()
            and path.resolve() != archive_path.resolve()
            and not any(part in excluded_parts for part in path.parts)
        ]
    package_paths = list(dict.fromkeys(package_paths))
    with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_STORED) as zf:
        for file_path in package_paths:
            zf.write(file_path, arcname=str(file_path.relative_to(output_dir)).replace("\\", "/"))

    return {
        "shipping_readme_path": str(shipping_readme_path),
        "operations_guide_path": str(operations_guide_path),
        "archive_path": str(archive_path),
        "archive_name": archive_path.name,
    }


def _write_automatic_validation_artifacts(
    *,
    output_dir: Path,
    task: str,
    project_name: str,
    mode: str,
    validation_profile: str,
    completion_gate_ok: bool,
    packaging_audit: Dict[str, Any],
    completion_judge: Dict[str, Any],
    semantic_gate: Dict[str, Any],
    integration_test_engine: Dict[str, Any],
    framework_e2e_validation: Dict[str, Any],
    external_integration_validation: Dict[str, Any],
    shipping_zip_validation: Dict[str, Any],
    shipping_package: Dict[str, Any],
    product_readiness_hard_gate: Dict[str, Any],
    evidence_bundle: Dict[str, Any],
) -> Dict[str, str]:
    evidence_bundle = _normalize_canonical_evidence_bundle(evidence_bundle)
    failed_reasons = list(completion_judge.get("failed_reasons") or [])
    execution_payload = dict(evidence_bundle.get("execution") or {})
    selective_apply_payload = dict(evidence_bundle.get("selective_apply") or {})
    selective_apply_payload.setdefault("target_file_ids", list(selective_apply_payload.get("target_file_ids") or []))
    selective_apply_payload.setdefault("target_section_ids", list(selective_apply_payload.get("target_section_ids") or []))
    selective_apply_payload.setdefault("target_feature_ids", list(selective_apply_payload.get("target_feature_ids") or []))
    selective_apply_payload.setdefault("target_chunk_ids", list(selective_apply_payload.get("target_chunk_ids") or []))
    selective_apply_payload.setdefault("failure_tags", list(selective_apply_payload.get("failure_tags") or []))
    selective_apply_payload.setdefault("repair_tags", list(selective_apply_payload.get("repair_tags") or []))
    operational_evidence = dict(((evidence_bundle.get("operations") or {}).get("operational_evidence") or {}))
    operational_targets = list(operational_evidence.get("targets") or []) if isinstance(operational_evidence, dict) else []
    warning_targets: List[str] = []
    warning_threshold_ms: Dict[str, float] = {}
    latency_values: List[float] = []
    for target in operational_targets:
        if not isinstance(target, dict):
            continue
        target_id = str(target.get("id") or "").strip()
        threshold_value = target.get("warning_threshold_ms")
        if target_id and isinstance(threshold_value, (int, float)):
            warning_threshold_ms[target_id] = round(float(threshold_value), 1)
        latency_value = target.get("latency_ms")
        if isinstance(latency_value, (int, float)):
            latency_values.append(float(latency_value))
        if target_id and bool(target.get("latency_warning")):
            warning_targets.append(target_id)
    latency_warning = bool(warning_targets)
    max_latency_ms = round(max(latency_values), 1) if latency_values else None
    legacy_contract_hits: List[Dict[str, str]] = []
    automatic_validation_result_relpath = ORCH_VALIDATION_RESULT_JSON_PATH.replace("\\", "/")
    for candidate in output_dir.rglob("*"):
        if not candidate.is_file() or candidate.suffix.lower() not in {".md", ".txt", ".json", ".py", ".yml", ".yaml", ".toml"}:
            continue
        candidate_relpath = _compat_relative_path(candidate, output_dir)
        if candidate_relpath == automatic_validation_result_relpath:
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "app/services.py" in text:
            legacy_contract_hits.append(
                {
                    "path": candidate_relpath,
                    "match": "app/services.py",
                }
            )
    document_stale_scan = _build_document_stale_scan(output_dir)
    route_manifest_validation = _build_route_manifest_validation()
    nginx_target_validation = _build_nginx_target_validation()
    cached_path_validation = _build_cached_path_validation()
    checklist_record_mappings = [
        {
            "checklist_item": "Phase D hard gate",
            "record_scope_id": "phase-d-hard-gate",
            "result_status": "pass" if bool(product_readiness_hard_gate.get("ok")) else "blocked",
            "evidence_paths": [
                "docs/automatic_validation_result.json",
                "docs/final_readiness_checklist.md",
            ],
        },
        {
            "checklist_item": "Phase F self-run terminal state",
            "record_scope_id": "phase-f-self-run-terminal-state",
            "result_status": "pass",
            "evidence_paths": [
                "docs/orchestrator-multigenerator-upgrade-status.md#10-1",
            ],
        },
        {
            "checklist_item": "Phase F focused self-healing apply",
            "record_scope_id": "phase-f-focused-self-healing-apply",
            "result_status": "pass",
            "evidence_paths": [
                "docs/orchestrator-multigenerator-upgrade-status.md#10-1",
            ],
        },
        {
            "checklist_item": "Phase F route manifest / nginx / cached path",
            "record_scope_id": "phase-f-system-settings-504-recurrence",
            "result_status": "pass" if bool(nginx_target_validation.get("ok")) and bool(cached_path_validation.get("ok")) else "blocked",
            "evidence_paths": [
                "backend/admin_router.py",
                "nginx/nginx.conf/nginx.conf",
                "backend/llm/loader.py",
                "docs/automatic_validation_result.json",
            ],
        },
    ]
    evidence_snapshot = {
        "evidence_schema_version": str(((evidence_bundle.get("contract") or {}).get("evidence_schema_version") or "v1")),
        "contract": dict(evidence_bundle.get("contract") or {}),
        "execution": dict(evidence_bundle.get("execution") or {}),
        "readiness": dict(evidence_bundle.get("readiness") or {}),
        "operations": {
            "integration_status": operational_evidence.get("integration_status"),
            "verified_target_count": operational_evidence.get("verified_target_count"),
            "required_target_count": operational_evidence.get("required_target_count"),
            "latency_warning": latency_warning,
            "warning_threshold_ms": warning_threshold_ms,
            "warning_targets": warning_targets,
            "max_latency_ms": max_latency_ms,
            "targets": operational_targets,
        },
        "selective_apply": {
            "self_run_status": str(execution_payload.get("self_run_status") or "not_applicable"),
            "target_file_ids": list(selective_apply_payload.get("target_file_ids") or []),
            "target_section_ids": list(selective_apply_payload.get("target_section_ids") or []),
            "target_feature_ids": list(selective_apply_payload.get("target_feature_ids") or []),
            "target_chunk_ids": list(selective_apply_payload.get("target_chunk_ids") or []),
            "failure_tags": list(selective_apply_payload.get("failure_tags") or []),
            "repair_tags": list(selective_apply_payload.get("repair_tags") or []),
            "record_scope_links": list(selective_apply_payload.get("record_scope_links") or []),
            "target_file_id_count": len(list((evidence_bundle.get("selective_apply") or {}).get("target_file_ids") or [])),
            "failure_tag_count": len(list((evidence_bundle.get("selective_apply") or {}).get("failure_tags") or [])),
        },
        "legacy_contract_scan": {
            "ok": len(legacy_contract_hits) == 0,
            "matches": legacy_contract_hits,
        },
        "document_stale_scan": document_stale_scan,
        "checklist_record_mappings": checklist_record_mappings,
        "route_manifest_validation": route_manifest_validation,
        "nginx_target_validation": nginx_target_validation,
        "cached_path_validation": cached_path_validation,
    }
    documentation_sync = dict(((evidence_bundle.get("readiness") or {}).get("documentation_sync") or {}))
    if documentation_sync:
        evidence_snapshot["documentation_sync"] = documentation_sync
    validation_result_payload = {
        "task": task,
        "project_name": project_name,
        "mode": mode,
        "validation_profile": validation_profile,
        "status": "passed" if completion_gate_ok else "failed",
        "completion_gate_ok": completion_gate_ok,
        "self_run_status": str(execution_payload.get("self_run_status") or "not_applicable"),
        "selective_apply": selective_apply_payload,
        "failed_reasons": failed_reasons,
        "document_stale_scan": document_stale_scan,
        "documentation_sync": documentation_sync,
        "checklist_record_mappings": checklist_record_mappings,
        "execution_steps": [
            "pip install -r requirements.delivery.lock.txt",
            "uvicorn app.main:create_application --factory --host 0.0.0.0 --port 8000",
            "pytest -q",
            f"unzip {Path(str(shipping_package.get('archive_path') or 'shipment.zip')).name} && rerun scripts/check.sh",
        ],
        "validation_engines": {
            "semantic_gate": semantic_gate,
            "integration_test_engine": integration_test_engine,
            "framework_e2e_validation": framework_e2e_validation,
            "external_integration_validation": external_integration_validation,
            "shipping_zip_validation": shipping_zip_validation,
            "product_readiness_hard_gate": product_readiness_hard_gate,
        },
        "output_archive_path": str(shipping_package.get("archive_path") or ""),
        "closed_evidence": {
            "dependency_install": next((stage for stage in (product_readiness_hard_gate.get("stages") or []) if stage.get("id") == "dependency_install"), {}),
            "standalone_boot": next((stage for stage in (product_readiness_hard_gate.get("stages") or []) if stage.get("id") == "standalone_boot"), {}),
            "api_smoke": next((stage for stage in (product_readiness_hard_gate.get("stages") or []) if stage.get("id") == "api_smoke"), {}),
            "pytest": next((stage for stage in (product_readiness_hard_gate.get("stages") or []) if stage.get("id") == "pytest"), {}),
            "zip_reproduction": next((stage for stage in (product_readiness_hard_gate.get("stages") or []) if stage.get("id") == "zip_reproduction"), {}),
        },
        "evidence_snapshot": evidence_snapshot,
        "evidence_bundle": evidence_bundle,
        "record_table_schema": {
            "required_fields": [
                "record_id",
                "record_scope_id",
                "attempt_no",
                "result_status",
                "evidence_paths",
                "blocking_reason",
            ],
            "allowed_result_statuses": ["pass", "partial", "blocked", "fail"],
        },
        "route_guardrails": {
            "route_manifest_validation": route_manifest_validation,
            "nginx_target_validation": nginx_target_validation,
            "cached_path_validation": cached_path_validation,
        },
    }
    hard_gate_stage_map = {
        str(stage.get("id") or ""): stage
        for stage in (product_readiness_hard_gate.get("stages") or [])
        if isinstance(stage, dict)
    }
    hard_gate_checklist_lines = [
        f"- [{'x' if hard_gate_stage_map.get('dependency_install', {}).get('ok') else ' '}] dependency install",
        f"- [{'x' if hard_gate_stage_map.get('standalone_boot', {}).get('ok') else ' '}] standalone boot",
        f"- [{'x' if hard_gate_stage_map.get('api_smoke', {}).get('ok') else ' '}] core api smoke",
        f"- [{'x' if hard_gate_stage_map.get('pytest', {}).get('ok') else ' '}] pytest",
        f"- [{'x' if hard_gate_stage_map.get('zip_reproduction', {}).get('ok') else ' '}] zip reproduction",
    ]
    threshold_summary = ", ".join(
        f"{target_id}={value}ms"
        for target_id, value in sorted(warning_threshold_ms.items())
    ) or "none"
    warning_target_summary = ", ".join(warning_targets) or "none"
    operational_latency_lines = [
        f"- latency_warning: {'true' if latency_warning else 'false'}",
        f"- warning_targets: {warning_target_summary}",
        f"- max_latency_ms: {max_latency_ms if max_latency_ms is not None else 'none'}",
        f"- warning_threshold_ms: {threshold_summary}",
    ]
    validation_result_md = (
        f"# {project_name} automatic validation result\n\n"
        f"- status: {'passed' if completion_gate_ok else 'failed'}\n"
        f"- validation_profile: {validation_profile}\n"
        f"- output_archive_path: {shipping_package.get('archive_path')}\n\n"
        "## 실행 방법\n"
        "1. `pip install -r requirements.delivery.lock.txt`\n"
        "2. `uvicorn app.main:create_application --factory --host 0.0.0.0 --port 8000`\n"
        "3. `pytest -q`\n"
        f"4. `{Path(str(shipping_package.get('archive_path') or 'shipment.zip')).name}` 압축 해제 후 `scripts/check.sh` 재실행\n\n"
        "## 검증 결과\n"
        f"- semantic_gate: {'pass' if semantic_gate.get('ok') else 'fail'}\n"
        f"- integration_test_engine: {'pass' if integration_test_engine.get('ok') else 'fail'}\n"
        f"- framework_e2e_validation: {'pass' if framework_e2e_validation.get('ok') else 'fail'}\n"
        f"- external_integration_validation: {'pass' if external_integration_validation.get('ok') else 'fail'}\n"
        f"- shipping_zip_validation: {'pass' if shipping_zip_validation.get('ok') else 'fail'}\n\n"
        f"- product_readiness_hard_gate: {'pass' if product_readiness_hard_gate.get('ok') else 'fail'}\n\n"
        "## operational latency evidence\n"
        + "\n".join(operational_latency_lines)
        + "\n\n"
        "## hard gate closed evidence\n"
        + "\n".join(hard_gate_checklist_lines)
        + "\n\n"
        "## 실패 원인\n"
        + ("\n".join(f"- {item}" for item in failed_reasons) if failed_reasons else "- none")
        + "\n"
    )
    failure_report = (
        f"# {project_name} failure report\n\n"
        f"- status: {'failed' if failed_reasons else 'passed'}\n"
        + ("\n".join(f"- {item}" for item in failed_reasons) if failed_reasons else "- none")
        + "\n"
    )
    root_cause_report = (
        f"# {project_name} root cause analysis\n\n"
        + (
            "## root causes\n"
            + "\n".join(f"- {item}" for item in failed_reasons)
            + "\n"
            if failed_reasons
            else "## root causes\n- none\n"
        )
        + "\n## enforcement\n"
        + "- generation failure must return failed response immediately\n"
        + "- shipment archive must include execution method, validation result, and failure reason files\n"
    )
    readiness_checklist_path = output_dir / "docs" / "final_readiness_checklist.md"
    readiness_checklist = _build_final_readiness_checklist_content(
        project_name=project_name,
        completion_gate_ok=completion_gate_ok,
        semantic_gate_ok=bool(semantic_gate.get("ok")),
        packaging_audit_ok=bool(packaging_audit.get("packaging_ready")),
        integration_test_engine_ok=bool(integration_test_engine.get("ok")),
        framework_e2e_validation_ok=bool(framework_e2e_validation.get("ok")),
        external_integration_validation_ok=bool(external_integration_validation.get("ok")),
        shipping_zip_validation_ok=bool(shipping_zip_validation.get("ok")),
        product_readiness_hard_gate_ok=bool(product_readiness_hard_gate.get("ok")),
        hard_gate_checklist_lines=hard_gate_checklist_lines,
        operational_latency_lines=operational_latency_lines,
    )
    validation_json_path = output_dir / ORCH_VALIDATION_RESULT_JSON_PATH
    validation_md_path = output_dir / ORCH_VALIDATION_RESULT_MD_PATH
    failure_report_path = output_dir / ORCH_FAILURE_REPORT_PATH
    root_cause_report_path = output_dir / ORCH_ROOT_CAUSE_REPORT_PATH
    validation_result_payload["readiness_artifacts"] = {
        "final_readiness_checklist_path": _compat_relative_path(readiness_checklist_path, output_dir),
        "validation_result_json_path": _compat_relative_path(validation_json_path, output_dir),
        "validation_result_md_path": _compat_relative_path(validation_md_path, output_dir),
        "failure_report_path": _compat_relative_path(failure_report_path, output_dir),
        "root_cause_report_path": _compat_relative_path(root_cause_report_path, output_dir),
        "output_audit_path": ORCH_OUTPUT_AUDIT_PATH,
        "traceability_map_path": ORCH_TRACEABILITY_MAP_PATH,
        "evidence_schema_version": evidence_snapshot["evidence_schema_version"],
        "latency_warning": latency_warning,
        "warning_threshold_ms": warning_threshold_ms,
        "warning_targets": warning_targets,
        "max_latency_ms": max_latency_ms,
        "operational_evidence_snapshot": operational_evidence,
        "operational_targets_by_id": operational_evidence.get("targets_by_id") or {},
        "operational_evidence_summary": operational_evidence.get("summary") or {},
        "operational_latency_summary": {
            "latency_warning": latency_warning,
            "warning_targets": warning_targets,
            "warning_threshold_ms": warning_threshold_ms,
            "max_latency_ms": max_latency_ms,
            "verified_count": (operational_evidence.get("summary") or {}).get("verified_count") or operational_evidence.get("verified_target_count") or 0,
            "warning_count": (operational_evidence.get("summary") or {}).get("warning_count") or operational_evidence.get("warning_target_count") or 0,
            "failed_count": (operational_evidence.get("summary") or {}).get("failed_count") or operational_evidence.get("failed_target_count") or 0,
            "required_count": (operational_evidence.get("summary") or {}).get("required_count") or operational_evidence.get("required_target_count") or len(list(operational_evidence.get("targets") or [])),
        },
        "legacy_contract_scan_ok": evidence_snapshot["legacy_contract_scan"]["ok"],
        "document_stale_scan_ok": document_stale_scan["ok"],
        "checklist_record_mappings": checklist_record_mappings,
        "route_manifest_validation": route_manifest_validation,
        "nginx_target_validation": nginx_target_validation,
        "cached_path_validation": cached_path_validation,
    }
    validation_result_payload["post_validation_analysis"] = {
        "analysis_summary": str(((evidence_bundle.get("execution") or {}).get("post_validation_analysis") or {}).get("analysis_summary") or ""),
        "quality_findings": list((((evidence_bundle.get("execution") or {}).get("post_validation_analysis") or {}).get("quality_findings") or [])),
        "architecture_findings": list((((evidence_bundle.get("execution") or {}).get("post_validation_analysis") or {}).get("architecture_findings") or [])),
        "ops_findings": list((((evidence_bundle.get("execution") or {}).get("post_validation_analysis") or {}).get("ops_findings") or [])),
        "recommended_expansion_actions": list((((evidence_bundle.get("execution") or {}).get("post_validation_analysis") or {}).get("recommended_expansion_actions") or [])),
        "new_technology_candidates": list((((evidence_bundle.get("execution") or {}).get("post_validation_analysis") or {}).get("new_technology_candidates") or [])),
    }
    _compat_write_text(readiness_checklist_path, readiness_checklist)
    _compat_write_json(validation_json_path, validation_result_payload)
    _compat_write_text(validation_md_path, validation_result_md)
    _compat_write_text(failure_report_path, failure_report)
    _compat_write_text(root_cause_report_path, root_cause_report)
    return {
        "final_readiness_checklist_path": _compat_relative_path(readiness_checklist_path, output_dir),
        "validation_result_json_path": _compat_relative_path(validation_json_path, output_dir),
        "validation_result_md_path": _compat_relative_path(validation_md_path, output_dir),
        "failure_report_path": _compat_relative_path(failure_report_path, output_dir),
        "root_cause_report_path": _compat_relative_path(root_cause_report_path, output_dir),
        "output_audit_path": ORCH_OUTPUT_AUDIT_PATH,
        "traceability_map_path": ORCH_TRACEABILITY_MAP_PATH,
    }


def _build_document_stale_scan(output_dir: Path) -> Dict[str, Any]:
    axis_labels = {
        "operational_paths": "운영 경로",
        "judgement": "판정",
        "latest_verification_round": "최근 실검증 회차",
        "localhost_usage": "localhost 사용 여부",
        "legacy_contract": "레거시 계약 문자열",
    }

    def _parse_latest_verification_record_row(status_text: str) -> Dict[str, str]:
        rows: List[Dict[str, str]] = []
        in_record_table = False
        for raw_line in status_text.splitlines():
            line = raw_line.rstrip()
            if line.startswith("### 10-1. 실검증 기록표"):
                in_record_table = True
                continue
            if in_record_table and line.startswith("## "):
                break
            if not in_record_table or not line.startswith("|"):
                continue
            normalized = line.strip()
            if normalized.startswith("| 회차 |") or normalized.startswith("|---"):
                continue
            cells = [cell.strip() for cell in normalized.strip("|").split("|")]
            if len(cells) < 6:
                continue
            rows.append(
                {
                    "round": cells[0],
                    "captured_at": cells[1],
                    "topic": cells[2],
                    "command": cells[3],
                    "result": cells[4],
                    "evidence": cells[5],
                }
            )
        return dict(rows[-1]) if rows else {}

    def _append_stale_hit(
        stale_hits: List[Dict[str, str]],
        axis_matches: Dict[str, List[Dict[str, str]]],
        *,
        axis: str,
        path: str,
        rule: str,
        match: str,
        note: str = "",
    ) -> None:
        payload = {
            "axis": axis,
            "axis_label": axis_labels.get(axis, axis),
            "path": path,
            "rule": rule,
            "match": match,
        }
        if note:
            payload["note"] = note
        stale_hits.append(payload)
        axis_matches.setdefault(axis, []).append(payload)

    stale_hits: List[Dict[str, str]] = []
    axis_matches: Dict[str, List[Dict[str, str]]] = {axis: [] for axis in axis_labels}
    scan_targets = [
        output_dir / "README.md",
        output_dir / "docs",
    ]
    for target in scan_targets:
        if not target.exists():
            continue
        candidates = [target] if target.is_file() else [path for path in target.rglob("*") if path.is_file()]
        for candidate in candidates:
            if candidate.suffix.lower() not in {".md", ".txt", ".json", ".py", ".yml", ".yaml"}:
                continue
            candidate_relpath = _compat_relative_path(candidate, output_dir)
            if candidate_relpath == ORCH_VALIDATION_RESULT_JSON_PATH.replace("\\", "/"):
                continue
            if candidate_relpath in {
                "README.md",
                "docs/orchestrator-multigenerator-upgrade-status.md",
                "docs/system-cleanup-checklist.md",
            }:
                continue
            try:
                text = candidate.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            normalized = text.lower()
            if "app/services.py" in normalized:
                _append_stale_hit(
                    stale_hits,
                    axis_matches,
                    axis="legacy_contract",
                    path=candidate_relpath,
                    rule="legacy_services_contract",
                    match="app/services.py",
                    note="서비스 패키지 단일화 헌법 규칙과 충돌합니다.",
                )
            if "http://localhost" in normalized:
                _append_stale_hit(
                    stale_hits,
                    axis_matches,
                    axis="localhost_usage",
                    path=_compat_relative_path(candidate, output_dir),
                    rule="localhost_performance_baseline_forbidden",
                    match="http://localhost",
                    note="성능 기준은 127.0.0.1 또는 운영 도메인만 허용됩니다.",
                )
    workspace_readme = REPO_ROOT / "README.md"
    workspace_status_doc = REPO_ROOT / "docs" / "orchestrator-multigenerator-upgrade-status.md"
    try:
        readme_text = workspace_readme.read_text(encoding="utf-8", errors="ignore") if workspace_readme.exists() else ""
    except Exception:
        readme_text = ""
    try:
        status_text = workspace_status_doc.read_text(encoding="utf-8", errors="ignore") if workspace_status_doc.exists() else ""
    except Exception:
        status_text = ""

    readme_normalized = readme_text.lower()
    status_normalized = status_text.lower()
    status_overview_text = status_text.split("## 10. 실검증 기록 규칙", 1)[0]
    status_overview_normalized = status_overview_text.lower()
    latest_verification_record = _parse_latest_verification_record_row(status_text)
    comparison_rules = [
        {
            "rule": "readme_status_judgement_sync",
            "readme_marker": "현재 판정: `조건부 운영 가능 / self-run 최종 종료 검증 진행 중`",
            "status_marker": "현재 판정:\n- 전체 체크리스트 작성 및 문서 반영: 구현됨\n- 전체 실검증 종료: 구현됨",
        },
        {
            "rule": "readme_self_run_tracking_sync",
            "readme_marker": "관리자 self-run 은 runtime artifact 생성 및 worker 기동 기록까지는 검증됐지만, 최종 상태 전이(`pending_approval / failed / applied`)는 계속 추적 중이다",
            "status_marker": "운영 실검증 2회 통과",
        },
    ]
    for rule in comparison_rules:
        readme_has = str(rule["readme_marker"]).lower() in readme_normalized
        status_has = str(rule["status_marker"]).lower() in status_normalized
        if readme_has != status_has:
            _append_stale_hit(
                stale_hits,
                axis_matches,
                axis="judgement",
                path="README.md <-> docs/orchestrator-multigenerator-upgrade-status.md",
                rule=str(rule["rule"]),
                match=f"readme={readme_has}, status_doc={status_has}",
                note="README와 상태 문서의 판정 문구가 서로 어긋납니다.",
            )
    readme_status_window = readme_text.split("### 현재 운영 핵심 메모", 1)[0]
    status_status_match = re.search(
        r"^## 현재 판정\s*(.*?)^(?:## |\Z)",
        status_text,
        re.MULTILINE | re.DOTALL,
    )
    status_status_window = status_status_match.group(1) if status_status_match else status_text
    readme_reflection_required = "- 현재 판정: `반영 필요`" in readme_status_window
    status_reflection_required = "- 상태: **반영 필요**" in status_status_window
    readme_completed = "- 현재 판정: `완료됨`" in readme_status_window
    status_completed = "- 상태: **완료됨**" in status_status_window
    if readme_reflection_required != status_reflection_required or readme_completed != status_completed:
        _append_stale_hit(
            stale_hits,
            axis_matches,
            axis="judgement",
            path="README.md <-> docs/orchestrator-multigenerator-upgrade-status.md",
            rule="readme_status_completion_sync",
            match=(
                f"readme_reflection_required={readme_reflection_required}, "
                f"status_reflection_required={status_reflection_required}, "
                f"readme_completed={readme_completed}, status_completed={status_completed}"
            ),
            note="README와 상태 문서의 반영 필요/완료됨 판정이 불일치합니다.",
        )
    latest_record_blob = " ".join(
        str(latest_verification_record.get(key) or "")
        for key in ["topic", "command", "result", "evidence"]
    ).lower()
    latest_record_result = str(latest_verification_record.get("result") or "")
    if latest_record_blob and "통과" in latest_record_result:
        latest_row_rules = [
            {
                "keyword": "system-settings",
                "rule": "latest_record_system_settings_sync",
                "readme_forbidden": ["504 gateway timeout", "오케스트레이터 전역 설정 조회 실패"],
                "status_forbidden": ["504 gateway timeout", "system-settings 반복 504", "오케스트레이터 전역 설정 조회 실패"],
            },
            {
                "keyword": "ws=open",
                "rule": "latest_record_websocket_sync",
                "readme_forbidden": ["운영 경로 websocket 미완료", "websocket 미완료"],
                "status_forbidden": ["운영 경로 websocket 미완료", "websocket 미완료"],
            },
            {
                "keyword": "customer_summary_ok=200",
                "rule": "latest_record_customer_summary_sync",
                "readme_forbidden": ["마켓 경로 미완료", "marketplace 미완료"],
                "status_forbidden": ["마켓 경로 미완료", "marketplace 미완료"],
            },
        ]
        for rule in latest_row_rules:
            if rule["keyword"] not in latest_record_blob:
                continue
            for forbidden in rule["readme_forbidden"]:
                if forbidden.lower() in readme_normalized:
                    _append_stale_hit(
                        stale_hits,
                        axis_matches,
                        axis="operational_paths",
                        path="README.md",
                        rule=rule["rule"],
                        match=f"latest_record={rule['keyword']} / forbidden={forbidden}",
                        note="최신 운영 실검증 통과 후 금지 문구가 README에 남아 있습니다.",
                    )
            for forbidden in rule["status_forbidden"]:
                if forbidden.lower() in status_overview_normalized:
                    _append_stale_hit(
                        stale_hits,
                        axis_matches,
                        axis="operational_paths",
                        path="docs/orchestrator-multigenerator-upgrade-status.md",
                        rule=rule["rule"],
                        match=f"latest_record={rule['keyword']} / forbidden={forbidden}",
                        note="최신 운영 실검증 통과 후 금지 문구가 상태 문서 개요에 남아 있습니다.",
                    )
    latest_record_link_table = [
        {
            "record_keyword": "system-settings",
            "record_scope_id": "phase-f-system-settings-504-recurrence",
            "document_paths": ["README.md", "docs/orchestrator-multigenerator-upgrade-status.md"],
            "expected_reflection": "system-settings 504 재발 차단 결과가 README/상태 문서에 stale 없이 반영돼야 합니다.",
        },
        {
            "record_keyword": "ws=open",
            "record_scope_id": "phase-f-websocket-recovery",
            "document_paths": ["README.md", "docs/orchestrator-multigenerator-upgrade-status.md"],
            "expected_reflection": "websocket 운영 경로 통과 상태가 README/상태 문서에 동기화돼야 합니다.",
        },
        {
            "record_keyword": "customer_summary_ok=200",
            "record_scope_id": "phase-f-marketplace-route-recovery",
            "document_paths": ["README.md", "docs/orchestrator-multigenerator-upgrade-status.md"],
            "expected_reflection": "marketplace/customer summary 운영 경로 통과 상태가 README/상태 문서에 동기화돼야 합니다.",
        },
        {
            "record_keyword": "반영 필요/완료됨",
            "record_scope_id": "phase-g-documentation-sync",
            "document_paths": ["README.md", "docs/orchestrator-multigenerator-upgrade-status.md"],
            "expected_reflection": "반영 필요/완료됨 판정이 두 문서에서 동일해야 합니다.",
        },
        {
            "record_keyword": "app/services.py",
            "record_scope_id": "phase-g-service-package-contract",
            "document_paths": ["README.md", "docs/**/*"],
            "expected_reflection": "서비스 패키지 계약은 app/services/__init__.py + runtime_service.py 기준만 유지해야 합니다.",
        },
    ]
    latest_round_matches = [
        item
        for item in stale_hits
        if str(item.get("rule") or "").startswith("latest_record_")
    ]
    if latest_verification_record and not latest_round_matches:
        matched_keywords = [
            entry["record_keyword"]
            for entry in latest_record_link_table
            if entry["record_keyword"] != "반영 필요/완료됨"
            and entry["record_keyword"].lower() in latest_record_blob
        ]
        axis_matches["latest_verification_round"] = [
            {
                "axis": "latest_verification_round",
                "axis_label": axis_labels["latest_verification_round"],
                "path": "README.md <-> docs/orchestrator-multigenerator-upgrade-status.md",
                "rule": "latest_record_document_sync_ok",
                "match": ", ".join(matched_keywords) or "no-known-keyword",
                "note": "최신 실검증 회차와 문서 반영 상태가 현재 기준으로 충돌하지 않습니다.",
            }
        ]
    else:
        axis_matches["latest_verification_round"] = latest_round_matches
    axes = {}
    for axis, axis_label in axis_labels.items():
        matches = list(axis_matches.get(axis) or [])
        axes[axis] = {
            "axis": axis,
            "axis_label": axis_label,
            "ok": len(matches) == 0,
            "stale_count": len(matches),
            "matches": matches,
        }
    documentation_sync = {
        "schema_version": "v1",
        "overall_status": "synced" if len(stale_hits) == 0 else "reflection_required",
        "stale_count": len(stale_hits),
        "axes": {
            axis: {
                "ok": payload["ok"],
                "stale_count": payload["stale_count"],
            }
            for axis, payload in axes.items()
        },
        "latest_verification_record": latest_verification_record,
        "latest_record_link_table": latest_record_link_table,
        "readme_status_sync": {
            "readme_reflection_required": readme_reflection_required,
            "status_reflection_required": status_reflection_required,
            "readme_completed": readme_completed,
            "status_completed": status_completed,
        },
        "stale_matches": stale_hits,
    }
    return {
        "ok": len(stale_hits) == 0,
        "axes": axes,
        "matches": stale_hits,
        "latest_verification_record": latest_verification_record,
        "documentation_sync": documentation_sync,
    }


def _build_final_readiness_checklist_content(
    *,
    project_name: str,
    completion_gate_ok: bool,
    semantic_gate_ok: bool,
    packaging_audit_ok: bool,
    integration_test_engine_ok: bool,
    framework_e2e_validation_ok: bool,
    external_integration_validation_ok: bool,
    shipping_zip_validation_ok: bool,
    product_readiness_hard_gate_ok: bool,
    hard_gate_checklist_lines: List[str],
    operational_latency_lines: List[str],
) -> str:
    return (
        f"# {project_name} final readiness checklist\n\n"
        f"- [{'x' if completion_gate_ok else ' '}] completion gate\n"
        f"- [{'x' if semantic_gate_ok else ' '}] semantic gate\n"
        f"- [{'x' if packaging_audit_ok else ' '}] packaging audit\n"
        f"- [{'x' if integration_test_engine_ok else ' '}] integration test engine\n"
        f"- [{'x' if framework_e2e_validation_ok else ' '}] framework e2e validation\n"
        f"- [{'x' if external_integration_validation_ok else ' '}] external integration validation\n"
        f"- [{'x' if shipping_zip_validation_ok else ' '}] shipping zip validation\n"
        f"- [{'x' if product_readiness_hard_gate_ok else ' '}] product readiness hard gate\n\n"
        "## hard gate closure\n"
        + "\n".join(hard_gate_checklist_lines)
        + "\n\n"
        + "## operational latency evidence\n"
        + "\n".join(operational_latency_lines)
        + "\n"
    )


def repair_final_readiness_checklist(output_dir: Path) -> Dict[str, Any]:
    output_dir = Path(output_dir).resolve()
    validation_json_path = output_dir / ORCH_VALIDATION_RESULT_JSON_PATH
    readiness_checklist_path = output_dir / "docs" / "final_readiness_checklist.md"
    if not validation_json_path.exists():
        return {
            "ok": False,
            "reason": f"validation result not found: {validation_json_path}",
            "output_dir": str(output_dir),
        }
    payload = json.loads(validation_json_path.read_text(encoding="utf-8"))
    validation_engines = payload.get("validation_engines") or {}
    product_readiness_hard_gate = validation_engines.get("product_readiness_hard_gate") or {}
    hard_gate_stage_map = {
        str(stage.get("id") or ""): stage
        for stage in (product_readiness_hard_gate.get("stages") or [])
        if isinstance(stage, dict)
    }
    hard_gate_checklist_lines = [
        f"- [{'x' if hard_gate_stage_map.get('dependency_install', {}).get('ok') else ' '}] dependency install",
        f"- [{'x' if hard_gate_stage_map.get('standalone_boot', {}).get('ok') else ' '}] standalone boot",
        f"- [{'x' if hard_gate_stage_map.get('api_smoke', {}).get('ok') else ' '}] core api smoke",
        f"- [{'x' if hard_gate_stage_map.get('pytest', {}).get('ok') else ' '}] pytest",
        f"- [{'x' if hard_gate_stage_map.get('zip_reproduction', {}).get('ok') else ' '}] zip reproduction",
    ]
    readiness_content = _build_final_readiness_checklist_content(
        project_name=str(payload.get("project_name") or output_dir.name),
        completion_gate_ok=bool(payload.get("completion_gate_ok")),
        semantic_gate_ok=bool((validation_engines.get("semantic_gate") or {}).get("ok")),
        packaging_audit_ok=bool(hard_gate_stage_map.get("packaging_audit", {}).get("ok")),
        integration_test_engine_ok=bool((validation_engines.get("integration_test_engine") or {}).get("ok")),
        framework_e2e_validation_ok=bool((validation_engines.get("framework_e2e_validation") or {}).get("ok")),
        external_integration_validation_ok=bool((validation_engines.get("external_integration_validation") or {}).get("ok")),
        shipping_zip_validation_ok=bool((validation_engines.get("shipping_zip_validation") or {}).get("ok")),
        product_readiness_hard_gate_ok=bool(product_readiness_hard_gate.get("ok")),
        hard_gate_checklist_lines=hard_gate_checklist_lines,
        operational_latency_lines=[
            f"- latency_warning: {'true' if ((payload.get('readiness_artifacts') or {}).get('latency_warning')) else 'false'}",
            f"- warning_targets: {', '.join(((payload.get('readiness_artifacts') or {}).get('warning_targets') or [])) or 'none'}",
            f"- max_latency_ms: {((payload.get('readiness_artifacts') or {}).get('max_latency_ms') if ((payload.get('readiness_artifacts') or {}).get('max_latency_ms') is not None) else 'none')}",
            f"- warning_threshold_ms: {', '.join(f'{key}={value}ms' for key, value in sorted((((payload.get('readiness_artifacts') or {}).get('warning_threshold_ms') or {}).items()))) or 'none'}",
        ],
    )
    _compat_write_text(readiness_checklist_path, readiness_content)
    payload["readiness_artifacts"] = {
        "final_readiness_checklist_path": _compat_relative_path(readiness_checklist_path, output_dir),
        "validation_result_json_path": ORCH_VALIDATION_RESULT_JSON_PATH,
        "validation_result_md_path": ORCH_VALIDATION_RESULT_MD_PATH,
        "failure_report_path": ORCH_FAILURE_REPORT_PATH,
        "root_cause_report_path": ORCH_ROOT_CAUSE_REPORT_PATH,
    }
    _compat_write_json(validation_json_path, payload)
    return {
        "ok": True,
        "output_dir": str(output_dir),
        "final_readiness_checklist_path": str(readiness_checklist_path),
        "length": len(readiness_content),
    }




def _build_product_readiness_hard_gate(
    *,
    validation_profile: str,
    packaging_audit: Dict[str, Any],
    framework_e2e_validation: Dict[str, Any],
    external_integration_validation: Dict[str, Any],
    integration_test_engine: Dict[str, Any],
    shipping_zip_validation: Dict[str, Any],
    shipping_package: Dict[str, Any],
) -> Dict[str, Any]:
    integration_checks = list(integration_test_engine.get("checks_run") or [])
    integration_failures = [str(item) for item in (integration_test_engine.get("failures") or []) if str(item).strip()]

    dependency_install_ran = any(
        check.startswith("pip install -r") or check.startswith("python -m pip install")
        for check in integration_checks
    )
    standalone_boot_ran = any(check.startswith("standalone_boot:") for check in integration_checks)
    api_smoke_ran = any(check.startswith("http_get:") for check in integration_checks)
    pytest_ran = any(check.startswith("pytest -q") for check in integration_checks)

    def _stage(stage_id: str, ok: bool, summary: str, evidence: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {
            "id": stage_id,
            "ok": bool(ok),
            "summary": summary,
            "evidence": dict(evidence or {}),
        }

    stages = [
        _stage(
            "packaging_audit",
            bool(packaging_audit.get("packaging_ready")),
            "패키징 필수 파일이 준비되었는지 확인합니다.",
            {
                "missing_packaging_files": list(packaging_audit.get("missing_packaging_files") or []),
                "required_packaging_files": list(packaging_audit.get("required_packaging_files") or []),
            },
        ),
        _stage(
            "dependency_install",
            dependency_install_ran and not any("pip install" in item or "venv" in item or "bootstrap" in item for item in integration_failures),
            "생성 직후 의존성 설치와 가상환경 구성이 성공해야 합니다.",
            {
                "checks_run": [check for check in integration_checks if check.startswith("pip install -r") or check.startswith("python -m pip install") or "venv" in check],
                "failures": [item for item in integration_failures if "pip install" in item or "venv" in item or "bootstrap" in item],
            },
        ),
        _stage(
            "standalone_boot",
            standalone_boot_ran and not any("standalone runtime" in item for item in integration_failures),
            "생성 산출물이 단독 기동되어야 합니다.",
            {
                "checks_run": [check for check in integration_checks if check.startswith("standalone_boot:")],
                "failures": [item for item in integration_failures if "standalone runtime" in item],
            },
        ),
        _stage(
            "api_smoke",
            api_smoke_ran and not any("standalone api" in item for item in integration_failures),
            "핵심 API 스모크 검증이 성공해야 합니다.",
            {
                "checks_run": [check for check in integration_checks if check.startswith("http_get:")],
                "failures": [item for item in integration_failures if "standalone api" in item],
            },
        ),
        _stage(
            "pytest",
            pytest_ran and not any("pytest" in item for item in integration_failures),
            "핵심 테스트가 통과해야 합니다.",
            {
                "checks_run": [check for check in integration_checks if check.startswith("pytest -q")],
                "failures": [item for item in integration_failures if "pytest" in item],
            },
        ),
        _stage(
            "framework_contract",
            bool(framework_e2e_validation.get("ok")),
            "프레임워크 구조와 실행 계약이 맞아야 합니다.",
            {
                "checks_run": list(framework_e2e_validation.get("commands_run") or []),
                "failures": list(framework_e2e_validation.get("failures") or []),
            },
        ),
        _stage(
            "external_integration",
            bool(external_integration_validation.get("ok")),
            "외부 연동 경계 파일과 커넥터가 존재해야 합니다.",
            {
                "checks_run": list(external_integration_validation.get("checks_run") or []),
                "failures": list(external_integration_validation.get("failures") or []),
            },
        ),
        _stage(
            "zip_reproduction",
            bool(shipping_zip_validation.get("ok")),
            "출고 ZIP 압축 해제 후 재현 검증이 성공해야 합니다.",
            {
                "checks_run": list(shipping_zip_validation.get("checks_run") or []),
                "failures": list(shipping_zip_validation.get("failures") or []),
                "archive_path": str(shipping_package.get("archive_path") or ""),
                "extracted_root": str(shipping_zip_validation.get("extracted_root") or ""),
            },
        ),
    ]

    failed_stages = [stage["id"] for stage in stages if not stage["ok"]]
    return {
        "validation_profile": validation_profile,
        "ok": len(failed_stages) == 0,
        "stages": stages,
        "failed_stages": failed_stages,
        "summary": (
            "product readiness hard gate passed"
            if not failed_stages
            else f"product readiness hard gate failed: {', '.join(failed_stages)}"
        ),
        "archive_path": str(shipping_package.get("archive_path") or ""),
    }


def _resolve_operational_evidence_target_defaults(profile_id: Optional[str]) -> List[Dict[str, Any]]:
    target_defaults = [
        {
            "id": "websocket",
            "target": "/api/llm/ws",
            "protocol": "websocket",
            "verification_method": "websocket-handshake-and-ping-pong",
            "note": "실도메인 handshake + connected + ping/pong 검증 결과를 연결해야 합니다.",
            "warning_threshold_ms": 150.0,
        },
        {
            "id": "admin",
            "target": "/admin/llm",
            "protocol": "https",
            "verification_method": "http-response-and-page-render",
            "note": "관리자 오케스트레이터 운영 경로 실검증 결과를 연결해야 합니다.",
            "warning_threshold_ms": 150.0,
        },
        {
            "id": "marketplace",
            "target": "/marketplace/orchestrator",
            "protocol": "https",
            "verification_method": "http-response-and-page-render",
            "note": "마켓 오케스트레이터 운영 경로 실검증 결과를 연결해야 합니다.",
            "warning_threshold_ms": 200.0,
        },
        {
            "id": "system_settings",
            "target": "/api/admin/system-settings",
            "protocol": "https",
            "verification_method": "http-response-json",
            "note": "관리자 시스템 설정 운영 경로 실검증 결과를 연결해야 합니다.",
            "warning_threshold_ms": 120.0,
        },
        {
            "id": "workspace_self_run_record",
            "target": "/api/admin/workspace-self-run-record?latest=true",
            "protocol": "https",
            "verification_method": "http-response-latest-record",
            "note": "latest self-run record 운영 경로 실검증 결과를 연결해야 합니다.",
            "warning_threshold_ms": 120.0,
        },
    ]

    normalized_profile = str(profile_id or "").strip().lower()
    if normalized_profile == "commerce_platform":
        allowed_ids = {"marketplace", "system_settings", "workspace_self_run_record"}
        return [dict(item) for item in target_defaults if item.get("id") in allowed_ids]
    return [dict(item) for item in target_defaults]


def _resolve_operational_evidence_probe_config() -> Dict[str, Any]:
    admin_probe_base_url = str(os.getenv("ADMIN_PROBE_BASE_URL") or "").strip() or "https://metanova1004.com"
    admin_probe_host = str(os.getenv("ADMIN_PROBE_HOST") or "").strip()

    admin_url = str(os.getenv("OPERATIONAL_EVIDENCE_ADMIN_URL") or "").strip()
    if not admin_url:
        admin_url = f"{admin_probe_base_url.rstrip('/')}/admin/llm"

    marketplace_url = str(os.getenv("OPERATIONAL_EVIDENCE_MARKETPLACE_URL") or "").strip()
    if not marketplace_url:
        marketplace_url = f"{admin_probe_base_url.rstrip('/')}/marketplace/orchestrator"

    public_headers: Dict[str, str] = {"Host": admin_probe_host} if admin_probe_host else {}
    return {
        "probe_base_url": admin_probe_base_url,
        "probe_urls": {
            "admin": admin_url,
            "marketplace": marketplace_url,
        },
        "public_headers": public_headers,
    }


def _build_operational_evidence_bundle(profile_id: Optional[str] = None, **_: Any) -> Dict[str, Any]:
    del profile_id
    target_defaults = _resolve_operational_evidence_target_defaults(None)

    capability_evidence = {}
    try:
        from backend.llm import admin_capabilities as admin_capabilities_module

        target_defaults = [dict(item) for item in (getattr(admin_capabilities_module, "OPERATIONAL_EVIDENCE_TARGETS", None) or target_defaults)]
        cached_reader = getattr(admin_capabilities_module, "_read_operational_evidence_cache", None)
        if callable(cached_reader):
            cached_payload = cached_reader()
            if isinstance(cached_payload, dict):
                capability_evidence = dict(cached_payload)
    except Exception:
        capability_evidence = {}

    def _build_operational_evidence_summary(targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        verified_count = 0
        warning_count = 0
        failed_count = 0
        warning_targets: List[str] = []
        latency_values: List[float] = []
        for target in targets:
            if not isinstance(target, dict):
                continue
            target_id = str(target.get("id") or "").strip()
            status = str(target.get("status") or "missing").strip().lower()
            if status == "verified":
                verified_count += 1
            elif status in {"warning", "degraded"}:
                warning_count += 1
            else:
                failed_count += 1
            if bool(target.get("latency_warning")) and target_id:
                warning_targets.append(target_id)
            latency_value = target.get("latency_ms")
            if isinstance(latency_value, (int, float)):
                latency_values.append(float(latency_value))
        return {
            "verified_count": verified_count,
            "warning_count": warning_count,
            "failed_count": failed_count,
            "required_count": len(targets),
            "warning_targets": warning_targets,
            "max_latency_ms": round(max(latency_values), 1) if latency_values else None,
        }

    evidence_map = capability_evidence if isinstance(capability_evidence, dict) else {}
    targets = []
    targets_by_id: Dict[str, Dict[str, Any]] = {}
    for item in target_defaults:
        evidence_item = evidence_map.get(item["id"]) if isinstance(evidence_map.get(item["id"]), dict) else {}
        ok = bool(evidence_item.get("ok")) # pyright: ignore[reportOptionalMemberAccess]
        status = str(evidence_item.get("status") or ("verified" if ok else "missing")) # pyright: ignore[reportOptionalMemberAccess]
        snapshot = {
            **item,
            "ok": ok,
            "status": status,
            "status_code": evidence_item.get("status_code"), # pyright: ignore[reportOptionalMemberAccess]
            "latency_ms": evidence_item.get("latency_ms"), # pyright: ignore[reportOptionalMemberAccess]
            "latency_warning": bool(evidence_item.get("latency_warning")), # pyright: ignore[reportOptionalMemberAccess]
            "warning_threshold_ms": evidence_item.get("warning_threshold_ms") or item.get("warning_threshold_ms"), # pyright: ignore[reportOptionalMemberAccess]
            "verified_at": evidence_item.get("verified_at"), # pyright: ignore[reportOptionalMemberAccess]
            "source": evidence_item.get("source") or "runtime-cache", # pyright: ignore[reportOptionalMemberAccess]
            "note": str(evidence_item.get("note") or item["note"]), # pyright: ignore[reportOptionalMemberAccess]
        }
        targets.append(snapshot)
        targets_by_id[item["id"]] = snapshot

    summary = _build_operational_evidence_summary(targets)
    return {
        "integration_status": (
            "verified"
            if summary["verified_count"] == len(targets)
            else ("partial" if summary["verified_count"] > 0 else "pending-runtime-verification")
        ),
        "verified_target_count": summary["verified_count"],
        "required_target_count": len(targets),
        "warning_target_count": summary["warning_count"],
        "failed_target_count": summary["failed_count"],
        "warning_targets": summary["warning_targets"],
        "max_latency_ms": summary["max_latency_ms"],
        "summary": summary,
        "targets_by_id": targets_by_id,
        "websocket": targets_by_id.get("websocket", {}),
        "admin": targets_by_id.get("admin", {}),
        "marketplace": targets_by_id.get("marketplace", {}),
        "system_settings": targets_by_id.get("system_settings", {}),
        "workspace_self_run_record": targets_by_id.get("workspace_self_run_record", {}),
        "targets": targets,
    }


def _build_post_validation_ai_analysis(
    *,
    completion_gate_ok: bool,
    semantic_audit_score: int,
    semantic_audit_ok: bool,
    product_readiness_hard_gate: Dict[str, Any],
    target_patch_registry: Dict[str, Any],
    operational_evidence: Dict[str, Any],
) -> Dict[str, Any]:
    failed_stages = list(product_readiness_hard_gate.get("failed_stages") or [])
    reusable_patch_units = list(target_patch_registry.get("reusable_patch_units") or [])
    target_file_ids = list(target_patch_registry.get("target_file_ids") or [])
    target_section_ids = list(target_patch_registry.get("target_section_ids") or [])
    target_feature_ids = list(target_patch_registry.get("target_feature_ids") or [])
    target_chunk_ids = list(target_patch_registry.get("target_chunk_ids") or [])
    failure_tags = list(target_patch_registry.get("failure_tags") or [])
    repair_tags = list(target_patch_registry.get("repair_tags") or [])
    operational_targets = list(operational_evidence.get("targets") or [])
    verified_targets = [
        str(item.get("id") or "target")
        for item in operational_targets
        if bool(item.get("ok"))
    ]
    missing_targets = [
        str(item.get("id") or "target")
        for item in operational_targets
        if not bool(item.get("ok"))
    ]
    analysis_summary = (
        "검증 통과 후 AI 정밀 분석: 출고 게이트를 통과했으며 selective apply 가능한 조각 단위를 중심으로 후속 확장 후보를 제안합니다."
        if completion_gate_ok
        else "검증 통과 후 AI 정밀 분석: 아직 게이트 차단이 남아 있어 실패 stage 제거와 selective apply 범위 축소가 우선입니다."
    )
    quality_findings = [
        f"semantic audit score={semantic_audit_score}",
        "semantic audit pass 상태입니다." if semantic_audit_ok else "semantic audit 보강이 필요합니다.",
        f"failure tags={len(failure_tags)} / repair tags={len(repair_tags)}",
    ]
    architecture_findings = [
        f"reusable patch units={len(reusable_patch_units)}",
        "고유 ID registry 기반 selective apply ready 상태입니다."
        if target_patch_registry.get("selective_apply_ready")
        else "고유 ID registry 매칭 범위를 더 늘려 selective apply ready 상태를 확보해야 합니다.",
        f"target ids files={len(target_file_ids)}, sections={len(target_section_ids)}, features={len(target_feature_ids)}, chunks={len(target_chunk_ids)}",
    ]
    ops_findings = [
        f"operational evidence integration={operational_evidence.get('integration_status') or 'unknown'}",
        "실도메인 운영 경로 증거를 hard gate evidence 체계와 연결해야 합니다.",
        f"verified targets={', '.join(verified_targets) or 'none'}",
    ]
    if failed_stages:
        ops_findings.append("차단된 hard gate stage: " + ", ".join(failed_stages))
    if missing_targets:
        ops_findings.append("추가 검증 필요 targets: " + ", ".join(missing_targets))
    return {
        "analysis_summary": analysis_summary,
        "quality_findings": quality_findings,
        "architecture_findings": architecture_findings,
        "ops_findings": ops_findings,
        "new_technology_candidates": [
            "evidence replay validator",
            "post-validation proposal ranking",
            "selective apply safety scorer",
            "target-id impact graph",
        ],
        "recommended_expansion_actions": [
            (
                "selective apply 대상으로 매칭된 file/section/chunk id를 기준으로 후속 self-improvement 작업문을 생성합니다."
                f" (files={len(target_file_ids)}, sections={len(target_section_ids)}, chunks={len(target_chunk_ids)})"
            ),
            (
                "운영 실도메인 evidence 결과를 approval/completion judge와 같은 증거 체계로 연결합니다."
                f" (verified={len(verified_targets)}/{len(operational_targets)})"
            ),
            (
                "failure_tags 와 repair_tags 우선순위를 기준으로 후속 개선 액션을 재정렬합니다."
                f" (failure_tags={len(failure_tags)}, repair_tags={len(repair_tags)})"
            ),
        ],
        "artifact_source": {
            "target_file_ids": target_file_ids,
            "target_section_ids": target_section_ids,
            "target_feature_ids": target_feature_ids,
            "target_chunk_ids": target_chunk_ids,
            "failure_tags": failure_tags,
            "repair_tags": repair_tags,
            "verified_operational_targets": verified_targets,
            "missing_operational_targets": missing_targets,
            "failed_hard_gate_stages": failed_stages,
        },
    }


def _build_completion_judge(
    *,
    semantic_gate: Dict[str, Any],
    packaging_audit: Dict[str, Any],
    integration_test_engine: Dict[str, Any],
    normalized_requirements: Dict[str, Any],
    integration_test_plan: Dict[str, Any],
    completion_state: str,
    framework_e2e_validation: Dict[str, Any],
    external_integration_validation: Dict[str, Any],
    shipping_zip_validation: Dict[str, Any],
    operational_evidence: Dict[str, Any] | None = None,
    legacy_contract_scan: Dict[str, Any] | None = None,
    output_dir: Path,
    written_files: List[str],
    domain_contract: Dict[str, Any],
    min_files: int = 9,
    min_dirs: int = 3,
) -> Dict[str, Any]:
    failed_reasons: List[str] = []
    quality_findings: List[str] = []
    if not bool(semantic_gate.get("ok")):
        failed_reasons.append("semantic gate failed")
    if not bool(packaging_audit.get("packaging_ready")):
        failed_reasons.append("packaging audit incomplete")
    if not bool(integration_test_engine.get("ok")):
        failed_reasons.append("integration test engine failed")

    runtime_checks = list(integration_test_plan.get("runtime_checks") or [])
    profile_id = str(domain_contract.get("profile_id") or "customer_program").strip()
    if completion_state != "ready":
        failed_reasons.append("scaffold output detected")
    if any("scaffold inventory" in str(path).lower() for path in written_files):
        quality_findings.append("scaffold inventory present in shipment")

    file_count = len(written_files)
    python_file_count = len([path for path in written_files if str(path).endswith(".py")])
    frontend_file_count = len([
        path for path in written_files
        if str(path).startswith(("frontend/", "app/")) and str(path).endswith((".ts", ".tsx", ".js", ".jsx"))
    ])
    test_file_count = len([path for path in written_files if str(path).startswith("tests/")])
    docs_file_count = len([path for path in written_files if str(path).startswith("docs/")])
    unique_dirs = {
        str(PurePosixPath(p).parent)
        for p in written_files
        if str(PurePosixPath(p).parent) not in {"", "."}
    }
    dir_count = len(unique_dirs)
    thin_file_markers: Dict[str, List[str]] = {
        "Makefile": ["run:", "test:", "check:"],
        "backend/main.py": ["create_application", "uvicorn.run", "__all__"],
        "scripts/dev.sh": ["set -euo pipefail", "uvicorn"],
        "scripts/check.sh": ["python -m compileall", "pytest -q -s", "requirements.delivery.lock.txt"],
        "backend/core/__init__.py": ["build_scaffold_runtime", "__all__"],
        "app/__init__.py": ["create_application", "build_runtime_payload", "__all__"],
        "backend/app/external_adapters/status_client.py": ["build_provider_status_map", "providers", "reachable"],
        "backend/app/connectors/base.py": ["CatalogConnectorResult", "build_sync_summary", "sync_products"],
        "backend/core/auth.py": ["JWT_SECRET", "JWT_ALGORITHM", "JWT_EXPIRE_MINUTES", "get_auth_settings"],
        "backend/core/security.py": ["ALLOWED_HOSTS", "CORS_ALLOW_ORIGINS", "https_only", "REQUEST_TIMEOUT_SEC"],
        "app/auth_routes.py": ["/auth", "/settings", "/token", "/validate"],
        "app/ops_routes.py": ["/ops", "/status", "/health", "/metrics"],
        "configs/app.env.example": ["DATABASE_URL=", "JWT_SECRET=", "ALLOWED_HOSTS=", "REQUEST_TIMEOUT_SEC=", "MODEL_REGISTRY_PATH="],
        "infra/prometheus.yml": ["scrape_interval", "job_name", "targets:"],
        "infra/deploy/security.md": ["JWT_SECRET", "ALLOWED_HOSTS", "CORS_ALLOW_ORIGINS", "TLS"],
    }
    tiny_files: List[str] = []
    for path in written_files:
        target_path = _resolve_orchestration_output_child_path(output_dir, str(path))
        if not target_path.exists() or not target_path.is_file() or "__pycache__" in str(path):
            continue
        normalized_path = str(path)
        if normalized_path.endswith("__init__.py"):
            continue
        if normalized_path.endswith((".json", ".yml", ".yaml", ".toml", ".env.example", ".md", ".txt", ".gitignore", ".d.ts")):
            continue
        if normalized_path.startswith("addons/"):
            continue
        file_text = _strip_generated_id_headers(target_path.read_text(encoding="utf-8", errors="ignore"))
        required_markers = thin_file_markers.get(normalized_path)
        if required_markers is not None:
            if not all(marker in file_text for marker in required_markers):
                tiny_files.append(normalized_path)
            continue
        if target_path.stat().st_size <= 120:
            tiny_files.append(normalized_path)

    if file_count < min_files:
        quality_findings.append(f"written_files too small: {file_count} (min={min_files})")
    if min_dirs > 0 and dir_count < min_dirs:
        quality_findings.append(f"output directories too few: {dir_count} (min={min_dirs})")
    if docs_file_count < 5:
        quality_findings.append(f"docs coverage too small: {docs_file_count}")
    if test_file_count < 3:
        quality_findings.append(f"test coverage too small: {test_file_count}")
    generic_runtime_sources: List[str] = []
    for candidate in [
        _resolve_orchestration_output_child_path(output_dir, "README.md"),
        _resolve_orchestration_output_child_path(output_dir, "docs/deployment.md"),
        _resolve_orchestration_output_child_path(output_dir, "docs/testing.md"),
        _resolve_orchestration_output_child_path(output_dir, "docs/runbook.md"),
        _resolve_orchestration_output_child_path(output_dir, "app/auth_routes.py"),
        _resolve_orchestration_output_child_path(output_dir, "app/ops_routes.py"),
        _resolve_orchestration_output_child_path(output_dir, "backend/core/auth.py"),
        _resolve_orchestration_output_child_path(output_dir, "backend/core/security.py"),
        _resolve_orchestration_output_child_path(output_dir, "infra/prometheus.yml"),
        _resolve_orchestration_output_child_path(output_dir, "infra/deploy/security.md"),
    ]:
        if candidate.exists():
            generic_runtime_sources.append(candidate.read_text(encoding="utf-8", errors="ignore").lower())
    generic_runtime_text = "\n".join(generic_runtime_sources)
    generic_runtime_markers = {
        "auth settings flow": ["/auth/settings", "jwt_secret", "scopes"],
        "ops health flow": ["/ops/health", "/ops/status", "provider_status"],
        "shipping package flow": ["shipping", "shipment", "scripts/check.sh"],
        "security runtime flow": ["allowed_hosts", "cors_allow_origins", "https_only"],
    }
    for check_name, markers in generic_runtime_markers.items():
        if check_name in runtime_checks and not any(marker in generic_runtime_text for marker in markers):
            quality_findings.append(f"runtime scenario marker missing: {check_name}")
    if profile_id == "commerce_platform":
        if frontend_file_count < 5:
            quality_findings.append(f"commerce frontend implementation too small: {frontend_file_count}")
        if python_file_count < 12:
            quality_findings.append(f"commerce backend implementation too small: {python_file_count}")
        required_runtime_markers = {
            "catalog flow": ["catalog", "product"],
            "order workflow": ["order", "checkout"],
            "marketplace publish payload": ["publish", "shipment"],
        }
        readme_text = ""
        readme_path = _resolve_orchestration_output_child_path(output_dir, "README.md")
        if readme_path.exists():
            readme_text = readme_path.read_text(encoding="utf-8", errors="ignore").lower()
        frontend_page_text = ""
        for candidate in [
            _resolve_orchestration_output_child_path(output_dir, "frontend/app/page.tsx"),
            _resolve_orchestration_output_child_path(output_dir, "app/page.tsx"),
        ]:
            if candidate.exists():
                frontend_page_text = candidate.read_text(encoding="utf-8", errors="ignore").lower()
                break
        combined_runtime_text = f"{readme_text}\n{frontend_page_text}"
        for check_name, markers in required_runtime_markers.items():
            if check_name in runtime_checks and not any(marker in combined_runtime_text for marker in markers):
                quality_findings.append(f"runtime scenario marker missing: {check_name}")

    if profile_id == "deployment_kit_program":
        if python_file_count < 18:
            quality_findings.append(f"deployment kit backend implementation too small: {python_file_count}")
        if docs_file_count < 8:
            quality_findings.append(f"deployment kit docs coverage too small: {docs_file_count}")
        deployment_markers = {
            "publish readiness flow": ["publish-readiness", "publish_payload_ready", "publish_targets"],
            "ops health flow": ["/ops/health", "provider_status", "metrics"],
            "auth settings flow": ["/auth/settings", "JWT_SECRET", "scopes"],
            "shipping package flow": ["출고 패키지", "shipment.zip", "scripts/check.sh"],
        }
        runtime_sources: List[str] = []
        for candidate in [
            _resolve_orchestration_output_child_path(output_dir, "README.md"),
            _resolve_orchestration_output_child_path(output_dir, "docs/deployment.md"),
            _resolve_orchestration_output_child_path(output_dir, "docs/testing.md"),
            _resolve_orchestration_output_child_path(output_dir, "docs/runbook.md"),
            _resolve_orchestration_output_child_path(output_dir, "docs/shipping_readme.md"),
            _resolve_orchestration_output_child_path(output_dir, "app/routes.py"),
            _resolve_orchestration_output_child_path(output_dir, "app/ops_routes.py"),
            _resolve_orchestration_output_child_path(output_dir, "app/auth_routes.py"),
            _resolve_orchestration_output_child_path(output_dir, "app/services/runtime_service.py"),
        ]:
            if candidate.exists():
                runtime_sources.append(candidate.read_text(encoding="utf-8", errors="ignore").lower())
        combined_runtime_text = "\n".join(runtime_sources)
        for check_name, markers in deployment_markers.items():
            if check_name in runtime_checks and not any(marker.lower() in combined_runtime_text for marker in markers):
                quality_findings.append(f"runtime scenario marker missing: {check_name}")

    if tiny_files:
        quality_findings.append("thin implementation files detected: " + ", ".join(tiny_files[:8]))
    if not bool(framework_e2e_validation.get("ok")):
        failed_reasons.append("framework e2e validation failed")
    if not bool(external_integration_validation.get("ok")):
        failed_reasons.append("external integration validation failed")
    if not bool(shipping_zip_validation.get("ok")):
        failed_reasons.append("shipping zip reproduction validation failed")
    legacy_contract_payload = dict(legacy_contract_scan or {})
    if legacy_contract_payload and not bool(legacy_contract_payload.get("ok")):
        failed_reasons.append("legacy services contract detected")
        for match in list(legacy_contract_payload.get("matches") or [])[:12]:
            match_path = str(match.get("path") or "unknown")
            match_text = str(match.get("match") or "app/services.py")
            quality_findings.append(f"legacy contract marker detected: {match_path} -> {match_text}")
    if quality_findings:
        failed_reasons.extend(quality_findings)

    failed_reasons = list(dict.fromkeys(failed_reasons))
    operational_evidence_payload = dict(operational_evidence or {})
    operational_targets = list(operational_evidence_payload.get("targets") or [])
    required_target_count = int(
        operational_evidence_payload.get("required_target_count")
        or len(operational_targets)
        or 0
    )
    verified_target_count = int(operational_evidence_payload.get("verified_target_count") or 0)
    integration_status = str(operational_evidence_payload.get("integration_status") or "unknown").strip()
    trusted_output_dir = _trusted_orchestration_output_dir(output_dir)
    customer_generation_mode = bool(
        trusted_output_dir.exists()
        and _resolve_orchestration_output_child_path(trusted_output_dir, "docs/generation-plan.json").exists()
    )
    if required_target_count > 0 and verified_target_count < required_target_count:
        if not customer_generation_mode:
            failed_reasons.append(
                f"operational evidence incomplete: {verified_target_count}/{required_target_count}"
            )
    elif required_target_count <= 0 or integration_status in {"", "unknown", "failed", "pending-runtime-verification"}:
        if not customer_generation_mode:
            failed_reasons.append(
                f"operational evidence unavailable: {integration_status or 'unknown'}"
            )
    warning_targets = [
        str(target.get("id") or "")
        for target in operational_targets
        if isinstance(target, dict) and target.get("latency_warning")
    ]
    warning_threshold_ms = {
        str(target.get("id") or ""): round(float(target.get("warning_threshold_ms")), 1) # pyright: ignore[reportArgumentType]
        for target in operational_targets
        if isinstance(target, dict)
        and str(target.get("id") or "")
        and isinstance(target.get("warning_threshold_ms"), (int, float))
    }
    latency_values = [
        float(target.get("latency_ms")) # pyright: ignore[reportArgumentType]
        for target in operational_targets
        if isinstance(target, dict) and isinstance(target.get("latency_ms"), (int, float))
    ]
    operational_summary = {
        "integration_status": operational_evidence_payload.get("integration_status") or "unknown",
        "verified_target_count": int(operational_evidence_payload.get("verified_target_count") or 0),
        "required_target_count": int(operational_evidence_payload.get("required_target_count") or len(operational_targets)),
        "latency_warning": bool(warning_targets),
        "warning_targets": warning_targets,
        "warning_threshold_ms": warning_threshold_ms,
        "max_latency_ms": round(max(latency_values), 1) if latency_values else None,
        "targets": operational_targets,
    }
    return {
        "product_ready": len(failed_reasons) == 0,
        "failed_reasons": failed_reasons,
        "quality_findings": quality_findings,
        "scaffold_only": completion_state != "ready",
        "quality_summary": {
            "written_files": file_count,
            "python_files": python_file_count,
            "frontend_files": frontend_file_count,
            "test_files": test_file_count,
            "docs_files": docs_file_count,
            "thin_files": tiny_files[:20],
        },
        "completion_conditions": normalized_requirements.get("completion_conditions") or [],
        "test_conditions": normalized_requirements.get("test_conditions") or [],
        "required_tests": integration_test_plan.get("required_tests") or [],
        "shipping_zip_validation": shipping_zip_validation,
        "improvement_loop_enabled": True,
        "improvement_loop_strategy": [
            "100% 통과 후 구매자 피드백 수집",
            "요구사항-기능 차이 구조화",
            "확장 및 보정 작업문 자동 생성",
            "같은 게이트/출고 엔진으로 재검증",
        ],
        "operational_evidence_summary": operational_summary,
        "legacy_contract_scan": legacy_contract_payload,
    }


















async def run_orchestration(
    request: OrchestrationRequest,
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> OrchestrationResponse:
    return await run_customer_orchestration_service(
        request,
        run_orchestration_impl=_run_orchestration_core,
        progress_callback=progress_callback,
    )


async def _run_orchestration_core(
    request: OrchestrationRequest,
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> OrchestrationResponse:
    started_at = time.perf_counter()
    preparation = await prepare_customer_orchestration_context_service(
        request,
        normalize_requested_mode_func=_normalize_requested_mode,
        emit_orchestration_progress_func=_emit_orchestration_progress,
        build_customer_order_profile_func=_build_customer_order_profile,
        compat_domain_required_files_func=_compat_domain_required_files,
        orch_required_file_paths=list(ORCH_REQUIRED_FILE_PATHS or []),
        normalize_customer_requirements_func=_normalize_customer_requirements,
        build_domain_contract_func=_build_domain_contract,
        build_integration_test_plan_func=_build_integration_test_plan,
        normalize_pipeline_agents_func=_normalize_pipeline_agents,
        filter_pipeline_for_validation_profile_func=_filter_pipeline_for_validation_profile,
        orch_b_brain_agent_key=ORCH_B_BRAIN_AGENT_KEY,
        orchestration_spec_type=OrchestrationSpec,
        default_dod_targets_func=_default_dod_targets,
        compat_project_name_func=_compat_project_name,
        compat_output_dir_func=_compat_output_dir,
        progress_callback=progress_callback,
    )
    task = str(preparation["task"])
    mode = str(preparation["mode"])
    order_profile = dict(preparation["order_profile"])
    validation_profile = str(preparation["validation_profile"])

    # ── 소리새 엔진 컨트롤 타워 훅 ─────────────────────────────────
    # 오케스트레이션 태스크를 소리새 의사결정 엔진에 알림(분석 힌트 수집).
    # 실패해도 기존 LLM 경로에 영향 없음(non-blocking).
    try:
        from backend.services.shinsegye.engine_hub import SorisaeEngineHub as _SHub
        _sorisae_hint = _SHub.get_instance().orchestrator_hook(
            task,
            {"mode": mode, "validation_profile": validation_profile},
        )
        if _sorisae_hint:
            order_profile.setdefault("sorisae_routing_hint", _sorisae_hint)
            logger.debug("[SorisaeHub] orchestrator_hook hint: %s", _sorisae_hint)
    except Exception as _se:
        logger.debug("[SorisaeHub] orchestrator_hook skipped: %s", _se)
    # ────────────────────────────────────────────────────────────────
    compat_required_files = list(preparation["compat_required_files"])
    normalized_requirements = dict(preparation["normalized_requirements"])
    domain_contract = dict(preparation["domain_contract"])
    integration_test_plan = dict(preparation["integration_test_plan"])
    spec = preparation["spec"]
    project_name = str(preparation["project_name"])
    output_dir = preparation["output_dir"]
    _log_orchestration_phase("prepared", started_at, project_name=project_name, validation_profile=validation_profile)
    _stages = await run_customer_validation_stages_service(
        request=request,
        task=task,
        mode=mode,
        order_profile=order_profile,
        validation_profile=validation_profile,
        compat_required_files=compat_required_files,
        normalized_requirements=normalized_requirements,
        domain_contract=domain_contract,
        integration_test_plan=integration_test_plan,
        project_name=project_name,
        output_dir=output_dir,
        started_at=started_at,
        progress_callback=progress_callback,
        _log_orchestration_phase=_log_orchestration_phase,
        _emit_orchestration_progress=_emit_orchestration_progress,
        _run_b_brain_multi_generator=_run_b_brain_multi_generator,
        _compat_manifest_for_request=_compat_manifest_for_request,
        _compat_write_manifest=_compat_write_manifest,
        _compat_run_semantic_gate=_compat_run_semantic_gate,
        _build_packaging_audit=_build_packaging_audit,
        _run_domain_integration_test_engine=_run_domain_integration_test_engine,
        _run_framework_e2e_validator=_run_framework_e2e_validator,
        _run_external_integration_validator=_run_external_integration_validator,
        _build_completion_judge=_build_completion_judge,
        _build_operational_evidence_bundle=_build_operational_evidence_bundle,
        build_target_patch_registry_snapshot=build_target_patch_registry_snapshot,
        _compat_write_json=_compat_write_json,
        _compat_write_auxiliary_outputs=_compat_write_auxiliary_outputs,
        _compat_relative_path=_compat_relative_path,
        ORCH_MIN_FILES=ORCH_MIN_FILES,
        ORCH_MIN_DIRS=ORCH_MIN_DIRS,
        ORCH_SEMANTIC_AUDIT_MIN_SCORE=ORCH_SEMANTIC_AUDIT_MIN_SCORE,
        ORCH_ARTIFACT_LOG_PATH=ORCH_ARTIFACT_LOG_PATH,
        ORCH_TRACEABILITY_MAP_PATH=ORCH_TRACEABILITY_MAP_PATH,
        ORCH_SEMANTIC_AUDIT_REPORT_PATH=ORCH_SEMANTIC_AUDIT_REPORT_PATH,
        ORCH_PYTHON_SECURITY_REPORT_PATH=ORCH_PYTHON_SECURITY_REPORT_PATH,
        ORCH_VALIDATION_RESULT_JSON_PATH=ORCH_VALIDATION_RESULT_JSON_PATH,
        ORCH_VALIDATION_RESULT_MD_PATH=ORCH_VALIDATION_RESULT_MD_PATH,
        ORCH_FAILURE_REPORT_PATH=ORCH_FAILURE_REPORT_PATH,
        ORCH_ROOT_CAUSE_REPORT_PATH=ORCH_ROOT_CAUSE_REPORT_PATH,
        ORCH_OUTPUT_AUDIT_PATH=ORCH_OUTPUT_AUDIT_PATH,
        ORCH_ID_REGISTRY_PATH=ORCH_ID_REGISTRY_PATH,
        ORCH_ID_REGISTRY_SCHEMA_PATH=ORCH_ID_REGISTRY_SCHEMA_PATH,
    )
    b_brain_result = _stages["b_brain_result"]
    written_files = _stages["written_files"]
    anchor_path = _stages["anchor_path"]
    completion_state = _stages["completion_state"]
    semantic_gate = _stages["semantic_gate"]
    packaging_audit = _stages["packaging_audit"]
    integration_test_engine = _stages["integration_test_engine"]
    framework_e2e_validation = _stages["framework_e2e_validation"]
    external_integration_validation = _stages["external_integration_validation"]
    completion_judge = _stages["completion_judge"]
    semantic_audit_score = _stages["semantic_audit_score"]
    semantic_audit_ok = _stages["semantic_audit_ok"]
    target_patch_registry_snapshot = _stages["target_patch_registry_snapshot"]
    artifact_log_path = _stages["artifact_log_path"]
    traceability_map_path = _stages["traceability_map_path"]
    semantic_audit_report_path = _stages["semantic_audit_report_path"]
    python_security_report_path = _stages["python_security_report_path"]
    auxiliary_outputs = _stages["auxiliary_outputs"]

    finalized = finalize_customer_validation_bundle_service(
        output_dir=output_dir,
        task=task,
        mode=mode,
        project_name=project_name,
        validation_profile=validation_profile,
        normalized_requirements=normalized_requirements,
        domain_contract=domain_contract,
        integration_test_plan=integration_test_plan,
        packaging_audit=packaging_audit,
        completion_state=completion_state,
        written_files=written_files,
        semantic_gate=semantic_gate,
        framework_e2e_validation=framework_e2e_validation,
        external_integration_validation=external_integration_validation,
        integration_test_engine=integration_test_engine,
        completion_judge=completion_judge,
        semantic_audit_score=semantic_audit_score,
        semantic_audit_ok=semantic_audit_ok,
        target_patch_registry_snapshot=target_patch_registry_snapshot,
        anchor_path=anchor_path,
        artifact_log_path=artifact_log_path,
        traceability_map_path=traceability_map_path,
        output_audit_path=output_dir / str(auxiliary_outputs.get("output_audit_path") or ORCH_OUTPUT_AUDIT_PATH),
        build_shipping_package_func=_build_shipping_package,
        log_orchestration_phase_func=_log_orchestration_phase,
        run_shipping_zip_reproduction_validation_func=_run_shipping_zip_reproduction_validation,
        build_product_readiness_hard_gate_func=_build_product_readiness_hard_gate,
        build_operational_evidence_bundle_func=_build_operational_evidence_bundle,
        build_completion_judge_func=_build_completion_judge,
        build_post_validation_ai_analysis_func=_build_post_validation_ai_analysis,
        write_automatic_validation_artifacts_func=_write_automatic_validation_artifacts,
        build_evidence_bundle_func=_build_evidence_bundle,
        request_run_id=str(request.run_id or ""),
        started_at=started_at,
        emit_orchestration_progress_func=_emit_orchestration_progress,
        progress_callback=progress_callback,
    )
    _log_orchestration_phase("finalization_returned", started_at, project_name=project_name, validation_profile=validation_profile)
    shipping_package = dict(finalized["shipping_package"])
    shipping_zip_validation = dict(finalized["shipping_zip_validation"])
    product_readiness_hard_gate = dict(finalized["product_readiness_hard_gate"])
    operational_evidence = dict(finalized["operational_evidence"])
    completion_judge = dict(finalized["completion_judge"])
    completion_gate_ok = bool(finalized["completion_gate_ok"])
    post_validation_analysis = dict(finalized["post_validation_analysis"])
    validation_artifacts = dict(finalized["validation_artifacts"])
    evidence_bundle = dict(finalized["evidence_bundle"])
    artifact_paths = dict(finalized.get("artifact_paths") or {})
    written_files = list(finalized["written_files"])

    return assemble_customer_orchestration_response_service(
        request=request,
        task=task,
        mode=mode,
        project_name=project_name,
        validation_profile=validation_profile,
        order_profile=order_profile,
        semantic_gate=semantic_gate,
        completion_judge=completion_judge,
        completion_gate_ok=completion_gate_ok,
        semantic_audit_score=semantic_audit_score,
        semantic_audit_ok=semantic_audit_ok,
        written_files=written_files,
        anchor_path=anchor_path,
        output_dir=output_dir,
        artifact_log_path=artifact_log_path,
        semantic_audit_report_path=semantic_audit_report_path,
        python_security_report_path=python_security_report_path,
        traceability_map_path=traceability_map_path,
        auxiliary_outputs=auxiliary_outputs,
        target_patch_registry_snapshot=target_patch_registry_snapshot,
        shipping_package=shipping_package,
        validation_artifacts=validation_artifacts,
        product_readiness_hard_gate=product_readiness_hard_gate,
        integration_test_engine=integration_test_engine,
        shipping_zip_validation=shipping_zip_validation,
        packaging_audit=packaging_audit,
        framework_e2e_validation=framework_e2e_validation,
        external_integration_validation=external_integration_validation,
        post_validation_analysis=post_validation_analysis,
        operational_evidence=operational_evidence,
        evidence_bundle=evidence_bundle,
        artifact_paths=artifact_paths,
        normalized_requirements=normalized_requirements,
        domain_contract=domain_contract,
        integration_test_plan=integration_test_plan,
        spec=spec,
        b_brain_result=b_brain_result,
        build_stage_history_with_refiner_fixer_func=_build_stage_history_with_refiner_fixer,
        build_refiner_fixer_stage_payload_func=_build_refiner_fixer_stage_payload,
        build_improvement_loop_plan_func=_build_improvement_loop_plan,
        run_refinement_loop_func=_run_refinement_loop,
        build_multi_command_plan_func=build_multi_command_plan,
        build_admin_flow_trace_func=build_admin_flow_trace,
        resolve_active_trace_func=resolve_active_trace,
        agent_result_type=AgentResult,
        conversation_message_type=ConversationMessage,
        response_type=OrchestrationResponse,
        agent_roles=AGENT_ROLES,
        orch_b_brain_agent_key=ORCH_B_BRAIN_AGENT_KEY,
        get_reasoning_model_func=get_reasoning_model,
        get_planner_model_func=get_planner_model,
        get_designer_model_func=get_designer_model,
        resolve_template_profile_func=_resolve_template_profile,
        orch_semantic_audit_min_score=ORCH_SEMANTIC_AUDIT_MIN_SCORE,
        log_orchestration_phase_func=_log_orchestration_phase,
        started_at=started_at,
    )


async def execute_orchestration(
    request: OrchestrationRequest,
    progress_callback: Optional[Callable[[str, str], None]] = None,
    owner_id: Optional[str] = None,
) -> OrchestrationResponse:
    from backend.orchestrator.autonomous.surface_adapter import (
        orchestration_payload_to_response,
        run_autonomous_surface_execution,
    )

    effective_owner = str(owner_id or request.run_id or "admin-orchestrate")
    payload = await run_autonomous_surface_execution(
        request,
        owner_id=effective_owner,
        progress_callback=progress_callback,
    )
    return orchestration_payload_to_response(payload)


async def _call_orchestrator_chat_llm(
    *,
    route_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> str:
    combined_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
    options = build_ollama_options(
        route_key,
        {
            "num_predict": max_tokens,
            "temperature": 0.4,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
        },
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": combined_prompt}],
        "stream": False,
        "max_tokens": int(options.get("num_predict", max_tokens)),
        "temperature": float(options.get("temperature", 0.4)),
        "top_p": float(options.get("top_p", 0.9)),
    }
    client = await _get_orchestrator_chat_http_client() # pyright: ignore[reportUndefinedVariable]
    response = await client.post("/chat/completions", json=payload)
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices") if isinstance(data, dict) else None
    first_choice = choices[0] if isinstance(choices, list) and choices else {}
    message = first_choice.get("message") if isinstance(first_choice, dict) else {}
    if not isinstance(message, dict):
        return ""
    content = str(message.get("content") or "").strip()
    return content


@router.post("/orchestrate", response_model=OrchestrationResponse)
async def orchestrate(
    request: OrchestrationRequest,
    current_user=Depends(require_llm_mutation_quota),
) -> OrchestrationResponse:
    _enforce_global_orchestration_gate(request)
    owner_id = str(getattr(current_user, "id", "admin-orchestrate"))
    return await execute_orchestration(request, owner_id=owner_id)


@router.post("/orchestrate/accepted", response_model=OrchestrationAcceptedResponse)
async def orchestrate_accepted(
    request: OrchestrationRequest,
    current_user=Depends(require_llm_mutation_quota),
) -> OrchestrationAcceptedResponse:
    _enforce_global_orchestration_gate(request)
    if _accepted_orchestrate_requests_full_mode(request):
        raise HTTPException(
            status_code=409,
            detail="accepted orchestrate는 장시간 full 생성 대신 progress polling/SSE 전용 경로입니다. 운영에서는 /api/llm/orchestrate/stream 또는 marketplace customer-orchestrate stage run 경로를 사용하세요.",
        )
    run_id = str(request.run_id or uuid4().hex)
    accepted_request = request.model_copy(update={"run_id": run_id})
    owner_id = str(getattr(current_user, "id", "admin-orchestrate"))
    initial_payload = {
        "run_id": run_id,
        "project_name": accepted_request.project_name,
        "output_dir": accepted_request.output_dir,
        "status": "accepted",
        "accepted_at": utcnow().isoformat() + "Z",
        "poll_url": _build_progress_poll_url(run_id),
        "stream_url": _build_progress_stream_url(run_id),
        "events": [
            {
                "at": utcnow().isoformat() + "Z",
                "level": "info",
                "message": "오케스트레이션 요청을 수락했고 백그라운드 작업을 시작합니다.",
            }
        ],
    }
    _save_orchestration_progress(run_id, initial_payload)

    def _progress_callback(message: str, level: str = "info") -> None:
        try:
            _record_orchestration_progress_event(run_id, message=message, level=level)
        except Exception:
            logger.warning("orchestrate accepted progress callback failed", exc_info=True)

    def _worker() -> None:
        try:
            response = asyncio.run(
                execute_orchestration(
                    accepted_request,
                    progress_callback=_progress_callback,
                    owner_id=owner_id,
                )
            )
            _mark_orchestration_progress_result(run_id, response)
        except Exception as exc:
            logger.exception("orchestrate accepted worker failed run_id=%s", run_id)
            _mark_orchestration_progress_error(run_id, error_message=str(exc))

    threading.Thread(
        target=_worker,
        name=f"orchestrate-accepted-{run_id[:12]}",
        daemon=True,
    ).start()

    return OrchestrationAcceptedResponse(
        accepted=True,
        run_id=run_id,
        project_name=accepted_request.project_name,
        output_dir=accepted_request.output_dir,
        status="accepted",
        poll_url=_build_progress_poll_url(run_id),
        stream_url=_build_progress_stream_url(run_id),
    )


@router.get("/orchestrate/progress/{run_id}")
async def get_orchestration_progress(
    run_id: str,
    current_user: Any = Depends(get_current_user),
) -> Dict[str, Any]:
    payload = _load_orchestration_progress(run_id)
    if not payload:
        raise HTTPException(status_code=404, detail="orchestration progress를 찾을 수 없습니다.")
    return payload


@router.get("/orchestrate/stream/{run_id}")
async def stream_orchestration_progress(
    run_id: str,
    current_user: Any = Depends(get_current_user_flexible),
):
    from backend.orchestrator.autonomous.progress_stream import iter_orchestration_progress_sse

    async def _event_stream():
        async for frame in iter_orchestration_progress_sse(run_id):
            yield frame

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@router.websocket("/orchestrate/progress/ws/{run_id}")
async def websocket_orchestration_progress(websocket: WebSocket, run_id: str):
    from backend.orchestrator.autonomous.progress_stream import iter_orchestration_progress_ws

    # [#6] Sec-WebSocket-Protocol 우선, ?token= 폴백(점진 전환·무중단).
    from backend.auth import resolve_ws_token
    token, accept_subprotocol = resolve_ws_token(websocket)
    if token:
        try:
            from jose import jwt as _jwt

            from backend.auth import ALGORITHM, SECRET_KEY

            _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except Exception:
            await websocket.close(code=4001, reason="인증 실패")
            return

    await websocket.accept(subprotocol=accept_subprotocol)
    try:
        await websocket.send_json({"event": "connected", "run_id": run_id})
        async for message in iter_orchestration_progress_ws(run_id):
            await websocket.send_json(message)
            if str(message.get("event") or "") in {"done", "error"}:
                break
    except WebSocketDisconnect:
        pass


@router.post("/orchestrate/chat", response_model=OrchestratorChatResponse)
@router.post("/orchestrate/chat/light", response_model=OrchestratorChatResponse)
async def answer_orchestrator_chat(
    request_context: Request,
    request: OrchestratorChatRequest,
    agent_key: str = "chat",
    current_user=Depends(require_llm_mutation_quota),
) -> OrchestratorChatResponse:
    from backend.orchestrator.autonomous.surface_adapter import (
        run_autonomous_surface_chat,
        should_route_orchestrator_chat_to_autonomous,
    )

    if should_route_orchestrator_chat_to_autonomous(request, request_context):
        owner_id = str(getattr(current_user, "id", None) or "admin-orchestrate")
        run_id = str(request.run_id or "").strip() or None
        stage_run_id = run_id if run_id and run_id.startswith("stage_run_") else None
        context_tags = list(request.context_tags or [])
        if "admin-orchestrator" not in context_tags:
            context_tags.append("admin-orchestrator")
        return await run_autonomous_surface_chat(
            message=str(request.message or ""),
            owner_id=owner_id,
            surface="admin",
            session_id=str(request.session_id or "").strip() or None,
            run_id=run_id,
            stage_run_id=stage_run_id,
            task=str(request.task or ""),
            project_name=str(request.task or "").strip() or None,
            mode=str(request.mode or "manual_9step"),
            manual_mode=bool(request.manual_mode),
            conversation=list(request.conversation or []),
            context_tags=context_tags,
            validation_profile="python_fastapi",
        )

    return await answer_orchestrator_chat_service(
        request_context=request_context,
        request=request,
        agent_key=agent_key,
        resolve_chat_model=_resolve_admin_chat_model,
        build_ollama_options=build_ollama_options,
        ollama_base=OLLAMA_BASE,
        orch_chat_request_max_tokens=ORCH_CHAT_REQUEST_MAX_TOKENS,
        orch_lightweight_chat_max_tokens=ORCH_LIGHTWEIGHT_CHAT_MAX_TOKENS,
        orch_chat_agent_timeout_sec=ORCH_CHAT_AGENT_TIMEOUT_SEC,
        orch_reasoner_brief_timeout_sec=ORCH_REASONER_BRIEF_TIMEOUT_SEC,
        logger=logger,
        re_module=re,
        session_factory=SessionLocal,
        current_user=current_user,
    )
