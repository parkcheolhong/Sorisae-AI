from __future__ import annotations

from typing import Dict


def build_identity_adapter_payload(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "identity_mode": "face-and-anatomy-lock",
        "payload": payload,
    }
