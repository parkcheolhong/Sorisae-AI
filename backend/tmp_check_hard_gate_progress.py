import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.tmp_hard_gate_paths import (
    hard_gate_progress_path,
    hard_gate_result_path,
    hard_gate_runlog_path,
    hard_gate_target_dir,
)

TARGET_DIR = hard_gate_target_dir()
PROGRESS_PATH = hard_gate_progress_path()
RUNLOG_PATH = hard_gate_runlog_path()
MODULE_NAME = "backend.tmp_run_hard_gate_consistency"
RESULT_PATH = hard_gate_result_path()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_result_snapshot(snapshot: dict) -> None:
    payload = json.dumps(snapshot, ensure_ascii=False)
    temp_path = RESULT_PATH.with_suffix(".result.tmp")
    temp_path.write_text(payload, encoding="utf-8")
    temp_path.replace(RESULT_PATH)


def _cleanup() -> dict:
    killed = []
    ps = subprocess.check_output(["ps", "-ef"], text=True)
    for line in ps.splitlines():
        if MODULE_NAME not in line or "tmp_check_hard_gate_progress" in line:
            continue
        parts = [p for p in line.split(" ") if p]
        if len(parts) <= 1:
            continue
        try:
            pid = int(parts[1])
            os.kill(pid, signal.SIGKILL)
            killed.append(pid)
        except Exception:
            continue
    cleanup = {}
    for path in [TARGET_DIR, PROGRESS_PATH, RUNLOG_PATH]:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            cleanup[str(path)] = "removed_dir"
        elif path.exists():
            path.unlink(missing_ok=True)
            cleanup[str(path)] = "removed_file"
        else:
            cleanup[str(path)] = "missing"
    return {"killed": killed, "cleanup": cleanup}


def _start() -> None:
    RUNLOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = RUNLOG_PATH.open("w", encoding="utf-8")
    subprocess.Popen(
        [sys.executable, "-m", MODULE_NAME],
        cwd="/app",
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )


def _load_progress_tail() -> list[dict]:
    if not PROGRESS_PATH.exists():
        return []
    rows = []
    for raw in PROGRESS_PATH.read_text(encoding="utf-8").splitlines()[-80:]:
        raw = raw.strip()
        if not raw:
            continue
        try:
            rows.append(json.loads(raw))
        except Exception:
            rows.append({"event": "raw", "message": raw})
    return rows


def _load_process_lines() -> list[str]:
    ps = subprocess.check_output(["ps", "-ef"], text=True)
    return [
        line
        for line in ps.splitlines()
        if MODULE_NAME in line and "tmp_check_hard_gate_progress" not in line
    ]


def _classify_state(latest: dict | None) -> str:
    if not latest:
        return "tracker_started"
    if latest.get("has_failed"):
        return "target_failed"
    if latest.get("has_completed"):
        return "target_completed"
    if latest.get("has_validation_write_complete"):
        return "validation_artifacts_written"
    if latest.get("has_finalization_enter"):
        return "entered_finalization_validation_write"
    if latest.get("has_meta_written") and latest.get("target_process_alive"):
        return "running_after_meta_written"
    if latest.get("has_semantic_gate") and latest.get("target_process_alive"):
        return "running_after_semantic_gate"
    if latest.get("target_process_alive"):
        return "running_before_semantic_gate"
    return "target_stopped_without_terminal_event"


def main() -> int:
    snapshot = {"cleanup": _cleanup()}
    _start()
    checkpoints = []
    if RESULT_PATH.exists():
        RESULT_PATH.unlink(missing_ok=True)
    for _ in range(24):
        time.sleep(15)
        progress_tail = _load_progress_tail()
        process_lines = _load_process_lines()
        latest_message = str((progress_tail[-1].get("message") if progress_tail else "") or "")
        checkpoints.append(
            {
                "observed_at": _utc_now(),
                "processes": process_lines,
                "target_process_alive": bool(process_lines),
                "progress_tail": progress_tail,
                "has_semantic_gate": any("semantic gate" in str(item.get("message") or "") for item in progress_tail),
                "has_meta_written": any("메타 파일 포함 총" in str(item.get("message") or "") for item in progress_tail),
                "has_finalization_enter": any("finalization entering validation_artifacts write" in str(item.get("message") or "") for item in progress_tail),
                "has_validation_write_complete": any("finalization completed validation_artifacts write" in str(item.get("message") or "") for item in progress_tail),
                "has_failed": any(str(item.get("event") or "") == "orchestration_failed" for item in progress_tail),
                "has_completed": any(str(item.get("event") or "") == "orchestration_completed" for item in progress_tail),
                "latest_message": latest_message,
            }
        )
        latest = checkpoints[-1]
        snapshot["checkpoints"] = checkpoints
        snapshot["tracker_state"] = _classify_state(latest)
        snapshot["updated_at"] = _utc_now()
        _write_result_snapshot(snapshot)
        if latest["has_failed"] or latest["has_completed"] or latest["has_validation_write_complete"]:
            break
    docs = TARGET_DIR / "docs"
    snapshot["checkpoints"] = checkpoints
    snapshot["tracker_state"] = _classify_state(checkpoints[-1] if checkpoints else None)
    snapshot["updated_at"] = _utc_now()
    snapshot["files"] = {
        name: (docs / name).exists()
        for name in [
            "final_readiness_checklist.md",
            "automatic_validation_result.json",
            "automatic_validation_result.md",
            "output_audit.json",
            "traceability_map.json",
        ]
    }
    payload = json.dumps(snapshot, ensure_ascii=False)
    _write_result_snapshot(snapshot)
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
