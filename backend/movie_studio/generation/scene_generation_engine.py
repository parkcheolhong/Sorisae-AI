from __future__ import annotations

from typing import Dict, List

from backend.movie_studio.contracts.scene_generation_contract import SceneGenerationRequestContract


MOVIE_STUDIO_OPERATION_SECONDS = 60
MOVIE_STUDIO_OPERATION_FPS = 8
MOVIE_STUDIO_OPERATION_TOTAL_FRAMES = MOVIE_STUDIO_OPERATION_SECONDS * MOVIE_STUDIO_OPERATION_FPS
MOVIE_STUDIO_CHUNK_SECONDS = 5
MOVIE_STUDIO_CHUNK_FRAMES = MOVIE_STUDIO_CHUNK_SECONDS * MOVIE_STUDIO_OPERATION_FPS


def _timeline_window(index: int, total: int) -> tuple[float, float, int, int, int]:
    del total
    start_frame = (index * MOVIE_STUDIO_CHUNK_FRAMES) + 1
    end_frame = min(MOVIE_STUDIO_OPERATION_TOTAL_FRAMES, start_frame + MOVIE_STUDIO_CHUNK_FRAMES - 1)
    frame_count = max(1, end_frame - start_frame + 1)
    start_second = round((start_frame - 1) / MOVIE_STUDIO_OPERATION_FPS, 3)
    end_second = round(end_frame / MOVIE_STUDIO_OPERATION_FPS, 3)
    return start_second, end_second, start_frame, end_frame, frame_count


def _narrative_prompt(item: Dict[str, object], index: int, total: int) -> str:
    objective = str(item.get("objective") or f"sequence {index + 1}").strip()
    emotional_state = str(item.get("emotional_state") or "controlled realism").strip()
    blocking_summary = str(item.get("blocking_summary") or "continuous actor and prop motion").strip()
    cta_required = bool(item.get("cta_required", False))
    prompt_lines = [
        f"sequence objective: {objective}",
        f"emotion: {emotional_state}",
        f"blocking: {blocking_summary}",
        "60-second cinema ad contract: every assigned frame must continue the previous frame without frozen holds or fake shake-only motion.",
        "narrative alignment rule: visuals must implement the same meaning as the scenario text, not just approximate it.",
        "continuity rule: actor, prop, lighting, horizon, camera direction, and action intent must remain temporally connected.",
    ]


def _physical_continuity_laws(index: int, total: int) -> List[str]:
    laws = [
        "momentum continuity: actor center of mass must not teleport between adjacent frames",
        "contact continuity: planted foot and hand contacts must persist until a motivated release occurs",
        "inertial camera continuity: camera acceleration must remain smooth without impulse-like shake jumps",
        "lighting continuity: key light direction and shadow flow must stay temporally coherent",
        "rigidity continuity: props and architectural lines must preserve stable geometry across time",
    ]
    if index > 0:
        laws.append("handoff continuity: incoming pose, gaze, and prop state must inherit from the previous chunk")
    if index == total - 1:
        laws.append("terminal continuity: final pose must settle with physically plausible deceleration")
    return laws


def _guidance_schedule(index: int, total: int) -> Dict[str, object]:
    return {
        "policy": "monotonic_increase",
        "source": "classifier-free guidance scheduler analysis + latent video diffusion practice",
        "start_guidance": 1.6 if index == 0 else 1.8,
        "mid_guidance": 2.1,
        "end_guidance": 2.6 if index == total - 1 else 2.4,
    }
    if cta_required or index == total - 1:
        prompt_lines.append("final progression rule: move toward conversion-ready CTA staging while keeping realistic motion continuity.")
    return " ".join(prompt_lines)


def _chunk_objective(index: int) -> str:
    if index == 0:
        return "setup and entry"
    if index == 11:
        return "final CTA and resolution"
    return f"chunk {index + 1} dramatic progression"


def _continuity_checks(index: int, total: int) -> List[str]:
    checks = [
        "hero identity must remain stable across all assigned frames",
        "prop position must progress continuously without teleport jumps",
        "camera path must move as a motivated cinematic shot instead of shake-only simulation",
        "frame-to-frame action intent must keep matching the scenario meaning",
    ]
    if index > 0:
        checks.append("opening frames must inherit motion direction and pose logic from the previous scene window")
    if index < total - 1:
        checks.append("closing frames must hand off actor, prop, and camera state to the next scene window")
    return checks


def _performance_actions(item: Dict[str, object], index: int, total: int) -> List[Dict[str, str]]:
    objective = str(item.get("objective") or f"sequence {index + 1}").strip() or f"sequence {index + 1}"
    cta_required = bool(item.get("cta_required", False)) or index == total - 1
    return [
        {
            "unit": "walking",
            "goal": f"{objective} 동안 전신 보행과 체중 이동을 유지",
            "requirement": "stride continuity and weight transfer visible",
        },
        {
            "unit": "gesture",
            "goal": f"{objective} 감정선에 맞는 손/팔 제스처 수행",
            "requirement": "gesture timing must support spoken intent",
        },
        {
            "unit": "gaze",
            "goal": "카메라, 대상물, 진행 방향 사이 시선 전환",
            "requirement": "eye tracking and head turn remain human-readable",
        },
        {
            "unit": "speech",
            "goal": "핵심 메시지를 말하는 얼굴 연기 유지",
            "requirement": "mouth articulation must match spoken performance",
        },
        {
            "unit": "cta" if cta_required else "dialogue_finish",
            "goal": "마지막 행동 의도를 분명히 전달",
            "requirement": "closing action must hand off to the next dramatic beat",
        },
    ]


def build_scene_generation_requests(
    project_id: str,
    sequence_plan: List[Dict[str, object]],
    camera_contract_ids: List[str],
    performance_contract_ids: List[List[str]],
    target_duration_seconds: int,
    target_fps: int,
    target_resolution: str,
) -> List[SceneGenerationRequestContract]:
    requests: List[SceneGenerationRequestContract] = []
    total_sequences = max(12, len(sequence_plan))
    expanded_sequence_plan: List[Dict[str, object]] = []
    for index in range(total_sequences):
        source_item = dict(sequence_plan[min(index, len(sequence_plan) - 1)] if sequence_plan else {})
        source_item.setdefault("objective", _chunk_objective(index))
        expanded_sequence_plan.append(source_item)

    for index, item in enumerate(expanded_sequence_plan):
        if item.get("narrative_prompt") is None:
            item["narrative_prompt"] = ""
        start_second, end_second, start_frame, end_frame, frame_count = _timeline_window(index, total_sequences)
        requests.append(
            SceneGenerationRequestContract(
                scene_id=f"scene-{index+1:02d}",
                sequence_id=str(item.get("sequence_id") or f"seq-{index+1:02d}"),
                chunk_index=index + 1,
                chunk_label=f"clip-{index + 1:02d}",
                director_notes=[str(item.get("objective") or "hero sequence")],
                identity_refs=[],
                environment_refs=[],
                camera_contract_id=camera_contract_ids[index] if index < len(camera_contract_ids) else camera_contract_ids[-1],
                performance_contract_ids=performance_contract_ids[index] if index < len(performance_contract_ids) else [],
                target_duration_seconds=max(1, int(round(frame_count / MOVIE_STUDIO_OPERATION_FPS))),
                target_fps=MOVIE_STUDIO_OPERATION_FPS,
                target_resolution=target_resolution,
                start_second=start_second,
                end_second=end_second,
                start_frame=start_frame,
                end_frame=end_frame,
                frame_count=frame_count,
                narrative_prompt=str(_narrative_prompt(item, index, total_sequences) or ""),
                interpolation_strategy="dual_keyframe_narrative_morph",
                continuity_checks=_continuity_checks(index, total_sequences),
                performance_actions=_performance_actions(item, index, total_sequences),
                physical_continuity_laws=_physical_continuity_laws(index, total_sequences),
                guidance_schedule=_guidance_schedule(index, total_sequences),
                carry_over_required=index > 0,
            ))
    return requests
