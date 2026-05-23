import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from backend.admin_router import (
    _approval_record_path,
    _emit_self_run_progress_marker,
    _force_fail_running_self_run_record,
    _load_json_file,
    _run_workspace_self_run_job_from_request,
    _self_run_worker_status_path,
    _update_self_run_approval_checklist,
    _write_json_file,
)


def _update_worker_runtime_state(approval_id: str, **fields: object) -> None:
    record_path = _approval_record_path(approval_id)
    status_path = _self_run_worker_status_path(approval_id)
    now_iso = datetime.now().isoformat()
    enriched_fields = {
        **fields,
        "worker_heartbeat_at": str(fields.get("worker_heartbeat_at") or now_iso),
        "worker_status_updated_at": now_iso,
    }
    if record_path.exists():
        payload = _load_json_file(record_path)
        payload.update(enriched_fields)
        payload["worker_status_path"] = str(status_path)
        _update_self_run_approval_checklist(
            payload,
            "worker_status_written",
            "completed",
            "worker status 파일이 갱신되었습니다.",
        )
        if fields.get("worker_started_at"):
            _update_self_run_approval_checklist(
                payload,
                "worker_boot_recorded",
                "completed",
                f"worker_started_at={fields.get('worker_started_at')}",
            )
        _write_json_file(record_path, payload)
    status_payload = _load_json_file(status_path) if status_path.exists() else {"approval_id": approval_id}
    status_payload.update(enriched_fields)
    _write_json_file(status_path, status_payload)


def _worker_heartbeat_loop(approval_id: str, started_at: datetime, stop_event: threading.Event) -> None:
    while not stop_event.wait(5):
        running_seconds = max(0, int((datetime.now() - started_at).total_seconds()))
        _update_worker_runtime_state(
            approval_id,
            worker_pid=os.getpid(),
            worker_alive=True,
            running_seconds=running_seconds,
            runtime_diagnostic=f"백그라운드 worker 실행 경과 {running_seconds}초",
        )


def _preserve_runtime_diagnostic(
    approval_id: str,
    fallback_message: str,
) -> str:
    record_path = _approval_record_path(approval_id)
    if not record_path.exists():
        return fallback_message

    payload = _load_json_file(record_path)
    current_message = str(payload.get("runtime_diagnostic") or "").strip()
    if not current_message:
        return fallback_message
    if current_message == "백그라운드 worker가 오케스트레이터 작업을 시작했습니다.":
        return fallback_message
    if current_message.startswith("백그라운드 worker 실행 경과 "):
        return fallback_message
    return current_message


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("job_request_path 인자가 필요합니다.")

    job_request_path = Path(sys.argv[1]).resolve()
    approval_id = ""
    try:
        approval_id = str(
            json.loads(job_request_path.read_text(encoding="utf-8")).get(
                "approval_id",
                "",
            )
        ).strip()
    except Exception:
        approval_id = ""

    if approval_id:
        started_at = datetime.now()
        _emit_self_run_progress_marker(
            approval_id,
            "worker_boot",
            job_request_path=str(job_request_path),
            worker_pid=os.getpid(),
        )
        _update_worker_runtime_state(
            approval_id,
            worker_pid=os.getpid(),
            worker_alive=True,
            worker_started_at=started_at.isoformat(),
            running_seconds=0,
            runtime_diagnostic="백그라운드 worker가 오케스트레이터 작업을 시작했습니다.",
        )
        stop_event = threading.Event()
        heartbeat_thread = threading.Thread(
            target=_worker_heartbeat_loop,
            args=(approval_id, started_at, stop_event),
            daemon=True,
        )
        heartbeat_thread.start()
    else:
        stop_event = threading.Event()
        heartbeat_thread = None

    try:
        if approval_id:
            _emit_self_run_progress_marker(
                approval_id,
                "worker_dispatch",
                job_request_path=str(job_request_path),
            )
        _run_workspace_self_run_job_from_request(job_request_path)
    except BaseException as exc:
        if approval_id:
            _emit_self_run_progress_marker(
                approval_id,
                "worker_exception",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            _update_worker_runtime_state(
                approval_id,
                worker_alive=False,
                worker_finished_at=datetime.now().isoformat(),
                runtime_diagnostic=f"worker 예외로 종료됨: {exc}",
            )
        raise
    finally:
        stop_event.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=1)
        if approval_id:
            _emit_self_run_progress_marker(
                approval_id,
                "worker_finalize",
                worker_pid=os.getpid(),
            )
            _update_worker_runtime_state(
                approval_id,
                worker_alive=False,
                worker_finished_at=datetime.now().isoformat(),
                runtime_diagnostic=_preserve_runtime_diagnostic(
                    approval_id,
                    "백그라운드 worker 작업이 종료되었습니다.",
                ),
            )
            record_path = _approval_record_path(approval_id)
            if record_path.exists():
                payload = _load_json_file(record_path)
                if str(payload.get("status") or "") == "running":
                    detail = str(
                        payload.get("orchestration_error")
                        or payload.get("runtime_diagnostic")
                        or "백그라운드 worker 가 종료됐지만 approval 상태가 running 으로 남았습니다."
                    ).strip()
                    _force_fail_running_self_run_record(
                        record_path,
                        stale_reason="worker_exit_without_final_status",
                        detail=detail,
                    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
