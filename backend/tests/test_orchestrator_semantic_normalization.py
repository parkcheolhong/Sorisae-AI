from backend.llm.orchestrator import (
    _build_customer_order_profile,
    _build_customer_order_template_candidates,
    _compat_validate_profile_alignment,
    _compat_validate_implementation_normalization,
    _resolve_customer_common_required_files,
)


def test_implementation_normalization_rejects_document_writer_thin_shell() -> None:
    order_profile = {
        "ai_enabled": True,
        "profile_id": "document_writer_suite",
    }
    manifest_lookup = {
        "docs/order_profile.md": "## implementation_normalization\n\n## expansion_targets\n",
        "docs/scaffold_inventory.md": "## implementation_normalization\n\n## expansion_targets\n",
        "backend/service/strategy_service.py": "def build_strategy_service_overview():\n    return {'document_id': 'DOC-01'}\n",
        "app/services/runtime_service.py": "def build_runtime_payload():\n    return {'evaluation_report': {}}\n",
        "ai/router.py": "from ai.schemas import InferenceRequest\n",
    }

    findings = _compat_validate_implementation_normalization(
        order_profile,
        manifest_lookup,
        "python_fastapi",
    )

    assert any("document lifecycle state" in finding for finding in findings)
    assert any("document typed AI router" in finding for finding in findings)


def test_implementation_normalization_accepts_trading_profile_markers() -> None:
    order_profile = {
        "ai_enabled": True,
        "profile_id": "trading_system",
    }
    manifest_lookup = {
        "docs/order_profile.md": "## implementation_normalization\n\n## expansion_targets\n",
        "docs/scaffold_inventory.md": "## implementation_normalization\n\n## expansion_targets\n",
        "backend/service/strategy_service.py": (
            "def build_risk_guard():\n    return {'risk-guard': True}\n\n"
            "def build_order_execution_plan():\n    return {'order-execution': True}\n\n"
            "def build_portfolio_sync():\n    return {'portfolio-sync': True}\n\n"
            "market_regime = 'bull'\n"
            "risk_score = 0.2\n"
        ),
        "backend/app/connectors/broker.py": (
            "def _provider_specific_missing():\n    return []\n\n"
            "BROKER_LIVE_ACK_TOKEN = 'LIVE_TRADING_ENABLED'\n"
            "provider_contracts = {'alpaca': True}\n"
            "message = 'live broker configuration incomplete'\n"
        ),
        "app/services/runtime_service.py": (
            "DOMAIN_RECORD_KEY = 'signals'\n\n"
            "def build_runtime_payload():\n    return {'ai_runtime_contract': True}\n"
        ),
    }

    findings = _compat_validate_implementation_normalization(
        order_profile,
        manifest_lookup,
        "python_fastapi",
    )

    assert findings == []


def test_common_required_files_include_frontend_runtime_surface() -> None:
    required_files = _resolve_customer_common_required_files()

    assert "frontend/app/page.tsx" in required_files


def test_multimall_profile_wins_over_generic_commerce_keywords() -> None:
    profile = _build_customer_order_profile(
        "AI 엔진 자율운영 멀티 쇼핑몰 프로그램을 실프로젝트 구조로 생성하고 tenant 운영, 카탈로그 동기화, 캠페인 최적화, fulfillment 감독을 포함해줘",
        "AI Multimall Regen Check V1",
    )

    assert profile["profile_id"] == "autonomous_multimall_platform"


def test_non_commerce_ai_auth_routes_expose_settings_endpoint() -> None:
    order_profile = _build_customer_order_profile(
        "AI 엔진 자동 로또 생성기 프로그램을 실프로젝트 구조로 생성하고 추첨 이력, 후보 번호 생성, 평가 리포트를 포함해줘",
        "AI Lottery Regen Check V1",
    )

    templates = _build_customer_order_template_candidates(
        "AI Lottery Regen Check V1",
        "AI 엔진 자동 로또 생성기 프로그램을 실프로젝트 구조로 생성하고 추첨 이력, 후보 번호 생성, 평가 리포트를 포함해줘",
        order_profile,
    )

    auth_routes = templates["app/auth_routes.py"]
    assert "@auth_router.get('/settings')" in auth_routes
    assert "os.getenv('JWT_SECRET', '').strip()" in templates["backend/core/auth.py"]


def test_multimall_profile_alignment_accepts_multimall_context() -> None:
    task = "AI 엔진 자율운영 멀티 쇼핑몰 프로그램을 실프로젝트 구조로 생성하고 tenant 운영, 카탈로그 동기화, 캠페인 최적화, fulfillment 감독을 포함해줘"
    profile = _build_customer_order_profile(task, "AI Multimall Regen Check V1")

    findings = _compat_validate_profile_alignment(
        task,
        "AI Multimall Regen Check V1",
        profile,
    )

    assert findings == []


def test_workspace_app_context_does_not_override_trading_keyword_profile() -> None:
    profile = _build_customer_order_profile(
        "source_path: /app\nAI 엔진 주식 자동매매 프로그램 생성",
        "stock-ai-autotrader",
    )

    assert profile["profile_id"] == "trading_system"


def test_customer_profile_defaults_to_ai_enabled_unless_explicitly_disabled() -> None:
    profile = _build_customer_order_profile(
        "간단한 내부 운영 프로그램 생성",
        "internal-ops",
    )

    assert profile["ai_enabled"] is True
    assert profile["ai_engine_core"] == "sorisae"


def test_commerce_template_check_script_contains_semantic_gate_markers() -> None:
    order_profile = _build_customer_order_profile(
        "AI 엔진 마켓플레이스 주문형 프로그램 생성",
        "commerce-ai-runtime",
    )

    templates = _build_customer_order_template_candidates(
        "commerce-ai-runtime",
        "AI 엔진 마켓플레이스 주문형 프로그램 생성",
        order_profile,
    )

    check_script = templates["scripts/check.sh"]
    assert "test -f requirements.delivery.lock.txt" in check_script
    assert "pytest -q -s" in check_script