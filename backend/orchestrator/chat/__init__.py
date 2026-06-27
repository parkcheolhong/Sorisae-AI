"""관리자 오케스트레이터 chat 모듈"""

from .flow_trace import (
    ADMIN_AUTONOMOUS_FLOW_TRACE,
    build_admin_flow_trace,
    build_multi_command_plan,
    build_lightweight_flow_trace,
    resolve_active_trace,
)
from .models import (
    AdvisoryEvidenceItem,
    AdvisoryNextAction,
    AdvisoryQuestion,
    AutoConnectMeta,
    ConversationMessage,
    FlowTraceCommand,
    FlowTraceStep,
    OrchestratorChatRequest,
    OrchestratorChatResponse,
    OrchestratorStageChatContext,
    WebGroundingItem,
)

__all__ = [
    "answer_orchestrator_chat",
    "ADMIN_AUTONOMOUS_FLOW_TRACE",
    "build_admin_flow_trace",
    "build_multi_command_plan",
    "build_lightweight_flow_trace",
    "resolve_active_trace",
    "AdvisoryEvidenceItem",
    "AdvisoryNextAction",
    "AdvisoryQuestion",
    "AutoConnectMeta",
    "ConversationMessage",
    "FlowTraceCommand",
    "FlowTraceStep",
    "OrchestratorChatRequest",
    "OrchestratorChatResponse",
    "OrchestratorStageChatContext",
    "WebGroundingItem",
]


def __getattr__(name: str):
    if name == "answer_orchestrator_chat":
        from .chat_service import answer_orchestrator_chat
        return answer_orchestrator_chat
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
