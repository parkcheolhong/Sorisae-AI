from __future__ import annotations

from typing import Dict


def build_internal_runtime_policy(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "runtime_mode": "self-hosted-commercial-staged-engine",
        "operation_profile": {
            "duration_seconds": 60,
            "frames_per_second": 8,
            "required_total_frames": 480,
            "subtitle_insertion_stage": "after_frame_lock",
            "music_insertion_stage": "after_frame_lock",
            "preferred_generation_backend": "video_diffusion_foundation_backend",
            "fallback_generation_backend": None,
            "chunk_seconds": 5,
            "chunk_count": 12,
            "smoke_test_required": True,
            "restoration_required": True,
        },
        "network_required_for_core_generation": False,
        "allowed_external_roles": ["optional research", "optional benchmarking"],
        "forbidden_external_roles": [
            "mandatory core generation",
            "mandatory quality gate",
            "mandatory commercial runtime",
        ],
        "storage_strategy": {
            "project_assets_local": True,
            "review_artifacts_local": True,
            "checkpoint_cache_local": True,
        },
        "operator_note": str(payload.get("operator_note") or "internal sovereignty enforced").strip() or "internal sovereignty enforced",
    }
