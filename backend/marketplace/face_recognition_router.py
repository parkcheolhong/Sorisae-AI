import asyncio
import json
import subprocess
import sys
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

# 프로브 엔드포인트 rate limiting: IP별 분당 30회 제한
try:
    from backend.marketplace.probe_rate_limit import limiter as _probe_limiter, PROBE_RATE_LIMIT
    _RATE_LIMIT_AVAILABLE = True
except Exception:
    _probe_limiter = None  # type: ignore[assignment]
    PROBE_RATE_LIMIT = "30/minute"
    _RATE_LIMIT_AVAILABLE = False

# face/ml subprocess 작업 타임아웃(초)
_FACE_PREVIEW_TIMEOUT_S = 90   # status 프로브용
_FACE_COMPARE_TIMEOUT_S = 150  # 비교 작업용 (subprocess 자체 timeout=120 + 여유 30s)


def _probe_face_runtime_subprocess() -> dict[str, Any]:
    probe_code = (
        "import json, torch\n"
        "from backend.movie_studio.quality.arcface_adapter import build_face_recognition_adapter\n"
        "_, adapter_status = build_face_recognition_adapter()\n"
        "gpu_available = bool(torch.cuda.is_available())\n"
        "device = 'cuda' if gpu_available else 'cpu'\n"
        "adapter_name = str(adapter_status.get('adapter_name') or adapter_status.get('embedding_backend') or '')\n"
        "adapter_available = bool(adapter_status.get('available'))\n"
        "payload = {\n"
        "  'available': adapter_available,\n"
        "  'adapter_name': adapter_name,\n"
        "  'device': str(adapter_status.get('device') or device),\n"
        "  'gpu_available': gpu_available,\n"
        "  'gpu_name': torch.cuda.get_device_name(0) if gpu_available else None,\n"
        "  'adapter': adapter_status,\n"
        "}\n"
        "print(json.dumps(payload))\n"
    )

    completed = subprocess.run(
        [sys.executable, "-c", probe_code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "subprocess probe failed").strip()
        raise RuntimeError(err)

    lines = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("empty subprocess probe output")
    return json.loads(lines[-1])


def _compare_face_runtime_subprocess(image_a: str, image_b: str) -> dict[str, Any]:
    compare_code = (
        "import json, sys, torch\n"
        "from pathlib import Path\n"
        "from backend.movie_studio.quality.arcface_adapter import build_face_recognition_adapter\n"
        "image_a, image_b = sys.argv[1], sys.argv[2]\n"
        "adapter, status = build_face_recognition_adapter()\n"
        "if not adapter.is_available():\n"
        "    raise RuntimeError(f\"얼굴 인식 어댑터 사용 불가: {status.get('reason')}\")\n"
        "embedding_a = adapter.embed(Path(image_a))\n"
        "embedding_b = adapter.embed(Path(image_b))\n"
        "similarity = torch.nn.functional.cosine_similarity(embedding_a, embedding_b).mean().item()\n"
        "payload = {\n"
        "  'similarity': round(similarity * 100.0, 2),\n"
        "  'adapter': status.get('adapter_name') or status.get('embedding_backend'),\n"
        "  'device': status.get('device'),\n"
        "}\n"
        "print(json.dumps(payload))\n"
    )

    completed = subprocess.run(
        [sys.executable, "-c", compare_code, image_a, image_b],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "subprocess compare failed").strip()
        raise RuntimeError(err)

    lines = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("empty subprocess compare output")
    return json.loads(lines[-1])


def _noop_auth():
    return None


def build_face_recognition_router(contract: Optional[Any] = None) -> APIRouter:
    router = APIRouter()
    _auth = contract.get_current_user if contract is not None else _noop_auth

    @router.get("/face-recognition/status")
    @(_probe_limiter.limit(PROBE_RATE_LIMIT) if _RATE_LIMIT_AVAILABLE else lambda f: f)
    def face_recognition_status(request: Request) -> dict[str, Any]:
        try:
            return _probe_face_runtime_subprocess()
        except Exception as exc:
            return {"error": str(exc), "gpu_available": False}

    @router.post("/face-recognition/compare")
    async def face_recognition_compare(
        payload: dict[str, Any],
        current_user=Depends(_auth),
    ) -> dict[str, Any]:
        del current_user
        image_a = str(payload.get("image_a") or "").strip()
        image_b = str(payload.get("image_b") or "").strip()
        if not image_a or not image_b:
            raise HTTPException(status_code=400, detail="image_a, image_b 경로 필수")
        try:
            # asyncio.wait_for 로 스레드 고갈 방지: 최대 _FACE_COMPARE_TIMEOUT_S 초
            result = await asyncio.wait_for(
                asyncio.to_thread(_compare_face_runtime_subprocess, image_a, image_b),
                timeout=_FACE_COMPARE_TIMEOUT_S,
            )
            return result
        except asyncio.TimeoutError as exc:
            raise HTTPException(status_code=504, detail=f"얼굴 비교 타임아웃 ({_FACE_COMPARE_TIMEOUT_S}s)") from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router


# Module-level router for direct import in main.py
router = build_face_recognition_router()