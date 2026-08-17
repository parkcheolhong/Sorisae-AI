from __future__ import annotations

from typing import Dict

from backend.movie_studio.contracts.environment_contract import EnvironmentContract


def build_lighting_map(environment: EnvironmentContract) -> Dict[str, object]:
    return {
        "environment_id": environment.environment_id,
        "lighting_direction": environment.lighting_direction,
        "time_of_day": environment.time_of_day,
        "rules": [
            "key light direction must stay fixed",
            "shadow density must remain believable",
            "exposure transitions must be motivated",
        ],
    }
