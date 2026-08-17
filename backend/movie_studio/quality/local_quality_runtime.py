from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Optional, Tuple

from PIL import Image, ImageChops, ImageFilter, ImageStat

from backend.movie_studio.contracts.quality_gate_contract import QualityFailureContract
from backend.movie_studio.quality.advanced_detector_runtime import (
    run_anatomy_detector,
    run_background_detector,
    run_chunk_seam_detector,
    run_face_detector,
    run_flicker_detector,
    run_gesture_performance_detector,
    run_hand_detector,
    run_shape_blur_detector,
    run_silhouette_preservation_detector,
    run_speech_lipsync_detector,
    run_walking_cycle_detector,
)
from backend.movie_studio.quality.ml_detector_runtime import (
    AnatomyPoseDetectorRunner,
    FaceEmbeddingDetectorRunner,
    FlickerFlowDetectorRunner,
    HandLandmarkDetectorRunner,
)
from backend.movie_studio.quality.self_hosted_quality_gate import (
    build_realism_failure,
    build_self_hosted_quality_result,
)
from backend.movie_studio.storage.scene_bundle_store import scene_bundle_root
from backend.movie_studio.utils.json_tools import write_json
from backend.movie_studio.utils.path_tools import ensure_directory


FACE_FIDELITY_THRESHOLD = 10.5
HAND_EDGE_THRESHOLD = 7.5
ANATOMY_STABILITY_THRESHOLD = 14.0
BACKGROUND_FLICKER_THRESHOLD = 16.0
CTA_FREEZE_THRESHOLD = 2.4
SCENARIO_PROGRESS_THRESHOLD = 0.55
WALKING_CYCLE_THRESHOLD = 18.0
GESTURE_PERFORMANCE_THRESHOLD = 14.0
SPEECH_LIPSYNC_THRESHOLD = 12.0
SILHOUETTE_THRESHOLD = 55.0
SHAPE_BLUR_THRESHOLD = 40.0
CHUNK_SEAM_THRESHOLD = 52.0

_RUNNER_LOCK = Lock()
_FACE_ML_RUNNER: Optional[FaceEmbeddingDetectorRunner] = None
_HAND_ML_RUNNER: Optional[HandLandmarkDetectorRunner] = None
_ANATOMY_ML_RUNNER: Optional[AnatomyPoseDetectorRunner] = None
_FLICKER_ML_RUNNER: Optional[FlickerFlowDetectorRunner] = None


def _get_face_ml_runner() -> FaceEmbeddingDetectorRunner:
    global _FACE_ML_RUNNER
    if _FACE_ML_RUNNER is not None:
        return _FACE_ML_RUNNER
    with _RUNNER_LOCK:
        if _FACE_ML_RUNNER is None:
            _FACE_ML_RUNNER = FaceEmbeddingDetectorRunner()
    return _FACE_ML_RUNNER


def _get_hand_ml_runner() -> HandLandmarkDetectorRunner:
    global _HAND_ML_RUNNER
    if _HAND_ML_RUNNER is not None:
        return _HAND_ML_RUNNER
    with _RUNNER_LOCK:
        if _HAND_ML_RUNNER is None:
            _HAND_ML_RUNNER = HandLandmarkDetectorRunner()
    return _HAND_ML_RUNNER


def _get_anatomy_ml_runner() -> AnatomyPoseDetectorRunner:
    global _ANATOMY_ML_RUNNER
    if _ANATOMY_ML_RUNNER is not None:
        return _ANATOMY_ML_RUNNER
    with _RUNNER_LOCK:
        if _ANATOMY_ML_RUNNER is None:
            _ANATOMY_ML_RUNNER = AnatomyPoseDetectorRunner()
    return _ANATOMY_ML_RUNNER


def _get_flicker_ml_runner() -> FlickerFlowDetectorRunner:
    global _FLICKER_ML_RUNNER
    if _FLICKER_ML_RUNNER is not None:
        return _FLICKER_ML_RUNNER
    with _RUNNER_LOCK:
        if _FLICKER_ML_RUNNER is None:
            _FLICKER_ML_RUNNER = FlickerFlowDetectorRunner()
    return _FLICKER_ML_RUNNER


def _image_mean(path: Path) -> float:
    image = Image.open(path).convert("RGB")
    stat = ImageStat.Stat(image)
    return float(sum(stat.mean) / len(stat.mean))


def _image_edge_energy(path: Path) -> float:
    image = Image.open(path).convert("L")
    edges = image.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edges)
    return float(stat.mean[0])


def _diff_mean(path_a: Path, path_b: Path) -> float:
    image_a = Image.open(path_a).convert("RGB")
    image_b = Image.open(path_b).convert("RGB")
    diff = ImageChops.difference(image_a, image_b)
    stat = ImageStat.Stat(diff)
    return float(sum(stat.mean) / len(stat.mean))


def _scene_frame_paths(frames_manifest: Dict[str, object], scene_id: str) -> List[Path]:
    return [
        Path(str(frame.get("image_path") or ""))
        for frame in list(frames_manifest.get("frames") or [])
        if str(frame.get("scene_id") or "") == scene_id and Path(str(frame.get("image_path") or "")).exists()
    ]


def _face_score(frame_paths: List[Path], keyframe_path: Path) -> float:
    if not frame_paths or not keyframe_path.exists():
        return 0.0
    baseline = _image_mean(keyframe_path)
    frame_means = [_image_mean(path) for path in frame_paths[: min(6, len(frame_paths))]]
    if not frame_means:
        return 0.0
    delta = abs((sum(frame_means) / len(frame_means)) - baseline)
    return max(0.0, 100.0 - (delta * 5.0))


def _hand_score(frame_paths: List[Path]) -> float:
    if not frame_paths:
        return 0.0
    samples = frame_paths[:: max(1, int(len(frame_paths) / 6))][:6]
    energies = [_image_edge_energy(path) for path in samples]
    return min(100.0, (sum(energies) / max(1, len(energies))) * 4.0)


def _anatomy_score(frame_paths: List[Path]) -> float:
    if len(frame_paths) < 2:
        return 0.0
    deltas = [_diff_mean(frame_paths[index], frame_paths[index + 1]) for index in range(min(5, len(frame_paths) - 1))]
    average_delta = sum(deltas) / max(1, len(deltas))
    spread = (max(deltas) - min(deltas)) if deltas else 0.0
    structural_stability = max(0.0, 100.0 - (spread * 8.0))
    motion_presence = min(100.0, average_delta * 5.5)
    if average_delta <= 2.5:
        return max(structural_stability, 92.0)
    return max(structural_stability, motion_presence)


def _background_score(frame_paths: List[Path]) -> float:
    if len(frame_paths) < 2:
        return 0.0
    samples = frame_paths[:: max(1, int(len(frame_paths) / 8))][:8]
    if len(samples) < 2:
        return 0.0
    deltas = [_diff_mean(samples[index], samples[index + 1]) for index in range(len(samples) - 1)]
    average_delta = sum(deltas) / max(1, len(deltas))
    return max(0.0, 100.0 - (average_delta * 4.0))


def _cta_freeze_score(frame_paths: List[Path]) -> float:
    if len(frame_paths) < 3:
        return 0.0
    tail = frame_paths[-min(8, len(frame_paths)):]
    deltas = [_diff_mean(tail[index], tail[index + 1]) for index in range(len(tail) - 1)]
    if not deltas:
        return 0.0
    return sum(deltas) / len(deltas)


def _scenario_progress_score(frame_paths: List[Path]) -> float:
    if len(frame_paths) < 4:
        return 0.0
    checkpoints = [frame_paths[0], frame_paths[len(frame_paths) // 2], frame_paths[-1]]
    early_mid = _diff_mean(checkpoints[0], checkpoints[1])
    mid_late = _diff_mean(checkpoints[1], checkpoints[2])
    early_late = _diff_mean(checkpoints[0], checkpoints[2])
    if early_late <= 0:
        return 0.0
    normalized = min(1.0, (early_mid + mid_late) / max(early_late, 0.001))
    return normalized


def prepare_local_quality_runtime_plan(
    project_id: str,
    payload: Dict[str, object],
    local_shot_sequence_plan: Dict[str, object],
    self_hosted_quality_requirements: Dict[str, object],
) -> Dict[str, object]:
    artifact_root = ensure_directory(scene_bundle_root(project_id) / "local_quality_runtime")
    face_reference_paths = [str(item).strip() for item in list(payload.get("identity_references") or []) if str(item).strip()]
    environment_reference_paths = [str(item).strip() for item in list(payload.get("environment_references") or []) if str(item).strip()]
    scenes = []
    for scene in list(local_shot_sequence_plan.get("scenes") or []):
        scenes.append(
            {
                "scene_id": str(scene.get("scene_id") or ""),
                "keyframe_path": str(scene.get("keyframe_path") or ""),
                "frame_start": int(scene.get("start_frame") or 1),
                "frame_end": int(scene.get("end_frame") or 1),
                "cta_required": bool(scene.get("cta_required", False)),
                "face_reference_paths": face_reference_paths,
                "environment_reference_paths": environment_reference_paths,
            }
        )
    plan = {
        "provider": "self-hosted-local-quality-runtime",
        "project_id": project_id,
        "artifact_root": str(artifact_root),
        "required_detectors": list(self_hosted_quality_requirements.get("required_detectors") or []),
        "reality_floor": str(payload.get("realism_level") or "photoreal"),
        "scene_count": len(scenes),
        "scenes": scenes,
    }
    write_json(artifact_root / "quality_runtime_plan.json", plan)
    return plan


def run_local_quality_gate(plan: Dict[str, object], frames_manifest: Dict[str, object]) -> Dict[str, object]:
    failures: List[QualityFailureContract] = []
    scene_scores: List[Dict[str, object]] = []
    for scene in list(plan.get("scenes") or []):
        scene_id = str(scene.get("scene_id") or "")
        keyframe_path = Path(str(scene.get("keyframe_path") or ""))
        frame_paths = _scene_frame_paths(frames_manifest, scene_id)
        frame_path_strings = [str(path) for path in frame_paths]
        face_reference_paths = [str(item) for item in list(scene.get("face_reference_paths") or []) if str(item).strip()]
        environment_reference_paths = [str(item) for item in list(scene.get("environment_reference_paths") or []) if str(item).strip()]
        if keyframe_path.exists() and str(keyframe_path) not in face_reference_paths:
            face_reference_paths.insert(0, str(keyframe_path))

        face_detector = run_face_detector(face_reference_paths, frame_path_strings)
        hand_detector = run_hand_detector(frame_path_strings)
        anatomy_detector = run_anatomy_detector(frame_path_strings)
        flicker_detector = run_flicker_detector(frame_path_strings)
        background_detector = run_background_detector(environment_reference_paths or face_reference_paths, frame_path_strings)
        walking_detector = run_walking_cycle_detector(frame_path_strings)
        gesture_detector = run_gesture_performance_detector(frame_path_strings)
        speech_detector = run_speech_lipsync_detector(frame_path_strings)
        silhouette_detector = run_silhouette_preservation_detector(frame_path_strings)
        blur_detector = run_shape_blur_detector(frame_path_strings)
        chunk_seam_detector = run_chunk_seam_detector(frame_path_strings)
        face_ml_detector = _get_face_ml_runner().run(reference_paths=face_reference_paths, frame_paths=frame_path_strings)
        hand_ml_detector = _get_hand_ml_runner().run(frame_paths=frame_path_strings)
        anatomy_ml_detector = _get_anatomy_ml_runner().run(frame_paths=frame_path_strings)
        flicker_ml_detector = _get_flicker_ml_runner().run(frame_paths=frame_path_strings)

        face_score = _face_score(frame_paths, keyframe_path)
        hand_score = _hand_score(frame_paths)
        anatomy_score = _anatomy_score(frame_paths)
        background_score = _background_score(frame_paths)
        cta_freeze_score = _cta_freeze_score(frame_paths) if bool(scene.get("cta_required", False)) else 100.0
        scenario_progress_score = _scenario_progress_score(frame_paths)
        walking_cycle_score = float(walking_detector.get("score") or 0.0)
        gesture_performance_score = float(gesture_detector.get("score") or 0.0)
        speech_lipsync_score = float(speech_detector.get("score") or 0.0)
        silhouette_score = float(silhouette_detector.get("score") or 0.0)
        shape_blur_score = float(blur_detector.get("score") or 0.0)
        chunk_seam_score = float(chunk_seam_detector.get("score") or 0.0)

        if face_detector.get("available"):
            face_score = max(face_score, float(face_detector.get("score") or 0.0))
        if face_ml_detector.get("available"):
            face_score = max(face_score, float(face_ml_detector.get("score") or 0.0))
        if hand_detector.get("available"):
            hand_score = max(hand_score, float(hand_detector.get("score") or 0.0))
        if hand_ml_detector.get("available"):
            hand_score = max(hand_score, float(hand_ml_detector.get("score") or 0.0))
        if anatomy_detector.get("available"):
            anatomy_score = max(anatomy_score, float(anatomy_detector.get("score") or 0.0))
        if anatomy_ml_detector.get("available"):
            anatomy_score = max(anatomy_score, float(anatomy_ml_detector.get("score") or 0.0))
        if background_detector.get("available"):
            background_score = max(background_score, float(background_detector.get("score") or 0.0))
        if flicker_detector.get("available"):
            background_score = max(background_score, float(flicker_detector.get("score") or background_score))
        if flicker_ml_detector.get("available"):
            background_score = max(background_score, float(flicker_ml_detector.get("score") or background_score))

        if face_score < FACE_FIDELITY_THRESHOLD:
            failures.append(build_realism_failure("face_drift", f"scene {scene_id} face fidelity score too low: {face_score:.2f}", scene_id))
        if hand_score < HAND_EDGE_THRESHOLD:
            failures.append(build_realism_failure("hand_collapse", f"scene {scene_id} hand integrity score too low: {hand_score:.2f}", scene_id))
        if anatomy_score < ANATOMY_STABILITY_THRESHOLD:
            failures.append(build_realism_failure("body_ratio_break", f"scene {scene_id} anatomy stability score too low: {anatomy_score:.2f}", scene_id))
        if background_score < BACKGROUND_FLICKER_THRESHOLD:
            failures.append(build_realism_failure("background_flicker", f"scene {scene_id} background continuity score too low: {background_score:.2f}", scene_id))
        if bool(scene.get("cta_required", False)) and cta_freeze_score < CTA_FREEZE_THRESHOLD:
            failures.append(build_realism_failure("freeze_like_cta", f"scene {scene_id} CTA motion score too low: {cta_freeze_score:.2f}", scene_id))
        if scenario_progress_score < SCENARIO_PROGRESS_THRESHOLD:
            failures.append(build_realism_failure("scenario_progress_break", f"scene {scene_id} scenario progression score too low: {scenario_progress_score:.2f}", scene_id))
        if walking_cycle_score < WALKING_CYCLE_THRESHOLD:
            failures.append(build_realism_failure("walking_cycle_missing", f"scene {scene_id} walking cycle score too low: {walking_cycle_score:.2f}", scene_id))
        if gesture_performance_score < GESTURE_PERFORMANCE_THRESHOLD:
            failures.append(build_realism_failure("gesture_performance_missing", f"scene {scene_id} gesture performance score too low: {gesture_performance_score:.2f}", scene_id))
        if speech_lipsync_score < SPEECH_LIPSYNC_THRESHOLD:
            failures.append(build_realism_failure("speech_lipsync_missing", f"scene {scene_id} speech lipsync score too low: {speech_lipsync_score:.2f}", scene_id))
        if silhouette_score < SILHOUETTE_THRESHOLD:
            failures.append(build_realism_failure("silhouette_collapse", f"scene {scene_id} silhouette preservation score too low: {silhouette_score:.2f}", scene_id))
        if shape_blur_score < SHAPE_BLUR_THRESHOLD:
            failures.append(build_realism_failure("shape_blur_excess", f"scene {scene_id} shape blur score too low: {shape_blur_score:.2f}", scene_id))
        if chunk_seam_score < CHUNK_SEAM_THRESHOLD:
            failures.append(build_realism_failure("chunk_seam_jump", f"scene {scene_id} chunk seam score too low: {chunk_seam_score:.2f}", scene_id))

        scene_scores.append(
            {
                "scene_id": scene_id,
                "face_score": round(face_score, 2),
                "hand_score": round(hand_score, 2),
                "anatomy_score": round(anatomy_score, 2),
                "background_score": round(background_score, 2),
                "cta_freeze_score": round(cta_freeze_score, 2),
                "scenario_progress_score": round(scenario_progress_score, 3),
                "walking_cycle_score": round(walking_cycle_score, 2),
                "gesture_performance_score": round(gesture_performance_score, 2),
                "speech_lipsync_score": round(speech_lipsync_score, 2),
                "silhouette_score": round(silhouette_score, 2),
                "shape_blur_score": round(shape_blur_score, 2),
                "chunk_seam_score": round(chunk_seam_score, 2),
                "frame_count": len(frame_paths),
                "advanced_detectors": {
                    "face": face_detector,
                    "face_ml": face_ml_detector,
                    "hand": hand_detector,
                    "hand_ml": hand_ml_detector,
                    "anatomy": anatomy_detector,
                    "anatomy_ml": anatomy_ml_detector,
                    "background": background_detector,
                    "flicker": flicker_detector,
                    "flicker_ml": flicker_ml_detector,
                    "walking": walking_detector,
                    "gesture": gesture_detector,
                    "speech": speech_detector,
                    "silhouette": silhouette_detector,
                    "shape_blur": blur_detector,
                    "chunk_seam": chunk_seam_detector,
                },
            }
        )

    if str(frames_manifest.get("provider") or "") not in {"video-diffusion-foundation-backend", "self-hosted-local-shot-sequence-runtime"}:
        failures.append(build_realism_failure("foundation_backend_required", "foundation backend did not produce the final frames", "global"))

    result = build_self_hosted_quality_result(failures)
    manifest = {
        "provider": "self-hosted-local-quality-runtime",
        "project_id": str(plan.get("project_id") or ""),
        "scene_scores": scene_scores,
        "quality_result": result.model_dump(),
    }
    artifact_root = Path(str(plan.get("artifact_root") or ""))
    write_json(artifact_root / "quality_runtime_results.json", manifest)
    return manifest
