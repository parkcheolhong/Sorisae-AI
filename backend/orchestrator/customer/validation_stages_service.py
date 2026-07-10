"""고객 오케스트레이션 중간 스테이지(생성→검증→아티팩트) 서비스 (orchestrator.py 에서 분리).

prepare 결과를 받아 b-brain 생성·compat manifest·semantic gate·packaging audit·통합/프레임워크/외부
검증·completion judge(1차)·seed/aux 아티팩트 기록을 수행하고, finalize/assemble 단계로 넘길 번들을 반환한다.
orchestrator.py 를 import 하지 않으며, 필요한 함수·상수는 모두 DI(키워드 인자, 원본과 동일 이름)로 받는다.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict

from backend.time_utils import utcnow

logger = logging.getLogger(__name__)


async def run_customer_validation_stages(
    *,
    request,
    task,
    mode,
    order_profile,
    validation_profile,
    compat_required_files,
    normalized_requirements,
    domain_contract,
    integration_test_plan,
    project_name,
    output_dir,
    started_at,
    progress_callback,
    # ── 주입 함수(orchestrator 소유, 원본과 동일 이름) ──
    _log_orchestration_phase,
    _emit_orchestration_progress,
    _run_b_brain_multi_generator,
    _compat_manifest_for_request,
    _compat_write_manifest,
    _compat_run_semantic_gate,
    _build_packaging_audit,
    _run_domain_integration_test_engine,
    _run_framework_e2e_validator,
    _run_external_integration_validator,
    _build_completion_judge,
    _build_operational_evidence_bundle,
    build_target_patch_registry_snapshot,
    _compat_write_json,
    _compat_write_auxiliary_outputs,
    _compat_relative_path,
    # ── 주입 상수(경로/임계) ──
    ORCH_MIN_FILES,
    ORCH_MIN_DIRS,
    ORCH_SEMANTIC_AUDIT_MIN_SCORE,
    ORCH_ARTIFACT_LOG_PATH,
    ORCH_TRACEABILITY_MAP_PATH,
    ORCH_SEMANTIC_AUDIT_REPORT_PATH,
    ORCH_PYTHON_SECURITY_REPORT_PATH,
    ORCH_VALIDATION_RESULT_JSON_PATH,
    ORCH_VALIDATION_RESULT_MD_PATH,
    ORCH_FAILURE_REPORT_PATH,
    ORCH_ROOT_CAUSE_REPORT_PATH,
    ORCH_OUTPUT_AUDIT_PATH,
    ORCH_ID_REGISTRY_PATH,
    ORCH_ID_REGISTRY_SCHEMA_PATH,
) -> Dict[str, Any]:
    b_brain_result = _run_b_brain_multi_generator(
        project_name=project_name,
        validation_profile=validation_profile,
        task=task,
        output_dir=output_dir,
    )
    _log_orchestration_phase("generator_bundle_written", started_at, project_name=project_name, validation_profile=validation_profile)
    anchor_path, manifest, completion_state = _compat_manifest_for_request(task, project_name, validation_profile, compat_required_files)
    written_files = _compat_write_manifest(output_dir, manifest)
    for generated_file in b_brain_result["written_files"]:
        if generated_file not in written_files:
            written_files.append(generated_file)
    _emit_orchestration_progress(progress_callback, f"초기 산출물 {len(written_files)}개를 생성했습니다.")
    _log_orchestration_phase("compat_manifest_written", started_at, project_name=project_name, validation_profile=validation_profile)

    semantic_manifest_by_path: Dict[str, Dict[str, str]] = {}
    for relative_path in written_files:
        normalized_path = str(relative_path or "").replace("\\", "/").strip()
        if not normalized_path:
            continue
        file_path = output_dir / normalized_path
        if not file_path.exists() or not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        semantic_manifest_by_path[normalized_path] = {
            "path": normalized_path,
            "content": content,
        }
    semantic_manifest = list(semantic_manifest_by_path.values()) or manifest
    semantic_gate = _compat_run_semantic_gate(task, project_name, order_profile, validation_profile, semantic_manifest)
    _emit_orchestration_progress(
        progress_callback,
        (
            "semantic gate 통과"
            if not semantic_gate.get("checklist")
            else f"semantic gate findings: {'; '.join(list(semantic_gate.get('checklist') or [])[:3])}"
        ),
        "success" if not semantic_gate.get("checklist") else "error",
    )
    _log_orchestration_phase("semantic_gate_finished", started_at, project_name=project_name, validation_profile=validation_profile)
    packaging_audit = _build_packaging_audit(order_profile, compat_required_files, written_files)
    _emit_orchestration_progress(progress_callback, "post-semantic stage: packaging audit computed")
    logger.info(
        "run_orchestration about_to_call_integration_test_engine elapsed_sec=%.2f project=%s validation_profile=%s output_dir=%s",
        max(0.0, time.perf_counter() - started_at),
        project_name,
        validation_profile,
        str(output_dir),
    )
    integration_test_engine = await asyncio.to_thread(
        _run_domain_integration_test_engine,
        output_dir=output_dir,
        validation_profile=validation_profile,
        integration_test_plan=integration_test_plan,
    )
    _emit_orchestration_progress(
        progress_callback,
        (
            "integration test engine 통과"
            if integration_test_engine.get("ok")
            else f"integration test engine findings: {'; '.join(list(integration_test_engine.get('failures') or [])[:3])}"
        ),
        "success" if integration_test_engine.get("ok") else "error",
    )
    logger.info(
        "run_orchestration returned_from_integration_test_engine elapsed_sec=%.2f project=%s validation_profile=%s integration_ok=%s failure_count=%s",
        max(0.0, time.perf_counter() - started_at),
        project_name,
        validation_profile,
        bool(integration_test_engine.get("ok")),
        len(list(integration_test_engine.get("failures") or [])),
    )
    _log_orchestration_phase("integration_test_engine_finished", started_at, project_name=project_name, validation_profile=validation_profile)
    framework_e2e_validation = await asyncio.to_thread(
        _run_framework_e2e_validator,
        output_dir=output_dir,
        validation_profile=validation_profile,
    )
    _emit_orchestration_progress(
        progress_callback,
        "framework e2e validation 통과" if framework_e2e_validation.get("ok") else f"framework e2e findings: {'; '.join(list(framework_e2e_validation.get('failures') or [])[:3])}",
        "success" if framework_e2e_validation.get("ok") else "error",
    )
    _log_orchestration_phase("framework_e2e_finished", started_at, project_name=project_name, validation_profile=validation_profile)
    external_integration_validation = _run_external_integration_validator(
        output_dir=output_dir,
        order_profile=order_profile,
    )
    _emit_orchestration_progress(
        progress_callback,
        "external integration validation 통과" if external_integration_validation.get("ok") else f"external integration findings: {'; '.join(list(external_integration_validation.get('failures') or [])[:3])}",
        "success" if external_integration_validation.get("ok") else "error",
    )
    _log_orchestration_phase("external_integration_finished", started_at, project_name=project_name, validation_profile=validation_profile)
    completion_judge = _build_completion_judge(
        semantic_gate=semantic_gate,
        packaging_audit=packaging_audit,
        integration_test_engine=integration_test_engine,
        normalized_requirements=normalized_requirements,
        integration_test_plan=integration_test_plan,
        completion_state=completion_state,
        framework_e2e_validation=framework_e2e_validation,
        external_integration_validation=external_integration_validation,
        shipping_zip_validation={"ok": False, "checks_run": [], "failures": ["shipping zip reproduction validation not yet executed"]},
        operational_evidence=_build_operational_evidence_bundle(),
        output_dir=output_dir,
        written_files=written_files,
        domain_contract=domain_contract,
        min_files=ORCH_MIN_FILES,
        min_dirs=ORCH_MIN_DIRS,
    )
    _emit_orchestration_progress(progress_callback, "post-validation stage: completion judge computed")
    semantic_audit_score = int(semantic_gate["score"])
    semantic_audit_ok = bool(semantic_gate["ok"]) and semantic_audit_score >= ORCH_SEMANTIC_AUDIT_MIN_SCORE

    artifact_log_path = output_dir / ORCH_ARTIFACT_LOG_PATH
    traceability_map_path = output_dir / ORCH_TRACEABILITY_MAP_PATH
    semantic_audit_report_path = output_dir / ORCH_SEMANTIC_AUDIT_REPORT_PATH
    python_security_report_path = output_dir / ORCH_PYTHON_SECURITY_REPORT_PATH
    target_patch_registry_snapshot = build_target_patch_registry_snapshot(
        written_files=written_files,
        target_paths=[anchor_path, "backend/llm/admin_capabilities.py", "frontend/frontend/app/admin/llm/page.tsx"],
        capability_ids=["code-generator", "self-healing-engine", "project-scanner"],
    )
    _emit_orchestration_progress(progress_callback, "post-validation stage: target patch registry computed")
    artifact_paths_seed = {
        "artifact_log_path": ORCH_ARTIFACT_LOG_PATH,
        "traceability_map_path": ORCH_TRACEABILITY_MAP_PATH,
        "semantic_audit_report_path": ORCH_SEMANTIC_AUDIT_REPORT_PATH,
        "python_security_validation_report_path": ORCH_PYTHON_SECURITY_REPORT_PATH,
        "final_readiness_checklist_path": "docs/final_readiness_checklist.md",
        "automatic_validation_result_path": ORCH_VALIDATION_RESULT_JSON_PATH,
        "automatic_validation_markdown_path": ORCH_VALIDATION_RESULT_MD_PATH,
        "failure_report_path": ORCH_FAILURE_REPORT_PATH,
        "root_cause_report_path": ORCH_ROOT_CAUSE_REPORT_PATH,
        "output_audit_path": ORCH_OUTPUT_AUDIT_PATH,
    }
    evidence_bundle_seed = {
        "contract": {
            "evidence_schema_version": "v1",
            "profile_id": validation_profile,
        },
        "execution": {
            "evidence_run_id": request.run_id or task,
            "evidence_generated_at": utcnow().isoformat() + "Z",
        },
        "readiness": {
            "artifact_paths": dict(artifact_paths_seed),
        },
        "snapshot": {
            "artifact_paths": dict(artifact_paths_seed),
        },
        "selective_apply": {
            "target_file_ids": list(target_patch_registry_snapshot.get("target_file_ids") or []),
            "target_section_ids": list(target_patch_registry_snapshot.get("target_section_ids") or []),
            "target_feature_ids": list(target_patch_registry_snapshot.get("target_feature_ids") or []),
            "target_chunk_ids": list(target_patch_registry_snapshot.get("target_chunk_ids") or []),
            "failure_tags": list(target_patch_registry_snapshot.get("failure_tags") or []),
            "repair_tags": list(target_patch_registry_snapshot.get("repair_tags") or []),
        },
    }
    _compat_write_json(artifact_log_path, {"task": task, "mode": mode, "written_files": written_files, "completion_state": completion_state, "evidence_bundle": evidence_bundle_seed})
    _compat_write_json(traceability_map_path, {
        "anchor_path": anchor_path,
        "written_files": written_files,
        "target_patch_registry": target_patch_registry_snapshot,
        "target_patch_candidates": list(target_patch_registry_snapshot.get("matched_entries") or []),
        "target_file_ids": list(target_patch_registry_snapshot.get("target_file_ids") or []),
        "target_section_ids": list(target_patch_registry_snapshot.get("target_section_ids") or []),
        "target_feature_ids": list(target_patch_registry_snapshot.get("target_feature_ids") or []),
        "target_chunk_ids": list(target_patch_registry_snapshot.get("target_chunk_ids") or []),
        "failure_tags": list(target_patch_registry_snapshot.get("failure_tags") or []),
        "repair_tags": list(target_patch_registry_snapshot.get("repair_tags") or []),
        "id_registry_path": ORCH_ID_REGISTRY_PATH,
        "id_registry_schema_path": ORCH_ID_REGISTRY_SCHEMA_PATH,
        "evidence_bundle": evidence_bundle_seed,
    })
    _compat_write_json(python_security_report_path, {"ok": True, "findings": []})
    _emit_orchestration_progress(progress_callback, "post-validation stage: seed artifacts written")
    semantic_audit_report_path.parent.mkdir(parents=True, exist_ok=True)
    semantic_audit_report_path.write_text(
        "# Semantic Completion Audit\n\n"
        f"- score: {semantic_audit_score}\n"
        f"- threshold: {ORCH_SEMANTIC_AUDIT_MIN_SCORE}\n"
        f"- status: {'pass' if semantic_audit_ok else 'fail'}\n",
        encoding="utf-8",
    )
    auxiliary_outputs = _compat_write_auxiliary_outputs(
        output_dir,
        task,
        project_name,
        mode,
        validation_profile,
        written_files,
        anchor_path,
        semantic_audit_score,
        semantic_audit_ok,
        target_patch_registry_snapshot,
    )
    _emit_orchestration_progress(progress_callback, "post-validation stage: auxiliary outputs written")
    generated_meta_paths = [
        _compat_relative_path(artifact_log_path, output_dir),
        _compat_relative_path(traceability_map_path, output_dir),
        _compat_relative_path(semantic_audit_report_path, output_dir),
        _compat_relative_path(python_security_report_path, output_dir),
    ]
    for rel_path in generated_meta_paths:
        if rel_path not in written_files:
            written_files.append(rel_path)
    for rel_path in auxiliary_outputs.values():
        if rel_path not in written_files:
            written_files.append(rel_path)
    written_files = list(dict.fromkeys(sorted(written_files)))
    artifact_paths_seed["checklist_path"] = str(auxiliary_outputs.get("checklist_path") or "")
    artifact_paths_seed["manifest_path"] = str(auxiliary_outputs.get("manifest_path") or "")
    evidence_bundle_seed.setdefault("readiness", {})["artifact_paths"] = dict(artifact_paths_seed)
    evidence_bundle_seed.setdefault("snapshot", {})["artifact_paths"] = dict(artifact_paths_seed)
    _compat_write_json(artifact_log_path, {"task": task, "mode": mode, "written_files": written_files, "completion_state": completion_state, "evidence_bundle": evidence_bundle_seed})
    _compat_write_json(traceability_map_path, {
        "anchor_path": anchor_path,
        "written_files": written_files,
        "target_patch_registry": target_patch_registry_snapshot,
        "target_patch_candidates": list(target_patch_registry_snapshot.get("matched_entries") or []),
        "target_file_ids": list(target_patch_registry_snapshot.get("target_file_ids") or []),
        "target_section_ids": list(target_patch_registry_snapshot.get("target_section_ids") or []),
        "target_feature_ids": list(target_patch_registry_snapshot.get("target_feature_ids") or []),
        "target_chunk_ids": list(target_patch_registry_snapshot.get("target_chunk_ids") or []),
        "failure_tags": list(target_patch_registry_snapshot.get("failure_tags") or []),
        "repair_tags": list(target_patch_registry_snapshot.get("repair_tags") or []),
        "id_registry_path": ORCH_ID_REGISTRY_PATH,
        "id_registry_schema_path": ORCH_ID_REGISTRY_SCHEMA_PATH,
        "artifact_paths": artifact_paths_seed,
        "evidence_bundle": evidence_bundle_seed,
    })
    _emit_orchestration_progress(progress_callback, f"메타 파일 포함 총 {len(written_files)}개 산출물을 정리했습니다.", "success")
    _emit_orchestration_progress(progress_callback, "finalization dispatch 시작")
    _log_orchestration_phase("validation_artifacts_written", started_at, project_name=project_name, validation_profile=validation_profile)
    _log_orchestration_phase("finalization_dispatch", started_at, project_name=project_name, validation_profile=validation_profile)
    return {
        "b_brain_result": b_brain_result,
        "written_files": written_files,
        "anchor_path": anchor_path,
        "completion_state": completion_state,
        "semantic_gate": semantic_gate,
        "packaging_audit": packaging_audit,
        "integration_test_engine": integration_test_engine,
        "framework_e2e_validation": framework_e2e_validation,
        "external_integration_validation": external_integration_validation,
        "completion_judge": completion_judge,
        "semantic_audit_score": semantic_audit_score,
        "semantic_audit_ok": semantic_audit_ok,
        "target_patch_registry_snapshot": target_patch_registry_snapshot,
        "artifact_log_path": artifact_log_path,
        "traceability_map_path": traceability_map_path,
        "semantic_audit_report_path": semantic_audit_report_path,
        "python_security_report_path": python_security_report_path,
        "auxiliary_outputs": auxiliary_outputs,
    }
