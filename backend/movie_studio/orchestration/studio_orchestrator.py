from __future__ import annotations

from typing import Dict, List

from backend.movie_studio.cinematography.camera_language_engine import build_camera_language
from backend.movie_studio.contracts.quality_gate_contract import QualityFailureContract
from backend.movie_studio.director.continuity_supervisor import build_continuity_contract
from backend.movie_studio.director.sequence_planner import build_sequence_plan
from backend.movie_studio.director.shot_planner import build_shot_plan
from backend.movie_studio.director.story_bible_engine import build_story_bible
from backend.movie_studio.editorial.sequence_editor import build_editorial_timeline
from backend.movie_studio.environment.environment_bible_engine import build_environment_contract
from backend.movie_studio.environment.horizon_perspective_lock import build_horizon_perspective_lock
from backend.movie_studio.environment.lighting_map_engine import build_lighting_map
from backend.movie_studio.environment.weather_time_engine import build_weather_time_contract
from backend.movie_studio.generation.multi_pass_refinement_engine import build_refinement_plan
from backend.movie_studio.generation.local_gpu_runtime import prepare_local_gpu_runtime_plan
from backend.movie_studio.generation.local_shot_sequence_runtime import (
    prepare_local_shot_sequence_plan,
    render_local_shot_sequence_video,
    run_local_shot_sequence_frames,
)
from backend.movie_studio.generation.scene_generation_engine import build_scene_generation_requests
from backend.movie_studio.generation.self_hosted_generation_engine import build_self_hosted_generation_bundle
from backend.movie_studio.generation.temporal_consistency_engine import build_temporal_consistency_contract
from backend.movie_studio.generation.upscale_restore_engine import build_upscale_plan
from backend.movie_studio.identity.actor_identity_engine import build_actor_identity
from backend.movie_studio.identity.anatomy_guard import build_anatomy_guard
from backend.movie_studio.identity.costume_continuity_engine import build_costume_continuity
from backend.movie_studio.identity.face_lock_engine import build_face_lock
from backend.movie_studio.performance.blocking_engine import build_blocking_plan
from backend.movie_studio.performance.cta_choreography_engine import build_cta_choreography
from backend.movie_studio.performance.eye_line_engine import build_eye_line_map
from backend.movie_studio.performance.gesture_engine import build_gesture_map
from backend.movie_studio.quality.anatomy_quality_gate import anatomy_quality_rules
from backend.movie_studio.quality.environment_quality_gate import environment_quality_rules
from backend.movie_studio.quality.face_quality_gate import face_quality_rules
from backend.movie_studio.quality.hand_quality_gate import hand_quality_rules
from backend.movie_studio.quality.local_quality_runtime import prepare_local_quality_runtime_plan
from backend.movie_studio.quality.local_quality_runtime import run_local_quality_gate
from backend.movie_studio.quality.self_hosted_quality_gate import build_self_hosted_quality_requirements, build_self_hosted_quality_result
from backend.movie_studio.quality.temporal_flicker_gate import temporal_flicker_rules
from backend.movie_studio.review.approval_queue_service import build_approval_queue
from backend.movie_studio.review.review_console_service import build_review_items
from backend.movie_studio.orchestration.internal_runtime_policy import build_internal_runtime_policy
from backend.movie_studio.orchestration.sovereign_pipeline_engine import build_sovereign_pipeline_contract
from backend.movie_studio.storage.review_artifact_store import review_artifact_root
from backend.movie_studio.storage.scene_bundle_store import scene_bundle_root
from backend.movie_studio.utils.json_tools import write_json


def build_movie_studio_project(payload: Dict[str, object]) -> Dict[str, object]:
    director_output = build_story_bible(payload)
    sequence_plan = build_sequence_plan(director_output)
    shot_plan = build_shot_plan(sequence_plan)
    continuity_contract = build_continuity_contract(payload)
    actor_identity = build_actor_identity(payload)
    face_lock = build_face_lock(actor_identity)
    anatomy_guard = build_anatomy_guard(actor_identity)
    costume_continuity = build_costume_continuity(payload)
    environment_contract = build_environment_contract(payload)
    lighting_map = build_lighting_map(environment_contract)
    horizon_lock = build_horizon_perspective_lock(environment_contract)
    weather_time = build_weather_time_contract(environment_contract)
    camera_language = build_camera_language(sequence_plan)
    blocking_plan = build_blocking_plan(sequence_plan, actor_identity.actor_id)
    gesture_map = build_gesture_map(payload)
    eye_line_map = build_eye_line_map(payload)
    cta_choreography = build_cta_choreography(payload)
    refinement_plan = build_refinement_plan()
    temporal_consistency = build_temporal_consistency_contract()
    upscale_plan = build_upscale_plan(payload)
    sovereign_pipeline_contract = build_sovereign_pipeline_contract(payload)
    internal_runtime_policy = build_internal_runtime_policy(payload)
    self_hosted_generation_bundle = build_self_hosted_generation_bundle(payload, director_output.project_id)
    scene_generation_requests = build_scene_generation_requests(
        project_id=director_output.project_id,
        sequence_plan=sequence_plan,
        camera_contract_ids=[shot.shot_id for shot in camera_language],
        performance_contract_ids=[[beat.beat_id] for beat in blocking_plan],
        target_duration_seconds=int(payload.get("target_duration_seconds") or 60),
        target_fps=int(payload.get("target_fps") or 24),
        target_resolution=str(payload.get("target_resolution") or "1920x1080"),
    )
    local_gpu_runtime_plan = prepare_local_gpu_runtime_plan(
        project_id=director_output.project_id,
        payload=payload,
        scene_generation_requests=[request.model_dump() for request in scene_generation_requests],
        self_hosted_generation_bundle=self_hosted_generation_bundle,
        continuity_contract=continuity_contract,
        environment_contract=environment_contract.model_dump(),
        actor_identity=actor_identity.model_dump(),
    )
    local_shot_sequence_plan = prepare_local_shot_sequence_plan(
        project_id=director_output.project_id,
        payload=payload,
        sequence_plan=sequence_plan,
        scene_generation_requests=[request.model_dump() for request in scene_generation_requests],
        local_gpu_runtime_plan=local_gpu_runtime_plan,
    )
    quality_failures: List[QualityFailureContract] = []
    quality_failures.extend(face_quality_rules())
    quality_failures.extend(hand_quality_rules())
    quality_failures.extend(anatomy_quality_rules())
    quality_failures.extend(environment_quality_rules())
    quality_failures.extend(temporal_flicker_rules())
    quality_result = build_self_hosted_quality_result(quality_failures)
    self_hosted_quality_requirements = build_self_hosted_quality_requirements(payload)
    local_quality_runtime_plan = prepare_local_quality_runtime_plan(
        project_id=director_output.project_id,
        payload=payload,
        local_shot_sequence_plan=local_shot_sequence_plan,
        self_hosted_quality_requirements=self_hosted_quality_requirements,
    )
    review_items = build_review_items([request.scene_id for request in scene_generation_requests])
    approval_queue = build_approval_queue([request.scene_id for request in scene_generation_requests])
    editorial_timeline = build_editorial_timeline(
        director_output.project_id,
        [request.scene_id for request in scene_generation_requests],
        [request.model_dump() for request in scene_generation_requests],
    )

    scene_root = scene_bundle_root(director_output.project_id)
    review_root = review_artifact_root(director_output.project_id)
    manifest = {
        "director_output": director_output.model_dump(),
        "sequence_plan": sequence_plan,
        "shot_plan": [shot.model_dump() for shot in shot_plan],
        "continuity_contract": continuity_contract,
        "actor_identity": actor_identity.model_dump(),
        "face_lock": face_lock,
        "anatomy_guard": anatomy_guard,
        "costume_continuity": costume_continuity,
        "environment_contract": environment_contract.model_dump(),
        "lighting_map": lighting_map,
        "horizon_lock": horizon_lock,
        "weather_time": weather_time,
        "camera_language": [shot.model_dump() for shot in camera_language],
        "blocking_plan": [beat.model_dump() for beat in blocking_plan],
        "gesture_map": gesture_map,
        "eye_line_map": eye_line_map,
        "cta_choreography": cta_choreography,
        "refinement_plan": refinement_plan,
        "temporal_consistency": temporal_consistency,
        "upscale_plan": upscale_plan,
        "operation_profile": {
            "duration_seconds": 60,
            "frames_per_second": 8,
            "required_total_frames": 480,
        },
        "sovereign_pipeline_contract": sovereign_pipeline_contract,
        "internal_runtime_policy": internal_runtime_policy,
        "self_hosted_generation_bundle": self_hosted_generation_bundle,
        "local_gpu_runtime_plan": local_gpu_runtime_plan,
        "local_shot_sequence_plan": local_shot_sequence_plan,
        "scene_generation_requests": [request.model_dump() for request in scene_generation_requests],
        "quality_result": quality_result.model_dump(),
        "self_hosted_quality_requirements": self_hosted_quality_requirements,
        "local_quality_runtime_plan": local_quality_runtime_plan,
        "review_items": [item.model_dump() for item in review_items],
        "approval_queue": approval_queue,
        "editorial_timeline": editorial_timeline.model_dump(),
        "operation_profile": {
            "duration_seconds": 60,
            "frames_per_second": 8,
            "required_total_frames": 480,
        },
    }
    write_json(scene_root / "studio_project_manifest.json", manifest)
    write_json(review_root / "studio_review_manifest.json", {
        "project_id": director_output.project_id,
        "review_items": [item.model_dump() for item in review_items],
        "approval_queue": approval_queue,
        "quality_result": quality_result.model_dump(),
        "self_hosted_quality_requirements": self_hosted_quality_requirements,
        "local_gpu_runtime_plan": local_gpu_runtime_plan,
        "local_shot_sequence_plan": local_shot_sequence_plan,
        "local_quality_runtime_plan": local_quality_runtime_plan,
    })

    return {
        "project_id": director_output.project_id,
        "scene_root": str(scene_root),
        "review_root": str(review_root),
        "director_output": director_output.model_dump(),
        "sequence_plan": sequence_plan,
        "shot_plan": [shot.model_dump() for shot in shot_plan],
        "continuity_contract": continuity_contract,
        "actor_identity": actor_identity.model_dump(),
        "environment_contract": environment_contract.model_dump(),
        "camera_language": [shot.model_dump() for shot in camera_language],
        "blocking_plan": [beat.model_dump() for beat in blocking_plan],
        "sovereign_pipeline_contract": sovereign_pipeline_contract,
        "internal_runtime_policy": internal_runtime_policy,
        "self_hosted_generation_bundle": self_hosted_generation_bundle,
        "local_gpu_runtime_plan": local_gpu_runtime_plan,
        "local_shot_sequence_plan": local_shot_sequence_plan,
        "scene_generation_requests": [request.model_dump() for request in scene_generation_requests],
        "quality_result": quality_result.model_dump(),
        "self_hosted_quality_requirements": self_hosted_quality_requirements,
        "local_quality_runtime_plan": local_quality_runtime_plan,
        "editorial_timeline": editorial_timeline.model_dump(),
        "review_items": [item.model_dump() for item in review_items],
        "approval_queue": approval_queue,
        "refinement_plan": refinement_plan,
        "temporal_consistency": temporal_consistency,
        "upscale_plan": upscale_plan,
        "operation_profile": {
            "duration_seconds": 60,
            "frames_per_second": 8,
            "required_total_frames": 480,
        },
    }


def execute_movie_studio_project(payload: Dict[str, object]) -> Dict[str, object]:
    result = build_movie_studio_project(payload)
    frames_manifest = None
    render_manifest = None
    quality_runtime_manifest = None
    quality_result = result.get("quality_result") or {}
    runtime_warning = None

    try:
        frames_manifest = run_local_shot_sequence_frames(result["local_shot_sequence_plan"])
        render_manifest = render_local_shot_sequence_video(result["local_shot_sequence_plan"], frames_manifest)
        quality_runtime_manifest = run_local_quality_gate(result["local_quality_runtime_plan"], frames_manifest)
        quality_result = quality_runtime_manifest.get("quality_result") or quality_result
    except Exception as exc:
        runtime_warning = str(exc)

    return {
        **result,
        "frames_manifest": frames_manifest,
        "render_manifest": render_manifest,
        "quality_runtime_manifest": quality_runtime_manifest,
        "quality_result": quality_result,
        "runtime_warning": runtime_warning,
        "output_mp4_path": (((render_manifest or {}).get("render_result") or {}).get("output_mp4_path")),
    }
