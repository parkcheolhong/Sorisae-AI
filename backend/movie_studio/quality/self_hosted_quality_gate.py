from __future__ import annotations

from typing import Dict, Iterable, List

from backend.movie_studio.contracts.quality_gate_contract import QualityFailureContract, StudioQualityGateResultContract


REALISM_BLOCKERS = {
    "cartoon_style_detected": "critical",
    "face_drift": "critical",
    "hand_collapse": "critical",
    "body_ratio_break": "critical",
    "structure_warp": "critical",
    "background_flicker": "critical",
    "freeze_like_cta": "critical",
    "foundation_backend_required": "critical",
    "human_motion_contract_missing": "critical",
    "walking_cycle_missing": "critical",
    "gesture_performance_missing": "critical",
    "speech_lipsync_missing": "critical",
    "silhouette_collapse": "critical",
    "shape_blur_excess": "critical",
    "chunk_seam_jump": "critical",
}


def build_self_hosted_quality_requirements(payload: Dict[str, object]) -> Dict[str, object]:
    return {
        "runtime_mode": "self-hosted-vision-stack",
        "external_dependency_allowed": False,
        "required_detectors": [
            "face-consistency-detector",
            "hand-anatomy-detector",
            "body-ratio-detector",
            "environment-structure-detector",
            "temporal-flicker-detector",
            "silhouette-preservation-detector",
            "shape-blur-detector",
            "chunk-seam-detector",
            "cta-freeze-detector",
            "walking-cycle-detector",
            "gesture-performance-detector",
            "speech-lipsync-detector",
        ],
        "reality_floor": str(payload.get("realism_level") or "photoreal"),
        "hard_fail_codes": list(REALISM_BLOCKERS.keys()),
    }


def build_self_hosted_quality_result(failures: Iterable[QualityFailureContract]) -> StudioQualityGateResultContract:
    failure_list: List[QualityFailureContract] = list(failures)
    passed = not failure_list
    score = 100.0 if passed else max(0.0, 100.0 - (len(failure_list) * 18.0))
    return StudioQualityGateResultContract(
        passed=passed,
        score=score,
        failures=failure_list,
        rerender_required=not passed,
    )


def build_realism_failure(code: str, message: str, frame_range: str = "scene") -> QualityFailureContract:
    return QualityFailureContract(
        code=code,
        message=message,
        frame_range=frame_range,
        severity=REALISM_BLOCKERS.get(code, "high"),
    )
