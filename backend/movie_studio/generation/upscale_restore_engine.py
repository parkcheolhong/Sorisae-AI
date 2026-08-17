from __future__ import annotations

from typing import Dict


def build_upscale_plan(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "target_resolution": str(payload.get("target_resolution") or "1920x1080").strip() or "1920x1080",
        "restore_passes": [
            "shape_preserve_restore",
            "edge_clarity_restore",
            "micro_detail_mastering",
        ],
        "stabilization": {
            "chunk_overlap_frames": 4,
            "seam_blend_ratio": 0.35,
            "max_blur_radius": 0.12,
            "min_edge_energy": 12.0,
        },
        "rules": [
            "preserve facial micro detail",
            "preserve hand and prop edge clarity",
            "forbid blur-heavy repair that destroys silhouette readability",
            "forbid chunk seams that create temporal jump cuts",
            "avoid over-sharpen halos and texture hallucination",
        ],
    }
