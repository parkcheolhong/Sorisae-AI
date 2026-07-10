"""Autonomous session progress snapshots for HTTP polling (G-0-3-2)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.llm.orchestrator_progress_tracker import (
    build_progress_stream_url,
    load_orchestration_progress,
    save_orchestration_progress,
)

AUTONOMOUS_PROGRESS_PIPELINE = [
    "autonomous_turn_controller",
    "reasoner",
    "planner",
    "coder",
    "validator",
]

SUBSTEP_AGENT_IDS = ("reasoner", "planner", "reviewer", "coder", "validator")


def _infer_substep_from_event(message: str) -> Optional[str]:
    text = str(message or "")
    for agent_id in SUBSTEP_AGENT_IDS:
        if f"· {agent_id}" in text or f"{agent_id} →" in text:
            return agent_id
    return None


def _infer_substep_status(message: str) -> str:
    text = str(message or "")
    if "→ failed" in text or "→ error" in text:
        return "failed"
    if "→ success" in text or "→ stub" in text:
        return "completed"
    if "→ needs_revision" in text:
        return "needs_revision"
    if "→" in text:
        return "running"
    return "info"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_from_execution_state(execution_state: str) -> str:
    normalized = str(execution_state or "idle").strip().lower()
    if normalized == "completed":
        return "success"
    if normalized == "failed":
        return "failed"
    if normalized in {"executing", "planning", "reviewing", "awaiting_approval"}:
        return "running"
    return "idle"


def _progress_alias_ids(
    session: Any,
    *,
    run_id: Optional[str] = None,
    stage_run_id: Optional[str] = None,
) -> List[str]:
    extra = dict(getattr(session, "extra", None) or {})
    ids: List[str] = []
    for candidate in (
        stage_run_id,
        extra.get("stage_run_id"),
        run_id,
        extra.get("progress_run_id"),
        getattr(session, "session_id", None),
    ):
        normalized = str(candidate or "").strip()
        if normalized and normalized not in ids:
            ids.append(normalized)
    return ids


def build_autonomous_progress_snapshot(
    session: Any,
    *,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    execution_state = str(getattr(session, "execution_state", "") or "idle")
    extra = dict(getattr(session, "extra", None) or {})
    current_stage = session.get_current_stage() if hasattr(session, "get_current_stage") else None
    stage_label = current_stage.stage_label if current_stage else None
    effective_run_id = str(
        run_id or extra.get("progress_run_id") or getattr(session, "session_id", "") or ""
    ).strip()
    agent_rows = [
        {
            "agent": getattr(result, "agent", ""),
            "status": getattr(result, "status", ""),
            "elapsed_ms": getattr(result, "elapsed_ms", 0),
        }
        for result in (getattr(session, "agent_results", None) or [])[-12:]
    ]
    stages = getattr(session, "stages", None) or []
    stage_number = extra.get("active_stage_number")
    substeps = list(extra.get("substep_trace") or [])
    return {
        "run_id": effective_run_id,
        "session_id": getattr(session, "session_id", ""),
        "orchestrator_core": "autonomous_turn_controller",
        "project_name": getattr(session, "project_name", "") or "",
        "task": getattr(session, "task", "") or "",
        "mode": getattr(session, "mode", "") or "",
        "pipeline": list(AUTONOMOUS_PROGRESS_PIPELINE),
        "status": _status_from_execution_state(execution_state),
        "execution_state": execution_state,
        "autonomous_intent": str(extra.get("last_intent") or extra.get("active_stage_command") or ""),
        "stage_command": str(extra.get("active_stage_command") or ""),
        "stage_number": stage_number,
        "stages_completed": sum(1 for stage in stages if getattr(stage, "status", "") == "completed"),
        "stages_total": len(stages) or 11,
        "current_stage": stage_label,
        "current_state": execution_state,
        "agent_results": agent_rows,
        "approval_state": getattr(session, "approval_state", ""),
        "requires_approval": getattr(session, "approval_state", "") == "pending",
        "llm_connected": bool(extra.get("llm_connected")),
        "active_substep": str(extra.get("active_substep") or ""),
        "substeps": substeps[-20:],
        "progress_source": "autonomous_poll",
        "poll_url": f"/api/llm/orchestrate/progress/{effective_run_id}",
        "stream_url": build_progress_stream_url(effective_run_id),
        "ws_url": f"/api/llm/orchestrate/progress/ws/{effective_run_id}",
        "updated_at": _utc_now_iso(),
    }


def persist_autonomous_progress(
    session: Any,
    *,
    run_id: Optional[str] = None,
    stage_run_id: Optional[str] = None,
    event_message: Optional[str] = None,
    event_level: str = "info",
) -> Dict[str, Any]:
    alias_ids = _progress_alias_ids(session, run_id=run_id, stage_run_id=stage_run_id)
    primary_id = alias_ids[0] if alias_ids else str(getattr(session, "session_id", "") or "")
    existing = load_orchestration_progress(primary_id) if primary_id else {}
    events = list(existing.get("events") or [])
    if event_message:
        normalized_message = str(event_message).strip()
        events.append(
            {
                "at": _utc_now_iso(),
                "level": event_level,
                "message": normalized_message,
            }
        )
        substep_id = _infer_substep_from_event(normalized_message)
        if substep_id:
            trace = list(getattr(session, "extra", {}).get("substep_trace") or existing.get("substeps") or [])
            trace.append(
                {
                    "id": substep_id,
                    "status": _infer_substep_status(normalized_message),
                    "message": normalized_message,
                    "at": _utc_now_iso(),
                }
            )
            session.extra["substep_trace"] = trace[-20:]
            session.extra["active_substep"] = substep_id
    snapshot = build_autonomous_progress_snapshot(session, run_id=primary_id)
    snapshot["events"] = events[-120:]
    primary = save_orchestration_progress(primary_id, snapshot)
    for alias in alias_ids[1:]:
        save_orchestration_progress(alias, snapshot)
    return primary


def load_progress_for_run(run_id: str) -> Dict[str, Any]:
    return load_orchestration_progress(str(run_id or "").strip())
