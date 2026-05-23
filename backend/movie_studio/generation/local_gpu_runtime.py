from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.request import urlopen

from PIL import Image

from backend.image.generator import check_gpu_status, generate_image, stylize_reference_image
from backend.movie_studio.storage.scene_bundle_store import scene_bundle_root
from backend.movie_studio.utils.json_tools import write_json
from backend.movie_studio.utils.path_tools import ensure_directory


def _parse_resolution(value: str) -> Tuple[int, int]:
    normalized = str(value or "1280x720").lower().replace("*", "x")
    if "x" not in normalized:
        return (1280, 720)
    left, right = normalized.split("x", 1)
    try:
        width = max(256, int(left))
        height = max(256, int(right))
    except ValueError:
        return (1280, 720)
    return (width, height)


def _map_model_stack_to_image_model(local_model_stack: List[str]) -> str:
    joined = " ".join(local_model_stack).lower()
    if "flux" in joined:
        return "flux-schnell"
    if "sd15" in joined:
        return "sd15"
    return "sdxl"


def _first_local_file(paths: List[str]) -> str:
    for item in paths:
        candidate = str(item or "").strip()
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists() and path.is_file():
            return str(path)
    return ""


def _materialize_reference_image(reference: str, artifact_root: Path, file_stem: str) -> str:
    candidate = str(reference or "").strip()
    if not candidate:
        return ""

    path = Path(candidate)
    if path.exists() and path.is_file():
        return str(path)

    refs_dir = ensure_directory(artifact_root / "references")
    output_path = refs_dir / f"{file_stem}.png"

    if candidate.startswith("data:image"):
        try:
            encoded = candidate.split(",", 1)[1]
            output_path.write_bytes(base64.b64decode(encoded))
            return str(output_path)
        except Exception:
            return ""

    if candidate.startswith("http://") or candidate.startswith("https://"):
        try:
            with urlopen(candidate, timeout=20) as response:
                output_path.write_bytes(response.read())
            return str(output_path)
        except Exception:
            return ""

    return ""


def _scene_prompt(
    payload: Dict[str, object],
    scene_request: Dict[str, object],
    continuity_contract: List[str],
    environment_contract: Dict[str, object],
    actor_identity: Dict[str, object],
) -> str:
    notes = [str(item).strip() for item in list(scene_request.get("director_notes") or []) if str(item).strip()]
    continuity = "; ".join(continuity_contract[:4])
    environment_summary = str(environment_contract.get("location_summary") or environment_contract.get("environment_type") or "environment").strip()
    actor_name = str(actor_identity.get("display_name") or actor_identity.get("actor_id") or "lead actor").strip()
    prompt_parts = [
        str(payload.get("synopsis") or payload.get("title") or "photoreal movie shot").strip(),
        f"scene objective: {'; '.join(notes) if notes else 'hero scene progression'}",
        str(scene_request.get("narrative_prompt") or "").strip(),
        f"lead subject: {actor_name}",
        f"environment: {environment_summary}",
        "style: photoreal cinematic film still, realistic human anatomy, realistic lighting, realistic architecture, premium camera composition",
        f"continuity: {continuity}" if continuity else "continuity: maintain real-human identity and environment realism",
        f"timeline window: {scene_request.get('start_frame')} to {scene_request.get('end_frame')} frames, {scene_request.get('start_second')}s to {scene_request.get('end_second')}s",
    ]
    return ". ".join(part for part in prompt_parts if part)


def _negative_prompt() -> str:
    return ", ".join([
        "cartoon",
        "animation",
        "illustration",
        "cgi look",
        "deformed hands",
        "extra fingers",
        "bad anatomy",
        "duplicate limbs",
        "face distortion",
        "warped background",
        "low detail",
        "text artifacts",
        "coarse grain",
        "heavy film grain",
        "sensor noise",
        "macro noise particles",
        "oversized texture clumps",
        "blotchy skin pores",
    ])


def prepare_local_gpu_runtime_plan(
    project_id: str,
    payload: Dict[str, object],
    scene_generation_requests: List[Dict[str, object]],
    self_hosted_generation_bundle: Dict[str, object],
    continuity_contract: List[str],
    environment_contract: Dict[str, object],
    actor_identity: Dict[str, object],
) -> Dict[str, object]:
    artifact_root = ensure_directory(scene_bundle_root(project_id) / "local_gpu_runtime")
    identity_references = [str(item).strip() for item in list(payload.get("identity_references") or []) if str(item).strip()]
    environment_references = [str(item).strip() for item in list(payload.get("environment_references") or []) if str(item).strip()]
    primary_reference = _first_local_file(identity_references) or _first_local_file(environment_references)
    if not primary_reference:
        for index, item in enumerate(identity_references):
            primary_reference = _materialize_reference_image(item, artifact_root, f"identity_{index + 1:02d}")
            if primary_reference:
                break
    if not primary_reference:
        for index, item in enumerate(environment_references):
            primary_reference = _materialize_reference_image(item, artifact_root, f"environment_{index + 1:02d}")
            if primary_reference:
                break
    local_model_stack = list(self_hosted_generation_bundle.get("local_model_stack") or [])
    image_model_key = _map_model_stack_to_image_model(local_model_stack)
    width, height = _parse_resolution(str(payload.get("target_resolution") or "1280x720"))
    tasks: List[Dict[str, object]] = []
    for index, scene_request in enumerate(scene_generation_requests):
        scene_id = str(scene_request.get("scene_id") or f"scene-{index+1:02d}")
        scene_dir = ensure_directory(artifact_root / scene_id)
        tasks.append(
            {
                "scene_id": scene_id,
                "sequence_id": str(scene_request.get("sequence_id") or f"seq-{index+1:02d}"),
                "prompt": _scene_prompt(payload, scene_request, continuity_contract, environment_contract, actor_identity),
                "negative_prompt": _negative_prompt(),
                "output_dir": str(scene_dir),
                "output_image_path": str(scene_dir / "keyframe.png"),
                "reference_image_path": primary_reference,
                "identity_reference_count": len(identity_references),
                "environment_reference_count": len(environment_references),
                "start_second": float(scene_request.get("start_second") or 0.0),
                "end_second": float(scene_request.get("end_second") or 0.0),
                "start_frame": int(scene_request.get("start_frame") or 1),
                "end_frame": int(scene_request.get("end_frame") or 1),
                "frame_count": int(scene_request.get("frame_count") or 1),
                "narrative_prompt": str(scene_request.get("narrative_prompt") or ""),
                "interpolation_strategy": str(scene_request.get("interpolation_strategy") or "dual_keyframe_narrative_morph"),
                "continuity_checks": list(scene_request.get("continuity_checks") or []),
                "width": width,
                "height": height,
                "steps": 40,
                "guidance_scale": 7.5,
                "strength": 0.3,
                "image_model_key": image_model_key,
            }
        )
    runtime_plan = {
        "provider": "self-hosted-local-gpu-runtime",
        "project_id": project_id,
        "artifact_root": str(artifact_root),
        "gpu_status": check_gpu_status(),
        "image_model_key": image_model_key,
        "task_count": len(tasks),
        "tasks": tasks,
    }
    write_json(artifact_root / "runtime_plan.json", runtime_plan)
    return runtime_plan


def _write_png_from_base64(image_base64: str, output_path: str) -> None:
    image = Image.open(BytesIO(base64.b64decode(image_base64))).convert("RGB")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")


def run_local_gpu_storyboard_keyframes(runtime_plan: Dict[str, object]) -> Dict[str, object]:
    tasks = list(runtime_plan.get("tasks") or [])
    results: List[Dict[str, object]] = []
    for task in tasks:
        reference_image_path = str(task.get("reference_image_path") or "").strip()
        if reference_image_path:
            generation = stylize_reference_image(
                prompt=str(task.get("prompt") or ""),
                source_image_path=reference_image_path,
                negative_prompt=str(task.get("negative_prompt") or ""),
                width=int(task.get("width") or 1280),
                height=int(task.get("height") or 720),
                steps=int(task.get("steps") or 20),
                guidance_scale=float(task.get("guidance_scale") or 6.0),
                strength=float(task.get("strength") or 0.42),
                model_key=str(task.get("image_model_key") or "sdxl"),
            )
            generation_mode = "img2img"
        else:
            generation = generate_image(
                prompt=str(task.get("prompt") or ""),
                negative_prompt=str(task.get("negative_prompt") or ""),
                width=int(task.get("width") or 1280),
                height=int(task.get("height") or 720),
                steps=int(task.get("steps") or 20),
                guidance_scale=float(task.get("guidance_scale") or 6.0),
                model_key=str(task.get("image_model_key") or "sdxl"),
            )
            generation_mode = "txt2img"
        _write_png_from_base64(str(generation["image_base64"]), str(task.get("output_image_path") or ""))
        results.append(
            {
                "scene_id": str(task.get("scene_id") or ""),
                "generation_mode": generation_mode,
                "output_image_path": str(task.get("output_image_path") or ""),
                "model_used": str(generation.get("model_used") or task.get("image_model_key") or ""),
                "seed": generation.get("seed"),
                "generation_time": generation.get("generation_time"),
            }
        )
    manifest = {
        "provider": "self-hosted-local-gpu-runtime",
        "project_id": str(runtime_plan.get("project_id") or ""),
        "artifact_root": str(runtime_plan.get("artifact_root") or ""),
        "result_count": len(results),
        "results": results,
    }
    artifact_root = Path(str(runtime_plan.get("artifact_root") or ""))
    if str(artifact_root):
        write_json(artifact_root / "runtime_results.json", manifest)
    return manifest
