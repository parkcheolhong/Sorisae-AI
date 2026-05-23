from __future__ import annotations

import re
from typing import Any, Dict, List

from .models import AutoConnectMeta, FlowTraceCommand, FlowTraceStep

ADMIN_AUTONOMOUS_FLOW_TRACE: List[Dict[str, Any]] = [
    {
        "flow_id": "FLOW-001",
        "step_number": 1,
        "step_id": "FLOW-001-1",
        "action": "INTAKE",
        "title": "멀티 명령 해석",
    },
    {
        "flow_id": "FLOW-001",
        "step_number": 2,
        "step_id": "FLOW-001-2",
        "action": "COMMAND_SPLIT",
        "title": "명령 분해",
    },
    {
        "flow_id": "FLOW-002",
        "step_number": 1,
        "step_id": "FLOW-002-1",
        "action": "EXECUTION_BIND",
        "title": "실행 연결",
    },
    {
        "flow_id": "FLOW-002",
        "step_number": 2,
        "step_id": "FLOW-002-2",
        "action": "API_RESPONSE",
        "title": "API 응답 정리",
    },
    {
        "flow_id": "FLOW-003",
        "step_number": 1,
        "step_id": "FLOW-003-1",
        "action": "LOG_SYNC",
        "title": "로그 동기화",
    },
    {
        "flow_id": "FLOW-003",
        "step_number": 2,
        "step_id": "FLOW-003-2",
        "action": "UI_HANDOFF",
        "title": "관리자 UI 반영",
    },
    {
        "flow_id": "FLOW-004",
        "step_number": 1,
        "step_id": "FLOW-004-1",
        "action": "MULTI_TURN_SYNC",
        "title": "멀티 대화 동기화",
    },
    {
        "flow_id": "FLOW-004",
        "step_number": 2,
        "step_id": "FLOW-004-2",
        "action": "DIRECTIVE_QA_BIND",
        "title": "지시형 질의 응답 연결",
    },
]


def build_admin_flow_trace(state: str = "ready") -> List[FlowTraceStep]:
    return [
        FlowTraceStep(
            flow_id=str(item["flow_id"]),
            step_id=str(item["step_id"]),
            action=str(item["action"]),
            title=str(item["title"]),
            trace_id=f"{item['flow_id']}:{item['step_id']}:{item['action']}",
            step_number=int(item.get("step_number") or 0) or None,
            state=state,
        )
        for item in ADMIN_AUTONOMOUS_FLOW_TRACE
    ]


def split_multi_command_text(source_text: str) -> List[str]:
    normalized = str(source_text or "").replace("\r", "\n")
    if not normalized.strip():
        return []
    raw_parts = re.split(r"\n+|\s+/\s+|\s*;\s*", normalized)
    commands: List[str] = []
    for part in raw_parts:
        cleaned = re.sub(r"^\s*(?:\d+[.)-]\s*|[-•*]+\s*)", "", str(part or "")).strip()
        if cleaned:
            commands.append(cleaned)
    return commands[: len(ADMIN_AUTONOMOUS_FLOW_TRACE)]


def build_multi_command_plan(source_text: str) -> List[FlowTraceCommand]:
    commands = split_multi_command_text(source_text)
    trace_steps = build_admin_flow_trace()
    if not commands:
        return []
    plan: List[FlowTraceCommand] = []
    for index, command_text in enumerate(commands):
        trace_step = trace_steps[min(index, len(trace_steps) - 1)]
        plan.append(
            FlowTraceCommand(
                command_id=f"CMD-{index + 1:03d}",
                command_text=command_text,
                flow_id=trace_step.flow_id,
                step_id=trace_step.step_id,
                action=trace_step.action,
                title=trace_step.title,
                trace_id=trace_step.trace_id,
            )
        )
    return plan


def resolve_active_trace(state_history: List[str]) -> FlowTraceStep:
    flow_trace = build_admin_flow_trace(state="active")
    lookup = {item.step_id: item for item in flow_trace}
    current_state = str(state_history[-1] if state_history else "").upper()
    if current_state in {"DESIGN", "PLAN"}:
        return lookup["FLOW-001-2"]
    if current_state in {"GENERATE", "BUILD", "TEST"}:
        return lookup["FLOW-002-1"]
    if current_state in {"REFLEXION", "FIX"}:
        return lookup["FLOW-003-1"]
    if current_state in {"DONE", "FAILED"}:
        return lookup["FLOW-003-2"]
    return lookup["FLOW-001-1"]


def build_lightweight_flow_trace(auto_connect: AutoConnectMeta) -> List[FlowTraceStep]:
    return [
        FlowTraceStep(
            flow_id=auto_connect.flow_id or "FLOW-ADM-CHAT",
            step_id=auto_connect.step_id or "FLOW-ADM-CHAT-1",
            action=auto_connect.action or "CHAT",
            title="경량 관리자 대화",
            trace_id=f"{auto_connect.flow_id or 'FLOW-ADM-CHAT'}:{auto_connect.step_id or 'FLOW-ADM-CHAT-1'}:{auto_connect.action or 'CHAT'}",
            step_number=1,
            state="ready",
        )
    ]
