from __future__ import annotations

from typing import Dict


def build_cta_choreography(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "cta_window_seconds": int(payload.get("cta_window_seconds") or 10),
        "cta_intent": str(payload.get("cta_intent") or "hero close with confident motion").strip() or "hero close with confident motion",
        "rules": [
            "CTA must evolve with visible pose progression",
            "CTA must not collapse into a freeze-frame",
            "CTA should keep face, hands, and hero object readable",
        ],
    }
