from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict

from backend.admin.orchestrator.runtime_verification_service import (
    build_runtime_verification_response,
)


def build_admin_runtime_verification_response(
    *,
    db: Any,
    project_root: Path,
    worker_log_path: str,
    mode: str,
    bearer_token: str,
    classify_gate_status: Callable[[list[Dict[str, Any]]], Dict[str, Any]],
    read_admin_env_values: Callable[[Path], Dict[str, str]],
    admin_env_path: Callable[[], Path],
) -> Dict[str, Any]:
    return build_runtime_verification_response(
        db=db,
        project_root=project_root,
        worker_log_path=worker_log_path,
        mode=mode,
        bearer_token=bearer_token,
        classify_gate_status=classify_gate_status,
        read_admin_env_values=read_admin_env_values,
        admin_env_path=admin_env_path,
    )
