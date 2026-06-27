"""단계별 코더 패치 범위 테스트."""
from __future__ import annotations

from backend.orchestrator.autonomous.stage_coder_scope import (
    build_stage_patch_task_suffix,
    get_stage_patch_scope,
    resolve_stage_patch_files,
)


def test_stage_one_bootstrap_is_small():
    files = resolve_stage_patch_files(
        stage_id="STAGE-01",
        validation_profile="python_fastapi",
    )
    assert len(files) <= 12
    assert "app/main.py" in files


def test_stage_two_patch_is_incremental():
    files = resolve_stage_patch_files(
        stage_id="STAGE-02",
        validation_profile="python_fastapi",
    )
    assert len(files) <= 6
    assert "app/core/config.py" in files


def test_patch_suffix_triggers_targeted_paths():
    files = ["app/main.py", "tests/test_health.py"]
    suffix = build_stage_patch_task_suffix("STAGE-01", files)
    assert "수정 가능 파일은" in suffix
    assert "app/main.py" in suffix


def test_patch_scope_unchanged_when_files_already_exist(tmp_path):
    """기존 파일이 있어도 스코프가 비워지지 않아 전체 템플릿 폭주를 막는다."""
    root = tmp_path / "proj"
    root.mkdir()
    for rel in get_stage_patch_scope("STAGE-04", "python_fastapi"):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# existing\n", encoding="utf-8")

    scoped = resolve_stage_patch_files(
        stage_id="STAGE-04",
        validation_profile="python_fastapi",
        output_dir=str(root),
    )
    assert len(scoped) == 3
    assert "app/core/engine.py" in scoped
