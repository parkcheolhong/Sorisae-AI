from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from backend.time_utils import utcnow
from base64 import b64encode
from html import escape
from io import BytesIO
from pathlib import Path
import math
import re
from typing import Dict, List, Optional
from uuid import uuid4

from PIL import Image, ImageChops, ImageDraw, ImageFont

from .execution_flow_registry import build_execution_identity

MIN_CONTINUITY_IMAGES_PER_SECOND = 8
MID_LATE_MIN_VISUAL_DELTA = 0.012
CTA_MIN_VISUAL_DELTA = 0.02
STAGNANT_VISUAL_DELTA_THRESHOLD = 0.01
MAX_STAGNANT_VISUAL_DELTA_RUN = 3

TITLE_FONT = ImageFont.load_default()
BODY_FONT = ImageFont.load_default()
SMALL_FONT = ImageFont.load_default()
_TEXT_MEASURE_DRAW = ImageDraw.Draw(Image.new("RGB", (1, 1), "black"))
_WRAP_TEXT_CACHE: Dict[tuple[str, str, int], List[str]] = {}


@dataclass(frozen=True)
class ActionRule:
    pattern: re.Pattern[str]
    title: str
    phrase: str
    speed_percent: int


@dataclass(frozen=True)
class PoseState:
    hand_x: float
    hand_y: float
    cup_x: float
    cup_y: float
    eye_shift: float
    smile_curve: float
    body_tilt: float
    free_hand_x: float
    free_hand_y: float


@dataclass(frozen=True)
class PoseStyleProfile:
    hand_reach_scale: float
    cup_raise_scale: float
    smile_bias: float
    body_tilt_bias: float
    cta_gesture_scale: float
    free_hand_lift_bias: float


@dataclass(frozen=True)
class RenderPromptProfile:
    visual_style: str
    lighting_preset: str
    detail_template: str
    advanced_render_mode: str
    auto_motion_boost: bool
    lighting_prompt: str
    detail_prompt: str
    mode_prompt: str


@dataclass(frozen=True)
class DomainProfile:
    domain_type: str
    environment_label: str
    environment_prompt: str
    movement_boost: float
    pose_style_keywords: str
    background_palette: List[str]


ACTION_RULES: List[ActionRule] = [
    ActionRule(re.compile(r"가서|가고|가다|향하|도착|들어가"), "이동", "이동하는 장면", 100),
    ActionRule(re.compile(r"잡|쥐|집어|붙잡"), "잡기", "잡는 장면", 95),
    ActionRule(re.compile(r"들|들어 올|lift|raise"), "들어 올리기", "들어 올리는 장면", 90),
    ActionRule(re.compile(r"놓|내려놓|drop|set down"), "내려놓기", "내려놓는 장면", 85),
    ActionRule(re.compile(r"먹|시식|drink|sip"), "먹기", "먹거나 마시는 장면", 88),
    ActionRule(re.compile(r"맛있|감탄|만족|행복|놀라|delicious|happy"), "맛 반응", "맛에 반응하는 장면", 92),
    ActionRule(re.compile(r"전화|통화|call|phone"), "전화하기", "전화하는 장면", 105),
    ActionRule(re.compile(r"오라고|부르|초대|invite|come"), "부르기", "상대를 부르는 장면", 110),
    ActionRule(re.compile(r"말하|대화|설명|외치|say|talk|speak"), "말하기", "말하는 장면", 102),
    ActionRule(re.compile(r"손짓|제스처|가리키|gesture|signal"), "제스처", "제스처하는 장면", 100),
    ActionRule(re.compile(r"걷|walk|move"), "이동", "걷는 장면", 100),
    ActionRule(re.compile(r"뛰|달리|run|sprint"), "달리기", "달리는 장면", 145),
    ActionRule(re.compile(r"앉|착석|sit"), "착석", "앉는 장면", 80),
    ActionRule(re.compile(r"일어나|기립|stand"), "기립", "일어나는 장면", 95),
]

KNOWN_ROLES = [
    "노인", "친구", "모델", "여성", "남성", "남자", "여자", "아주머니", "아이", "학생", "직장인", "발표자",
]

LIGHTING_PRESET_PROMPTS: Dict[str, str] = {
    "soft-window": "soft window light, realistic daylight falloff, gentle facial shadow separation, subtle contact shadow under hands and cup",
    "cinema-rim": "cinematic rim light, controlled key light, motivated shadow direction, fine silhouette separation on face, hands, and cup",
    "luxury-product": "premium product spotlight, glossy highlight control, tabletop contact shadow, refined reflective edge light",
    "noir-contrast": "high-contrast noir lighting, deep but readable shadows, strong side key, sculpted facial planes and object contour shadows",
}

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "human": ["모델", "사람", "인물", "여성", "남성", "presenter", "human", "spokesperson"],
    "animal": ["동물", "강아지", "개", "고양이", "말", "bird", "animal", "pet", "dog", "cat"],
    "architecture": ["건물", "쇼룸", "실내", "도시", "빌딩", "room", "interior", "architecture", "building", "city"],
    "nature": ["바다", "해변", "하늘", "파도", "숲", "mountain", "ocean", "sea", "nature", "beach"],
}

DOMAIN_PROFILES: Dict[str, DomainProfile] = {
    "human": DomainProfile(
        domain_type="human",
        environment_label="studio",
        environment_prompt="clean premium studio set, soft key light, stable skin tone, readable face and hands, shallow commercial depth",
        movement_boost=1.2,
        pose_style_keywords="confident human presentation, stable face direction, expressive hand gesture, readable CTA posture",
        background_palette=["#0f172a", "#1d4ed8", "#334155", "#7c3aed"],
    ),
    "animal": DomainProfile(
        domain_type="animal",
        environment_label="shoreline",
        environment_prompt="natural outdoor ground contact, stable fur silhouette, readable paws and ears, consistent horizon and shoreline",
        movement_boost=1.35,
        pose_style_keywords="animal gait continuity, head turn continuity, tail balance, paw rhythm",
        background_palette=["#0f172a", "#065f46", "#1d4ed8", "#0f766e"],
    ),
    "architecture": DomainProfile(
        domain_type="architecture",
        environment_label="showroom",
        environment_prompt="architectural perspective stability, straight vertical lines, reflective interior materials, stable camera dolly path",
        movement_boost=1.28,
        pose_style_keywords="camera-led architectural reveal, controlled perspective glide, structural continuity",
        background_palette=["#111827", "#1f2937", "#334155", "#475569"],
    ),
    "nature": DomainProfile(
        domain_type="nature",
        environment_label="ocean view",
        environment_prompt="ocean horizon continuity, natural sky light, stable wave rhythm, soft atmospheric perspective",
        movement_boost=1.32,
        pose_style_keywords="natural outdoor movement, sea-breeze gesture, scenic CTA pose, horizon stability",
        background_palette=["#0f172a", "#0369a1", "#0f766e", "#1d4ed8"],
    ),
}

DETAIL_TEMPLATE_PROMPTS: Dict[str, str] = {
    "skin-fabric": "visible skin texture, subtle fabric folds, natural wrinkle response on sleeves, realistic finger compression on object contact",
    "glass-metal": "realistic cup reflections, highlight rolloff on curved surfaces, glass and metal edge detail, shadowed reflective material response",
    "premium-commercial": "commercial-grade product detailing, precise material separation, clean shape definition, refined micro contrast, premium shadow control",
    "film-closeup": "filmic close-up texture, fine skin gradation, small shadow transitions around nose and lips, realistic depth around hands and object",
}

ADVANCED_RENDER_MODE_PROMPTS: Dict[str, str] = {
    "standard-preview": "preview-friendly render notes with clear motion readability",
    "cinematic-depth": "cinematic depth cues, layered foreground-midground-background separation, nuanced light falloff",
    "shadow-detail": "shadow-detail emphasis, soft occlusion in hand-object contact, stronger form modeling and contour readability",
    "photoreal-film": "photoreal film frame styling, realistic exposure balance, delicate highlight clipping control, tactile material presence",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _output_root() -> Path:
    root = _repo_root() / "uploads" / "tmp" / "designer_engine_runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _infer_domain_type(*values: object) -> str:
    combined = _normalize_text(" ".join(str(value or "") for value in values)).lower()
    for domain_type, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword.lower() in combined for keyword in keywords):
            return domain_type
    return "human"


def _resolve_domain_profile(*values: object) -> DomainProfile:
    domain_type = _infer_domain_type(*values)
    return DOMAIN_PROFILES.get(domain_type, DOMAIN_PROFILES["human"])


def _extract_role(segment: str) -> Optional[str]:
    text = _normalize_text(segment)
    for role in KNOWN_ROLES:
        if role in text:
            return role
    match = re.search(r"([가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+){0,2})\s*(?:이|가|은|는)", text)
    return match.group(1).strip() if match else None


def _extract_object(segment: str) -> Optional[str]:
    text = _normalize_text(segment)
    matches = list(re.finditer(r"([가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+){0,2})\s*(?:을|를)", text))
    if matches:
        return matches[-1].group(1).strip()
    return None


def _extract_target(segment: str) -> Optional[str]:
    text = _normalize_text(segment)
    match = re.search(r"([가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+){0,2})\s*(?:에게|한테|께)", text)
    return match.group(1).strip() if match else None


def _split_sentences(scenario_script: str) -> List[str]:
    normalized = _normalize_text(scenario_script)
    if not normalized:
        return []
    return [
        item.strip()
        for item in re.sub(r"\s*(그리고|그 뒤|그 후|이후|다음에|then|and then)\s+", "|", normalized, flags=re.IGNORECASE).split("|")
        for item in re.split(r"[.!?。]+", item)
        if item.strip()
    ]


def _semantic_segments(sentence: str) -> List[str]:
    normalized = _normalize_text(sentence)
    hits = []
    for rule in ACTION_RULES:
        index = normalized.find(next((m.group(0) for m in [rule.pattern.search(normalized)] if m), ""))
        if index >= 0 and rule.pattern.search(normalized):
            hits.append((index, rule))
    hits.sort(key=lambda item: item[0])
    deduped: List[ActionRule] = []
    seen_titles = set()
    for _, rule in hits:
        if rule.title in seen_titles:
            continue
        seen_titles.add(rule.title)
        deduped.append(rule)
    if len(deduped) <= 1:
        return [normalized]
    prefix = normalized[: hits[0][0]].strip() if hits else ""
    return [f"{prefix} {rule.phrase}".strip() for rule in deduped]


def _infer_rule(segment: str) -> Optional[ActionRule]:
    text = _normalize_text(segment)
    for rule in ACTION_RULES:
        if rule.pattern.search(text):
            return rule
    return None


def _infer_title(segment: str, index: int) -> str:
    rule = _infer_rule(segment)
    object_name = _extract_object(segment)
    role_name = _extract_role(segment)
    target_name = _extract_target(segment)
    if rule is None:
        return f"컷 {index + 1}"
    if rule.title in {"잡기", "들어 올리기", "내려놓기", "먹기", "맛 반응"} and object_name:
        suffix = {
            "잡기": "잡기",
            "들어 올리기": "들어 올리기",
            "내려놓기": "내려놓기",
            "먹기": "먹기",
            "맛 반응": "맛 반응",
        }[rule.title]
        return f"{object_name} {suffix}"
    if rule.title in {"전화하기", "부르기"} and target_name:
        return f"{target_name} {rule.title}"
    if role_name:
        return f"{role_name} {rule.title}"
    return rule.title


def _designer_prompt(title: str, segment: str, scenario_script: str, render_profile: RenderPromptProfile, domain_profile: DomainProfile) -> str:
    role_name = _extract_role(segment) or "인물"
    object_name = _extract_object(segment) or "핵심 객체"
    return " ".join([
        scenario_script,
        f"현재 컷: {title}.",
        f"장면 설명: {segment}.",
        f"비주얼 스타일: {render_profile.visual_style}.",
        f"도메인 환경: {domain_profile.environment_label}. {domain_profile.environment_prompt}.",
        f"광원/그림자 프리셋: {render_profile.lighting_preset}. {render_profile.lighting_prompt}.",
        f"실사 디테일 템플릿: {render_profile.detail_template}. {render_profile.detail_prompt}.",
        f"고급 렌더 모드: {render_profile.advanced_render_mode}. {render_profile.mode_prompt}.",
        "디자이너 주입 규칙: 시나리오를 읽고 사람이 실제로 이어서 하는 동작을 이미지로 직접 그려낼 것.",
        f"역할 기준: {role_name}의 몸짓, 시선, 자연 표정을 유지할 것.",
        f"객체 기준: {object_name}의 위치와 손 접촉 상태를 연속적으로 유지할 것.",
        f"도메인 포즈 규칙: {domain_profile.pose_style_keywords}.",
        "광원 방향과 그림자 형체를 컷 안에서 일관되게 유지하고, 손-컵-얼굴 접촉부의 미세 음영을 잃지 말 것.",
        "모델 제스처 허용, 자연 표정 유지, 전신 자유 모션, 포즈 반복 금지.",
    ])


def _scene_prompt(title: str, segment: str, fps: int, speed_percent: int, render_profile: RenderPromptProfile, domain_profile: DomainProfile) -> str:
    return " ".join([
        "편집/이음 전용 scene prompt.",
        f"컷 제목: {title}.",
        f"장면 요약: {segment}.",
        f"속도: {speed_percent}%.",
        f"초당 프레임 기준: {fps}장.",
        f"도메인 continuity: {domain_profile.environment_prompt}.",
        f"광원 continuity: {render_profile.lighting_prompt}.",
        f"실사 형체 continuity: {render_profile.detail_prompt}.",
        f"고급 렌더 모드 continuity: {render_profile.mode_prompt}.",
        "이 프롬프트는 그림 생성용이 아니라 인접 컷의 타이밍, 이음, 속도 연결, jump cut 방지 편집 전용이다.",
    ])


def _continuity_frame_multiplier(speed_percent: int) -> float:
    return max(1.0, max(25, min(300, int(speed_percent or 100))) / 100.0)


def _normalize_storyboard_input(
    storyboard_input: object,
    scenario_script: str,
    frames_per_second: int,
    render_profile: RenderPromptProfile,
    domain_profile: DomainProfile,
) -> List[Dict[str, object]]:
    if not isinstance(storyboard_input, list):
        return []

    normalized_storyboard: List[Dict[str, object]] = []
    second_cursor = 0.0
    frame_cursor = 0

    for index, raw_item in enumerate(storyboard_input):
        if not isinstance(raw_item, dict):
            continue

        duration_sec = max(1.0, min(60.0, float(raw_item.get("duration_sec") or 1.0)))
        speed_percent = max(25, min(300, int(raw_item.get("motion_speed_percent") or 100)))
        frame_count = max(1, int(math.ceil(duration_sec * frames_per_second * _continuity_frame_multiplier(speed_percent))))
        title = _normalize_text(str(raw_item.get("title") or f"컷 {index + 1}")) or f"컷 {index + 1}"
        visual_focus = _normalize_text(str(raw_item.get("visual_focus") or title))
        narration_line = _normalize_text(str(raw_item.get("narration_line") or visual_focus or title))
        segment = _normalize_text(
            str(raw_item.get("source_scenario") or raw_item.get("scene_prompt") or visual_focus or narration_line or title)
        )
        designer_prompt = _normalize_text(str(raw_item.get("designer_prompt") or ""))
        scene_prompt = _normalize_text(str(raw_item.get("scene_prompt") or ""))
        if not designer_prompt:
            designer_prompt = _designer_prompt(title, segment, scenario_script, render_profile, domain_profile)
        if not scene_prompt:
            scene_prompt = _scene_prompt(title, segment, frames_per_second, speed_percent, render_profile, domain_profile)

        start_sec = round(second_cursor, 3)
        end_sec = round(second_cursor + duration_sec, 3)
        normalized_storyboard.append({
            "cut": index + 1,
            "title": title,
            "segment": segment,
            "duration_sec": round(duration_sec, 3),
            "frame_count": frame_count,
            "start_frame": frame_cursor + 1,
            "end_frame": frame_cursor + frame_count,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "motion_speed_percent": speed_percent,
            "designer_prompt": designer_prompt,
            "scene_prompt": scene_prompt,
            "narration_line": narration_line,
            "visual_focus": visual_focus,
            "source_scenario": _normalize_text(str(raw_item.get("source_scenario") or scenario_script)),
            "asset_source": _normalize_text(str(raw_item.get("asset_source") or "auto")) or "auto",
            "product_index": raw_item.get("product_index"),
            "asset_ref": _normalize_text(str(raw_item.get("asset_ref") or "")),
            "domain_type": domain_profile.domain_type,
            "environment_prompt": domain_profile.environment_prompt,
            "next_scene_title": _normalize_text(str(raw_item.get("next_scene_title") or "")),
            "next_scene_prompt": _normalize_text(str(raw_item.get("next_scene_prompt") or "")),
            "next_scene_segment": _normalize_text(str(raw_item.get("next_scene_segment") or "")),
            "next_scene_narration": _normalize_text(str(raw_item.get("next_scene_narration") or "")),
        })
        second_cursor += duration_sec
        frame_cursor += frame_count

    return normalized_storyboard


def _apply_domain_pose_style(profile: PoseStyleProfile, domain_profile: DomainProfile) -> PoseStyleProfile:
    movement_boost = max(1.0, float(domain_profile.movement_boost or 1.0))
    return PoseStyleProfile(
        hand_reach_scale=min(1.7, profile.hand_reach_scale * movement_boost),
        cup_raise_scale=min(1.45, profile.cup_raise_scale * (1.0 + ((movement_boost - 1.0) * 0.6))),
        smile_bias=profile.smile_bias + (1.0 if domain_profile.domain_type == "human" else 0.4),
        body_tilt_bias=max(-0.2, min(0.26, profile.body_tilt_bias + ((movement_boost - 1.0) * 0.08))),
        cta_gesture_scale=min(1.9, profile.cta_gesture_scale * (1.0 + ((movement_boost - 1.0) * 0.9))),
        free_hand_lift_bias=max(-42.0, min(24.0, profile.free_hand_lift_bias - ((movement_boost - 1.0) * 20.0))),
    )


def _fit_storyboard_to_duration(
    storyboard: List[Dict[str, object]],
    target_duration_seconds: int,
    frames_per_second: int,
) -> List[Dict[str, object]]:
    if not storyboard:
        return storyboard

    safe_target_duration = max(1, min(60, int(target_duration_seconds or 60)))
    total_duration = sum(float(item.get("duration_sec") or 0) for item in storyboard)
    if total_duration <= 0:
        return storyboard

    ratio = safe_target_duration / total_duration
    target_total_frames = max(1, safe_target_duration * max(1, frames_per_second))
    next_storyboard: List[Dict[str, object]] = []
    frame_cursor = 0
    second_cursor = 0.0
    for index, item in enumerate(storyboard):
        speed_percent = max(25, min(300, int(item.get("motion_speed_percent") or 100)))
        if index == len(storyboard) - 1:
            duration_sec = max(1.0, round(safe_target_duration - second_cursor, 3))
        else:
            duration_sec = max(1.0, round(float(item.get("duration_sec") or 0) * ratio, 3))
        remaining_frames = max(1, target_total_frames - frame_cursor)
        if index == len(storyboard) - 1:
            frame_count = remaining_frames
        else:
            frame_count = max(
                int(round(duration_sec * max(1, frames_per_second))),
                int(math.ceil(duration_sec * MIN_CONTINUITY_IMAGES_PER_SECOND)),
            )
            frame_count = min(frame_count, max(1, remaining_frames - (len(storyboard) - index - 1)))
        start_sec = round(second_cursor, 3)
        end_sec = round(second_cursor + duration_sec, 3)
        next_storyboard.append({
            **item,
            "cut": index + 1,
            "duration_sec": duration_sec,
            "frame_count": frame_count,
            "start_frame": frame_cursor + 1,
            "end_frame": frame_cursor + frame_count,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "motion_speed_percent": speed_percent,
        })
        frame_cursor += frame_count
        second_cursor += duration_sec

    return next_storyboard


def _chunk_text_for_subtitles(text: str, duration_seconds: int, subtitle_speed: float) -> List[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    cps = max(6.0, min(15.0, 10.0 * subtitle_speed))
    max_chars = max(8, int(duration_seconds * cps / 2))
    words = normalized.split(" ")
    chunks: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = word
    if current:
        chunks.append(current)
    return chunks or [normalized]


def _subtitle_cues(storyboard: List[Dict[str, object]], subtitle_speed: float) -> List[Dict[str, object]]:
    cues: List[Dict[str, object]] = []
    for cut in storyboard:
        start_ms = int(round(float(cut["start_sec"]) * 1000))
        end_ms = int(round(float(cut["end_sec"]) * 1000))
        subtitle_seed = str(cut.get("narration_line") or cut.get("segment") or "")
        texts = _chunk_text_for_subtitles(subtitle_seed, max(1, int(math.ceil(float(cut["duration_sec"])))), subtitle_speed)
        if not texts:
            continue
        slice_ms = max(300, int((end_ms - start_ms) / max(1, len(texts))))
        for index, text in enumerate(texts):
            cue_start = start_ms + (index * slice_ms)
            cue_end = min(end_ms, cue_start + slice_ms)
            cues.append({
                "start_ms": cue_start,
                "end_ms": cue_end,
                "text": text,
                "chars_per_second": round(len(text) / max(0.2, (cue_end - cue_start) / 1000), 2),
            })
    return cues


def _allocate_frames(total_frames: int, segments: List[str]) -> List[int]:
    safe_count = max(1, len(segments))
    base = total_frames // safe_count
    remainder = total_frames % safe_count
    return [base + (1 if index < remainder else 0) for index in range(safe_count)]


def _background_color(index: int, palette: Optional[List[str]] = None) -> str:
    colors = palette or ["#0f172a", "#1d4ed8", "#065f46", "#7c2d12", "#6d28d9", "#334155"]
    return colors[index % len(colors)]


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    text = str(value or "#000000").lstrip("#")
    if len(text) != 6:
        return (0, 0, 0)
    return tuple(int(text[index:index + 2], 16) for index in (0, 2, 4))


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    del draw
    normalized = _normalize_text(text)
    if not normalized:
        return []
    font_key = "default"
    if font is TITLE_FONT:
        font_key = "title"
    elif font is BODY_FONT:
        font_key = "body"
    elif font is SMALL_FONT:
        font_key = "small"
    cache_key = (normalized, font_key, max_width)
    cached_lines = _WRAP_TEXT_CACHE.get(cache_key)
    if cached_lines is not None:
        return list(cached_lines)
    words = normalized.split(" ")
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        width = _TEXT_MEASURE_DRAW.textbbox((0, 0), candidate, font=font)[2]
        if current and width > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    _WRAP_TEXT_CACHE[cache_key] = list(lines)
    return list(lines)


def _default_pose_state() -> PoseState:
    return PoseState(
        hand_x=265.0,
        hand_y=420.0,
        cup_x=760.0,
        cup_y=400.0,
        eye_shift=0.0,
        smile_curve=6.0,
        body_tilt=0.0,
        free_hand_x=240.0,
        free_hand_y=430.0,
    )


def _resolve_pose_style_profile(
    visual_style: str | None,
    pose_style_prompt: str | None,
    motion_tempo: str | None,
) -> PoseStyleProfile:
    style_text = _normalize_text(f"{visual_style or ''} {pose_style_prompt or ''} {motion_tempo or ''}").lower()

    hand_reach_scale = 1.0
    cup_raise_scale = 1.0
    smile_bias = 0.0
    body_tilt_bias = 0.0
    cta_gesture_scale = 1.0
    free_hand_lift_bias = 0.0

    if "cinematic" in style_text or "시네마" in style_text or "dramatic" in style_text or "드라마틱" in style_text:
        hand_reach_scale += 0.08
        cup_raise_scale += 0.1
        body_tilt_bias += 0.08
        cta_gesture_scale += 0.18
    if "modern-commercial" in style_text or "commercial" in style_text or "광고" in style_text or "브랜드" in style_text:
        hand_reach_scale += 0.04
        smile_bias += 2.0
        cta_gesture_scale += 0.15
        free_hand_lift_bias -= 10.0
    if "energetic" in style_text or "power" in style_text or "스포티" in style_text or "활동적" in style_text or "dynamic" in style_text:
        hand_reach_scale += 0.18
        cup_raise_scale += 0.08
        body_tilt_bias += 0.12
        cta_gesture_scale += 0.22
        free_hand_lift_bias -= 14.0
    if "elegant" in style_text or "luxury" in style_text or "우아" in style_text or "고급" in style_text or "graceful" in style_text:
        hand_reach_scale -= 0.04
        cup_raise_scale += 0.04
        smile_bias += 1.0
        body_tilt_bias += 0.03
        free_hand_lift_bias += 6.0
    if "cute" in style_text or "playful" in style_text or "밝" in style_text or "발랄" in style_text or "friendly" in style_text:
        smile_bias += 4.0
        body_tilt_bias -= 0.05
        cta_gesture_scale += 0.1
        free_hand_lift_bias -= 20.0
    if "photorealistic" in style_text or "실사" in style_text or "realistic" in style_text:
        hand_reach_scale *= 0.98
        cup_raise_scale *= 0.98
        body_tilt_bias *= 0.6

    if "slow" in style_text or "느리" in style_text:
        hand_reach_scale *= 0.96
        cup_raise_scale *= 0.97
    if "fast" in style_text or "run" in style_text or "빠르" in style_text or "뛰" in style_text:
        hand_reach_scale *= 1.08
        cta_gesture_scale *= 1.05

    return PoseStyleProfile(
        hand_reach_scale=max(0.8, min(1.4, hand_reach_scale)),
        cup_raise_scale=max(0.85, min(1.3, cup_raise_scale)),
        smile_bias=max(-2.0, min(8.0, smile_bias)),
        body_tilt_bias=max(-0.15, min(0.2, body_tilt_bias)),
        cta_gesture_scale=max(0.85, min(1.5, cta_gesture_scale)),
        free_hand_lift_bias=max(-30.0, min(18.0, free_hand_lift_bias)),
    )


def _boost_pose_style_profile(profile: PoseStyleProfile) -> PoseStyleProfile:
    return PoseStyleProfile(
        hand_reach_scale=min(1.5, profile.hand_reach_scale + 0.08),
        cup_raise_scale=min(1.35, profile.cup_raise_scale + 0.06),
        smile_bias=min(9.0, profile.smile_bias + 0.6),
        body_tilt_bias=min(0.24, profile.body_tilt_bias + 0.03),
        cta_gesture_scale=min(1.6, profile.cta_gesture_scale + 0.1),
        free_hand_lift_bias=max(-36.0, profile.free_hand_lift_bias - 6.0),
    )


def _resolve_render_prompt_profile(payload: Dict[str, object]) -> RenderPromptProfile:
    visual_style = _normalize_text(str(payload.get("visual_style") or "photorealistic")) or "photorealistic"
    lighting_preset = _normalize_text(str(payload.get("lighting_preset") or "soft-window")) or "soft-window"
    detail_template = _normalize_text(str(payload.get("detail_template") or "premium-commercial")) or "premium-commercial"
    advanced_render_mode = _normalize_text(str(payload.get("advanced_render_mode") or "photoreal-film")) or "photoreal-film"
    auto_motion_boost = bool(payload.get("auto_motion_boost", True))
    return RenderPromptProfile(
        visual_style=visual_style,
        lighting_preset=lighting_preset,
        detail_template=detail_template,
        advanced_render_mode=advanced_render_mode,
        auto_motion_boost=auto_motion_boost,
        lighting_prompt=LIGHTING_PRESET_PROMPTS.get(lighting_preset, LIGHTING_PRESET_PROMPTS["soft-window"]),
        detail_prompt=DETAIL_TEMPLATE_PROMPTS.get(detail_template, DETAIL_TEMPLATE_PROMPTS["premium-commercial"]),
        mode_prompt=ADVANCED_RENDER_MODE_PROMPTS.get(advanced_render_mode, ADVANCED_RENDER_MODE_PROMPTS["photoreal-film"]),
    )


def _ease_in_out(value: float) -> float:
    normalized = max(0.0, min(1.0, float(value)))
    return 0.5 - (0.5 * math.cos(normalized * math.pi))


def _lerp(start: float, end: float, amount: float) -> float:
    return start + ((end - start) * amount)


def _interpolate_pose(start: PoseState, end: PoseState, amount: float) -> PoseState:
    eased = _ease_in_out(amount)
    return PoseState(
        hand_x=_lerp(start.hand_x, end.hand_x, eased),
        hand_y=_lerp(start.hand_y, end.hand_y, eased),
        cup_x=_lerp(start.cup_x, end.cup_x, eased),
        cup_y=_lerp(start.cup_y, end.cup_y, eased),
        eye_shift=_lerp(start.eye_shift, end.eye_shift, eased),
        smile_curve=_lerp(start.smile_curve, end.smile_curve, eased),
        body_tilt=_lerp(start.body_tilt, end.body_tilt, eased),
        free_hand_x=_lerp(start.free_hand_x, end.free_hand_x, eased),
        free_hand_y=_lerp(start.free_hand_y, end.free_hand_y, eased),
    )


def _pose_delta(first: PoseState, second: PoseState) -> float:
    values = (
        abs(second.hand_x - first.hand_x),
        abs(second.hand_y - first.hand_y),
        abs(second.cup_x - first.cup_x),
        abs(second.cup_y - first.cup_y),
        abs(second.eye_shift - first.eye_shift) * 4,
        abs(second.smile_curve - first.smile_curve) * 3,
        abs(second.body_tilt - first.body_tilt) * 60,
        abs(second.free_hand_x - first.free_hand_x),
        abs(second.free_hand_y - first.free_hand_y),
    )
    return round(sum(values) / len(values), 3)


def _frame_visual_delta_from_images(previous_image: Image.Image | None, current_image: Image.Image) -> float:
    if previous_image is None:
        return 1.0
    previous = previous_image if previous_image.mode == "RGB" else previous_image.convert("RGB")
    current = current_image if current_image.mode == "RGB" else current_image.convert("RGB")
    diff = ImageChops.difference(previous, current)
    histogram = diff.histogram()
    total_pixels = previous.size[0] * previous.size[1] * 3
    weighted = sum(value * (index % 256) for index, value in enumerate(histogram))
    return round(weighted / max(1, total_pixels), 4)


def _frame_visual_delta(previous_png: bytes | None, current_png: bytes) -> float:
    if not previous_png:
        return 1.0
    previous = Image.open(BytesIO(previous_png)).convert("RGB")
    current = Image.open(BytesIO(current_png)).convert("RGB")
    return _frame_visual_delta_from_images(previous, current)


def _absolute_timeline_second(cut: Dict[str, object], local_progress: float) -> float:
    start_sec = float(cut.get("start_sec") or 0.0)
    duration_sec = float(cut.get("duration_sec") or 0.0)
    return start_sec + (duration_sec * max(0.0, min(1.0, float(local_progress))))


def _is_cta_window(cut: Dict[str, object], local_progress: float) -> bool:
    end_sec = float(cut.get("end_sec") or 0.0)
    if end_sec <= 0:
        return False
    return _absolute_timeline_second(cut, local_progress) >= max(0.0, end_sec - 10.0)


def _minimum_visual_delta(cut: Dict[str, object], local_progress: float, frame_index: int, total_frames: int) -> float:
    if _is_cta_window(cut, local_progress):
        return CTA_MIN_VISUAL_DELTA
    if frame_index > int(total_frames * 0.5):
        return MID_LATE_MIN_VISUAL_DELTA
    return 0.0


def _amplify_pose_motion(
    pose: PoseState,
    cut: Dict[str, object],
    local_progress: float,
    frame_index: int,
    total_frames: int,
    attempt: int,
) -> PoseState:
    timeline_phase = frame_index / max(1, total_frames)
    cta_window = _is_cta_window(cut, local_progress)
    amplitude = 3.5 + (attempt * 2.25)
    if timeline_phase > 0.5:
        amplitude *= 1.3
    if cta_window:
        amplitude *= 2.0
    wave = math.sin((timeline_phase * math.pi * 10.0) + (attempt * 0.7))
    breath = math.cos((timeline_phase * math.pi * 6.0) + (attempt * 0.45))
    cta_push = 1.0 if cta_window else 0.0
    return PoseState(
        hand_x=pose.hand_x + (amplitude * 1.8 * wave),
        hand_y=pose.hand_y - (amplitude * (1.1 + cta_push) * breath),
        cup_x=pose.cup_x + (amplitude * (0.9 + (0.5 * cta_push)) * wave),
        cup_y=pose.cup_y - (amplitude * (0.75 + (0.65 * cta_push)) * breath),
        eye_shift=pose.eye_shift + ((1.0 + (1.4 * cta_push)) * wave),
        smile_curve=pose.smile_curve + ((0.8 + (1.8 * cta_push)) * max(0.0, wave)),
        body_tilt=pose.body_tilt + ((0.02 + (0.04 * cta_push)) * wave),
        free_hand_x=pose.free_hand_x + (amplitude * (1.25 + (1.4 * cta_push)) * breath),
        free_hand_y=pose.free_hand_y - (amplitude * (1.5 + (2.0 * cta_push)) * wave),
    )


def _next_scene_hint_text(cut: Dict[str, object]) -> str:
    return _normalize_text(
        " ".join(
            str(cut.get(key) or "")
            for key in ("next_scene_title", "next_scene_prompt", "next_scene_segment", "next_scene_narration")
        )
    ).lower()


def _blend_pose(first: PoseState, second: PoseState, amount: float) -> PoseState:
    return PoseState(
        hand_x=_lerp(first.hand_x, second.hand_x, amount),
        hand_y=_lerp(first.hand_y, second.hand_y, amount),
        cup_x=_lerp(first.cup_x, second.cup_x, amount),
        cup_y=_lerp(first.cup_y, second.cup_y, amount),
        eye_shift=_lerp(first.eye_shift, second.eye_shift, amount),
        smile_curve=_lerp(first.smile_curve, second.smile_curve, amount),
        body_tilt=_lerp(first.body_tilt, second.body_tilt, amount),
        free_hand_x=_lerp(first.free_hand_x, second.free_hand_x, amount),
        free_hand_y=_lerp(first.free_hand_y, second.free_hand_y, amount),
    )


def _pose_end_state(previous: PoseState, cut: Dict[str, object], style_profile: PoseStyleProfile) -> PoseState:
    text = _normalize_text(
        " ".join(
            str(cut.get(key) or "")
            for key in ("title", "segment", "scene_prompt", "narration_line", "visual_focus")
        )
    ).lower()
    domain_type = str(cut.get("domain_type") or "human").strip().lower()
    base_pose = PoseState(previous.hand_x, previous.hand_y, previous.cup_x, previous.cup_y, previous.eye_shift, previous.smile_curve, previous.body_tilt, previous.free_hand_x, previous.free_hand_y)
    is_static_cut = False

    if domain_type == "animal":
        if any(token in text for token in ("브랜드 마감", "cta", "마감", "반응")):
            base_pose = PoseState(520.0, 402.0, 705.0, 390.0, 9.0, 8.0 + style_profile.smile_bias, 0.16 + style_profile.body_tilt_bias, 355.0, 332.0 + style_profile.free_hand_lift_bias)
        elif any(token in text for token in ("이동", "걷", "등장")):
            base_pose = PoseState(438.0, 418.0, 740.0, 398.0, 7.0, 7.0 + style_profile.smile_bias, 0.12 + style_profile.body_tilt_bias, 320.0, 360.0 + style_profile.free_hand_lift_bias)
        else:
            base_pose = PoseState(474.0, 410.0, 720.0, 394.0, 8.0, 8.0 + style_profile.smile_bias, 0.14 + style_profile.body_tilt_bias, 338.0, 346.0 + style_profile.free_hand_lift_bias)
    elif domain_type == "architecture":
        if any(token in text for token in ("브랜드 마감", "cta", "마감")):
            base_pose = PoseState(604.0, 340.0, 760.0, 354.0, 2.0, 5.0 + style_profile.smile_bias, 0.05 + style_profile.body_tilt_bias, 488.0, 286.0 + style_profile.free_hand_lift_bias)
        else:
            base_pose = PoseState(546.0, 360.0, 780.0, 372.0, 1.0, 4.0 + style_profile.smile_bias, 0.04 + style_profile.body_tilt_bias, 438.0, 320.0 + style_profile.free_hand_lift_bias)
    elif domain_type == "nature":
        if any(token in text for token in ("브랜드 마감", "cta", "마감")):
            base_pose = PoseState(470.0, 334.0, 642.0, 360.0, 6.0, 10.0 + style_profile.smile_bias, 0.12 + style_profile.body_tilt_bias, 414.0, 268.0 + style_profile.free_hand_lift_bias)
        else:
            base_pose = PoseState(422.0, 378.0, 690.0, 384.0, 5.0, 8.0 + style_profile.smile_bias, 0.10 + style_profile.body_tilt_bias, 376.0, 318.0 + style_profile.free_hand_lift_bias)

    if domain_type == "human" and any(token in text for token in ("시선 고정", "바라보", "응시", "착석", "출발 자세")):
        base_pose = PoseState(280.0, 415.0, 760.0, 400.0, 6.0, 5.0 + style_profile.smile_bias, 0.05 + style_profile.body_tilt_bias, 242.0, 432.0 + style_profile.free_hand_lift_bias)
        is_static_cut = True
    elif domain_type == "human" and any(token in text for token in ("손 뻗기", "접근", "reach", "approach")):
        base_pose = PoseState(310.0 + (380.0 * style_profile.hand_reach_scale), 410.0, previous.cup_x, previous.cup_y, 8.0, 5.0 + style_profile.smile_bias, 0.12 + style_profile.body_tilt_bias, 250.0, 432.0 + style_profile.free_hand_lift_bias)
    elif domain_type == "human" and any(token in text for token in ("컵 잡기", "손잡이를 정확히 잡", "잡는", "grasp", "grab")):
        base_pose = PoseState(previous.cup_x + (6.0 * style_profile.hand_reach_scale), previous.cup_y + 10.0, previous.cup_x, previous.cup_y, 8.0, 6.0 + style_profile.smile_bias, 0.18 + style_profile.body_tilt_bias, 255.0, 432.0 + style_profile.free_hand_lift_bias)
    elif domain_type == "human" and any(token in text for token in ("들어 올리기", "떠오르", "lift", "raise")):
        base_pose = PoseState(310.0 + (380.0 * style_profile.hand_reach_scale), 332.0 - (16.0 * (style_profile.cup_raise_scale - 1.0)), 680.0, 400.0 - (80.0 * style_profile.cup_raise_scale), 7.0, 8.0 + style_profile.smile_bias, 0.24 + style_profile.body_tilt_bias, 260.0, 430.0 + style_profile.free_hand_lift_bias)
    elif domain_type == "human" and any(token in text for token in ("입으로 이동", "입 가까이", "mouth", "toward mouth")):
        base_pose = PoseState(520.0 - (20.0 * (style_profile.hand_reach_scale - 1.0)), 274.0 - (18.0 * (style_profile.cup_raise_scale - 1.0)), 505.0, 258.0 - (24.0 * (style_profile.cup_raise_scale - 1.0)), 2.0, 10.0 + style_profile.smile_bias, 0.28 + style_profile.body_tilt_bias, 265.0, 428.0 + style_profile.free_hand_lift_bias)
    elif domain_type == "human" and any(token in text for token in ("한 모금", "마시", "drink", "sip")):
        base_pose = PoseState(490.0 - (18.0 * (style_profile.hand_reach_scale - 1.0)), 258.0 - (20.0 * (style_profile.cup_raise_scale - 1.0)), 478.0, 244.0 - (30.0 * (style_profile.cup_raise_scale - 1.0)), 0.0, 13.0 + style_profile.smile_bias, 0.30 + style_profile.body_tilt_bias, 268.0, 426.0 + style_profile.free_hand_lift_bias)
    elif domain_type == "human" and any(token in text for token in ("내려놓기", "조심스럽게 내려", "set down", "drop")):
        base_pose = PoseState(735.0, 398.0, 760.0, 400.0, 4.0, 8.0 + style_profile.smile_bias, 0.10 + style_profile.body_tilt_bias, 290.0 + (40.0 * style_profile.cta_gesture_scale), 360.0 + style_profile.free_hand_lift_bias)
    elif domain_type == "human" and any(token in text for token in ("브랜드 마감", "마감", "cta", "미소", "smile")):
        base_pose = PoseState(450.0, 350.0, max(620.0, previous.cup_x - (80.0 * style_profile.cta_gesture_scale)), 400.0, -2.0, 15.0 + style_profile.smile_bias, -0.05 + style_profile.body_tilt_bias, 430.0 + (70.0 * style_profile.cta_gesture_scale), 320.0 + style_profile.free_hand_lift_bias)

    next_hint = _next_scene_hint_text(cut)
    if next_hint:
        hinted_cut = {
            "title": cut.get("next_scene_title") or next_hint,
            "segment": cut.get("next_scene_segment") or next_hint,
            "scene_prompt": cut.get("next_scene_prompt") or next_hint,
            "narration_line": cut.get("next_scene_narration") or next_hint,
            "visual_focus": cut.get("next_scene_segment") or next_hint,
        }
        hinted_pose = _pose_end_state(base_pose, hinted_cut, style_profile)
        blend_amount = 0.22 if is_static_cut else 0.12
        base_pose = _blend_pose(base_pose, hinted_pose, blend_amount)

    return base_pose


def _annotate_pose_timeline(storyboard: List[Dict[str, object]], style_profile: PoseStyleProfile) -> List[Dict[str, object]]:
    previous_end = _default_pose_state()
    next_storyboard: List[Dict[str, object]] = []
    for index, cut in enumerate(storyboard):
        start_pose = previous_end
        end_pose = _pose_end_state(previous_end, cut, style_profile)
        next_cut = storyboard[index + 1] if index + 1 < len(storyboard) else None
        next_storyboard.append({
            **cut,
            "pose_start": asdict(start_pose),
            "pose_end": asdict(end_pose),
            "next_scene_title": next_cut.get("title") if next_cut else cut.get("next_scene_title"),
            "next_scene_prompt": next_cut.get("scene_prompt") if next_cut else cut.get("next_scene_prompt"),
            "next_scene_segment": next_cut.get("segment") if next_cut else cut.get("next_scene_segment"),
            "next_scene_narration": next_cut.get("narration_line") if next_cut else cut.get("next_scene_narration"),
        })
        previous_end = end_pose
    return next_storyboard


def _apply_micro_motion(pose: PoseState, cut: Dict[str, object], local_progress: float) -> PoseState:
    phase = max(0.0, min(1.0, float(local_progress)))
    absolute_second = _absolute_timeline_second(cut, phase)
    is_cta_window = _is_cta_window(cut, phase)
    domain_type = str(cut.get("domain_type") or "human").strip().lower()
    text = _normalize_text(
        " ".join(str(cut.get(key) or "") for key in ("title", "segment", "scene_prompt", "visual_focus"))
    ).lower()
    subtle_amp = 1.6 if any(token in text for token in ("시선 고정", "바라보", "응시", "착석")) else 2.8
    if domain_type == "animal":
        subtle_amp *= 1.35
    elif domain_type == "architecture":
        subtle_amp *= 1.2
    elif domain_type == "nature":
        subtle_amp *= 1.28
    if absolute_second >= 30.0:
        subtle_amp *= 1.6
    if is_cta_window:
        subtle_amp *= 2.4
    breath = math.sin(phase * math.pi)
    sway = math.sin(phase * math.pi * 2)
    cta_sweep = math.sin(phase * math.pi * 3.5) if is_cta_window else 0.0
    domain_wave = math.cos((phase * math.pi * 2.5) + (0.7 if domain_type == "animal" else 0.0))
    return PoseState(
        hand_x=pose.hand_x + (subtle_amp * (0.8 * sway + (0.9 * cta_sweep) + (0.35 * domain_wave))),
        hand_y=pose.hand_y - (subtle_amp * (breath + (0.35 * cta_sweep) + (0.2 * domain_wave))),
        cup_x=pose.cup_x + (subtle_amp * (0.35 * sway + (0.5 * cta_sweep) + (0.25 * domain_wave))),
        cup_y=pose.cup_y - (subtle_amp * (0.45 * breath + (0.35 * cta_sweep) + (0.18 * domain_wave))),
        eye_shift=pose.eye_shift + (0.6 * sway) + (1.2 * cta_sweep) + (0.5 * domain_wave),
        smile_curve=pose.smile_curve + (0.8 * breath) + (1.6 * max(0.0, cta_sweep)) + (0.4 * max(0.0, domain_wave)),
        body_tilt=pose.body_tilt + (0.01 * sway) + (0.02 * cta_sweep) + (0.015 * domain_wave),
        free_hand_x=pose.free_hand_x - (subtle_amp * 0.55 * sway) + (subtle_amp * 0.85 * cta_sweep) + (subtle_amp * 0.42 * domain_wave),
        free_hand_y=pose.free_hand_y - (subtle_amp * 0.8 * breath) - (subtle_amp * 1.1 * cta_sweep) - (subtle_amp * 0.34 * domain_wave),
    )


def _pose_for_frame(cut: Dict[str, object], local_progress: float) -> PoseState:
    start_pose_raw = cut.get("pose_start") or asdict(_default_pose_state())
    end_pose_raw = cut.get("pose_end") or start_pose_raw
    start_pose = PoseState(**{key: float(start_pose_raw.get(key) or 0.0) for key in PoseState.__dataclass_fields__.keys()})
    end_pose = PoseState(**{key: float(end_pose_raw.get(key) or 0.0) for key in PoseState.__dataclass_fields__.keys()})
    return _apply_micro_motion(_interpolate_pose(start_pose, end_pose, local_progress), cut, local_progress)


def _render_frame_image(frame: Dict[str, object], cut: Dict[str, object], total_frames: int) -> Image.Image:
    width = 1280
    height = 720
    progress = float(frame["frame_index"]) / max(1, total_frames)
    local_progress = float(frame["local_progress"])
    pose_raw = frame.get("pose")
    if isinstance(pose_raw, dict):
        pose = PoseState(**{key: float(pose_raw.get(key) or 0.0) for key in PoseState.__dataclass_fields__.keys()})
    else:
        pose = _pose_for_frame(cut, local_progress)
    x_hand = int(pose.hand_x)
    y_hand = int(pose.hand_y)
    x_object = int(pose.cup_x)
    y_object = int(pose.cup_y)
    eye_offset = int(pose.eye_shift)
    smile_curve = int(pose.smile_curve)
    body_tilt = int(pose.body_tilt * 24)
    free_hand_x = int(pose.free_hand_x)
    free_hand_y = int(pose.free_hand_y)
    background = _hex_to_rgb(_background_color(int(cut["cut"]) - 1))

    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    title_font = TITLE_FONT
    body_font = BODY_FONT
    small_font = SMALL_FONT

    draw.rounded_rectangle((40, 40, 1240, 680), radius=24, outline=(203, 213, 225), width=2, fill=(255, 255, 255))
    draw.text((70, 80), str(cut.get("title") or "-"), fill=(15, 23, 42), font=title_font)
    draw.text((70, 115), f"frame {frame['frame_index']}/{total_frames} · continuity {float(frame['continuity_score']):.2f}", fill=(71, 85, 105), font=body_font)
    draw.rounded_rectangle((70, 150, 1210, 158), radius=4, fill=(226, 232, 240))
    draw.rounded_rectangle((70, 150, 70 + int(1140 * progress), 158), radius=4, fill=(34, 197, 94))

    draw.ellipse((252 + body_tilt, 232, 368 + body_tilt, 348), fill=(253, 230, 138), outline=(15, 23, 42), width=2)
    draw.ellipse((286 + eye_offset, 274, 298 + eye_offset, 286), fill=(15, 23, 42))
    draw.ellipse((322 + eye_offset, 274, 334 + eye_offset, 286), fill=(15, 23, 42))
    draw.arc((285, 305, 335, 315 + smile_curve), start=15, end=165, fill=(15, 23, 42), width=3)
    draw.line((310, 348, 310 + body_tilt, 470), fill=(248, 250, 252), width=12)
    draw.line((310, 380, x_hand, y_hand), fill=(248, 250, 252), width=10)
    draw.line((310, 380, free_hand_x, free_hand_y), fill=(248, 250, 252), width=10)
    draw.line((310 + body_tilt, 470, 250, 580), fill=(248, 250, 252), width=10)
    draw.line((310 + body_tilt, 470, 370, 580), fill=(248, 250, 252), width=10)

    draw.rounded_rectangle((x_object, y_object, x_object + 96, y_object + 120), radius=16, fill=(245, 158, 11), outline=(255, 247, 237), width=4)
    draw.rounded_rectangle((x_object + 18, y_object - 26, x_object + 78, y_object + 12), radius=12, fill=(253, 230, 138), outline=(255, 247, 237), width=3)
    draw.arc((x_object + 80, y_object + 20, x_object + 120, y_object + 90), start=270, end=90, fill=(255, 247, 237), width=4)

    text_blocks = [
        (f"narration: {cut.get('narration_line') or '-'}", (70, 600), (15, 23, 42), 1140),
        (f"focus: {cut.get('visual_focus') or '-'} · asset: {cut.get('asset_source') or 'auto'}", (70, 628), (30, 64, 175), 1140),
        (str(cut.get('segment') or '-'), (70, 656), (15, 23, 42), 1140),
        (f"designer_prompt: {cut.get('designer_prompt') or '-'}", (70, 684), (14, 116, 144), 520),
        (f"scene_prompt: {cut.get('scene_prompt') or '-'}", (650, 684), (67, 56, 202), 520),
    ]
    for text, origin, fill, max_width in text_blocks:
        y = origin[1]
        for line in _wrap_text(draw, text, small_font if origin[1] >= 684 else body_font, max_width):
            draw.text((origin[0], y), line, fill=fill, font=small_font if origin[1] >= 684 else body_font)
            y += 16

    return image


def _frame_png_bytes(frame: Dict[str, object], cut: Dict[str, object], total_frames: int, image: Image.Image | None = None) -> bytes:
    rendered_image = image if image is not None else _render_frame_image(frame, cut, total_frames)

    buffer = BytesIO()
    rendered_image.save(buffer, format="PNG", compress_level=1)
    return buffer.getvalue()


def _frame_svg(frame: Dict[str, object], cut: Dict[str, object], total_frames: int) -> str:
    width = 1280
    height = 720
    progress = float(frame["frame_index"]) / max(1, total_frames)
    local_progress = float(frame["local_progress"])
    pose_raw = frame.get("pose")
    if isinstance(pose_raw, dict):
        pose = PoseState(**{key: float(pose_raw.get(key) or 0.0) for key in PoseState.__dataclass_fields__.keys()})
    else:
        pose = _pose_for_frame(cut, local_progress)
    x_hand = int(pose.hand_x)
    y_hand = int(pose.hand_y)
    x_object = int(pose.cup_x)
    y_object = int(pose.cup_y)
    eye_offset = int(pose.eye_shift)
    smile_curve = int(pose.smile_curve)
    body_tilt = int(pose.body_tilt * 24)
    free_hand_x = int(pose.free_hand_x)
    free_hand_y = int(pose.free_hand_y)
    background = _background_color(int(cut["cut"]) - 1)
    title = escape(str(cut["title"]))
    segment = escape(str(cut["segment"]))
    designer_prompt = escape(str(cut["designer_prompt"]))
    scene_prompt = escape(str(cut["scene_prompt"]))
    narration_line = escape(str(cut.get("narration_line") or "-"))
    visual_focus = escape(str(cut.get("visual_focus") or "-"))
    asset_source = escape(str(cut.get("asset_source") or "auto"))
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
  <rect width='100%' height='100%' fill='{background}'/>
  <rect x='40' y='40' width='1200' height='640' rx='24' fill='rgba(255,255,255,0.08)' stroke='rgba(255,255,255,0.2)'/>
  <text x='70' y='95' fill='#f8fafc' font-size='34' font-family='Segoe UI, Arial'>{title}</text>
  <text x='70' y='135' fill='#cbd5e1' font-size='18' font-family='Segoe UI, Arial'>frame {frame['frame_index']}/{total_frames} · continuity {frame['continuity_score']:.2f}</text>
  <rect x='70' y='160' width='1140' height='8' rx='4' fill='rgba(255,255,255,0.15)'/>
  <rect x='70' y='160' width='{int(1140 * progress)}' height='8' rx='4' fill='#22c55e'/>

  <circle cx='{310 + body_tilt}' cy='290' r='58' fill='#fde68a'/>
  <circle cx='{292 + eye_offset}' cy='280' r='6' fill='#0f172a'/>
  <circle cx='{328 + eye_offset}' cy='280' r='6' fill='#0f172a'/>
  <path d='M285 315 Q310 {315 + smile_curve} 335 315' stroke='#0f172a' stroke-width='4' fill='none'/>
  <line x1='310' y1='348' x2='{310 + body_tilt}' y2='470' stroke='#f8fafc' stroke-width='12' stroke-linecap='round'/>
  <line x1='310' y1='380' x2='{x_hand}' y2='{y_hand}' stroke='#f8fafc' stroke-width='10' stroke-linecap='round'/>
  <line x1='310' y1='380' x2='{free_hand_x}' y2='{free_hand_y}' stroke='#f8fafc' stroke-width='10' stroke-linecap='round'/>
  <line x1='{310 + body_tilt}' y1='470' x2='250' y2='580' stroke='#f8fafc' stroke-width='10' stroke-linecap='round'/>
  <line x1='{310 + body_tilt}' y1='470' x2='370' y2='580' stroke='#f8fafc' stroke-width='10' stroke-linecap='round'/>

  <rect x='{x_object}' y='{y_object}' width='96' height='120' rx='16' fill='#f59e0b' stroke='#fff7ed' stroke-width='6'/>
  <rect x='{x_object + 18}' y='{y_object - 26}' width='60' height='38' rx='12' fill='#fde68a' stroke='#fff7ed' stroke-width='5'/>
  <path d='M{x_object + 95} {y_object + 32} Q{x_object + 126} {y_object + 58} {x_object + 95} {y_object + 80}' stroke='#fff7ed' stroke-width='6' fill='none'/>

  <text x='70' y='602' fill='#f8fafc' font-size='18' font-family='Segoe UI, Arial'>narration: {narration_line}</text>
  <text x='70' y='632' fill='#dbeafe' font-size='16' font-family='Segoe UI, Arial'>focus: {visual_focus} · asset: {asset_source}</text>
  <text x='70' y='660' fill='#f8fafc' font-size='18' font-family='Segoe UI, Arial'>{segment}</text>
  <foreignObject x='70' y='680' width='550' height='80'>
    <div xmlns='http://www.w3.org/1999/xhtml' style='color:#dbeafe;font-size:13px;font-family:Segoe UI, Arial;line-height:1.3;'>designer_prompt: {designer_prompt}</div>
  </foreignObject>
  <foreignObject x='650' y='680' width='560' height='80'>
    <div xmlns='http://www.w3.org/1999/xhtml' style='color:#e0e7ff;font-size:13px;font-family:Segoe UI, Arial;line-height:1.3;'>scene_prompt: {scene_prompt}</div>
  </foreignObject>
</svg>"""


def render_local_designer_sequence(payload: Dict[str, object]) -> Dict[str, object]:
    title = _normalize_text(str(payload.get("title") or "차 마시는 연속 장면")) or "차 마시는 연속 장면"
    scenario_script = _normalize_text(str(payload.get("scenario_script") or ""))
    duration_seconds = max(1, min(60, int(payload.get("duration_seconds") or 60)))
    frames_per_second = max(1, min(24, int(payload.get("frames_per_second") or 8)))
    subtitle_speed = max(0.5, min(2.0, float(payload.get("subtitle_speed") or 1.0)))
    render_profile = _resolve_render_prompt_profile(payload)
    domain_profile = _resolve_domain_profile(
        title,
        scenario_script,
        payload.get("background_prompt"),
        payload.get("visual_style"),
    )
    pose_style_prompt = _normalize_text(str(payload.get("pose_style_prompt") or ""))
    motion_tempo = _normalize_text(str(payload.get("motion_tempo") or ""))
    base_style_profile = _resolve_pose_style_profile(render_profile.visual_style, pose_style_prompt, motion_tempo)
    style_profile = _apply_domain_pose_style(base_style_profile, domain_profile)
    normalized_storyboard = _normalize_storyboard_input(payload.get("storyboard"), scenario_script, frames_per_second, render_profile, domain_profile)
    total_frames = 0

    sentences = _split_sentences(scenario_script) or [scenario_script]
    segments = [segment for sentence in sentences for segment in _semantic_segments(sentence)] or [scenario_script]
    frame_allocations = _allocate_frames(duration_seconds * frames_per_second, segments)

    run_id = f"designer-{utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    output_dir = _output_root() / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    base_storyboard: List[Dict[str, object]] = []
    frame_cursor = 0
    second_cursor = 0.0

    if normalized_storyboard:
        base_storyboard = _fit_storyboard_to_duration(normalized_storyboard, duration_seconds, frames_per_second)
        total_frames = sum(int(cut.get("frame_count") or 0) for cut in base_storyboard)
        duration_seconds = max(1, int(math.ceil(sum(float(cut.get("duration_sec") or 0) for cut in base_storyboard))))
    else:
        total_frames = duration_seconds * frames_per_second
        for index, segment in enumerate(segments):
            frame_count = frame_allocations[index]
            duration_sec = frame_count / frames_per_second
            rule = _infer_rule(segment)
            title_text = _infer_title(segment, index)
            speed_percent = rule.speed_percent if rule else 100
            speed_percent = max(25, min(300, int(round(speed_percent * domain_profile.movement_boost))))
            cut = {
                "cut": index + 1,
                "title": title_text,
                "segment": segment,
                "duration_sec": round(duration_sec, 3),
                "frame_count": frame_count,
                "start_frame": frame_cursor + 1,
                "end_frame": frame_cursor + frame_count,
                "start_sec": round(second_cursor, 3),
                "end_sec": round(second_cursor + duration_sec, 3),
                "motion_speed_percent": speed_percent,
                "designer_prompt": _designer_prompt(title_text, segment, scenario_script, render_profile, domain_profile),
                "scene_prompt": _scene_prompt(title_text, segment, frames_per_second, speed_percent, render_profile, domain_profile),
                "narration_line": segment,
                "visual_focus": title_text,
                "source_scenario": scenario_script,
                "asset_source": "auto",
                "product_index": None,
                "asset_ref": "",
                "domain_type": domain_profile.domain_type,
                "environment_prompt": domain_profile.environment_prompt,
            }
            base_storyboard.append(cut)
            frame_cursor += frame_count
            second_cursor += duration_sec

    def _render_once(current_style_profile: PoseStyleProfile) -> Dict[str, object]:
        storyboard = _annotate_pose_timeline(base_storyboard, current_style_profile)
        frames: List[Dict[str, object]] = []
        local_frame_cursor = 0
        motion_deltas: List[float] = []
        visual_deltas: List[float] = []
        previous_png_bytes: bytes | None = None
        previous_image: Image.Image | None = None
        stagnant_run = 0
        max_stagnant_run = 0
        for cut in storyboard:
            frame_count = int(cut["frame_count"])
            cut_title = str(cut.get("title") or f"컷 {cut.get('cut')}")
            for local_index in range(frame_count):
                frame_index = local_frame_cursor + local_index + 1
                local_progress = (local_index + 1) / max(1, frame_count)
                continuity_score = round(0.9 + (0.08 * (1 - abs(0.5 - local_progress))), 3)
                current_pose = _pose_for_frame(cut, local_progress)
                previous_pose = _pose_for_frame(cut, local_index / max(1, frame_count)) if local_index > 0 else _pose_for_frame(cut, 0)
                motion_delta = _pose_delta(previous_pose, current_pose)
                motion_deltas.append(motion_delta)
                frame = {
                    "frame_index": frame_index,
                    "cut": cut["cut"],
                    "title": cut_title,
                    "local_progress": local_progress,
                    "continuity_score": min(0.99, continuity_score),
                    "pose": asdict(current_pose),
                }
                svg_file_path = output_dir / f"frame_{frame_index:04d}.svg"
                png_file_path = output_dir / f"frame_{frame_index:04d}.png"
                rendered_image = _render_frame_image(frame, cut, total_frames)
                visual_delta = _frame_visual_delta_from_images(previous_image, rendered_image)
                minimum_visual_delta = _minimum_visual_delta(cut, local_progress, frame_index, total_frames)
                if previous_png_bytes and minimum_visual_delta > 0:
                    for attempt in range(1, 5):
                        if visual_delta >= minimum_visual_delta:
                            break
                        current_pose = _amplify_pose_motion(current_pose, cut, local_progress, frame_index, total_frames, attempt)
                        frame["pose"] = asdict(current_pose)
                        motion_delta = _pose_delta(previous_pose, current_pose)
                        rendered_image = _render_frame_image(frame, cut, total_frames)
                        visual_delta = _frame_visual_delta_from_images(previous_image, rendered_image)
                png_bytes = _frame_png_bytes(frame, cut, total_frames, image=rendered_image)
                svg_content = _frame_svg(frame, cut, total_frames)
                svg_file_path.write_text(svg_content, encoding="utf-8")
                png_file_path.write_bytes(png_bytes)
                visual_deltas.append(visual_delta)
                if previous_png_bytes and minimum_visual_delta > 0 and visual_delta < STAGNANT_VISUAL_DELTA_THRESHOLD:
                    stagnant_run += 1
                    max_stagnant_run = max(max_stagnant_run, stagnant_run)
                else:
                    stagnant_run = 0
                frames.append({
                    "frame_index": frame_index,
                    "cut": cut["cut"],
                    "title": cut_title,
                    "image_path": str(png_file_path),
                    "image_data_url": f"data:image/png;base64,{b64encode(png_bytes).decode('ascii')}",
                    "continuity_score": frame["continuity_score"],
                    "motion_delta": motion_delta,
                    "visual_delta": visual_delta,
                })
                previous_png_bytes = png_bytes
                previous_image = rendered_image
            local_frame_cursor += frame_count

        subtitle_cues = _subtitle_cues(storyboard, subtitle_speed)
        average_motion_delta = round(sum(motion_deltas) / len(motion_deltas), 3) if motion_deltas else 0.0
        average_visual_delta = round(sum(visual_deltas) / len(visual_deltas), 4) if visual_deltas else 0.0
        motion_guard_failed = max_stagnant_run >= MAX_STAGNANT_VISUAL_DELTA_RUN
        static_motion_warning = None
        if motion_guard_failed:
            static_motion_warning = (
                f"정지 연속 구간 감지: visual delta < {STAGNANT_VISUAL_DELTA_THRESHOLD:.2f} 구간이 {max_stagnant_run}프레임 연속 발생했습니다."
            )
        elif average_motion_delta < 0.75:
            static_motion_warning = "정지에 가까움: 프레임 간 차이가 매우 작습니다. 손/시선/컵 동선을 더 키우세요."
        return {
            "storyboard": storyboard,
            "frames": frames,
            "subtitle_cues": subtitle_cues,
            "average_motion_delta": average_motion_delta,
            "average_visual_delta": average_visual_delta,
            "motion_guard_failed": motion_guard_failed,
            "max_stagnant_run": max_stagnant_run,
            "static_motion_warning": static_motion_warning,
        }

    render_result = _render_once(style_profile)
    auto_motion_boost_applied = False
    if render_profile.auto_motion_boost and (render_result["static_motion_warning"] or render_result.get("motion_guard_failed")):
        render_result = _render_once(_boost_pose_style_profile(style_profile))
        auto_motion_boost_applied = True

    return {
        "run_id": run_id,
        "title": title,
        "scenario_script": scenario_script,
        "output_dir": str(output_dir),
        "duration_seconds": duration_seconds,
        "frames_per_second": frames_per_second,
        "total_frames": total_frames,
        "storyboard": render_result["storyboard"],
        "frames": render_result["frames"],
        "subtitle_cues": render_result["subtitle_cues"],
        "average_motion_delta": render_result["average_motion_delta"],
        "average_visual_delta": render_result["average_visual_delta"],
        "motion_guard_failed": render_result["motion_guard_failed"],
        "max_stagnant_run": render_result["max_stagnant_run"],
        "static_motion_warning": render_result["static_motion_warning"],
        "auto_motion_boost_applied": auto_motion_boost_applied,
        "domain_profile": {
            "domain_type": domain_profile.domain_type,
            "environment_label": domain_profile.environment_label,
            "environment_prompt": domain_profile.environment_prompt,
            "movement_boost": domain_profile.movement_boost,
        },
        "render_profile": {
            "visual_style": render_profile.visual_style,
            "lighting_preset": render_profile.lighting_preset,
            "detail_template": render_profile.detail_template,
            "advanced_render_mode": render_profile.advanced_render_mode,
            "auto_motion_boost": render_profile.auto_motion_boost,
        },
    }
