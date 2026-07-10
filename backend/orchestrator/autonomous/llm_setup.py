"""Autonomous orchestrator LLM wiring (FastAPI-free — scripts/tests can import safely)."""
from __future__ import annotations

import os
from typing import Callable, Dict, Tuple


def resolve_model_routes_for_live_server(model_routes: Dict[str, str]) -> Dict[str, str]:
    from backend.llm.model_config import resolve_live_model_routes

    return resolve_live_model_routes(model_routes)


def build_llm_call() -> Tuple[Callable, Dict[str, str]]:
    from backend.llm.model_config import build_ollama_options, get_configured_model_routes
    from backend.orchestrator.chat.llm_client import call_orchestrator_chat_llm

    ollama_base = os.getenv("OLLAMA_BASE", "http://host.docker.internal:8008/v1").strip()
    timeout_sec = float(os.getenv("ORCHESTRATOR_CHAT_TIMEOUT_SEC", "180"))
    model_routes = get_configured_model_routes()

    async def llm_call(*, route_key: str, model: str, system_prompt: str, user_prompt: str) -> str:
        resolved_model = model or model_routes.get(route_key, model_routes.get("default", ""))
        return await call_orchestrator_chat_llm(
            route_key=route_key,
            model=resolved_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096,
            ollama_base=ollama_base,
            timeout_sec=timeout_sec,
            build_ollama_options=build_ollama_options,
        )

    return llm_call, model_routes
