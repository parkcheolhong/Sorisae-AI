"""Phase5.8 — 소리새 AI 진화형 멀티도메인 동반자 페르소나/기억 주입 단위테스트.

핵심:
- `_friend_system_prompt` 가 관광 단일 정체성을 넘어 멀티도메인 동반자(지식/생활/감정)
  framing 을 포함한다(관광 전문성은 유지 — 회귀 방지).
- `_build_friend_messages` 가 persona_brief 를 시스템 컨텍스트로 주입하되, 비었으면
  기존 메시지 구성을 변경하지 않는다(무회귀, additive).
- persona_brief 는 방어적 상한(PERSONA_BRIEF_MAX_LEN)으로 잘린다.
실 네트워크/LLM 없이 순수 메시지 빌더만 검증한다.
"""

from backend.llm.voice_gateway import (
    PERSONA_BRIEF_MAX_LEN,
    _build_operational_failure_fallback,
    _build_friend_messages,
    _ensure_emotional_companion_response,
    _ensure_high_risk_source_disclosure,
    _ensure_on_topic_companion_response,
    _ensure_source_missing_disclosure,
    _ensure_immediate_safety_alert,
    _classify_safety_template_category,
    _resolve_safety_template_response,
    _build_gps_risk_evidence_message,
    _friend_is_place_query,
    _is_fact_sensitive_query,
    _ensure_nearby_companion_response,
    _ensure_overview_companion_response,
    _ensure_grounded_place_guidance_response,
    _extract_requested_place_count,
    _friend_should_use_fast_itinerary_path,
    _resolve_nearby_radius_km,
    _trim_friend_reply_for_speed,
    _friend_is_tourism_guide_query,
    _resolve_friend_reply_budget,
    _prefer_live_region_label,
    _redact_unverified_contacts,
    _resolve_geo_accuracy_max_m,
    _friend_system_prompt,
    _resolve_friend_reply_language,
    _sanitize_friend_reply_for_speech,
    _strip_qwen_thinking_blocks,
    _sort_grounding_rows_by_distance,
    _build_user_memory_hint,
    _append_travel_brief_categories,
    _build_fast_overview_by_country_ko,
    _extract_route_place_candidates,
    _infer_region_hint_from_query,
)
from backend.worldlinco.safety_policy import radius_risk_profile


def test_persona_prompt_is_multidomain_companion():
    prompt = _friend_system_prompt("ko")
    low = prompt.lower()
    # 멀티도메인 동반자 framing(지식/생활/감정).
    assert "close, warm friend" in low
    assert "senior-tier worldwide travel guide" in low
    assert "memory & evolution rule" in low
    assert "same evolving companion" in low
    # 관광 전문성은 유지(회귀 방지).
    assert "travel" in low


def test_persona_prompt_korean_output_lock():
    low = _friend_system_prompt("ko").lower()
    assert "output language lock" in low
    assert "korean only" in low


def test_resolve_friend_reply_language_prefers_profile_ko():
    lang = _resolve_friend_reply_language("ko", "en", 0.99, "춘천 맛집 추천해줘", 0.55)
    assert lang == "ko"


def test_resolve_friend_reply_language_allows_explicit_english_question():
    lang = _resolve_friend_reply_language("ko", "en", 0.99, "Where is the best ramen shop?", 0.55)
    assert lang == "en"


def test_strip_qwen_thinking_blocks_removes_leaked_reasoning():
    raw = "<think\nOkay, the user wants food.\n\n춘천에서는 닭갈비가 유명해."
    assert _strip_qwen_thinking_blocks(raw) == "춘천에서는 닭갈비가 유명해."


def test_sanitize_friend_reply_strips_thinking_before_markdown():
    raw = "<think\nEnglish planning only\n\n**안녕** 반가워"
    out = _sanitize_friend_reply_for_speech(raw)
    assert "planning" not in out.lower()
    assert "안녕" in out


def test_persona_prompt_strengthens_empathy_and_follow_up_flow():
    low = _friend_system_prompt("ko").lower()
    assert "companion style rule" in low
    assert "acknowledge with natural empathy" in low
    assert "follow-up question" in low
    assert "avoid robotic templates" in low


def test_persona_prompt_prioritizes_local_context_before_far_options():
    low = _friend_system_prompt("ko").lower()
    assert "local-context travel rule" in low
    assert "prioritize nearby" in low
    assert "farther highlights" in low


def test_persona_prompt_has_honesty_contract():
    """사장님 최우선 원칙: 거짓 안내 절대 금지 + 위험지/관습/예절 정직."""
    low = _friend_system_prompt("ko").lower()
    assert "honesty contract" in low
    assert "never" in low and ("fabricat" in low or "invent" in low)
    # 위험지역/법/관습/예절.
    assert "danger" in low
    assert "laws" in low or "law" in low
    assert "custom" in low or "etiquette" in low
    # 주식/시세/최신 — 검증된 데이터 없으면 수치 단정 금지.
    assert "stock" in low or "market" in low
    assert "live" in low or "authoritative" in low


def test_persona_prompt_has_language_pair_tutor():
    low = _friend_system_prompt("ko").lower()
    assert "always reply in the same language" in low
    assert "useful local phrases" in low
    assert "pronunciation" in low


def test_persona_brief_injected_as_system_when_present():
    msgs = _build_friend_messages(
        "안녕",
        "ko",
        [],
        persona_brief="[Companion memory] likes coffee.",
    )
    systems = [m for m in msgs if m["role"] == "system"]
    assert any("Companion memory" in m["content"] for m in systems)
    # 마지막은 항상 현재 user 발화.
    assert msgs[-1] == {"role": "user", "content": "안녕"}


def test_proactive_hint_injected_as_optional_system_message():
    msgs = _build_friend_messages(
        "요즘 뭐할까",
        "ko",
        [],
        proactive_hint="여행 얘기 자주 했으니 다음 일정 같이 짜보자.",
    )
    systems = [m for m in msgs if m["role"] == "system"]
    assert any("Optional proactive nudge:" in m["content"] for m in systems)


def test_no_persona_brief_keeps_baseline_messages():
    base = _build_friend_messages("안녕", "ko", [])
    # 페르소나 시스템 1개 + user 1개 = 2 (그라운딩/브리프 없음).
    assert len(base) == 2
    assert base[0]["role"] == "system"
    assert base[-1] == {"role": "user", "content": "안녕"}


def test_persona_brief_is_length_capped():
    huge = "x" * (PERSONA_BRIEF_MAX_LEN + 500)
    msgs = _build_friend_messages("hi", "en", [], persona_brief=huge)
    injected = [m for m in msgs if m["role"] == "system" and set(m["content"]) == {"x"}]
    assert injected, "brief system message should be present"
    assert len(injected[0]["content"]) == PERSONA_BRIEF_MAX_LEN


def test_history_and_grounding_order_preserved():
    msgs = _build_friend_messages(
        "지금 뭐해",
        "ko",
        [{"role": "user", "content": "이전 질문"}, {"role": "assistant", "content": "이전 답변"}],
        grounding_block="[web] fresh results",
        persona_brief="brief here",
    )
    roles = [m["role"] for m in msgs]
    # system(persona) → system(brief) → system(grounding) → user/assistant 히스토리 → user
    assert roles[0] == "system"
    assert msgs[-1]["content"] == "지금 뭐해"
    assert any("fresh results" in m["content"] for m in msgs if m["role"] == "system")
    assert any(m["content"] == "이전 답변" and m["role"] == "assistant" for m in msgs)


def test_emotional_response_is_enforced_with_empathy_and_followup_for_korean():
    out = _ensure_emotional_companion_response(
        "요즘 너무 지치고 마음이 복잡해.",
        "서울에서 산책해보면 도움될 수 있어.",
        "ko",
    )
    assert any(token in out for token in ("힘들", "지쳤", "괜찮", "버거"))
    assert "?" in out or "？" in out


def test_non_emotional_response_stays_unchanged():
    original = "명동 근처 카페 한 곳 먼저 갈래?"
    out = _ensure_emotional_companion_response(
        "명동 근처 카페 추천해줘.",
        original,
        "ko",
    )
    assert out == original


def test_nearby_response_adds_local_context_keyword_when_missing_for_korean():
    out = _ensure_nearby_companion_response(
        "여기 근처 카페 추천해줘.",
        "명동에 있는 카페 세검정이 있어요.",
        "ko",
    )
    assert any(token in out for token in ("근처", "가까", "도보", "주변"))


def test_non_nearby_response_is_not_modified():
    original = "오사카 2박 3일 일정부터 잡아볼게."
    out = _ensure_nearby_companion_response(
        "오사카 여행 코스 짜줘.",
        original,
        "ko",
    )
    assert out == original


def test_nearby_response_adds_nearby_keyword_when_missing_for_english():
    out = _ensure_nearby_companion_response(
        "Find me a pharmacy near me.",
        "There is a pharmacy east from your location.",
        "en",
    )
    low = out.lower()
    assert any(token in low for token in ("near", "nearby", "walk", "closest"))


def test_overview_response_adds_schedule_route_keywords_when_missing_for_korean():
    out = _ensure_overview_companion_response(
        "오사카 2박 3일 여행 동선 개요를 짜줘.",
        "오사카에서 주요 명소를 중심으로 여행하면 좋아.",
        "ko",
    )
    assert any(token in out for token in ("동선", "일정", "1일차", "2일차", "3일차", "코스"))


def test_overview_response_rewrites_lodging_only_answer_to_day_structure():
    out = _ensure_overview_companion_response(
        "오사카 2박 3일 여행 동선 개요를 짜줘.",
        "오사카에는 호텔과 숙박 시설이 많아요. 현대호텔이 유명해요.",
        "ko",
    )
    assert "1일차" in out and "2일차" in out and "3일차" in out
    assert any(token in out for token in ("동선", "일정", "코스"))


def test_osaka_two_night_overview_is_not_forced_to_fixed_template_anymore():
    out = _ensure_overview_companion_response(
        "오사카 2박 3일 여행 동선 개요를 짜줘.",
        "나고야 해변과 호텔 중심으로 보면 좋아요.",
        "ko",
    )
    assert "오사카 2박 3일 동선 개요" not in out
    assert "난바" not in out and "도톤보리" not in out and "오사카성" not in out
    assert any(token in out for token in ("동선", "일정", "1일차", "2일차", "3일차", "코스"))


def test_non_overview_response_is_not_modified():
    original = "근처 기준으로 보면, 명동 카페 한 곳 먼저 갈래?"
    out = _ensure_overview_companion_response(
        "여기 근처 카페 추천해줘.",
        original,
        "ko",
    )
    assert out == original


def test_place_query_rebuilds_answer_from_grounded_places_when_offtopic():
    grounding = """
[관광 지식베이스 장소 결과(오픈데이터: OSM ODbL / Wikidata CC0) — 아래 실제 장소만 사용하고 지어내지 말 것]
- 명동교자 | 주소: 서울 중구 명동10길 29 | 거리: 0.4km | 방향: 북 | 종류: restaurant
- 하이커그라운드 | 주소: 서울 중구 청계천로 40 | 거리: 0.9km | 방향: 북동 | 종류: attraction
""".strip()
    out = _ensure_grounded_place_guidance_response(
        "여기 근처 맛집이랑 관광지 추천해줘.",
        "서울은 분위기가 좋아요. 천천히 걸어보세요.",
        "ko",
        grounding,
    )
    assert "명동교자" in out
    assert any(token in out for token in ("근처", "일정", "추천"))


def test_place_query_keeps_response_when_grounded_place_already_mentioned():
    grounding = """
[Google Maps 실시간 장소 결과 — 아래 실제 장소만 사용하고 지어내지 말 것]
- Kyoto Station | 주소: Higashishiokoji Kamadonocho, Shimogyo Ward, Kyoto
""".strip()
    original = "근처라면 Kyoto Station부터 들르는 게 편해."
    out = _ensure_grounded_place_guidance_response(
        "nearby station 추천해줘",
        original,
        "ko",
        grounding,
    )
    assert out == original


def test_place_query_enforces_category_type_match_from_grounding():
    grounding = """
[Google Maps 실시간 장소 결과 — 아래 실제 장소만 사용하고 지어내지 말 것]
- Myeongdong Art Gallery | 주소: 서울 중구 ... | 종류: gallery
""".strip()
    out = _ensure_grounded_place_guidance_response(
        "명동 근처 맛집 2곳 추천해줘",
        "근처면 갤러리부터 볼래?",
        "ko",
        grounding,
    )
    assert "맛집" in out
    assert "갤러리" not in out


def test_place_query_cafe_mismatch_fallback_uses_cafe_label():
    grounding = """
[Google Maps 실시간 장소 결과 — 아래 실제 장소만 사용하고 지어내지 말 것]
- Myeongdong Art Gallery | 주소: 서울 중구 ... | 종류: gallery
""".strip()
    out = _ensure_grounded_place_guidance_response(
        "명동 근처 카페 2곳 추천해줘",
        "근처면 갤러리부터 볼래?",
        "ko",
        grounding,
    )
    assert "카페" in out
    assert "맛집" not in out
    assert "반경" in out
    assert "예:" in out


def test_place_query_enforces_requested_count_when_grounding_has_enough_items():
    grounding = """
[관광 지식베이스 장소 결과(오픈데이터: OSM ODbL / Wikidata CC0) — 아래 실제 장소만 사용하고 지어내지 말 것]
- A 식당 | 주소: 서울 | 거리: 0.3km | 방향: 북 | 종류: restaurant
- B 식당 | 주소: 서울 | 거리: 0.5km | 방향: 북동 | 종류: restaurant
- C 식당 | 주소: 서울 | 거리: 0.8km | 방향: 동 | 종류: restaurant
""".strip()
    out = _ensure_grounded_place_guidance_response(
        "명동 근처 맛집 3곳 추천해줘",
        "A 식당이 좋아.",
        "ko",
        grounding,
    )
    assert "A 식당" in out and "B 식당" in out and "C 식당" in out


def test_place_query_reports_count_shortfall_when_grounding_is_insufficient():
    grounding = """
[관광 지식베이스 장소 결과(오픈데이터: OSM ODbL / Wikidata CC0) — 아래 실제 장소만 사용하고 지어내지 말 것]
- A 식당 | 주소: 서울 | 거리: 0.3km | 방향: 북 | 종류: restaurant
""".strip()
    out = _ensure_grounded_place_guidance_response(
        "명동 근처 맛집 3곳 추천해줘",
        "A 식당이 좋아.",
        "ko",
        grounding,
    )
    assert "3곳" in out
    assert "채우지 못" in out or "부족" in out
    assert "현재 1곳" in out
    assert "반경" in out
    assert "예:" in out


def test_extract_requested_place_count_parses_korean_and_numeric_forms():
    assert _extract_requested_place_count("근처 맛집 두 곳 추천해줘") == 2
    assert _extract_requested_place_count("근처 관광지 3곳 알려줘") == 3


def test_fast_itinerary_path_is_blocked_for_nearby_place_query():
    assert not _friend_should_use_fast_itinerary_path("명동 근처 관광지 3곳 추천해줘", "ko")


def test_nearby_radius_resolution_uses_geo_policy_and_accuracy():
    cfg = {"geo_accuracy_max_m": 3000.0, "geo_accuracy_nearby_max_m": 800.0}
    radius = _resolve_nearby_radius_km("근처 맛집 추천", 30.0, cfg)
    assert radius is not None
    assert 0.3 <= radius <= 2.4


def test_overview_response_rewrites_offtopic_shopping_when_not_requested():
    out = _ensure_overview_companion_response(
        "오사카 2박 3일 일정 짜줘. 음식 중심으로",
        "1일차 도착 후 쇼핑, 2일차 시청 방문, 3일차 쇼핑 정리",
        "ko",
    )
    assert "결론:" in out
    assert "1일차" in out and "2일차" in out and "3일차" in out
    assert "목적:" in out and "이유:" in out


def test_trim_friend_reply_keeps_more_content_for_overview_queries():
    long_text = (
        "1일차는 도착 후 근거리 핵심 구간을 본다. "
        "2일차는 대표 명소를 동선으로 묶는다. "
        "3일차는 체크아웃 근처를 정리한다. "
        "각 구간은 목적과 이유를 함께 적는다. "
        "마지막으로 귀환 동선을 안내한다."
    )
    trimmed = _trim_friend_reply_for_speed(
        long_text,
        "ko",
        "오사카 2박 3일 여행 동선 개요를 짜줘",
    )
    assert "1일차" in trimmed and "2일차" in trimmed and "3일차" in trimmed
    assert "목적" in trimmed or "이유" in trimmed


def test_tourism_guide_query_detects_food_recommendation():
    assert _friend_is_tourism_guide_query("춘천 맛집 추천해줘") is True
    assert _friend_is_tourism_guide_query("안녕") is False


def test_resolve_friend_reply_budget_tier3_food_query_is_rich():
    budget = _resolve_friend_reply_budget(
        "춘천 맛집 추천해줘",
        {"tourism_guide_tier": 3, "friend_reply_max_tokens": 360, "friend_realtime_max_tokens": 280},
    )
    assert budget["is_guide_query"] is True
    assert budget["guide_depth"] == "rich"
    assert int(budget["max_tokens"]) >= 280
    assert int(budget["max_sentences"]) >= 6
    assert int(budget["max_len_ko"]) >= 700


def test_trim_friend_reply_keeps_rich_food_guide_content():
    long_text = (
        "춘천은 닭갈비와 막국수가 대표야. "
        "중앙시장 일대는 현지인 맛집이 많고 저녁에 활기가 있어. "
        "소양강 근처는 카페와 산책 동선이 좋아. "
        "숙소는 시내 중심이 이동하기 편하고, 주말엔 미리 예약하는 게 좋아. "
        "역사적으로는 춘천은 근대 문화와 예술 도시로도 유명해. "
        "막국수는 쫄깃한 면과 시원한 육수가 특징이야."
    )
    trimmed = _trim_friend_reply_for_speed(long_text, "ko", "춘천 맛집 추천해줘")
    assert len(trimmed) >= 120
    assert "막국수" in trimmed or "닭갈비" in trimmed


def test_chiang_rai_overview_includes_airport_lodging_and_distance():
    out = _ensure_overview_companion_response(
        "소리새 태국 치앙라이 여행 갈거야. 역사 문화 중심으로 2박 3일 일정 잡아줘.",
        "간단히 일정 알려줄게.",
        "ko",
    )
    assert "CEI" in out
    assert "시계탑" in out
    assert "백색사원" in out and "블루템플" in out
    assert "km" in out.lower()
    assert "1일차" in out and "2일차" in out and "3일차" in out


def test_food_marker_detects_generic_food_word():
    out = _ensure_overview_companion_response(
        "치앙라이 음식 중심으로 2박 3일 일정 짜줘",
        "짧게 안내할게",
        "ko",
    )
    assert "식문화" in out or "음식" in out


def test_fast_overview_template_selects_japan_profile_by_country_code():
    out = _build_fast_overview_by_country_ko(
        "도쿄 2박3일 일정 짜줘",
        "JP",
        "Tokyo, Japan",
    )
    assert "일본 여행" in out
    assert "1일차" in out and "2일차" in out and "3일차" in out


def test_fast_overview_template_selects_thailand_profile_by_location_hint():
    out = _build_fast_overview_by_country_ko(
        "방콕 2박3일 일정 짜줘",
        None,
        "Bangkok, Thailand",
    )
    assert "태국 여행" in out
    assert "BTS/MRT" in out


def test_fast_overview_template_selects_vietnam_profile_by_country_code():
    out = _build_fast_overview_by_country_ko(
        "하노이 2박3일 일정 짜줘",
        "VN",
        "Hanoi, Vietnam",
    )
    assert "베트남 여행" in out


def test_fast_overview_template_falls_back_to_global_profile():
    out = _build_fast_overview_by_country_ko(
        "리스본 2박3일 일정 짜줘",
        "PT",
        "Lisbon, Portugal",
    )
    assert "결론:" in out
    assert "1일차" in out and "2일차" in out and "3일차" in out


def test_offtopic_lodging_response_is_suppressed_for_food_query():
    out = _ensure_on_topic_companion_response(
        "오사카 라멘 맛집 알려줘",
        "오사카에는 호텔과 숙박 시설이 많고 현대호텔이 유명해요.",
        "ko",
    )
    assert "맛집" in out
    assert "숙소" in out or "호텔" in out


def test_offtopic_lodging_response_is_suppressed_for_attraction_query():
    out = _ensure_on_topic_companion_response(
        "도쿄 관광 명소 추천해줘",
        "도쿄에서는 호텔 특가와 숙소 예약이 가장 중요해요.",
        "ko",
    )
    assert "관광지" in out


def test_promotional_phrase_is_removed_from_on_topic_reply():
    out = _ensure_on_topic_companion_response(
        "교토 숙소 추천해줘",
        "교토역 근처 료칸이 좋아요. 지금 예약 특가 할인 중이에요.",
        "ko",
    )
    assert "특가" not in out
    assert "할인" not in out
    assert "료칸" in out


def test_fact_sensitive_query_detects_safety_and_place_intents():
    assert _is_fact_sensitive_query("오사카에서 치안 위험지역 알려줘") is True
    assert _is_fact_sensitive_query("명동 근처 맛집 추천해줘") is True
    assert _is_fact_sensitive_query("춘천에서 대마도 가려면 부산 가서 배 타야 하지? 몇 시간 걸려?") is True
    assert _is_fact_sensitive_query("오늘 기분이 너무 별로야") is False


def test_fast_itinerary_path_rejects_route_and_transit_queries():
    assert _friend_should_use_fast_itinerary_path(
        "춘천에서 대마도 가려면 부산 내려가서 배 타야 하지? 몇 시간 걸려?",
        "ko",
    ) is False


def test_infer_region_hint_extracts_actual_city_from_route_question():
    assert _infer_region_hint_from_query(
        "저기 대마도가 좋다는데 대마도를 갔다 오려면 여기 춘천에서 어떻게 가야 되지"
    ) == "춘천"


def test_extract_route_place_candidates_keeps_origin_and_destination_tokens():
    assert _extract_route_place_candidates(
        "저기 대마도가 좋다는데 대마도를 갔다 오려면 여기 춘천에서 어떻게 가야 되지"
    )[:2] == ["대마도", "춘천"]


def test_place_query_detects_tourist_attraction_category():
    assert _friend_is_place_query("도쿄 관광 명소 추천해줘") is True


def test_place_query_detects_restaurant_category():
    assert _friend_is_place_query("오사카 라멘 맛집 알려줘") is True


def test_place_query_detects_lodging_category_in_korean_and_english():
    assert _friend_is_place_query("교토 료칸 숙소 추천해줘") is True
    assert _friend_is_place_query("Find me accommodation near Kyoto station") is True
    assert _friend_is_place_query("Any hostel near Osaka castle?") is True


def test_place_query_does_not_classify_non_place_regulation_question():
    assert _friend_is_place_query("도쿄 여행 비자 규정 알려줘") is False


def test_redact_unverified_contacts_removes_unverified_address_and_hours():
    out, redacted = _redact_unverified_contacts(
        "주소: 오사카시 기타구 1-2-3 | 영업: 24시간 | 전화: 06-1234-5678",
        "ko",
        "- 장소명: 우메다역",
    )
    assert redacted is True
    assert "오사카시 기타구 1-2-3" not in out
    assert "24시간" not in out
    assert "06-1234-5678" not in out
    assert "검증된 정보만 안내" in out


def test_redact_unverified_contacts_keeps_verified_address_hours_and_phone():
    grounding = "- 우메다역 | 주소: 오사카시 기타구 1-2-3 | 영업: 24시간 | 전화: 06-1234-5678"
    original = "주소: 오사카시 기타구 1-2-3 | 영업: 24시간 | 전화: 06-1234-5678"
    out, redacted = _redact_unverified_contacts(original, "ko", grounding)
    assert redacted is False
    assert out == original


def test_redact_unverified_contacts_removes_short_hotline_numbers_when_unverified():
    out, redacted = _redact_unverified_contacts(
        "To find the latest weather, call 114 for directory help.",
        "en",
        "",
    )
    assert redacted is True
    assert "114" not in out


def test_prefer_live_region_label_overrides_stale_region_hint_when_gps_is_trustworthy():
    out = _prefer_live_region_label("Jeju, South Korea", "Osaka, Japan", geo_trustworthy=True)
    assert out == "Osaka, Japan"


def test_prefer_live_region_label_keeps_existing_hint_when_no_live_region_available():
    out = _prefer_live_region_label("Jeju, South Korea", "", geo_trustworthy=True)
    assert out == "Jeju, South Korea"


def test_source_missing_disclosure_is_forced_when_fact_sensitive_and_ungrounded():
    out, forced = _ensure_source_missing_disclosure(
        "도쿄 여행 비자 규정 알려줘",
        "현재 기준으로 안내할게.",
        "ko",
        "",
    )
    assert forced is True
    assert "공식 출처" in out or "확인" in out


def test_source_missing_disclosure_not_forced_when_grounded_or_non_fact_query():
    out_grounded, forced_grounded = _ensure_source_missing_disclosure(
        "도쿄 여행 비자 규정 알려줘",
        "공식 사이트 기준으로 안내할게.",
        "ko",
        "- 도쿄 출입국 관리청: https://example.com",
    )
    assert forced_grounded is False
    assert out_grounded == "공식 사이트 기준으로 안내할게."

    out_nonfact, forced_nonfact = _ensure_source_missing_disclosure(
        "오늘 너무 피곤해",
        "많이 지쳤겠다.",
        "ko",
        "",
    )
    assert forced_nonfact is False
    assert out_nonfact == "많이 지쳤겠다."


def test_high_risk_source_disclosure_is_forced_without_authoritative_source():
    out, forced = _ensure_high_risk_source_disclosure(
        "오사카에서 치안 위험지역 알려줘",
        "도톤보리 쪽은 밤늦게 조심하면 돼.",
        "ko",
        "- 블로그 후기: https://example.com/blog/osaka-safety\n- 커뮤니티 요약: reddit.com/r/japantravel",
    )
    assert forced is True
    assert "공식 출처" in out or "대사관" in out or "관광청" in out


def test_high_risk_source_disclosure_not_forced_with_authoritative_source():
    out, forced = _ensure_high_risk_source_disclosure(
        "도쿄 여행 비자 규정 알려줘",
        "일본 출입국재류관리청 기준으로 단기 체류 규정을 확인하면 돼.",
        "ko",
        "- 일본 출입국재류관리청: https://www.moj.go.jp/isa/\n- 주일 한국대사관: https://overseas.mofa.go.kr/jp-ko/index.do",
    )
    assert forced is False
    assert out == "일본 출입국재류관리청 기준으로 단기 체류 규정을 확인하면 돼."


def test_operational_failure_fallback_is_standardized_for_general_queries():
    out = _build_operational_failure_fallback("오늘 기분이 좀 이상해", "ko")
    assert "불안정" in out
    assert "추측" in out
    assert "다시" in out


def test_operational_failure_fallback_adds_official_source_note_for_high_risk_queries():
    out = _build_operational_failure_fallback("도쿄 여행 비자 규정 알려줘", "ko")
    assert "불안정" in out
    assert "공식 출처" in out or "대사관" in out or "관광청" in out


def test_grounding_rows_sort_near_first_for_nearby_queries():
    rows = [
        {"name": "far", "distance_km": 8.0},
        {"name": "near", "distance_km": 0.4},
        {"name": "mid", "distance_km": 2.1},
    ]
    out = _sort_grounding_rows_by_distance(rows, prefer_far_first=False)
    assert [row["name"] for row in out] == ["near", "mid", "far"]


def test_grounding_rows_sort_far_first_for_overview_queries():
    rows = [
        {"name": "far", "distance_km": 8.0},
        {"name": "near", "distance_km": 0.4},
        {"name": "mid", "distance_km": 2.1},
    ]
    out = _sort_grounding_rows_by_distance(rows, prefer_far_first=True)
    assert [row["name"] for row in out] == ["far", "mid", "near"]


def test_geo_accuracy_policy_prefers_strict_threshold_for_nearby_queries():
    cfg = {
        "geo_accuracy_max_m": 3000.0,
        "geo_accuracy_nearby_max_m": 800.0,
        "geo_accuracy_overview_max_m": 5000.0,
    }
    threshold, policy = _resolve_geo_accuracy_max_m("여기 근처 카페 추천해줘", cfg)
    assert threshold == 800.0
    assert policy == "nearby"


def test_geo_accuracy_policy_prefers_looser_threshold_for_overview_queries():
    cfg = {
        "geo_accuracy_max_m": 3000.0,
        "geo_accuracy_nearby_max_m": 800.0,
        "geo_accuracy_overview_max_m": 5000.0,
    }
    threshold, policy = _resolve_geo_accuracy_max_m("오사카 2박 3일 여행 동선 개요를 짜줘", cfg)
    assert threshold == 5000.0
    assert policy == "overview"


def test_geo_accuracy_policy_uses_default_threshold_for_non_place_queries():
    cfg = {
        "geo_accuracy_max_m": 3000.0,
        "geo_accuracy_nearby_max_m": 800.0,
        "geo_accuracy_overview_max_m": 5000.0,
    }
    threshold, policy = _resolve_geo_accuracy_max_m("오늘 기분이 좀 이상해", cfg)
    assert threshold == 3000.0
    assert policy == "default"


def test_immediate_safety_alert_is_injected_when_critical_signal_detected():
    out, injected = _ensure_immediate_safety_alert(
        transcript="오사카에서 치안 위험지역 알려줘",
        response_text="야간 이동은 줄이고 주요 관광 동선 위주로 이동해.",
        language="ko",
        location_hint="Osaka, Japan",
        grounding_block="[웹 검색 근거]\n1. 일본 외무성\n- 요약: breaking alert, Civil unrest advisory and curfew notice",
        safety_advisory_block="",
    )
    assert injected is True
    assert "긴급 안전 경고" in out


def test_immediate_safety_alert_is_not_injected_for_stale_non_realtime_risk_signal():
    out, injected = _ensure_immediate_safety_alert(
        transcript="오사카에서 치안 위험지역 알려줘",
        response_text="공식 공지를 확인해줘.",
        language="ko",
        location_hint="Osaka, Japan",
        grounding_block="[웹 검색 근거]\n1. 일본 외무성\n- 요약: Civil unrest advisory in 2024 archive",
        safety_advisory_block="",
    )
    assert injected is False
    assert out == "공식 공지를 확인해줘."


def test_immediate_safety_alert_is_not_injected_without_location_context():
    out, injected = _ensure_immediate_safety_alert(
        transcript="치안 정보 알려줘",
        response_text="공식 사이트를 먼저 확인해줘.",
        language="ko",
        location_hint="",
        grounding_block="[웹 검색 근거]",
        safety_advisory_block="",
    )
    assert injected is False
    assert out == "공식 사이트를 먼저 확인해줘."


def test_immediate_safety_alert_is_not_injected_for_general_itinerary_query_without_critical_signal():
    out, injected = _ensure_immediate_safety_alert(
        transcript="치앙라이 2박 3일 일정 짜줘",
        response_text="치앙라이 일정부터 정리할게.",
        language="ko",
        location_hint="Chiang Rai, Thailand",
        grounding_block="[웹 검색 근거]",
        safety_advisory_block="",
    )
    assert injected is False
    assert out.startswith("치앙라이 일정부터 정리할게.")


def test_user_memory_hint_includes_display_name_and_recent_query():
    hint = _build_user_memory_hint(
        user_key="test-user-memory-001",
        user_display_name="철홍",
        transcript="치앙라이 숙소와 맛집 알려줘",
    )
    assert "Companion reusable user memory" in hint
    assert "철홍" in hint
    assert "숙소" in hint or "맛집" in hint


def test_append_travel_brief_categories_rewrites_location_missing_reply_for_full_brief_query():
    out = _append_travel_brief_categories(
        "관광지 정보, 교통수단, 숙소, 먹거리, 정통음식, 역사 유적지, 밤문화, 카지노 정보를 GPS 근처 기준으로 안내해줘",
        "현재 위치가 제공되지 않았어. 위치를 알려주시면 안내할게.",
        "ko",
    )
    assert "GPS 기준" in out
    assert "관광지" in out and "교통수단" in out and "숙소" in out
    assert "밤문화" in out and "카지노" in out


def test_safety_template_router_classifies_crime_query():
    category = _classify_safety_template_category("오사카 위험지역 치안 정보 알려줘")
    assert category == "crime"


def test_safety_template_router_classifies_law_query():
    category = _classify_safety_template_category("도쿄에서 드론 촬영 법규 알려줘")
    assert category == "law"


def test_safety_template_router_returns_fixed_response_for_medical_query():
    text = _resolve_safety_template_response("근처 응급 병원과 약국 어떻게 찾아?", "ko")
    assert text is not None
    assert "안전 고정 안내" in text
    assert "의료" in text or "응급" in text


def test_safety_template_router_returns_none_for_non_safety_query():
    text = _resolve_safety_template_response("오늘 오사카 날씨 어때?", "ko")
    assert text is None


def test_safety_template_router_does_not_block_normal_airport_itinerary_query():
    text = _resolve_safety_template_response(
        "태국 치앙라이 2박 3일 일정 짜줘. 방콕에서 어떤 공항으로 들어가면 돼?",
        "ko",
    )
    assert text is None


def test_gps_risk_evidence_message_includes_zone_distance_radius():
    msg = _build_gps_risk_evidence_message(
        language="ko",
        latitude=34.6937,
        longitude=135.5023,
        risk_profile={
            "matched_zone": "osaka-test-zone",
            "distance_km": 0.41,
            "radius_km": 1.2,
        },
    )
    assert "GPS 근거" in msg
    assert "osaka-test-zone" in msg
    assert "거리=0.41km" in msg
    assert "반경=1.20km" in msg


def test_radius_risk_profile_returns_radius_for_matched_zone():
    # 일본 오사카 시내권 샘플 좌표(규칙 파일 내 테스트 존 반경과 매칭되는 경우).
    profile = radius_risk_profile(34.6937, 135.5023)
    if str(profile.get("level") or "none").lower() == "high":
        assert isinstance(profile.get("radius_km"), (int, float))


def test_resolve_edge_tts_prosody_splits_sorisae_and_voip():
    from backend.llm.voice_gateway import _edge_tts_prosody_defaults, _resolve_edge_tts_prosody
    from backend.marketplace.worldlinco_section_freeze import (
        frozen_sorisae_edge_tts_prosody_ko,
        frozen_voip_edge_tts_prosody_ko_default,
    )

    default = _edge_tts_prosody_defaults("ko")
    face = _resolve_edge_tts_prosody("ko", "face.interpret")
    sorisae = _resolve_edge_tts_prosody("ko", "sorisae.friend")
    voip = _resolve_edge_tts_prosody("ko", "voip.voice_relay")
    assert face == ("-1%", "+28%", "+2Hz")
    assert sorisae == frozen_sorisae_edge_tts_prosody_ko()
    assert voip == default == frozen_voip_edge_tts_prosody_ko_default()
