from __future__ import annotations

from typing import Dict


def build_upscale_request(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "provider": "upscale-engine",
        "payload": payload,
        "mode": "photoreal-detail-restore",
    }
