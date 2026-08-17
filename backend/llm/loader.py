"""
LLM Loader - Ollama 기반
"""

import httpx
import logging
import time
import os

from .model_config import (
    FULL_GPU_OFFLOAD_NUM_GPU,
    build_ollama_options,
    get_configured_execution_controls,
    get_configured_model_routes,
    get_default_model,
)

logger = logging.getLogger(__name__)

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://host.docker.internal:8008/v1")
STATUS_CHECK_TIMEOUT = float(
    os.getenv("OLLAMA_STATUS_TIMEOUT_SEC")
    or os.getenv("LLM_STATUS_TIMEOUT_SEC")
    or "5"
)
DEFAULT_GPU_LAYERS = int(
    os.getenv("OLLAMA_GPU_LAYERS")
    or os.getenv("LLM_GPU_LAYERS")
    or "0"
)
DEFAULT_CONTEXT_SIZE = int(
    os.getenv("OLLAMA_CONTEXT_SIZE")
    or os.getenv("LLM_CONTEXT_SIZE")
    or "8192"
)


class LLMLoader:

    def __init__(self):
        self.llm = None
        self.ollama_models = []
        self.last_check = 0
        self.cache_ttl = 30
        self.last_status_payload = {}

        # HTTP client 재사용
        self.client = httpx.Client(timeout=180.0)

        self._check_ollama()

    def _check_ollama(self):
        """Ollama 서버 상태 확인"""

        now = time.time()

        if now - self.last_check < self.cache_ttl:
            return

        try:
            r = self.client.get(
                f"{OLLAMA_BASE}/models",
                timeout=STATUS_CHECK_TIMEOUT,
            )

            if r.status_code == 200:
                data = r.json()
                self.ollama_models = [
                    m["id"] for m in data.get("data", [])
                ]

                logger.info(
                    f"[LLM] 연결 성공 - 모델: {self.ollama_models}"
                )

            else:
                logger.warning("Ollama 상태 확인 실패")

        except Exception as e:
            logger.warning(f"Ollama 연결 실패: {e}")
            self.ollama_models = []

        self.last_check = now

    def get_status(self):

        self._check_ollama()

        ollama_available = len(self.ollama_models) > 0
        configured_default_model = get_default_model()
        if configured_default_model in self.ollama_models:
            primary = configured_default_model
        else:
            primary = self.ollama_models[0] if self.ollama_models else None

        default_execution_control = get_configured_execution_controls().get(
            "default", {}
        )
        acceleration_mode = str(
            default_execution_control.get("acceleration_mode") or "gpu_only"
        ).strip()
        configured_num_gpu = default_execution_control.get("num_gpu")
        if configured_num_gpu is None and acceleration_mode == "gpu_only":
            configured_num_gpu = FULL_GPU_OFFLOAD_NUM_GPU

        gpu_runtime_label = None
        if acceleration_mode == "cpu_only":
            gpu_runtime_label = "CPU 전용"
        elif configured_num_gpu == FULL_GPU_OFFLOAD_NUM_GPU:
            gpu_runtime_label = "GPU 전체 오프로딩"
        elif isinstance(configured_num_gpu, int) and configured_num_gpu > 0:
            gpu_runtime_label = f"GPU {configured_num_gpu}개 사용"
        elif DEFAULT_GPU_LAYERS > 0:
            gpu_runtime_label = f"GPU {DEFAULT_GPU_LAYERS} layers"

        status_payload = {
            "loaded": ollama_available,
            "mode": "ollama" if ollama_available else "offline",
            "ollama_url": OLLAMA_BASE,
            "models": self.ollama_models,
            "configured_models": get_configured_model_routes(),
            "primary_model": primary,
            "n_gpu_layers": DEFAULT_GPU_LAYERS or None,
            "num_gpu": configured_num_gpu,
            "acceleration_mode": acceleration_mode,
            "gpu_runtime_label": gpu_runtime_label,
            "model_path": primary or "none",
            "n_ctx": DEFAULT_CONTEXT_SIZE,
            "n_batch": 512,
        }
        self.last_status_payload = dict(status_payload)
        return status_payload

    def get_cached_status(self):
        now = time.time()
        if self.last_status_payload and (now - self.last_check) < self.cache_ttl:
            return dict(self.last_status_payload)
        status = self.get_status()
        self.last_status_payload = dict(status)
        return dict(status)

    def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """
        Ollama API 호출하여 코드 생성
        """

        if not self.ollama_models:
            logger.error("사용 가능한 Ollama 모델이 없습니다.")
            return "ERROR: No Ollama model available"

        configured_default_model = get_default_model()

        selected_model = (
            configured_default_model
            if configured_default_model in self.ollama_models
            else self.ollama_models[0]
        )
        if selected_model != configured_default_model:
            logger.warning(
                "Configured Ollama model '%s' not installed; using '%s'",
                configured_default_model,
                selected_model,
            )

        url = f"{OLLAMA_BASE}/chat/completions"

        payload = {
            "model": selected_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "top_p": 0.9,
        }

        try:

            response = self.client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()

            generated_text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not generated_text:
                logger.warning("LLM 응답이 비어있습니다.")

            return generated_text

        except httpx.TimeoutException:
            logger.error("Ollama 요청 timeout")
            return "ERROR: Ollama timeout"

        except httpx.HTTPError as e:
            logger.error(f"Ollama HTTP 오류: {e}")
            return "ERROR: Ollama HTTP error"

        except Exception as e:
            logger.error(f"Ollama 코드 생성 중 오류: {e}")
            return "ERROR: LLM generation failed"


llm_loader = LLMLoader()
