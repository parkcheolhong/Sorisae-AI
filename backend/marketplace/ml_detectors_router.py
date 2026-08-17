import asyncio
import json
import subprocess
import sys
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

# 프로브 엔드포인트 rate limiting
try:
    from backend.marketplace.probe_rate_limit import limiter as _probe_limiter, PROBE_RATE_LIMIT
    _RATE_LIMIT_AVAILABLE = True
except Exception:
    _probe_limiter = None  # type: ignore[assignment]
    PROBE_RATE_LIMIT = "30/minute"
    _RATE_LIMIT_AVAILABLE = False

# ML detector subprocess 작업 타임아웃(초)
_ML_RUN_TIMEOUT_S = 150  # subprocess 자체 timeout=120 + 여유 30s

_ML_STATUS_SCRIPT = """
import json, sys
try:
    import torch
    gpu_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else None
    device = "cuda" if gpu_available else "cpu"
    print(json.dumps({
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "device": device,
        "detectors": {
            "face_consistency": "face-consistency-detector-ml",
            "hand_anatomy": "hand-anatomy-detector-ml",
            "body_ratio": "body-ratio-detector-ml",
            "temporal_flicker": "temporal-flicker-detector-ml",
        },
        "model_source": "torchvision-pretrained",
    }))
except Exception as exc:
    print(json.dumps({"error": str(exc), "gpu_available": False, "gpu_name": None, "device": "unavailable", "detectors": {}, "model_source": "torchvision-pretrained"}))
"""

_ML_RUN_SCRIPT_TMPL = """
import json, sys
sys.argv = ['probe']
detector_type = {detector_type!r}
frame_paths = {frame_paths!r}
reference_paths = {reference_paths!r}
try:
    import os; os.environ.setdefault('PYTHONPATH', '/app')
    import sys; sys.path.insert(0, '/app')
    from backend.movie_studio.quality.ml_detector_runtime import (
        FaceEmbeddingDetectorRunner,
        HandLandmarkDetectorRunner,
        AnatomyPoseDetectorRunner,
        FlickerFlowDetectorRunner,
    )
    if detector_type == "face":
        runner = FaceEmbeddingDetectorRunner()
        result = runner.run(reference_paths=reference_paths, frame_paths=frame_paths)
    elif detector_type == "hand":
        runner = HandLandmarkDetectorRunner()
        result = runner.run(frame_paths=frame_paths)
    elif detector_type in ("anatomy", "body", "pose"):
        runner = AnatomyPoseDetectorRunner()
        result = runner.run(frame_paths=frame_paths)
    elif detector_type in ("flicker", "flow", "temporal"):
        runner = FlickerFlowDetectorRunner()
        result = runner.run(frame_paths=frame_paths)
    else:
        result = {{"error": f"지원되지 않는 검출기: {{detector_type}}"}}
    print(json.dumps(result))
except Exception as exc:
    print(json.dumps({{"error": str(exc)}}))
"""


def _probe_ml_status_subprocess() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _ML_STATUS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=30,
        )
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
        return {"error": proc.stderr or "no output", "gpu_available": False, "gpu_name": None, "device": "unavailable", "detectors": {}, "model_source": "torchvision-pretrained"}
    except Exception as exc:
        return {"error": str(exc), "gpu_available": False, "gpu_name": None, "device": "unavailable", "detectors": {}, "model_source": "torchvision-pretrained"}


def _run_ml_detector_subprocess(detector_type: str, frame_paths: list, reference_paths: list) -> dict[str, Any]:
    script = _ML_RUN_SCRIPT_TMPL.format(
        detector_type=detector_type,
        frame_paths=frame_paths,
        reference_paths=reference_paths,
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=120,
        )
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
        return {"error": proc.stderr or "no output"}
    except Exception as exc:
        return {"error": str(exc)}


def _noop_auth():
    return None


def build_ml_detectors_router(contract: Optional[Any] = None) -> APIRouter:
    router = APIRouter()
    _auth = contract.get_current_user if contract is not None else _noop_auth

    @router.get("/ml-detectors/status")
    @(_probe_limiter.limit(PROBE_RATE_LIMIT) if _RATE_LIMIT_AVAILABLE else lambda f: f)
    def ml_detectors_status(request: Request) -> dict[str, Any]:
        return _probe_ml_status_subprocess()

    @router.post("/ml-detectors/run")
    async def run_ml_detector(
        payload: dict[str, Any],
        current_user=Depends(_auth),
    ) -> dict[str, Any]:
        del current_user
        detector_type = str(payload.get("detector") or "face").strip().lower()
        frame_paths = list(payload.get("frame_paths") or [])
        reference_paths = list(payload.get("reference_paths") or [])
        if detector_type not in ("face", "hand", "anatomy", "body", "pose", "flicker", "flow", "temporal"):
            raise HTTPException(status_code=400, detail=f"지원되지 않는 검출기: {detector_type}")
        try:
            # asyncio.wait_for 로 스레드 고갈 방지: 최대 _ML_RUN_TIMEOUT_S 초
            result = await asyncio.wait_for(
                asyncio.to_thread(_run_ml_detector_subprocess, detector_type, frame_paths, reference_paths),
                timeout=_ML_RUN_TIMEOUT_S,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(status_code=504, detail=f"ML 검출기 타임아웃 ({_ML_RUN_TIMEOUT_S}s): {detector_type}") from exc
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result

    return router


# Module-level router for direct import in main.py
router = build_ml_detectors_router()