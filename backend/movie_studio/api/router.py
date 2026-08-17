from __future__ import annotations

import json
import subprocess
import sys

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import get_current_user
from backend.movie_studio.api.schemas import (
    MovieStudioProjectRequest,
    MovieStudioProjectResponse,
)
router = APIRouter(prefix="/api/movie-studio", tags=["movie-studio"])


def _execute_movie_studio_project_subprocess(payload_data: dict) -> dict:
    script = (
        "import json\n"
        "import sys\n"
        "from backend.movie_studio.orchestration.studio_orchestrator import execute_movie_studio_project\n"
        "payload = json.loads(sys.stdin.read())\n"
        "result = execute_movie_studio_project(payload)\n"
        "print(json.dumps(result, ensure_ascii=False))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(payload_data, ensure_ascii=False),
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"movie studio subprocess 실행 실패: {stderr or 'unknown error'}",
        )
    stdout = (proc.stdout or "").strip()
    try:
        return json.loads(stdout)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="movie studio subprocess 결과 파싱 실패",
        ) from exc


@router.post("/projects", response_model=MovieStudioProjectResponse)
def create_movie_studio_project(
    payload: MovieStudioProjectRequest,
    current_user=Depends(get_current_user),
):
    del current_user
    try:
        return _execute_movie_studio_project_subprocess(payload.model_dump())
    except ModuleNotFoundError as exc:
        missing_name = str(getattr(exc, "name", "") or "runtime dependency")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"movie studio 런타임 의존성이 누락되었습니다: {missing_name}",
        ) from exc
