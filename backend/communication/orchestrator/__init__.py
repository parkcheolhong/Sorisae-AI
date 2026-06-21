"""WorldLinco V2 — Call Orchestrator (라이프사이클·정책 레이어, additive).

로드맵(`docs/worldlinco-v2/WORLDLINCO_V2_ROADMAP.md`) #3. 기존 VoIP hot path
(`nadotongryoksa_voip_router`)를 변경하지 않고, 통화 **라이프사이클 상태 전이 + 정책
결정 + 감사**를 상위에서 관찰/기록하는 얇은 래퍼다. `COMM_V2_CALL_ORCHESTRATOR` env
opt-in, 기본 off. Session Core(#2) 위에 얹혀 같은 세션 키로 정렬된다.
"""

from .config import CallOrchestratorConfig, get_call_orchestrator_config, is_call_orchestrator_enabled
from .models import CallStateV2, LifecycleEvent, CallLifecycle, PolicyDecision
from .manager import CallOrchestrator

__all__ = [
    "CallOrchestratorConfig",
    "get_call_orchestrator_config",
    "is_call_orchestrator_enabled",
    "CallStateV2",
    "LifecycleEvent",
    "CallLifecycle",
    "PolicyDecision",
    "CallOrchestrator",
]
