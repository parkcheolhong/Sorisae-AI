"""Append lightweight autonomous run snapshots for knowledge/runs flywheel."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def append_autonomous_run_snapshot(
    *,
    session_id: str,
    surface: str,
    execution_state: str,
    stages_completed: int,
    runnable_proof: Optional[Dict[str, Any]] = None,
    task: str = "",
) -> Optional[str]:
    runs_dir = _workspace_root() / "knowledge" / "runs"
    try:
        runs_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = runs_dir / f"autonomous_surface_{stamp}.jsonl"
    record = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "surface": surface,
        "execution_state": execution_state,
        "stages_completed": stages_completed,
        "task_preview": str(task or "")[:240],
        "runnable_proof_ok": bool((runnable_proof or {}).get("ok")),
        "runnable_proof_detail": str((runnable_proof or {}).get("detail") or "")[:400],
    }
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        return None
    return str(path)
