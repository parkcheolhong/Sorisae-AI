from __future__ import annotations

import httpx
import os
import random

_orchestrator_chat_http_client: httpx.AsyncClient | None = None
_orchestrator_chat_http_client_signature: tuple[str, float] | None = None


def _is_true(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_chat_endpoint_chain(ollama_base: str) -> list[str]:
    primary = str(os.getenv("SORISAE_URL", "")).strip()
    enabled = _is_true(os.getenv("SORISAE_CENTRAL_ENABLED", "false"))
    if not enabled or not primary:
        return [ollama_base]
    ratio_raw = str(os.getenv("SORISAE_CENTRAL_RATIO", "1.0")).strip()
    try:
        ratio = float(ratio_raw)
    except ValueError:
        ratio = 1.0
    ratio = max(0.0, min(1.0, ratio))
    if ratio <= 0.0:
        return [ollama_base]
    if ratio < 1.0 and random.random() > ratio:
        return [ollama_base]
    if primary.rstrip("/") == ollama_base.rstrip("/"):
        return [ollama_base]
    return [primary, ollama_base]


def _resolve_sorisae_fallback_timeout(timeout_sec: float) -> float:
    raw = str(os.getenv("SORISAE_FALLBACK_TIMEOUT_SEC", "2.5")).strip()
    try:
        parsed = float(raw)
    except ValueError:
        parsed = 2.5
    parsed = max(0.2, parsed)
    return min(float(timeout_sec), parsed)


def _extract_response_content(data: object) -> str:
    choices = data.get("choices") if isinstance(data, dict) else None
    first_choice = choices[0] if isinstance(choices, list) and choices else {}
    message = first_choice.get("message") if isinstance(first_choice, dict) else {}
    if not isinstance(message, dict):
        return ""
    return str(message.get("content") or "").strip()


async def get_orchestrator_chat_http_client(
    *,
    ollama_base: str,
    timeout_sec: float,
) -> httpx.AsyncClient:
    global _orchestrator_chat_http_client
    global _orchestrator_chat_http_client_signature

    signature = (ollama_base, timeout_sec)
    if (
        _orchestrator_chat_http_client is not None
        and _orchestrator_chat_http_client_signature == signature
    ):
        return _orchestrator_chat_http_client

    if _orchestrator_chat_http_client is not None:
        await _orchestrator_chat_http_client.aclose()

    _orchestrator_chat_http_client = httpx.AsyncClient(
        base_url=ollama_base,
        timeout=timeout_sec,
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    _orchestrator_chat_http_client_signature = signature
    return _orchestrator_chat_http_client


async def call_orchestrator_chat_llm(
    *,
    route_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    ollama_base: str,
    timeout_sec: float,
    build_ollama_options,
) -> str:
    options = build_ollama_options(
        route_key,
        {
            "num_predict": max_tokens,
            "temperature": 0.4,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
        },
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt}],
        "stream": False,
        "max_tokens": int(options.get("num_predict", max_tokens)),
        "temperature": float(options.get("temperature", 0.4)),
        "top_p": float(options.get("top_p", 0.9)),
    }
    endpoint_chain = _resolve_chat_endpoint_chain(ollama_base)
    sorisae_timeout_sec = _resolve_sorisae_fallback_timeout(timeout_sec)
    last_error: Exception | None = None
    for index, endpoint_base in enumerate(endpoint_chain):
        client = await get_orchestrator_chat_http_client(
            ollama_base=endpoint_base,
            timeout_sec=timeout_sec,
        )
        try:
            request_timeout = timeout_sec if endpoint_base.rstrip("/") == ollama_base.rstrip("/") else sorisae_timeout_sec
            response = await client.post("/chat/completions", json=payload, timeout=request_timeout)
            response.raise_for_status()
            return _extract_response_content(response.json())
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            last_error = exc
            if index < len(endpoint_chain) - 1:
                continue
            raise

    if last_error is not None:
        raise last_error
    return ""
