"""
generator.py - Stable Diffusion pipeline (RTX 5090 / CUDA 12.6+ optimised)

Fix history:
  v2 - Use StableDiffusionXLPipeline directly instead of AutoPipelineForText2Image
       to avoid HunyuanDiT import chain that requires MT5Tokenizer (removed in
       transformers >= 5.0).  Compatible with transformers 5.x + diffusers 0.36.
"""
import os, time, io, base64, logging
from typing import Optional

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

_pipeline       = None
_current_model_id: str = ""
_img2img_pipeline = None
_current_img2img_model_id: str = ""
_current_device: str = ""
_current_img2img_device: str = ""

SUPPORTED_MODELS = {
    "sdxl-turbo":   "stabilityai/sdxl-turbo",
    "sdxl":         "stabilityai/stable-diffusion-xl-base-1.0",
    "sd15":         "runwayml/stable-diffusion-v1-5",
    "flux-schnell": "black-forest-labs/FLUX.1-schnell",
}
DEFAULT_MODEL = os.getenv("SD_MODEL", "sdxl-turbo")


def _nano_detail_enabled() -> bool:
    return (os.getenv("IMAGE_GENERATOR_NANO_DETAIL", "1") or "1").strip().lower() not in {"0", "false", "off", "no"}


def _merge_negative_prompt(negative_prompt: str) -> str:
    base_terms = [term.strip() for term in str(negative_prompt or "").split(",") if term.strip()]
    nano_terms = [
        "coarse grain",
        "heavy film grain",
        "sensor noise",
        "chroma noise",
        "pixel noise",
        "mosquito noise",
        "blotchy texture",
        "oversharpened halos",
        "macro texture clumps",
    ]
    merged: list[str] = []
    for term in base_terms + nano_terms:
        lowered = term.lower()
        if lowered not in {item.lower() for item in merged}:
            merged.append(term)
    return ", ".join(merged)


def _apply_nano_detail_finish(image: Image.Image) -> Image.Image:
    if not _nano_detail_enabled():
        return image.convert("RGB")

    refined = image.convert("RGB")
    refined = refined.filter(ImageFilter.MedianFilter(size=3))
    refined = refined.filter(ImageFilter.GaussianBlur(radius=0.18))
    refined = refined.filter(ImageFilter.UnsharpMask(radius=1.1, percent=120, threshold=2))
    refined = ImageEnhance.Contrast(refined).enhance(1.015)
    refined = ImageEnhance.Sharpness(refined).enhance(1.04)
    return refined


def _resolve_torch_device() -> str:
    import torch

    preferred = (os.getenv("IMAGE_GENERATOR_DEVICE", "") or "").strip().lower()
    if preferred in {"cpu", "cuda"}:
        if preferred == "cuda" and not torch.cuda.is_available():
            logger.warning("IMAGE_GENERATOR_DEVICE=cuda but CUDA is unavailable. Falling back to CPU.")
            return "cpu"
        return preferred
    return "cuda" if torch.cuda.is_available() else "cpu"


# ── pipeline factory ──────────────────────────────────────────────────────────
def _build_pipe(model_key: str, model_id: str):
    """Return the correct pipeline class for a given model key."""
    import torch

    device = _resolve_torch_device()
    dtype = torch.float16 if device == "cuda" else torch.float32

    if "flux" in model_key.lower():
        from diffusers.pipelines.flux.pipeline_flux import FluxPipeline
        return FluxPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        )

    if model_key in ("sdxl-turbo", "sdxl"):
        from diffusers.pipelines.stable_diffusion_xl.pipeline_stable_diffusion_xl import (
            StableDiffusionXLPipeline,
        )
        kwargs = {
            "torch_dtype": dtype,
            "use_safetensors": True,
        }
        if device == "cuda":
            kwargs["variant"] = "fp16"
        return StableDiffusionXLPipeline.from_pretrained(model_id, **kwargs)

    # sd15 or anything else
    from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import (
        StableDiffusionPipeline,
    )
    return StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=dtype,
        use_safetensors=True,
    )


def _build_img2img_pipe(model_key: str, model_id: str):
    import torch

    device = _resolve_torch_device()
    dtype = torch.float16 if device == "cuda" else torch.float32

    if "flux" in model_key.lower():
        raise RuntimeError("flux-schnell does not support img2img in this backend yet")

    if model_key in ("sdxl-turbo", "sdxl"):
        from diffusers.pipelines.stable_diffusion_xl.pipeline_stable_diffusion_xl_img2img import (
            StableDiffusionXLImg2ImgPipeline,
        )
        kwargs = {
            "torch_dtype": dtype,
            "use_safetensors": True,
        }
        if device == "cuda":
            kwargs["variant"] = "fp16"
        return StableDiffusionXLImg2ImgPipeline.from_pretrained(model_id, **kwargs)

    from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_img2img import (
        StableDiffusionImg2ImgPipeline,
    )
    return StableDiffusionImg2ImgPipeline.from_pretrained(
        model_id,
        torch_dtype=dtype,
        use_safetensors=True,
    )


def _load_pipeline(model_key: str):
    global _pipeline, _current_model_id, _current_device

    device = _resolve_torch_device()

    if _pipeline is not None and _current_model_id == model_key and _current_device == device:
        return _pipeline

    try:
        model_id = SUPPORTED_MODELS.get(model_key, SUPPORTED_MODELS[DEFAULT_MODEL])
        logger.info(f"Loading model: {model_id}  (key={model_key}, device={device})")

        pipe = _build_pipe(model_key, model_id)
        pipe = pipe.to(device)

        # optional VRAM optimisations
        if device == "cuda":
            try:
                pipe.enable_xformers_memory_efficient_attention()
                logger.info("xformers memory-efficient attention enabled.")
            except Exception as _e:
                logger.debug(f"xformers not available: {_e}")

        _pipeline        = pipe
        _current_model_id = model_key
        _current_device = device
        logger.info(f"Model {model_key} loaded on {device}.")
        return _pipeline

    except ImportError as e:
        raise RuntimeError(
            f"Required packages missing: {e}\n"
            "Run: pip install torch diffusers transformers accelerate"
        )
    except Exception as e:
        logger.exception(f"Failed to load model {model_key}")
        raise RuntimeError(f"Model load failed: {e}") from e


def _load_img2img_pipeline(model_key: str):
    global _img2img_pipeline, _current_img2img_model_id, _current_img2img_device

    device = _resolve_torch_device()

    if _img2img_pipeline is not None and _current_img2img_model_id == model_key and _current_img2img_device == device:
        return _img2img_pipeline

    try:
        model_id = SUPPORTED_MODELS.get(model_key, SUPPORTED_MODELS[DEFAULT_MODEL])
        logger.info(f"Loading img2img model: {model_id}  (key={model_key}, device={device})")

        pipe = _build_img2img_pipe(model_key, model_id)
        pipe = pipe.to(device)

        if device == "cuda":
            try:
                pipe.enable_xformers_memory_efficient_attention()
            except Exception as _e:
                logger.debug(f"xformers not available for img2img: {_e}")

        _img2img_pipeline = pipe
        _current_img2img_model_id = model_key
        _current_img2img_device = device
        logger.info(f"Img2img model {model_key} loaded on {device}.")
        return _img2img_pipeline

    except ImportError as e:
        raise RuntimeError(
            f"Required packages missing: {e}\n"
            "Run: pip install torch diffusers transformers accelerate"
        )
    except Exception as e:
        logger.exception(f"Failed to load img2img model {model_key}")
        raise RuntimeError(f"Img2img model load failed: {e}") from e


def _load_source_image(*, source_image_base64: str = "", source_image_path: str = "") -> Image.Image:
    image_base64 = (source_image_base64 or "").strip()
    image_path = (source_image_path or "").strip()

    if image_base64:
        return Image.open(io.BytesIO(base64.b64decode(image_base64))).convert("RGB")

    if image_path:
        return Image.open(image_path).convert("RGB")

    raise RuntimeError("source_image_base64 or source_image_path is required")


def _fit_source_image(image: Image.Image, width: int, height: int) -> Image.Image:
    return ImageOps.fit(image.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)


def _encode_image_to_base64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── public API ────────────────────────────────────────────────────────────────
def generate_image(
    prompt: str,
    negative_prompt: str = "",
    width: int  = 1024,
    height: int = 1024,
    steps: int  = 4,
    guidance_scale: float = 0.0,
    seed: Optional[int] = None,
    model_key: str = "",
) -> dict:
    """
    Generate an image and return base64-encoded PNG + metadata.

    Returns:
        {"image_base64": str, "seed": int,
         "generation_time": float, "model_used": str}
    """
    import torch

    model_key = model_key or DEFAULT_MODEL
    pipe      = _load_pipeline(model_key)
    device = _resolve_torch_device()

    if seed is None:
        seed = int(torch.randint(0, 2**31, (1,)).item())
    generator = torch.Generator(device).manual_seed(seed)

    is_turbo = "turbo" in model_key.lower()
    kwargs: dict[str, object] = dict(
        prompt                = prompt,
        width                 = width,
        height                = height,
        num_inference_steps   = max(steps, 1),
        generator             = generator,
    )
    merged_negative_prompt = _merge_negative_prompt(negative_prompt)
    if merged_negative_prompt:
        kwargs["negative_prompt"] = merged_negative_prompt
    if not is_turbo:
        kwargs["guidance_scale"] = guidance_scale

    t0     = time.time()
    result = pipe(**kwargs)
    elapsed = round(time.time() - t0, 2)

    output_image = _apply_nano_detail_finish(result.images[0])
    buf = io.BytesIO()
    output_image.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "image_base64":    img_b64,
        "seed":            seed,
        "generation_time": elapsed,
        "model_used":      model_key,
    }


def stylize_reference_image(
    prompt: str,
    source_image_base64: str = "",
    source_image_path: str = "",
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 20,
    guidance_scale: float = 5.5,
    strength: float = 0.45,
    seed: Optional[int] = None,
    model_key: str = "",
) -> dict:
    import torch

    model_key = model_key or DEFAULT_MODEL
    pipe = _load_img2img_pipeline(model_key)
    device = _resolve_torch_device()
    init_image = _fit_source_image(
        _load_source_image(
            source_image_base64=source_image_base64,
            source_image_path=source_image_path,
        ),
        width,
        height,
    )

    if seed is None:
        seed = int(torch.randint(0, 2**31, (1,)).item())
    generator = torch.Generator(device).manual_seed(seed)

    is_turbo = "turbo" in model_key.lower()
    kwargs: dict[str, object] = dict(
        prompt=prompt,
        image=init_image,
        strength=max(0.05, min(float(strength), 0.9)),
        num_inference_steps=max(int(steps), 1),
        generator=generator,
    )
    merged_negative_prompt = _merge_negative_prompt(negative_prompt)
    if merged_negative_prompt:
        kwargs["negative_prompt"] = merged_negative_prompt
    if not is_turbo:
        kwargs["guidance_scale"] = guidance_scale

    t0 = time.time()
    try:
        result = pipe(**kwargs)
    except Exception as exc:
        error_text = str(exc).lower()
        if device == "cuda" and (
            "illegal memory access" in error_text
            or "cuda error" in error_text
            or "device-side assert" in error_text
        ):
            logger.warning("img2img CUDA failure detected, retrying on CPU: %s", exc)
            torch.cuda.empty_cache()
            cpu_pipe = _load_img2img_pipeline(model_key)
            if hasattr(cpu_pipe, "to"):
                cpu_pipe = cpu_pipe.to("cpu")
            cpu_generator = torch.Generator("cpu").manual_seed(seed)
            cpu_kwargs = dict(kwargs)
            cpu_kwargs["generator"] = cpu_generator
            result = cpu_pipe(**cpu_kwargs)
        else:
            raise
    elapsed = round(time.time() - t0, 2)
    output_image = _apply_nano_detail_finish(result.images[0])

    return {
        "image_base64": _encode_image_to_base64(output_image),
        "seed": seed,
        "generation_time": elapsed,
        "model_used": model_key,
    }


def check_gpu_status() -> dict:
    """Return GPU status dict (used by /api/v1/image/status)."""
    try:
        import torch
        if torch.cuda.is_available():
            idx = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(idx)
            return {
                "available":       True,
                "device_name":     torch.cuda.get_device_name(idx),
                "total_memory_gb": round(props.total_memory / 1e9, 1),
                "allocated_gb":    round(torch.cuda.memory_allocated(idx) / 1e9, 2),
                "sm_version":      f"{props.major}.{props.minor}",
                "model_loaded":    _current_model_id or None,
            }
        return {"available": False, "device_name": "cpu", "model_loaded": _current_model_id or None}
    except ImportError:
        return {"available": False, "error": "torch not installed"}
