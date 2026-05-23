from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional
from datetime import datetime


def prepare_workspace_self_prepare_result(
    source_dir: Path,
    requested_mode: str,
    create_experiment_clone: bool,
    *,
    scan_workspace_for_self_analysis: Callable[[Path], Dict[str, Any]],
    build_self_analysis_bundle: Callable[[Path, list[Dict[str, Any]]], Dict[str, Any]],
    clone_workspace_for_experiment: Callable[[Path], Dict[str, Any]],
    build_self_prepare_task: Callable[[str, Path, Dict[str, Any], Dict[str, Any], Optional[str]], str],
    suggested_self_mode: Callable[[str], str],
    build_admin_analysis_summary: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    scan_result = scan_workspace_for_self_analysis(source_dir)
    bundle_result = build_self_analysis_bundle(
        source_dir,
        scan_result["text_files"],
    )

    experiment_clone_path = None
    clone_result: Optional[Dict[str, Any]] = None
    if create_experiment_clone:
        clone_result = clone_workspace_for_experiment(source_dir)
        experiment_clone_path = str(clone_result["clone_path"])

    suggested_task = build_self_prepare_task(
        requested_mode,
        source_dir,
        scan_result,
        bundle_result,
        experiment_clone_path,
    )

    return {
        "source_path": str(source_dir),
        "requested_mode": requested_mode,
        "suggested_mode": suggested_self_mode(requested_mode),
        "recommended_work_dir": experiment_clone_path,
        "experiment_clone_path": experiment_clone_path,
        "clone_copied_files": (
            clone_result["copied_files"] if clone_result else None
        ),
        "analysis_summary": build_admin_analysis_summary(
            scan_result,
            bundle_result,
        ),
        "skipped_directories": scan_result["skipped_directories"],
        "tree_preview": "\n".join(scan_result["tree_lines"]),
        "key_text_files": scan_result["text_files"][:80],
        "suggested_task": suggested_task,
    }


def build_initial_running_self_run_payload(
    approval_id: str,
    requested_mode: str,
    directive_template: str,
    directive_scope: str,
    directive_request: str,
    source_dir: Path,
    report_path: Path,
    report_preview: str,
    *,
    self_run_execution_mode: Callable[[str], str],
    self_run_worker_log_path: Callable[[str], Path],
    self_run_worker_host_log_path: Callable[[str], str],
    self_run_worker_status_path: Callable[[str], Path],
) -> Dict[str, Any]:
    execution_mode = self_run_execution_mode(requested_mode)
    return {
        "approval_id": approval_id,
        "created_at": datetime.now().isoformat(),
        "started_at": datetime.now().isoformat(),
        "requested_mode": requested_mode,
        "execution_mode": execution_mode,
        "directive_template": directive_template,
        "directive_scope": directive_scope,
        "directive_request": directive_request,
        "status": "running",
        "source_path": str(source_dir),
        "experiment_clone_path": "",
        "analysis_summary": {},
        "tree_preview": "",
        "key_text_files": [],
        "source_snapshot": {},
        "approval_gate_ok": False,
        "approval_gate_failed_fields": [],
        "diff_summary": {
            "added_files": [],
            "modified_files": [],
            "deleted_files": [],
            "total_changed_files": 0,
        },
        "orchestration_result": {},
        "report_preview": report_preview,
        "report_path": str(report_path),
        "report_preview_path": str(report_path),
        "orchestration_error": "",
        "executed_task": "",
        "worker_pid": None,
        "worker_log_path": str(self_run_worker_log_path(approval_id)),
        "worker_log_host_path": self_run_worker_host_log_path(approval_id),
        "worker_status_path": str(self_run_worker_status_path(approval_id)),
        "worker_alive": False,
        "running_seconds": 0,
        "runtime_diagnostic": "백그라운드 worker가 self-run 준비를 시작하기 전입니다.",
        "approval_checklist": [
            {
                "id": "worker_boot_recorded",
                "label": "worker 시작 기록",
                "status": "pending",
                "check_label": "대기",
                "note": "",
                "closed_at": "",
            },
            {
                "id": "worker_status_written",
                "label": "worker 상태 파일 기록",
                "status": "pending",
                "check_label": "대기",
                "note": "",
                "closed_at": "",
            },
            {
                "id": "report_preview_linked",
                "label": "report preview 연결",
                "status": "completed",
                "check_label": "완료",
                "note": "초기 report preview 경로가 연결되었습니다.",
                "closed_at": datetime.now().isoformat(),
            },
            {
                "id": "terminal_status_closed",
                "label": "terminal 상태 마감",
                "status": "pending",
                "check_label": "대기",
                "note": "",
                "closed_at": "",
            },
            {
                "id": "approval_failure_reason_recorded",
                "label": "실패 사유 기록",
                "status": "pending",
                "check_label": "대기",
                "note": "",
                "closed_at": "",
            },
        ],
    }
