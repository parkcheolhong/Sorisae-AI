import json

from backend import tmp_hard_gate_paths
from backend.tools import backfill_generated_artifacts


def _normalized(path) -> str:
    return str(path).replace("\\", "/")


def test_hard_gate_temp_paths_default_outside_projects(monkeypatch) -> None:
    for env_name in [
        "CODEAI_HARD_GATE_TEMP_ROOT",
        "CODEAI_HARD_GATE_TARGET_DIR",
        "CODEAI_HARD_GATE_PROGRESS_PATH",
        "CODEAI_HARD_GATE_RUNLOG_PATH",
        "CODEAI_HARD_GATE_RESULT_PATH",
    ]:
        monkeypatch.delenv(env_name, raising=False)

    temp_root = tmp_hard_gate_paths.hard_gate_temp_root()
    target_dir = tmp_hard_gate_paths.hard_gate_target_dir()
    progress_path = tmp_hard_gate_paths.hard_gate_progress_path()
    result_path = tmp_hard_gate_paths.hard_gate_result_path()

    assert "/uploads/projects/" not in f"/{_normalized(temp_root)}/"
    assert _normalized(temp_root).endswith("uploads/tmp/hard-gate-consistency")
    assert target_dir.parent == temp_root
    assert progress_path.parent == temp_root
    assert result_path.parent == temp_root


def test_discover_backfill_targets_from_live_project_root(tmp_path, monkeypatch) -> None:
    valid_alpha = tmp_path / "uploads" / "projects" / "alpha"
    valid_alpha.mkdir(parents=True)
    (valid_alpha / ".codeai-template.json").write_text(json.dumps({"project_name": "alpha"}), encoding="utf-8")
    (valid_alpha / "docs").mkdir()
    (valid_alpha / "docs" / "traceability_map.json").write_text(json.dumps({"written_files": []}), encoding="utf-8")

    invalid_missing_traceability = tmp_path / "uploads" / "projects" / "invalid"
    invalid_missing_traceability.mkdir(parents=True)
    (invalid_missing_traceability / ".codeai-template.json").write_text("{}", encoding="utf-8")

    valid_beta = tmp_path / "uploads" / "projects" / "beta"
    valid_beta.mkdir(parents=True)
    (valid_beta / ".codeai-template.json").write_text(json.dumps({"project_name": "beta"}), encoding="utf-8")
    (valid_beta / "docs").mkdir()
    (valid_beta / "docs" / "traceability_map.json").write_text(json.dumps({"written_files": []}), encoding="utf-8")

    monkeypatch.setattr(backfill_generated_artifacts, "ROOT", tmp_path)

    targets = backfill_generated_artifacts.discover_backfill_targets()

    assert targets == ["uploads/projects/alpha", "uploads/projects/beta"]