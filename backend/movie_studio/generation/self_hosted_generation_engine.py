from __future__ import annotations

from typing import Dict, List


def _normalized_list(value: object, fallback: List[str]) -> List[str]:
    items = [str(item).strip() for item in list(value or []) if str(item).strip()]
    return items or list(fallback)


def build_self_hosted_generation_bundle(payload: Dict[str, object], project_id: str) -> Dict[str, object]:
    local_model_stack = _normalized_list(
        payload.get("local_model_stack"),
        [
            "wan2.2-i2v-high-motion",
            "hunyuan-video-photoreal-refiner",
            "film-grain-detail-upscaler",
        ],
    )
    gpu_targets = _normalized_list(
        payload.get("gpu_targets"),
        ["nvidia-rtx-primary", "nvidia-rtx-secondary"],
    )
    inference_profiles = [
        {
            "stage": "base_generation",
            "model": local_model_stack[0],
            "objective": "photoreal scene motion and actor blocking",
        },
        {
            "stage": "identity_refinement",
            "model": local_model_stack[min(1, len(local_model_stack) - 1)],
            "objective": "face, hand, anatomy, and continuity repair",
        },
        {
            "stage": "mastering_upscale",
            "model": local_model_stack[min(2, len(local_model_stack) - 1)],
            "objective": "detail restoration and final mastering",
        },
    ]
    foundation_backend = {
        "provider": "video-diffusion-foundation-backend",
        "runtime_mode": "commercial-staged-foundation-generation",
        "required_total_frames": 480,
        "frames_per_second": 8,
        "operation_seconds": 60,
        "preferred_models": local_model_stack,
        "camera_motion_only_forbidden": True,
        "latent_interpolation_required": True,
        "temporal_generation_required": True,
        "shape_preservation_required": True,
        "carry_over_state_required": True,
        "restoration_required": True,
    }
    return {
        "provider": "self-hosted-movie-studio",
        "project_id": project_id,
        "runtime_mode": "offline-first",
        "external_dependency_allowed": False,
        "commercial_sovereignty": "internal-only",
        "local_model_stack": local_model_stack,
        "gpu_targets": gpu_targets,
        "inference_profiles": inference_profiles,
        "foundation_backend": foundation_backend,
        "commercial_pipeline": {
            "character_lock_required": True,
            "motion_plan_required": True,
            "overlap_chunk_seconds": 1,
            "restoration_stage": "identity_and_shape_restore",
            "mastering_stage": "nano_detail_mastering",
        },
        "storage_policy": {
            "artifact_root": f"movie_studio_assets/{project_id}",
            "retain_all_review_candidates": True,
        },
    }
