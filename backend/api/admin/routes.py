from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.admin_router import (
    _admin_env_path,
    _classify_gate_status,
    _read_admin_env_values,
    require_admin,
)
from backend.admin.orchestrator.project_root_service import resolve_admin_project_root
from backend.api.admin.schemas import (
    AdminRuntimeVerificationRequest,
    AdminRuntimeVerificationResponse,
)
from backend.application.admin.runtime_verification_service import (
    build_admin_runtime_verification_response,
)
from backend.database import get_db
from backend.models import User

router = APIRouter(tags=["admin-refactor"])


@router.post(
    "/orchestrator/runtime-verification",
    response_model=AdminRuntimeVerificationResponse,
)
def run_admin_orchestrator_runtime_verification_v2(
    payload: AdminRuntimeVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    project_root = resolve_admin_project_root(payload.project_root, allow_workspace_default=True)
    del admin
    return build_admin_runtime_verification_response(
        db=db,
        project_root=project_root,
        worker_log_path=payload.worker_log_path,
        mode=payload.mode,
        bearer_token=str(request.headers.get("authorization") or "").replace("Bearer ", "").strip(),
        classify_gate_status=_classify_gate_status,
        read_admin_env_values=_read_admin_env_values,
        admin_env_path=_admin_env_path,
    )
