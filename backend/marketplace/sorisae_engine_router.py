"""
소리새 엔진 마켓 라우터 (SorisaeEngineHub API)

마켓플레이스에서 소리새 AI 엔진 컨트롤 타워를 노출하는 FastAPI 라우터.
새 상품을 소리새 엔진 위에 올리려면:
  1. SORISAE_ENGINE_REGISTRY 에 엔진 타입을 추가하거나
  2. 런타임에 /api/marketplace/sorisae/register 로 등록합니다.

새 마켓 라우터 빌더에서 소리새 엔진 사용 규칙:
  ─────────────────────────────────────────────────────────────
  from backend.services.shinsegye.engine_hub import SorisaeEngineHub
  hub = SorisaeEngineHub.get_instance()
  result = hub.dispatch("decision", context={"query": "..."})
  ─────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field


# ── Request / Response 모델 ──────────────────────────────────────

class SorisaeDispatchRequest(BaseModel):
    engine_type: str = Field(..., description="소리새 엔진 타입 키 (예: 'decision')")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="엔진에 전달할 파라미터 딕셔너리"
    )
    entry_fn: str = Field(default="main", description="슬롯 내 호출 함수명")
    use_module_adapter: bool = Field(
        default=True,
        description="entry_fn 미존재 시 모듈 어댑터 후보 함수 자동 실행 여부",
    )
    adapter_entry_candidates: Optional[List[str]] = Field(
        default=None,
        description="모듈 어댑터 함수명 후보 목록 (예: ['run', 'execute'])",
    )


class SorisaeRegisterRequest(BaseModel):
    engine_type: str = Field(..., description="등록할 엔진 타입 키")
    slot_file: str = Field(
        ..., description="engines120/ 아래 슬롯 파일명 (예: slot121_my_product.py)"
    )


class TutorAnalyzeRequest(BaseModel):
    code: str = Field(..., description="분석할 코드 스니펫")
    language: str = Field(default="python", description="프로그래밍 언어 (python / typescript 등)")


def _input_validation_failure(
    *,
    engine_type: str,
    registered_engines: List[str],
) -> Dict[str, Any]:
    message = (
        f"등록되지 않은 엔진 타입: '{engine_type}'. "
        f"등록 목록: {registered_engines}"
    )
    return {
        "engine": engine_type,
        "status": "input_validation_error",
        "error": message,
        "error_code": "INPUT_ENGINE_TYPE_NOT_REGISTERED",
        "error_message": message,
        "retryable": False,
        "source": "router_validation",
        "result": None,
    }


# ── 라우터 빌더 ──────────────────────────────────────────────────

def build_sorisae_engine_router(contract: Any) -> APIRouter:
    """
    마켓플레이스 라우터에 소리새 엔진 API를 추가합니다.

    router.py 에서:
        from .sorisae_engine_router import build_sorisae_engine_router
        router.include_router(build_sorisae_engine_router(sys.modules[__name__]))
    """
    router = APIRouter(prefix="/sorisae", tags=["marketplace-sorisae-engine"])

    @router.get("/health")
    def sorisae_health(
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """소리새 컨트롤 타워 헬스 체크."""
        from backend.services.shinsegye.engine_hub import SorisaeEngineHub
        hub = SorisaeEngineHub.get_instance()
        return {
            "status": "ok",
            "registered_engines": len(hub.list_engines()),
            "engine_types": list(hub.list_engines().keys()),
        }

    @router.get("/engines")
    def sorisae_list_engines(
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """등록된 소리새 엔진 목록 반환."""
        from backend.services.shinsegye.engine_hub import SorisaeEngineHub
        hub = SorisaeEngineHub.get_instance()
        return {"engines": hub.list_engines()}

    @router.post("/dispatch")
    def sorisae_dispatch(
        payload: SorisaeDispatchRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """소리새 AI 엔진 슬롯 실행."""
        from backend.services.shinsegye.engine_hub import SorisaeEngineHub
        hub = SorisaeEngineHub.get_instance()

        if not hub.is_registered(payload.engine_type):
            registered = list(hub.list_engines().keys())
            raise HTTPException(
                status_code=400,
                detail=_input_validation_failure(
                    engine_type=payload.engine_type,
                    registered_engines=registered,
                ),
            )

        return hub.dispatch(
            engine_type=payload.engine_type,
            context=payload.context,
            entry_fn=payload.entry_fn,
            use_module_adapter=payload.use_module_adapter,
            adapter_entry_candidates=payload.adapter_entry_candidates,
        )

    @router.post("/register")
    def sorisae_register_engine(
        payload: SorisaeRegisterRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """
        런타임에 새 소리새 엔진 슬롯을 등록합니다.
        새 마켓 상품 배포 시 호출하세요.
        """
        from backend.services.shinsegye.engine_hub import SorisaeEngineHub
        hub = SorisaeEngineHub.get_instance()

        # 슬롯 파일명 기본 검증 (경로 순회 방지)
        slot_file = payload.slot_file.strip()
        if "/" in slot_file or "\\" in slot_file or ".." in slot_file:
            raise HTTPException(
                status_code=400,
                detail="slot_file 은 파일명만 허용됩니다 (경로 포함 불가).",
            )
        if not slot_file.endswith(".py"):
            raise HTTPException(
                status_code=400,
                detail="slot_file 은 .py 파일명이어야 합니다.",
            )

        hub.register_engine(payload.engine_type, slot_file)
        return {
            "status": "registered",
            "engine_type": payload.engine_type,
            "slot_file": slot_file,
        }

    # ── 소리새 AI 튜터 전용 엔드포인트 ────────────────────────────────

    @router.get("/tutor/profile")
    def sorisae_tutor_profile(
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """소리새 AI 튜터 사용자 학습 프로필 반환."""
        from backend.services.shinsegye.engines120.slot095_integrated_shopping_tutor_designer import PersonalAITutor
        tutor = PersonalAITutor()
        return {"profile": tutor.user_profile, "status": "ok"}

    @router.get("/tutor/path")
    def sorisae_tutor_path(
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """소리새 AI 튜터 학습 경로·도전 과제·격려 메시지 반환."""
        from backend.services.shinsegye.engines120.slot095_integrated_shopping_tutor_designer import PersonalAITutor
        tutor = PersonalAITutor()
        learning_path = tutor.suggest_learning_path()
        challenge = tutor.generate_personalized_challenge()
        encouragement = tutor.get_personalized_encouragement()
        return {
            "learning_path": learning_path,
            "challenge": challenge,
            "encouragement": encouragement,
            "skill_level": tutor.user_profile.get("skill_level", "beginner"),
            "session_count": tutor.user_profile.get("session_count", 0),
            "status": "ok",
        }

    @router.post("/tutor/analyze")
    def sorisae_tutor_analyze(
        req: TutorAnalyzeRequest,
        current_user=Depends(contract.get_current_user),
    ) -> Dict[str, Any]:
        """소리새 AI 튜터 코드 패턴 분석 및 맞춤 피드백 반환."""
        from backend.services.shinsegye.engines120.slot095_integrated_shopping_tutor_designer import PersonalAITutor
        code = req.code.strip()
        language = req.language.strip() or "python"
        if not code:
            return {"feedback": [], "language": language, "status": "empty_code"}
        tutor = PersonalAITutor()
        feedback = tutor.analyze_coding_pattern(code, language)
        return {"feedback": feedback, "language": language, "status": "ok"}

    return router
