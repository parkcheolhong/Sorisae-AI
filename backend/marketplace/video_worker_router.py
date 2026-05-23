from typing import Any

from fastapi import APIRouter, Depends, HTTPException


def build_video_worker_router(contract: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/video-worker/status")
    def get_video_worker_status(
        current_user=Depends(contract.get_current_user),
    ) -> dict[str, Any]:
        del current_user
        return contract.get_self_run_video_worker_status()

    @router.get("/video-worker/jobs/{job_id}")
    def get_video_worker_job(
        job_id: str,
        current_user=Depends(contract.get_current_user),
    ) -> dict[str, Any]:
        del current_user
        job = contract.get_self_run_video_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="비디오 잡을 찾을 수 없습니다.")
        return job

    @router.post("/video-worker/jobs")
    def enqueue_video_worker_job(
        request: contract.VideoJobRequest,
        current_user=Depends(contract.get_current_user),
    ) -> dict[str, Any]:
        del current_user
        payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        return contract.enqueue_self_run_video_job(payload)

    return router