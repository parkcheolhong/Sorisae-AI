from __future__ import annotations

from collections import deque
from copy import deepcopy
from threading import Lock
import time
from typing import Deque, Dict, Optional
from uuid import uuid4

from .execution_flow_registry import build_execution_identity
from .ffmpeg_render_executor import render_final_video
from .image_to_video_pipeline import run_image_to_video_pipeline

_QUEUE: Deque[str] = deque()
_JOBS: Dict[str, Dict[str, object]] = {}
_ACTIVE_JOB_ID: Optional[str] = None
_RUNNING = False
_LOCK = Lock()

def enqueue_self_run_video_job(payload: Dict[str, object]) -> Dict[str, object]:
    job_id = f"selfrun-video-{uuid4().hex[:10]}"
    with _LOCK:
        _JOBS[job_id] = {"job_id": job_id, "status": "queued", "payload": deepcopy(payload), "output_dir": None, "ffconcat_path": None, "output_mp4_path": None, "log_path": None, "error_message": None}
        _QUEUE.append(job_id)
        job = dict(_JOBS[job_id])
    job.pop("payload", None)
    job["execution"] = build_execution_identity("self_run_enqueue")
    return job

def get_self_run_video_job(job_id: str) -> Optional[Dict[str, object]]:
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return None
        safe_job = dict(job)
    safe_job.pop("payload", None)
    safe_job["execution"] = build_execution_identity("self_run_status")
    return safe_job

def get_self_run_video_worker_status() -> Dict[str, object]:
    with _LOCK:
        completed_job_count = sum(1 for item in _JOBS.values() if item.get("status") == "completed")
        return {"running": _RUNNING, "queue_depth": len(_QUEUE), "active_job_id": _ACTIVE_JOB_ID, "completed_job_count": completed_job_count, "execution": build_execution_identity("self_run_worker")}

def run_self_run_video_worker() -> None:
    global _RUNNING, _ACTIVE_JOB_ID
    _RUNNING = True
    while True:
        job_id: Optional[str] = None
        with _LOCK:
            if _QUEUE:
                job_id = _QUEUE.popleft()
                _ACTIVE_JOB_ID = job_id
                _JOBS[job_id]["status"] = "planning"
        if not job_id:
            time.sleep(1.0)
            continue
        try:
            with _LOCK:
                payload = deepcopy(_JOBS[job_id].get("payload") or {})
            pipeline = run_image_to_video_pipeline(payload)
            video_line = dict((pipeline.get("video_engine") or {}).get("video_line") or {})
            render_result = render_final_video({
                "title": payload.get("title") or "self-run-final-video",
                "ffconcat_path": video_line.get("ffconcat_path") or "",
                "frames_per_second": payload.get("frames_per_second") or 8,
                "duration_seconds": video_line.get("duration_seconds") or payload.get("duration_seconds") or 60,
                "expected_total_frames": video_line.get("total_frames") or 0,
                "output_dir": video_line.get("output_dir"),
                "output_basename": "self_run_final.mp4",
            })
            with _LOCK:
                _JOBS[job_id].update({"status": render_result.get("status") or "failed", "output_dir": video_line.get("output_dir"), "ffconcat_path": video_line.get("ffconcat_path"), "output_mp4_path": render_result.get("output_mp4_path"), "log_path": render_result.get("log_path"), "error_message": render_result.get("error_message")})
        except Exception as exc:
            with _LOCK:
                _JOBS[job_id].update({"status": "failed", "error_message": str(exc)})
        finally:
            with _LOCK:
                _ACTIVE_JOB_ID = None
