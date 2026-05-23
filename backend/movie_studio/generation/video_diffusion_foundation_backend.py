from __future__ import annotations

import importlib
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageEnhance, ImageFilter

from backend.movie_studio.storage.scene_bundle_store import scene_bundle_root
from backend.movie_studio.utils.json_tools import write_json
from backend.movie_studio.utils.path_tools import ensure_directory


MOVIE_STUDIO_OPERATION_SECONDS = 60
MOVIE_STUDIO_OPERATION_FPS = 8
MOVIE_STUDIO_OPERATION_TOTAL_FRAMES = MOVIE_STUDIO_OPERATION_SECONDS * MOVIE_STUDIO_OPERATION_FPS
MOVIE_STUDIO_SMOKE_TEST_SECONDS = 5
MOVIE_STUDIO_SMOKE_TEST_FRAMES = 40

FOUNDATION_PIPELINE_CANDIDATES: List[Dict[str, object]] = [
    {
        "match": "wan",
        "pipeline_classes": ["WanImageToVideoPipeline"],
        "model_id_env": "MOVIE_STUDIO_WAN_MODEL_ID",
        "default_model_id": "stabilityai/stable-video-diffusion-img2vid-xt",
        "mode": "image_to_video",
        "accepts_prompt": True,
        "adapter_key": "wan",
        "smoke_inference_steps": 8,
        "full_inference_steps": 18,
        "segment_frames": 10,
    },
    {
        "match": "hunyuan",
        "pipeline_classes": ["HunyuanVideoPipeline", "HunyuanImageToVideoPipeline"],
        "model_id_env": "MOVIE_STUDIO_HUNYUAN_MODEL_ID",
        "default_model_id": "stabilityai/stable-video-diffusion-img2vid-xt",
        "mode": "image_to_video",
        "accepts_prompt": True,
        "adapter_key": "hunyuan",
        "smoke_inference_steps": 8,
        "full_inference_steps": 18,
        "segment_frames": 10,
    },
    {
        "match": "stable-video",
        "pipeline_classes": ["StableVideoDiffusionPipeline"],
        "model_id_env": "MOVIE_STUDIO_STABLE_VIDEO_MODEL_ID",
        "default_model_id": "stabilityai/stable-video-diffusion-img2vid-xt",
        "mode": "image_to_video",
        "accepts_prompt": False,
        "adapter_key": "stable-video",
        "smoke_inference_steps": 8,
        "full_inference_steps": 18,
        "segment_frames": 10,
    },
]


def _truncate_tokens(value: str, limit: int) -> str:
    tokens = [token for token in str(value or "").replace("\n", " ").split(" ") if token]
    return " ".join(tokens[:limit]).strip()


def _compress_prompt(scene: Dict[str, object], frame_index: int, progress: float) -> str:
    performance_actions = list(scene.get("performance_actions") or [])
    physical_laws = list(scene.get("physical_continuity_laws") or [])
    action_summary = "; ".join(
        f"{str(item.get('unit') or '').strip()}:{str(item.get('goal') or '').strip()}"
        for item in performance_actions[:4]
        if str(item.get("unit") or "").strip()
    )
    law_summary = "; ".join(str(item).strip() for item in physical_laws[:3] if str(item).strip())
    prompt_parts = [
        _truncate_tokens(str(scene.get("title") or scene.get("scene_id") or "scene"), 8),
        _truncate_tokens(str(scene.get("prompt") or ""), 24),
        _truncate_tokens(str(scene.get("narrative_prompt") or ""), 28),
        _truncate_tokens(action_summary, 24),
        _truncate_tokens(law_summary, 24),
        "nano-detail skin texture, micro-grain suppressed, clean photoreal surface",
        _truncate_tokens(str(scene.get("walking_pattern") or ""), 10),
        _truncate_tokens(str(scene.get("gesture_pattern") or ""), 10),
        _truncate_tokens(str(scene.get("speaking_mode") or ""), 6),
        _truncate_tokens(str(scene.get("lip_sync_requirement") or ""), 6),
        f"frame {frame_index}",
        f"progress {progress:.2f}",
    ]
    return ", ".join(part for part in prompt_parts if part)


def _build_adapter_call(
    backend: Dict[str, Any],
    scene: Dict[str, object],
    init_image: Image.Image,
    frame_count: int,
    generator: Any,
    prompt: str,
    phase: str,
) -> Dict[str, Any]:
    model_name = str(backend.get("model_name") or "").lower()
    adapter_key = str(backend.get("adapter_key") or "").lower()
    inference_steps = int(backend.get("smoke_inference_steps") or 10) if phase == "smoke" else int(backend.get("full_inference_steps") or 14)
    guidance_schedule = dict(scene.get("guidance_schedule") or {})
    start_guidance = float(guidance_schedule.get("start_guidance") or 1.8)
    end_guidance = float(guidance_schedule.get("end_guidance") or 2.4)
    base_kwargs: Dict[str, Any] = {
        "image": init_image,
        "height": init_image.height,
        "width": init_image.width,
        "num_frames": frame_count,
        "generator": generator,
        "fps": MOVIE_STUDIO_OPERATION_FPS,
        "decode_chunk_size": 4,
        "min_guidance_scale": start_guidance,
        "max_guidance_scale": end_guidance,
    }

    if adapter_key == "stable-video" or "stable-video" in model_name:
        base_kwargs["num_inference_steps"] = inference_steps
        base_kwargs["motion_bucket_id"] = 160
        base_kwargs["noise_aug_strength"] = 0.002
        return base_kwargs

    if adapter_key == "wan" or "wan" in model_name:
        base_kwargs["prompt"] = prompt
        base_kwargs["num_inference_steps"] = inference_steps
        return base_kwargs

    if adapter_key == "hunyuan" or "hunyuan" in model_name:
        base_kwargs["prompt"] = prompt
        base_kwargs["num_inference_steps"] = inference_steps
        return base_kwargs

    if bool(backend.get("accepts_prompt", True)):
        base_kwargs["prompt"] = prompt
    base_kwargs["num_inference_steps"] = inference_steps
    return base_kwargs


def _safe_pipeline_call(pipeline: Any, call_kwargs: Dict[str, Any]) -> Any:
    try:
        return pipeline(**call_kwargs)
    except TypeError as exc:
        filtered = dict(call_kwargs)
        error_text = str(exc)
        for candidate in ["prompt", "fps", "decode_chunk_size", "noise_aug_strength", "motion_bucket_id"]:
            if candidate in filtered and candidate in error_text:
                filtered.pop(candidate, None)
        if filtered == call_kwargs:
            raise
        return pipeline(**filtered)


def _normalize_clip_frames(frames: List[Image.Image], required_frames: int, size: tuple[int, int]) -> List[Image.Image]:
    if required_frames <= 0:
        return []
    if not frames:
        return []
    if len(frames) == required_frames:
        return [frame.convert("RGB").resize(size, Image.Resampling.LANCZOS) for frame in frames]

    normalized: List[Image.Image] = []
    for index in range(required_frames):
        source_index = min(len(frames) - 1, int(math.floor((index / max(1, required_frames - 1)) * max(1, len(frames) - 1))))
        normalized.append(frames[source_index].convert("RGB").resize(size, Image.Resampling.LANCZOS))
    return normalized


def _apply_nano_frame_refinement(frame: Image.Image) -> Image.Image:
    refined = frame.convert("RGB").resize(frame.size, Image.Resampling.LANCZOS)
    refined = refined.filter(ImageFilter.MedianFilter(size=3))
    refined = refined.filter(ImageFilter.GaussianBlur(radius=0.08))
    refined = refined.filter(ImageFilter.UnsharpMask(radius=1.25, percent=135, threshold=2))
    refined = ImageEnhance.Contrast(refined).enhance(1.02)
    refined = ImageEnhance.Sharpness(refined).enhance(1.08)
    return refined


def _generate_chunk_frames(
    backend: Dict[str, Any],
    scene: Dict[str, object],
    init_image: Image.Image,
    frame_count: int,
    generator: Any,
    compressed_prompt: str,
    carry_over_state: Dict[str, str],
) -> tuple[List[Image.Image], List[Dict[str, object]]]:
    remaining = frame_count
    current_image = init_image
    all_frames: List[Image.Image] = []
    segment_logs: List[Dict[str, object]] = []
    segment_index = 0
    segment_frames = max(8, int(backend.get("segment_frames") or 20))

    while remaining > 0:
        segment_index += 1
        request_frames = min(segment_frames, remaining)
        call_prompt = f"{compressed_prompt}, carry_over={carry_over_state}, segment={segment_index}"
        call_kwargs = _build_adapter_call(backend, scene, current_image, request_frames, generator, call_prompt, "full")
        started_at = time.time()
        result = _safe_pipeline_call(backend["pipeline"], call_kwargs)
        segment_clip = _extract_frames(result)
        elapsed = round(time.time() - started_at, 2)
        normalized_segment = _normalize_clip_frames(segment_clip, request_frames, (current_image.width, current_image.height))
        if not normalized_segment:
            break
        all_frames.extend(normalized_segment)
        current_image = normalized_segment[-1]
        remaining -= len(normalized_segment)
        segment_logs.append(
            {
                "segment_index": segment_index,
                "requested_frames": request_frames,
                "generated_frames": len(segment_clip),
                "normalized_frames": len(normalized_segment),
                "generation_time_seconds": elapsed,
            }
        )

    final_frames = _normalize_clip_frames(all_frames, frame_count, (init_image.width, init_image.height))
    return final_frames, segment_logs


def _carry_over_payload(scene: Dict[str, object], previous_carry_over: Dict[str, str] | None) -> Dict[str, str]:
    payload = {
        "identity": str(scene.get("performance_unit") or "full_body_human_motion"),
        "walking_pattern": str(scene.get("walking_pattern") or "motivated cinematic walking"),
        "gesture_pattern": str(scene.get("gesture_pattern") or "motivated hand and arm gesture progression"),
        "speaking_mode": str(scene.get("speaking_mode") or "dialogue_sync_required"),
        "lip_sync_requirement": str(scene.get("lip_sync_requirement") or "phoneme_visible"),
        "physical_law": "; ".join(str(item).strip() for item in list(scene.get("physical_continuity_laws") or [])[:2] if str(item).strip()),
    }
    if previous_carry_over:
        payload["previous_identity"] = str(previous_carry_over.get("identity") or "")
        payload["previous_walking_pattern"] = str(previous_carry_over.get("walking_pattern") or "")
    return payload


def _run_smoke_test(backend: Dict[str, Any], scene: Dict[str, object], init_image: Image.Image, generator: Any) -> Dict[str, object]:
    prompt = _compress_prompt(scene, int(scene.get("start_frame") or 1), 0.0)
    smoke_kwargs = _build_adapter_call(backend, scene, init_image, MOVIE_STUDIO_SMOKE_TEST_FRAMES, generator, prompt, "smoke")
    result = _safe_pipeline_call(backend["pipeline"], smoke_kwargs)
    clip_frames = _extract_frames(result)
    normalized_frames = _normalize_clip_frames(clip_frames, MOVIE_STUDIO_SMOKE_TEST_FRAMES, (init_image.width, init_image.height))
    passed = len(normalized_frames) >= MOVIE_STUDIO_SMOKE_TEST_FRAMES
    return {
        "passed": passed,
        "generated_frames": len(clip_frames),
        "normalized_frames": len(normalized_frames),
        "required_frames": MOVIE_STUDIO_SMOKE_TEST_FRAMES,
        "reason": None if passed else f"smoke test produced {len(clip_frames)} frames",
    }


def _load_rgb(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")


def _resolve_device(torch_module: Any) -> str:
    preferred = (os.getenv("MOVIE_STUDIO_VIDEO_DEVICE", "") or "").strip().lower()
    if preferred in {"cpu", "cuda"}:
        if preferred == "cuda" and not torch_module.cuda.is_available():
            return "cpu"
        return preferred
    return "cuda" if torch_module.cuda.is_available() else "cpu"


def _resolve_pipeline(model_stack: List[str]) -> Dict[str, Any]:
    diffusers = importlib.import_module("diffusers")
    torch = importlib.import_module("torch")
    device = _resolve_device(torch)
    available_stack = [str(item).strip() for item in model_stack if str(item).strip()]
    available_stack = available_stack or ["stable-video-diffusion-xt"]
    errors: List[str] = []

    for model_name in available_stack:
        normalized_name = model_name.lower()
        for candidate in FOUNDATION_PIPELINE_CANDIDATES:
            if str(candidate["match"]) not in normalized_name and str(candidate["match"]) != "stable-video":
                continue
            for class_name in list(candidate["pipeline_classes"]):
                pipeline_cls = getattr(diffusers, class_name, None)
                if pipeline_cls is None:
                    errors.append(f"missing pipeline class: {class_name}")
                    continue
                model_id = os.getenv(str(candidate["model_id_env"]), str(candidate["default_model_id"]))
                try:
                    dtype = torch.float16 if device == "cuda" else torch.float32
                    pipeline = pipeline_cls.from_pretrained(model_id, torch_dtype=dtype)
                    pipeline = pipeline.to(device)
                    return {
                        "pipeline": pipeline,
                        "mode": str(candidate["mode"]),
                        "accepts_prompt": bool(candidate.get("accepts_prompt", True)),
                        "adapter_key": str(candidate.get("adapter_key") or "generic"),
                        "smoke_inference_steps": int(candidate.get("smoke_inference_steps") or 10),
                        "full_inference_steps": int(candidate.get("full_inference_steps") or 14),
                        "segment_frames": int(candidate.get("segment_frames") or 20),
                        "model_name": model_name,
                        "model_id": model_id,
                        "device": device,
                    }
                except Exception as exc:  # pragma: no cover - runtime backend best-effort
                    errors.append(f"{class_name}:{model_id}:{exc}")
    raise RuntimeError("video diffusion foundation backend unavailable: " + " | ".join(errors[-6:]))


def _extract_frames(result: Any) -> List[Image.Image]:
    frames = getattr(result, "frames", None)
    if isinstance(frames, list) and frames:
        if isinstance(frames[0], list):
            return [frame.convert("RGB") for frame in frames[0] if hasattr(frame, "convert")]
        return [frame.convert("RGB") for frame in frames if hasattr(frame, "convert")]
    images = getattr(result, "images", None)
    if isinstance(images, list) and images:
        return [frame.convert("RGB") for frame in images if hasattr(frame, "convert")]
    return []


def _frame_prompt(scene: Dict[str, object], frame_index: int, progress: float) -> str:
    continuity_checks = [str(item).strip() for item in list(scene.get("continuity_checks") or []) if str(item).strip()]
    performance_actions = list(scene.get("performance_actions") or [])
    physical_laws = [str(item).strip() for item in list(scene.get("physical_continuity_laws") or []) if str(item).strip()]
    performance_summary = " ; ".join(
        f"{str(item.get('unit') or '').strip()}={str(item.get('requirement') or '').strip()}"
        for item in performance_actions[:5]
        if str(item.get("unit") or "").strip()
    )
    return " ".join(
        part for part in [
            str(scene.get("prompt") or "").strip(),
            str(scene.get("narrative_prompt") or "").strip(),
            f"performance_unit={str(scene.get('performance_unit') or 'full_body_human_motion').strip()}",
            f"walking_pattern={str(scene.get('walking_pattern') or 'motivated cinematic walking').strip()}",
            f"gesture_pattern={str(scene.get('gesture_pattern') or 'motivated hand and arm gesture progression').strip()}",
            f"speaking_mode={str(scene.get('speaking_mode') or 'dialogue_sync_required').strip()}",
            f"lip_sync_requirement={str(scene.get('lip_sync_requirement') or 'phoneme_visible').strip()}",
            f"performance_actions={performance_summary}" if performance_summary else "",
            f"physical_laws={' ; '.join(physical_laws[:3])}" if physical_laws else "",
            f"frame_index={frame_index}",
            f"progress={progress:.4f}",
            f"interpolation={str(scene.get('interpolation_strategy') or 'video_diffusion_foundation').strip()}",
            f"continuity_checks={' ; '.join(continuity_checks)}" if continuity_checks else "",
        ] if part
    )


def run_video_diffusion_foundation_backend(plan: Dict[str, object], runtime_plan: Dict[str, object]) -> Dict[str, object]:
    project_id = str(plan.get("project_id") or runtime_plan.get("project_id") or "movie-studio")
    artifact_root = ensure_directory(scene_bundle_root(project_id) / "video_diffusion_foundation_backend")
    model_stack = list((runtime_plan or {}).get("local_model_stack") or [])
    try:
        backend = _resolve_pipeline(model_stack)
    except Exception as exc:  # pragma: no cover - runtime dependency path
        manifest = {
            "provider": "video-diffusion-foundation-backend",
            "project_id": project_id,
            "required_total_frames": MOVIE_STUDIO_OPERATION_TOTAL_FRAMES,
            "generated_frame_count": 0,
            "quality_gate_failed": True,
            "quality_gate_reason": str(exc),
            "frames": [],
        }
        write_json(artifact_root / "video_diffusion_foundation_manifest.json", manifest)
        return manifest

    scenes = list(plan.get("scenes") or [])
    frame_records: List[Dict[str, object]] = []
    generation_log: List[Dict[str, object]] = []
    torch = importlib.import_module("torch")
    device = str(backend.get("device") or _resolve_device(torch))
    carry_over_state: Dict[str, str] | None = None

    for index, scene in enumerate(scenes):
        keyframe_path = str(scene.get("keyframe_path") or "").strip()
        if not keyframe_path:
            continue
        seed = int(scene.get("start_frame") or (index + 1))
        generator = torch.Generator(device).manual_seed(seed)
        init_image = _load_rgb(keyframe_path)
        frame_count = max(1, int(scene.get("frame_count") or 1))
        frames_dir = ensure_directory(Path(str(scene.get("frames_dir") or artifact_root / str(scene.get("scene_id") or f"scene-{index+1:02d}") / "frames")))
        compressed_prompt = _compress_prompt(scene, int(scene.get("start_frame") or 1), 0.0)
        smoke_test = _run_smoke_test(backend, scene, init_image, generator)
        if not smoke_test["passed"]:
            manifest = {
                "provider": "video-diffusion-foundation-backend",
                "project_id": project_id,
                "model_name": str(backend.get("model_name") or ""),
                "model_id": str(backend.get("model_id") or ""),
                "device": device,
                "required_total_frames": MOVIE_STUDIO_OPERATION_TOTAL_FRAMES,
                "generated_frame_count": len(frame_records),
                "quality_gate_failed": True,
                "quality_gate_reason": smoke_test["reason"] or "foundation smoke test failed",
                "generation_log": generation_log,
                "frames": frame_records,
            }
            write_json(artifact_root / "video_diffusion_foundation_manifest.json", manifest)
            return manifest

        carry_over_state = _carry_over_payload(scene, carry_over_state)
        clip_frames, segment_logs = _generate_chunk_frames(
            backend,
            scene,
            init_image,
            frame_count,
            generator,
            compressed_prompt,
            carry_over_state,
        )
        elapsed = round(sum(float(item.get("generation_time_seconds") or 0.0) for item in segment_logs), 2)
        generation_log.append(
            {
                "scene_id": str(scene.get("scene_id") or ""),
                "model_name": str(backend.get("model_name") or ""),
                "model_id": str(backend.get("model_id") or ""),
                "device": device,
                "requested_frames": frame_count,
                "generated_frames": len(clip_frames),
                "generation_time_seconds": elapsed,
                "compressed_prompt": compressed_prompt,
                "smoke_test": smoke_test,
                "carry_over_state": carry_over_state,
                "segment_logs": segment_logs,
            }
        )

        start_frame = int(scene.get("start_frame") or 1)
        performance_actions = list(scene.get("performance_actions") or [])
        for local_index, frame in enumerate(clip_frames[:frame_count]):
            absolute_index = start_frame + local_index
            output_path = frames_dir / f"frame_{absolute_index:04d}.png"
            frame.save(output_path, format="PNG")
            progress = local_index / max(1, frame_count - 1)
            frame_records.append(
                {
                    "scene_id": str(scene.get("scene_id") or ""),
                    "frame_index": absolute_index,
                    "image_path": str(output_path),
                    "prompt": _frame_prompt(scene, absolute_index, progress),
                    "compressed_prompt": _compress_prompt(scene, absolute_index, progress),
                    "interpolation_strategy": str(scene.get("interpolation_strategy") or "video_diffusion_foundation"),
                    "continuity_checks": list(scene.get("continuity_checks") or []),
                    "performance_unit": str(scene.get("performance_unit") or "full_body_human_motion"),
                    "walking_pattern": str(scene.get("walking_pattern") or "motivated cinematic walking"),
                    "gesture_pattern": str(scene.get("gesture_pattern") or "motivated hand and arm gesture progression"),
                    "speaking_mode": str(scene.get("speaking_mode") or "dialogue_sync_required"),
                    "lip_sync_requirement": str(scene.get("lip_sync_requirement") or "phoneme_visible"),
                    "performance_actions": performance_actions,
                    "physical_continuity_laws": list(scene.get("physical_continuity_laws") or []),
                    "guidance_schedule": dict(scene.get("guidance_schedule") or {}),
                }
            )

    quality_gate_failed = len(frame_records) != MOVIE_STUDIO_OPERATION_TOTAL_FRAMES
    manifest = {
        "provider": "video-diffusion-foundation-backend",
        "project_id": project_id,
        "model_name": str(backend.get("model_name") or ""),
        "model_id": str(backend.get("model_id") or ""),
        "device": device,
        "operation_seconds": MOVIE_STUDIO_OPERATION_SECONDS,
        "frames_per_second": MOVIE_STUDIO_OPERATION_FPS,
        "required_total_frames": MOVIE_STUDIO_OPERATION_TOTAL_FRAMES,
        "generated_frame_count": len(frame_records),
        "quality_gate_failed": quality_gate_failed,
        "quality_gate_reason": None if not quality_gate_failed else f"expected {MOVIE_STUDIO_OPERATION_TOTAL_FRAMES} frames, got {len(frame_records)}",
        "generation_log": generation_log,
        "frames": frame_records,
    }
    write_json(artifact_root / "video_diffusion_foundation_manifest.json", manifest)
    return manifest
