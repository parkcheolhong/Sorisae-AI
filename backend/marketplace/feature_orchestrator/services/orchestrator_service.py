"""
P1-2: Feature Orchestrator Service Layer

엔진 레지스트리를 기반으로 preview/final 파이프라인을 실행하고,
아티팩트 상태를 관리하는 서비스 계층입니다.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.marketplace.feature_orchestrator.engines import get_engine

logger = logging.getLogger(__name__)


class FeatureOrchestratorService:
    """Feature Orchestrator 비즈니스 로직."""

    async def execute_preview(
        self,
        feature_id: str,
        prompt: str,
        *,
        project_name: str = "",
        template: str = "",
        reference_image_path: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        preview 단계를 실행합니다.
        1. 엔진 레지스트리에서 feature_id에 해당하는 엔진 조회
        2. 엔진의 run_preview 호출
        3. 결과 아티팩트 반환
        """
        logger.info(
            "[FeatureOrchService] execute_preview: feature=%s project=%s",
            feature_id,
            project_name,
        )
        engine = get_engine(feature_id)
        kwargs: Dict[str, Any] = {
            "project_name": project_name,
            "template": template,
            "options": options,
        }
        if reference_image_path and hasattr(engine, "run_preview"):
            # 이미지 엔진만 reference_image_path 지원
            kwargs["reference_image_path"] = reference_image_path

        result = await engine.run_preview(prompt, **kwargs)
        result["feature_id"] = feature_id
        return result

    async def execute_final(
        self,
        feature_id: str,
        preview_artifact_id: str,
        *,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        final 단계를 실행합니다.
        1. preview 아티팩트 ID 검증
        2. 엔진의 run_final 호출
        3. 최종 아티팩트 반환
        """
        logger.info(
            "[FeatureOrchService] execute_final: feature=%s preview=%s",
            feature_id,
            preview_artifact_id,
        )
        engine = get_engine(feature_id)
        result = await engine.run_final(preview_artifact_id, options=options)
        result["feature_id"] = feature_id
        return result

    async def get_status(
        self,
        feature_id: str,
        artifact_id: str,
    ) -> Dict[str, Any]:
        """아티팩트 상태를 조회합니다."""
        # TODO: DB 또는 캐시에서 아티팩트 상태 조회
        return {
            "feature_id": feature_id,
            "artifact_id": artifact_id,
            "state": "completed",
        }
