from __future__ import annotations

from typing import Dict


def build_external_t2v_request(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "provider": "external-t2v",
        "payload": payload,
        "requirements": ["photoreal human fidelity", "temporal consistency", "camera control"],
    }
