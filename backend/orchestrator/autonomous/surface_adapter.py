"""관리자·마켓 오케스트레이터 대화창 → ① TurnController SSOT 어댑터."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from backend.orchestrator.chat.models import (
    AdvisoryNextAction,
    ConversationMessage,
    OrchestratorChatResponse,
)

logger = logging.getLogger(__name__)

_SURFACE_SPEAKERS = {
    "admin": {"user": "관리자", "user_voice": "관리자(음성)", "assistant": "오케스트레이터"},
    "marketplace": {"user": "고객", "user_voice": "고객(음성)", "assistant": "오케스트레이터"},
}


def resolve_autonomous_mode(*, mode: str = "", manual_mode: bool = True) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized in {"full_auto", "full"}:
        return "full_auto"
    if normalized in {"advisory", "advise", "analysis", "research_only"}:
        return "advisory"
    return "semi_auto"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_conversation(raw: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not raw:
        return []
    return [dict(item) for item in raw if isinstance(item, dict)]


def _conversation_message_from_dict(item: Dict[str, Any]) -> ConversationMessage:
    return ConversationMessage(
        role=str(item.get("role") or "assistant"),
        content=str(item.get("content") or ""),
        speaker=item.get("speaker"),
        step_id=item.get("step_id"),
        step_title=item.get("step_title"),
        timestamp=item.get("timestamp"),
        connection_id=item.get("connection_id"),
        flow_id=item.get("flow_id"),
        action=item.get("action"),
        route_id=item.get("route_id"),
        panel_id=item.get("panel_id"),
    )


def _build_next_actions(
    requires_approval: bool,
    *,
    stage_command_hint: Optional[str] = None,
    stage_number: Optional[float] = None,
    stage_command: Optional[str] = None,
) -> List[AdvisoryNextAction]:
    actions: List[AdvisoryNextAction] = []
    if requires_approval:
        actions.extend([
            AdvisoryNextAction(
                title="승인 후 코드 생성",
                action_type="approval",
                detail="채팅에 '승인' 또는 '진행해'라고 입력하면 STAGE 파이프라인이 실행됩니다.",
            ),
            AdvisoryNextAction(
                title="요청 수정",
                action_type="revision",
                detail="'수정' 또는 변경 사항을 말씀하시면 설계를 다시 조정합니다.",
            ),
        ])
    if stage_command == "design" and stage_number is not None:
        actions.append(
            AdvisoryNextAction(
                title=f"{stage_number:g}단계 코드 생성",
                action_type="stage_execute",
                detail=f"'{stage_number:g}단계 진행해줘' 또는 '진행해'로 해당 단계 구현을 시작합니다.",
            )
        )
    elif stage_command == "discuss" and stage_number is not None:
        actions.append(
            AdvisoryNextAction(
                title=f"{stage_number:g}단계 구현 진행",
                action_type="stage_execute",
                detail=f"아이디어 확정 후 '{stage_number:g}단계 진행해줘'로 코드 생성을 시작합니다.",
            )
        )
    if stage_command_hint and not any(a.detail == stage_command_hint for a in actions):
        actions.append(
            AdvisoryNextAction(
                title="단계 명령 안내",
                action_type="stage_hint",
                detail=stage_command_hint,
            )
        )
    return actions


def _map_autonomous_to_chat_response(
    *,
    autonomous_payload: Dict[str, Any],
    request_message: str,
    prior_conversation: List[Dict[str, Any]],
    surface: str,
    run_id: Optional[str],
    task: str,
    context_tags: Optional[List[str]] = None,
) -> OrchestratorChatResponse:
    speakers = _SURFACE_SPEAKERS.get(surface, _SURFACE_SPEAKERS["admin"])
    timestamp = _utc_now_iso()
    user_message = ConversationMessage(
        role="user",
        content=request_message,
        speaker=speakers["user"],
        timestamp=timestamp,
    )
    assistant_message = ConversationMessage(
        role="assistant",
        content=str(autonomous_payload.get("content") or ""),
        speaker=speakers["assistant"],
        step_title=str(autonomous_payload.get("current_stage") or "멀티 자율대화"),
        timestamp=timestamp,
    )

    merged_conversation = [
        _conversation_message_from_dict(item) for item in prior_conversation
    ]
    if not merged_conversation or merged_conversation[-1].content != request_message:
        merged_conversation.append(user_message)
    merged_conversation.append(assistant_message)

    requires_approval = bool(autonomous_payload.get("requires_approval"))
    execution_state = str(autonomous_payload.get("execution_state") or "idle")
    conversation_stage = "approval_pending" if requires_approval else execution_state

    agent_results = autonomous_payload.get("agent_results") or []
    inferred_goal = task.strip() or None
    if autonomous_payload.get("intent") == "code_generation":
        inferred_goal = inferred_goal or request_message[:240]

    diagnostics: Dict[str, Any] = {
        "surface": surface,
        "orchestrator_core": "autonomous_turn_controller",
        "autonomous_session_id": autonomous_payload.get("session_id"),
        "autonomous_mode": autonomous_payload.get("mode"),
        "autonomous_intent": autonomous_payload.get("intent"),
        "llm_connected": autonomous_payload.get("llm_connected"),
        "agent_results": agent_results,
        "stages_completed": autonomous_payload.get("stages_completed"),
        "stages_total": autonomous_payload.get("stages_total"),
        "stages_remaining": autonomous_payload.get("stages_remaining"),
        "stage_command": autonomous_payload.get("stage_command"),
        "stage_number": autonomous_payload.get("stage_number"),
        "stage_command_hint": autonomous_payload.get("stage_command_hint"),
        "context_tags": list(context_tags or []),
    }

    return OrchestratorChatResponse(
        reply=assistant_message,
        conversation=merged_conversation,
        output_dir=autonomous_payload.get("output_dir"),
        run_id=run_id,
        session_id=str(autonomous_payload.get("session_id") or ""),
        grounding_mode="internal",
        grounding_note="멀티 에이전트 자율 오케스트레이터(①) 코어",
        conversation_stage=conversation_stage,
        next_action_suggestions=_build_next_actions(
            requires_approval,
            stage_command_hint=autonomous_payload.get("stage_command_hint"),
            stage_number=autonomous_payload.get("stage_number"),
            stage_command=autonomous_payload.get("stage_command"),
        ),
        inferred_goal=inferred_goal,
        multi_turn_enabled=True,
        diagnostics=diagnostics,
    )


async def run_autonomous_surface_chat(
    *,
    message: str,
    owner_id: str,
    surface: str = "admin",
    session_id: Optional[str] = None,
    run_id: Optional[str] = None,
    stage_run_id: Optional[str] = None,
    task: str = "",
    project_name: Optional[str] = None,
    mode: str = "manual_9step",
    manual_mode: bool = True,
    conversation: Optional[List[Dict[str, Any]]] = None,
    context_tags: Optional[List[str]] = None,
    validation_profile: str = "python_fastapi",
) -> OrchestratorChatResponse:
    """① TurnController로 대화 턴을 처리하고 레거시 ② 응답 형식으로 반환."""
    from .router import _build_llm_call
    from .session import AutonomousSession
    from .stage_run_sync import sync_stage_run_from_autonomous_session
    from .turn_controller import TurnController

    trimmed_message = str(message or "").strip()
    if not trimmed_message:
        raise ValueError("message가 필요합니다.")

    autonomous_mode = resolve_autonomous_mode(mode=mode, manual_mode=manual_mode)
    effective_run_id = str(run_id or "").strip()
    effective_stage_run_id = str(stage_run_id or "").strip() or (
        effective_run_id if effective_run_id.startswith("stage_run_") else ""
    )
    effective_session_id = str(session_id or "").strip() or None
    if not effective_session_id and effective_run_id and not effective_run_id.startswith("stage_run_"):
        effective_session_id = effective_run_id
    prior_conversation = _normalize_conversation(conversation)

    if effective_session_id:
        session = AutonomousSession.load(effective_session_id, owner_id)
        if not session:
            session = AutonomousSession.create(
                owner_id=owner_id,
                mode=autonomous_mode,
                project_name=project_name or task or "",
                validation_profile=validation_profile,
            )
    else:
        session = AutonomousSession.create(
            owner_id=owner_id,
            mode=autonomous_mode,
            project_name=project_name or task or "",
            validation_profile=validation_profile,
        )

    llm_call = None
    try:
        llm_call, model_routes = _build_llm_call()
        session.model_routes = model_routes
        session.extra["llm_connected"] = llm_call is not None
    except Exception as exc:
        logger.warning("Autonomous surface adapter LLM setup failed: %s", exc)
        session.extra["llm_connected"] = False

    controller = TurnController(llm_call=llm_call)
    autonomous_payload = await controller.process_turn(trimmed_message, session)

    if session.output_dir:
        autonomous_payload["output_dir"] = session.output_dir

    synced_stage_run = None
    if effective_stage_run_id:
        synced_stage_run = sync_stage_run_from_autonomous_session(
            stage_run_id=effective_stage_run_id,
            session=session,
        )

    response = _map_autonomous_to_chat_response(
        autonomous_payload=autonomous_payload,
        request_message=trimmed_message,
        prior_conversation=prior_conversation,
        surface=surface,
        run_id=run_id if not str(run_id or "").startswith("stage_run_") else None,
        task=task,
        context_tags=context_tags,
    )
    if synced_stage_run:
        response.diagnostics = {
            **dict(response.diagnostics or {}),
            "synced_stage_run": synced_stage_run,
            "stage_run_id": effective_stage_run_id,
        }
    return response


def _ensure_code_generation_message(task: str) -> str:
    task = str(task or "").strip()
    if not task:
        return "기본 프로그램을 만들어줘"
    lowered = task.lower()
    triggers = ("만들어", "생성", "구현", "개발", "빌드", "build", "create", "generate", "implement")
    if any(token in lowered for token in triggers):
        return task
    return f"{task}\n\n위 요청으로 실행 가능한 프로그램을 만들어줘"


def _collect_written_files(session: Any) -> List[str]:
    written: List[str] = []
    for result in getattr(session, "agent_results", []) or []:
        artifacts = getattr(result, "artifacts", None) or {}
        for item in artifacts.get("written_files") or []:
            path = str(item).strip()
            if path and path not in written:
                written.append(path)
    return written


def _map_session_to_orchestration_payload(
    *,
    session: Any,
    orchestration_request: Any,
    turn_payload: Dict[str, Any],
) -> Dict[str, Any]:
    task = str(getattr(orchestration_request, "task", "") or session.task or "").strip()
    mode = str(getattr(orchestration_request, "mode", "") or session.mode or "full_auto").strip()
    run_id = str(getattr(orchestration_request, "run_id", "") or session.session_id or "").strip() or None
    written_files = _collect_written_files(session)
    execution_state = str(getattr(session, "execution_state", "") or "idle")
    failed = execution_state == "failed"
    completed = execution_state == "completed"
    product_ready = completed and not failed and bool(session.output_dir)
    final_output = str(turn_payload.get("content") or "").strip() or (
        "멀티 자율 코어 코드 생성이 완료되었습니다." if product_ready else "멀티 자율 코어 코드 생성 결과"
    )
    stages_completed = int(turn_payload.get("stages_completed") or 0)
    stages_total = int(turn_payload.get("stages_total") or 0)
    agent_rows = [
        {
            "agent": getattr(item, "agent", ""),
            "status": getattr(item, "status", ""),
            "output": getattr(item, "output", ""),
            "elapsed_ms": getattr(item, "elapsed_ms", 0),
        }
        for item in (getattr(session, "agent_results", None) or [])
    ]

    return {
        "task": task,
        "mode": mode,
        "run_id": run_id,
        "pipeline": ["autonomous_turn_controller", "reasoner", "planner", "coder", "validator"],
        "results": agent_rows,
        "final_output": final_output,
        "applied": bool(session.output_dir),
        "output_dir": session.output_dir,
        "written_files": written_files,
        "postcheck_ran": stages_completed > 0,
        "postcheck_ok": completed and not failed,
        "completion_gate_ok": product_ready,
        "completion_summary": final_output if product_ready else None,
        "failure_summary": final_output if failed else None,
        "completion_judge": {
            "product_ready": product_ready,
            "failed_reasons": [] if product_ready else [final_output[:240] or execution_state],
            "orchestrator_core": "autonomous_turn_controller",
            "stages_completed": stages_completed,
            "stages_total": stages_total,
            "llm_connected": bool(turn_payload.get("llm_connected")),
        },
        "integration_test_plan": {
            "required_tests": ["autonomous_coder_validator_pipeline"],
        },
        "packaging_audit": {
            "packaging_ready": product_ready,
            "shipping_readme_path": None,
        },
        "diagnostics": {
            "orchestrator_core": "autonomous_turn_controller",
            "execution_state": execution_state,
            "approval_state": getattr(session, "approval_state", ""),
            "autonomous_session_id": session.session_id,
        },
    }


async def run_autonomous_surface_execution(
    orchestration_request: Any,
    *,
    owner_id: str,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """① TurnController full_auto — 마켓/관리자 /run stream SSOT."""
    from .router import _build_llm_call
    from .session import AutonomousSession
    from .turn_controller import TurnController

    task = str(getattr(orchestration_request, "task", "") or "").strip()
    if not task:
        raise ValueError("task가 필요합니다.")

    project_name = str(getattr(orchestration_request, "project_name", "") or "").strip() or "autonomous-project"
    session_id = str(getattr(orchestration_request, "run_id", "") or "").strip() or None
    validation_profile = str(getattr(orchestration_request, "validation_profile", "") or "python_fastapi")

    if session_id:
        session = AutonomousSession.load(session_id, owner_id)
        if not session:
            session = AutonomousSession.create(
                owner_id=owner_id,
                mode="full_auto",
                project_name=project_name,
                validation_profile=validation_profile,
            )
    else:
        session = AutonomousSession.create(
            owner_id=owner_id,
            mode="full_auto",
            project_name=project_name,
            validation_profile=validation_profile,
        )

    output_dir = str(getattr(orchestration_request, "output_dir", "") or "").strip()
    if output_dir:
        session.output_dir = output_dir

    llm_call = None
    try:
        llm_call, model_routes = _build_llm_call()
        session.model_routes = model_routes
        session.extra["llm_connected"] = llm_call is not None
    except Exception as exc:
        logger.warning("Autonomous surface execution LLM setup failed: %s", exc)
        session.extra["llm_connected"] = False

    if progress_callback:
        progress_callback("① 멀티 자율 코어 full_auto 생성 시작", "info")

    session.mode = "full_auto"
    session.task = task
    controller = TurnController(llm_call=llm_call)
    turn_payload = await controller.process_turn(_ensure_code_generation_message(task), session)

    if progress_callback:
        progress_callback(
            f"① 생성 상태: {session.execution_state} · STAGE {turn_payload.get('stages_completed', 0)}/{turn_payload.get('stages_total', 0)}",
            "info" if session.execution_state != "failed" else "error",
        )

    session.save()
    return _map_session_to_orchestration_payload(
        session=session,
        orchestration_request=orchestration_request,
        turn_payload=turn_payload,
    )


def orchestration_payload_to_response(payload: Dict[str, Any]) -> Any:
    """① 실행 dict → Admin `OrchestrationResponse` (POST /api/llm/orchestrate)."""
    from backend.llm.orchestrator import AgentResult, OrchestrationResponse

    results = [
        AgentResult(
            agent=str(item.get("agent") or ""),
            role=str(item.get("agent") or "autonomous"),
            model="autonomous",
            output=str(item.get("output") or ""),
        )
        for item in (payload.get("results") or [])
        if isinstance(item, dict)
    ]
    completion_judge = dict(payload.get("completion_judge") or {})
    completion_judge.setdefault("orchestrator_core", "autonomous_turn_controller")

    return OrchestrationResponse(
        task=str(payload.get("task") or ""),
        mode=str(payload.get("mode") or "full_auto"),
        run_id=payload.get("run_id"),
        pipeline=list(payload.get("pipeline") or ["autonomous_turn_controller"]),
        results=results,
        final_output=str(payload.get("final_output") or ""),
        applied=bool(payload.get("applied")),
        output_dir=payload.get("output_dir"),
        written_files=[str(path) for path in (payload.get("written_files") or []) if str(path).strip()],
        postcheck_ran=bool(payload.get("postcheck_ran")),
        postcheck_ok=bool(payload.get("postcheck_ok")),
        completion_gate_ok=bool(payload.get("completion_gate_ok")),
        completion_summary=payload.get("completion_summary"),
        failure_summary=payload.get("failure_summary"),
        completion_judge=completion_judge,
        integration_test_plan=dict(payload.get("integration_test_plan") or {}),
        packaging_audit=dict(payload.get("packaging_audit") or {}),
    )
