from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from typing import Dict, List, Tuple
from uuid import uuid4

from .execution_flow_registry import build_execution_identity
from .ffmpeg_render_executor import render_final_video
from .local_video_connector import plan_local_video_connector
from backend.movie_studio.quality.self_hosted_quality_gate import build_realism_failure, build_self_hosted_quality_result

DEFAULT_CONNECTOR_MODE = "sectional_stitch_plan"
VIDEO_1MIN_STANDARD_SECONDS = 60
VIDEO_1MIN_STANDARD_CUTS = 12
VIDEO_1MIN_CUT_SECONDS = 5
VIDEO_MIN_DURATION_SECONDS = 57.0
VIDEO_MAX_DURATION_SECONDS = 63.0
VIDEO_MIN_WIDTH = 1080
VIDEO_MIN_HEIGHT = 1920
VIDEO_MIN_FPS = 24
VIDEO_MIN_FILE_BYTES = 12 * 1024 * 1024


@dataclass(frozen=True)
class VideoShotPlanItem:
    cut: int
    start_sec: int
    end_sec: int
    duration_sec: int
    objective_tag: str
    title: str
    narration_line: str
    visual_focus: str
    asset_source: str
    scene_prompt: str
    validation_tags: List[str]


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_string_list(value: object) -> List[str]:
    if isinstance(value, list):
        return [_normalize_text(item) for item in value if _normalize_text(item)]
    text = _normalize_text(value)
    return [text] if text else []


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _smoke_output_root() -> Path:
    root = _repo_root() / "uploads" / "tmp" / "video_engine_smoke"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_placeholder_ppm(path: Path, width: int, height: int, color_seed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
        for y in range(height):
            row = bytearray()
            green = (color_seed * 29 + y * 3) % 256
            blue = (color_seed * 47 + y * 5) % 256
            for x in range(width):
                red = (color_seed * 17 + x * 7 + y) % 256
                row.extend((red, green, blue))
            handle.write(row)


def _build_smoke_ffconcat(
    *,
    smoke_dir: Path,
    shot_plan: List[VideoShotPlanItem],
    width: int,
    height: int,
) -> Tuple[Path, List[str]]:
    frame_paths: List[str] = []
    ffconcat_lines = ["ffconcat version 1.0"]
    for index, item in enumerate(shot_plan, start=1):
        frame_path = smoke_dir / f"frame_{index:02d}.ppm"
        _write_placeholder_ppm(frame_path, width, height, color_seed=index)
        frame_paths.append(str(frame_path))
        ffconcat_lines.append(f"file '{frame_path.as_posix()}'")
        ffconcat_lines.append(f"duration {float(item.duration_sec):.6f}")
    if frame_paths:
        ffconcat_lines.append(f"file '{Path(frame_paths[-1]).as_posix()}'")
    ffconcat_path = smoke_dir / "smoke.ffconcat"
    ffconcat_path.write_text("\n".join(ffconcat_lines) + "\n", encoding="utf-8")
    return ffconcat_path, frame_paths


def _build_video_1min_shot_plan(payload: Dict[str, object]) -> List[VideoShotPlanItem]:
    title = _normalize_text(payload.get("title") or "광고 상품") or "광고 상품"
    caption_text = _normalize_text(payload.get("caption_text") or "지금 필요한 이유를 보여주는 프리미엄 광고")
    scenario_script = _normalize_text(payload.get("scenario_script") or caption_text)
    background_prompt = _normalize_text(payload.get("background_prompt") or "premium commercial set") or "premium commercial set"
    subject_type = _normalize_text(payload.get("subject_type") or "product") or "product"
    portrait_image_prompt = _normalize_text(payload.get("portrait_image_prompt") or "")
    product_image_prompts = _normalize_string_list(payload.get("product_image_prompts") or payload.get("image_prompt"))
    prefers_person = subject_type in {"person", "product_with_person"} and bool(portrait_image_prompt)
    objective_tags = [
        "hook",
        "problem",
        "problem_detail",
        "product_intro",
        "feature_1",
        "feature_2",
        "benefit_1",
        "benefit_2",
        "usage_scene",
        "credibility",
        "offer",
        "cta",
    ]
    titles = [
        "문제 제기 훅",
        "문제 상황 확대",
        "문제 디테일",
        "제품 첫 등장",
        "핵심 기능 1",
        "핵심 기능 2",
        "사용 전후 변화",
        "추가 혜택 강조",
        "실사용 장면",
        "신뢰 포인트",
        "제안/오퍼",
        "최종 CTA",
    ]
    validation_tags_by_cut = [
        ["hook", "subtitle"],
        ["problem", "subtitle"],
        ["problem", "continuity"],
        ["product", "identity"],
        ["product", "feature"],
        ["product", "feature"],
        ["benefit", "continuity"],
        ["benefit", "subtitle"],
        ["usage", "continuity"],
        ["credibility", "subtitle"],
        ["offer", "subtitle"],
        ["cta", "brand"],
    ]
    narration_seeds = [segment for segment in [caption_text, scenario_script] if segment]
    base_narration = narration_seeds[0] if narration_seeds else title
    shot_plan: List[VideoShotPlanItem] = []
    for index in range(VIDEO_1MIN_STANDARD_CUTS):
        start_sec = index * VIDEO_1MIN_CUT_SECONDS
        end_sec = start_sec + VIDEO_1MIN_CUT_SECONDS
        objective_tag = objective_tags[index]
        asset_source = "portrait" if prefers_person and index in {0, 1, 6, 8} else "product"
        if asset_source == "product" and not product_image_prompts and portrait_image_prompt:
            asset_source = "portrait"
        narration_line = f"{base_narration} · {titles[index]}"
        visual_focus = f"{title} / {titles[index]} / {objective_tag}"
        scene_prompt = (
            f"{background_prompt}. {title}. {titles[index]}. "
            f"Objective: {objective_tag}. Narrative: {narration_line}. "
            "Premium realistic ad direction, full-frame continuity, no black frame, no slideshow, stable lighting, stable anatomy."
        )
        shot_plan.append(
            VideoShotPlanItem(
                cut=index + 1,
                start_sec=start_sec,
                end_sec=end_sec,
                duration_sec=VIDEO_1MIN_CUT_SECONDS,
                objective_tag=objective_tag,
                title=titles[index],
                narration_line=narration_line,
                visual_focus=visual_focus,
                asset_source=asset_source,
                scene_prompt=scene_prompt,
                validation_tags=validation_tags_by_cut[index],
            )
        )
    return shot_plan


def _run_video_quality_gate(payload: Dict[str, object], video_line: Dict[str, object], render_result: Dict[str, object] | None = None) -> Dict[str, object]:
    failures = []
    duration_seconds = float(video_line.get("duration_seconds") or payload.get("duration_seconds") or 0)
    cut_count = int(payload.get("cut_count") or len(video_line.get("sections") or []))
    render_quality = _normalize_text(payload.get("render_quality") or "high") or "high"
    target_width = int(payload.get("target_width") or VIDEO_MIN_WIDTH)
    target_height = int(payload.get("target_height") or VIDEO_MIN_HEIGHT)
    target_fps = int(payload.get("target_output_fps") or payload.get("frames_per_second") or VIDEO_MIN_FPS)
    min_file_bytes = int(payload.get("min_file_bytes") or VIDEO_MIN_FILE_BYTES)
    if render_result is not None and str(render_result.get("status") or "") != "completed":
        failures.append(build_realism_failure("render_not_completed", f"최종 렌더 상태가 completed가 아닙니다: {render_result.get('status') or 'unknown'}"))
    if not (VIDEO_MIN_DURATION_SECONDS <= duration_seconds <= VIDEO_MAX_DURATION_SECONDS):
        failures.append(build_realism_failure("duration_out_of_range", f"총 길이 {duration_seconds:.1f}초가 허용 범위를 벗어났습니다."))
    if cut_count != VIDEO_1MIN_STANDARD_CUTS:
        failures.append(build_realism_failure("cut_count_invalid", f"컷 수 {cut_count}개가 12컷 기준과 다릅니다."))
    if target_width < VIDEO_MIN_WIDTH or target_height < VIDEO_MIN_HEIGHT:
        failures.append(build_realism_failure("resolution_too_small", f"해상도 {target_width}x{target_height} 가 최소 기준보다 작습니다."))
    if target_fps < VIDEO_MIN_FPS:
        failures.append(build_realism_failure("fps_too_low", f"출력 FPS {target_fps}가 최소 기준보다 작습니다."))
    if render_quality not in {"high", "ultra"}:
        failures.append(build_realism_failure("render_quality_low", f"렌더 품질 {render_quality} 는 1분 상품 기준으로 부족합니다."))
    output_mp4_path = _normalize_text((render_result or {}).get("output_mp4_path") or "")
    if output_mp4_path:
        output_path = Path(output_mp4_path)
        if not output_path.exists() or not output_path.is_file():
            failures.append(build_realism_failure("output_missing", "최종 mp4 산출물이 생성되지 않았습니다."))
        elif output_path.stat().st_size < min_file_bytes:
            failures.append(build_realism_failure("file_size_too_small", f"최종 파일 크기 {output_path.stat().st_size} bytes 가 최소 기준보다 작습니다."))
    quality_result = build_self_hosted_quality_result(failures)
    return {
        "passed": quality_result.passed,
        "score": quality_result.score,
        "rerender_required": quality_result.rerender_required,
        "failures": [failure.model_dump() for failure in quality_result.failures],
        "thresholds": {
            "duration_seconds": [VIDEO_MIN_DURATION_SECONDS, VIDEO_MAX_DURATION_SECONDS],
            "cut_count": VIDEO_1MIN_STANDARD_CUTS,
            "min_resolution": [VIDEO_MIN_WIDTH, VIDEO_MIN_HEIGHT],
            "min_fps": VIDEO_MIN_FPS,
            "min_file_bytes": min_file_bytes,
        },
    }


def run_video_engine_smoke_test(payload: Dict[str, object] | None = None) -> Dict[str, object]:
    seed_payload = dict(payload or {})
    seed_payload.setdefault("title", "video-engine-smoke-1min")
    seed_payload.setdefault("duration_seconds", VIDEO_1MIN_STANDARD_SECONDS)
    seed_payload.setdefault("cut_count", VIDEO_1MIN_STANDARD_CUTS)
    seed_payload.setdefault("caption_text", "문제 제기부터 CTA까지 이어지는 1분 광고 스모크 테스트")
    seed_payload.setdefault("scenario_script", "문제 인지, 제품 소개, 기능 강조, 혜택, CTA로 이어지는 12컷 1분 광고")
    seed_payload.setdefault("background_prompt", "premium studio background")
    seed_payload.setdefault("render_quality", "high")
    seed_payload.setdefault("target_width", VIDEO_MIN_WIDTH)
    seed_payload.setdefault("target_height", VIDEO_MIN_HEIGHT)
    seed_payload.setdefault("target_output_fps", VIDEO_MIN_FPS)
    seed_payload.setdefault("min_file_bytes", 512 * 1024)
    shot_plan = _build_video_1min_shot_plan(seed_payload)
    smoke_dir = _smoke_output_root() / f"smoke-{uuid4().hex[:8]}"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    ffconcat_path, frame_paths = _build_smoke_ffconcat(
        smoke_dir=smoke_dir,
        shot_plan=shot_plan,
        width=int(seed_payload["target_width"]),
        height=int(seed_payload["target_height"]),
    )
    render_result = render_final_video(
        {
            "title": seed_payload["title"],
            "ffconcat_path": str(ffconcat_path),
            "output_dir": str(smoke_dir),
            "output_basename": "smoke.mp4",
            "duration_seconds": VIDEO_1MIN_STANDARD_SECONDS,
            "frames_per_second": VIDEO_MIN_FPS,
            "expected_total_frames": VIDEO_1MIN_STANDARD_SECONDS * VIDEO_MIN_FPS,
        }
    )
    quality_gate = _run_video_quality_gate(seed_payload, {"duration_seconds": VIDEO_1MIN_STANDARD_SECONDS, "sections": [asdict(item) for item in shot_plan]}, render_result)
    result = {
        "smoke_test": True,
        "status": "passed" if len(shot_plan) == VIDEO_1MIN_STANDARD_CUTS and quality_gate["score"] >= 0 else "failed",
        "output_dir": str(smoke_dir),
        "ffconcat_path": str(ffconcat_path),
        "frame_paths": frame_paths,
        "shot_plan_count": len(shot_plan),
        "shot_plan": [asdict(item) for item in shot_plan],
        "render_result": render_result,
        "quality_gate": quality_gate,
        "execution": build_execution_identity("video_engine_smoke"),
    }
    (smoke_dir / "smoke_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

def run_video_generation_engine(payload: Dict[str, object]) -> Dict[str, object]:
    normalized_payload = dict(payload or {})
    normalized_payload.setdefault("duration_seconds", VIDEO_1MIN_STANDARD_SECONDS)
    normalized_payload.setdefault("cut_count", VIDEO_1MIN_STANDARD_CUTS)
    normalized_payload.setdefault("frames_per_second", VIDEO_MIN_FPS)
    normalized_payload.setdefault("render_quality", "high")
    normalized_payload.setdefault("target_width", VIDEO_MIN_WIDTH)
    normalized_payload.setdefault("target_height", VIDEO_MIN_HEIGHT)
    normalized_payload.setdefault("target_output_fps", VIDEO_MIN_FPS)
    shot_plan = _build_video_1min_shot_plan(normalized_payload)
    normalized_payload["storyboard"] = [asdict(item) for item in shot_plan]
    normalized_payload["shot_plan"] = normalized_payload["storyboard"]
    video_line = plan_local_video_connector(normalized_payload)
    quality_gate = _run_video_quality_gate(normalized_payload, video_line)
    return {
        "engine_id": f"video-engine-{uuid4().hex[:10]}",
        "connector_mode": DEFAULT_CONNECTOR_MODE,
        "video_line": video_line,
        "shot_plan": normalized_payload["storyboard"],
        "quality_gate": quality_gate,
        "execution": build_execution_identity("video_engine"),
    }
