import json

from backend import admin_router
from backend.llm import orchestrator


def test_load_runtime_config_from_disk_bootstraps_canonical_file(tmp_path, monkeypatch) -> None:
    runtime_config_path = tmp_path / "knowledge" / "orchestrator_runtime_config.json"
    monkeypatch.setattr(orchestrator, "_runtime_config_file_path", lambda: runtime_config_path)

    payload = orchestrator._load_runtime_config_from_disk()

    assert runtime_config_path.exists()
    persisted = json.loads(runtime_config_path.read_text(encoding="utf-8"))
    assert persisted["config_path"] == orchestrator.ORCH_RUNTIME_CONFIG_PATH
    assert payload["config_path"] == orchestrator.ORCH_RUNTIME_CONFIG_PATH


def test_admin_runtime_config_summary_bootstraps_missing_canonical_file(tmp_path, monkeypatch) -> None:
    runtime_config_path = tmp_path / "knowledge" / "orchestrator_runtime_config.json"
    monkeypatch.setattr(orchestrator, "_runtime_config_file_path", lambda: runtime_config_path)
    monkeypatch.setattr(admin_router, "_admin_orchestrator_runtime_config_path", lambda: runtime_config_path)
    admin_router._ADMIN_SYSTEM_SETTINGS_CACHE.clear()

    summary = admin_router._load_runtime_config_summary()

    assert runtime_config_path.exists()
    persisted = json.loads(runtime_config_path.read_text(encoding="utf-8"))
    assert summary["config_path"] == orchestrator.ORCH_RUNTIME_CONFIG_PATH
    assert persisted["config_path"] == orchestrator.ORCH_RUNTIME_CONFIG_PATH