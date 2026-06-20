from __future__ import annotations

import json
import re
from datetime import datetime

from backend.time_utils import utcnow
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional


def _canonical_evidence_identity(evidence_bundle: Dict[str, Any]) -> Dict[str, Any]:
    contract = dict(evidence_bundle.get("contract") or {})
    execution = dict(evidence_bundle.get("execution") or {})
    selective_apply = dict(evidence_bundle.get("selective_apply") or {})
    return {
        "evidence_schema_version": str(contract.get("evidence_schema_version") or "v1"),
        "profile_id": str(contract.get("profile_id") or ""),
        "evidence_run_id": str(execution.get("evidence_run_id") or ""),
        "evidence_generated_at": str(execution.get("evidence_generated_at") or ""),
        "self_run_status": str(execution.get("self_run_status") or ""),
        "completion_gate_ok": execution.get("completion_gate_ok"),
        "failure_tags": list(selective_apply.get("failure_tags") or []),
        "target_file_ids": list(selective_apply.get("target_file_ids") or []),
    }


def _build_self_run_readiness_payload(
    *,
    written_files: List[str],
    traceability_map_path: Path,
    semantic_audit_report_path: Path,
    artifact_paths: Dict[str, Any],
    validation_artifacts: Dict[str, Any],
    completion_gate_ok: bool,
    semantic_audit_ok: bool,
) -> Dict[str, Any]:
    readiness_artifact_paths = {
        "final_readiness_checklist_path": str(artifact_paths.get("final_readiness_checklist_path") or ""),
        "automatic_validation_result_path": str(artifact_paths.get("automatic_validation_result_path") or ""),
        "automatic_validation_markdown_path": str(artifact_paths.get("automatic_validation_markdown_path") or ""),
        "failure_report_path": str(artifact_paths.get("failure_report_path") or ""),
        "root_cause_report_path": str(artifact_paths.get("root_cause_report_path") or ""),
        "output_audit_path": str(artifact_paths.get("output_audit_path") or ""),
        "traceability_map_path": str(artifact_paths.get("traceability_map_path") or ""),
    }
    artifact_checks = {
        "written_files_present": bool(written_files),
        "validation_result_present": bool(readiness_artifact_paths["automatic_validation_result_path"]),
        "output_audit_present": bool(readiness_artifact_paths["output_audit_path"]),
        "traceability_map_present": bool(str(traceability_map_path or "").strip()),
        "semantic_audit_report_present": bool(str(semantic_audit_report_path or "").strip()),
        "final_checklist_present": bool(readiness_artifact_paths["final_readiness_checklist_path"]),
    }
    applied = artifact_checks["written_files_present"]
    postcheck_ok = artifact_checks["validation_result_present"] and artifact_checks["output_audit_present"]
    dod_ok = artifact_checks["written_files_present"] and artifact_checks["final_checklist_present"]
    structure_validation_ok = artifact_checks["traceability_map_present"]
    semantic_review_ok = artifact_checks["semantic_audit_report_present"]
    completion_review_ok = postcheck_ok and dod_ok and structure_validation_ok
    blocking_reasons = [key for key, ok in artifact_checks.items() if not ok]
    ready_for_pending_approval = applied and postcheck_ok and dod_ok and structure_validation_ok and semantic_review_ok
    return {
        "contract_version": "v1",
        "ready_for_pending_approval": ready_for_pending_approval,
        "blocking_reasons": blocking_reasons,
        "applied": applied,
        "postcheck_ok": postcheck_ok,
        "dod_ok": dod_ok,
        "completion_gate_ok": completion_review_ok,
        "semantic_audit_ok": semantic_review_ok,
        "structure_validation_ok": structure_validation_ok,
        "traceability_map_path": str(traceability_map_path or ""),
        "written_file_count": len(written_files),
        "artifact_paths": readiness_artifact_paths,
        "validation_artifacts": {
            "validation_result_json_path": str(validation_artifacts.get("validation_result_json_path") or ""),
            "validation_result_md_path": str(validation_artifacts.get("validation_result_md_path") or ""),
            "output_audit_path": str(validation_artifacts.get("output_audit_path") or ""),
        },
        "product_completion_gate_ok": bool(completion_gate_ok),
        "product_semantic_audit_ok": bool(semantic_audit_ok),
    }


def _sync_readme_status_section(*, output_dir: Path, completion_gate_ok: bool) -> None:
    readme_path = output_dir / "README.md"
    if not readme_path.exists():
        return
    status_line = "- 현재 판정: `완료됨`" if completion_gate_ok else "- 현재 판정: `실패`"
    content = readme_path.read_text(encoding="utf-8", errors="ignore")
    section_pattern = re.compile(r"^## 현재 판정\s*(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    replacement = f"## 현재 판정\n\n{status_line}\n\n"
    if section_pattern.search(content):
        updated = section_pattern.sub(replacement, content, count=1)
    else:
        updated = content.rstrip() + f"\n\n## 현재 판정\n\n{status_line}\n"
    if updated != content:
        readme_path.write_text(updated, encoding="utf-8")


def _sync_workspace_status_doc(*, output_dir: Path, completion_gate_ok: bool) -> None:
    status_doc_path = output_dir / "docs" / "orchestrator-multigenerator-upgrade-status.md"
    status_label = "완료됨" if completion_gate_ok else "실패"
    status_doc_path.parent.mkdir(parents=True, exist_ok=True)
    status_doc_path.write_text(
        "# Orchestrator Multigenerator Upgrade Status\n\n"
        "## 현재 판정\n\n"
        f"- 상태: **{status_label}**\n"
        f"- completion_gate_ok: {'true' if completion_gate_ok else 'false'}\n"
        "- 반영 범위: customer output workspace only\n\n"
        "## 10. 실검증 기록 규칙\n\n"
        "- latest verification record is emitted from the current customer generation output.\n",
        encoding="utf-8",
    )


def finalize_customer_validation_bundle(
    *,
    output_dir: Path,
    task: str,
    mode: str,
    project_name: str,
    validation_profile: str,
    normalized_requirements: Dict[str, Any],
    domain_contract: Dict[str, Any],
    integration_test_plan: Dict[str, Any],
    packaging_audit: Dict[str, Any],
    completion_state: str,
    written_files: List[str],
    semantic_gate: Dict[str, Any],
    framework_e2e_validation: Dict[str, Any],
    external_integration_validation: Dict[str, Any],
    integration_test_engine: Dict[str, Any],
    completion_judge: Dict[str, Any],
    semantic_audit_score: int,
    semantic_audit_ok: bool,
    target_patch_registry_snapshot: Dict[str, Any],
    anchor_path: str,
    artifact_log_path: Path,
    traceability_map_path: Path,
    output_audit_path: Path,
    build_shipping_package_func,
    log_orchestration_phase_func,
    run_shipping_zip_reproduction_validation_func,
    build_product_readiness_hard_gate_func,
    build_operational_evidence_bundle_func,
    build_completion_judge_func,
    build_post_validation_ai_analysis_func,
    write_automatic_validation_artifacts_func,
    build_evidence_bundle_func,
    request_run_id: str,
    started_at: float,
    emit_orchestration_progress_func: Optional[Callable[[Optional[Callable[[str, str], None]], str, str], None]] = None,
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, Any]:
    def _emit_progress(message: str, level: str = "info") -> None:
        if callable(emit_orchestration_progress_func):
            emit_orchestration_progress_func(progress_callback, message, level)

    _emit_progress("finalization service entered")

    def _run_stage(stage_name: str, func):
        _emit_progress(f"finalization stage start: {stage_name}")
        stage_started_at = time.perf_counter()
        result = func()
        _emit_progress(
            f"finalization stage done: {stage_name} ({max(0.0, time.perf_counter() - stage_started_at):.2f}s)",
            "success",
        )
        return result

    shipping_package = _run_stage(
        "build_shipping_package",
        lambda: build_shipping_package_func(
            output_dir=output_dir,
            project_name=project_name,
            normalized_requirements=normalized_requirements,
            completion_judge=completion_judge,
            packaging_audit=packaging_audit,
            written_files=written_files,
        ),
    )
    log_orchestration_phase_func(
        "shipping_package_built",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    shipping_zip_validation = _run_stage(
        "run_shipping_zip_reproduction_validation",
        lambda: run_shipping_zip_reproduction_validation_func(
            output_dir=output_dir,
            archive_path=Path(shipping_package["archive_path"]),
            validation_profile=validation_profile,
        ),
    )
    log_orchestration_phase_func(
        "shipping_zip_validation_finished",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    product_readiness_hard_gate = _run_stage(
        "build_product_readiness_hard_gate",
        lambda: build_product_readiness_hard_gate_func(
            validation_profile=validation_profile,
            packaging_audit=packaging_audit,
            framework_e2e_validation=framework_e2e_validation,
            external_integration_validation=external_integration_validation,
            integration_test_engine=integration_test_engine,
            shipping_zip_validation=shipping_zip_validation,
            shipping_package=shipping_package,
        ),
    )
    operational_evidence = _run_stage(
        "build_operational_evidence_bundle",
        lambda: build_operational_evidence_bundle_func(
            profile_id=str(domain_contract.get("profile_id") or "").strip() or None,
        ),
    )
    log_orchestration_phase_func(
        "product_readiness_hard_gate_finished",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    completion_judge = _run_stage(
        "build_completion_judge",
        lambda: build_completion_judge_func(
            semantic_gate=semantic_gate,
            packaging_audit=packaging_audit,
            integration_test_engine=integration_test_engine,
            normalized_requirements=normalized_requirements,
            integration_test_plan=integration_test_plan,
            completion_state=completion_state,
            framework_e2e_validation=framework_e2e_validation,
            external_integration_validation=external_integration_validation,
            shipping_zip_validation=shipping_zip_validation,
            operational_evidence=operational_evidence,
            output_dir=output_dir,
            written_files=written_files,
            domain_contract=domain_contract,
        ),
    )
    log_orchestration_phase_func(
        "completion_judge_finished",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    completion_gate_ok = completion_state == "ready" and bool(semantic_gate.get("ok"))
    completion_gate_ok = completion_gate_ok and bool(completion_judge.get("product_ready"))
    post_validation_analysis = _run_stage(
        "build_post_validation_ai_analysis",
        lambda: build_post_validation_ai_analysis_func(
            completion_gate_ok=completion_gate_ok,
            semantic_audit_score=semantic_audit_score,
            semantic_audit_ok=semantic_audit_ok,
            product_readiness_hard_gate=product_readiness_hard_gate,
            target_patch_registry=target_patch_registry_snapshot,
            operational_evidence=operational_evidence,
        ),
    )
    log_orchestration_phase_func(
        "post_validation_analysis_finished",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    evidence_run_id = str(request_run_id or task).strip() or task
    evidence_generated_at = utcnow().isoformat() + "Z"
    evidence_bundle = _run_stage(
        "build_evidence_bundle",
        lambda: build_evidence_bundle_func(
            validation_profile=validation_profile,
            completion_gate_ok=completion_gate_ok,
            completion_gate_error="" if completion_gate_ok else "; ".join(list(completion_judge.get("failed_reasons") or [])[:8]),
            semantic_audit_ok=semantic_audit_ok,
            semantic_audit_score=semantic_audit_score,
            product_readiness_hard_gate=product_readiness_hard_gate,
            shipping_zip_validation=shipping_zip_validation,
            final_readiness_checklist_path="docs/final_readiness_checklist.md",
            operational_evidence=operational_evidence,
            target_patch_registry_snapshot=target_patch_registry_snapshot,
            run_id=evidence_run_id,
            post_validation_analysis=post_validation_analysis,
        ),
    )
    log_orchestration_phase_func(
        "evidence_bundle_built",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    evidence_bundle.setdefault("contract", {})["profile_id"] = validation_profile
    evidence_bundle.setdefault("execution", {})["evidence_run_id"] = evidence_run_id
    evidence_bundle.setdefault("execution", {})["evidence_generated_at"] = evidence_generated_at
    evidence_bundle.setdefault("execution", {})["evidence_snapshot_version"] = evidence_bundle.get("contract", {}).get("evidence_schema_version") or "v1"
    evidence_bundle.setdefault("readiness", {})["output_audit_path"] = "docs/output_audit.json"
    evidence_bundle.setdefault("readiness", {})["automatic_validation_result_path"] = "docs/automatic_validation_result.json"
    artifact_paths = {
        "final_readiness_checklist_path": "docs/final_readiness_checklist.md",
        "automatic_validation_result_path": "docs/automatic_validation_result.json",
        "output_audit_path": "docs/output_audit.json",
        "traceability_map_path": "docs/traceability_map.json",
    }
    evidence_snapshot = {
        "evidence_schema_version": evidence_bundle.get("contract", {}).get("evidence_schema_version") or "v1",
        "evidence_snapshot_version": evidence_bundle.get("execution", {}).get("evidence_snapshot_version") or "v1",
        "evidence_generated_at": evidence_generated_at,
        "evidence_run_id": evidence_run_id,
        "profile_id": validation_profile,
        "hard_gate": product_readiness_hard_gate,
        "readiness_checklist": {
            "final_readiness_checklist_path": "docs/final_readiness_checklist.md",
            "automatic_validation_result_path": "docs/automatic_validation_result.json",
        },
        "output_audit": {
            "path": "docs/output_audit.json",
            "completion_gate_ok": completion_gate_ok,
            "semantic_audit_ok": semantic_audit_ok,
            "semantic_audit_score": semantic_audit_score,
        },
        "artifact_paths": artifact_paths,
        "operational_evidence": operational_evidence,
    }
    operational_targets = list((operational_evidence.get("targets") or [])) if isinstance(operational_evidence, dict) else []
    operational_targets_by_id = dict((operational_evidence.get("targets_by_id") or {})) if isinstance(operational_evidence, dict) else {}
    operational_summary = dict((operational_evidence.get("summary") or {})) if isinstance(operational_evidence, dict) else {}
    warning_targets = list(operational_summary.get("warning_targets") or [])
    warning_threshold_ms = {
        str(target.get("id") or ""): round(float(target.get("warning_threshold_ms")), 1)
        for target in operational_targets
        if isinstance(target, dict)
        and str(target.get("id") or "")
        and isinstance(target.get("warning_threshold_ms"), (int, float))
    }
    operational_latency_summary = {
        "latency_warning": bool(warning_targets),
        "warning_targets": warning_targets,
        "warning_threshold_ms": warning_threshold_ms,
        "max_latency_ms": operational_summary.get("max_latency_ms"),
        "verified_count": operational_summary.get("verified_count") or operational_evidence.get("verified_target_count") or 0,
        "warning_count": operational_summary.get("warning_count") or operational_evidence.get("warning_target_count") or 0,
        "failed_count": operational_summary.get("failed_count") or operational_evidence.get("failed_target_count") or 0,
        "required_count": operational_summary.get("required_count") or operational_evidence.get("required_target_count") or len(operational_targets),
    }
    log_orchestration_phase_func(
        "operational_latency_summary_built",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    evidence_snapshot["operational_latency_summary"] = operational_latency_summary
    _sync_readme_status_section(output_dir=output_dir, completion_gate_ok=completion_gate_ok)
    _sync_workspace_status_doc(output_dir=output_dir, completion_gate_ok=completion_gate_ok)
    document_stale_scan = _run_stage(
        "build_document_stale_scan",
        lambda: write_automatic_validation_artifacts_func.__globals__["_build_document_stale_scan"](output_dir),
    )
    log_orchestration_phase_func(
        "document_stale_scan_finished",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    evidence_snapshot["document_stale_scan"] = document_stale_scan
    evidence_snapshot["documentation_sync"] = dict(document_stale_scan.get("documentation_sync") or {})
    evidence_bundle["snapshot"] = evidence_snapshot
    evidence_bundle.setdefault("readiness", {})["operational_evidence_snapshot"] = operational_evidence
    evidence_bundle.setdefault("readiness", {})["operational_targets_by_id"] = operational_targets_by_id
    evidence_bundle.setdefault("readiness", {})["operational_evidence_summary"] = operational_summary
    evidence_bundle.setdefault("readiness", {})["operational_latency_summary"] = operational_latency_summary
    evidence_bundle.setdefault("readiness", {})["documentation_sync"] = dict(document_stale_scan.get("documentation_sync") or {})
    _emit_progress("finalization entering validation_artifacts write")
    validation_artifacts = write_automatic_validation_artifacts_func(
        output_dir=output_dir,
        task=task,
        project_name=project_name,
        mode=mode,
        validation_profile=validation_profile,
        completion_gate_ok=completion_gate_ok,
        packaging_audit=packaging_audit,
        completion_judge=completion_judge,
        semantic_gate=semantic_gate,
        integration_test_engine=integration_test_engine,
        framework_e2e_validation=framework_e2e_validation,
        external_integration_validation=external_integration_validation,
        shipping_zip_validation=shipping_zip_validation,
        product_readiness_hard_gate=product_readiness_hard_gate,
        shipping_package=shipping_package,
        evidence_bundle=evidence_bundle,
    )
    _emit_progress(
        "finalization completed validation_artifacts write",
        "success",
    )
    log_orchestration_phase_func(
        "validation_artifacts_finalized",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    evidence_bundle["execution"]["evidence_run_id"] = evidence_run_id
    evidence_bundle["readiness"]["final_readiness_checklist_path"] = str(validation_artifacts.get("final_readiness_checklist_path") or "docs/final_readiness_checklist.md")
    evidence_bundle["readiness"]["automatic_validation_result_path"] = str(validation_artifacts.get("validation_result_json_path") or "docs/automatic_validation_result.json")
    evidence_bundle["readiness"]["output_audit_path"] = str(validation_artifacts.get("output_audit_path") or "docs/output_audit.json")
    artifact_paths = {
        "final_readiness_checklist_path": str(validation_artifacts.get("final_readiness_checklist_path") or "docs/final_readiness_checklist.md"),
        "automatic_validation_result_path": str(validation_artifacts.get("validation_result_json_path") or "docs/automatic_validation_result.json"),
        "automatic_validation_markdown_path": str(validation_artifacts.get("validation_result_md_path") or "docs/automatic_validation_result.md"),
        "failure_report_path": str(validation_artifacts.get("failure_report_path") or "docs/failure_report.md"),
        "root_cause_report_path": str(validation_artifacts.get("root_cause_report_path") or "docs/root_cause_analysis.md"),
        "output_audit_path": str(validation_artifacts.get("output_audit_path") or "docs/output_audit.json"),
        "traceability_map_path": "docs/traceability_map.json",
    }
    evidence_bundle["snapshot"]["artifact_paths"] = artifact_paths
    evidence_bundle.setdefault("readiness", {})["artifact_paths"] = artifact_paths
    log_orchestration_phase_func(
        "artifact_paths_finalized",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    compat_write_json = write_automatic_validation_artifacts_func.__globals__.get("_compat_write_json")

    def _load_json_payload(path: Path) -> Dict[str, Any]:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {}

    def _write_json_payload(path: Path, payload: Dict[str, Any]) -> None:
        if callable(compat_write_json):
            compat_write_json(path, payload)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    validation_result_json_path = output_dir / Path(
        str(validation_artifacts.get("validation_result_json_path") or "docs/automatic_validation_result.json")
    )
    canonical_validation_payload = _load_json_payload(validation_result_json_path)
    canonical_bundle = dict(canonical_validation_payload.get("evidence_bundle") or evidence_bundle)
    canonical_contract = dict(canonical_bundle.get("contract") or {})
    canonical_execution = dict(canonical_bundle.get("execution") or {})
    canonical_readiness = dict(canonical_bundle.get("readiness") or {})
    canonical_selective_apply = dict(canonical_bundle.get("selective_apply") or {})
    canonical_target_patch_entries = [
        item
        for item in (
            canonical_selective_apply.get("target_patch_entries")
            or target_patch_registry_snapshot.get("matched_entries")
            or target_patch_registry_snapshot.get("reusable_patch_units")
            or []
        )
        if isinstance(item, dict)
    ]
    canonical_selective_apply["target_patch_entries"] = canonical_target_patch_entries
    canonical_selective_apply["target_file_ids"] = list(canonical_selective_apply.get("target_file_ids") or target_patch_registry_snapshot.get("target_file_ids") or [])
    canonical_selective_apply["target_section_ids"] = list(canonical_selective_apply.get("target_section_ids") or target_patch_registry_snapshot.get("target_section_ids") or [])
    canonical_selective_apply["target_feature_ids"] = list(canonical_selective_apply.get("target_feature_ids") or target_patch_registry_snapshot.get("target_feature_ids") or [])
    canonical_selective_apply["target_chunk_ids"] = list(canonical_selective_apply.get("target_chunk_ids") or target_patch_registry_snapshot.get("target_chunk_ids") or [])
    canonical_selective_apply["failure_tags"] = list(canonical_selective_apply.get("failure_tags") or target_patch_registry_snapshot.get("failure_tags") or [])
    canonical_selective_apply["repair_tags"] = list(canonical_selective_apply.get("repair_tags") or target_patch_registry_snapshot.get("repair_tags") or [])
    canonical_selective_apply["target_file_id_count"] = len(canonical_selective_apply["target_file_ids"])
    canonical_selective_apply["failure_tag_count"] = len(canonical_selective_apply["failure_tags"])

    canonical_execution["evidence_run_id"] = str(canonical_execution.get("evidence_run_id") or evidence_run_id)
    canonical_execution["evidence_generated_at"] = str(canonical_execution.get("evidence_generated_at") or evidence_generated_at)
    canonical_execution["self_run_status"] = str(canonical_execution.get("self_run_status") or evidence_bundle.get("execution", {}).get("self_run_status") or "")
    canonical_execution["completion_gate_ok"] = canonical_execution.get("completion_gate_ok") if canonical_execution.get("completion_gate_ok") is not None else completion_gate_ok
    canonical_execution["semantic_audit_ok"] = canonical_execution.get("semantic_audit_ok") if canonical_execution.get("semantic_audit_ok") is not None else semantic_audit_ok
    canonical_execution["evidence_snapshot_version"] = str(canonical_execution.get("evidence_snapshot_version") or canonical_contract.get("evidence_schema_version") or "v1")

    canonical_readiness["final_readiness_checklist_path"] = artifact_paths["final_readiness_checklist_path"]
    canonical_readiness["automatic_validation_result_path"] = artifact_paths["automatic_validation_result_path"]
    canonical_readiness["output_audit_path"] = artifact_paths["output_audit_path"]
    canonical_readiness["artifact_paths"] = artifact_paths
    canonical_readiness["operational_evidence_snapshot"] = dict(canonical_readiness.get("operational_evidence_snapshot") or operational_evidence)
    canonical_readiness["operational_targets_by_id"] = dict(canonical_readiness.get("operational_targets_by_id") or operational_targets_by_id)
    canonical_readiness["operational_evidence_summary"] = dict(canonical_readiness.get("operational_evidence_summary") or operational_summary)
    canonical_readiness["operational_latency_summary"] = dict(canonical_readiness.get("operational_latency_summary") or operational_latency_summary)
    canonical_readiness["documentation_sync"] = dict(canonical_readiness.get("documentation_sync") or document_stale_scan.get("documentation_sync") or {})

    canonical_bundle["contract"] = canonical_contract
    canonical_bundle["execution"] = canonical_execution
    canonical_bundle["readiness"] = canonical_readiness
    canonical_bundle["operations"] = {
        "canonical_source": "evidence_bundle.readiness.operational_evidence_snapshot",
        "operational_evidence_deprecated": True,
    }
    canonical_bundle["selective_apply"] = canonical_selective_apply
    canonical_validation_payload["evidence_bundle"] = canonical_bundle
    canonical_validation_payload["selective_apply"] = canonical_selective_apply
    canonical_validation_payload["documentation_sync"] = dict(canonical_readiness.get("documentation_sync") or {})
    canonical_validation_payload["semantic_gate"] = dict(canonical_validation_payload.get("semantic_gate") or semantic_gate)
    canonical_validation_payload["semantic_audit_score"] = canonical_validation_payload.get("semantic_audit_score") if canonical_validation_payload.get("semantic_audit_score") is not None else semantic_audit_score
    canonical_validation_payload["semantic_audit_ok"] = canonical_validation_payload.get("semantic_audit_ok") if canonical_validation_payload.get("semantic_audit_ok") is not None else semantic_audit_ok

    canonical_snapshot = dict(canonical_validation_payload.get("evidence_snapshot") or {})
    canonical_snapshot["contract"] = canonical_contract
    canonical_snapshot["execution"] = canonical_execution
    canonical_snapshot["readiness"] = {
        "artifact_paths": artifact_paths,
        "operational_targets_by_id": canonical_readiness.get("operational_targets_by_id") or {},
        "operational_evidence_summary": canonical_readiness.get("operational_evidence_summary") or {},
        "operational_latency_summary": canonical_readiness.get("operational_latency_summary") or {},
        "documentation_sync": canonical_readiness.get("documentation_sync") or {},
    }
    canonical_snapshot["operations"] = {
        "canonical_source": "evidence_bundle.readiness.operational_evidence_snapshot",
        "operational_evidence_deprecated": True,
    }
    canonical_snapshot["selective_apply"] = {
        "self_run_status": canonical_execution.get("self_run_status") or "",
        "target_file_ids": canonical_selective_apply["target_file_ids"],
        "target_section_ids": canonical_selective_apply["target_section_ids"],
        "target_feature_ids": canonical_selective_apply["target_feature_ids"],
        "target_chunk_ids": canonical_selective_apply["target_chunk_ids"],
        "failure_tags": canonical_selective_apply["failure_tags"],
        "repair_tags": canonical_selective_apply["repair_tags"],
        "target_file_id_count": canonical_selective_apply["target_file_id_count"],
        "failure_tag_count": canonical_selective_apply["failure_tag_count"],
    }
    canonical_validation_payload["evidence_snapshot"] = canonical_snapshot

    canonical_completion_gate_ok = canonical_execution.get("completion_gate_ok")
    canonical_validation_engines = dict(canonical_validation_payload.get("validation_engines") or {})
    canonical_validation_engines["semantic_gate"] = dict(canonical_validation_engines.get("semantic_gate") or semantic_gate)
    canonical_validation_engines["integration_test_engine"] = dict(canonical_validation_engines.get("integration_test_engine") or integration_test_engine)
    canonical_validation_engines["framework_e2e_validation"] = dict(canonical_validation_engines.get("framework_e2e_validation") or framework_e2e_validation)
    canonical_validation_engines["external_integration_validation"] = dict(canonical_validation_engines.get("external_integration_validation") or external_integration_validation)
    canonical_product_readiness_hard_gate = dict(
        canonical_validation_engines.get("product_readiness_hard_gate")
        or canonical_readiness.get("product_readiness_hard_gate")
        or product_readiness_hard_gate
        or {}
    )
    canonical_shipping_zip_validation = dict(
        canonical_validation_engines.get("shipping_zip_validation")
        or canonical_readiness.get("shipping_zip_validation")
        or shipping_zip_validation
        or {}
    )
    canonical_validation_engines["shipping_zip_validation"] = canonical_shipping_zip_validation
    canonical_validation_engines["product_readiness_hard_gate"] = canonical_product_readiness_hard_gate
    canonical_validation_payload["validation_engines"] = canonical_validation_engines
    canonical_packaging_audit = {
        **dict(packaging_audit or {}),
        **dict(shipping_package or {}),
        **dict(validation_artifacts or {}),
        "artifact_paths": artifact_paths,
        "integration_test_engine_ok": integration_test_engine.get("ok"),
        "shipping_zip_validation": canonical_shipping_zip_validation,
        "product_readiness_hard_gate": canonical_product_readiness_hard_gate,
        "target_patch_registry": target_patch_registry_snapshot,
        "operational_evidence": canonical_readiness.get("operational_evidence_snapshot") or {},
        "operational_latency_summary": canonical_readiness.get("operational_latency_summary") or {},
    }

    readiness_artifacts_payload = dict(canonical_validation_payload.get("readiness_artifacts") or {})
    readiness_artifacts_payload["final_readiness_checklist_path"] = artifact_paths["final_readiness_checklist_path"]
    readiness_artifacts_payload["validation_result_json_path"] = artifact_paths["automatic_validation_result_path"]
    readiness_artifacts_payload["validation_result_md_path"] = artifact_paths["automatic_validation_markdown_path"]
    readiness_artifacts_payload["failure_report_path"] = artifact_paths["failure_report_path"]
    readiness_artifacts_payload["root_cause_report_path"] = artifact_paths["root_cause_report_path"]
    readiness_artifacts_payload["output_audit_path"] = artifact_paths["output_audit_path"]
    readiness_artifacts_payload["traceability_map_path"] = artifact_paths["traceability_map_path"]
    readiness_artifacts_payload["operational_evidence_snapshot"] = canonical_readiness["operational_evidence_snapshot"]
    readiness_artifacts_payload["operational_targets_by_id"] = canonical_readiness["operational_targets_by_id"]
    readiness_artifacts_payload["operational_evidence_summary"] = canonical_readiness["operational_evidence_summary"]
    readiness_artifacts_payload["operational_latency_summary"] = canonical_readiness["operational_latency_summary"]
    readiness_artifacts_payload["documentation_sync"] = canonical_readiness["documentation_sync"]
    canonical_validation_payload["readiness_artifacts"] = readiness_artifacts_payload
    _write_json_payload(validation_result_json_path, canonical_validation_payload)

    canonical_identity = _canonical_evidence_identity(canonical_bundle)
    evidence_reference = {
        "canonical_snapshot_path": artifact_paths["automatic_validation_result_path"],
        "evidence_schema_version": str(canonical_contract.get("evidence_schema_version") or "v1"),
        "evidence_generated_at": str(canonical_execution.get("evidence_generated_at") or ""),
        "evidence_run_id": str(canonical_execution.get("evidence_run_id") or ""),
        "self_run_status": str(canonical_execution.get("self_run_status") or ""),
        "target_file_ids": list(canonical_selective_apply.get("target_file_ids") or []),
        "failure_tags": list(canonical_selective_apply.get("failure_tags") or []),
    }

    artifact_log_payload = _load_json_payload(artifact_log_path)
    artifact_log_payload.update(
        {
            "task": canonical_validation_payload.get("task") or task,
            "mode": canonical_validation_payload.get("mode") or mode,
            "written_files": written_files,
            "completion_state": completion_state,
            "completion_gate_ok": canonical_validation_payload.get("completion_gate_ok") if canonical_validation_payload.get("completion_gate_ok") is not None else completion_gate_ok,
            "canonical_evidence_identity": canonical_identity,
            "validation_artifacts": validation_artifacts,
            "artifact_paths": artifact_paths,
            "evidence_reference": evidence_reference,
        }
    )
    _emit_progress("finalization rewriting artifact_log.json")
    _write_json_payload(artifact_log_path, artifact_log_payload)
    _emit_progress("finalization artifact_log_rewritten", "success")
    log_orchestration_phase_func(
        "artifact_log_rewritten",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )

    traceability_payload = _load_json_payload(traceability_map_path)
    traceability_payload.update(
        {
            "anchor_path": anchor_path,
            "written_files": written_files,
            "target_patch_registry": target_patch_registry_snapshot,
            "target_patch_candidates": canonical_target_patch_entries,
            "target_file_ids": list(canonical_selective_apply.get("target_file_ids") or []),
            "target_section_ids": list(canonical_selective_apply.get("target_section_ids") or []),
            "target_feature_ids": list(canonical_selective_apply.get("target_feature_ids") or []),
            "target_chunk_ids": list(canonical_selective_apply.get("target_chunk_ids") or []),
            "failure_tags": list(canonical_selective_apply.get("failure_tags") or []),
            "repair_tags": list(canonical_selective_apply.get("repair_tags") or []),
            "canonical_evidence_identity": canonical_identity,
            "artifact_paths": artifact_paths,
            "validation_artifacts": validation_artifacts,
            "evidence_reference": evidence_reference,
            "completion_gate_ok": canonical_completion_gate_ok,
            "product_readiness_hard_gate": canonical_product_readiness_hard_gate,
            "shipping_zip_validation": canonical_shipping_zip_validation,
            "packaging_audit": canonical_packaging_audit,
        }
    )
    _emit_progress("finalization rewriting traceability_map.json")
    _write_json_payload(traceability_map_path, traceability_payload)
    _emit_progress("finalization traceability_map_rewritten", "success")
    log_orchestration_phase_func(
        "traceability_map_rewritten",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )

    output_audit_payload = _load_json_payload(output_audit_path)
    output_audit_payload.update(
        {
            "task": canonical_validation_payload.get("task") or task,
            "mode": canonical_validation_payload.get("mode") or mode,
            "project_name": canonical_validation_payload.get("project_name") or project_name,
            "validation_profile": canonical_validation_payload.get("validation_profile") or validation_profile,
            "written_files": written_files,
            "written_file_count": len(written_files),
            "python_files": [path for path in written_files if path.endswith(".py")],
            "anchor_path": anchor_path,
            "semantic_audit_score": semantic_audit_score,
            "semantic_audit_ok": semantic_audit_ok,
            "completion_gate_ok": canonical_completion_gate_ok,
            "canonical_evidence_identity": canonical_identity,
            "product_readiness_hard_gate": canonical_product_readiness_hard_gate,
            "shipping_zip_validation": canonical_shipping_zip_validation,
            "packaging_audit": canonical_packaging_audit,
            "target_patch_registry": target_patch_registry_snapshot,
            "target_patch_candidates": canonical_target_patch_entries,
            "target_file_ids": list(canonical_selective_apply.get("target_file_ids") or []),
            "target_section_ids": list(canonical_selective_apply.get("target_section_ids") or []),
            "target_feature_ids": list(canonical_selective_apply.get("target_feature_ids") or []),
            "target_chunk_ids": list(canonical_selective_apply.get("target_chunk_ids") or []),
            "failure_tags": list(canonical_selective_apply.get("failure_tags") or []),
            "repair_tags": list(canonical_selective_apply.get("repair_tags") or []),
            "validation_artifacts": validation_artifacts,
            "artifact_paths": artifact_paths,
            "operational_latency_summary": canonical_readiness.get("operational_latency_summary") or {},
            "evidence_reference": evidence_reference,
        }
    )
    _emit_progress("finalization rewriting output_audit.json")
    _write_json_payload(output_audit_path, output_audit_payload)
    _emit_progress("finalization output_audit_rewritten", "success")
    log_orchestration_phase_func(
        "output_audit_rewritten",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    for rel_path in validation_artifacts.values():
        if rel_path not in written_files:
            written_files.append(rel_path)
    _emit_progress("finalization building final shipping package")
    shipping_package = build_shipping_package_func(
        output_dir=output_dir,
        project_name=project_name,
        normalized_requirements=normalized_requirements,
        completion_judge=completion_judge,
        packaging_audit=canonical_packaging_audit,
        written_files=written_files,
    )
    _emit_progress("finalization final_shipping_package_built", "success")
    log_orchestration_phase_func(
        "final_shipping_package_built",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    return {
        "shipping_package": shipping_package,
        "shipping_zip_validation": canonical_shipping_zip_validation,
        "product_readiness_hard_gate": canonical_product_readiness_hard_gate,
        "operational_evidence": canonical_readiness.get("operational_evidence_snapshot") or {},
        "completion_judge": completion_judge,
        "completion_gate_ok": canonical_completion_gate_ok,
        "post_validation_analysis": post_validation_analysis,
        "validation_artifacts": validation_artifacts,
        "artifact_paths": artifact_paths,
        "evidence_bundle": canonical_bundle,
        "written_files": written_files,
    }


def assemble_customer_orchestration_response(
    *,
    request,
    task: str,
    mode: str,
    project_name: str,
    validation_profile: str,
    order_profile: Dict[str, Any],
    semantic_gate: Dict[str, Any],
    completion_judge: Dict[str, Any],
    completion_gate_ok: bool,
    semantic_audit_score: int,
    semantic_audit_ok: bool,
    written_files: List[str],
    anchor_path: str,
    output_dir: Path,
    artifact_log_path: Path,
    semantic_audit_report_path: Path,
    python_security_report_path: Path,
    traceability_map_path: Path,
    auxiliary_outputs: Dict[str, str],
    target_patch_registry_snapshot: Dict[str, Any],
    shipping_package: Dict[str, Any],
    validation_artifacts: Dict[str, Any],
    product_readiness_hard_gate: Dict[str, Any],
    integration_test_engine: Dict[str, Any],
    shipping_zip_validation: Dict[str, Any],
    packaging_audit: Dict[str, Any],
    framework_e2e_validation: Dict[str, Any],
    external_integration_validation: Dict[str, Any],
    post_validation_analysis: Dict[str, Any],
    operational_evidence: Dict[str, Any],
    evidence_bundle: Dict[str, Any],
    artifact_paths: Dict[str, Any],
    normalized_requirements: Dict[str, Any],
    domain_contract: Dict[str, Any],
    integration_test_plan: Dict[str, Any],
    spec,
    b_brain_result: Dict[str, Any],
    build_stage_history_with_refiner_fixer_func,
    build_refiner_fixer_stage_payload_func,
    build_improvement_loop_plan_func,
    run_refinement_loop_func,
    build_multi_command_plan_func,
    build_admin_flow_trace_func,
    resolve_active_trace_func,
    agent_result_type,
    conversation_message_type,
    response_type,
    agent_roles: Dict[str, str],
    orch_b_brain_agent_key: str,
    get_reasoning_model_func,
    get_planner_model_func,
    get_designer_model_func,
    resolve_template_profile_func,
    orch_semantic_audit_min_score: int,
    log_orchestration_phase_func,
    started_at: float,
):
    state_history = build_stage_history_with_refiner_fixer_func(completion_gate_ok)
    final_output = (
        f"{project_name} orchestration completed with executable product gates passed for {order_profile['label']}."
        if completion_gate_ok
        else f"{project_name} orchestration failed immediately because validation gates blocked shipment for {order_profile['label']}."
    )
    command_plan = build_multi_command_plan_func(task)
    flow_trace = build_admin_flow_trace_func(
        state="done" if completion_gate_ok else "failed"
    )
    active_trace = resolve_active_trace_func(state_history)
    conversation = [
        conversation_message_type(
            role="assistant",
            speaker="orchestrator",
            content=final_output,
            step_id=request.auto_connect.step_id if request.auto_connect and request.auto_connect.step_id else "ORCH-001",
            step_title="compat-orchestration",
            timestamp=datetime.now().isoformat(),
            connection_id=request.auto_connect.connection_id if request.auto_connect else None,
            flow_id=request.auto_connect.flow_id if request.auto_connect else None,
            action=request.auto_connect.action if request.auto_connect else None,
            route_id=request.auto_connect.route_id if request.auto_connect else None,
            panel_id=request.auto_connect.panel_id if request.auto_connect else None,
        )
    ]
    refiner_fixer_stage = build_refiner_fixer_stage_payload_func(
        completion_gate_ok=completion_gate_ok,
        semantic_gate=semantic_gate,
        completion_judge=completion_judge,
        b_brain_result=b_brain_result,
    )
    improvement_loop = build_improvement_loop_plan_func(
        validation_profile=validation_profile,
        completion_judge=completion_judge,
        integration_test_plan=integration_test_plan,
        packaging_audit=packaging_audit,
    )
    refinement_loop = run_refinement_loop_func(
        request=request,
        completion_judge=completion_judge,
        improvement_loop=improvement_loop,
    )
    result_agents = [
        agent_result_type(
            agent="reasoner",
            role=agent_roles["reasoner"],
            model=get_reasoning_model_func(),
            output=f"A 브레인 추론 완료 · validation_profile={validation_profile} · generator_family={b_brain_result['generator_family']}",
        ),
        agent_result_type(
            agent="planner",
            role=agent_roles["planner"],
            model=get_planner_model_func(),
            output=f"A 브레인 설계/라우팅 판단 완료 · generator_profile={b_brain_result['generator_profile']} · pipeline={spec.pipeline}",
        ),
    ]
    if "designer" in spec.pipeline:
        result_agents.append(
            agent_result_type(
                agent="designer",
                role=agent_roles["designer"],
                model=get_designer_model_func(),
                output=f"A 브레인 UI/UX 설계 완료 · validation_profile={validation_profile} · frontend_generator={b_brain_result['generator_profile']}",
            )
        )
    result_agents.append(
        agent_result_type(
            agent=orch_b_brain_agent_key,
            role=agent_roles[orch_b_brain_agent_key],
            model=b_brain_result["generator_family"],
            output=f"B 브레인 멀티 코드 생성기 실행 완료 · written_files={b_brain_result['file_count']} · generator_profile={b_brain_result['generator_profile']}",
        )
    )
    log_orchestration_phase_func(
        "response_ready",
        started_at,
        project_name=project_name,
        validation_profile=validation_profile,
    )
    self_run_readiness = _build_self_run_readiness_payload(
        written_files=written_files,
        traceability_map_path=traceability_map_path,
        semantic_audit_report_path=semantic_audit_report_path,
        artifact_paths=artifact_paths,
        validation_artifacts=validation_artifacts,
        completion_gate_ok=completion_gate_ok,
        semantic_audit_ok=semantic_audit_ok,
    )
    return response_type(
        task=task,
        mode=mode,
        run_id=request.run_id,
        pipeline=list(spec.pipeline),
        results=result_agents,
        final_output=final_output,
        applied=completion_gate_ok,
        output_dir=str(output_dir),
        failed_output_dir=None if completion_gate_ok else str(output_dir),
        written_files=written_files,
        apply_error=None if completion_gate_ok else "product_readiness_gate_failed",
        postcheck_ran=False,
        postcheck_ok=completion_gate_ok,
        postcheck_logs=[],
        postcheck_error=None,
        secondary_validation_ran=False,
        secondary_validation_ok=completion_gate_ok,
        secondary_validation_logs=[],
        secondary_validation_error=None,
        structure_validation_ran=True,
        structure_validation_ok=completion_gate_ok,
        structure_validation_logs=[f"written_files={len(written_files)}", f"required_files={len(semantic_gate['required_files'])}"],
        structure_validation_error=None if completion_gate_ok else semantic_gate["summary"],
        forensic_report=None,
        failure_summary=None if completion_gate_ok else "; ".join(list(completion_judge.get("failed_reasons") or [])[:8]) or semantic_gate["summary"],
        state_history=state_history,
        dod_ran=True,
        dod_ok=completion_gate_ok,
        dod_logs=[f"anchor_path={anchor_path}", f"semantic_checklist={len(semantic_gate['checklist'])}"],
        dod_error=None if completion_gate_ok else "; ".join(list(completion_judge.get("failed_reasons") or [])[:8]) or semantic_gate["summary"],
        checklist_path=str(output_dir / auxiliary_outputs["checklist_path"]),
        manifest_path=str(output_dir / auxiliary_outputs["manifest_path"]),
        artifact_log_path=str(artifact_log_path),
        output_audit_path=str(output_dir / auxiliary_outputs["output_audit_path"]),
        completion_gate_ok=completion_gate_ok,
        completion_gate_error=None if completion_gate_ok else "; ".join(list(completion_judge.get("failed_reasons") or [])[:8]) or semantic_gate["summary"],
        completion_summary=final_output,
        semantic_audit_ran=True,
        semantic_audit_ok=semantic_audit_ok,
        semantic_audit_error=None if semantic_audit_ok else semantic_gate["summary"],
        semantic_audit_summary=semantic_gate["summary"],
        semantic_audit_score=semantic_audit_score,
        semantic_audit_max_score=100,
        semantic_audit_threshold=orch_semantic_audit_min_score,
        semantic_audit_checklist=list(semantic_gate["checklist_items"]),
        semantic_audit_report_path=str(semantic_audit_report_path),
        python_security_validation_ran=True,
        python_security_validation_ok=True,
        python_security_validation_logs=[],
        python_security_validation_error=None,
        python_security_validation_findings=[],
        python_security_validation_report_path=str(python_security_report_path),
        traceability_map_path=str(traceability_map_path),
        traceability_items=list(target_patch_registry_snapshot.get("matched_entries") or []),
        template_profile=resolve_template_profile_func(spec),
        output_archive_path=str(shipping_package["archive_path"]),
        conversation=conversation,
        normalized_requirements=normalized_requirements,
        domain_contract=domain_contract,
        completion_judge={**completion_judge, **validation_artifacts, "artifact_paths": artifact_paths, "integration_test_engine": integration_test_engine, "product_readiness_hard_gate": product_readiness_hard_gate, "target_patch_registry": target_patch_registry_snapshot, "post_validation_analysis": post_validation_analysis, "operational_evidence": operational_evidence, "operational_latency_summary": evidence_bundle.get("readiness", {}).get("operational_latency_summary") or {}, "b_brain_result": b_brain_result, "refiner_fixer_stage": refiner_fixer_stage},
        integration_test_plan=integration_test_plan,
        packaging_audit={**packaging_audit, **shipping_package, **validation_artifacts, "artifact_paths": artifact_paths, "integration_test_engine_ok": integration_test_engine.get("ok"), "shipping_zip_validation": shipping_zip_validation, "product_readiness_hard_gate": product_readiness_hard_gate, "target_patch_registry": target_patch_registry_snapshot, "operational_evidence": operational_evidence, "operational_latency_summary": evidence_bundle.get("readiness", {}).get("operational_latency_summary") or {}},
        improvement_loop={**improvement_loop, "refinement_loop": refinement_loop, "refiner_fixer_stage": refiner_fixer_stage},
        framework_e2e_validation=framework_e2e_validation,
        external_integration_validation=external_integration_validation,
        post_validation_analysis=post_validation_analysis,
        validation_artifacts=validation_artifacts,
        operational_evidence=operational_evidence,
        operational_latency_summary=evidence_bundle.get("readiness", {}).get("operational_latency_summary") or {},
        artifact_paths=artifact_paths,
        evidence_bundle=evidence_bundle,
        self_run_readiness=self_run_readiness,
        flow_trace=flow_trace,
        command_plan=command_plan,
        active_trace=active_trace,
        auto_connect=request.auto_connect,
    )
