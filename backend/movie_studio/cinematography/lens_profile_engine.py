from __future__ import annotations

from typing import Dict


def build_lens_profile(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "lens_profile": str(payload.get("lens_profile") or "cinematic 50mm spherical").strip() or "cinematic 50mm spherical",
        "rules": [
            "avoid non-motivated distortion",
            "keep subject scale stable within shot",
            "depth of field must support realism and subject readability",
        ],
    }
