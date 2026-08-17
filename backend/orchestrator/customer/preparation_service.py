from __future__ import annotations

from typing import Any, Dict, List


_LEGACY_REQUIRED_FILE_CANONICAL_MAP = {
    "backend/auth.py": "backend/core/auth.py",
}

_CUSTOMER_COMPAT_SAFE_GLOBAL_REQUIRED_FILES = {
    ".gitignore",
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    "Dockerfile",
    "Makefile",
    "tests/test_health.py",
}


def _normalize_customer_required_files(paths: List[str]) -> List[str]:
    normalized: List[str] = []
    for raw_path in paths:
        normalized_path = str(raw_path or "").strip().replace("\\", "/")
        if not normalized_path:
            continue
        normalized.append(_LEGACY_REQUIRED_FILE_CANONICAL_MAP.get(normalized_path, normalized_path))
    return list(dict.fromkeys(normalized))


def _merge_customer_required_files(
    orch_required_file_paths: List[str],
    profile_required_files: List[str],
    validation_profile: str,
) -> List[str]:
    normalized_profile_required_files = _normalize_customer_required_files(profile_required_files)
    if validation_profile != "python_fastapi":
        return normalized_profile_required_files

    allowed_paths = set(normalized_profile_required_files)
    allowed_paths.update(_CUSTOMER_COMPAT_SAFE_GLOBAL_REQUIRED_FILES)
    filtered_global_required_files = [
        path
        for path in _normalize_customer_required_files(list(orch_required_file_paths or []))
        if path in allowed_paths
    ]
    return _normalize_customer_required_files(filtered_global_required_files + normalized_profile_required_files)


async def prepare_customer_orchestration_context(
    request,
    *,
    normalize_requested_mode_func,
    emit_orchestration_progress_func,
    build_customer_order_profile_func,
    compat_domain_required_files_func,
    orch_required_file_paths: List[str],
    normalize_customer_requirements_func,
    build_domain_contract_func,
    build_integration_test_plan_func,
    normalize_pipeline_agents_func,
    filter_pipeline_for_validation_profile_func,
    orch_b_brain_agent_key: str,
    orchestration_spec_type,
    default_dod_targets_func,
    compat_project_name_func,
    compat_output_dir_func,
    progress_callback=None,
) -> Dict[str, Any]:
    task = str(request.task or "").strip() or "workspace self-run orchestration"
    mode = normalize_requested_mode_func(request.mode)
    emit_orchestration_progress_func(
        progress_callback,
        "오케스트레이터 호환 생성부를 준비합니다.",
    )
    order_profile = build_customer_order_profile_func(
        task,
        request.project_name or "",
    )
    validation_profile = str(
        order_profile.get("validation_profile") or "python_fastapi"
    )
    profile_required_files = compat_domain_required_files_func(
        order_profile,
        validation_profile,
    )
    compat_required_files = _merge_customer_required_files(
        list(orch_required_file_paths or []),
        profile_required_files,
        validation_profile,
    )
    normalized_requirements = normalize_customer_requirements_func(
        task,
        order_profile,
    )
    domain_contract = build_domain_contract_func(
        order_profile,
        validation_profile,
        compat_required_files,
    )
    integration_test_plan = build_integration_test_plan_func(
        order_profile,
        validation_profile,
    )
    spec = orchestration_spec_type(
        mode=mode,
        pipeline=filter_pipeline_for_validation_profile_func(
            normalize_pipeline_agents_func(
                request.pipeline or ["reasoner", "planner", orch_b_brain_agent_key]
            ),
            validation_profile,
        ),
        required_files=compat_required_files,
        validation_profile=validation_profile,
        dod_targets=default_dod_targets_func(validation_profile),
        reasoning="compat orchestration runner",
        spec_source="compat",
        fallback_reason="compat_runner",
    )
    project_name = compat_project_name_func(request)
    output_dir = compat_output_dir_func(request, project_name)
    return {
        "task": task,
        "mode": mode,
        "order_profile": order_profile,
        "validation_profile": validation_profile,
        "compat_required_files": compat_required_files,
        "normalized_requirements": normalized_requirements,
        "domain_contract": domain_contract,
        "integration_test_plan": integration_test_plan,
        "spec": spec,
        "project_name": project_name,
        "output_dir": output_dir,
    }
