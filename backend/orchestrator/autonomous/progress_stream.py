"""SSE / WebSocket progress streams for autonomous orchestrator (G-0-3-3)."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional

from backend.llm.orchestrator_progress_tracker import (
    build_progress_stream_url,
    load_orchestration_progress,
)

_TERMINAL_EXECUTION_STATES = frozenset({"completed", "failed", "idle"})
_TERMINAL_STATUSES = frozenset({"success", "completed", "failed"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _progress_signature(payload: Dict[str, Any]) -> str:
    events = payload.get("events") or []
    last_event = events[-1] if events else {}
    return "|".join(
        [
            str(payload.get("updated_at") or ""),
            str(payload.get("status") or ""),
            str(payload.get("execution_state") or ""),
            str(payload.get("active_substep") or ""),
            str(len(events)),
            str(last_event.get("at") or ""),
            str(last_event.get("message") or "")[:120],
        ]
    )


def _is_terminal(payload: Dict[str, Any]) -> bool:
    status = str(payload.get("status") or "").strip().lower()
    execution_state = str(payload.get("execution_state") or "").strip().lower()
    if status in _TERMINAL_STATUSES:
        return True
    if execution_state in {"completed", "failed"}:
        return True
    return False


def _decorate_sse_payload(payload: Dict[str, Any], *, run_id: str) -> Dict[str, Any]:
    normalized = dict(payload)
    normalized["run_id"] = str(normalized.get("run_id") or run_id)
    normalized["progress_source"] = "autonomous_sse"
    normalized["stream_url"] = build_progress_stream_url(run_id)
    normalized["ws_connected"] = True
    return normalized


def format_sse_frame(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def iter_orchestration_progress_sse(
    run_id: str,
    *,
    poll_interval_sec: float = 0.6,
    heartbeat_interval_sec: float = 12.0,
    wait_for_start_sec: float = 45.0,
    max_stream_sec: float = 900.0,
) -> AsyncIterator[str]:
    """Poll-backed SSE — emits on snapshot change, heartbeats, terminal done."""
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        yield format_sse_frame("error", {"detail": "run_id required"})
        return

    loop = asyncio.get_running_loop()
    started = loop.time()
    last_signature = ""
    last_heartbeat = started

    while True:
        now = loop.time()
        if now - started >= max_stream_sec:
            yield format_sse_frame(
                "done",
                {"run_id": normalized_run_id, "status": "timeout", "reason": "max_stream_sec"},
            )
            break

        payload = load_orchestration_progress(normalized_run_id)
        if not payload:
            if now - started >= wait_for_start_sec:
                yield format_sse_frame(
                    "error",
                    {"run_id": normalized_run_id, "detail": "orchestration progress를 찾을 수 없습니다."},
                )
                break
            await asyncio.sleep(poll_interval_sec)
            continue

        decorated = _decorate_sse_payload(payload, run_id=normalized_run_id)
        signature = _progress_signature(decorated)
        if signature != last_signature:
            last_signature = signature
            yield format_sse_frame("progress", decorated)

        if _is_terminal(decorated):
            yield format_sse_frame(
                "done",
                {
                    "run_id": normalized_run_id,
                    "status": str(decorated.get("status") or decorated.get("execution_state") or "done"),
                },
            )
            break

        if now - last_heartbeat >= heartbeat_interval_sec:
            last_heartbeat = now
            yield format_sse_frame(
                "heartbeat",
                {"run_id": normalized_run_id, "at": _utc_now_iso()},
            )

        await asyncio.sleep(poll_interval_sec)


async def iter_orchestration_progress_ws(
    run_id: str,
    *,
    poll_interval_sec: float = 0.6,
    wait_for_start_sec: float = 45.0,
    max_stream_sec: float = 900.0,
) -> AsyncIterator[Dict[str, Any]]:
    """WebSocket message iterator — same contract as SSE progress/done frames."""
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        yield {"event": "error", "detail": "run_id required"}
        return

    loop = asyncio.get_running_loop()
    started = loop.time()
    last_signature = ""

    while True:
        now = loop.time()
        if now - started >= max_stream_sec:
            yield {
                "event": "done",
                "run_id": normalized_run_id,
                "status": "timeout",
                "reason": "max_stream_sec",
            }
            break

        payload = load_orchestration_progress(normalized_run_id)
        if not payload:
            if now - started >= wait_for_start_sec:
                yield {
                    "event": "error",
                    "run_id": normalized_run_id,
                    "detail": "orchestration progress를 찾을 수 없습니다.",
                }
                break
            await asyncio.sleep(poll_interval_sec)
            continue

        decorated = _decorate_sse_payload(payload, run_id=normalized_run_id)
        decorated["progress_source"] = "autonomous_ws"
        signature = _progress_signature(decorated)
        if signature != last_signature:
            last_signature = signature
            yield {"event": "progress", **decorated}

        if _is_terminal(decorated):
            yield {
                "event": "done",
                "run_id": normalized_run_id,
                "status": str(decorated.get("status") or decorated.get("execution_state") or "done"),
            }
            break

        await asyncio.sleep(poll_interval_sec)
