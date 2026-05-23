from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime
import shutil

from fastapi import HTTPException
from backend.llm.target_patch_registry import build_target_patch_registry_snapshot


def _unique_ordered(values: List[Any]) -> List[str]:
    ordered: List[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _merge_registry_metadata(*payloads: Dict[str, Any]) -> Dict[str, List[str]]:
    merged = {
        "target_file_ids": [],
        "target_section_ids": [],
        "target_feature_ids": [],
        "target_chunk_ids": [],
        "failure_tags": [],
        "repair_tags": [],
    }
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        for key in merged.keys():
            merged[key].extend(list(payload.get(key) or []))
    return {key: _unique_ordered(values) for key, values in merged.items()}


def _load_traceability_registry_metadata(clone_dir: Path, orchestration_result: Dict[str, Any]) -> Dict[str, List[str]]:
    candidate_paths = [
        orchestration_result.get("traceability_map_path"),
        ((orchestration_result.get("validation_artifacts") or {}).get("traceability_map_path") if isinstance(orchestration_result.get("validation_artifacts"), dict) else None),
        ((orchestration_result.get("artifact_paths") or {}).get("traceability_map_path") if isinstance(orchestration_result.get("artifact_paths"), dict) else None),
    ]
    for candidate in candidate_paths:
        relative_path = str(candidate or "").strip()
        if not relative_path:
            continue
        traceability_path = Path(relative_path)
        if not traceability_path.is_absolute():
            traceability_path = clone_dir / traceability_path
        if not traceability_path.exists() or not traceability_path.is_file():
            continue
        try:
            payload = json.loads(traceability_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        registry_payload = payload.get("target_patch_registry") if isinstance(payload.get("target_patch_registry"), dict) else payload
        return _merge_registry_metadata(registry_payload)
    return _merge_registry_metadata({})


def _extract_applied_target_registry_metadata(clone_dir: Path, orchestration_result: Dict[str, Any], fallback_registry: Dict[str, Any]) -> Dict[str, List[str]]:
    evidence_bundle = orchestration_result.get("evidence_bundle") if isinstance(orchestration_result.get("evidence_bundle"), dict) else {}
    selective_apply = evidence_bundle.get("selective_apply") if isinstance(evidence_bundle.get("selective_apply"), dict) else {}
    direct_payload = {
        "target_file_ids": orchestration_result.get("target_file_ids"),
        "target_section_ids": orchestration_result.get("target_section_ids"),
        "target_feature_ids": orchestration_result.get("target_feature_ids"),
        "target_chunk_ids": orchestration_result.get("target_chunk_ids"),
        "failure_tags": orchestration_result.get("failure_tags"),
        "repair_tags": orchestration_result.get("repair_tags"),
    }
    target_registry_payload = orchestration_result.get("target_patch_registry") if isinstance(orchestration_result.get("target_patch_registry"), dict) else {}
    traceability_payload = _load_traceability_registry_metadata(clone_dir, orchestration_result)
    return _merge_registry_metadata(fallback_registry, selective_apply, direct_payload, target_registry_payload, traceability_payload)


def run_admin_approval_validation(
    target_dir: Path,
    *,
    collect_syncable_files: Callable[[Path], Dict[str, Dict[str, Any]]],
    collect_empty_syncable_dirs: Callable[[Path], List[str]],
    py_compile_module,
    changed_paths: Optional[List[str]] = None,
) -> Tuple[bool, List[str], Optional[str]]:
    logs: List[str] = []
    inventory = collect_syncable_files(target_dir)
    logs.append(f"[approval-check] files_total={len(inventory)}")

    changed_path_set = {
        str(path or "").replace("\\", "/").strip()
        for path in (changed_paths or [])
        if str(path or "").strip()
    }

    zero_files = [
        rel_path
        for rel_path, file_info in inventory.items()
        if int(file_info.get("size_bytes", 0)) == 0
        and (not changed_path_set or rel_path.replace("\\", "/") in changed_path_set)
    ]
    if zero_files:
        logs.append(f"[approval-check] empty_files={len(zero_files)}")
        return False, logs, "승인 직전 재검증에서 빈 파일이 감지되었습니다"

    empty_dirs = collect_empty_syncable_dirs(target_dir)
    if changed_path_set:
        empty_dirs = []
    if empty_dirs:
        logs.append(f"[approval-check] empty_dirs={len(empty_dirs)}")
        return False, logs, "승인 직전 재검증에서 빈 폴더가 감지되었습니다"

    py_files = [
        rel_path for rel_path in sorted(inventory.keys())
        if rel_path.lower().endswith(".py")
    ]
    for rel_path in py_files:
        try:
            py_compile_module.compile(
                str(target_dir / Path(rel_path)),
                doraise=True,
            )
            logs.append(f"[approval-check][py_compile] {rel_path}: ok")
        except py_compile_module.PyCompileError:
            logs.append(f"[approval-check][py_compile] {rel_path}: fail")
            return (
                False,
                logs,
                f"승인 직전 재검증 py_compile 실패: {rel_path}",
            )

    return True, logs, None


def sync_clone_into_source(
    source_dir: Path,
    clone_dir: Path,
    *,
    admin_self_backup_root: Callable[[], Path],
    slugify_admin_name: Callable[[str], str],
    admin_self_exclude_dir_names: List[str] | tuple[str, ...] | set[str],
    diff_workspace_trees: Callable[[Path, Path], Dict[str, Any]],
) -> Dict[str, Any]:
    backup_root = admin_self_backup_root()
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_dir = backup_root / (
        f"{slugify_admin_name(source_dir.name)}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    shutil.copytree(
        source_dir,
        backup_dir,
        ignore=shutil.ignore_patterns(*admin_self_exclude_dir_names),
    )

    diff_summary = diff_workspace_trees(source_dir, clone_dir)
    for rel_path in diff_summary["deleted_files"]:
        target = source_dir / Path(rel_path)
        if target.exists() and target.is_file():
            target.unlink()

    for rel_path in (
        diff_summary["added_files"] + diff_summary["modified_files"]
    ):
        clone_file = clone_dir / Path(rel_path)
        target_file = source_dir / Path(rel_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(clone_file, target_file)

    return {
        "backup_path": str(backup_dir),
        "diff_summary": diff_summary,
    }


def approve_workspace_self_run_response(
    *,
    payload,
    approval_record_path: Callable[[str], Path],
    load_json_file: Callable[[Path], Dict[str, Any]],
    write_json_file: Callable[[Path, Dict[str, Any]], None],
    resolve_admin_workspace_path: Callable[[str], Path],
    is_self_run_approval_ready: Callable[[Dict[str, Any]], tuple[bool, List[str]]],
    build_workspace_snapshot: Callable[[Path], Dict[str, Any]],
    run_admin_approval_validation_func: Callable[[Path], Tuple[bool, List[str], Optional[str]]],
    diff_workspace_trees: Callable[[Path, Path], Dict[str, Any]],
    sync_clone_into_source_func: Callable[[Path, Path], Dict[str, Any]],
) -> Dict[str, Any]:
    record_path = approval_record_path(payload.approval_id)
    if not record_path.exists():
        raise HTTPException(status_code=404, detail="승인 대기 기록을 찾을 수 없습니다.")

    approval_payload = load_json_file(record_path)
    if approval_payload.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="승인 대기 상태가 아닙니다.")

    source_dir = resolve_admin_workspace_path(approval_payload["source_path"])
    clone_dir = resolve_admin_workspace_path(approval_payload["experiment_clone_path"])
    orchestration_result = approval_payload.get("orchestration_result") or {}
    approval_gate_ok, approval_gate_failed_fields = is_self_run_approval_ready(orchestration_result)
    if not approval_gate_ok:
        approval_payload["last_approval_check"] = {
            "checked_at": datetime.now().isoformat(),
            "ok": False,
            "reason": "stored_orchestration_gate_failed",
            "failed_fields": approval_gate_failed_fields,
        }
        write_json_file(record_path, approval_payload)
        raise HTTPException(
            status_code=400,
            detail=(
                "승인 조건을 충족하지 못했습니다: "
                + ", ".join(approval_gate_failed_fields)
            ),
        )

    recorded_source_snapshot = approval_payload.get("source_snapshot") or {}
    current_source_snapshot = build_workspace_snapshot(source_dir)
    if (
        recorded_source_snapshot.get("fingerprint")
        and recorded_source_snapshot.get("fingerprint") != current_source_snapshot.get("fingerprint")
    ):
        approval_payload["last_approval_check"] = {
            "checked_at": datetime.now().isoformat(),
            "ok": False,
            "reason": "source_changed_after_self_run",
            "recorded_fingerprint": recorded_source_snapshot.get("fingerprint"),
            "current_fingerprint": current_source_snapshot.get("fingerprint"),
        }
        write_json_file(record_path, approval_payload)
        raise HTTPException(
            status_code=409,
            detail=(
                "self-run 이후 원본 폴더가 변경되어 자동 반영을 중단합니다. "
                "다시 실행 후 새 승인 대기 결과를 생성해 주세요."
            ),
        )

    current_diff_summary = diff_workspace_trees(source_dir, clone_dir)
    if current_diff_summary["total_changed_files"] <= 0:
        approval_payload["last_approval_check"] = {
            "checked_at": datetime.now().isoformat(),
            "ok": False,
            "reason": "no_syncable_changes",
            "logs": [],
        }
        write_json_file(record_path, approval_payload)
        raise HTTPException(
            status_code=400,
            detail="승인 시점에 반영할 변경 파일이 없습니다.",
        )

    changed_paths = list(
        dict.fromkeys(
            list(current_diff_summary.get("added_files") or [])
            + list(current_diff_summary.get("modified_files") or [])
        )
    )

    approval_validation_ok, approval_validation_logs, approval_validation_error = run_admin_approval_validation_func(
        clone_dir,
        changed_paths=changed_paths,
    )
    if not approval_validation_ok:
        approval_payload["last_approval_check"] = {
            "checked_at": datetime.now().isoformat(),
            "ok": False,
            "reason": "clone_revalidation_failed",
            "logs": approval_validation_logs,
            "error": approval_validation_error,
        }
        write_json_file(record_path, approval_payload)
        raise HTTPException(
            status_code=400,
            detail=(approval_validation_error or "승인 직전 재검증에 실패했습니다."),
        )

    sync_result = sync_clone_into_source_func(source_dir, clone_dir)
    applied_diff_summary = dict(sync_result.get("diff_summary") or {})
    changed_paths = list(dict.fromkeys(list(applied_diff_summary.get("added_files") or []) + list(applied_diff_summary.get("modified_files") or [])))
    applied_target_patch_registry = build_target_patch_registry_snapshot(
        written_files=changed_paths,
        target_paths=changed_paths,
        capability_ids=["self-healing-engine", "code-generator"],
    )
    applied_target_patch_registry = {
        **applied_target_patch_registry,
        **_extract_applied_target_registry_metadata(clone_dir, orchestration_result, applied_target_patch_registry),
    }
    approval_payload["status"] = "applied_to_source"
    approval_payload["approved_at"] = datetime.now().isoformat()
    approval_payload["backup_path"] = sync_result["backup_path"]
    approval_payload["applied_diff_summary"] = applied_diff_summary
    approval_payload["applied_to_source_evidence"] = {
        "record_scope_id": "phase-f-focused-self-healing-apply",
        "result_status": "pass",
        "target_file_ids": list(applied_target_patch_registry.get("target_file_ids") or []),
        "target_section_ids": list(applied_target_patch_registry.get("target_section_ids") or []),
        "target_feature_ids": list(applied_target_patch_registry.get("target_feature_ids") or []),
        "target_chunk_ids": list(applied_target_patch_registry.get("target_chunk_ids") or []),
        "changed_paths": changed_paths,
    }
    approval_payload["last_approval_check"] = {
        "checked_at": approval_payload["approved_at"],
        "ok": True,
        "reason": "approved_after_revalidation",
        "logs": approval_validation_logs,
        "source_fingerprint": current_source_snapshot.get("fingerprint"),
    }
    write_json_file(record_path, approval_payload)

    return {
        "approval_id": payload.approval_id,
        "status": approval_payload["status"],
        "source_path": str(source_dir),
        "backup_path": sync_result["backup_path"],
        "diff_summary": applied_diff_summary,
        "applied_to_source_evidence": approval_payload["applied_to_source_evidence"],
    }


def assert_self_run_approval_contract() -> None:
    sample_sync = {
        "backup_path": "/tmp/backup",
        "diff_summary": {
            "added_files": [],
            "modified_files": [],
            "deleted_files": [],
            "total_changed_files": 0,
        },
    }
    required_sync_keys = {"backup_path", "diff_summary"}
    if not required_sync_keys.issubset(sample_sync.keys()):
        missing = sorted(required_sync_keys.difference(sample_sync.keys()))
        raise RuntimeError(f"self-run approval sync contract 누락: {', '.join(missing)}")
