from backend.admin_router import (
    _resolve_admin_available_models,
    _resolve_admin_summary_display_values,
)


def test_resolve_admin_available_models_merges_configured_routes():
    models = _resolve_admin_available_models(
        {
            "models": ["Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"],
            "configured_models": {
                "default": "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ",
                "coder": "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ",
            },
        }
    )
    assert "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ" in models
    assert "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ" in models


def test_resolve_admin_summary_display_values_uses_fallbacks():
    display = _resolve_admin_summary_display_values(
        {
            "DOMAIN_NAME": "validation.local",
            "LOCAL_API_BASE_URL": "",
            "MARKETPLACE_HOST_ROOT": "",
        }
    )
    assert display["admin_domain"] == "validation.local"
    assert display["local_api_base_url"] == "http://127.0.0.1:8000"
    assert display["marketplace_host_root"] == "./uploads"


def test_compute_recommended_env_defaults_fills_empty_llm_keys():
    from backend.admin_router import _compute_recommended_env_defaults

    recommended = _compute_recommended_env_defaults(
        {"LLM_MODEL_DEFAULT": "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"},
        {"model_routes": {"reasoning": "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ", "default": "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"}, "min_files": 9, "min_dirs": 3},
    )
    assert recommended["LLM_MODEL_REASONING"] == "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
    assert recommended["ORCH_MIN_FILES"] == "9"


def test_build_admin_integration_checks_structure():
    from backend.admin_router import _build_admin_integration_checks

    checks = _build_admin_integration_checks(
        {"OLLAMA_BASE": "http://127.0.0.1:8008/v1", "DATABASE_URL": "postgresql://admin@postgres:5432/devanalysis114", "POSTGRES_HOST": "postgres"},
        {"local_api_base_url": "http://127.0.0.1:8000", "marketplace_host_root": "./uploads", "marketplace_upload_root": "./uploads", "admin_domain": "metanova1004.com"},
        {"min_files": 9, "min_dirs": 3},
        ["Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"],
    )
    assert checks["total_count"] >= 6
    assert any(item["id"] == "swagger_docs" for item in checks["items"])
