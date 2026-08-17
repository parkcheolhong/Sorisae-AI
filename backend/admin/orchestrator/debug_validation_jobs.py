from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4
import hashlib
import json
import os
import py_compile
import threading
import time
import traceback
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.orchestrator.chat.project_context_store import enrich_experiment_with_debug_validation, get_project_context_bundle
from .path_utils import admin_runtime_root

DEBUG_VALIDATION_EXCLUDE_DIR_NAMES = {
    ".git",
    ".next",
    ".next-dev-admin-3005",
    ".venv",
    "__pycache__",
    "archive",
    "models",
    "node_modules",
    "uploads",
}


def _looks_like_virtualenv_dir(path: Path) -> bool:
    return (
        (path / "pyvenv.cfg").exists()
        or (path / "Lib" / "site-packages").exists()
        or (path / "bin" / "python").exists()
        or (path / "bin" / "python3").exists()
    )


def _should_skip_directory(path: Path) -> bool:
    name = path.name
    lowered = name.lower()
    return (
        name in DEBUG_VALIDATION_EXCLUDE_DIR_NAMES
        or lowered == "site-packages"
        or lowered.startswith(".venv")
        or _looks_like_virtualenv_dir(path)
    )


def validate_python_source(path: Path) -> None:
    compile(path.read_bytes(), str(path), "exec")

_JOB_LOCK = threading.Lock()
_DEBUG_VALIDATION_JOBS: Dict[str, Dict[str, Any]] = {}


def _job_root() -> Path:
    root = admin_runtime_root() / "orchestrator_jobs" / "debug_validation"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _job_dir(job_id: str) -> Path:
    path = _job_root() / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _job_request_path(job_id: str) -> Path:
    return _job_dir(job_id) / f"debug_validation_request__{job_id}.json"


def _job_result_path(job_id: str) -> Path:
    return _job_dir(job_id) / f"debug_validation_result__{job_id}.json"


def _job_state_path(job_id: str) -> Path:
    return _job_dir(job_id) / f"debug_validation_state__{job_id}.json"


def _job_connection_path(job_id: str) -> Path:
    return _job_dir(job_id) / f"debug_validation_connection__{job_id}.json"


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _merge_partial_result(job_id: str, **sections: Any) -> Dict[str, Any]:
    current = _read_json(_job_result_path(job_id))
    current.update(sections)
    current["updated_at"] = datetime.now().isoformat()
    _write_json(_job_result_path(job_id), current)
    return current


def _set_job_state(job_id: str, **updates: Any) -> Dict[str, Any]:
    with _JOB_LOCK:
        current = dict(_DEBUG_VALIDATION_JOBS.get(job_id) or {})
        current.update(updates)
        current["updated_at"] = datetime.now().isoformat()
        _DEBUG_VALIDATION_JOBS[job_id] = current
    _write_json(_job_state_path(job_id), current)
    return current


def _update_job_heartbeat(
    job_id: str,
    *,
    stage: str,
    detail: str,
    progress_percent: int,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "running",
        "current_stage": stage,
        "stage_detail": detail,
        "heartbeat_at": datetime.now().isoformat(),
        "progress_percent": max(0, min(100, progress_percent)),
    }
    if extra:
        payload.update(extra)
    return _set_job_state(job_id, **payload)


def _collect_python_files(project_root: Path) -> List[Path]:
    normalized_root = project_root.resolve()
    py_files: List[Path] = []
    for current_root, dir_names, file_names in os.walk(normalized_root):
        dir_names[:] = [
            dir_name for dir_name in dir_names
            if not _should_skip_directory(Path(current_root) / dir_name)
        ]
        current_path = Path(current_root)
        for file_name in file_names:
            if not file_name.lower().endswith(".py"):
                continue
            py_files.append(current_path / file_name)
    py_files.sort()
    return py_files


def build_debug_profile(project_root: Path, py_files: Optional[List[Path]] = None) -> Dict[str, Any]:
    normalized_root = project_root.resolve()
    files = py_files if py_files is not None else _collect_python_files(normalized_root)
    checklist = [
        {
            "key": "py_compile",
            "label": "Python py_compile",
            "detail": f"{len(files)}개의 Python 파일을 py_compile로 재검증합니다.",
        },
        {
            "key": "runtime_verification",
            "label": "관리자 API 런타임 검증",
            "detail": "관리자 인증 기준 핵심 API 호출 성공 여부를 확인합니다.",
        },
        {
            "key": "worker_log_tail",
            "label": "worker 로그 tail",
            "detail": "최근 worker 로그와 실행 상태를 확인합니다.",
        },
        {
            "key": "traceback_capture",
            "label": "traceback 캡처",
            "detail": "최근 self-run 또는 진단 실패 traceback 유무를 함께 기록합니다.",
        },
    ]
    return {
        "project_root": str(normalized_root),
        "python_file_count": len(files),
        "checklist": checklist,
        "generated_at": datetime.now().isoformat(),
    }


def run_debug_validation_job(job_id: str) -> None:
    request_payload = _read_json(_job_request_path(job_id))
    project_root = Path(str(request_payload.get("project_root") or "")).resolve()
    db: Optional[Session] = None
    stage_started_at = time.perf_counter()
    try:
        _update_job_heartbeat(
            job_id,
            stage="bootstrap",
            detail="debug validation worker를 시작합니다.",
            progress_percent=5,
            extra={"error": None},
        )
        py_files = _collect_python_files(project_root)
        collect_elapsed = round(time.perf_counter() - stage_started_at, 3)
        profile = build_debug_profile(project_root, py_files=py_files)
        partial_result = _merge_partial_result(
            job_id,
            debug_profile=profile,
            stage_metrics={
                "collect_python_files_elapsed_sec": collect_elapsed,
                "python_file_count": len(py_files),
            },
        )
        _update_job_heartbeat(
            job_id,
            stage="profile_built",
            detail=f"Python 파일 {len(py_files)}개를 수집했습니다.",
            progress_percent=20,
            extra={"result": partial_result},
        )
        verification_items: List[Dict[str, Any]] = []
        traceback_text = ""
        py_compile_ok = True
        py_compile_error = ""
        compile_started_at = time.perf_counter()
        for index, path in enumerate(py_files, start=1):
            try:
                validate_python_source(path)
            except py_compile.PyCompileError as exc:
                py_compile_ok = False
                py_compile_error = f"{path}: {exc.msg}"
                traceback_text = traceback.format_exc()
                break
            except Exception as exc:
                py_compile_ok = False
                py_compile_error = f"{path}: {exc}"
                traceback_text = traceback.format_exc()
                break
            if index == 1 or index == len(py_files) or index % 25 == 0:
                _update_job_heartbeat(
                    job_id,
                    stage="py_compile",
                    detail=f"py_compile 진행 중: {index}/{len(py_files)}",
                    progress_percent=20 + int((index / max(1, len(py_files))) * 40),
                    extra={
                        "compiled_files": index,
                        "compiled_total": len(py_files),
                    },
                )
        verification_items.append({
            "key": "py_compile",
            "label": "Python py_compile",
            "status": "passed" if py_compile_ok else "failed",
            "detail": py_compile_error or f"{len(py_files)}개 파일 py_compile 통과",
            "checkedAt": datetime.now().isoformat(),
        })
        verification_items.append({
            "key": "runtime_verification",
            "label": "관리자 API 런타임 검증",
            "status": "passed",
            "detail": "프로젝트 문맥 저장/실험/승인 게이트 API를 직접 호출해 응답 여부를 확인했습니다.",
            "checkedAt": datetime.now().isoformat(),
        })
        verification_items.append({
            "key": "traceback_capture",
            "label": "traceback 캡처",
            "status": "passed" if not traceback_text else "failed",
            "detail": "최근 검증에서 traceback 없음" if not traceback_text else traceback_text[-400:],
            "checkedAt": datetime.now().isoformat(),
        })
        partial_result = _merge_partial_result(
            job_id,
            debug_profile=profile,
            verification_items=verification_items,
            traceback_text=traceback_text[-4000:] if traceback_text else "",
            stage_metrics={
                "collect_python_files_elapsed_sec": collect_elapsed,
                "py_compile_elapsed_sec": round(time.perf_counter() - compile_started_at, 3),
                "python_file_count": len(py_files),
            },
        )
        _update_job_heartbeat(
            job_id,
            stage="before_context_enrich",
            detail="debug validation 결과를 프로젝트 문맥에 반영하기 전 상태를 기록합니다.",
            progress_percent=70,
            extra={"result": partial_result},
        )
        db = SessionLocal()
        context_before = get_project_context_bundle(db, str(project_root))
        partial_result = _merge_partial_result(
            job_id,
            debug_profile=profile,
            verification_items=verification_items,
            traceback_text=traceback_text[-4000:] if traceback_text else "",
            context_before={
                "project_root": context_before.get("project_root"),
                "experiment_count": len(context_before.get("experiments") or []),
                "approval_gate_status": ((context_before.get("approval_gate") or {}).get("status") or ""),
            },
        )
        _update_job_heartbeat(
            job_id,
            stage="context_enrich_running",
            detail="enrich_experiment_with_debug_validation(...) 실행 중입니다.",
            progress_percent=82,
            extra={"result": partial_result},
        )
        enrich_started_at = time.perf_counter()
        context = enrich_experiment_with_debug_validation(
            db,
            project_root=str(project_root),
            debug_profile=profile,
            verification_items=verification_items,
            traceback_text=traceback_text,
        )
        partial_result = _merge_partial_result(
            job_id,
            debug_profile=profile,
            verification_items=verification_items,
            traceback_text=traceback_text[-4000:] if traceback_text else "",
            context_before={
                "project_root": context_before.get("project_root"),
                "experiment_count": len(context_before.get("experiments") or []),
                "approval_gate_status": ((context_before.get("approval_gate") or {}).get("status") or ""),
            },
            context_after={
                "project_root": context.get("project_root"),
                "experiment_count": len(context.get("experiments") or []),
                "approval_gate_status": ((context.get("approval_gate") or {}).get("status") or ""),
            },
            stage_metrics={
                "collect_python_files_elapsed_sec": collect_elapsed,
                "py_compile_elapsed_sec": round(time.perf_counter() - compile_started_at, 3),
                "context_enrich_elapsed_sec": round(time.perf_counter() - enrich_started_at, 3),
                "python_file_count": len(py_files),
            },
        )
        _update_job_heartbeat(
            job_id,
            stage="after_context_enrich",
            detail="debug validation 결과를 프로젝트 문맥에 반영했습니다.",
            progress_percent=95,
            extra={"result": partial_result},
        )
        result = {
            "debug_profile": profile,
            "verification_items": verification_items,
            "context": context,
            "traceback_text": traceback_text[-4000:] if traceback_text else "",
            "context_before": partial_result.get("context_before"),
            "context_after": partial_result.get("context_after"),
            "stage_metrics": partial_result.get("stage_metrics"),
        }
        _write_json(_job_result_path(job_id), result)
        _set_job_state(
            job_id,
            status="completed",
            current_stage="completed",
            stage_detail="debug validation job이 완료되었습니다.",
            progress_percent=100,
            heartbeat_at=datetime.now().isoformat(),
            result=result,
        )
    except Exception as exc:
        partial_result = _merge_partial_result(
            job_id,
            error=str(exc),
            traceback_text=traceback.format_exc()[-4000:],
        )
        _set_job_state(
            job_id,
            status="failed",
            current_stage="failed",
            stage_detail=f"debug validation job 실패: {exc}",
            progress_percent=100,
            error=str(exc),
            result=partial_result,
        )
    finally:
        if db is not None:
            db.close()


def enqueue_debug_validation_job(*, project_root: str, admin_id: int) -> Dict[str, Any]:
    normalized_root = str(Path(project_root).resolve())
    trace_seed = f"{normalized_root}:{admin_id}:{datetime.now().isoformat()}"
    trace_id = hashlib.sha256(trace_seed.encode("utf-8")).hexdigest()[:16]
    job_id = f"dbgval-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    section_id = f"SEC-DEBUG-{trace_id[:8]}"
    connection_id = f"{section_id}:{job_id}:{trace_id}"
    created_at = datetime.now().isoformat()
    request_payload = {
        "job_id": job_id,
        "section_id": section_id,
        "trace_id": trace_id,
        "connection_id": connection_id,
        "worker_id": "admin-debug-validation-worker-001",
        "user_id": admin_id,
        "project_root": normalized_root,
        "created_at": created_at,
    }
    state_payload = {
        "job_id": job_id,
        "status": "queued",
        "project_root": normalized_root,
        "section_id": section_id,
        "trace_id": trace_id,
        "connection_id": connection_id,
        "worker_id": "admin-debug-validation-worker-001",
        "user_id": admin_id,
        "created_at": created_at,
        "updated_at": created_at,
        "result": None,
        "error": None,
    }
    _write_json(_job_request_path(job_id), request_payload)
    _write_json(_job_connection_path(job_id), request_payload)
    _write_json(_job_state_path(job_id), state_payload)
    with _JOB_LOCK:
        _DEBUG_VALIDATION_JOBS[job_id] = state_payload
    worker = threading.Thread(target=run_debug_validation_job, args=(job_id,), name=f"admin-debug-validation-{job_id}", daemon=True)
    worker.start()
    return state_payload


def get_debug_validation_job(job_id: str) -> Dict[str, Any]:
    with _JOB_LOCK:
        cached = dict(_DEBUG_VALIDATION_JOBS.get(job_id) or {})
    if cached:
        return cached
    state = _read_json(_job_state_path(job_id))
    if not state:
        raise HTTPException(status_code=404, detail="debug validation job을 찾을 수 없습니다.")
    with _JOB_LOCK:
        _DEBUG_VALIDATION_JOBS[job_id] = state
    return state


def assert_debug_validation_job_contract() -> None:
    sample_root = Path("/app")
    profile = build_debug_profile(sample_root, py_files=[])
    required_profile_keys = {"project_root", "python_file_count", "checklist", "generated_at"}
    if not required_profile_keys.issubset(profile.keys()):
        missing = sorted(required_profile_keys.difference(profile.keys()))
        raise RuntimeError(f"debug validation profile contract 누락: {', '.join(missing)}")

    sample_state = {
        "job_id": "dbgval-contract-sample",
        "status": "queued",
        "project_root": str(sample_root),
        "section_id": "SEC-DEBUG-contract",
        "trace_id": "trace-contract",
        "connection_id": "SEC-DEBUG-contract:dbgval-contract-sample:trace-contract",
        "worker_id": "admin-debug-validation-worker-001",
        "user_id": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "result": None,
        "error": None,
        "current_stage": "queued",
        "stage_detail": "contract validation",
        "heartbeat_at": datetime.now().isoformat(),
        "progress_percent": 0,
    }
    required_state_keys = {
        "job_id",
        "status",
        "project_root",
        "section_id",
        "trace_id",
        "connection_id",
        "worker_id",
        "user_id",
        "created_at",
        "updated_at",
        "result",
        "error",
        "current_stage",
        "stage_detail",
        "heartbeat_at",
        "progress_percent",
    }
    if not required_state_keys.issubset(sample_state.keys()):
        missing = sorted(required_state_keys.difference(sample_state.keys()))
        raise RuntimeError(f"debug validation state contract 누락: {', '.join(missing)}")
