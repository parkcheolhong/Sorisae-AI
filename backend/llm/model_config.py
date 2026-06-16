import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import URLError
from urllib.request import urlopen


DEFAULT_OLLAMA_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
PREFERRED_VLLM_MODEL_32B_AWQ = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
FALLBACK_VLLM_MODEL_14B_AWQ = "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"
PREFERRED_VLLM_MODEL_CANDIDATES = (
    PREFERRED_VLLM_MODEL_32B_AWQ,
    FALLBACK_VLLM_MODEL_14B_AWQ,
)
RUNTIME_CONFIG_PATH = Path(__file__).resolve().parents[2] / "knowledge" / "orchestrator_runtime_config.json"
MODEL_ROUTE_KEYS = [
    "default",
    "reasoning",
    "coding",
    "chat",
    "voice_chat",
    "planner",
    "coder",
    "reviewer",
    "designer",
    "smart_planner",
    "smart_executor",
    "smart_designer",
]
EXECUTION_ACCELERATION_MODES = {"cpu_only", "gpu_only"}
CURRENT_GPU_PROFILE_KEY = "rtx5090_32gb"
UPPER_TIER_PROFILE_KEY = "upper_tier_70b"
QWEN_CODER_Q4_TAG = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
QWEN_CODER_Q5_TAG = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
QWEN_CODER_Q6_TAG = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
QWEN_CODER_Q8_TAG = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
FULL_GPU_OFFLOAD_NUM_GPU = -1
SAFE_GPU_NUM_GPU = 24
SAFE_CPU_THREAD_CAP = 24
SAFE_MEMORY_OCCUPANCY_LIMIT_PERCENT = 80
SAFE_COMPUTE_USAGE_LIMIT_PERCENT = 85
OLLAMA_TAGS_CACHE_TTL_SEC = max(5.0, float(os.getenv("OLLAMA_TAGS_CACHE_TTL_SEC", "300")))
GPU_RUNTIME_CACHE_TTL_SEC = max(5.0, float(os.getenv("GPU_RUNTIME_CACHE_TTL_SEC", "60")))
RUNTIME_CONFIG_CACHE_TTL_SEC = max(1.0, float(os.getenv("RUNTIME_CONFIG_CACHE_TTL_SEC", "30")))
_MODEL_CONFIG_CACHE: Dict[str, Dict[str, Any]] = {}


def _env_first(*keys: str) -> str:
    for key in keys:
        value = str(os.getenv(key, "")).strip()
        if value:
            return value
    return ""


def _read_cached_value(cache_key: str, *, ttl_sec: float) -> Any | None:
    cached = _MODEL_CONFIG_CACHE.get(cache_key)
    if not cached:
        return None
    captured_at = float(cached.get("captured_at") or 0.0)
    if (time.time() - captured_at) > ttl_sec:
        _MODEL_CONFIG_CACHE.pop(cache_key, None)
        return None
    return cached.get("value")


def _write_cached_value(cache_key: str, value: Any) -> Any:
    _MODEL_CONFIG_CACHE[cache_key] = {"captured_at": time.time(), "value": value}
    return value


def _load_runtime_config() -> Dict[str, Any]:
    cached = _read_cached_value("runtime_config", ttl_sec=RUNTIME_CONFIG_CACHE_TTL_SEC)
    if isinstance(cached, dict):
        return dict(cached)
    if not RUNTIME_CONFIG_PATH.exists():
        return {}
    try:
        payload = json.loads(RUNTIME_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    result = payload if isinstance(payload, dict) else {}
    return dict(_write_cached_value("runtime_config", result))


def _runtime_model_routes() -> Dict[str, str]:
    payload = _load_runtime_config()
    model_routes = payload.get("model_routes")
    if not isinstance(model_routes, dict):
        return {}
    normalized: Dict[str, str] = {}
    for key in MODEL_ROUTE_KEYS:
        value = str(model_routes.get(key, "")).strip()
        if value:
            normalized[key] = value
    return normalized


def get_advisory_controls() -> Dict[str, Any]:
    payload = _load_runtime_config()
    raw_controls = payload.get("advisory_controls")
    defaults: Dict[str, Any] = {
        "clarification_questions_enabled": True,
        "max_clarification_questions": 3,
        "evidence_panel_enabled": True,
        "max_evidence_items": 5,
        "next_action_suggestions_enabled": True,
        "max_next_actions": 3,
        "scientific_reasoning_enabled": True,
        "systems_thinking_enabled": True,
        "future_tech_expansion_enabled": True,
        "cross_domain_synthesis_enabled": True,
        "innovation_scenarios_enabled": True,
        "max_innovation_scenarios": 5,
        "max_system_design_alternatives": 4,
    }
    if not isinstance(raw_controls, dict):
        return defaults
    merged = dict(defaults)
    for key, default_value in defaults.items():
        candidate = raw_controls.get(key)
        if isinstance(default_value, bool):
            if isinstance(candidate, bool):
                merged[key] = candidate
        elif isinstance(default_value, int):
            if not isinstance(candidate, bool):
                try:
                    merged[key] = int(candidate)
                except (TypeError, ValueError):
                    pass
        else:
            merged[key] = candidate if candidate is not None else default_value
    return merged


def _default_execution_controls(profile_key: str) -> Dict[str, Dict[str, Any]]:
    controls: Dict[str, Dict[str, Any]] = {}
    for key in MODEL_ROUTE_KEYS:
        controls[key] = {
            "acceleration_mode": "gpu_only",
            "num_gpu": SAFE_GPU_NUM_GPU,
            "num_thread": SAFE_CPU_THREAD_CAP,
        }
    return controls


def _runtime_execution_controls() -> Dict[str, Dict[str, Any]]:
    payload = _load_runtime_config()
    selected_profile = str(payload.get("selected_profile") or CURRENT_GPU_PROFILE_KEY).strip() or CURRENT_GPU_PROFILE_KEY
    defaults = _default_execution_controls(selected_profile)
    raw_controls = payload.get("execution_controls")
    if not isinstance(raw_controls, dict):
        return defaults
    normalized: Dict[str, Dict[str, Any]] = {}
    for key in MODEL_ROUTE_KEYS:
        merged = dict(defaults.get(key, {}))
        raw_value = raw_controls.get(key)
        if isinstance(raw_value, dict):
            acceleration_mode = str(raw_value.get("acceleration_mode", "")).strip()
            if acceleration_mode in EXECUTION_ACCELERATION_MODES:
                merged["acceleration_mode"] = acceleration_mode
            num_gpu = raw_value.get("num_gpu")
            if num_gpu is None:
                merged.pop("num_gpu", None)
            elif not isinstance(num_gpu, bool):
                try:
                    parsed_num_gpu = int(num_gpu)
                    merged["num_gpu"] = parsed_num_gpu
                except (TypeError, ValueError):
                    pass
            num_thread = raw_value.get("num_thread")
            if num_thread is None:
                merged.pop("num_thread", None)
            elif not isinstance(num_thread, bool):
                try:
                    merged["num_thread"] = int(num_thread)
                except (TypeError, ValueError):
                    pass
        if merged.get("acceleration_mode") == "cpu_only":
            merged["num_gpu"] = 0
        elif merged.get("num_gpu") == 0:
            merged.pop("num_gpu", None)
        normalized[key] = merged
    return normalized


def get_configured_execution_controls() -> Dict[str, Dict[str, Any]]:
    return _runtime_execution_controls()


def build_ollama_options(route_key: str, base_options: Dict[str, Any] | None = None) -> Dict[str, Any]:
    options = dict(base_options or {})
    control = get_configured_execution_controls().get(route_key, {})
    acceleration_mode = str(control.get("acceleration_mode") or "gpu_only").strip()
    if acceleration_mode == "cpu_only":
        options["num_gpu"] = 0
    elif control.get("num_gpu") is not None:
        configured_num_gpu = int(control["num_gpu"])
        if configured_num_gpu < 0:
            options["num_gpu"] = SAFE_GPU_NUM_GPU
        else:
            options["num_gpu"] = configured_num_gpu
    else:
        options["num_gpu"] = SAFE_GPU_NUM_GPU
    if control.get("num_thread") is not None:
        options["num_thread"] = max(1, min(int(control["num_thread"]), SAFE_CPU_THREAD_CAP))
    else:
        options["num_thread"] = SAFE_CPU_THREAD_CAP
    return options


def _runtime_or_env(route_key: str, *env_keys: str) -> str:
    runtime_value = _runtime_model_routes().get(route_key, "")
    if runtime_value:
        return runtime_value
    return _env_first(*env_keys)


def get_default_model() -> str:
    return _runtime_or_env("default", "OLLAMA_MODEL", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_reasoning_model() -> str:
    return _runtime_or_env("reasoning", "LLM_MODEL_REASONING", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_coding_model() -> str:
    return _runtime_or_env("coding", "LLM_MODEL_CODING", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_chat_model() -> str:
    return _runtime_or_env("chat", "LLM_MODEL_CHAT", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_voice_chat_model() -> str:
    return _runtime_or_env("voice_chat", "LLM_MODEL_VOICE_CHAT", "LLM_MODEL_CHAT", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_planner_model() -> str:
    return _runtime_or_env("planner", "LLM_MODEL_PLANNER", "LLM_MODEL_REASONING", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_coder_model() -> str:
    return _runtime_or_env("coder", "LLM_MODEL_CODER", "LLM_MODEL_CODING", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_reviewer_model() -> str:
    return _runtime_or_env("reviewer", "LLM_MODEL_REVIEWER", "LLM_MODEL_REASONING", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_designer_model() -> str:
    return _runtime_or_env("designer", "LLM_MODEL_DESIGNER", "LLM_MODEL_CHAT", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_smart_planner_model() -> str:
    return _runtime_or_env("smart_planner", "LLM_MODEL_SMART_PLANNER", "LLM_MODEL_REASONING", "LLM_MODEL_PLANNER", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_smart_executor_model() -> str:
    return _runtime_or_env("smart_executor", "LLM_MODEL_SMART_EXECUTOR", "LLM_MODEL_CODING", "LLM_MODEL_CODER", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_smart_designer_model() -> str:
    return _runtime_or_env("smart_designer", "LLM_MODEL_SMART_DESIGNER", "LLM_MODEL_DESIGNER", "LLM_MODEL_CHAT", "LLM_MODEL_DEFAULT") or DEFAULT_OLLAMA_MODEL


def get_configured_model_routes() -> Dict[str, str]:
    routes = {
        "default": get_default_model(),
        "reasoning": get_reasoning_model(),
        "coding": get_coding_model(),
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
    resolve_live = str(os.getenv("LLM_RESOLVE_LIVE_MODELS", "true")).strip().lower() not in {
        "0", "false", "no", "off",
    }
    if resolve_live:
        routes = resolve_live_model_routes(routes)
    return routes


def _pick_first_available(available_models: List[str], candidates: List[str], fallback: str) -> str:
    available_set = set(available_models)
    for candidate in candidates:
        if candidate in available_set:
            return candidate
    return fallback


def pick_best_live_vllm_model(available_models: List[str], preferred: str = "") -> str:
    """vLLM /v1/models 목록에서 RTX 5090 용도에 맞는 최적 모델 ID 선택."""
    if not available_models:
        return preferred or PREFERRED_VLLM_MODEL_32B_AWQ
    available_set = set(available_models)
    if preferred and preferred in available_set:
        return preferred
    for candidate in PREFERRED_VLLM_MODEL_CANDIDATES:
        if candidate in available_set:
            return candidate
    for model_id in available_models:
        lowered = model_id.lower()
        if "32b" in lowered and "awq" in lowered and "coder" in lowered:
            return model_id
    for model_id in available_models:
        lowered = model_id.lower()
        if "14b" in lowered and "awq" in lowered and "coder" in lowered:
            return model_id
    return available_models[0]


def resolve_live_model_routes(
    model_routes: Dict[str, str],
    available_models: List[str] | None = None,
) -> Dict[str, str]:
    """설정 라우트를 live vLLM 모델 ID에 맞춘다 (32B AWQ 우선, 14B AWQ 폴백)."""
    resolved_models = list(available_models) if isinstance(available_models, list) else get_available_ollama_models()
    if not resolved_models:
        return dict(model_routes)
    best = pick_best_live_vllm_model(resolved_models, model_routes.get("default", ""))
    return {key: (value if value in resolved_models else best) for key, value in model_routes.items()}


def _runtime_profile_payload(key: str, label: str, description: str, hardware_hint: str, available_models: List[str]) -> Dict[str, Any]:
    fallback_default = get_default_model()
    if key == CURRENT_GPU_PROFILE_KEY:
        model_routes = {
            "default": _pick_first_available(available_models, [QWEN_CODER_Q5_TAG, QWEN_CODER_Q4_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "reasoning": _pick_first_available(available_models, [QWEN_CODER_Q6_TAG, QWEN_CODER_Q5_TAG, QWEN_CODER_Q4_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "coding": _pick_first_available(available_models, [QWEN_CODER_Q5_TAG, QWEN_CODER_Q6_TAG, QWEN_CODER_Q4_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "chat": _pick_first_available(available_models, [QWEN_CODER_Q4_TAG, QWEN_CODER_Q5_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "voice_chat": _pick_first_available(available_models, [QWEN_CODER_Q4_TAG, QWEN_CODER_Q5_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "planner": _pick_first_available(available_models, [QWEN_CODER_Q6_TAG, QWEN_CODER_Q5_TAG, QWEN_CODER_Q4_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "coder": _pick_first_available(available_models, [QWEN_CODER_Q5_TAG, QWEN_CODER_Q6_TAG, QWEN_CODER_Q4_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "reviewer": _pick_first_available(available_models, [QWEN_CODER_Q6_TAG, QWEN_CODER_Q5_TAG, QWEN_CODER_Q4_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "designer": _pick_first_available(available_models, [QWEN_CODER_Q4_TAG, QWEN_CODER_Q5_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "smart_planner": _pick_first_available(available_models, [QWEN_CODER_Q6_TAG, QWEN_CODER_Q5_TAG, QWEN_CODER_Q4_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "smart_executor": _pick_first_available(available_models, [QWEN_CODER_Q5_TAG, QWEN_CODER_Q6_TAG, QWEN_CODER_Q4_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
            "smart_designer": _pick_first_available(available_models, [QWEN_CODER_Q4_TAG, QWEN_CODER_Q5_TAG, FALLBACK_VLLM_MODEL_14B_AWQ, "qwen2.5-coder:32b"], fallback_default),
        }
        settings = {
            "selected_profile": CURRENT_GPU_PROFILE_KEY,
            "max_tokens_per_step": 32768,
            "default_request_max_tokens": 12288,
            "chat_request_max_tokens": 768,
            "default_agent_max_tokens": 8192,
            "planner_max_tokens": 8192,
            "coder_max_tokens": 12288,
            "reviewer_max_tokens": 8192,
            "step_timeout_sec": 1200,
            "job_timeout_sec": 10800,
            "agent_http_timeout_sec": 1800,
            "forensic_max_inventory": 2000,
            "max_force_retries": 60,
            "force_complete": False,
            "allow_synthetic_fallback": False,
            "min_files": 27,
            "min_dirs": 5,
        }
        execution_controls = _default_execution_controls(key)
    else:
        model_routes = {
            "default": _pick_first_available(available_models, ["qwen2.5:72b", "llama3.3:70b", "deepseek-r1:70b", "qwen2.5-coder:32b"], fallback_default),
            "reasoning": _pick_first_available(available_models, ["deepseek-r1:70b", "qwen2.5:72b", "qwq:32b"], fallback_default),
            "coding": _pick_first_available(available_models, ["qwen2.5:72b", "deepseek-r1:70b", "qwen2.5-coder:32b"], fallback_default),
            "chat": _pick_first_available(available_models, ["llama3.3:70b", "qwen2.5:72b", "gemma3:27b"], fallback_default),
            "voice_chat": _pick_first_available(available_models, ["glm4:latest", "gemma3:27b"], fallback_default),
            "planner": _pick_first_available(available_models, ["deepseek-r1:70b", "qwen2.5:72b", "qwq:32b"], fallback_default),
            "coder": _pick_first_available(available_models, ["qwen2.5:72b", "deepseek-r1:70b", "qwen2.5-coder:32b"], fallback_default),
            "reviewer": _pick_first_available(available_models, ["deepseek-r1:70b", "qwen2.5:72b", "deepseek-r1:32b"], fallback_default),
            "designer": _pick_first_available(available_models, ["llama3.3:70b", "qwen2.5:72b", "gemma3:27b"], fallback_default),
            "smart_planner": _pick_first_available(available_models, ["deepseek-r1:70b", "qwen2.5:72b", "qwq:32b"], fallback_default),
            "smart_executor": _pick_first_available(available_models, ["qwen2.5:72b", "deepseek-r1:70b", "qwen2.5-coder:32b"], fallback_default),
            "smart_designer": _pick_first_available(available_models, ["llama3.3:70b", "qwen2.5:72b", "gemma3:27b"], fallback_default),
        }
        settings = {
            "selected_profile": UPPER_TIER_PROFILE_KEY,
            "max_tokens_per_step": 65536,
            "default_request_max_tokens": 24576,
            "chat_request_max_tokens": 1536,
            "default_agent_max_tokens": 32768,
            "planner_max_tokens": 24576,
            "coder_max_tokens": 32768,
            "reviewer_max_tokens": 24576,
            "step_timeout_sec": 1800,
            "job_timeout_sec": 14400,
            "agent_http_timeout_sec": 3600,
            "forensic_max_inventory": 4000,
            "max_force_retries": 99,
            "force_complete": False,
            "allow_synthetic_fallback": False,
            "min_files": 27,
            "min_dirs": 5,
        }
        execution_controls = _default_execution_controls(key)
    return {
        "key": key,
        "label": label,
        "description": description,
        "hardware_hint": hardware_hint,
        "model_routes": model_routes,
        "execution_controls": execution_controls,
        "settings": settings,
    }


def get_recommended_runtime_profiles(available_models: List[str] | None = None) -> List[Dict[str, Any]]:
    resolved_models = list(available_models) if isinstance(available_models, list) else get_available_ollama_models()
    return [
        _runtime_profile_payload(CURRENT_GPU_PROFILE_KEY, "RTX 5090 32GB 권장", "현재 단일 32GB VRAM 환경에서 실사용 가능한 안정 라우팅입니다.", "RTX 5090 32GB 1장, RAM 128GB 권장", resolved_models),
        _runtime_profile_payload(UPPER_TIER_PROFILE_KEY, "상위 서버 70B 권장", "48GB+ 단일 GPU 또는 다중 GPU 서버용 상위 라우팅입니다.", "VRAM 48GB 이상 또는 다중 GPU 서버 권장", resolved_models),
    ]


def get_available_ollama_models() -> List[str]:
    cached = _read_cached_value("available_ollama_models", ttl_sec=OLLAMA_TAGS_CACHE_TTL_SEC)
    if isinstance(cached, list):
        return list(cached)
    ollama_base = os.getenv("OLLAMA_BASE", "http://host.docker.internal:8008/v1")
    try:
        with urlopen(f"{ollama_base}/models", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError, OSError):
        return []
    models = payload.get("data") if isinstance(payload, dict) else []
    if not isinstance(models, list):
        return []
    available = [str(item.get("id", "")).strip() for item in models if isinstance(item, dict) and str(item.get("id", "")).strip()]
    result = sorted(set(available))
    return list(_write_cached_value("available_ollama_models", result))


def get_gpu_runtime_info() -> Dict[str, Any]:
    cached = _read_cached_value("gpu_runtime_info", ttl_sec=GPU_RUNTIME_CACHE_TTL_SEC)
    if isinstance(cached, dict):
        return dict(cached)
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except Exception as exc:
        result = {"available": False, "devices": [], "error": str(exc)}
        return dict(_write_cached_value("gpu_runtime_info", result))
    if completed.returncode != 0:
        result = {"available": False, "devices": [], "error": completed.stderr.strip() or completed.stdout.strip()}
        return dict(_write_cached_value("gpu_runtime_info", result))
    devices = []
    for raw_line in completed.stdout.splitlines():
        parts = [part.strip() for part in raw_line.split(",")]
        if len(parts) < 4:
            continue
        devices.append({
            "name": parts[0],
            "memory_total_mb": int(parts[1] or 0),
            "memory_used_mb": int(parts[2] or 0),
            "utilization_gpu": int(parts[3] or 0),
        })
    result = {"available": len(devices) > 0, "devices": devices}
    return dict(_write_cached_value("gpu_runtime_info", result))
