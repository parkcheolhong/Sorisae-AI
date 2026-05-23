from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.llm.model_config import (
    get_chat_model,
    get_coder_model,
    get_default_model,
    get_designer_model,
    get_planner_model,
    get_reasoning_model,
    get_reviewer_model,
    get_smart_designer_model,
    get_smart_executor_model,
    get_smart_planner_model,
    get_voice_chat_model,
)

CANDIDATE_MODELS = [
    {"name": "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ", "recommended_vram_gb": 24, "expected_latency_ms": "30-60"},
    {"name": "Qwen/Qwen2.5-72B-Instruct-AWQ", "recommended_vram_gb": 48, "expected_latency_ms": "60-90"},
    {"name": "Qwen/Qwen2.5-72B-Instruct-FP16", "recommended_vram_gb": 144, "expected_latency_ms": "20-30"},
    {"name": "DeepSeek-Coder-33B-Instruct-AWQ", "recommended_vram_gb": 24, "expected_latency_ms": "35-70"},
]


def run_command(command: List[str]) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        return f"ERROR: {exc}"
    if completed.returncode != 0:
        return f"ERROR({completed.returncode}): {completed.stderr.strip() or completed.stdout.strip()}"
    return completed.stdout.strip()


def collect_gpu_info() -> Dict[str, Any]:
    query = "name,memory.total,memory.used,utilization.gpu"
    output = run_command(["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"])
    if output.startswith("ERROR"):
        return {"available": False, "error": output, "gpus": []}

    gpus: List[Dict[str, Any]] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 4:
            continue
        name, mem_total, mem_used, utilization = parts
        try:
            total_mb = int(mem_total)
            used_mb = int(mem_used)
            util = int(utilization)
        except ValueError:
            continue
        gpus.append(
            {
                "name": name,
                "memory_total_mb": total_mb,
                "memory_used_mb": used_mb,
                "memory_free_mb": max(0, total_mb - used_mb),
                "utilization_gpu_percent": util,
            }
        )

    total_free_gb = round(sum(item["memory_free_mb"] for item in gpus) / 1024.0, 2)
    max_free_gb = round(max((item["memory_free_mb"] for item in gpus), default=0) / 1024.0, 2)
    return {
        "available": bool(gpus),
        "gpus": gpus,
        "total_free_vram_gb": total_free_gb,
        "max_single_gpu_free_vram_gb": max_free_gb,
    }


def measure_http_latency(url: str, retries: int = 3, timeout_sec: float = 4.0) -> Dict[str, Any]:
    if not url:
        return {"url": url, "ok": False, "error": "empty url", "samples_ms": [], "avg_ms": None}

    samples: List[float] = []
    last_error = ""
    for _ in range(max(1, retries)):
        req = Request(url, method="GET")
        started = time.perf_counter()
        try:
            with urlopen(req, timeout=timeout_sec) as resp:
                _ = resp.read(256)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            samples.append(round(elapsed_ms, 2))
        except (TimeoutError, URLError, OSError) as exc:
            last_error = str(exc)

    if not samples:
        return {"url": url, "ok": False, "error": last_error or "request failed", "samples_ms": [], "avg_ms": None}
    avg = round(sum(samples) / len(samples), 2)
    return {"url": url, "ok": True, "error": "", "samples_ms": samples, "avg_ms": avg}


def evaluate_candidates(gpu_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    single_gpu_free = float(gpu_info.get("max_single_gpu_free_vram_gb") or 0.0)
    evaluated: List[Dict[str, Any]] = []
    for candidate in CANDIDATE_MODELS:
        required = float(candidate["recommended_vram_gb"])
        feasible = single_gpu_free >= required
        margin = round(single_gpu_free - required, 2)
        evaluated.append(
            {
                **candidate,
                "feasible_on_current_single_gpu": feasible,
                "vram_margin_gb": margin,
                "risk": "low" if margin >= 6 else ("medium" if margin >= 0 else "high"),
            }
        )
    return evaluated


def collect_model_routes() -> Dict[str, str]:
    return {
        "default": get_default_model(),
        "reasoning": get_reasoning_model(),
        "chat": get_chat_model(),
        "voice_chat": get_voice_chat_model(),
        "planner": get_planner_model(),
        "coder": get_coder_model(),
        "reviewer": get_reviewer_model(),
        "designer": get_designer_model(),
        "smart_planner": get_smart_planner_model(),
        "smart_executor": get_smart_executor_model(),
        "smart_designer": get_smart_designer_model(),
    }


def main() -> int:
    output_path = Path("model_upgrade_precheck_result.json")

    ollama_base = str(os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434")).rstrip("/")
    vllm_base = str(os.getenv("VLLM_BASE", "http://127.0.0.1:8008")).rstrip("/")

    gpu_info = collect_gpu_info()
    latency_checks = {
        "ollama_tags": measure_http_latency(f"{ollama_base}/api/tags"),
        "vllm_models": measure_http_latency(f"{vllm_base}/v1/models"),
    }

    payload = {
        "checked_at": datetime.now().isoformat(),
        "gpu": gpu_info,
        "latency": latency_checks,
        "configured_routes": collect_model_routes(),
        "candidate_evaluation": evaluate_candidates(gpu_info),
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[model-precheck] wrote", output_path)
    print("[model-precheck] max single GPU free VRAM (GB):", gpu_info.get("max_single_gpu_free_vram_gb"))
    for key, value in latency_checks.items():
        print(f"[model-precheck] {key}: ok={value.get('ok')} avg_ms={value.get('avg_ms')} err={value.get('error')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
