"""Multi-agent autonomous orchestrator package (①)."""

from .session import AutonomousSession, EXECUTION_MODES, StageState
from .turn_controller import TurnController, STAGE_DEFINITIONS

__all__ = [
    "autonomous_router",
    "AutonomousSession",
    "EXECUTION_MODES",
    "StageState",
    "TurnController",
    "STAGE_DEFINITIONS",
]


def __getattr__(name: str):
    if name == "autonomous_router":
        from .router import router as autonomous_router
        return autonomous_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
