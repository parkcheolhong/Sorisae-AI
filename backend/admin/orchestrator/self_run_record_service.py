from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional
from datetime import datetime
import shutil
import re

from fastapi import HTTPException
from fastapi.responses import Response

from .path_utils import require_allowed_root_path


APPROVAL_ID_PATTERN = r"[A-Za-z0-9._-]{1,128}"
INVALID_APPROVAL_ID_DETAIL = "approval_id 형식이 올바르지 않습니다."


def _normalize_approval_id(approval_id: Optional[str]) -> str:
    normalized_approval_id = str(approval_id or "").strip()
    if not re.fullmatch(APPROVAL_ID_PATTERN, normalized_approval_id):
        raise HTTPException(status_code=400, detail=INVALID_APPROVAL_ID_DETAIL)
    return normalized_approval_id


def _resolve_self_run_delete_target(admin_self_run_root: Callable[[], Path], approval_id: Optional[str]) -> Path:
    return require_allowed_root_path(
        admin_self_run_root() / _normalize_approval_id(approval_id),
        detail="삭제 대상 경로가 허용 범위를 벗어났습니다.",
    )


def _build_terminal_evidence(approval_payload: Dict[str, Any]) -> Dict[str, Any]:
    status = str(approval_payload.get("status") or "failed").strip() or "failed"
    finished_at = str(approval_payload.get("finished_at") or "").strip()
    worker_log_path = str(approval_payload.get("worker_log_path") or "").strip()
    worker_status_path = str(approval_payload.get("worker_status_path") or "").strip()
    worker_alive_raw = approval_payload.get("worker_alive")
    worker_alive = bool(worker_alive_raw) if isinstance(worker_alive_raw, bool) else None
    report_preview_path = str(approval_payload.get("report_preview_path") or approval_payload.get("report_path") or "").strip()
    terminal_statuses = {"failed", "no_changes", "pending_approval", "applied_to_source"}
    terminal_state = status in terminal_statuses
    evidence_items = {
        "approval_status": status,
        "finished_at_present": bool(finished_at),
        "worker_alive_false": worker_alive is False,
        "worker_log_present": bool(worker_log_path),
        "worker_status_present": bool(worker_status_path),
        "report_preview_present": bool(report_preview_path),
    }
    required_checks = {
        "terminal_state": terminal_state,
        "finished_at_present": bool(finished_at),
        "worker_alive_false": worker_alive is False,
        "worker_log_present": bool(worker_log_path),
    }
    missing_items = [key for key, ok in required_checks.items() if not ok]
    return {
        "status": status,
        "terminal_state": terminal_state,
        "result_status": "pass" if terminal_state and not missing_items else ("partial" if terminal_state else "blocked"),
        "required_checks": required_checks,
        "missing_items": missing_items,
        "evidence_items": evidence_items,
        "paths": {
            "worker_log_path": worker_log_path,
            "worker_status_path": worker_status_path,
            "report_preview_path": report_preview_path,
        },
    }


def approval_payload_to_self_run_response(approval_payload: Dict[str, Any]) -> Dict[str, Any]:
    orchestration_result = dict(approval_payload.get("orchestration_result") or {})
    self_run_readiness = dict(orchestration_result.get("self_run_readiness") or {})
    target_patch_registry = dict(orchestration_result.get("completion_judge", {}).get("target_patch_registry") or orchestration_result.get("packaging_audit", {}).get("target_patch_registry") or {})
    terminal_evidence = _build_terminal_evidence(approval_payload)
    return {
        "approval_id": str(approval_payload.get("approval_id") or ""),
        "status": str(approval_payload.get("status") or "failed"),
        "requested_mode": str(approval_payload.get("requested_mode") or ""),
        "execution_mode": str(approval_payload.get("execution_mode") or ""),
        "directive_template": str(approval_payload.get("directive_template") or ""),
        "directive_scope": str(approval_payload.get("directive_scope") or ""),
        "source_path": str(approval_payload.get("source_path") or ""),
        "target_file_ids": list(target_patch_registry.get("target_file_ids") or []),
        "target_section_ids": list(target_patch_registry.get("target_section_ids") or []),
        "target_feature_ids": list(target_patch_registry.get("target_feature_ids") or []),
        "target_chunk_ids": list(target_patch_registry.get("target_chunk_ids") or []),
        "failure_tags": list(target_patch_registry.get("failure_tags") or []),
        "repair_tags": list(target_patch_registry.get("repair_tags") or []),
        "started_at": str(approval_payload.get("started_at") or ""),
        "finished_at": str(approval_payload.get("finished_at") or ""),
        "worker_log_path": str(approval_payload.get("worker_log_path") or ""),
        "running_seconds": approval_payload.get("running_seconds"),
        "runtime_diagnostic": str(approval_payload.get("runtime_diagnostic") or ""),
        "analysis_path": str(orchestration_result.get("analysis_path") or ""),
        "root_cause_report_path": str(orchestration_result.get("root_cause_report_path") or ""),
        "python_self_diagnostic_error": str(orchestration_result.get("python_self_diagnostic_error") or ""),
        "python_self_diagnostic_logs": list(orchestration_result.get("python_self_diagnostic_logs") or []),
        "python_compile_failed_files": list((orchestration_result.get("python_self_diagnostic_result") or {}).get("failed_files") or []),
        "approval_gate_ok": bool(approval_payload.get("approval_gate_ok")),
        "approval_gate_failed_fields": list(approval_payload.get("approval_gate_failed_fields") or []),
        "self_run_readiness": self_run_readiness,
        "applied": self_run_readiness.get("applied", orchestration_result.get("applied")),
        "postcheck_ok": self_run_readiness.get("postcheck_ok", orchestration_result.get("postcheck_ok")),
        "dod_ok": self_run_readiness.get("dod_ok", orchestration_result.get("dod_ok")),
        "completion_gate_ok": self_run_readiness.get("completion_gate_ok", orchestration_result.get("completion_gate_ok")),
        "semantic_audit_ok": self_run_readiness.get("semantic_audit_ok", orchestration_result.get("semantic_audit_ok")),
        "structure_validation_ok": self_run_readiness.get("structure_validation_ok", orchestration_result.get("structure_validation_ok")),
        "traceability_map_path": str(self_run_readiness.get("traceability_map_path") or orchestration_result.get("traceability_map_path") or ""),
        "terminal_evidence": terminal_evidence,
        "applied_to_source_evidence": dict(approval_payload.get("applied_to_source_evidence") or {}),
        "approval_checklist": list(approval_payload.get("approval_checklist") or []),
    }


def latest_self_run_record_path(
    *,
    admin_self_run_root: Callable[[], Path],
    load_json_file: Callable[[Path], Dict[str, Any]],
    pending_only: bool = False,
) -> Optional[Path]:
    root_dir = admin_self_run_root()
    if not root_dir.exists():
        return None

    candidate_dirs = sorted(
        (path for path in root_dir.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    )
    for candidate_dir in candidate_dirs:
        record_path = candidate_dir / "approval.json"
        if not record_path.exists():
            continue
        if not pending_only:
            return record_path
        try:
            payload = load_json_file(record_path)
        except Exception:
            continue
        if payload.get("status") == "pending_approval":
            return record_path
    return None


def _delete_all_pending_self_run_records(
    *,
    admin_self_run_root: Callable[[], Path],
    load_json_file: Callable[[Path], Dict[str, Any]],
) -> Dict[str, Any]:
    root_dir = admin_self_run_root()
    if not root_dir.exists():
        return {
            "deleted_approval_ids": [],
            "deleted_count": 0,
        }

    deleted_approval_ids: list[str] = []
    root_dir = require_allowed_root_path(
        root_dir,
        detail="자가 실행 루트 경로가 허용 범위를 벗어났습니다.",
    )
    for candidate_dir in sorted(
        (path for path in root_dir.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    ):
        candidate_dir = require_allowed_root_path(
            candidate_dir,
            detail="자가 실행 삭제 대상 경로가 허용 범위를 벗어났습니다.",
        )
        record_path = candidate_dir / "approval.json"
        if not record_path.exists():
            continue
        try:
            payload = load_json_file(record_path)
        except Exception:
            continue
        if str(payload.get("status") or "") != "pending_approval":
            continue
        deleted_approval_ids.append(str(payload.get("approval_id") or candidate_dir.name))
        shutil.rmtree(candidate_dir, ignore_errors=True)

    return {
        "deleted_approval_ids": deleted_approval_ids,
        "deleted_count": len(deleted_approval_ids),
    }


def get_workspace_self_run_record_response(
    *,
    approval_id: Optional[str],
    latest: bool,
    pending_only: bool,
    approval_record_path: Callable[[str], Path],
    latest_self_run_record_path_func: Callable[..., Optional[Path]],
    load_json_file: Callable[[Path], Dict[str, Any]],
    stabilize_running_self_run_record: Callable[[Path, Dict[str, Any]], Dict[str, Any]],
    approval_payload_to_response: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any] | Response:
    record_path: Optional[Path] = None
    if approval_id:
        record_path = approval_record_path(_normalize_approval_id(approval_id))
    elif latest:
        record_path = latest_self_run_record_path_func(pending_only=pending_only)

    if not record_path or not record_path.exists():
        if approval_id:
            return Response(status_code=204)
        if latest:
            return Response(status_code=204)
        raise HTTPException(status_code=404, detail="자가 실행 기록을 찾을 수 없습니다.")

    approval_payload = load_json_file(record_path)
    approval_payload = stabilize_running_self_run_record(record_path, approval_payload)
    return approval_payload_to_response(approval_payload)


async def normalize_workspace_self_run_record_response(
    *,
    request,
    db,
    admin,
    approval_record_path: Callable[[str], Path],
    latest_self_run_record_path_func: Callable[..., Optional[Path]],
    load_json_file: Callable[[Path], Dict[str, Any]],
    stabilize_running_self_run_record: Callable[[Path, Dict[str, Any]], Dict[str, Any]],
    approval_payload_to_response: Callable[[Dict[str, Any]], Dict[str, Any]],
    admin_self_run_root: Callable[[], Path],
    resolve_admin_workspace_path: Callable[[str], Path],
    admin_workspace_root: Callable[[], Path],
    execute_workspace_self_run: Callable[..., Awaitable[Any]],
    workspace_self_run_request_type,
):
    if request.cleanup_only and not request.approval_id:
        cleanup_result = _delete_all_pending_self_run_records(
            admin_self_run_root=admin_self_run_root,
            load_json_file=load_json_file,
        )
        next_record_path = latest_self_run_record_path_func()
        latest_after_cleanup: Optional[Dict[str, Any]] = None
        if next_record_path and next_record_path.exists():
            next_payload = load_json_file(next_record_path)
            next_payload = stabilize_running_self_run_record(next_record_path, next_payload)
            latest_after_cleanup = approval_payload_to_response(next_payload)
        if cleanup_result["deleted_count"] > 0:
            return {
                "normalized": True,
                "action": "cleaned_all_pending_approval",
                "message": f"pending_approval self-run 기록 {cleanup_result['deleted_count']}건을 일괄 정리했습니다.",
                "deleted_approval_ids": cleanup_result["deleted_approval_ids"],
                "latest": latest_after_cleanup,
            }

    record_path: Optional[Path] = None
    if request.approval_id:
        record_path = approval_record_path(_normalize_approval_id(request.approval_id))
    else:
        record_path = latest_self_run_record_path_func()

    if not record_path or not record_path.exists():
        return {
            "normalized": False,
            "action": "noop",
            "message": "정리 대상 최신 self-run 실패 기록이 없습니다.",
            "latest": None,
        }

    approval_payload = load_json_file(record_path)
    approval_payload = stabilize_running_self_run_record(record_path, approval_payload)
    current_status = str(approval_payload.get("status") or "")
    if current_status == "pending_approval" and request.cleanup_only:
        deleted_approval_id = _normalize_approval_id(approval_payload.get("approval_id"))
        shutil.rmtree(
            _resolve_self_run_delete_target(admin_self_run_root, deleted_approval_id),
            ignore_errors=True,
        )
        latest_after_cleanup: Optional[Dict[str, Any]] = None
        next_record_path = latest_self_run_record_path_func()
        if next_record_path and next_record_path.exists():
            next_payload = load_json_file(next_record_path)
            next_payload = stabilize_running_self_run_record(next_record_path, next_payload)
            latest_after_cleanup = approval_payload_to_response(next_payload)
        return {
            "normalized": True,
            "action": "cleaned_pending_approval",
            "message": "최신 pending_approval self-run 기록을 운영 정리 대상으로 삭제했습니다.",
            "deleted_approval_id": deleted_approval_id,
            "latest": latest_after_cleanup,
        }
    if current_status != "failed":
        return {
            "normalized": False,
            "action": "noop",
            "message": "최신 self-run 실패 기록이 없어 정리하지 않았습니다.",
            "latest": approval_payload_to_response(approval_payload),
        }

    source_path = str(approval_payload.get("source_path") or "").strip()
    retry_source_path = source_path
    if source_path and not request.cleanup_only:
        try:
            resolved_source_dir = resolve_admin_workspace_path(source_path)
        except Exception:
            resolved_source_dir = None
        workspace_root = admin_workspace_root().resolve()
        if resolved_source_dir and resolved_source_dir != workspace_root:
            retry_source_path = str(workspace_root)

        try:
            retry_result = await execute_workspace_self_run(
                workspace_self_run_request_type(
                    source_path=retry_source_path,
                    mode=str(approval_payload.get("requested_mode") or "self-diagnosis"),
                    self_run_stage="remediation",
                    directive_template=str(approval_payload.get("directive_template") or ""),
                    directive_scope=str(approval_payload.get("directive_scope") or ""),
                    directive_request="관리자 정상화 루틴에서 최신 self-run 실패 기록 재생성을 요청했습니다.",
                ),
                db=db,
                admin=admin,
            )
        except HTTPException as exc:
            if exc.status_code == 400:
                return {
                    "normalized": False,
                    "action": "blocked",
                    "message": str(exc.detail or "self-run 정상화 재실행이 차단되었습니다."),
                    "latest": approval_payload_to_response(approval_payload),
                }
            raise
        return {
            "normalized": True,
            "action": "regenerated",
            "message": (
                "최신 self-run 실패 기록을 전체 프로젝트 루트 기준 재생성 큐로 전환했습니다."
                if retry_source_path != source_path
                else "최신 self-run 실패 기록을 재생성 큐로 전환했습니다."
            ),
            "retry": retry_result,
            "latest": approval_payload_to_response(approval_payload),
        }

    deleted_approval_id = _normalize_approval_id(approval_payload.get("approval_id"))
    shutil.rmtree(
        _resolve_self_run_delete_target(admin_self_run_root, deleted_approval_id),
        ignore_errors=True,
    )
    latest_after_cleanup: Optional[Dict[str, Any]] = None
    next_record_path = latest_self_run_record_path_func()
    if next_record_path and next_record_path.exists():
        next_payload = load_json_file(next_record_path)
        next_payload = stabilize_running_self_run_record(next_record_path, next_payload)
        latest_after_cleanup = approval_payload_to_response(next_payload)
    return {
        "normalized": True,
        "action": "cleaned",
        "message": "최신 self-run 실패 기록을 정리했습니다.",
        "deleted_approval_id": deleted_approval_id,
        "latest": latest_after_cleanup,
    }


def assert_self_run_record_contract() -> None:
    sample = approval_payload_to_self_run_response({
        "approval_id": "sample",
        "status": "running",
        "requested_mode": "self-diagnosis",
        "execution_mode": "review",
        "directive_template": "",
        "directive_scope": "",
        "source_path": "/app",
        "orchestration_result": {},
        "started_at": datetime.now().isoformat(),
        "finished_at": "",
        "worker_log_path": "",
        "running_seconds": 0,
        "runtime_diagnostic": "",
    })
    required_keys = {
        "approval_id", "status", "requested_mode", "execution_mode", "directive_template",
        "directive_scope", "source_path", "started_at", "finished_at", "worker_log_path",
        "running_seconds", "runtime_diagnostic", "analysis_path", "root_cause_report_path",
        "python_self_diagnostic_error", "python_self_diagnostic_logs", "python_compile_failed_files",
        "target_file_ids", "target_section_ids", "target_feature_ids", "target_chunk_ids",
        "failure_tags", "repair_tags",
    }
    if not required_keys.issubset(sample.keys()):
        missing = sorted(required_keys.difference(sample.keys()))
        raise RuntimeError(f"self-run record contract 누락: {', '.join(missing)}")
