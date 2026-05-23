import asyncio
from types import SimpleNamespace

from backend.llm.orchestrator import (
    _build_customer_order_profile,
    _build_domain_contract,
    _build_integration_test_plan,
    _compat_domain_required_files,
    _default_dod_targets,
    _filter_pipeline_for_validation_profile,
    _normalize_customer_requirements,
    _normalize_pipeline_agents,
)
from backend.orchestrator.customer.preparation_service import prepare_customer_orchestration_context


def test_prepare_customer_orchestration_context_canonicalizes_legacy_auth_required_path() -> None:
    request = SimpleNamespace(task="고객 생성", mode="full", project_name="demo", pipeline=None)

    result = asyncio.run(
        prepare_customer_orchestration_context(
            request,
            normalize_requested_mode_func=lambda mode: mode,
            emit_orchestration_progress_func=lambda *args, **kwargs: None,
            build_customer_order_profile_func=lambda task, project_name: {
                "profile_id": "customer_program",
                "validation_profile": "python_fastapi",
            },
            compat_domain_required_files_func=lambda order_profile, validation_profile: [
                "backend/core/auth.py",
                "app/main.py",
                "tests/test_health.py",
            ],
            orch_required_file_paths=[
                "backend/auth.py",
                "README.md",
                "frontend/frontend/app/admin/page.tsx",
                "knowledge/orchestrator_runtime_config.json",
            ],
            normalize_customer_requirements_func=lambda task, order_profile: {"task": task},
            build_domain_contract_func=lambda order_profile, validation_profile, required_files: {"required_files": required_files},
            build_integration_test_plan_func=lambda order_profile, validation_profile: {},
            normalize_pipeline_agents_func=lambda pipeline: list(pipeline),
            filter_pipeline_for_validation_profile_func=lambda pipeline, validation_profile: list(pipeline),
            orch_b_brain_agent_key="b_brain",
            orchestration_spec_type=lambda **kwargs: SimpleNamespace(**kwargs),
            default_dod_targets_func=lambda validation_profile: [],
            compat_project_name_func=lambda request: "demo",
            compat_output_dir_func=lambda request, project_name: "/tmp/demo",
        )
    )

    assert "backend/auth.py" not in result["compat_required_files"]
    assert result["compat_required_files"].count("backend/core/auth.py") == 1
    assert "frontend/frontend/app/admin/page.tsx" not in result["compat_required_files"]
    assert "knowledge/orchestrator_runtime_config.json" not in result["compat_required_files"]
    assert "README.md" in result["compat_required_files"]


def test_prepare_customer_orchestration_context_preserves_multimall_generation_contract() -> None:
    task = "AI 엔진 자율운영 멀티 쇼핑몰 프로그램을 실프로젝트 구조로 생성하고 tenant 운영, 카탈로그 동기화, 캠페인 최적화, fulfillment 감독을 포함해줘"
    request = SimpleNamespace(
        task=task,
        mode="full",
        project_name="AI Multimall Regen Check V1",
        pipeline=["reasoner", "planner", "designer", "b_brain"],
    )

    result = asyncio.run(
        prepare_customer_orchestration_context(
            request,
            normalize_requested_mode_func=lambda mode: mode,
            emit_orchestration_progress_func=lambda *args, **kwargs: None,
            build_customer_order_profile_func=_build_customer_order_profile,
            compat_domain_required_files_func=_compat_domain_required_files,
            orch_required_file_paths=[],
            normalize_customer_requirements_func=_normalize_customer_requirements,
            build_domain_contract_func=_build_domain_contract,
            build_integration_test_plan_func=_build_integration_test_plan,
            normalize_pipeline_agents_func=_normalize_pipeline_agents,
            filter_pipeline_for_validation_profile_func=_filter_pipeline_for_validation_profile,
            orch_b_brain_agent_key="b_brain",
            orchestration_spec_type=lambda **kwargs: SimpleNamespace(**kwargs),
            default_dod_targets_func=_default_dod_targets,
            compat_project_name_func=lambda request: request.project_name,
            compat_output_dir_func=lambda request, project_name: f"/tmp/{project_name}",
        )
    )

    assert result["order_profile"]["profile_id"] == "autonomous_multimall_platform"
    assert result["order_profile"]["ai_enabled"] is True
    assert result["validation_profile"] == "python_fastapi"
    assert "backend/app/connectors/shopify.py" in result["compat_required_files"]
    assert "tests/test_ai_pipeline.py" in result["compat_required_files"]
    assert result["domain_contract"]["profile_id"] == "autonomous_multimall_platform"
    assert "tenant operations" in result["domain_contract"]["required_structure"]
    assert "fulfillment supervision" in result["domain_contract"]["required_structure"]
    assert "catalog flow" in result["integration_test_plan"]["runtime_checks"]
    assert "marketplace publish payload" in result["integration_test_plan"]["runtime_checks"]
    assert result["spec"].validation_profile == "python_fastapi"
