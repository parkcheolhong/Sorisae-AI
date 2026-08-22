from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy.orm import Session
from backend.time_utils import utcnow

if TYPE_CHECKING:
    from backend.models import User
    from backend.admin.program_registry_models import (
        AdminProgramRegistryApproveRequest,
        AdminProgramRegistryCheckRunRequest,
        AdminProgramRegistryRollbackRequest,
        AdminProgramRegistryStatusUpdateRequest,
    )

__all__ = [
    "load_admin_program_registry_rows",
    "load_admin_program_registry_row",
    "save_admin_program_registry_row",
    "serialize_admin_program_registry_summary_item",
    "serialize_admin_program_registry_artifact",
    "serialize_admin_program_registry_check",
    "build_admin_program_registry_state_payload",
    "build_admin_program_registry_detail_payload",
    "build_admin_program_registry_builds_payload",
    "build_admin_program_registry_deployments_payload",
    "build_admin_program_registry_checks_payload",
    "build_admin_program_registry_artifacts_payload",
    "build_admin_program_registry_docs_payload",
    "build_admin_program_registry_check_run_payload",
    "build_admin_program_registry_approve_payload",
    "build_admin_program_registry_rollback_payload",
]


_PROGRAM_REGISTRY_STORE: Dict[str, Dict[str, Any]] = {
    "core-admin": {
        "program_id": "core-admin",
        "program_key": "core-admin",
        "program_name": "Core Admin",
        "program_type": "service",
        "primary_domain": "http://127.0.0.1:3005",
        "admin_domain": "http://127.0.0.1:3005/admin",
        "api_base_url": "http://127.0.0.1:8000",
        "target_platform": "web",
        "build_status": "ready",
        "deploy_status": "deployed",
        "verification_status": "verified",
        "latest_version": "0.1.0",
        "latest_build_id": "build-core-admin-001",
        "latest_release_channel": "stable",
        "owner_team": "platform",
        "operator_notes": "bootstrap record",
        "docs_links": [{"label": "registry-design", "url": "docs/checklists/admin-program-registry-design.md"}],
        "builds": [{"build_id": "build-core-admin-001", "status": "ready"}],
        "deployments": [{"deployment_id": "dep-core-admin-001", "status": "deployed"}],
        "checks": [{"check_id": "chk-core-admin-001", "check_name": "bootstrap-check", "check_type": "runtime", "check_status": "verified"}],
        "artifacts": [{"artifact_id": "art-core-admin-001", "artifact_name": "core-admin.zip", "artifact_type": "binary"}],
        "updated_at": utcnow().isoformat() + "Z",
    }
}


def _touch_updated_at(row: Dict[str, Any]) -> None:
    row["updated_at"] = utcnow().isoformat() + "Z"


def load_admin_program_registry_rows(db: Session) -> List[Any]:
    """모든 프로그램 레지스트리 row 목록을 조회한다."""
    return [deepcopy(item) for item in _PROGRAM_REGISTRY_STORE.values()]


def load_admin_program_registry_row(db: Session, program_id: str) -> Optional[Any]:
    """주어진 program_id 기준으로 단일 프로그램 row를 조회한다."""
    key = str(program_id or "").strip()
    if not key:
        return None
    row = _PROGRAM_REGISTRY_STORE.get(key)
    return deepcopy(row) if isinstance(row, dict) else None


def save_admin_program_registry_row(
    *,
    db: Session,
    program_id: str,
    payload: "AdminProgramRegistryStatusUpdateRequest",
    admin: Optional["User"] = None,
) -> Any:
    """program 레지스트리 상태/메타 정보를 저장한다."""
    key = str(program_id or "").strip()
    row = _PROGRAM_REGISTRY_STORE.get(key)
    if not isinstance(row, dict):
        return None

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        row[field] = value
    _touch_updated_at(row)
    _PROGRAM_REGISTRY_STORE[key] = row
    return deepcopy(row)


def serialize_admin_program_registry_summary_item(row: Any) -> Dict[str, Any]:
    """목록 summary에 사용되는 dict를 반환한다."""
    item = dict(row or {})
    return {
        "program_id": str(item.get("program_id") or ""),
        "program_key": str(item.get("program_key") or item.get("program_id") or ""),
        "program_name": str(item.get("program_name") or item.get("program_id") or "unknown"),
        "program_type": str(item.get("program_type") or "app"),
        "build_status": str(item.get("build_status") or "pending"),
        "deploy_status": str(item.get("deploy_status") or "pending"),
        "verification_status": str(item.get("verification_status") or "pending"),
        "latest_version": str(item.get("latest_version") or "0.0.0"),
        "latest_build_id": item.get("latest_build_id"),
        "latest_release_channel": str(item.get("latest_release_channel") or "stable"),
        "owner_team": item.get("owner_team"),
        "primary_domain": item.get("primary_domain"),
        "admin_domain": item.get("admin_domain"),
        "updated_at": item.get("updated_at"),
    }


def serialize_admin_program_registry_artifact(item: Any) -> Dict[str, Any]:
    """산출물 item을 API 응답 dict로 직렬화한다."""
    data = dict(item or {})
    return {
        "artifact_id": str(data.get("artifact_id") or ""),
        "program_id": str(data.get("program_id") or ""),
        "artifact_name": str(data.get("artifact_name") or "artifact"),
        "artifact_type": str(data.get("artifact_type") or "binary"),
        "artifact_path": data.get("artifact_path"),
        "created_at": data.get("created_at"),
        "size_bytes": data.get("size_bytes"),
        "checksum": data.get("checksum"),
    }


def serialize_admin_program_registry_check(item: Any) -> Dict[str, Any]:
    """검증 기록 item을 API 응답 dict로 직렬화한다."""
    data = dict(item or {})
    return {
        "check_id": str(data.get("check_id") or ""),
        "program_id": str(data.get("program_id") or ""),
        "check_name": str(data.get("check_name") or "check"),
        "check_type": str(data.get("check_type") or "runtime"),
        "check_status": str(data.get("check_status") or "pending"),
        "started_at": data.get("started_at"),
        "finished_at": data.get("finished_at"),
        "result_summary": data.get("result_summary"),
        "detail_url": data.get("detail_url"),
    }


def build_admin_program_registry_state_payload(
    *,
    db: Session,
    rows: Optional[List[Any]] = None,
    items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """StateResponse용 전체 payload를 조립한다."""
    row_items = rows if isinstance(rows, list) else load_admin_program_registry_rows(db)
    summary_items = items if isinstance(items, list) else [serialize_admin_program_registry_summary_item(row) for row in row_items]
    summary = {
        "total": len(summary_items),
        "pending": sum(1 for item in summary_items if str(item.get("verification_status") or "") == "pending"),
        "verified": sum(1 for item in summary_items if str(item.get("verification_status") or "") == "verified"),
    }
    return {
        "items": summary_items,
        "total_count": len(summary_items),
        "active_filter": "all",
        "summary": summary,
        "updated_at": utcnow().isoformat() + "Z",
    }


def build_admin_program_registry_detail_payload(
    *,
    db: Session,
    program_id: str,
    row: Optional[Any] = None,
) -> Dict[str, Any]:
    """DetailResponse용 상세 payload를 조립한다."""
    current = row if isinstance(row, dict) else load_admin_program_registry_row(db, program_id)
    data = dict(current or {})
    return {
        "program_id": str(data.get("program_id") or program_id),
        "program_key": str(data.get("program_key") or data.get("program_id") or program_id),
        "program_name": str(data.get("program_name") or data.get("program_id") or "unknown"),
        "program_type": str(data.get("program_type") or "app"),
        "primary_domain": data.get("primary_domain"),
        "admin_domain": data.get("admin_domain"),
        "api_base_url": data.get("api_base_url"),
        "target_platform": data.get("target_platform"),
        "build_status": str(data.get("build_status") or "pending"),
        "deploy_status": str(data.get("deploy_status") or "pending"),
        "verification_status": str(data.get("verification_status") or "pending"),
        "latest_version": str(data.get("latest_version") or "0.0.0"),
        "latest_build_id": data.get("latest_build_id"),
        "latest_release_channel": str(data.get("latest_release_channel") or "stable"),
        "owner_team": data.get("owner_team"),
        "operator_notes": data.get("operator_notes"),
        "docs_links": list(data.get("docs_links") or []),
        "builds": list(data.get("builds") or []),
        "deployments": list(data.get("deployments") or []),
        "checks": list(data.get("checks") or []),
        "artifacts": list(data.get("artifacts") or []),
        "updated_at": data.get("updated_at") or utcnow().isoformat() + "Z",
    }


def build_admin_program_registry_builds_payload(
    *,
    db: Session,
    program_id: str,
) -> List[Dict[str, Any]]:
    """빌드 히스토리 목록을 조립한다."""
    row = load_admin_program_registry_row(db, program_id) or {}
    return [dict(item) for item in list(row.get("builds") or [])]


def build_admin_program_registry_deployments_payload(
    *,
    db: Session,
    program_id: str,
) -> List[Dict[str, Any]]:
    """배포 히스토리 목록을 조립한다."""
    row = load_admin_program_registry_row(db, program_id) or {}
    return [dict(item) for item in list(row.get("deployments") or [])]


def build_admin_program_registry_checks_payload(
    *,
    db: Session,
    program_id: str,
) -> List[Dict[str, Any]]:
    """검증 기록 목록을 조립한다."""
    row = load_admin_program_registry_row(db, program_id) or {}
    checks = []
    for item in list(row.get("checks") or []):
        normalized = serialize_admin_program_registry_check(item)
        if not normalized.get("program_id"):
            normalized["program_id"] = str(program_id)
        checks.append(normalized)
    return checks


def build_admin_program_registry_artifacts_payload(
    *,
    db: Session,
    program_id: str,
) -> List[Dict[str, Any]]:
    """산출물 목록을 조립한다."""
    row = load_admin_program_registry_row(db, program_id) or {}
    artifacts = []
    for item in list(row.get("artifacts") or []):
        normalized = serialize_admin_program_registry_artifact(item)
        if not normalized.get("program_id"):
            normalized["program_id"] = str(program_id)
        artifacts.append(normalized)
    return artifacts


def build_admin_program_registry_docs_payload(
    *,
    db: Session,
    program_id: str,
) -> List[Dict[str, str]]:
    """문서 링크 목록을 조립한다."""
    row = load_admin_program_registry_row(db, program_id) or {}
    docs = []
    for item in list(row.get("docs_links") or []):
        data = dict(item or {})
        docs.append({
            "label": str(data.get("label") or "doc"),
            "url": str(data.get("url") or ""),
        })
    return docs


def build_admin_program_registry_check_run_payload(
    *,
    db: Session,
    program_id: str,
    payload: "AdminProgramRegistryCheckRunRequest",
    admin: Optional["User"] = None,
) -> Dict[str, Any]:
    """검증 실행 결과 payload를 조립한다."""
    _ = payload
    _ = admin
    return {
        "build_status": "ready",
        "verification_status": "pending",
        "updated_at": utcnow().isoformat() + "Z",
    }


def build_admin_program_registry_approve_payload(
    *,
    db: Session,
    program_id: str,
    payload: "AdminProgramRegistryApproveRequest",
    admin: Optional["User"] = None,
) -> Dict[str, Any]:
    """승인 처리 payload를 조립한다."""
    _ = payload
    _ = admin
    return {
        "deploy_status": "deployed",
        "verification_status": "verified",
        "updated_at": utcnow().isoformat() + "Z",
    }


def build_admin_program_registry_rollback_payload(
    *,
    db: Session,
    program_id: str,
    payload: "AdminProgramRegistryRollbackRequest",
    admin: Optional["User"] = None,
) -> Dict[str, Any]:
    """롤백 처리 payload를 조립한다."""
    _ = payload
    _ = admin
    return {
        "deploy_status": "pending",
        "verification_status": "pending",
        "updated_at": utcnow().isoformat() + "Z",
    }
