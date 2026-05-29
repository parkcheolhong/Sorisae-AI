"""
customer_orchestrate_context.py
────────────────────────────────────────────────────────────────────────────
고객 오케스트레이터 실행 컨텍스트 유틸리티.

- 실행 로그/재시도 큐 헬퍼 (_compose_trace_fields, _write_feature_execution_log,
  _enqueue_feature_retry_record)
- 고객 요청 Pydantic 모델
- 고객 오케스트레이터 실행 단계별 헬퍼 전반
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import models
from backend.orchestration_stage_service import (
    ORCHESTRATION_STAGE_DEFINITIONS,
    build_stage_tracking_payload,
    initialize_stage_run,
    load_stage_run,
    save_stage_run,
    update_stage_run,
)
from backend.orchestrator.chat import (
    OrchestratorStageChatContext,
)

# ─────────────────────────────────────────────────────────────────────────────
# 모듈-레벨 실행 잠금 (router.py에서도 import해서 동일 객체를 공유)
# ─────────────────────────────────────────────────────────────────────────────
_customer_orchestrate_run_locks: Dict[str, threading.Lock] = {}
_customer_orchestrate_run_locks_guard = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# 실행 추적 유틸리티
# ─────────────────────────────────────────────────────────────────────────────

def _compose_trace_fields(flow_id: str, step_id: str, action: str) -> Dict[str, str]:
    return {
        "flow_id": flow_id,
        "step_id": step_id,
        "action": action,
        "trace_id": f"{flow_id}:{step_id}:{action}",
    }


def _write_feature_execution_log(
    db: Session,
    *,
    user_id: Optional[int],
    entity_type: str,
    entity_id: str,
    flow_id: str,
    step_id: str,
    action: str,
    status: str,
    message: str,
    payload: Optional[Dict[str, Any]] = None,
) -> models.FeatureExecutionLog:
    trace_fields = _compose_trace_fields(flow_id, step_id, action)
    row = models.FeatureExecutionLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        flow_id=trace_fields["flow_id"],
        step_id=trace_fields["step_id"],
        action=trace_fields["action"],
        trace_id=trace_fields["trace_id"],
        status=status,
        message=message,
        payload_json=(json.dumps(payload, ensure_ascii=False) if payload is not None else None),
    )
    db.add(row)
    db.flush()


def _enqueue_feature_retry_record(
    db: Session,
    *,
    user_id: Optional[int],
    entity_type: str,
    entity_id: str,
    flow_id: str,
    step_id: str,
    action: str,
    queue_name: str,
    payload: Optional[Dict[str, Any]] = None,
    last_error: Optional[str] = None,
    status: str = "queued",
    attempt_count: int = 0,
) -> models.FeatureRetryQueue:
    trace_fields = _compose_trace_fields(flow_id, step_id, action)
    row = models.FeatureRetryQueue(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        flow_id=trace_fields["flow_id"],
        step_id=trace_fields["step_id"],
        action=trace_fields["action"],
        trace_id=trace_fields["trace_id"],
        queue_name=queue_name,
        status=status,
        payload_json=(json.dumps(payload, ensure_ascii=False) if payload is not None else None),
        last_error=last_error,
        attempt_count=attempt_count,
    )
    db.add(row)
    db.flush()
    return row


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic 요청/응답 모델
# ─────────────────────────────────────────────────────────────────────────────

class CustomerOrchestrateRequest(BaseModel):
    task: str
    mode: str = "auto"
    project_name: Optional[str] = None
    output_dir: Optional[str] = None
    allow_new_output_dir: bool = False
    refinement_request: Optional[str] = None
    max_improvement_cycles: int = 1
    stage_run_id: Optional[str] = None
    stage_id: Optional[str] = None
    manual_correction: Optional[str] = None


class CustomerOrchestrateStageUpdateRequest(BaseModel):
    run_id: str
    stage_id: str
    status: str
    note: str = ""
    manual_correction: str = ""
    substep_checks: Optional[Dict[str, bool]] = None
    revision_note: str = ""


class CustomerOrchestratorChatRequest(BaseModel):
    message: str
    task: str = ""
    conversation: List[Dict[str, Any]] = []
    run_id: Optional[str] = None
    session_id: Optional[str] = None
    stage_id: Optional[str] = None
    project_name: Optional[str] = None
    output_dir: Optional[str] = None
    project_memory: Dict[str, Any] = {}
    context_tags: List[str] = []
    conversation_mode: str = "auto"
    companion_mode: str = "hybrid"
    response_style: str = "balanced"
    tone_preset: str = "auto"
    reverse_question_mode: Optional[str] = None
    max_tokens: int = 768


class CustomerOrchestrateAcceptedResponse(BaseModel):
    accepted: bool = True
    run_id: Optional[str] = None
    stage_run: Optional[Dict[str, Any]] = None
    status: str = "accepted"
    message: str = "고객 오케스트레이터 요청을 수락했습니다. 이어지는 stream 호출에서 실제 실행 결과를 반환합니다."


class CustomerPublishRequest(BaseModel):
    output_dir: str
    title: str
    description: str
    price: float = 99000
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    demo_url: Optional[str] = None
    github_url: Optional[str] = None
    tags: Optional[List[str]] = None


class CustomerGeneratedProgramSummary(BaseModel):
    output_dir: Optional[str] = None
    output_archive_path: Optional[str] = None
    delivery_gate_blocked: bool = False
    delivery_gate_message: Optional[str] = None
    publish_ready: bool = False
    publish_targets: List[str] = []
    shipping_zip_ok: bool = False
    validation_profile: Optional[str] = None
    required_tests: List[str] = []
    priority_average_score: int = 0
    priority_peak_score: int = 0
    priority_latest_score: int = 0
    priority_previous_score: Optional[int] = None
    priority_momentum: int = 0
    priority_cumulative_score: int = 0
    approval_history_count: int = 0
    stage_run_status: Optional[str] = None
    hard_gate_failed_stages: List[str] = []


# ─────────────────────────────────────────────────────────────────────────────
# 고객 오케스트레이터 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _build_customer_stage_chat_context(
    stage_run: Optional[Dict[str, Any]],
    request: CustomerOrchestratorChatRequest,
) -> OrchestratorStageChatContext:
    active_stage: Dict[str, Any] = {}
    if isinstance(stage_run, dict):
        active_stage = next(
            (
                stage
                for stage in (stage_run.get("stages") or [])
                if stage.get("id") == stage_run.get("current_stage_id")
            ),
            {},
        ) or {}
    return OrchestratorStageChatContext(
        run_id=str((stage_run or {}).get("run_id") or request.run_id or "") or None,
        stage_id=str((active_stage or {}).get("id") or request.stage_id or "") or None,
        stage_label=str((active_stage or {}).get("label") or "") or None,
        stage_title=str((active_stage or {}).get("title") or "") or None,
        stage_status=str((active_stage or {}).get("status") or (stage_run or {}).get("status") or "running") or None,
        scope=str((stage_run or {}).get("scope") or "marketplace") or None,
        project_name=str((stage_run or {}).get("project_name") or request.project_name or "") or None,
        pending_revision_note=str(request.message or "").strip() or None,
        last_command=(
            str(request.message or "").strip().split()[0]
            if str(request.message or "").strip().startswith("/")
            else None
        ),
    )


def _build_customer_orchestrate_sse_event(event: str, payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps({'event': event, 'payload': payload}, ensure_ascii=False)}\n\n"


def _get_customer_orchestrate_run_lock(run_id: str) -> threading.Lock:
    with _customer_orchestrate_run_locks_guard:
        lock = _customer_orchestrate_run_locks.get(run_id)
        if lock is None:
            lock = threading.Lock()
            _customer_orchestrate_run_locks[run_id] = lock
        return lock


def _get_customer_stage_execution_metadata(stage_run_payload: Dict[str, Any]) -> Dict[str, Any]:
    metadata = dict(stage_run_payload.get("metadata") or {})
    return dict(metadata.get("orchestration_execution") or {})


def _update_customer_stage_execution_metadata(run_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    payload = load_stage_run(run_id)
    if not payload:
        return None
    metadata = dict(payload.get("metadata") or {})
    execution_metadata = dict(metadata.get("orchestration_execution") or {})
    execution_metadata.update(fields)
    metadata["orchestration_execution"] = execution_metadata
    payload["metadata"] = metadata
    return save_stage_run(payload)


def _guard_customer_orchestrate_execution(stage_run_payload: Dict[str, Any]) -> None:
    execution_metadata = _get_customer_stage_execution_metadata(stage_run_payload)
    execution_status = str(execution_metadata.get("status") or "").strip().lower()
    if execution_status == "running":
        raise HTTPException(status_code=409, detail="같은 stage run 생성이 이미 실행 중입니다.")
    if execution_status == "completed":
        raise HTTPException(status_code=409, detail="이미 생성이 끝난 stage run입니다. 새 stage run으로 다시 시작하세요.")


def _ensure_customer_stage_run_payload(
    request: CustomerOrchestrateRequest,
    current_user: models.User,
) -> Dict[str, Any]:
    stage_run_payload = _resolve_stage_run_for_request(request, current_user)
    if not stage_run_payload:
        raise HTTPException(status_code=404, detail="고객 stage run을 찾을 수 없습니다.")
    return stage_run_payload


async def _run_customer_orchestration_request(orchestration_request: Any) -> Any:
    from backend.llm.orchestrator import execute_orchestration as execute_orchestration_handler

    return await execute_orchestration_handler(orchestration_request)


def _build_customer_orchestrate_result_payload(
    *,
    response: Any,
    request: CustomerOrchestrateRequest,
    current_user: models.User,
    stage_run_payload: Dict[str, Any],
) -> Dict[str, Any]:
    result_payload = _normalize_customer_orchestrate_result_payload(response, request.task)
    synced_stage_run = _sync_stage_run_after_result(
        stage_run_id=str(stage_run_payload.get("run_id") or request.stage_run_id or "").strip() or None,
        stage_id=str(request.stage_id or stage_run_payload.get("current_stage_id") or "ARCH-001").strip() or None,
        result_payload=result_payload,
    )
    if synced_stage_run:
        result_payload["stage_run"] = synced_stage_run
    return {
        "requested_by": {
            "id": getattr(current_user, "id", None),
            "email": getattr(current_user, "email", None),
        },
        "result": result_payload,
    }


def _build_customer_orchestrate_error_payload(
    *,
    error_message: str,
    request: CustomerOrchestrateRequest,
    stage_run_payload: Dict[str, Any],
) -> Dict[str, Any]:
    stage_run_error_payload = {
        "completion_summary": "고객 오케스트레이터 실행 실패",
        "failure_summary": error_message,
        "apply_error": error_message,
        "completion_gate_error": error_message,
        "completion_judge": {
            "product_ready": False,
            "failed_reasons": [error_message],
        },
    }
    synced_stage_run = _sync_stage_run_after_result(
        stage_run_id=str(stage_run_payload.get("run_id") or request.stage_run_id or "").strip() or None,
        stage_id=str(request.stage_id or stage_run_payload.get("current_stage_id") or "ARCH-001").strip() or None,
        result_payload=stage_run_error_payload,
        error_message=error_message,
    )
    payload: Dict[str, Any] = {"message": error_message}
    if synced_stage_run:
        payload["stage_run"] = synced_stage_run
    return payload


_CUSTOMER_ORCHESTRATE_TRACKING_KEY_MAP = {
    "현재 아키텍처 단계 ID": "architecture_id",
    "active_flow_id": "flow_id",
    "active_step_id": "step_id",
    "active_action": "action",
    "next_architecture_id": "next_architecture_id",
    "next_flow_step_id": "next_step_id",
    "next_flow_action": "next_action",
}


def _extract_customer_orchestrate_tracking_context(task: str) -> Dict[str, Optional[str]]:
    tracking: Dict[str, Optional[str]] = {
        "architecture_id": None,
        "flow_id": None,
        "step_id": None,
        "action": None,
        "next_architecture_id": None,
        "next_step_id": None,
        "next_action": None,
    }
    for raw_line in str(task or "").splitlines():
        line = raw_line.strip()
        match = re.match(r"^-\s*([^:]+):\s*(.+)$", line)
        if not match:
            continue
        raw_key = match.group(1).strip()
        raw_value = match.group(2).strip()
        mapped_key = _CUSTOMER_ORCHESTRATE_TRACKING_KEY_MAP.get(raw_key)
        if not mapped_key:
            continue
        if raw_value in {"-", "END", ""}:
            tracking[mapped_key] = raw_value
        else:
            tracking[mapped_key] = raw_value
    return tracking


def _normalize_customer_orchestrate_result_payload(result: Any, task: str) -> Dict[str, Any]:
    if hasattr(result, "model_dump"):
        payload = result.model_dump()
    elif isinstance(result, dict):
        payload = dict(result)
    else:
        payload = {"result": result}

    tracking = _extract_customer_orchestrate_tracking_context(task)
    payload.update({key: value for key, value in tracking.items() if value})
    payload["marketplace_delivery_gate"] = {
        "product_ready": bool((payload.get("completion_judge") or {}).get("product_ready")),
        "packaging_ready": bool((payload.get("packaging_audit") or {}).get("packaging_ready")),
        "required_tests": list((payload.get("integration_test_plan") or {}).get("required_tests") or []),
        "marketplace_quality_aligned": bool(payload.get("completion_gate_ok")),
        "output_archive_path": payload.get("output_archive_path"),
        "shipping_readme_path": (payload.get("packaging_audit") or {}).get("shipping_readme_path"),
        "operations_guide_path": (payload.get("packaging_audit") or {}).get("operations_guide_path"),
        "integration_test_engine_ok": bool(
            ((payload.get("completion_judge") or {}).get("integration_test_engine") or {}).get("ok")
        ),
        "improvement_loop_enabled": bool(
            (payload.get("completion_judge") or {}).get("improvement_loop_enabled")
        ),
        "improvement_loop_strategy": list(
            (payload.get("completion_judge") or {}).get("improvement_loop_strategy") or []
        ),
        "improvement_loop": payload.get("improvement_loop") or {},
        "framework_e2e_validation": payload.get("framework_e2e_validation") or {},
        "external_integration_validation": payload.get("external_integration_validation") or {},
    }
    payload.setdefault("orchestration_stage_definitions", ORCHESTRATION_STAGE_DEFINITIONS)
    return payload


def _persist_customer_orchestrator_completion(
    db: Session,
    *,
    current_user: models.User,
    request: CustomerOrchestrateRequest,
    result_payload: Dict[str, Any],
) -> None:
    completion = models.CustomerOrchestratorCompletion(
        user_id=current_user.id,
        trace_id=str(result_payload.get("trace_id") or "") or None,
        flow_id=str(result_payload.get("flow_id") or "") or None,
        step_id=str(result_payload.get("step_id") or "") or None,
        action=str(result_payload.get("action") or "") or None,
        project_name=((request.project_name or "customer-product").strip() or "customer-product"),
        mode=str(request.mode or "auto").strip() or "auto",
        attempts=1,
        output_dir=str(result_payload.get("output_dir") or "") or None,
        postcheck_ok=result_payload.get("postcheck_ok"),
        gate_passed=bool((result_payload.get("completion_judge") or {}).get("product_ready")),
        override_used=False,
    )
    db.add(completion)
    _write_feature_execution_log(
        db,
        user_id=current_user.id,
        entity_type="customer_orchestrator_completion",
        entity_id=str(completion.project_name),
        flow_id=str(result_payload.get("flow_id") or "FLOW-001"),
        step_id=str(result_payload.get("step_id") or "FLOW-001-4"),
        action=str(result_payload.get("action") or "SAVE_COMPLETION"),
        status="saved",
        message="고객 오케스트레이터 completion 자동 저장",
        payload={
            "project_name": completion.project_name,
            "mode": completion.mode,
            "output_dir": completion.output_dir,
            "postcheck_ok": completion.postcheck_ok,
            "gate_passed": completion.gate_passed,
            "completion_gate_ok": result_payload.get("completion_gate_ok"),
            "failed_reasons": list(
                (result_payload.get("completion_judge") or {}).get("failed_reasons") or []
            ),
        },
    )


def _resolve_stage_run_for_request(
    request: CustomerOrchestrateRequest,
    current_user: models.User,
) -> Optional[Dict[str, Any]]:
    if request.stage_run_id:
        return load_stage_run(request.stage_run_id)
    project_name = (request.project_name or "customer-product").strip() or "customer-product"
    return initialize_stage_run(
        scope="marketplace",
        project_name=project_name,
        mode=request.mode,
        requested_by={
            "id": current_user.id,
            "email": getattr(current_user, "email", ""),
        },
        metadata={
            "task": request.task,
        },
    )


def _merge_stage_tracking_into_task(
    task: str,
    stage_id: str,
    manual_correction: Optional[str] = None,
) -> str:
    tracking_payload = build_stage_tracking_payload(stage_id)
    if not tracking_payload:
        return task
    lines = [str(task or "").strip(), "", "[9단계 Stage Tracking]"]
    for key, value in tracking_payload.items():
        if key == "architecture_id":
            lines.append(f"- 현재 아키텍처 단계 ID: {value}")
        elif key == "flow_id":
            lines.append(f"- active_flow_id: {value}")
        elif key == "step_id":
            lines.append(f"- active_step_id: {value}")
        elif key == "action":
            lines.append(f"- active_action: {value}")
        elif key == "next_architecture_id":
            lines.append(f"- next_architecture_id: {value}")
        elif key == "next_step_id":
            lines.append(f"- next_flow_step_id: {value}")
        elif key == "next_action":
            lines.append(f"- next_flow_action: {value}")
    if str(manual_correction or "").strip():
        lines.extend(["", "[수동 보정 메모]", str(manual_correction or "").strip()])
    return "\n".join(lines).strip()


def _sync_stage_run_after_result(
    *,
    stage_run_id: Optional[str],
    stage_id: Optional[str],
    result_payload: Dict[str, Any],
    error_message: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not stage_run_id or not stage_id:
        return None
    normalized_stage_id = str(stage_id or "").strip().upper()
    if not normalized_stage_id:
        return None

    completion_judge = result_payload.get("completion_judge") or {}
    product_ready = bool(completion_judge.get("product_ready"))
    apply_error = str(result_payload.get("apply_error") or "").strip()
    postcheck_error = str(result_payload.get("postcheck_error") or "").strip()
    completion_gate_error = str(result_payload.get("completion_gate_error") or "").strip()
    failure_summary = str(result_payload.get("failure_summary") or "").strip()
    combined_error = error_message or apply_error or postcheck_error or completion_gate_error or failure_summary

    scaffold_only = bool(completion_judge.get("scaffold_only"))
    next_status = "passed" if product_ready and not combined_error and not scaffold_only else "manual_correction"
    note_parts = [
        str(result_payload.get("completion_summary") or "").strip(),
        combined_error,
        "; ".join(list(completion_judge.get("failed_reasons") or [])[:8]),
    ]
    note = "\n".join([part for part in note_parts if part])

    synced = update_stage_run(
        run_id=stage_run_id,
        stage_id=normalized_stage_id,
        status=next_status,
        note=note,
        manual_correction=combined_error if next_status != "passed" else "",
    )
    if next_status == "passed":
        synced["status"] = "completed"
        synced["final_completed"] = True
        synced["current_stage_id"] = normalized_stage_id
        for stage in list(synced.get("stages") or []):
            if str(stage.get("id") or "").upper() == normalized_stage_id:
                continue
            if str(stage.get("status") or "").lower() == "running":
                stage["status"] = "pending"
                stage["check_label"] = "대기"
        synced = save_stage_run(synced)
    return synced


def _build_customer_orchestrate_log_event(
    message: str,
    level: str,
    tracking: Optional[Dict[str, Optional[str]]] = None,
) -> Dict[str, Any]:
    event: Dict[str, Any] = {
        "event": "log",
        "level": level,
        "message": message,
    }
    if tracking:
        if tracking.get("flow_id"):
            event["flow_id"] = tracking["flow_id"]
        if tracking.get("step_id"):
            event["step_id"] = tracking["step_id"]
        if tracking.get("action"):
            event["action"] = tracking["action"]
    return event


def _customer_follow_up_history_path() -> Path:
    runtime_root = (
        Path(os.getenv("ADMIN_RUNTIME_ROOT", "")).expanduser().resolve()
        if os.getenv("ADMIN_RUNTIME_ROOT", "").strip()
        else (Path(tempfile.gettempdir()) / "codeai_admin_runtime").resolve()
    )
    return runtime_root / "capability_cache" / "customer_follow_up_history.json"


def _read_customer_follow_up_history() -> Dict[str, List[Dict[str, Any]]]:
    path = _customer_follow_up_history_path()
    try:
        if not path.exists() or not path.is_file():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_customer_follow_up_history(payload: Dict[str, List[Dict[str, Any]]]) -> None:
    path = _customer_follow_up_history_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def _append_customer_follow_up_history(
    *,
    history_id: str,
    score: int,
    limit: int = 24,
) -> Dict[str, Any]:
    payload = _read_customer_follow_up_history()
    entries = list(payload.get(history_id) or [])
    normalized_score = max(0, min(100, int(score)))
    if not entries or int(entries[-1].get("score") or -1) != normalized_score:
        entries.append({
            "recorded_at": datetime.utcnow().isoformat() + "Z",
            "score": normalized_score,
        })
    entries = entries[-max(2, limit):]
    payload[history_id] = entries
    _write_customer_follow_up_history(payload)
    scores = [max(0, min(100, int(item.get("score") or 0))) for item in entries]
    average_score = round(sum(scores) / len(scores)) if scores else normalized_score
    peak_score = max(scores) if scores else normalized_score
    previous_score = scores[-2] if len(scores) > 1 else None
    momentum = normalized_score - previous_score if previous_score is not None else 0
    cumulative_score = max(
        0,
        min(
            100,
            round(
                (normalized_score * 0.45)
                + (average_score * 0.3)
                + (peak_score * 0.15)
                + (max(0, momentum) * 0.1)
            ),
        ),
    )
    return {
        "average_score": average_score,
        "peak_score": peak_score,
        "latest_score": normalized_score,
        "previous_score": previous_score,
        "momentum": momentum,
        "cumulative_score": cumulative_score,
    }


def _customer_orchestrate_connection_id(
    trace_id: Optional[str],
    flow_id: Optional[str],
    step_id: Optional[str],
    action: Optional[str],
) -> Optional[str]:
    if flow_id and step_id and action:
        return f"{flow_id}:{step_id}:{action}"
    return trace_id
