"""
router.py - /api/v1/image endpoints
"""
from __future__ import annotations
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from backend.security_gates import require_image_mutation_quota

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/image", tags=["Image Generation"])


class GenerateRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        json_schema_extra={
            "example": "A futuristic city at night, cyberpunk style"
        },
    )
    negative_prompt: str = Field(
        default="",
        max_length=500,
        json_schema_extra={"example": "blurry, low quality"},
    )
    width: int = Field(default=1024, ge=256, le=2048, multiple_of=8)
    height: int = Field(default=1024, ge=256, le=2048, multiple_of=8)
    steps: int = Field(default=4, ge=1, le=50)
    guidance_scale: float = Field(default=0.0, ge=0.0, le=20.0)
    seed: Optional[int] = Field(default=None, ge=0)
    model: str = Field(
        default="sdxl-turbo",
        json_schema_extra={"example": "sdxl-turbo"},
    )


class GenerateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    image_base64: str
    seed: int
    generation_time: float
    model_used: str
    width: int
    height: int


class StylizeReferenceRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    source_image_base64: str = Field(default="")
    source_image_path: str = Field(default="")
    negative_prompt: str = Field(default="", max_length=500)
    width: int = Field(default=1024, ge=256, le=2048, multiple_of=8)
    height: int = Field(default=1024, ge=256, le=2048, multiple_of=8)
    steps: int = Field(default=20, ge=1, le=50)
    guidance_scale: float = Field(default=5.5, ge=0.0, le=20.0)
    strength: float = Field(default=0.45, ge=0.05, le=0.9)
    seed: Optional[int] = Field(default=None, ge=0)
    model: str = Field(default="sdxl")


class KeyframeItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    index: int
    scene_prompt: str
    image_base64: str
    seed: int
    model_used: str


class GenerateKeyframesRequest(BaseModel):
    scenes: list[str] = Field(..., min_length=1, max_length=24)
    base_prompt: str = Field(..., min_length=1, max_length=1000)
    source_image_base64: str = Field(default="")
    source_image_path: str = Field(default="")
    negative_prompt: str = Field(default="", max_length=500)
    width: int = Field(default=1024, ge=256, le=2048, multiple_of=8)
    height: int = Field(default=1024, ge=256, le=2048, multiple_of=8)
    steps: int = Field(default=20, ge=1, le=50)
    guidance_scale: float = Field(default=5.5, ge=0.0, le=20.0)
    strength: float = Field(default=0.42, ge=0.05, le=0.9)
    seed: Optional[int] = Field(default=None, ge=0)
    model: str = Field(default="sdxl")


class GenerateKeyframesResponse(BaseModel):
    items: list[KeyframeItem]
    width: int
    height: int


@router.get("/status")
async def image_status():
    """GPU status and loaded model check."""
    try:
        from backend.image.generator import check_gpu_status
        return {"status": "ok", "gpu": check_gpu_status()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/models")
async def list_models():
    """List supported models."""
    from backend.image.generator import SUPPORTED_MODELS, DEFAULT_MODEL
    return {
        "models": list(SUPPORTED_MODELS.keys()),
        "default": DEFAULT_MODEL,
        "descriptions": {
            "sdxl-turbo":   "Fastest (1-4 steps), near real-time",
            "sdxl":         "High-quality SDXL 1.0, 20-30 steps",
            "sd15":         "Lightweight SD 1.5, lower VRAM",
            "flux-schnell": "Best quality FLUX.1, requires 32 GB VRAM",
        },
    }


@router.post("/generate", response_model=GenerateResponse)
async def generate_image_endpoint(
    req: GenerateRequest,
    current_user=Depends(require_image_mutation_quota),
):
    """
    Generate an image with Stable Diffusion.

    - **model**: sdxl-turbo | sdxl | sd15 | flux-schnell
    - **steps**: SDXL-Turbo produces good results with just 1-4 steps
    """
    try:
        from backend.image.generator import generate_image
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=str(e))
    try:
        result = await asyncio.to_thread(
            generate_image,
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
            width=req.width,
            height=req.height,
            steps=req.steps,
            guidance_scale=req.guidance_scale,
            seed=req.seed,
            model_key=req.model,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Image generation failed")
        raise HTTPException(status_code=500, detail=f"Generation error: {e}")

    return GenerateResponse(
        image_base64=result["image_base64"],
        seed=result["seed"],
        generation_time=result["generation_time"],
        model_used=result["model_used"],
        width=req.width, height=req.height,
    )


@router.post("/stylize-reference", response_model=GenerateResponse)
async def stylize_reference_endpoint(
    req: StylizeReferenceRequest,
    current_user=Depends(require_image_mutation_quota),
):
    try:
        from backend.image.generator import stylize_reference_image
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=str(e))

    if not (req.source_image_base64 or req.source_image_path):
        raise HTTPException(
            status_code=400,
            detail="source_image_base64 or source_image_path is required",
        )

    try:
        result = await asyncio.to_thread(
            stylize_reference_image,
            prompt=req.prompt,
            source_image_base64=req.source_image_base64,
            source_image_path=req.source_image_path,
            negative_prompt=req.negative_prompt,
            width=req.width,
            height=req.height,
            steps=req.steps,
            guidance_scale=req.guidance_scale,
            strength=req.strength,
            seed=req.seed,
            model_key=req.model,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Reference stylization failed")
        raise HTTPException(status_code=500, detail=f"Stylize error: {e}")

    return GenerateResponse(
        image_base64=result["image_base64"],
        seed=result["seed"],
        generation_time=result["generation_time"],
        model_used=result["model_used"],
        width=req.width, height=req.height,
    )


@router.post("/generate-keyframes", response_model=GenerateKeyframesResponse)
async def generate_keyframes_endpoint(
    req: GenerateKeyframesRequest,
    current_user=Depends(require_image_mutation_quota),
):
    try:
        from backend.image.generator import stylize_reference_image
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=str(e))

    if not (req.source_image_base64 or req.source_image_path):
        raise HTTPException(
            status_code=400,
            detail="source_image_base64 or source_image_path is required",
        )

    items: list[KeyframeItem] = []
    seed_base = req.seed if req.seed is not None else None
    for index, scene in enumerate(req.scenes):
        scene_prompt = scene.strip()
        if not scene_prompt:
            continue
        prompt = f"{req.base_prompt.strip()}, {scene_prompt}"
        try:
            result = await asyncio.to_thread(
                stylize_reference_image,
                prompt=prompt,
                source_image_base64=req.source_image_base64,
                source_image_path=req.source_image_path,
                negative_prompt=req.negative_prompt,
                width=req.width,
                height=req.height,
                steps=req.steps,
                guidance_scale=req.guidance_scale,
                strength=req.strength,
                seed=(seed_base + index) if seed_base is not None else None,
                model_key=req.model,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            logger.exception("Keyframe generation failed for scene %s", index)
            raise HTTPException(
                status_code=500,
                detail=f"Keyframe generation error: {e}",
            )

        items.append(KeyframeItem(
            index=index,
            scene_prompt=scene_prompt,
            image_base64=result["image_base64"],
            seed=result["seed"],
            model_used=result["model_used"],
        ))

    return GenerateKeyframesResponse(
        items=items,
        width=req.width,
        height=req.height,
    )
