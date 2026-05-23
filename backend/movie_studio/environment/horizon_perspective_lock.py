from __future__ import annotations

from typing import Dict

from backend.movie_studio.contracts.environment_contract import EnvironmentContract


def build_horizon_perspective_lock(environment: EnvironmentContract) -> Dict[str, object]:
    return {
        "environment_id": environment.environment_id,
        "perspective_lock": environment.perspective_lock,
        "horizon_lock": environment.horizon_lock,
        "rules": [
            "vertical lines must remain stable",
            "horizon must not jump between shots",
            "camera perspective drift must remain below tolerance",
        ],
    }
