from __future__ import annotations

from typing import Any, Optional


def bounded_token_floor(target: int, max_tokens_per_step: int) -> int:
    return min(max_tokens_per_step, max(1024, int(target)))


def coerce_runtime_int(
    value: Any,
    fallback: int,
    *,
    minimum: int,
    maximum: Optional[int] = None,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = fallback
    parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def coerce_runtime_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
        return fallback
    if value is None:
        return fallback
    return bool(value)


def resolve_step_token_budget(
    requested: Optional[int],
    *,
    minimum: int,
    preferred_default: Optional[int] = None,
    default_agent_max_tokens: int,
    max_tokens_per_step: int,
) -> int:
    effective_budget = int(preferred_default or default_agent_max_tokens)
    requested_cap = int(requested or 0)
    if requested_cap > 0:
        effective_budget = min(effective_budget, requested_cap)
    effective_budget = max(
        effective_budget,
        bounded_token_floor(minimum, max_tokens_per_step),
    )
    return min(max_tokens_per_step, effective_budget)


def agent_default_token_budget(
    agent_key: str,
    *,
    planner_max_tokens: int,
    coder_max_tokens: int,
    reviewer_max_tokens: int,
    default_agent_max_tokens: int,
) -> int:
    if agent_key == "planner":
        return planner_max_tokens
    if agent_key == "coder":
        return coder_max_tokens
    if agent_key == "reviewer":
        return reviewer_max_tokens
    return default_agent_max_tokens


def agent_prompt_char_limit(
    agent_key: str,
    *,
    planner_prompt_char_limit: int,
    coder_prompt_char_limit: int,
    reviewer_prompt_char_limit: int,
) -> int:
    if agent_key == "planner":
        return planner_prompt_char_limit
    if agent_key == "coder":
        return coder_prompt_char_limit
    if agent_key == "reviewer":
        return reviewer_prompt_char_limit
    return coder_prompt_char_limit


def agent_context_char_limit(
    agent_key: str,
    *,
    planner_context_char_limit: int,
    coder_context_char_limit: int,
    reviewer_context_char_limit: int,
) -> int:
    if agent_key == "planner":
        return planner_context_char_limit
    if agent_key == "coder":
        return coder_context_char_limit
    if agent_key == "reviewer":
        return reviewer_context_char_limit
    return coder_context_char_limit


def truncate_prompt_segment(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...[truncated]"
