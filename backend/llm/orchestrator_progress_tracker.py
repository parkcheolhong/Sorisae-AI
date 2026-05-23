from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

_ORCHESTRATION_PROGRESS_STORE: Dict[str, Dict[str, Any]] = {}


def runtime_progress_root() -> Path:
    configured_root = (os.getenv("ADMIN_RUNTIME_ROOT", "") or "").strip()
    runtime_root = Path(configured_root).expanduser().resolve() if configured_root else (Path(tempfile.gettempdir()) / "codeai_admin_runtime").resolve()
    progress_root = runtime_root / "orchestration_progress"
    progress_root.mkdir(parents=True, exist_ok=True)
    return progress_root


def orchestration_progress_path(run_id: str) -> Path:
    safe_run_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(run_id or "unknown")).strip("-") or "unknown"
    return runtime_progress_root() / f"{safe_run_id}.json"


def build_progress_poll_url(run_id: str) -> str:
    return f"/api/llm/orchestrate/progress/{run_id}"


def build_progress_stream_url(run_id: str) -> str:
    return f"/api/llm/orchestrate/stream/{run_id}"


def save_orchestration_progress(run_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    normalized["run_id"] = str(run_id or normalized.get("run_id") or "")
    normalized.setdefault("updated_at", datetime.utcnow().isoformat() + "Z")
    _ORCHESTRATION_PROGRESS_STORE[normalized["run_id"]] = normalized
    progress_path = orchestration_progress_path(normalized["run_id"])
    progress_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def load_orchestration_progress(run_id: str) -> Dict[str, Any]:
    cached = _ORCHESTRATION_PROGRESS_STORE.get(str(run_id or ""))
    if isinstance(cached, dict) and cached:
        return dict(cached)
    progress_path = orchestration_progress_path(run_id)
    try:
        if progress_path.exists() and progress_path.is_file():
            payload = json.loads(progress_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                _ORCHESTRATION_PROGRESS_STORE[str(run_id or "")] = dict(payload)
                return dict(payload)
    except Exception:
        return {}
    return {}


def record_orchestration_progress_event(run_id: str, *, message: str, level: str = "info") -> Dict[str, Any]:
    current = load_orchestration_progress(run_id)
    events = list(current.get("events") or [])
    events.append(
        {
            "at": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": str(message or "").strip(),
        }
    )
    current["events"] = events[-120:]
    current["status"] = "running"
    return save_orchestration_progress(run_id, current)


def mark_orchestration_progress_result(run_id: str, response: Any) -> Dict[str, Any]:
    payload = load_orchestration_progress(run_id)
    normalized_requirements = getattr(response, "normalized_requirements", None)
    payload.update(
        {
            "status": "completed",
            "result": response.model_dump() if hasattr(response, "model_dump") else dict(response or {}),
            "output_dir": getattr(response, "output_dir", payload.get("output_dir")),
            "project_name": normalized_requirements.get("project_name") if isinstance(normalized_requirements, dict) else payload.get("project_name"),
            "completed_at": datetime.utcnow().isoformat() + "Z",
        }
    )
    return save_orchestration_progress(run_id, payload)


def mark_orchestration_progress_error(run_id: str, *, error_message: str) -> Dict[str, Any]:
    payload = load_orchestration_progress(run_id)
    payload.update(
        {
            "status": "failed",
            "error": str(error_message or "실행 중 오류가 발생했습니다."),
            "completed_at": datetime.utcnow().isoformat() + "Z",
        }
    )
    return save_orchestration_progress(run_id, payload)
