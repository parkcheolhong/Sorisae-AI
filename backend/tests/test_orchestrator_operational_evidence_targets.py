from backend.llm.orchestrator import (
    _resolve_operational_evidence_probe_config,
    _resolve_operational_evidence_target_defaults,
)


def test_commerce_platform_operational_evidence_scope_is_customer_specific() -> None:
    targets = _resolve_operational_evidence_target_defaults("commerce_platform")

    assert [item["id"] for item in targets] == [
        "marketplace",
        "system_settings",
        "workspace_self_run_record",
    ]


def test_default_operational_evidence_scope_keeps_full_runtime_probe_set() -> None:
    targets = _resolve_operational_evidence_target_defaults(None)

    assert [item["id"] for item in targets] == [
        "websocket",
        "admin",
        "marketplace",
        "system_settings",
        "workspace_self_run_record",
    ]


def test_operational_evidence_probe_config_prefers_internal_gateway(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PROBE_BASE_URL", "https://nginx")
    monkeypatch.setenv("ADMIN_PROBE_HOST", "metanova1004.com")
    monkeypatch.delenv("OPERATIONAL_EVIDENCE_ADMIN_URL", raising=False)
    monkeypatch.delenv("OPERATIONAL_EVIDENCE_MARKETPLACE_URL", raising=False)

    probe_config = _resolve_operational_evidence_probe_config()

    assert probe_config["probe_urls"]["admin"] == "https://nginx/admin/llm"
    assert probe_config["probe_urls"]["marketplace"] == "https://nginx/marketplace/orchestrator"
    assert probe_config["public_headers"] == {"Host": "metanova1004.com"}
