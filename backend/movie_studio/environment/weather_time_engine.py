from __future__ import annotations

from typing import Dict

from backend.movie_studio.contracts.environment_contract import EnvironmentContract


def build_weather_time_contract(environment: EnvironmentContract) -> Dict[str, object]:
    return {
        "environment_id": environment.environment_id,
        "time_of_day": environment.time_of_day,
        "weather_mode": environment.weather_mode,
        "rules": [
            "weather pattern must remain stable",
            "sun position must remain stable unless story-motivated",
            "atmospheric haze must remain continuous",
        ],
    }
