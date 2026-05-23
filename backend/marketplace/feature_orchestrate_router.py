import traceback
from typing import Any

from fastapi import APIRouter, HTTPException


def build_feature_orchestrate_router(contract: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/feature-catalog")
    def get_marketplace_feature_catalog() -> list[dict[str, Any]]:
        return contract._feature_runtime_service.get_catalog()

    @router.post(
        "/feature-orchestrate/accepted",
        response_model=contract.FeatureOrchestrateAcceptedResponse,
        status_code=contract.status.HTTP_202_ACCEPTED,
    )
    def accept_marketplace_feature_orchestration(
        request: contract.FeatureOrchestrateAcceptedRequest,
    ) -> contract.FeatureOrchestrateAcceptedResponse:
        request_payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        feature_id = str(request_payload.get("feature_id") or "").strip()
        service = contract._feature_runtime_service.get_service(feature_id)

        stage_run = contract.initialize_stage_run(
            scope="marketplace-feature-orchestrator",
            project_name=str(request_payload.get("project_name") or feature_id or "marketplace-feature-run"),
            mode="feature-popup",
            metadata={},
        )
        feature_metadata = {
            "feature_id": feature_id,
            "popup_state": "accepted",
            "request": request_payload,
            "artifact_manifest": {
                "preview_artifact_id": None,
                "final_artifact_id": None,
            },
            "last_event": None,
            "updated_at": contract._utc_now_iso(),
            "service": service.__class__.__name__,
        }
        stage_run = contract._set_feature_metadata(stage_run, feature_metadata)
        stage_run = contract._apply_feature_popup_state(stage_run, "accepted")
        stage_run = contract.save_stage_run(stage_run)
        return contract.FeatureOrchestrateAcceptedResponse(
            accepted=True,
            run_id=str(stage_run.get("run_id") or ""),
            stage_run=stage_run,
            status="accepted",
            stream_url="/api/marketplace/feature-orchestrate/stream",
            poll_url=f"/api/marketplace/feature-orchestrate/stage-runs/{stage_run.get('run_id')}",
        )

    @router.post("/feature-orchestrate/stream")
    async def stream_marketplace_feature_orchestration(
        request: contract.FeatureOrchestrateStreamRequest,
    ):
        stage_run = contract._get_feature_stage_run_or_404(request.run_id)
        feature_metadata = contract._get_feature_metadata(stage_run)
        feature_id = str(feature_metadata.get("feature_id") or "").strip()
        request_payload = dict(feature_metadata.get("request") or {})
        if not feature_id or not request_payload:
            raise HTTPException(status_code=400, detail="feature orchestrator 요청 메타데이터가 없습니다.")
        service = contract._feature_runtime_service.get_service(feature_id)

        async def event_stream():
            local_stage_run = contract._get_feature_stage_run_or_404(request.run_id)
            local_metadata = contract._get_feature_metadata(local_stage_run)

            def _persist_progress(*, percent: int, step: str, state: str, message: str) -> None:
                progress_payload = {
                    "percent": max(0, min(100, int(percent))),
                    "step": step,
                    "state": state,
                    "message": message,
                    "updated_at": contract._utc_now_iso(),
                }
                local_metadata["progress"] = progress_payload
                local_metadata["updated_at"] = progress_payload["updated_at"]

            try:
                local_metadata["popup_state"] = "preview_running"
                local_metadata["last_event"] = "preview_running"
                local_metadata["updated_at"] = contract._utc_now_iso()
                _persist_progress(percent=10, step="preview_started", state="preview_running", message="preview 생성 단계를 시작했습니다.")
                local_stage_run = contract._set_feature_metadata(local_stage_run, local_metadata)
                local_stage_run = contract._apply_feature_popup_state(local_stage_run, "preview_running")
                contract.save_stage_run(local_stage_run)
                yield contract._build_feature_sse_event("state", {"run_id": request.run_id, "state": "preview_running"})
                yield contract._build_feature_sse_event(
                    "progress",
                    contract._build_feature_progress_payload(
                        request.run_id,
                        percent=10,
                        step="preview_started",
                        state="preview_running",
                        message="preview 생성 단계를 시작했습니다.",
                    ),
                )

                preview_artifact = await contract.asyncio.wait_for(
                    contract.asyncio.to_thread(service.run_preview_phase, request_payload),
                    timeout=120,
                )
                local_metadata["popup_state"] = "preview_ready"
                local_metadata["preview_artifact"] = preview_artifact
                local_metadata["artifact_manifest"] = {
                    **dict(local_metadata.get("artifact_manifest") or {}),
                    "preview_artifact_id": preview_artifact.get("artifact_id"),
                }
                local_metadata["last_event"] = "preview_ready"
                local_metadata["updated_at"] = contract._utc_now_iso()
                _persist_progress(percent=45, step="preview_ready", state="preview_ready", message="preview 결과가 준비되었습니다.")
                local_stage_run = contract._set_feature_metadata(local_stage_run, local_metadata)
                local_stage_run = contract._apply_feature_popup_state(local_stage_run, "preview_ready")
                contract.save_stage_run(local_stage_run)
                yield contract._build_feature_sse_event("artifact", {"run_id": request.run_id, "state": "preview_ready", "artifact": preview_artifact})
                yield contract._build_feature_sse_event(
                    "progress",
                    contract._build_feature_progress_payload(
                        request.run_id,
                        percent=45,
                        step="preview_ready",
                        state="preview_ready",
                        message="preview 결과가 준비되었습니다.",
                    ),
                )

                if not bool(request_payload.get("final_enabled", True)):
                    # preview-only path: skip final render and quality gate entirely
                    manifest = service.build_artifact_manifest(preview_artifact, None, None)
                    local_metadata["popup_state"] = "completed_preview_only"
                    local_metadata["artifact_manifest"] = manifest
                    local_metadata["last_event"] = "completed_preview_only"
                    local_metadata["updated_at"] = contract._utc_now_iso()
                    _persist_progress(percent=100, step="completed_preview_only", state="completed_preview_only", message="preview 전용 라이브뷰 실행이 완료되었습니다.")
                    local_stage_run = contract._set_feature_metadata(local_stage_run, local_metadata)
                    local_stage_run = contract._apply_feature_popup_state(local_stage_run, "completed_preview_only")
                    contract.save_stage_run(local_stage_run)
                    yield contract._build_feature_sse_event("completed", {"run_id": request.run_id, "state": "completed_preview_only", "artifact_manifest": manifest, "quality_review": None})
                    yield contract._build_feature_sse_event(
                        "progress",
                        contract._build_feature_progress_payload(
                            request.run_id,
                            percent=100,
                            step="completed_preview_only",
                            state="completed_preview_only",
                            message="preview 전용 라이브뷰 실행이 완료되었습니다.",
                        ),
                    )
                    return

                local_metadata["popup_state"] = "final_running"
                local_metadata["last_event"] = "final_running"
                local_metadata["updated_at"] = contract._utc_now_iso()
                _persist_progress(percent=65, step="final_started", state="final_running", message="final 렌더 단계를 시작했습니다.")
                local_stage_run = contract._set_feature_metadata(local_stage_run, local_metadata)
                local_stage_run = contract._apply_feature_popup_state(local_stage_run, "final_running")
                contract.save_stage_run(local_stage_run)
                yield contract._build_feature_sse_event("state", {"run_id": request.run_id, "state": "final_running"})
                yield contract._build_feature_sse_event(
                    "progress",
                    contract._build_feature_progress_payload(
                        request.run_id,
                        percent=65,
                        step="final_started",
                        state="final_running",
                        message="final 렌더 단계를 시작했습니다.",
                    ),
                )

                final_artifact = await contract.asyncio.wait_for(
                    contract.asyncio.to_thread(service.run_final_phase, request_payload, preview_artifact),
                    timeout=300,
                )
                quality_review = await contract.asyncio.wait_for(
                    contract.asyncio.to_thread(service.run_quality_gate, request_payload, preview_artifact, final_artifact),
                    timeout=60,
                )
                manifest = service.build_artifact_manifest(preview_artifact, final_artifact, quality_review)
                completed_state = "completed" if bool(quality_review.get("passed")) else "completed_preview_only"

                local_metadata["popup_state"] = "quality_review"
                local_metadata["quality_review"] = quality_review
                local_metadata["updated_at"] = contract._utc_now_iso()
                _persist_progress(percent=85, step="quality_review", state="quality_review", message="quality gate 결과를 정리하고 있습니다.")
                local_stage_run = contract._set_feature_metadata(local_stage_run, local_metadata)
                local_stage_run = contract._apply_feature_popup_state(local_stage_run, "quality_review")
                contract.save_stage_run(local_stage_run)
                yield contract._build_feature_sse_event("quality_review", {"run_id": request.run_id, "state": "quality_review", "quality_review": quality_review})
                yield contract._build_feature_sse_event(
                    "progress",
                    contract._build_feature_progress_payload(
                        request.run_id,
                        percent=85,
                        step="quality_review",
                        state="quality_review",
                        message="quality gate 결과를 정리하고 있습니다.",
                    ),
                )

                local_metadata["popup_state"] = completed_state
                local_metadata["final_artifact"] = final_artifact
                local_metadata["artifact_manifest"] = manifest
                local_metadata["last_event"] = completed_state
                local_metadata["updated_at"] = contract._utc_now_iso()
                _persist_progress(percent=100, step="completed", state=completed_state, message="라이브뷰 실행이 완료되었습니다.")
                local_stage_run = contract._set_feature_metadata(local_stage_run, local_metadata)
                local_stage_run = contract._apply_feature_popup_state(local_stage_run, completed_state)
                contract.save_stage_run(local_stage_run)
                yield contract._build_feature_sse_event("completed", {"run_id": request.run_id, "state": completed_state, "artifact_manifest": manifest, "quality_review": quality_review})
                yield contract._build_feature_sse_event(
                    "progress",
                    contract._build_feature_progress_payload(
                        request.run_id,
                        percent=100,
                        step="completed",
                        state=completed_state,
                        message="라이브뷰 실행이 완료되었습니다.",
                    ),
                )
            except Exception as exc:
                error_code = type(exc).__name__
                failure_tag = f"feature-orchestrate/{feature_id}/{error_code}"
                stage_id = str(local_stage_run.get("run_id") or request.run_id)
                tb_summary = traceback.format_exc()[-500:]
                local_metadata["popup_state"] = "failed"
                local_metadata["last_event"] = "failed"
                local_metadata["error"] = str(exc)
                local_metadata["failure_tag"] = failure_tag
                local_metadata["error_code"] = error_code
                local_metadata["updated_at"] = contract._utc_now_iso()
                _persist_progress(percent=100, step="failed", state="failed", message=str(exc))
                local_stage_run = contract._set_feature_metadata(local_stage_run, local_metadata)
                local_stage_run = contract._apply_feature_popup_state(local_stage_run, "failed", str(exc))
                contract.save_stage_run(local_stage_run)
                yield contract._build_feature_sse_event("failed", {
                    "run_id": request.run_id,
                    "state": "failed",
                    "message": str(exc),
                    "failure_tag": failure_tag,
                    "stage_id": stage_id,
                    "error_code": error_code,
                    "traceback_summary": tb_summary,
                })
                yield contract._build_feature_sse_event(
                    "progress",
                    contract._build_feature_progress_payload(
                        request.run_id,
                        percent=100,
                        step="failed",
                        state="failed",
                        message=str(exc),
                    ),
                )
            finally:
                # 제너레이터가 비정상 종료(예: 클라이언트 연결 끊김)되어도 상태 보장
                _terminal_states = ("completed", "completed_preview_only", "failed")
                if local_metadata.get("popup_state") not in _terminal_states:
                    local_metadata["popup_state"] = "failed"
                    local_metadata["last_event"] = "abandoned"
                    local_metadata["error"] = "stream abandoned"
                    local_metadata["failure_tag"] = f"feature-orchestrate/{feature_id}/StreamAbandoned"
                    local_metadata["updated_at"] = contract._utc_now_iso()
                    try:
                        local_stage_run = contract._set_feature_metadata(local_stage_run, local_metadata)
                        contract.save_stage_run(local_stage_run)
                    except Exception:
                        pass  # best-effort: 저장 실패 시 무시

        return contract.StreamingResponse(event_stream(), media_type="text/event-stream")

    @router.get("/feature-orchestrate/stage-runs/{run_id}")
    def get_marketplace_feature_stage_run(run_id: str) -> dict[str, Any]:
        return contract._get_feature_stage_run_or_404(run_id)

    return router