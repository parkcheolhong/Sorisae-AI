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


def should_route_orchestrator_chat_to_autonomous(
    request: Any,
    request_context: Any,
) -> bool:
    """Admin/Market `orchestrate/chat` → ① TurnController 분기 (G-1-1).

    Legacy ② fallback: lightweight · reverse_question · tone-selection 흐름.
    """
    from backend.orchestrator.chat.chat_service import is_lightweight_chat_request

    if is_lightweight_chat_request(request, request_context):
        return False

    conversation_mode = str(getattr(request, "conversation_mode", None) or "auto").strip().lower()
    if conversation_mode in {"reverse_question", "reciprocal", "interview"}:
        return False

    mode = str(getattr(request, "mode", None) or "").strip().lower()
    manual_mode = bool(getattr(request, "manual_mode", True))
    if manual_mode or mode.startswith("manual_") or mode in {
        "semi_auto",
        "full_auto",
        "full",
        "advisory",
        "advise",
        "analysis",
        "research_only",
    }:
        return True

    return False


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
    tags = [str(item).strip() for item in (context_tags or []) if str(item).strip()]
    voice_entry = "voice-entry" in tags or "voice-stt" in tags
    user_speaker = speakers["user_voice"] if voice_entry else speakers["user"]
    user_message = ConversationMessage(
        role="user",
        content=request_message,
        speaker=user_speaker,
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
        "requires_approval": requires_approval,
        "execution_state": autonomous_payload.get("execution_state"),
        "approval_state": autonomous_payload.get("approval_state"),
        "current_stage": autonomous_payload.get("current_stage"),
        "context_tags": tags,
        "command_rules": autonomous_payload.get("command_rules") or [],
        "command_modes": autonomous_payload.get("command_modes") or [],
        "discuss_locked": bool(autonomous_payload.get("discuss_locked")),
    }
    if voice_entry:
        diagnostics["voice_entry"] = True
        diagnostics["voice_speaker"] = speakers["user_voice"]
        diagnostics["voice_context_tags"] = [tag for tag in tags if tag.startswith("voice-")]

    proposal_items = autonomous_payload.get("proposal_items") or []
    technology_recommendations = autonomous_payload.get("technology_recommendations") or []
    new_technology_candidates = autonomous_payload.get("new_technology_candidates") or []
    clarification_questions = autonomous_payload.get("clarification_questions") or []
    evidence_highlights = autonomous_payload.get("evidence_highlights") or []
    web_results = autonomous_payload.get("web_results") or []
    web_grounding_used = bool(autonomous_payload.get("web_grounding_used"))

    from backend.orchestrator.chat.models import (
        AdvisoryEvidenceItem,
        AdvisoryQuestion,
        ProposalItem,
        TechnologyRecommendation,
        WebGroundingItem,
    )

    def _proposal_items():
        items = []
        for raw in proposal_items:
            if isinstance(raw, dict):
                items.append(ProposalItem(**raw))
        return items

    def _technology_recommendations():
        items = []
        for raw in technology_recommendations:
            if isinstance(raw, dict):
                items.append(TechnologyRecommendation(**raw))
        return items

    def _clarification_questions():
        items = []
        for raw in clarification_questions:
            if isinstance(raw, dict):
                items.append(AdvisoryQuestion(**raw))
        return items

    def _evidence_highlights():
        items = []
        for raw in evidence_highlights:
            if isinstance(raw, dict):
                items.append(AdvisoryEvidenceItem(**raw))
        return items

    def _web_results():
        items = []
        for raw in web_results:
            if isinstance(raw, dict):
                items.append(WebGroundingItem(**raw))
        return items

    return OrchestratorChatResponse(
        reply=assistant_message,
        conversation=merged_conversation,
        output_dir=autonomous_payload.get("output_dir"),
        run_id=run_id,
        session_id=str(autonomous_payload.get("session_id") or ""),
        grounding_mode="web" if web_grounding_used else "internal",
        grounding_note=(
            "웹 검색 근거를 포함한 ① discuss advisory"
            if web_grounding_used
            else "멀티 에이전트 자율 오케스트레이터(①) 코어"
        ),
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
        proposal_items=_proposal_items(),
        technology_recommendations=_technology_recommendations(),
        new_technology_candidates=[str(item) for item in new_technology_candidates if str(item).strip()],
        clarification_questions=_clarification_questions(),
        evidence_highlights=_evidence_highlights(),
        web_results=_web_results(),
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

    session.extra["surface"] = surface
    if effective_stage_run_id:
        session.extra["stage_run_id"] = effective_stage_run_id
    if effective_run_id:
        session.extra["progress_run_id"] = effective_run_id
    elif effective_session_id:
        session.extra["progress_run_id"] = effective_session_id
    else:
        session.extra["progress_run_id"] = session.session_id

    controller = TurnController(llm_call=llm_call)
    autonomous_payload = await controller.process_turn(trimmed_message, session)

    from .progress_tracker import persist_autonomous_progress

    persist_autonomous_progress(
        session,
        run_id=effective_run_id,
        stage_run_id=effective_stage_run_id,
        event_message=f"chat · {autonomous_payload.get('intent') or 'turn'}",
    )

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

    if int(autonomous_payload.get("stages_completed") or 0) > 0 and session.output_dir:
        from .runnable_proof import evaluate_runnable_proof

        runnable_proof = evaluate_runnable_proof(
            output_dir=session.output_dir,
            written_files=_collect_written_files(session),
            validation_profile=str(session.validation_profile or validation_profile),
            agent_results=session.agent_results,
        )
        response.diagnostics = {
            **dict(response.diagnostics or {}),
            "runnable_proof": runnable_proof,
            "product_ready_hint": bool(runnable_proof.get("ok")),
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


def _build_completion_judge(
    *,
    session: Any,
    turn_payload: Dict[str, Any],
    written_files: List[str],
) -> Dict[str, Any]:
    from .runnable_proof import evaluate_runnable_proof
    from .run_experience import append_autonomous_run_snapshot

    execution_state = str(getattr(session, "execution_state", "") or "idle")
    failed = execution_state == "failed"
    completed = execution_state == "completed"
    stages_completed = int(turn_payload.get("stages_completed") or 0)
    validation_profile = str(getattr(session, "validation_profile", "") or "python_fastapi")

    runnable_proof = evaluate_runnable_proof(
        output_dir=getattr(session, "output_dir", None),
        written_files=written_files,
        validation_profile=validation_profile,
        agent_results=getattr(session, "agent_results", None),
    )
    structural_ready = completed and not failed and bool(getattr(session, "output_dir", None))
    product_ready = bool(structural_ready and runnable_proof.get("ok"))

    if structural_ready and stages_completed > 0:
        append_autonomous_run_snapshot(
            session_id=str(getattr(session, "session_id", "") or ""),
            surface=str((getattr(session, "extra", None) or {}).get("surface") or "autonomous"),
            execution_state=execution_state,
            stages_completed=stages_completed,
            runnable_proof=runnable_proof,
            task=str(getattr(session, "task", "") or turn_payload.get("content") or ""),
        )

    final_output = str(turn_payload.get("content") or "").strip()
    if product_ready:
        final_hint = runnable_proof.get("detail") or "runnable proof OK"
        final_output = final_output or f"멀티 자율 코어 코드 생성 완료 — {final_hint}"
    elif structural_ready:
        final_output = final_output or (
            f"구조는 완료됐으나 runnable proof 미충족: {runnable_proof.get('detail') or '검증 필요'}"
        )
    else:
        final_output = final_output or "멀티 자율 코어 코드 생성 결과"

    return {
        "product_ready": product_ready,
        "structural_ready": structural_ready,
        "failed_reasons": [] if product_ready else [final_output[:240] or execution_state],
        "orchestrator_core": "autonomous_turn_controller",
        "stages_completed": stages_completed,
        "stages_total": int(turn_payload.get("stages_total") or 0),
        "llm_connected": bool(turn_payload.get("llm_connected")),
        "runnable_proof": runnable_proof,
        "completion_model": "structural_plus_runnable_proof",
    }


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
    completion_judge = _build_completion_judge(
        session=session,
        turn_payload=turn_payload,
        written_files=written_files,
    )
    product_ready = bool(completion_judge.get("product_ready"))
    final_output = str(turn_payload.get("content") or "").strip() or (
        str(completion_judge.get("failed_reasons") or ["멀티 자율 코어 코드 생성 결과"])[0]
        if isinstance(completion_judge.get("failed_reasons"), list) and completion_judge.get("failed_reasons")
        else "멀티 자율 코어 코드 생성 결과"
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
        "failure_summary": final_output if failed or (completed and not product_ready) else None,
        "completion_judge": completion_judge,
        "integration_test_plan": {
            "required_tests": ["autonomous_coder_validator_pipeline", "runnable_proof"],
            "runnable_proof": completion_judge.get("runnable_proof"),
        },
        "packaging_audit": {
            "packaging_ready": product_ready,
            "shipping_readme_path": None,
            "runnable_proof_ok": bool((completion_judge.get("runnable_proof") or {}).get("ok")),
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

    session.extra["surface"] = "execution"

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
