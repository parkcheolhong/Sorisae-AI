import backend.marketplace.local_designer_engine as local_designer_engine

from backend.marketplace.local_designer_engine import render_local_designer_sequence


def test_render_local_designer_sequence_enforces_minimum_continuity_frames_for_slow_motion():
    result = render_local_designer_sequence(
        {
            "title": "slow continuity",
            "scenario_script": "모델이 천천히 컵을 들어 올려 마시고 다시 내려놓는다.",
            "duration_seconds": 60,
            "frames_per_second": 8,
            "storyboard": [
                {
                    "title": "천천히 컵 들기",
                    "duration_sec": 60,
                    "motion_speed_percent": 80,
                    "scene_prompt": "천천히 컵을 들어 올린다.",
                }
            ],
        }
    )

    assert result["duration_seconds"] == 60
    assert result["total_frames"] >= 480
    assert result["storyboard"][0]["frame_count"] >= 480


def test_render_local_designer_sequence_rescales_storyboard_to_full_minute():
    result = render_local_designer_sequence(
        {
            "title": "minute storyboard",
            "scenario_script": "제품을 소개하고 기능을 보여준 뒤 CTA로 마무리한다.",
            "duration_seconds": 60,
            "frames_per_second": 8,
            "storyboard": [
                {
                    "title": "제품 소개",
                    "duration_sec": 10,
                    "motion_speed_percent": 100,
                    "scene_prompt": "제품을 보여준다.",
                },
                {
                    "title": "기능 시연",
                    "duration_sec": 10,
                    "motion_speed_percent": 100,
                    "scene_prompt": "기능을 보여준다.",
                },
                {
                    "title": "CTA",
                    "duration_sec": 10,
                    "motion_speed_percent": 100,
                    "scene_prompt": "행동 유도를 보여준다.",
                },
            ],
        }
    )

    assert result["duration_seconds"] == 60
    assert sum(item["duration_sec"] for item in result["storyboard"]) == 60
    assert result["total_frames"] >= 480


def test_render_local_designer_sequence_keeps_pose_continuity_between_cuts():
    result = render_local_designer_sequence(
        {
            "title": "pose continuity",
            "scenario_script": "모델이 컵을 바라본 뒤 손을 뻗어 잡고 들어 올린다.",
            "duration_seconds": 6,
            "frames_per_second": 8,
            "storyboard": [
                {"title": "시선 고정", "duration_sec": 2, "motion_speed_percent": 100, "scene_prompt": "컵을 바라본다."},
                {"title": "손 뻗기", "duration_sec": 2, "motion_speed_percent": 100, "scene_prompt": "손이 컵으로 접근한다."},
                {"title": "컵 잡기", "duration_sec": 2, "motion_speed_percent": 100, "scene_prompt": "컵 손잡이를 잡는다."},
            ],
        }
    )

    first_end = result["storyboard"][0]["pose_end"]
    second_start = result["storyboard"][1]["pose_start"]
    second_end = result["storyboard"][1]["pose_end"]

    assert first_end == second_start
    assert second_end["hand_x"] > second_start["hand_x"]


def test_render_local_designer_sequence_moves_cup_toward_mouth_before_drink():
    result = render_local_designer_sequence(
        {
            "title": "cup to mouth",
            "scenario_script": "컵을 들어 올려 입으로 가져간 뒤 마신다.",
            "duration_seconds": 6,
            "frames_per_second": 8,
            "storyboard": [
                {"title": "들어 올리기", "duration_sec": 2, "motion_speed_percent": 100, "scene_prompt": "컵을 들어 올린다."},
                {"title": "입으로 이동", "duration_sec": 2, "motion_speed_percent": 100, "scene_prompt": "컵을 입 가까이 가져간다."},
                {"title": "한 모금 마시기", "duration_sec": 2, "motion_speed_percent": 100, "scene_prompt": "컵을 마신다."},
            ],
        }
    )

    lift_end = result["storyboard"][0]["pose_end"]
    move_end = result["storyboard"][1]["pose_end"]
    drink_end = result["storyboard"][2]["pose_end"]

    assert move_end["cup_x"] < lift_end["cup_x"]
    assert drink_end["cup_y"] <= move_end["cup_y"]


def test_render_local_designer_sequence_applies_customer_pose_style_prompt():
    base = render_local_designer_sequence(
        {
            "title": "base cta",
            "scenario_script": "마지막에 브랜드 메시지를 보여준다.",
            "duration_seconds": 6,
            "frames_per_second": 8,
            "visual_style": "photorealistic",
            "storyboard": [
                {"title": "브랜드 마감", "duration_sec": 6, "motion_speed_percent": 100, "scene_prompt": "브랜드 메시지를 보여준다."},
            ],
        }
    )
    styled = render_local_designer_sequence(
        {
            "title": "styled cta",
            "scenario_script": "마지막에 브랜드 메시지를 보여준다.",
            "duration_seconds": 6,
            "frames_per_second": 8,
            "visual_style": "cinematic",
            "pose_style_prompt": "자신감 있고 활동적인 CTA 제스처, 밝은 미소",
            "storyboard": [
                {"title": "브랜드 마감", "duration_sec": 6, "motion_speed_percent": 100, "scene_prompt": "브랜드 메시지를 보여준다."},
            ],
        }
    )

    base_pose = base["storyboard"][0]["pose_end"]
    styled_pose = styled["storyboard"][0]["pose_end"]

    assert styled_pose["free_hand_x"] > base_pose["free_hand_x"]
    assert styled_pose["smile_curve"] > base_pose["smile_curve"]


def test_render_local_designer_sequence_adds_micro_motion_for_static_cut():
    result = render_local_designer_sequence(
        {
            "title": "static micro motion",
            "scenario_script": "인물이 컵을 바라본다.",
            "duration_seconds": 1,
            "frames_per_second": 8,
            "storyboard": [
                {"title": "시선 고정", "duration_sec": 1, "motion_speed_percent": 100, "scene_prompt": "컵을 바라본다."},
            ],
        }
    )

    deltas = [frame["motion_delta"] for frame in result["frames"][1:]]

    assert all(delta and delta > 0 for delta in deltas)
    assert result["average_motion_delta"] and result["average_motion_delta"] > 0.75
    assert result["static_motion_warning"] is None


def test_render_local_designer_sequence_uses_next_scene_hint_for_single_cut_preview():
    result = render_local_designer_sequence(
        {
            "title": "preview continuity",
            "scenario_script": "인물이 컵을 바라본 뒤 손을 뻗는다.",
            "duration_seconds": 1,
            "frames_per_second": 8,
            "storyboard": [
                {
                    "title": "시선 고정 · 1초 preview",
                    "duration_sec": 1,
                    "motion_speed_percent": 100,
                    "scene_prompt": "컵을 바라본다.",
                    "next_scene_title": "손 뻗기",
                    "next_scene_prompt": "손이 컵으로 접근한다.",
                    "next_scene_segment": "팔과 손이 컵으로 이동",
                },
            ],
        }
    )

    pose_end = result["storyboard"][0]["pose_end"]

    assert pose_end["hand_x"] > 280


def test_render_local_designer_sequence_embeds_render_profile_prompts():
    result = render_local_designer_sequence(
        {
            "title": "render profile",
            "scenario_script": "컵을 들어 올린다.",
            "duration_seconds": 1,
            "frames_per_second": 8,
            "lighting_preset": "cinema-rim",
            "detail_template": "film-closeup",
            "advanced_render_mode": "shadow-detail",
            "storyboard": [
                    {"title": "들어 올리기", "duration_sec": 1, "motion_speed_percent": 100},
            ],
        }
    )

    prompt = result["storyboard"][0]["designer_prompt"]
    scene_prompt = result["storyboard"][0]["scene_prompt"]

    assert "광원/그림자 프리셋" in prompt
    assert "실사 디테일 템플릿" in prompt
    assert "고급 렌더 모드" in prompt
    assert "광원 continuity" in scene_prompt
    assert result["render_profile"]["lighting_preset"] == "cinema-rim"


def test_render_local_designer_sequence_auto_motion_boost_when_static_warning(monkeypatch):
    monkeypatch.setattr(local_designer_engine, "_apply_micro_motion", lambda pose, cut, local_progress: pose)
    monkeypatch.setattr(local_designer_engine, "_pose_delta", lambda first, second: 0.0)

    result = render_local_designer_sequence(
        {
            "title": "auto boost",
            "scenario_script": "인물이 컵을 바라본다.",
            "duration_seconds": 1,
            "frames_per_second": 8,
            "auto_motion_boost": True,
            "storyboard": [
                {"title": "시선 고정", "duration_sec": 1, "motion_speed_percent": 100, "scene_prompt": "컵을 바라본다."},
            ],
        }
    )

    assert result["auto_motion_boost_applied"] is True


def test_render_local_designer_sequence_flags_stagnant_visual_run(monkeypatch):
    monkeypatch.setattr(local_designer_engine, "_frame_visual_delta_from_images", lambda previous_image, current_image: 0.0 if previous_image else 1.0)

    result = render_local_designer_sequence(
        {
            "title": "stagnant guard",
            "scenario_script": "모델이 제품을 소개하며 CTA 포즈로 유지한다.",
            "duration_seconds": 2,
            "frames_per_second": 8,
            "auto_motion_boost": False,
            "storyboard": [
                {"title": "브랜드 마감", "duration_sec": 2, "motion_speed_percent": 100, "scene_prompt": "행동 유도 포즈를 유지한다."},
            ],
        }
    )

    assert result["motion_guard_failed"] is True
    assert result["max_stagnant_run"] >= 3
    assert "정지 연속 구간 감지" in (result["static_motion_warning"] or "")


def test_render_local_designer_sequence_strengthens_cta_visual_delta():
    result = render_local_designer_sequence(
        {
            "title": "cta motion",
            "scenario_script": "모델이 마지막 10초 동안 CTA 포즈로 손짓하며 제품을 보여준다.",
            "duration_seconds": 20,
            "frames_per_second": 8,
            "storyboard": [
                {"title": "제품 소개", "duration_sec": 10, "motion_speed_percent": 100, "scene_prompt": "제품을 설명한다."},
                {"title": "브랜드 마감", "duration_sec": 10, "motion_speed_percent": 100, "scene_prompt": "CTA 포즈로 마무리한다."},
            ],
        }
    )

    cta_start_frame = result["storyboard"][1]["start_frame"]
    cta_frames = [frame for frame in result["frames"] if frame["frame_index"] >= cta_start_frame]
    cta_visual_deltas = [frame.get("visual_delta") for frame in cta_frames[1:]]

    assert cta_visual_deltas
    assert max(cta_visual_deltas) >= 0.02
    assert result["motion_guard_failed"] is False


def test_render_local_designer_sequence_applies_domain_specific_profiles():
    animal = render_local_designer_sequence(
        {
            "title": "동물형 실험",
            "scenario_script": "건강한 대형견이 해변에서 제품 옆을 따라 움직인다.",
            "duration_seconds": 6,
            "frames_per_second": 8,
            "storyboard": [
                {"title": "등장 이동", "duration_sec": 6, "motion_speed_percent": 100, "scene_prompt": "대형견이 해변에서 움직인다."},
            ],
        }
    )
    architecture = render_local_designer_sequence(
        {
            "title": "건물형 실험",
            "scenario_script": "현대적인 쇼룸 내부를 따라 카메라가 이동한다.",
            "duration_seconds": 6,
            "frames_per_second": 8,
            "storyboard": [
                {"title": "쇼룸 진입", "duration_sec": 6, "motion_speed_percent": 100, "scene_prompt": "쇼룸 내부를 따라 이동한다."},
            ],
        }
    )

    assert animal["domain_profile"]["domain_type"] == "animal"
    assert architecture["domain_profile"]["domain_type"] == "architecture"
    assert animal["storyboard"][0]["domain_type"] == "animal"
    assert architecture["storyboard"][0]["domain_type"] == "architecture"
    assert animal["storyboard"][0]["environment_prompt"] != architecture["storyboard"][0]["environment_prompt"]


def test_render_local_designer_sequence_boosts_early_mid_motion_windows():
    result = render_local_designer_sequence(
        {
            "title": "사람형 실험",
            "scenario_script": "세련된 모델이 제품을 소개하고 이동하며 마지막 10초 CTA 포즈로 마무리한다.",
            "duration_seconds": 20,
            "frames_per_second": 8,
            "storyboard": [
                {"title": "제품 소개", "duration_sec": 6, "motion_speed_percent": 100, "scene_prompt": "모델이 제품을 소개한다."},
                {"title": "이동 설명", "duration_sec": 8, "motion_speed_percent": 100, "scene_prompt": "모델이 이동하며 설명한다."},
                {"title": "브랜드 마감", "duration_sec": 6, "motion_speed_percent": 100, "scene_prompt": "마지막 CTA 포즈로 마무리한다."},
            ],
        }
    )

    first_cut_end = result["storyboard"][0]["end_frame"]
    second_cut_start = result["storyboard"][1]["start_frame"]
    second_cut_end = result["storyboard"][1]["end_frame"]
    early_deltas = [frame.get("visual_delta") for frame in result["frames"][1:first_cut_end]]
    mid_deltas = [frame.get("visual_delta") for frame in result["frames"][second_cut_start:second_cut_end]]

    assert early_deltas and mid_deltas
    assert max(early_deltas) > 0.02
    assert max(mid_deltas) > 0.05
