import ast
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, cast


MAIN_PATH = Path(__file__).resolve().parent.parent / "backend" / "main.py"


def _load_functions(*names: str, extra_globals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8-sig"), filename=str(MAIN_PATH))
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Path": Path,
        "cast": cast,
        "os": os,
    }
    if extra_globals:
        namespace.update(extra_globals)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(MAIN_PATH), "exec"), namespace)
    return namespace


def test_sanitize_diagnostic_error_redacts_exception_text():
    namespace = _load_functions(
        "_sanitize_diagnostic_error",
        extra_globals={
            "_SAFE_DIAGNOSTIC_ERROR_CODES": frozenset(
                {
                    "cpu_load_unavailable",
                    "gpu_runtime_unavailable",
                    "memory_snapshot_unavailable",
                    "queue_runtime_unavailable",
                }
            ),
        },
    )

    sanitize = namespace["_sanitize_diagnostic_error"]

    assert sanitize(PermissionError("cannot open /proc/meminfo"), "memory_snapshot_unavailable") == "memory_snapshot_unavailable"
    assert sanitize("gpu_runtime_unavailable", "memory_snapshot_unavailable") == "gpu_runtime_unavailable"
    assert sanitize(None, "memory_snapshot_unavailable") is None


def test_memory_snapshot_error_becomes_warning_payload():
    namespace = _load_functions(
        "_sanitize_diagnostic_error",
        "_memory_snapshot",
        extra_globals={
            "_SAFE_DIAGNOSTIC_ERROR_CODES": frozenset(
                {
                    "cpu_load_unavailable",
                    "gpu_runtime_unavailable",
                    "memory_snapshot_unavailable",
                    "queue_runtime_unavailable",
                }
            ),
            "_linux_memory_snapshot": lambda: {"error": "permission denied: /proc/meminfo"},
            "_windows_memory_snapshot": lambda: None,
            "SAFE_COMPUTE_USAGE_LIMIT_PERCENT": 90,
            "SAFE_MEMORY_OCCUPANCY_LIMIT_PERCENT": 75,
        },
    )

    payload = namespace["_memory_snapshot"]()

    assert payload["available"] is False
    assert payload["state"] == "warning"
    assert payload["error"] == "memory_snapshot_unavailable"
    assert "/proc/meminfo" not in payload["error"]


def test_cpu_and_gpu_snapshots_expose_only_safe_error_codes(monkeypatch):
    namespace = _load_functions(
        "_sanitize_diagnostic_error",
        "_cpu_snapshot",
        "_gpu_snapshot",
        extra_globals={
            "_SAFE_DIAGNOSTIC_ERROR_CODES": frozenset(
                {
                    "cpu_load_unavailable",
                    "gpu_runtime_unavailable",
                    "memory_snapshot_unavailable",
                    "queue_runtime_unavailable",
                }
            ),
            "SAFE_COMPUTE_USAGE_LIMIT_PERCENT": 90,
            "SAFE_MEMORY_OCCUPANCY_LIMIT_PERCENT": 75,
            "_relative_percent": lambda numerator, denominator: round((numerator / denominator) * 100, 1) if denominator > 0 else None,
            "_linux_cpu_usage_percent": lambda: None,
            "get_gpu_runtime_info": lambda: {
                "available": False,
                "error": "driver init failed for /dev/nvidia0",
                "devices": [],
            },
        },
    )

    def _raise_loadavg_error():
        raise OSError("cannot read /proc/loadavg")

    monkeypatch.setattr(os, "getloadavg", _raise_loadavg_error)

    cpu_payload = namespace["_cpu_snapshot"]()
    gpu_payload = namespace["_gpu_snapshot"]()

    assert cpu_payload["error"] == "cpu_load_unavailable"
    assert "/proc/loadavg" not in cpu_payload["error"]
    assert gpu_payload["error"] == "gpu_runtime_unavailable"
    assert "/dev/nvidia0" not in gpu_payload["error"]
