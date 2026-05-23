from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT_RELATIVE = Path("uploads") / "tmp" / "hard-gate-consistency"
RUN_STEM = "hard-gate-consistency-rerun"


def _workspace_path_from_env(env_name: str, default_relative: Path) -> Path:
    value = (os.getenv(env_name) or "").strip()
    if value:
        candidate = Path(value)
        return candidate if candidate.is_absolute() else (ROOT / candidate).resolve()
    return (ROOT / default_relative).resolve()


def hard_gate_temp_root() -> Path:
    return _workspace_path_from_env("CODEAI_HARD_GATE_TEMP_ROOT", TEMP_ROOT_RELATIVE)


def hard_gate_target_dir() -> Path:
    return _workspace_path_from_env(
        "CODEAI_HARD_GATE_TARGET_DIR",
        TEMP_ROOT_RELATIVE / RUN_STEM,
    )


def hard_gate_progress_path() -> Path:
    return _workspace_path_from_env(
        "CODEAI_HARD_GATE_PROGRESS_PATH",
        TEMP_ROOT_RELATIVE / f"{RUN_STEM}.progress.jsonl",
    )


def hard_gate_runlog_path() -> Path:
    return _workspace_path_from_env(
        "CODEAI_HARD_GATE_RUNLOG_PATH",
        TEMP_ROOT_RELATIVE / f"{RUN_STEM}.run.log",
    )


def hard_gate_result_path() -> Path:
    return _workspace_path_from_env(
        "CODEAI_HARD_GATE_RESULT_PATH",
        TEMP_ROOT_RELATIVE / "hard-gate-progress-check.result.json",
    )