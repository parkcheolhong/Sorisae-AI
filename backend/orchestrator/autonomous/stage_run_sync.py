"""① AutonomousSession STAGE-* ↔ marketplace stage_run ARCH-* 동기화."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.orchestration_stage_service import (
    get_next_stage_id,
    load_stage_run,
    save_stage_run,
    update_stage_run,
)

AUTONOMOUS_STAGE_TO_ARCH: Dict[str, str] = {
    "STAGE-01": "ARCH-001",
    "STAGE-02": "ARCH-002",
    "STAGE-03": "ARCH-003",
    "STAGE-04": "ARCH-004",
    "STAGE-045": "ARCH-0045",
    "STAGE-05": "ARCH-005",
    "STAGE-06": "ARCH-006",
    "STAGE-07": "ARCH-007",
    "STAGE-08": "ARCH-008",
    "STAGE-09": "ARCH-009",
    "STAGE-10": "ARCH-010",
}

_DESIGN_AGENT_SUBSTEP_INDEX = {
    "ARCH-001": {"reasoner": 0, "planner": 1},
    "ARCH-002": {"planner": 0, "coder": 1},
}


def _session_active_stage_command(session: Any) -> str:
    extra = getattr(session, "extra", None) or {}
    if isinstance(extra, dict):
        return str(extra.get("active_stage_command") or "").strip().lower()
    return ""


def _is_discuss_turn(session: Any) -> bool:
    return _session_active_stage_command(session) == "discuss"


def _arch_stage(payload: Dict[str, Any], arch_id: str) -> Optional[Dict[str, Any]]:
    for stage in payload.get("stages") or []:
        if str(stage.get("id") or "").upper() == arch_id.upper():
            return stage
    return None


def _arch_for_active_stage_number(active_number: Any) -> Optional[str]:
    try:
        normalized = float(active_number)
    except (TypeError, ValueError):
        return None
    if normalized == 4.5:
        return AUTONOMOUS_STAGE_TO_ARCH.get("STAGE-045")
    if normalized.is_integer() and 1 <= int(normalized) <= 10:
        return AUTONOMOUS_STAGE_TO_ARCH.get(f"STAGE-{int(normalized):02d}")
    return None


def _sync_discuss_substeps(payload: Dict[str, Any], arch_id: str) -> Dict[str, Any]:
    arch_stage = _arch_stage(payload, arch_id)
    if not arch_stage:
        return payload

    substeps: List[Dict[str, Any]] = list(arch_stage.get("substeps") or [])
    if substeps:
        substeps[0]["status"] = "running"
        substeps[0]["check_label"] = "협업 Q&A 진행 중"
        arch_stage["substeps"] = substeps

    # discuss 턴은 completed/passed ARCH-004에도 Q&A 오버레이 — current_stage_id 고정 (G-4-3)
    arch_stage["status"] = "running"
    arch_stage["check_label"] = "협업 Q&A"
    payload["current_stage_id"] = arch_id
    payload["status"] = "running"
    payload["final_completed"] = False

    return payload


def _agent_successes(session: Any) -> set[str]:
    return {
        str(getattr(result, "agent", "") or "")
        for result in (getattr(session, "agent_results", None) or [])
        if getattr(result, "status", "") in {"success", "stub"}
    }


def _sync_design_substeps(payload: Dict[str, Any], arch_id: str, session: Any) -> Dict[str, Any]:
    arch_stage = _arch_stage(payload, arch_id)
    if not arch_stage:
        return payload

    agents = _agent_successes(session)
    substeps: List[Dict[str, Any]] = list(arch_stage.get("substeps") or [])
    index_map = _DESIGN_AGENT_SUBSTEP_INDEX.get(arch_id, {})

    for agent_id, index in index_map.items():
        if agent_id not in agents or index >= len(substeps):
            continue
        substeps[index]["status"] = "passed"
        substeps[index]["check_label"] = "통과"
        substeps[index]["checked"] = True

    if (
        getattr(session, "approval_state", "") == "pending"
        and "coder" not in agents
        and len(substeps) >= 3
        and str(substeps[2].get("status") or "pending") == "pending"
    ):
        substeps[2]["status"] = "running"
        substeps[2]["check_label"] = "승인 대기"

    if "coder" in agents and "validator" in agents and len(substeps) >= 3:
        substeps[2]["status"] = "passed"
        substeps[2]["check_label"] = "통과"
        substeps[2]["checked"] = True

    arch_stage["substeps"] = substeps
    if str(arch_stage.get("status") or "pending") == "pending":
        arch_stage["status"] = "running"
        arch_stage["check_label"] = "진행 중"
        payload["current_stage_id"] = arch_id
        payload["status"] = "running"
        payload["final_completed"] = False

    return payload


def sync_stage_run_from_autonomous_session(
    *,
    stage_run_id: str,
    session: Any,
) -> Optional[Dict[str, Any]]:
    """자율 코어 세션 진행 상태를 stage_run JSON에 반영."""
    normalized_run_id = str(stage_run_id or "").strip()
    if not normalized_run_id:
        return None

    payload = load_stage_run(normalized_run_id)
    if not payload:
        return None

    synced = payload
    for stage in getattr(session, "stages", None) or []:
        arch_id = AUTONOMOUS_STAGE_TO_ARCH.get(str(getattr(stage, "stage_id", "") or ""))
        if not arch_id:
            continue
        arch_stage = _arch_stage(synced, arch_id)
        if not arch_stage:
            continue

        autonomous_status = str(getattr(stage, "status", "") or "")
        arch_status = str(arch_stage.get("status") or "pending").lower()

        if autonomous_status == "completed" and arch_status != "passed":
            synced = update_stage_run(
                run_id=normalized_run_id,
                stage_id=arch_id,
                status="passed",
                note=f"① 자율 코어 {arch_id} coder/validator 완료",
            )
        elif autonomous_status == "failed" and arch_status not in {"failed", "manual_correction"}:
            synced = update_stage_run(
                run_id=normalized_run_id,
                stage_id=arch_id,
                status="manual_correction",
                note="① 자율 코어 단계 검증 실패",
            )

    current = session.get_current_stage() if hasattr(session, "get_current_stage") else None
    if _is_discuss_turn(session):
        extra = getattr(session, "extra", None) or {}
        discuss_arch = _arch_for_active_stage_number(extra.get("active_stage_number") if isinstance(extra, dict) else None)
        if discuss_arch:
            synced = _sync_discuss_substeps(synced, discuss_arch)
            synced = save_stage_run(synced)
    elif current is not None:
        arch_id = AUTONOMOUS_STAGE_TO_ARCH.get(str(getattr(current, "stage_id", "") or ""))
        if arch_id and str(getattr(current, "status", "") or "") == "in_progress":
            synced = _sync_design_substeps(synced, arch_id, session)
            synced = save_stage_run(synced)

            execution_state = str(getattr(session, "execution_state", "") or "")
            if execution_state == "awaiting_approval":
                synced["current_stage_id"] = arch_id
                synced["status"] = "running"
                synced["final_completed"] = False
                synced = save_stage_run(synced)
            elif execution_state == "executing" and not _is_discuss_turn(session):
                next_arch = get_next_stage_id(arch_id)
                if next_arch and str(synced.get("current_stage_id") or "").upper() == arch_id.upper():
                    next_stage = _arch_stage(synced, next_arch)
                    if next_stage and str(next_stage.get("status") or "pending") == "pending":
                        next_stage["status"] = "running"
                        next_stage["check_label"] = "진행 중"
                        synced["current_stage_id"] = next_arch
                        synced["status"] = "running"
                        synced = save_stage_run(synced)

    return synced
