from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from backend.admin.program_registry_models import (
    AdminProgramRegistryApproveRequest,
    AdminProgramRegistryCheckRunRequest,
    AdminProgramRegistryRollbackRequest,
    AdminProgramRegistryStatusUpdateRequest,
)

VALID_PROGRAM_STATUSES = {
    "pending",
    "building",
    "build_failed",
    "ready",
    "deploying",
    "deployed",
    "deploy_failed",
    "verifying",
    "verified",
    "verification_failed",
    "blocked",
    "archived",
}

VALID_PROGRAM_TYPES = {
    "app",
    "service",
    "worker",
    "gateway",
    "tool",
    "package",
}


def _normalize_status(value: Optional[str], *, field_name: str, fallback: str = "pending") -> str:
    text = str(value or "").strip().lower()
    if not text:
        return fallback
    if text not in VALID_PROGRAM_STATUSES:
        raise ValueError(f"{field_name} must be one of: {sorted(VALID_PROGRAM_STATUSES)}")
    return text


def _normalize_program_type(value: Optional[str], *, fallback: str = "app") -> str:
    text = str(value or "").strip().lower()
    if not text:
        return fallback
    if text not in VALID_PROGRAM_TYPES:
        raise ValueError(f"program_type must be one of: {sorted(VALID_PROGRAM_TYPES)}")
    return text


def validate_program_id(program_id: str) -> str:
    text = str(program_id or "").strip()
    if not text:
        raise ValueError("program_id is required")
    return text


def validate_program_key(program_key: Optional[str]) -> Optional[str]:
    if program_key is None:
        return None
    text = str(program_key).strip()
    if not text:
        raise ValueError("program_key cannot be blank")
    return text


def validate_program_registry_status_update_payload(
    payload: AdminProgramRegistryStatusUpdateRequest,
) -> AdminProgramRegistryStatusUpdateRequest:
    if payload.build_status is not None:
        payload.build_status = _normalize_status(payload.build_status, field_name="build_status")
    if payload.deploy_status is not None:
        payload.deploy_status = _normalize_status(payload.deploy_status, field_name="deploy_status")
    if payload.verification_status is not None:
        payload.verification_status = _normalize_status(payload.verification_status, field_name="verification_status")
    if payload.program_type is not None:
        payload.program_type = _normalize_program_type(payload.program_type)
    if payload.primary_domain is not None:
        payload.primary_domain = str(payload.primary_domain).strip() or None
    if payload.admin_domain is not None:
        payload.admin_domain = str(payload.admin_domain).strip() or None
    if payload.api_base_url is not None:
        payload.api_base_url = str(payload.api_base_url).strip() or None
    if payload.target_platform is not None:
        payload.target_platform = str(payload.target_platform).strip() or None
    if payload.operator_notes is not None:
        payload.operator_notes = str(payload.operator_notes).strip() or None
    if payload.owner_team is not None:
        payload.owner_team = str(payload.owner_team).strip() or None
    return payload


def validate_program_registry_check_run_payload(
    payload: AdminProgramRegistryCheckRunRequest,
) -> AdminProgramRegistryCheckRunRequest:
    payload.check_name = str(payload.check_name or "").strip()
    if not payload.check_name:
        raise ValueError("check_name is required")
    payload.check_type = str(payload.check_type or "runtime").strip().lower()
    payload.target_environment = str(payload.target_environment or "staging").strip().lower()
    return payload


def validate_program_registry_approve_payload(
    payload: AdminProgramRegistryApproveRequest,
) -> AdminProgramRegistryApproveRequest:
    payload.approved_version = str(payload.approved_version or "").strip()
    if not payload.approved_version:
        raise ValueError("approved_version is required")
    payload.approval_note = str(payload.approval_note).strip() if payload.approval_note is not None else None
    payload.approved_by = str(payload.approved_by).strip() if payload.approved_by is not None else None
    return payload


def validate_program_registry_rollback_payload(
    payload: AdminProgramRegistryRollbackRequest,
) -> AdminProgramRegistryRollbackRequest:
    payload.target_version = str(payload.target_version or "").strip()
    if not payload.target_version:
        raise ValueError("target_version is required")
    if payload.confirm is not True:
        raise ValueError("rollback confirmation is required")
    payload.reason = str(payload.reason).strip() if payload.reason is not None else None
    return payload


def validate_program_registry_route_context(
    *,
    program_id: Optional[str] = None,
    payload: Optional[Any] = None,
) -> Dict[str, Any]:
    """라우트 진입 전에 허용된 program_id/payload 조합을 검증한다."""
    normalized_program_id = validate_program_id(program_id) if program_id is not None else None
    return {
        "program_id": normalized_program_id,
        "payload": payload,
    }


__all__ = [
    "VALID_PROGRAM_STATUSES",
    "VALID_PROGRAM_TYPES",
    "validate_program_id",
    "validate_program_key",
    "validate_program_registry_status_update_payload",
    "validate_program_registry_check_run_payload",
    "validate_program_registry_approve_payload",
    "validate_program_registry_rollback_payload",
    "validate_program_registry_route_context",
]
