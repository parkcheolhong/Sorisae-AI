"""RTX 5090 32B AWQ live model route resolution."""

from backend.llm.model_config import (
    FALLBACK_VLLM_MODEL_14B_AWQ,
    PREFERRED_VLLM_MODEL_32B_AWQ,
    pick_best_live_vllm_model,
    resolve_live_model_routes,
)


def test_pick_best_prefers_32b_when_both_loaded():
    available = [FALLBACK_VLLM_MODEL_14B_AWQ, PREFERRED_VLLM_MODEL_32B_AWQ]
    assert pick_best_live_vllm_model(available) == PREFERRED_VLLM_MODEL_32B_AWQ


def test_pick_best_falls_back_to_14b():
    available = [FALLBACK_VLLM_MODEL_14B_AWQ]
    assert pick_best_live_vllm_model(available) == FALLBACK_VLLM_MODEL_14B_AWQ


def test_resolve_live_model_routes_unifies_routes():
    routes = {
        "default": PREFERRED_VLLM_MODEL_32B_AWQ,
        "reasoning": PREFERRED_VLLM_MODEL_32B_AWQ,
    }
    resolved = resolve_live_model_routes(
        routes,
        [FALLBACK_VLLM_MODEL_14B_AWQ],
    )
    assert resolved["default"] == FALLBACK_VLLM_MODEL_14B_AWQ
    assert resolved["reasoning"] == FALLBACK_VLLM_MODEL_14B_AWQ
