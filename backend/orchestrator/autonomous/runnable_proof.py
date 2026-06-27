"""Autonomous surface completion — 1 runnable proof (compile + health signal)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_HEALTH_ROUTE_MARKERS = (
    "/health",
    "health_check",
    "healthcheck",
    '@router.get("/health"',
    "@app.get(\"/health\"",
    "@app.get('/health'",
)


def _agent_rows(agent_results: Optional[Sequence[Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in agent_results or []:
        if isinstance(item, dict):
            rows.append(item)
            continue
        rows.append(
            {
                "agent": getattr(item, "agent", ""),
                "status": getattr(item, "status", ""),
                "artifacts": getattr(item, "artifacts", None) or {},
            }
        )
    return rows


def _validator_passed(agent_results: Optional[Sequence[Any]]) -> bool:
    for row in _agent_rows(agent_results):
        if str(row.get("agent") or "") != "validator":
            continue
        artifacts = row.get("artifacts") or {}
        if artifacts.get("passed") is True:
            return True
        if str(row.get("status") or "") == "success" and artifacts.get("passed") is not False:
            return True
    return False


def _compile_python_files(paths: List[Path]) -> List[str]:
    errors: List[str] = []
    for path in paths:
        completed = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "py_compile failed").strip()
            errors.append(f"{path.name}: {detail[:240]}")
    return errors


def _detect_health_route(paths: List[Path]) -> bool:
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lowered = text.lower()
        if "health" not in lowered:
            continue
        if any(marker.lower() in lowered for marker in _HEALTH_ROUTE_MARKERS):
            return True
        if "fastapi" in lowered and "health" in lowered:
            return True
    return False


def evaluate_runnable_proof(
    *,
    output_dir: Optional[str],
    written_files: Optional[List[str]] = None,
    validation_profile: str = "python_fastapi",
    agent_results: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    written = [str(path).strip() for path in (written_files or []) if str(path).strip()]
    validator_ok = _validator_passed(agent_results)
    result: Dict[str, Any] = {
        "ok": False,
        "proof_kind": "none",
        "detail": "",
        "compile_passed": False,
        "health_route_detected": False,
        "validator_passed": validator_ok,
        "python_file_count": 0,
        "checks": [],
    }

    if not output_dir:
        result["detail"] = "output_dir 없음 — runnable proof 미충족"
        return result

    root = Path(output_dir)
    if not root.exists():
        result["detail"] = f"output_dir 미존재: {root}"
        return result

    py_paths: List[Path] = []
    for rel in written:
        if not rel.endswith(".py"):
            continue
        candidate = root / rel
        if candidate.is_file():
            py_paths.append(candidate)
    if not py_paths:
        py_paths = sorted(root.rglob("*.py"))[:40]

    result["python_file_count"] = len(py_paths)
    if not py_paths:
        result["detail"] = "검증할 Python 파일 없음"
        return result

    compile_errors = _compile_python_files(py_paths)
    result["compile_passed"] = len(compile_errors) == 0
    result["checks"].append(
        {
            "id": "py_compile",
            "ok": result["compile_passed"],
            "detail": "모든 .py compile 통과" if result["compile_passed"] else "; ".join(compile_errors[:3]),
        }
    )

    health_detected = _detect_health_route(py_paths)
    result["health_route_detected"] = health_detected
    result["checks"].append(
        {
            "id": "health_route",
            "ok": health_detected,
            "detail": "health 라우트/핸들러 흔적 감지" if health_detected else "health 라우트 미감지",
        }
    )

    profile = str(validation_profile or "python_fastapi").strip().lower()
    if profile == "python_fastapi":
        result["proof_kind"] = "fastapi_compile_and_health"
        result["ok"] = bool(result["compile_passed"] and (health_detected or validator_ok))
        if result["ok"]:
            result["detail"] = (
                "runnable proof OK — py_compile 통과 + "
                + ("validator 통과" if validator_ok else "health 라우트 감지")
            )
        else:
            missing = []
            if not result["compile_passed"]:
                missing.append("py_compile")
            if not health_detected and not validator_ok:
                missing.append("health/validator")
            result["detail"] = "runnable proof FAIL — " + ", ".join(missing)
    else:
        result["proof_kind"] = "compile_and_validator"
        result["ok"] = bool(result["compile_passed"] and validator_ok)
        result["detail"] = (
            "runnable proof OK — compile + validator"
            if result["ok"]
            else "runnable proof FAIL — compile 또는 validator 미충족"
        )

    return result
