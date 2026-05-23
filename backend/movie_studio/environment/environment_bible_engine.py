from __future__ import annotations

from typing import Dict

from backend.movie_studio.contracts.environment_contract import EnvironmentContract


def build_environment_contract(payload: Dict[str, object]) -> EnvironmentContract:
    environment_type = str(payload.get("environment_type") or "studio").strip() or "studio"
    return EnvironmentContract(
        environment_id=str(payload.get("environment_id") or f"env-{environment_type}"),
        environment_type=environment_type,
        location_summary=str(payload.get("location_summary") or payload.get("background_prompt") or environment_type).strip() or environment_type,
        lighting_direction=str(payload.get("lighting_direction") or "soft key from camera-left").strip() or "soft key from camera-left",
        time_of_day=str(payload.get("time_of_day") or "day").strip() or "day",
        weather_mode=str(payload.get("weather_mode") or "clear").strip() or "clear",
        horizon_lock=environment_type in {"nature", "ocean", "coast", "sea"},
    )
