"""멀티 에이전트 자율대화 API 엔드포인트"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/llm/autonomous", tags=["autonomous-orchestrator"])


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


class SessionStatusResponse(BaseModel):
    session_id: str
    mode: str
    execution_state: str
    approval_state: str
    stages: List[Dict[str, Any]] = []
    conversation_length: int = 0
    agent_result_count: int = 0


def _build_llm_call():
    from backend.orchestrator.chat.llm_client import call_orchestrator_chat_llm
    from backend.llm.model_config import get_configured_model_routes, build_ollama_options

    ollama_base = os.getenv("OLLAMA_BASE", "http://host.docker.internal:8008/v1").strip()
    timeout_sec = float(os.getenv("ORCHESTRATOR_CHAT_TIMEOUT_SEC", "120"))
    model_routes = get_configured_model_routes()

    async def llm_call(*, route_key: str, model: str, system_prompt: str, user_prompt: str) -> str:
        resolved_model = model or model_routes.get(route_key, model_routes.get("default", ""))
        return await call_orchestrator_chat_llm(
            route_key=route_key,
            model=resolved_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=4096,
            ollama_base=ollama_base,
            timeout_sec=timeout_sec,
            build_ollama_options=build_ollama_options,
        )

    return llm_call, model_routes


@router.post("/chat", response_model=AutonomousChatResponse)
async def autonomous_chat(
    request: AutonomousChatRequest,
    current_user=Depends(get_current_user),
) -> AutonomousChatResponse:
    """멀티 에이전트 자율대화 엔드포인트

    에이전트들이 협업하여 사용자의 요청을 처리합니다.
    - advisory 모드: 설계/분석만 (실행 없음)
    - semi_auto 모드: 사용자 승인 후 코드 생성
    - full_auto 모드: 자율 실행
    """
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
    except Exception:
        llm_call = None

    controller = TurnController(llm_call=llm_call)
    response_data = await controller.process_turn(request.message, session)

    return AutonomousChatResponse(**response_data)


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    current_user=Depends(get_current_user),
) -> SessionStatusResponse:
    """자율대화 세션 상태 조회"""
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
