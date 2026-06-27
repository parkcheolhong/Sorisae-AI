"""멀티 에이전트 자율대화 API 엔드포인트"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from backend.auth import get_current_user
from backend.security_gates import require_llm_mutation_quota

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/llm/autonomous", tags=["autonomous-orchestrator"])

_DEBUG_API_HEADERS = {
    "X-Orchestrator-Api-Tier": "debug-internal",
    "X-Orchestrator-Preferred-Endpoint": "/api/llm/orchestrate/chat",
}


def _apply_debug_api_headers(response: Response) -> None:
    for key, value in _DEBUG_API_HEADERS.items():
        response.headers[key] = value


class AutonomousChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: str = Field(default="semi_auto", description="advisory | semi_auto | full_auto")
    project_name: Optional[str] = None
    validation_profile: str = "python_fastapi"


class AutonomousChatResponse(BaseModel):
    session_id: str
    mode: str
    intent: str
    content: str
    execution_state: str
    approval_state: str
    current_stage: Optional[str] = None
    stages_completed: int = 0
    stages_total: int = 0
    agent_results: List[Dict[str, Any]] = []
    message_log: List[Dict[str, Any]] = []
    requires_approval: bool = False
    llm_connected: bool = False
    stages_remaining: int = 0


class SessionStatusResponse(BaseModel):
    session_id: str
    mode: str
    execution_state: str
    approval_state: str
    stages: List[Dict[str, Any]] = []
    conversation_length: int = 0
    agent_result_count: int = 0


def _resolve_model_routes_for_live_server(model_routes: Dict[str, str]) -> Dict[str, str]:
    from .llm_setup import resolve_model_routes_for_live_server
    return resolve_model_routes_for_live_server(model_routes)


def _build_llm_call():
    from .llm_setup import build_llm_call
    return build_llm_call()


@router.post("/chat", response_model=AutonomousChatResponse)
async def autonomous_chat(
    request: AutonomousChatRequest,
    response: Response,
    current_user=Depends(require_llm_mutation_quota),
) -> AutonomousChatResponse:
    """Raw TurnController HTTP — debug / regression scripts only.

    Product UI and admin workbench should call ``POST /api/llm/orchestrate/chat``.
    """
    _apply_debug_api_headers(response)
    from .turn_controller import TurnController
    from .session import AutonomousSession

    owner_id = str(getattr(current_user, "id", "unknown"))

    if request.session_id:
        session = AutonomousSession.load(request.session_id, owner_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    else:
        session = AutonomousSession.create(
            owner_id=owner_id,
            mode=request.mode,
            project_name=request.project_name or "",
            validation_profile=request.validation_profile,
        )

    try:
        llm_call, model_routes = _build_llm_call()
        session.model_routes = model_routes
    except Exception as exc:
        logger.warning("Autonomous orchestrator LLM call setup failed: %s", exc)
        llm_call = None

    controller = TurnController(llm_call=llm_call)
    response_data = await controller.process_turn(request.message, session)

    return AutonomousChatResponse(**response_data)


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    response: Response,
    current_user=Depends(get_current_user),
) -> SessionStatusResponse:
    """자율대화 세션 상태 조회 (debug-internal)."""
    _apply_debug_api_headers(response)
    from .session import AutonomousSession

    owner_id = str(getattr(current_user, "id", "unknown"))
    session = AutonomousSession.load(session_id, owner_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    return SessionStatusResponse(
        session_id=session.session_id,
        mode=session.mode,
        execution_state=session.execution_state,
        approval_state=session.approval_state,
        stages=[
            {"stage_id": s.stage_id, "label": s.stage_label, "status": s.status}
            for s in session.stages
        ],
        conversation_length=len(session.conversation),
        agent_result_count=len(session.agent_results),
    )
