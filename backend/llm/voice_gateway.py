"""Voice entrypoint for orchestrator requests.

Supports whisper.cpp-compatible CLIs and a basic TTS bridge.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.voip_language_locales import (
    resolve_edge_tts_voice,
    resolve_whisper_initial_prompt,
    resolve_whisper_language_hint,
)

from backend.llm.model_config import (
    build_ollama_options,
    get_chat_model,
    get_coder_model,
    get_designer_model,
    get_planner_model,
    get_reasoning_model,
    get_reviewer_model,
    get_voice_chat_model,
)
from backend.orchestrator.chat.chat_service import answer_orchestrator_chat as answer_orchestrator_chat_service
from backend.orchestrator.chat.models import OrchestratorChatRequest


router = APIRouter(prefix="/api/llm", tags=["voice"])
logger = logging.getLogger(__name__)
VOICE_OLLAMA_BASE = os.getenv('OLLAMA_BASE', 'http://host.docker.internal:8008/v1')
VOICE_CHAT_REQUEST_MAX_TOKENS = max(128, int(os.getenv('ORCH_CHAT_REQUEST_MAX_TOKENS', '768')))
VOICE_LIGHTWEIGHT_CHAT_MAX_TOKENS = max(64, int(os.getenv('ORCH_LIGHTWEIGHT_CHAT_MAX_TOKENS', '192')))
VOICE_CHAT_AGENT_TIMEOUT_SEC = max(5.0, float(os.getenv('ORCH_CHAT_AGENT_TIMEOUT_SEC', '75')))
VOICE_REASONER_BRIEF_TIMEOUT_SEC = max(5.0, float(os.getenv('ORCH_REASONER_BRIEF_TIMEOUT_SEC', '45')))
VOICE_RELAY_MIN_SEGMENT_MS = max(800, int(os.getenv("VOICE_RELAY_MIN_SEGMENT_MS", "2400")))
VOICE_RELAY_MIN_SEGMENT_TOLERANCE_MS = max(0, int(os.getenv("VOICE_RELAY_MIN_SEGMENT_TOLERANCE_MS", "350")))
VOICE_RELAY_MIN_SPEECH_RMS_DB = float(os.getenv("VOICE_RELAY_MIN_SPEECH_RMS_DB", "-58"))
VOICE_RELAY_PCM_SAMPLE_RATE = 16_000


# ──────────────────────────────────────────────────────────────────────────
# 대면 통역 "친구 모드" (face GPT) — 무거운 개발 오케스트레이터와 100% 분리.
# vLLM에 직접 따뜻한 친구 페르소나로 질의한다(번역 엔진과 동일한 검증된 연결 재사용).
# ──────────────────────────────────────────────────────────────────────────
VOICE_FRIEND_MAX_TOKENS = max(48, int(os.getenv("VOICE_FRIEND_MAX_TOKENS", "256")))
VOICE_FRIEND_TEMPERATURE = float(os.getenv("VOICE_FRIEND_TEMPERATURE", "0.8"))
VOICE_FRIEND_HISTORY_TURNS = max(0, int(os.getenv("VOICE_FRIEND_HISTORY_TURNS", "10")))
VOICE_FRIEND_TIMEOUT_SEC = max(5.0, float(os.getenv("VOICE_FRIEND_TIMEOUT_SEC", "30")))
# 친구 모드 웹 검색 그라운딩(최신 정보 주입). 기본 on, 키 없으면 자동으로 무력화된다.
VOICE_FRIEND_WEB_SEARCH = os.getenv("VOICE_FRIEND_WEB_SEARCH", "1").strip().lower() not in {"0", "false", "no", "off", ""}
VOICE_FRIEND_WEB_MAX_ITEMS = max(1, int(os.getenv("VOICE_FRIEND_WEB_MAX_ITEMS", "4")))
VOICE_FRIEND_WEB_TIMEOUT_SEC = max(2.0, float(os.getenv("VOICE_FRIEND_WEB_TIMEOUT_SEC", "8")))
# 장소 찾기 그라운딩 소스. 기본은 OpenStreetMap(Nominatim) — ODbL 라이선스라 상업·음성(TTS)·
# 저장이 모두 허용된다. Google Maps(SerpAPI google_maps)는 약관상 콘텐츠의 TTS 사용·복사 저장·
# 모델 학습이 금지(Service Specific Terms §13, ToS (iii)/(iv)/(vii))이므로 **기본 비활성**한다.
# 정식 라이선스를 확보한 운영 환경에서만 VOICE_FRIEND_MAPS_GROUNDING=1 로 켤 수 있다.
# 자체 관광 인덱스(Qdrant tourism_places) 그라운딩 — 합법 오픈데이터(OSM/Wikidata)를 사전 적재해
# 의미검색+지오필터로 즉답한다. 1순위(자체 인덱스) → 2순위(OSM 실시간) → 3순위(웹) 폴백.
VOICE_FRIEND_INDEX_GROUNDING = os.getenv("VOICE_FRIEND_INDEX_GROUNDING", "1").strip().lower() not in {"0", "false", "no", "off", ""}
VOICE_FRIEND_OSM_GROUNDING = os.getenv("VOICE_FRIEND_OSM_GROUNDING", "1").strip().lower() not in {"0", "false", "no", "off", ""}
VOICE_FRIEND_MAPS_GROUNDING = os.getenv("VOICE_FRIEND_MAPS_GROUNDING", "0").strip().lower() not in {"0", "false", "no", "off", ""}
# Nominatim(OSM 지오코딩/POI) 엔드포인트. 공용 인스턴스는 1req/s·User-Agent 필수 정책이 있으므로
# 운영 트래픽이 늘면 자체 호스팅 Nominatim 으로 교체(VOICE_FRIEND_OSM_ENDPOINT)한다.
VOICE_FRIEND_OSM_ENDPOINT = os.getenv("VOICE_FRIEND_OSM_ENDPOINT", "https://nominatim.openstreetmap.org/search").strip()
VOICE_FRIEND_OSM_USER_AGENT = os.getenv("VOICE_FRIEND_OSM_USER_AGENT", "SorisaeAI/1.0 (tourism voice assistant)").strip()


# 친구 모드 전용 웹 검색 트리거 — 일상 대화에 흔한 시간 단어(오늘/지금/현재/올해)는 제외하고,
# 명백한 '최신/외부 정보' 신호일 때만 검색한다(오케스트레이터용 휴리스틱은 잡담에 과트리거됨).
_FRIEND_WEB_SEARCH_KEYWORDS = (
    "뉴스", "속보", "최신", "트렌드", "신기술", "출시", "발표", "업데이트", "리뷰", "랭킹", "순위",
    "날씨", "기온", "미세먼지", "환율", "주가", "시세", "코스피", "코스닥", "나스닥", "비트코인", "금값", "유가",
    "검색해", "검색 해", "찾아봐", "찾아 줘", "찾아줘", "알아봐", "알아 봐",
    # 여행/지역 컨시어지(외국에서 실시간 현지 정보가 가장 중요) — 호텔·맛집·명소·교통·주소·전화 등.
    "호텔", "숙소", "료칸", "게스트하우스", "민박", "에어비앤비", "맛집", "식당", "레스토랑", "카페",
    "술집", "이자카야", "포장마차", "관광", "명소", "가볼만", "가 볼 만", "볼거리", "축제", "행사",
    "박물관", "미술관", "전망대", "온천", "해변", "공원", "시장", "쇼핑", "백화점", "면세점", "마트",
    "편의점", "약국", "병원", "은행", "환전", "주소", "전화번호", "연락처", "위치", "가는 길", "가는길",
    "길 안내", "길안내", "근처", "주변", "지하철", "전철", "버스", "기차", "택시", "공항", "역",
    "입장료", "요금", "영업시간", "운영시간", "오픈", "예약", "메뉴", "특산물", "기념품",
    # 안전/치안·법규·관습/예절·음식문화(전 세계 관광 안전 안내 특화).
    "안전", "위험", "치안", "위험지역", "우범", "사기", "소매치기", "바가지", "주의", "조심",
    "여행경보", "여행 경보", "테러", "시위", "대사관", "영사관", "비상", "응급", "긴급",
    "법", "법규", "규정", "규칙", "금지", "벌금", "불법", "처벌", "비자", "입국", "세관", "통관",
    "팁", "팁문화", "매너", "에티켓", "예절", "관습", "풍습", "문화", "금기", "복장", "드레스코드",
    "종교", "사원", "모스크", "성당", "음식문화", "음식", "향신료", "식문화", "현지음식", "길거리음식",
    "safety", "danger", "dangerous", "crime", "scam", "pickpocket", "travel advisory", "advisory",
    "law", "laws", "rule", "prohibited", "forbidden", "visa", "customs", "tipping", "etiquette",
    "manners", "culture", "religion", "dress code", "food culture", "street food",
    "news", "latest", "release", "breaking", "trend", "weather", "stock price",
    "hotel", "restaurant", "cafe", "near me", "nearby", "address", "phone", "directions",
    "open hours", "museum", "station", "airport", "ramen", "sushi", "things to do",
    "2024", "2025", "2026", "2027", "2028",
)


# 사실 질문 신호(웹검색으로 정확히 답할 가치가 있는 정보성 질문).
_FRIEND_QUESTION_MARKERS = (
    "누구", "누가", "언제", "어디", "어느", "왜", "어떻게", "어떤", "무엇", "뭐야", "뭐예요",
    "뭐냐", "뭔지", "몇", "이름", "뜻", "의미", "방법", "차이", "얼마", "수도", "인구", "역사",
)
# 잡담/자기참조 신호(이게 있으면 정보검색이 아니라 친구 대화로 본다).
_FRIEND_CHITCHAT_MARKERS = (
    "너 ", "넌 ", "네가", "너는", "당신", "기분", "뭐해", "뭐 해", "뭐하", "뭐 하", "지냈",
    "잘 잤", "잘잤", "안녕", "사랑", "보고싶", "보고 싶", "심심", "고마워", "고맙",
)


# 현재 위치 기반('여기/근처') 질의 신호 — 검색어에 위치를 합성해 정확도를 높인다.
_FRIEND_NEARBY_MARKERS = (
    "근처", "주변", "여기", "이근처", "이 근처", "근방", "가까운", "가까이",
    "nearby", "near me", "near here", "around here", "close to me", "여기서",
)

# 국가코드 → 표기명(여행 컨시어지 위치 맥락용, 흔한 여행국 위주. 미지정은 코드 그대로).
_COUNTRY_LABELS = {
    "KR": "South Korea", "JP": "Japan", "CN": "China", "US": "USA", "GB": "UK",
    "FR": "France", "IT": "Italy", "ES": "Spain", "DE": "Germany", "TH": "Thailand",
    "VN": "Vietnam", "TW": "Taiwan", "HK": "Hong Kong", "SG": "Singapore", "ID": "Indonesia",
    "PH": "Philippines", "IN": "India", "AU": "Australia", "CA": "Canada", "TR": "Turkey",
    "NL": "Netherlands", "CH": "Switzerland", "AT": "Austria", "GR": "Greece", "PT": "Portugal",
    "MY": "Malaysia", "AE": "UAE", "MX": "Mexico", "BR": "Brazil", "NZ": "New Zealand",
}


def _friend_location_hint(
    region_hint: Optional[str],
    country_code: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
) -> str:
    """사용자의 현재 여행 위치를 사람이 읽을 짧은 문자열로. 없으면 ''.

    예: 'Kansai, Japan', 'Jeju, South Korea', '34.6937,135.5023'.
    """
    parts: list[str] = []
    region = (region_hint or "").strip()
    code = (country_code or "").strip().upper()
    if region:
        parts.append(region)
    if code:
        parts.append(_COUNTRY_LABELS.get(code, code))
    label = ", ".join(parts)
    if not label and latitude is not None and longitude is not None:
        try:
            label = f"{float(latitude):.4f},{float(longitude):.4f}"
        except (TypeError, ValueError):
            label = ""
    return label


# ── 로그 익명화(PIPA/GDPR 데이터 최소화) ───────────────────────────────────
# 운영 로그에 정밀좌표·발화 원문을 남기지 않는다. 좌표는 소수 1자리(≈11km)로 거칠게,
# 발화는 길이+sha256 앞 8자리(추적용 비가역 지문)만 남긴다.
_COORD_LIKE_RE = re.compile(r"^\s*-?\d{1,3}\.\d+\s*,\s*-?\d{1,3}\.\d+\s*$")


def _anonymize_loc_for_log(location_hint: Optional[str]) -> str:
    raw = str(location_hint or "").strip()
    if not raw:
        return "-"
    if _COORD_LIKE_RE.match(raw):
        try:
            lat_s, lon_s = raw.split(",")
            return f"~{float(lat_s):.1f},{float(lon_s):.1f}"  # 좌표는 거칠게(지역 식별 불가 수준)
        except (TypeError, ValueError):
            return "coord"
    return raw  # 지역/국가 라벨은 PII 아님 — 그대로 둔다.


def _anonymize_text_for_log(text: Optional[str]) -> str:
    raw = str(text or "")
    if not raw:
        return "len=0"
    digest = hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:8]
    return f"len={len(raw)} h={digest}"


def _friend_should_search(transcript: str) -> bool:
    normalized = " ".join(str(transcript or "").strip().split()).lower()
    if not normalized:
        return False
    if normalized.startswith(("/search", "/news", "검색", "뉴스")):
        return True
    # 1) 시간민감/외부정보 키워드 → 검색
    if any(token.lower() in normalized for token in _FRIEND_WEB_SEARCH_KEYWORDS):
        return True
    # 2) 정보성 사실 질문 → 검색(단, 잡담성 질문은 제외해 과트리거 방지)
    is_chitchat = any(marker in normalized for marker in _FRIEND_CHITCHAT_MARKERS)
    if is_chitchat:
        return False
    is_question = normalized.endswith("?") or any(q in normalized for q in _FRIEND_QUESTION_MARKERS)
    return is_question


# 여행 '장소 찾기' 의도 키워드 — 구글 지도(local) 검색으로 실제 장소(이름·주소·전화·평점)를 가져온다.
_FRIEND_PLACE_KEYWORDS = (
    "호텔", "숙소", "료칸", "게스트하우스", "민박", "에어비앤비", "맛집", "식당", "레스토랑", "카페",
    "술집", "이자카야", "포장마차", "관광", "명소", "가볼만", "가 볼 만", "볼거리", "박물관", "미술관",
    "전망대", "온천", "해변", "공원", "시장", "쇼핑", "백화점", "면세점", "마트", "편의점", "약국",
    "병원", "은행", "환전", "주유소", "주차장", "역", "지하철역", "공항", "터미널", "정류장",
    "hotel", "restaurant", "cafe", "bar", "museum", "attraction", "pharmacy", "hospital", "atm",
    "station", "airport", "ramen", "sushi", "things to do", "near me", "nearby",
)


def _friend_is_place_query(transcript: str) -> bool:
    norm = " ".join(str(transcript or "").lower().split())
    return any(k.lower() in norm for k in _FRIEND_PLACE_KEYWORDS)


def _friend_fetch_maps_grounding(
    query: str,
    latitude: Optional[float],
    longitude: Optional[float],
    *,
    max_items: int,
    timeout_sec: float,
) -> str:
    """구글 지도(SerpAPI google_maps)로 실제 주변 장소를 검색해 근거 블록 생성.

    이름·주소·전화·평점·영업시간을 그대로 담아 모델이 장소 정보를 지어내지 않게 한다.
    좌표(ll)가 있으면 그 위치 반경으로, 없으면 질의어만으로 검색한다(전 세계 어디든).
    """
    try:
        from backend.api.external_search_router import _serpapi_call
    except Exception as exc:
        logger.warning("[voice/friend-chat] maps import 실패: %s", exc)
        return ""
    extra: dict = {}
    if latitude is not None and longitude is not None:
        try:
            extra["ll"] = f"@{float(latitude)},{float(longitude)},14z"
        except (TypeError, ValueError):
            pass
    try:
        payload = _serpapi_call("google_maps", query, max_items, timeout_sec, **extra)
    except Exception as exc:
        logger.warning("[voice/friend-chat] google_maps 검색 실패: %s", exc)
        return ""
    locals_ = payload.get("local_results") if isinstance(payload, dict) else None
    if not isinstance(locals_, list) or not locals_:
        return ""
    lines = ["[Google Maps 실시간 장소 결과 — 아래 실제 장소만 사용하고 지어내지 말 것]"]
    for item in locals_[:max_items]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("title") or "").strip()
        if not name:
            continue
        parts = [f"- {name}"]
        addr = str(item.get("address") or "").strip()
        if addr:
            parts.append(f"주소: {addr}")
        phone = str(item.get("phone") or "").strip()
        if phone:
            parts.append(f"전화: {phone}")
        rating = item.get("rating")
        if rating:
            reviews = item.get("reviews")
            parts.append(f"평점: {rating}" + (f"({reviews})" if reviews else ""))
        hours = item.get("hours") or item.get("open_state") or ""
        if hours:
            parts.append(f"영업: {str(hours).strip()}")
        ptype = item.get("type") or ""
        if ptype:
            parts.append(f"종류: {str(ptype).strip()}")
        lines.append(" | ".join(parts))
    return "\n".join(lines) if len(lines) > 1 else ""


def _friend_fetch_index_grounding(
    query: str,
    latitude: Optional[float],
    longitude: Optional[float],
    *,
    max_items: int,
) -> str:
    """자체 관광 인덱스(Qdrant tourism_places)에서 의미검색+지오필터로 장소 근거 블록 생성.

    사전 적재된 합법 오픈데이터(OSM ODbL / Wikidata CC0)만 담겨 있어 음성·저장·학습이 모두 합법.
    미가동(미설치/미적재)이면 빈 문자열 → 상위에서 OSM 실시간/웹으로 폴백한다.
    """
    try:
        from backend.services.tourism_kb import search_tourism_places
    except Exception:
        return ""
    try:
        rows = search_tourism_places(query, limit=max_items, latitude=latitude, longitude=longitude)
    except Exception as exc:
        logger.warning("[voice/friend-chat] tourism index 검색 실패: %s", exc)
        return ""
    if not rows:
        return ""
    lines = ["[관광 지식베이스 장소 결과(오픈데이터: OSM ODbL / Wikidata CC0) — 아래 실제 장소만 사용하고 지어내지 말 것]"]
    for r in rows[:max_items]:
        name = str(r.get("name") or "").strip()
        if not name:
            continue
        parts = [f"- {name}"]
        addr = str(r.get("address") or "").strip()
        if addr:
            parts.append(f"주소: {addr}")
        phone = str(r.get("phone") or "").strip()
        if phone:
            parts.append(f"전화: {phone}")
        hours = str(r.get("hours") or "").strip()
        if hours:
            parts.append(f"영업: {hours}")
        website = str(r.get("website") or "").strip()
        if website:
            parts.append(f"웹: {website}")
        cat = str(r.get("category") or "").strip()
        if cat:
            parts.append(f"종류: {cat}")
        lines.append(" | ".join(parts))
    return "\n".join(lines) if len(lines) > 1 else ""


def _friend_fetch_osm_grounding(
    query: str,
    latitude: Optional[float],
    longitude: Optional[float],
    *,
    max_items: int,
    timeout_sec: float,
) -> str:
    """OpenStreetMap(Nominatim)으로 실제 장소를 검색해 근거 블록 생성(ODbL).

    Google Maps 약관이 금지하는 'TTS 발화·DB 저장·모델 학습'이 ODbL에서는 모두 허용되므로,
    음성으로 읽어주는 소리새 AI 장소 안내의 1차 소스로 사용한다.
    이름·주소·좌표·종류와(있으면) 전화/영업시간/웹사이트를 그대로 담아 모델이 지어내지 않게 한다.
    좌표가 있으면 그 주변(viewbox)을 우선해 근접 검색하고, 없으면 질의어만으로 검색한다(전 세계).
    """
    q = " ".join(str(query or "").split())
    if not q:
        return ""
    params: dict = {
        "q": q,
        "format": "jsonv2",
        "limit": str(max(1, int(max_items))),
        "addressdetails": "1",
        "extratags": "1",
        "namedetails": "1",
        "accept-language": "ko",
    }
    # 좌표가 있으면 약 ±0.15° (≈15km) viewbox 로 근접 결과를 우선한다(bounded=0: 선호하되 강제 안 함).
    if latitude is not None and longitude is not None:
        try:
            lat_f = float(latitude)
            lon_f = float(longitude)
            d = 0.15
            params["viewbox"] = f"{lon_f - d},{lat_f + d},{lon_f + d},{lat_f - d}"
            params["bounded"] = "0"
        except (TypeError, ValueError):
            pass
    url = f"{VOICE_FRIEND_OSM_ENDPOINT}?{urllib.parse.urlencode(params)}"

    def _fetch_osm():
        request = urllib.request.Request(
            url,
            headers={"User-Agent": VOICE_FRIEND_OSM_USER_AGENT, "Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))

    # 캐시 키는 좌표를 2자리(≈1km)로 거칠게 묶어 재사용↑ + 정밀좌표 저장 회피(프라이버시).
    try:
        lat_key = round(float(latitude), 2) if latitude is not None else None
        lon_key = round(float(longitude), 2) if longitude is not None else None
    except (TypeError, ValueError):
        lat_key = lon_key = None
    try:
        from backend.services.realtime_cache import cached_fetch

        payload = cached_fetch(
            "osm", (q, lat_key, lon_key, int(max_items)), _fetch_osm
        )
    except Exception as exc:
        logger.warning("[voice/friend-chat] nominatim 검색 실패: %s", exc)
        return ""
    if not isinstance(payload, list) or not payload:
        return ""
    lines = ["[OpenStreetMap 실시간 장소 결과(© OpenStreetMap contributors, ODbL) — 아래 실제 장소만 사용하고 지어내지 말 것]"]
    for item in payload[:max_items]:
        if not isinstance(item, dict):
            continue
        namedetails = item.get("namedetails") if isinstance(item.get("namedetails"), dict) else {}
        name = str(namedetails.get("name") or item.get("name") or "").strip()
        display = str(item.get("display_name") or "").strip()
        if not name and display:
            name = display.split(",")[0].strip()
        if not name:
            continue
        parts = [f"- {name}"]
        if display:
            parts.append(f"주소: {display}")
        extratags = item.get("extratags") if isinstance(item.get("extratags"), dict) else {}
        phone = str(extratags.get("phone") or extratags.get("contact:phone") or "").strip()
        if phone:
            parts.append(f"전화: {phone}")
        hours = str(extratags.get("opening_hours") or "").strip()
        if hours:
            parts.append(f"영업: {hours}")
        website = str(extratags.get("website") or extratags.get("contact:website") or "").strip()
        if website:
            parts.append(f"웹: {website}")
        ptype = str(item.get("type") or item.get("addresstype") or "").strip()
        if ptype:
            parts.append(f"종류: {ptype}")
        lines.append(" | ".join(parts))
    return "\n".join(lines) if len(lines) > 1 else ""


def _friend_fetch_grounding(
    transcript: str,
    *,
    force: Optional[bool],
    location_hint: str = "",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> str:
    """필요 시 실시간 근거 블록을 만든다(동기 — 호출측에서 to_thread 권장).

    force=True 면 무조건 검색, force=False 면 검색 안 함, None 이면 보수적 휴리스틱 자동 판단.
    여행 '장소 찾기' 의도면 **구글 지도(local)** 를 우선 사용해 실제 장소(이름·주소·전화·평점)를
    가져오고(전 세계, 좌표 반경 기준), 그 외/실패 시 일반 웹 검색으로 폴백한다.
    """
    if not VOICE_FRIEND_WEB_SEARCH or force is False:
        return ""
    if force is not True and not _friend_should_search(transcript):
        return ""
    norm = " ".join(str(transcript or "").lower().split())
    nearby = any(marker in norm for marker in _FRIEND_NEARBY_MARKERS)

    # 1) 장소 찾기 의도 → 합법 오픈데이터만 사용(음성/저장/학습 합법).
    #    1순위 자체 인덱스(Qdrant) → 2순위 OSM 실시간(Nominatim) → 3순위 Google(정식 라이선스 시만).
    if _friend_is_place_query(transcript):
        place_query = transcript
        # 좌표가 없으면 질의어에 현재 위치명을 붙여 지역을 좁힌다.
        if location_hint and (nearby or latitude is None or longitude is None):
            place_query = f"{location_hint} {transcript}"
        if VOICE_FRIEND_INDEX_GROUNDING:
            index_block = _friend_fetch_index_grounding(
                transcript,  # 의미검색 — 원문 질의가 가장 정확(위치는 좌표 지오필터로 처리)
                latitude,
                longitude,
                max_items=VOICE_FRIEND_WEB_MAX_ITEMS,
            )
            if index_block:
                return index_block
        if VOICE_FRIEND_OSM_GROUNDING:
            osm_block = _friend_fetch_osm_grounding(
                place_query,
                latitude,
                longitude,
                max_items=VOICE_FRIEND_WEB_MAX_ITEMS,
                timeout_sec=VOICE_FRIEND_WEB_TIMEOUT_SEC,
            )
            if osm_block:
                return osm_block
        # 정식 라이선스 확보 환경에서만(기본 off) Google Maps 폴백.
        if VOICE_FRIEND_MAPS_GROUNDING:
            maps_block = _friend_fetch_maps_grounding(
                place_query,
                latitude,
                longitude,
                max_items=VOICE_FRIEND_WEB_MAX_ITEMS,
                timeout_sec=VOICE_FRIEND_WEB_TIMEOUT_SEC,
            )
            if maps_block:
                return maps_block

    # 2) 폴백: 일반 웹 검색(뉴스·사실·시세 등 비장소 질의 포함).
    try:
        from backend.orchestrator.chat.web_search import (
            build_web_grounding_block,
            fetch_web_grounding,
        )
    except Exception as exc:
        logger.warning("[voice/friend-chat] web_search import 실패: %s", exc)
        return ""
    query = transcript
    if location_hint and nearby:
        query = f"{location_hint} {transcript}"
    try:
        results = fetch_web_grounding(
            query,
            max_items=VOICE_FRIEND_WEB_MAX_ITEMS,
            timeout_sec=VOICE_FRIEND_WEB_TIMEOUT_SEC,
            logger=logger,
        )
    except Exception as exc:
        logger.warning("[voice/friend-chat] web grounding 실패: %s", exc)
        return ""
    return build_web_grounding_block(results)


def _friend_chat_base_url() -> str:
    """친구 모드 전용 vLLM base URL.

    일반 대화용 모델을 '별도 vLLM 인스턴스'(예: :8009)에 올렸다면
    LLM_VOICE_FRIEND_BASE_URL 로 지정한다. 미지정 시 번역 엔진과 동일한 vLLM(:8008)을 재사용한다.
    컨테이너 내부 127.0.0.1/localhost → host.docker.internal 보정도 동일 규칙으로 적용한다.
    """
    raw = (os.getenv("LLM_VOICE_FRIEND_BASE_URL") or os.getenv("LLM_MODEL_VOICE_CHAT_BASE_URL") or "").strip().rstrip("/")
    if not raw:
        from backend.services.nadotongryoksa.translator import _llm_translate_base_url

        return _llm_translate_base_url()
    if os.path.exists("/.dockerenv"):
        raw = raw.replace("://127.0.0.1", "://host.docker.internal").replace(
            "://localhost", "://host.docker.internal"
        )
    return raw


def _list_served_models(base_url: Optional[str] = None) -> set[str]:
    """vLLM /v1/models 에 현재 실서빙 중인 모델 ID 집합. 실패 시 빈 집합."""
    try:
        import httpx

        base = base_url or _friend_chat_base_url()
        resp = httpx.get(f"{base}/models", timeout=5)
        if resp.status_code != 200:
            return set()
        data = (resp.json() or {}).get("data") or []
        return {str(item.get("id")) for item in data if item.get("id")}
    except Exception:
        return set()


def _resolve_friend_chat_model() -> str:
    """친구 모드 모델 해석.

    1순위: LLM_MODEL_VOICE_CHAT(일반 대화용 모델을 별도로 vLLM에 올린 경우) — 단, **실제 서빙 중일 때만**.
    2순위: 친구 전용 vLLM의 실서빙 모델 자동탐지(전용 인스턴스면 그쪽 단일 모델).
    3순위: 번역 엔진 모델 자동탐지(동일 vLLM 재사용 환경).

    오버라이드가 미서빙 모델을 가리키면(예: 14B만 올라간 환경에서 .env=32B) vLLM이 404를
    던지므로, 실서빙 목록에 있을 때만 채택하고 아니면 자동탐지로 폴백한다.
    """
    from backend.services.nadotongryoksa.translator import _resolve_llm_translate_model

    base = _friend_chat_base_url()
    served = _list_served_models(base)

    override = (os.getenv("LLM_MODEL_VOICE_CHAT") or os.getenv("LLM_MODEL_VOICE_FRIEND") or "").strip()
    if override:
        if not served or override in served:
            return override
        logger.info(
            "[voice/friend-chat] override model %s not served; falling back to discovered served model",
            override,
        )
    # 전용 인스턴스가 단일 모델만 서빙하면 그 ID를 그대로 사용.
    if len(served) == 1:
        return next(iter(served))
    return _resolve_llm_translate_model()


def _friend_system_prompt(
    language: Optional[str], *, web_grounded: bool = False, location_hint: str = ""
) -> str:
    """아주 자연스러운 '친구 모드' 페르소나. 사용자 언어로 따뜻하고 편하게 대화.

    web_grounded=True 이면 실시간 웹 검색 근거가 함께 제공되므로 '인터넷 접속 없음' 문구를
    빼고, 검색 근거를 우선 활용해 최신 정보로 답하도록 지시한다.
    location_hint(현재 여행지)가 있으면 '여기/근처' 질의를 그 위치 기준으로 해석하게 한다.
    """
    try:
        from backend.services.nadotongryoksa.translator import _llm_lang_label

        lang_label = _llm_lang_label((language or "ko").strip() or "ko")
    except Exception:
        lang_label = language or "Korean"
    base = (
        "You are 소리새 AI: the user's close, warm friend AND an expert worldwide travel guide who keeps "
        "them company anywhere on Earth. "
        f"ALWAYS reply in the same language as the user (their language is {lang_label}); "
        "never switch languages or translate. "
        "Talk like a real friend: warm, casual, natural and human. In Korean use a friendly, "
        "comfortable spoken tone (가벼운 반말·친근한 말투 환영), not stiff or formal. "
        "Because this is spoken aloud, keep replies short and conversational (usually 1-3 sentences); "
        "no markdown, no asterisks, no bullet lists, no headings, no code blocks, no emoji spam. "
        "Write phone numbers, addresses and hours as plain spoken text with normal digits and hyphens "
        "(e.g. 0570-04-2222). NEVER mask or redact them with asterisks like *** or **; "
        "if you don't have the real number, just say you couldn't find it instead of writing symbols. "
        "Your specialty is travel guidance, finding places, and sightseeing — in ANY country or city. "
        "Help with: finding hotels/restaurants/cafes/pharmacies/ATMs/stores/attractions nearby; "
        "directions and public transport; addresses, phone numbers, opening hours, prices and tickets; "
        "landmarks, must-see spots, local food, festivals, and what to do; plus practical travel help "
        "(currency/exchange, useful local phrases, customs/etiquette, safety, weather). "
        "You are also a TRAVEL SAFETY & CULTURE guide: warn about unsafe/high-risk areas, common scams, "
        "and pickpocket spots; explain country-specific LAWS and rules a tourist must obey (e.g. drug/alcohol/"
        "smoking rules, photography or drone limits, what's illegal locally, visa/customs basics, tipping); "
        "explain local CUSTOMS, etiquette, dress codes, religious-site manners, and taboos; and share local "
        "FOOD CULTURE (signature dishes, dining etiquette, spice/dietary notes, street-food tips). "
        "Tailor all of this to the user's current country/region. When you give a place or plan, proactively "
        "add a brief, genuinely useful safety, law, etiquette, or food tip for that area in one short sentence. "
        "In an emergency, point them to local emergency numbers and the nearest embassy/consulate. "
        "Be a proactive guide who makes the trip easier, safer, and less boring. "
    )
    if location_hint:
        base += (
            f"The user is currently traveling near: {location_hint}. "
            "Treat this as their current location for any 'nearby / here / around here' question, "
            "and tailor recommendations and directions to this area. "
        )
    if web_grounded:
        return base + (
            "Fresh web search results are provided below as context. "
            "Use them as the primary, trusted source. When the user asks for a place, hotel, restaurant, "
            "pharmacy, station, etc., pull the concrete details from the results — the NAME and, when "
            "available, the ADDRESS, PHONE NUMBER, and OPENING HOURS — and say them clearly out loud "
            "(spell phone numbers naturally). Do not read URLs aloud. If the results do not contain the "
            "exact detail, say what you did find and suggest the next step. Answer directly and confidently."
        )
    return base + (
        "Answer confidently from your own knowledge for general topics (chat, history, science, how-to, "
        "well-known facts) — never just say 'I don't know'. "
        "BUT do NOT fabricate specific local facts you are unsure of: real business names, exact addresses, "
        "phone numbers, prices, or opening hours. If you don't truly know a specific local detail, do not "
        "invent it — instead briefly tell them you'll look it up, or ask for the city/area to narrow it down, "
        "and offer the best general guidance you can. Keep it warm, brief, and human."
    )


async def _friend_chat_completion(
    transcript: str,
    language: Optional[str],
    conversation: list[dict],
    grounding_block: str = "",
    location_hint: str = "",
) -> str:
    """vLLM /chat/completions 직접 호출로 친구 모드 답변 생성.

    grounding_block 이 있으면(실시간 웹 검색 근거) 시스템 컨텍스트로 주입해 최신 정보로 답한다.
    location_hint 가 있으면 현재 여행지 맥락을 페르소나에 주입한다.
    """
    import httpx

    web_grounded = bool(grounding_block.strip())
    messages: list[dict] = [
        {
            "role": "system",
            "content": _friend_system_prompt(
                language, web_grounded=web_grounded, location_hint=location_hint
            ),
        }
    ]
    if web_grounded:
        messages.append({"role": "system", "content": grounding_block})
    history = conversation[-(VOICE_FRIEND_HISTORY_TURNS * 2):] if VOICE_FRIEND_HISTORY_TURNS else []
    for turn in history:
        role = str((turn or {}).get("role") or "").strip()
        content = str((turn or {}).get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": transcript})

    payload = {
        "model": _resolve_friend_chat_model(),
        "messages": messages,
        "temperature": VOICE_FRIEND_TEMPERATURE,
        # 근거 요약은 토큰 여유가 더 필요하므로 그라운딩 시 상한을 키운다.
        "max_tokens": (VOICE_FRIEND_MAX_TOKENS + 192) if web_grounded else VOICE_FRIEND_MAX_TOKENS,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=VOICE_FRIEND_TIMEOUT_SEC) as client:
        response = await client.post(
            f"{_friend_chat_base_url()}/chat/completions",
            json=payload,
        )
    if response.status_code != 200:
        raise RuntimeError(f"친구 모드 LLM 응답 오류(status={response.status_code})")
    data = response.json()
    choices = data.get("choices") or []
    content = ""
    if choices:
        content = (choices[0].get("message") or {}).get("content") or ""
    return str(content or "").strip()


# 음성 합성 전 정리 패턴 — TTS가 마크다운 기호를 '별표(*)/우물정(#)' 등으로 읽지 않도록 제거.
_SPEECH_CLEAN_PATTERNS = (
    (re.compile(r"```.*?```", re.S), " "),          # 코드펜스
    (re.compile(r"`([^`]*)`"), r"\1"),               # 인라인 코드
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), " "),      # 이미지
    (re.compile(r"\[([^\]]+)\]\([^)]*\)"), r"\1"),   # 링크 → 표시 텍스트
    (re.compile(r"https?://\S+"), " "),              # 맨 URL
)


def _sanitize_friend_reply_for_speech(text: str) -> str:
    """친구 모드 답변을 음성/표시용으로 정리.

    모델이 가끔 마크다운(**굵게**, # 제목, - 리스트)이나 ``***`` 마스킹을 출력하면 단말 TTS가
    그 기호를 '별표/우물정'처럼 읽어버린다. 전화번호의 하이픈 등 정보는 보존하면서 기호만 제거한다.
    """
    s = str(text or "")
    for pat, repl in _SPEECH_CLEAN_PATTERNS:
        s = pat.sub(repl, s)
    # 마크다운 강조/헤딩/인용 기호 제거(*, _, #, >, ~, `). 하이픈(-)은 전화번호/주소 보존 위해 남김.
    s = re.sub(r"[*_#>~`]+", "", s)
    # 줄머리 리스트 불릿(-, •) 제거(하이픈은 줄머리에서만 불릿으로 간주).
    s = re.sub(r"(?m)^[ \t]*[-•·]\s+", "", s)
    # 공백 정리.
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _friend_is_noise_or_hallucination(transcript: str) -> bool:
    """무음/잡음 구간에서 생성된 입력인지 판정 — 친구 모드 '혼자 발화' 방지.

    아주 짧은 노이즈나 Whisper 환각(영상 아웃트로·자막 크레딧 등)이면 응답을 생성하지 않는다.
    환각 시그니처는 통역 라우터와 동일 정의를 재사용한다(순환 임포트 회피 위해 지연 임포트).
    """
    text = " ".join(str(transcript or "").split())
    if len(text) < 2:
        return True
    try:
        from backend.llm.router import _is_whisper_hallucination_phrase

        if _is_whisper_hallucination_phrase(text):
            return True
    except Exception:
        pass
    return False


def _resolve_voice_chat_model(agent_key: str, *, lightweight: bool) -> str:
    normalized = str(agent_key or 'chat').strip().lower()
    if normalized == 'voice_chat':
        return get_voice_chat_model()
    if normalized == 'reasoner':
        return get_reasoning_model()
    if normalized == 'coder':
        return get_coder_model()
    if normalized == 'planner':
        return get_planner_model()
    if normalized == 'reviewer':
        return get_reviewer_model()
    if normalized == 'designer':
        return get_designer_model()
    if lightweight:
        return get_chat_model()
    return get_chat_model()


class VoiceRequest(BaseModel):
    audio_base64: Optional[str] = None
    transcript: Optional[str] = None
    agent_key: str = "reasoner"
    tts: bool = True
    auto_apply: bool = False
    max_tokens: int = 2048
    task: str = ""
    mode: str = "manual_9step"
    manual_mode: bool = True
    companion_mode: str = "hybrid"
    output_dir: Optional[str] = None
    run_id: Optional[str] = None
    conversation: list[dict] = []
    language: Optional[str] = None  # STT 언어 힌트 (zh, ja, ko, en 등)
    detected_language: Optional[str] = None  # Whisper 감지 언어 (zh, ja, ko, en 등)


class VoiceResponse(BaseModel):
    transcript: str
    response_text: str
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = None
    output_dir: Optional[str] = None
    run_id: Optional[str] = None
    conversation: list[dict] = []


def _run_whisper_cpp(audio_bytes: bytes) -> str:
    whisper_bin = os.getenv("WHISPER_CPP_BIN", "")
    whisper_model = os.getenv("WHISPER_CPP_MODEL", "")
    if not whisper_bin or not whisper_model:
        raise RuntimeError("whisper.cpp configuration missing")

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "voice_input.wav"
        output_path = Path(temp_dir) / "voice_output.txt"
        audio_path.write_bytes(audio_bytes)
        proc = subprocess.run(
            [
                whisper_bin,
                "-m",
                whisper_model,
                "-f",
                str(audio_path),
                "-otxt",
                "-of",
                str(output_path.with_suffix("")),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "whisper.cpp failed")
        txt_path = output_path
        if not txt_path.exists():
            raise RuntimeError("whisper.cpp output missing")
        return txt_path.read_text(encoding="utf-8").strip()


def _normalize_whisper_language_hint(language: Optional[str]) -> Optional[str]:
    """앱 LangCode → faster-whisper ISO 639-1 (50개국 SSOT)."""
    return resolve_whisper_language_hint(language)


def _resolve_whisper_initial_prompt(language: Optional[str]) -> str:
    return resolve_whisper_initial_prompt(language)


def _pcm16_mono_rms_db(audio_bytes: bytes, sample_rate: int = VOICE_RELAY_PCM_SAMPLE_RATE) -> float:
    import math
    import struct

    pcm_offset = 44 if audio_bytes[:4] == b"RIFF" else 0
    pcm = audio_bytes[pcm_offset:]
    if len(pcm) < 2:
        return -160.0
    sample_count = len(pcm) // 2
    samples = struct.unpack("<" + "h" * sample_count, pcm[: sample_count * 2])
    if not samples:
        return -160.0
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    rms = math.sqrt(mean_square)
    if rms <= 0:
        return -160.0
    return 20.0 * math.log10(rms / 32768.0)


def _assert_min_voice_energy(normalized_wav: bytes) -> None:
    rms_db = _pcm16_mono_rms_db(normalized_wav)
    if rms_db < VOICE_RELAY_MIN_SPEECH_RMS_DB:
        raise RuntimeError("음성이 감지되지 않았습니다. 다시 말씀해 주세요.")


def _pcm16_mono_duration_ms(audio_bytes: bytes, sample_rate: int = VOICE_RELAY_PCM_SAMPLE_RATE) -> float:
    pcm_offset = 44 if audio_bytes[:4] == b"RIFF" else 0
    pcm_len = max(0, len(audio_bytes) - pcm_offset)
    return (pcm_len / (sample_rate * 2)) * 1000.0


def _assert_min_voice_capture_duration(normalized_wav: bytes) -> None:
    duration_ms = _pcm16_mono_duration_ms(normalized_wav)
    if duration_ms < (VOICE_RELAY_MIN_SEGMENT_MS - VOICE_RELAY_MIN_SEGMENT_TOLERANCE_MS):
        raise RuntimeError(
            "녹음 길이가 너무 짧습니다. "
            f"({duration_ms:.0f}ms / 최소 {VOICE_RELAY_MIN_SEGMENT_MS}ms)"
        )


def _normalize_voice_audio_bytes(audio_bytes: bytes) -> bytes:
    """Expo/모바일 m4a·aac 등을 16kHz mono PCM wav로 정규화 + 음성 대역·잡음 제거."""
    if not audio_bytes:
        raise RuntimeError("오디오 데이터가 비어 있습니다")

    with tempfile.TemporaryDirectory() as temp_dir:
        src = Path(temp_dir) / "voice_input.bin"
        dst = Path(temp_dir) / "voice_normalized.wav"
        src.write_bytes(audio_bytes)
        audio_filter = os.getenv(
            "VOICE_STT_AUDIO_FILTER",
            "highpass=f=80,lowpass=f=4200",
        )
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(src),
                "-af",
                audio_filter,
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(dst),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if proc.returncode != 0 or not dst.exists():
            stderr = (proc.stderr or "").strip()
            raise RuntimeError(stderr or "오디오 정규화에 실패했습니다")
        normalized = dst.read_bytes()
        if not normalized:
            raise RuntimeError("정규화된 오디오가 비어 있습니다")
        _assert_min_voice_capture_duration(normalized)
        _assert_min_voice_energy(normalized)
        return normalized


_WHISPER_MODEL_LOCK = __import__("threading").Lock()
_INPROCESS_WHISPER_MODEL = None
_INPROCESS_WHISPER_KEY: Optional[tuple[str, str, str]] = None
_INPROCESS_WHISPER_DISABLED = False


def _faster_whisper_use_subprocess() -> bool:
    """서브프로세스 강제 사용 여부. 기본은 인프로세스(모델 1회 로드)로 지연을 최소화한다."""
    flag = os.getenv("FASTER_WHISPER_SUBPROCESS", "0").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def _get_inprocess_whisper_model(model_name: str, device: str, compute_type: str):
    """faster-whisper 모델을 프로세스 수명 동안 1회만 로드해 재사용한다.

    기존 구현은 호출마다 서브프로세스를 띄우고 그 안에서 모델을 새로 로드해
    (파이썬 기동 + 모델 로드) 비용이 매 세그먼트마다 발생, 대면 통역 지연의 핵심 원인이었다.
    """
    global _INPROCESS_WHISPER_MODEL, _INPROCESS_WHISPER_KEY
    key = (model_name, device, compute_type)
    if _INPROCESS_WHISPER_MODEL is not None and _INPROCESS_WHISPER_KEY == key:
        return _INPROCESS_WHISPER_MODEL
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    _INPROCESS_WHISPER_MODEL = model
    _INPROCESS_WHISPER_KEY = key
    logger.info(
        "[voice-stt] in-process faster-whisper model loaded model=%s device=%s compute=%s",
        model_name,
        device,
        compute_type,
    )
    return model


def _transcribe_with_inprocess_whisper(
    audio_path: Path,
    model_name: str,
    device: str,
    compute_type: str,
    whisper_lang: str,
    prompt: str,
) -> dict[str, object]:
    model = _get_inprocess_whisper_model(model_name, device, compute_type)
    return _transcribe_with_loaded_model(model, audio_path, whisper_lang, prompt)


def _whisper_decode_kwargs() -> dict[str, object]:
    """STT 디코딩 파라미터 SSOT.

    인프로세스/서브프로세스 추론이 **동일 설정**을 쓰도록 한 곳에서 생성한다(드리프트 방지).
    large-v3는 무음·짧은 발화에서 환각이 잦으므로 temperature 폴백(0.0 실패 시 0.2→0.4
    재시도)을 켜서 Whisper 내부 품질 게이트(compression_ratio / log_prob / no_speech
    임계)가 실제로 동작하게 한다. 모든 값은 env로 라이브 미세조정 가능(기본값=기존 동작).
    """

    def _f(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    def _i(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    temps: list[float] = []
    for part in os.getenv("WHISPER_TEMPERATURE_FALLBACK", "0.0,0.2,0.4").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            temps.append(float(part))
        except ValueError:
            continue
    if not temps:
        temps = [0.0]

    vad_flag = os.getenv("WHISPER_VAD_FILTER", "0").strip().lower() in {"1", "true", "yes", "on"}

    return {
        "vad_filter": vad_flag,
        "condition_on_previous_text": False,
        "no_speech_threshold": _f("WHISPER_NO_SPEECH_THRESHOLD", 0.45),
        "log_prob_threshold": _f("WHISPER_LOG_PROB_THRESHOLD", -1.2),
        "compression_ratio_threshold": _f("WHISPER_COMPRESSION_RATIO_THRESHOLD", 3.2),
        "beam_size": _i("WHISPER_BEAM_SIZE", 5),
        "best_of": _i("WHISPER_BEST_OF", 3),
        "temperature": temps[0] if len(temps) == 1 else temps,
    }


def _transcribe_with_loaded_model(
    model,
    audio_path: Path,
    whisper_lang: str,
    prompt: str,
) -> dict[str, object]:
    kwargs: dict[str, object] = _whisper_decode_kwargs()
    if whisper_lang:
        kwargs["language"] = whisper_lang
    if prompt:
        kwargs["initial_prompt"] = prompt
    segments, info = model.transcribe(str(audio_path), **kwargs)
    segment_rows = list(segments)
    transcript = " ".join((seg.text or "").strip() for seg in segment_rows).strip()
    detected = getattr(info, "language", None) or ""
    language_probability = float(getattr(info, "language_probability", 0.0) or 0.0)
    avg_logprob = (
        sum(float(getattr(seg, "avg_logprob", -5.0)) for seg in segment_rows) / len(segment_rows)
        if segment_rows
        else -5.0
    )
    max_no_speech_prob = (
        max(float(getattr(seg, "no_speech_prob", 1.0)) for seg in segment_rows)
        if segment_rows
        else 1.0
    )
    return {
        "transcript": transcript,
        "detected_language": detected,
        "language_probability": language_probability,
        "avg_logprob": avg_logprob,
        "max_no_speech_prob": max_no_speech_prob,
    }


def warmup_faster_whisper_model() -> None:
    """Warm ffmpeg + whisper (in-process model load) with a tiny silent clip."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            silent = Path(temp_dir) / "warmup.wav"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=16000:cl=mono",
                    "-t",
                    "0.2",
                    str(silent),
                ],
                capture_output=True,
                check=False,
            )
            if silent.exists():
                _run_faster_whisper(silent.read_bytes(), "ko", "")
        logger.info("[voice-stt] faster-whisper warmup complete")
    except Exception as exc:
        logger.warning("[voice-stt] faster-whisper warmup skipped: %s", exc)


VOICE_RELAY_MIN_AVG_LOGPROB = float(os.getenv("VOICE_RELAY_MIN_AVG_LOGPROB", "-0.95"))
VOICE_RELAY_MAX_NO_SPEECH_PROB = float(os.getenv("VOICE_RELAY_MAX_NO_SPEECH_PROB", "0.62"))


def classify_voice_relay_stt_trust(
    transcript: str,
    avg_logprob: float,
    max_no_speech_prob: float,
) -> str:
    if not str(transcript or "").strip():
        return "low"
    if avg_logprob < VOICE_RELAY_MIN_AVG_LOGPROB:
        return "low"
    if max_no_speech_prob > VOICE_RELAY_MAX_NO_SPEECH_PROB:
        return "low"
    return "high"


def _run_faster_whisper(
    audio_bytes: bytes,
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
) -> dict[str, object]:
    """Returns whisper payload including transcript, language, and confidence metrics."""
    model_name = os.getenv("FASTER_WHISPER_MODEL", "tiny")
    device = os.getenv("FASTER_WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8")
    whisper_lang = _normalize_whisper_language_hint(language)
    prompt = str(initial_prompt or _resolve_whisper_initial_prompt(language) or "").strip()

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / "voice_input.wav"
        audio_path.write_bytes(audio_bytes)

        global _INPROCESS_WHISPER_DISABLED
        payload: dict[str, object] | None = None
        if not _faster_whisper_use_subprocess() and not _INPROCESS_WHISPER_DISABLED:
            model = None
            try:
                with _WHISPER_MODEL_LOCK:
                    model = _get_inprocess_whisper_model(model_name, device, compute_type)
            except Exception as exc:
                # 모델 로드 자체가 불가능한 환경(예: faster_whisper 미설치/GPU 부재)에서만
                # 영구 비활성화한다. 일시적 추론 오류로는 비활성화하지 않는다.
                logger.warning(
                    "[voice-stt] in-process faster-whisper model load failed, "
                    "disabling in-process and using subprocess: %s",
                    exc,
                )
                _INPROCESS_WHISPER_DISABLED = True
                model = None
            if model is not None:
                try:
                    with _WHISPER_MODEL_LOCK:
                        payload = _transcribe_with_loaded_model(
                            model,
                            audio_path,
                            whisper_lang or "",
                            prompt,
                        )
                except Exception as exc:
                    # 추론 단계 일시 오류는 이번 호출만 서브프로세스로 폴백(영구 비활성화 금지).
                    logger.warning(
                        "[voice-stt] in-process transcribe failed, "
                        "falling back to subprocess for this call: %s",
                        exc,
                    )
                    payload = None

        if payload is None:
            payload = _run_faster_whisper_subprocess(
                audio_path,
                model_name,
                device,
                compute_type,
                whisper_lang or "",
                prompt,
            )

        transcript = str(payload.get("transcript") or "").strip()
        detected = str(payload.get("detected_language") or "").strip() or None
        avg_logprob = float(payload.get("avg_logprob", -5.0))
        max_no_speech_prob = float(payload.get("max_no_speech_prob", 1.0))
        return {
            "transcript": transcript,
            "detected_language": detected,
            "avg_logprob": avg_logprob,
            "max_no_speech_prob": max_no_speech_prob,
            "stt_trust": classify_voice_relay_stt_trust(
                transcript,
                avg_logprob,
                max_no_speech_prob,
            ),
        }


def _run_faster_whisper_subprocess(
    audio_path: Path,
    model_name: str,
    device: str,
    compute_type: str,
    whisper_lang: str,
    prompt: str,
) -> dict[str, object]:
    """격리된 서브프로세스에서 1회 추론(인프로세스 로드 실패 시 fallback 경로)."""
    script = """
import json
import sys

from faster_whisper import WhisperModel

audio_path = sys.argv[1]
model_name = sys.argv[2]
device = sys.argv[3]
compute_type = sys.argv[4]
lang_hint = sys.argv[5] if len(sys.argv) > 5 else ""
initial_prompt = sys.argv[6] if len(sys.argv) > 6 else ""
decode_kwargs_json = sys.argv[7] if len(sys.argv) > 7 else ""

model = WhisperModel(model_name, device=device, compute_type=compute_type)
try:
    kwargs = json.loads(decode_kwargs_json) if decode_kwargs_json else {}
except Exception:
    kwargs = {}
if not kwargs:
    kwargs = {
        "vad_filter": False,
        "condition_on_previous_text": False,
        "no_speech_threshold": 0.45,
        "log_prob_threshold": -1.2,
        "compression_ratio_threshold": 3.2,
        "beam_size": 5,
        "best_of": 3,
        "temperature": [0.0, 0.2, 0.4],
    }
if lang_hint:
    kwargs["language"] = lang_hint
if initial_prompt:
    kwargs["initial_prompt"] = initial_prompt
segments, info = model.transcribe(audio_path, **kwargs)
segment_rows = list(segments)
transcript = " ".join((seg.text or "").strip() for seg in segment_rows).strip()
detected = getattr(info, "language", None) or ""
language_probability = float(getattr(info, "language_probability", 0.0) or 0.0)
avg_logprob = (
    sum(float(getattr(seg, "avg_logprob", -5.0)) for seg in segment_rows) / len(segment_rows)
    if segment_rows
    else -5.0
)
max_no_speech_prob = (
    max(float(getattr(seg, "no_speech_prob", 1.0)) for seg in segment_rows)
    if segment_rows
    else 1.0
)
print(json.dumps({
    "transcript": transcript,
    "detected_language": detected,
    "language_probability": language_probability,
    "avg_logprob": avg_logprob,
    "max_no_speech_prob": max_no_speech_prob,
}, ensure_ascii=False))
"""

    cmd = [
        sys.executable,
        "-c",
        script,
        str(audio_path),
        model_name,
        device,
        compute_type,
        whisper_lang or "",
        prompt,
        json.dumps(_whisper_decode_kwargs()),
    ]

    with _WHISPER_MODEL_LOCK:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=240,
        )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(stderr or "faster-whisper subprocess failed")

    return json.loads((proc.stdout or "{}").strip())


def _edge_tts_enabled() -> bool:
    flag = os.getenv("VOICE_EDGE_TTS_ENABLED", "1").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def _detect_dominant_script_lang(text: str) -> Optional[str]:
    """텍스트의 우세 스크립트를 감지해 언어 코드를 돌려준다.

    Edge 뉴럴 TTS는 텍스트 언어와 보이스 언어가 불일치하면(예: ja 보이스에
    한글 텍스트) 'No audio was received'로 오디오를 거부한다. 번역문에 원문
    스크립트가 일부 섞이거나(스크립트 누수) 상위 단계가 잘못된 lang을 넘긴 경우,
    실제 글자 스크립트에 맞는 보이스로 폴백해 항상 뉴럴 발화를 보장한다.
    라틴 문자 등 다국어 공유 스크립트는 모호하므로 None을 반환한다.
    """
    counts: dict[str, int] = {}
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3 or 0x1100 <= code <= 0x11FF:
            counts["ko"] = counts.get("ko", 0) + 1
        elif 0x3040 <= code <= 0x30FF:  # 히라가나/가타카나 → 일본어 확정
            counts["ja"] = counts.get("ja", 0) + 1
        elif 0x4E00 <= code <= 0x9FFF:  # CJK 한자(가나 없으면 중국어로 간주)
            counts["zh"] = counts.get("zh", 0) + 1
        elif 0x0400 <= code <= 0x04FF:
            counts["ru"] = counts.get("ru", 0) + 1
        elif 0x0600 <= code <= 0x06FF:
            counts["ar"] = counts.get("ar", 0) + 1
        elif 0x0E00 <= code <= 0x0E7F:
            counts["th"] = counts.get("th", 0) + 1
        elif 0x0590 <= code <= 0x05FF:
            counts["he"] = counts.get("he", 0) + 1
        elif 0x0900 <= code <= 0x097F:
            counts["hi"] = counts.get("hi", 0) + 1
        elif 0x0370 <= code <= 0x03FF:
            counts["el"] = counts.get("el", 0) + 1
    if not counts:
        return None
    # 가나(ja)가 하나라도 있으면 한자 다수여도 일본어로 본다.
    if counts.get("ja"):
        return "ja"
    return max(counts.items(), key=lambda kv: kv[1])[0]


def edge_tts_base_rate_pct() -> float:
    """제품 기본 TTS 속도(`VOICE_EDGE_TTS_RATE`, 기본 -6%)를 퍼센트 실수로 파싱.

    E3 표현형 운율 델타가 이 baseline 을 기준점으로 가산되도록(감정 중립 ≈ 기존 속도).
    """

    raw = os.getenv("VOICE_EDGE_TTS_RATE", "-6%").strip().rstrip("%").strip()
    try:
        return float(raw or "-6")
    except ValueError:
        return -6.0


def _synthesize_edge_tts(
    text: str,
    target_lang: Optional[str] = None,
    *,
    expressive: Optional[object] = None,
) -> tuple[bytes, str]:
    import edge_tts

    rate = os.getenv("VOICE_EDGE_TTS_RATE", "-6%").strip() or "-6%"
    volume = "+0%"
    pitch = "+0Hz"
    # [V2 감정 E3] 표현형 운율 적용(카나리). expressive 가 주어지면(=COMM_V2_EMOTION_EXPRESSIVE_TTS
    # on + 비중립) rate/volume/pitch 를 감정 운율로 대체. 없으면 기존 동작과 100% 동일.
    if expressive is not None:
        rate = str(getattr(expressive, "rate", rate) or rate)
        volume = str(getattr(expressive, "volume", volume) or volume)
        pitch = str(getattr(expressive, "pitch", pitch) or pitch)

    requested_voice = resolve_edge_tts_voice(target_lang)
    # 보이스 후보: 1순위는 요청 타깃 언어, 실패 시 텍스트 실제 스크립트 기반 보이스.
    voice_candidates: list[str] = [requested_voice]
    detected_lang = _detect_dominant_script_lang(text)
    if detected_lang:
        detected_voice = resolve_edge_tts_voice(detected_lang)
        if detected_voice != requested_voice:
            voice_candidates.append(detected_voice)

    async def _run(voice: str) -> bytes:
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks)

    # edge-tts는 MS 엔드포인트의 Sec-MS-GEC 토큰 타이밍/콜드스타트로 드물게
    # "No audio was received"를 던진다. 짧게 재시도해 상품 신뢰성을 확보한다(기본 3회).
    try:
        attempts = max(1, int(os.getenv("VOICE_EDGE_TTS_RETRIES", "3")))
    except (TypeError, ValueError):
        attempts = 3
    last_exc: Optional[Exception] = None
    for voice in voice_candidates:
        for _ in range(attempts):
            try:
                audio_bytes = asyncio.run(_run(voice))
            except Exception as exc:  # NoAudioReceived 등 일시 오류 → 재시도
                last_exc = exc
                continue
            if audio_bytes:
                if voice != requested_voice:
                    logger.info(
                        "edge-tts voice fallback: requested=%s used=%s (script=%s)",
                        requested_voice,
                        voice,
                        detected_lang,
                    )
                return audio_bytes, "audio/mpeg"
            last_exc = RuntimeError("edge-tts produced no audio")
    raise last_exc or RuntimeError("edge-tts produced no audio")


def _synthesize_tts(
    text: str,
    target_lang: Optional[str] = None,
    *,
    expressive: Optional[object] = None,
) -> tuple[Optional[str], Optional[str]]:
    trimmed = str(text or "").strip()
    if not trimmed:
        return None, None

    if _edge_tts_enabled():
        try:
            audio_bytes, audio_format = _synthesize_edge_tts(
                trimmed, target_lang, expressive=expressive
            )
            return base64.b64encode(audio_bytes).decode("ascii"), audio_format
        except ImportError:
            logger.debug("edge-tts not installed; falling back to VOICE_TTS_COMMAND")
        except Exception as exc:
            logger.warning("edge-tts synthesis failed: %s", exc)

    tts_command = os.getenv("VOICE_TTS_COMMAND", "").strip()
    if tts_command:
        proc = subprocess.run(
            [tts_command, trimmed],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                proc.stderr.decode("utf-8", errors="ignore").strip()
                or "tts failed"
            )
        content_type = "audio/mpeg" if proc.stdout[:3] == b"ID3" or proc.stdout[:2] == b"\xff\xfb" else "audio/wav"
        return base64.b64encode(proc.stdout).decode("ascii"), content_type

    return (
        base64.b64encode(trimmed.encode("utf-8")).decode("ascii"),
        "text/plain",
    )


class VoiceSynthesizeRequest(BaseModel):
    text: str
    # 대상 언어 코드(예: ja, ko). 지정 시 해당 언어 네이티브 뉴럴 보이스로 합성한다.
    # 미지정이면 기존 동작(기본 보이스) 유지 — 하위호환.
    target_lang: Optional[str] = None
    # V.2 ID 백본 — 발화(vocalization) 단계가 출처 상관 ID에 스스로 붙도록 echo 한다.
    correlation_id: Optional[str] = None
    feature_id: Optional[str] = None


class VoiceSynthesizeResponse(BaseModel):
    text: str
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = None
    tts_delivery: str = "device_speech"
    correlation_id: Optional[str] = None


@router.post("/voice/synthesize", response_model=VoiceSynthesizeResponse)
async def voice_synthesize(request: VoiceSynthesizeRequest):
    """오케스트레이터·통역 수신측 TTS — Edge neural 우선, 없으면 device speech."""
    from backend.llm.correlation import FEATURE_IDS, ensure_correlation_id

    trimmed = str(request.text or "").strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="text가 필요합니다.")
    correlation_id = ensure_correlation_id(
        request.correlation_id,
        request.feature_id or FEATURE_IDS["voice_synthesize"],
    )
    try:
        audio_base64, audio_format = await asyncio.to_thread(
            _synthesize_tts, trimmed, request.target_lang
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS 실패: {exc}") from exc
    delivery = (
        "server_audio"
        if audio_base64 and str(audio_format or "").startswith("audio/")
        else "device_speech"
    )
    logger.info(
        "[voice/synthesize] cid=%s lang=%s delivery=%s",
        correlation_id,
        request.target_lang,
        delivery,
    )
    return VoiceSynthesizeResponse(
        text=trimmed,
        audio_base64=audio_base64,
        audio_format=audio_format,
        tts_delivery=delivery,
        correlation_id=correlation_id,
    )


@router.post("/voice/orchestrate", response_model=VoiceResponse)
async def voice_orchestrate(request_context: Request, request: VoiceRequest):
    transcript = (request.transcript or "").strip()
    detected_language: Optional[str] = None

    if not transcript and request.audio_base64:
        stt_errors: list[str] = []
        try:
            audio_bytes = base64.b64decode(request.audio_base64)
            whisper_bin = os.getenv("WHISPER_CPP_BIN", "").strip()
            whisper_model = os.getenv("WHISPER_CPP_MODEL", "").strip()

            if whisper_bin and whisper_model:
                try:
                    transcript = await asyncio.to_thread(
                        _run_whisper_cpp,
                        audio_bytes,
                    )
                except Exception as exc:
                    stt_errors.append(f"whisper.cpp: {exc}")

            if not transcript:
                try:
                    whisper_payload = await asyncio.to_thread(
                        _run_faster_whisper,
                        audio_bytes,
                        request.language,
                    )
                    transcript = str(whisper_payload.get("transcript") or "").strip()
                    detected_language = whisper_payload.get("detected_language")
                except Exception as exc:
                    stt_errors.append(f"faster-whisper: {exc}")

            # Keep voice flow alive even when audio is silent but STT engine is available.
            if not transcript and not stt_errors:
                transcript = "voice input received"

            if not transcript:
                raise HTTPException(
                    status_code=400,
                    detail=f"STT 실패: {' | '.join(stt_errors) or 'no STT engine configured'}",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"STT 실패: {exc}")

    if not transcript:
        raise HTTPException(status_code=400, detail="텍스트 또는 오디오 입력이 필요합니다")

    output_dir = request.output_dir
    run_id = request.run_id
    conversation: list[dict] = request.conversation or []

    if request.auto_apply:
        from backend.llm.orchestrator import OrchestrationRequest, run_orchestration

        orch_response = await asyncio.to_thread(
            lambda: asyncio.run(
                run_orchestration(
                    OrchestrationRequest(
                        task=transcript,
                        mode=request.mode or "auto",
                        max_tokens=request.max_tokens,
                        auto_apply=request.auto_apply,
                        manual_mode=request.manual_mode,
                        output_dir=request.output_dir,
                        run_id=request.run_id,
                        conversation=conversation,
                    )
                )
            )
        )
        response_text = orch_response.final_output
        output_dir = orch_response.output_dir
        run_id = orch_response.run_id
        conversation = [
            item.model_dump() for item in orch_response.conversation
        ]
    else:
        chat_response = await asyncio.to_thread(
            lambda: asyncio.run(
                answer_orchestrator_chat_service(
                    request_context=request_context,
                    request=OrchestratorChatRequest(
                        task=request.task or transcript,
                        message=transcript,
                        agent_key=request.agent_key or "reasoner",
                        mode=request.mode,
                        manual_mode=request.manual_mode,
                        companion_mode=request.companion_mode,
                        output_dir=request.output_dir,
                        run_id=request.run_id,
                        max_tokens=request.max_tokens,
                        conversation=conversation,
                    ),
                    agent_key=request.agent_key or "reasoner",
                    resolve_chat_model=_resolve_voice_chat_model,
                    build_ollama_options=build_ollama_options,
                    ollama_base=VOICE_OLLAMA_BASE,
                    orch_chat_request_max_tokens=VOICE_CHAT_REQUEST_MAX_TOKENS,
                    orch_lightweight_chat_max_tokens=VOICE_LIGHTWEIGHT_CHAT_MAX_TOKENS,
                    orch_chat_agent_timeout_sec=VOICE_CHAT_AGENT_TIMEOUT_SEC,
                    orch_reasoner_brief_timeout_sec=VOICE_REASONER_BRIEF_TIMEOUT_SEC,
                    logger=logger,
                    re_module=re,
                    session_factory=None,
                )
            )
        )
        response_text = chat_response.reply.content
        output_dir = chat_response.output_dir
        run_id = chat_response.run_id
        conversation = [
            item.model_dump() for item in chat_response.conversation
        ]

    audio_base64 = None
    audio_format = None
    if request.tts:
        try:
            audio_base64, audio_format = await asyncio.to_thread(
                _synthesize_tts,
                response_text,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"TTS 실패: {exc}")

    return VoiceResponse(
        transcript=transcript,
        response_text=response_text,
        audio_base64=audio_base64,
        audio_format=audio_format,
        output_dir=output_dir,
        run_id=run_id,
        conversation=conversation,
        detected_language=detected_language, # pyright: ignore[reportCallIssue]
    )


class FriendChatRequest(BaseModel):
    audio_base64: Optional[str] = None
    transcript: Optional[str] = None
    tts: bool = False
    language: Optional[str] = None  # 사용자 언어(답변 언어). 미지정 시 STT 감지/ko 폴백
    conversation: list[dict] = []
    # 실시간 웹 검색 그라운딩: None=자동(키워드 휴리스틱), True=강제 검색, False=검색 안 함
    web_search: Optional[bool] = None
    # 전 세계 여행 안내/찾기 특화 — 현재 위치 맥락('여기/근처' 질의를 현지 기준으로 해석).
    region_hint: Optional[str] = None
    country_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    correlation_id: Optional[str] = None
    feature_id: Optional[str] = None


@router.post("/voice/friend-chat", response_model=VoiceResponse)
async def voice_friend_chat(request: FriendChatRequest):
    """대면 통역 '친구 모드' 전용 — 따뜻하고 자연스러운 AI 친구 대화.

    무거운 개발 오케스트레이터(/voice/orchestrate)와 100% 분리된 경량 경로.
    STT → vLLM 친구 페르소나 답변 → (옵션) TTS. VoIP 통역과도 완전 독립.
    """
    transcript = (request.transcript or "").strip()
    detected_language: Optional[str] = None

    if not transcript and request.audio_base64:
        stt_errors: list[str] = []
        try:
            audio_bytes = base64.b64decode(request.audio_base64)
            whisper_bin = os.getenv("WHISPER_CPP_BIN", "").strip()
            whisper_model = os.getenv("WHISPER_CPP_MODEL", "").strip()

            if whisper_bin and whisper_model:
                try:
                    transcript = await asyncio.to_thread(_run_whisper_cpp, audio_bytes)
                except Exception as exc:
                    stt_errors.append(f"whisper.cpp: {exc}")

            if not transcript:
                try:
                    # 친구 모드는 '사용자가 실제 말한 언어'로 답해야 자연스럽다.
                    # 프로필 언어(request.language)를 STT 힌트로 강제하면 한국어 발화를
                    # 일본어 등으로 오인식·강제 디코딩하므로, 자동 감지(None)로 진짜 발화 언어를 얻는다.
                    whisper_payload = await asyncio.to_thread(
                        _run_faster_whisper,
                        audio_bytes,
                        None,
                    )
                    transcript = str(whisper_payload.get("transcript") or "").strip()
                    detected_language = whisper_payload.get("detected_language")  # type: ignore[assignment]
                except Exception as exc:
                    stt_errors.append(f"faster-whisper: {exc}")

            if not transcript:
                raise HTTPException(
                    status_code=400,
                    detail=f"STT 실패: {' | '.join(stt_errors) or 'no STT engine configured'}",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"STT 실패: {exc}")

    if not transcript:
        raise HTTPException(status_code=400, detail="텍스트 또는 오디오 입력이 필요합니다")

    # 무음/잡음 자기발화 방지 — Whisper 환각·노이즈 입력에는 답하지 않는다(혼자 계속 발화 차단).
    if _friend_is_noise_or_hallucination(transcript):
        logger.info("[voice/friend-chat] rejected noise/hallucination input %s", _anonymize_text_for_log(transcript))
        raise HTTPException(status_code=422, detail="음성이 감지되지 않았습니다. 다시 말씀해 주세요.")

    # 답변 언어 = 실제 말한 언어(STT 감지) 우선 → 없으면 요청 언어 → ko.
    # (프로필 언어를 우선하면 한국어 화자가 일본어 답을 받는 '번역체' 버그가 생김)
    reply_language = (detected_language or request.language or "ko").strip() or "ko"
    conversation: list[dict] = list(request.conversation or [])

    # 현재 여행지 맥락(전 세계 안내/찾기 특화) — '여기/근처' 질의를 현지 기준으로 해석.
    location_hint = _friend_location_hint(
        request.region_hint,
        request.country_code,
        request.latitude,
        request.longitude,
    )

    # 실시간 웹 검색 근거(최신 정보) — 자동/강제 판단 후 주입. urllib 블로킹이라 스레드로.
    grounding_block = ""
    try:
        grounding_block = await asyncio.to_thread(
            _friend_fetch_grounding,
            transcript,
            force=request.web_search,
            location_hint=location_hint,
            latitude=request.latitude,
            longitude=request.longitude,
        )
    except Exception as exc:
        logger.warning("[voice/friend-chat] grounding skip: %s", exc)

    try:
        response_text = await _friend_chat_completion(
            transcript,
            reply_language,
            conversation,
            grounding_block,
            location_hint,
        )
    except Exception as exc:
        logger.warning("[voice/friend-chat] LLM 실패: %s", exc)
        raise HTTPException(status_code=502, detail=f"친구 모드 응답 실패: {exc}")

    # 음성/표시용 정리 — 마크다운(**, #, -)·*** 마스킹 제거(단말 TTS '별표' 발화 방지).
    response_text = _sanitize_friend_reply_for_speech(response_text)

    if not response_text:
        raise HTTPException(status_code=502, detail="친구 모드 응답이 비어 있습니다")

    conversation = conversation + [
        {"role": "user", "content": transcript},
        {"role": "assistant", "content": response_text},
    ]
    # 히스토리 폭주 방지(최근 N턴만 유지)
    if VOICE_FRIEND_HISTORY_TURNS:
        conversation = conversation[-(VOICE_FRIEND_HISTORY_TURNS * 2):]

    audio_base64 = None
    audio_format = None
    if request.tts:
        try:
            audio_base64, audio_format = await asyncio.to_thread(
                _synthesize_tts,
                response_text,
                reply_language,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"TTS 실패: {exc}")

    logger.info(
        "[voice/friend-chat] lang=%s loc=%s in_len=%d out_len=%d tts=%s web_grounded=%s",
        reply_language,
        _anonymize_loc_for_log(location_hint),
        len(transcript),
        len(response_text),
        bool(request.tts),
        bool(grounding_block.strip()),
    )
    return VoiceResponse(
        transcript=transcript,
        response_text=response_text,
        audio_base64=audio_base64,
        audio_format=audio_format,
        output_dir=None,
        run_id=None,
        conversation=conversation,
    )


# ──────────────────────────────────────────────────────────────────────────
# 구조화 답변 /voice/answer — RAG(관광 인덱스) → LLM(스키마 강제) → JSON 일정/장소/지도URL.
# 설계: docs/worldlinco-v2/TOURISM_AI_KNOWLEDGE_RAG_DESIGN.md §4 stage4 (Structured-Output).
# 환각 방지 원칙: LLM 은 '검색된 후보(place_id) 배치 + 한줄 설명'만 담당하고, 이름·주소·좌표·
# 지도URL 같은 사실은 서버가 검색 결과에서 직접 주입한다(모델이 장소를 지어낼 수 없게).
# 지도 URL 은 OpenStreetMap(ODbL) 만 생성 — Google Maps 약관 회피(상업·저장·표시 합법).
# ──────────────────────────────────────────────────────────────────────────
VOICE_ANSWER_MAX_TOKENS = max(256, int(os.getenv("VOICE_ANSWER_MAX_TOKENS", "1100")))
VOICE_ANSWER_TEMPERATURE = float(os.getenv("VOICE_ANSWER_TEMPERATURE", "0.4"))
VOICE_ANSWER_MAX_DAYS = max(1, int(os.getenv("VOICE_ANSWER_MAX_DAYS", "7")))
VOICE_ANSWER_MAX_PLACES = max(4, int(os.getenv("VOICE_ANSWER_MAX_PLACES", "24")))
VOICE_ANSWER_TIMEOUT_SEC = max(5.0, float(os.getenv("VOICE_ANSWER_TIMEOUT_SEC", "45")))

_ANSWER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "integer"},
                    "title": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "place_id": {"type": "integer"},
                                "blurb": {"type": "string"},
                            },
                            "required": ["place_id", "blurb"],
                        },
                    },
                },
                "required": ["day", "title", "items"],
            },
        },
        "tips": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "days", "tips"],
}


def _osm_map_url(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    """OpenStreetMap 표준 지도 링크(ODbL — 표시·공유 합법). 좌표 없으면 None."""
    try:
        la = float(lat)  # type: ignore[arg-type]
        lo = float(lon)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return (
        f"https://www.openstreetmap.org/?mlat={la:.6f}&mlon={lo:.6f}"
        f"#map=17/{la:.6f}/{lo:.6f}"
    )


# 일정 '계획' 표현 — 검색어에서 빼면 핵심 의도(라멘/박물관 등)에 집중돼 검색 품질이 오른다.
# (원문 질의는 LLM 에 그대로 전달하고, 검색용 질의에서만 제거한다.)
_ANSWER_PLAN_FILLER = (
    "하루 코스", "당일 코스", "데이 코스", "여행 코스", "코스로", "코스", "일정표", "일정",
    "여행 계획", "계획 좀", "계획", "플랜", "동선", "짜줘", "짜 줘", "짜주세요", "만들어줘",
    "만들어 줘", "추천해줘", "추천해 줘", "위주로", "위주", "중심으로", "중심", "돌아보", "둘러보",
    "구경", "여행하고", "여행", "가볼만한", "가 볼 만한",
    "itinerary", "day trip", "trip plan", "plan a", "plan my", "things to do", "day plan",
    "one day", "1 day", "2 day", "3 day", "make me", "build me",
)
_ANSWER_DAYS_RE = re.compile(r"\b(\d+)\s*(박|일|days?|nights?)\b", re.IGNORECASE)


def _answer_search_query(query: str) -> str:
    """일정 계획 표현을 제거해 검색 핵심어만 남긴다(예: '오사카 라멘 맛집 하루 코스 짜줘'→'오사카 라멘 맛집')."""
    s = " ".join(str(query or "").split())
    s = _ANSWER_DAYS_RE.sub(" ", s)
    low = s
    for f in _ANSWER_PLAN_FILLER:
        low = low.replace(f, " ")
    cleaned = " ".join(low.split())
    return cleaned if cleaned else s


def _answer_collect_candidates(
    query: str,
    latitude: Optional[float],
    longitude: Optional[float],
    *,
    limit: int,
) -> list[dict]:
    """관광 인덱스(Qdrant tourism_places)에서 후보 장소를 구조화 dict 로 수집(동기).

    각 후보는 이름·종류·주소·좌표(+있으면 전화/영업/웹/출처)를 가진다. 좌표가 있으면
    OSM 지도 URL 을 서버에서 부여한다. 미가동/미적재 시 빈 리스트."""
    try:
        from backend.services.tourism_kb import search_tourism_places
    except Exception:
        return []
    try:
        rows = search_tourism_places(query, limit=limit, latitude=latitude, longitude=longitude)
    except Exception as exc:
        logger.warning("[voice/answer] index 검색 실패: %s", exc)
        return []
    cands: list[dict] = []
    for r in rows or []:
        name = str(r.get("name") or "").strip()
        if not name:
            continue
        lat = r.get("lat")
        lon = r.get("lon")
        cands.append({
            "name": name,
            "category": str(r.get("category") or "").strip(),
            "address": str(r.get("address") or "").strip(),
            "phone": str(r.get("phone") or "").strip(),
            "hours": str(r.get("hours") or "").strip(),
            "website": str(r.get("website") or "").strip(),
            "lat": lat,
            "lon": lon,
            "source": str(r.get("source") or "osm").strip(),
            "license": str(r.get("license") or "").strip(),
            "map_url": _osm_map_url(lat, lon),
        })
    return cands


def _answer_build_candidate_block(candidates: list[dict]) -> str:
    lines = []
    for i, c in enumerate(candidates):
        bits = [f"[{i}] {c['name']}"]
        if c.get("category"):
            bits.append(f"({c['category']})")
        if c.get("address"):
            bits.append(f"- {c['address']}")
        lines.append(" ".join(bits))
    return "\n".join(lines)


async def _answer_chat_raw(messages: list[dict], *, use_guided: bool) -> str:
    """vLLM /chat/completions 호출. use_guided 면 스키마 강제(guided_json)+json_object 요청."""
    import httpx

    payload: dict = {
        "model": _resolve_friend_chat_model(),
        "messages": messages,
        "temperature": VOICE_ANSWER_TEMPERATURE,
        "max_tokens": VOICE_ANSWER_MAX_TOKENS,
        "stream": False,
    }
    if use_guided:
        # vLLM 확장: 스키마 강제 디코딩. response_format 은 OpenAI 표준 폴백 신호.
        payload["guided_json"] = _ANSWER_JSON_SCHEMA
        payload["response_format"] = {"type": "json_object"}
    # 탄소·전력 측정(best-effort, 실패해도 추론에 영향 없음).
    try:
        from backend.services.carbon_meter import get_carbon_meter

        _carbon_ctx = get_carbon_meter().measure("voice_answer")
    except Exception:
        from contextlib import nullcontext

        _carbon_ctx = nullcontext()
    with _carbon_ctx:
        async with httpx.AsyncClient(timeout=VOICE_ANSWER_TIMEOUT_SEC) as client:
            resp = await client.post(f"{_friend_chat_base_url()}/chat/completions", json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"answer LLM status={resp.status_code}")
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    return str((choices[0].get("message") or {}).get("content") or "").strip()


def _extract_json_object(text: str) -> Optional[dict]:
    """텍스트에서 첫 균형 잡힌 JSON 오브젝트를 추출(코드펜스/잡설 혼입 대비)."""
    s = str(text or "")
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start:i + 1])
                except Exception:
                    return None
    return None


def _answer_system_prompt(language_label: str, location_hint: str, max_days: int) -> str:
    loc = f" The traveler is currently near: {location_hint}." if location_hint else ""
    return (
        f"You are 소리새 AI, an expert worldwide travel planner.{loc} "
        "You are given a numbered list of REAL candidate places (from an open-data tourism index). "
        "Build a realistic day-by-day plan by SELECTING places from the candidates using their numeric id. "
        "Rules: (1) Use ONLY the given candidate ids — never invent places, names, or addresses. "
        "(2) Prefer candidates that best match what the user asked for (e.g. if they ask for ramen/food, "
        "favor restaurants/cafes), then group nearby/similar places sensibly per day and order them logically. "
        f"(3) If the user states a trip length (e.g. 3 days), produce that many days, max {max_days}; "
        "otherwise produce 1 day. (4) For each item write a short 'blurb' (max 25 words). "
        "(5) Add 2-4 practical 'tips' for this area: safety, local law, etiquette, or food culture. "
        f"CRITICAL LANGUAGE RULE: ALL human-readable text you write — summary, every day 'title', every "
        f"'blurb', and every 'tips' entry — MUST be written ONLY in {language_label}. Do NOT use English "
        f"(unless {language_label} is English). Keep place names as given. "
        "Output ONLY a JSON object with keys: summary (string), days (array of {day:int, title:string, "
        "items:array of {place_id:int, blurb:string}}), tips (array of string). No markdown, no extra text. "
        f"Remember: summary, titles, blurbs and tips are in {language_label}."
    )


async def _answer_generate(
    query: str,
    language_label: str,
    location_hint: str,
    candidates: list[dict],
    max_days: int,
) -> dict:
    """후보 장소 + 사용자 질의 → LLM 구조화 일정(dict). guided 실패 시 plain 파싱 폴백."""
    candidate_block = _answer_build_candidate_block(candidates)
    messages = [
        {"role": "system", "content": _answer_system_prompt(language_label, location_hint, max_days)},
        {"role": "system", "content": f"Candidate places (id) :\n{candidate_block}"},
        {"role": "user", "content": query},
    ]
    content = ""
    for use_guided in (True, False):
        try:
            content = await _answer_chat_raw(messages, use_guided=use_guided)
            parsed = _extract_json_object(content)
            if parsed is not None:
                return parsed
        except Exception as exc:
            logger.warning("[voice/answer] LLM(guided=%s) 실패: %s", use_guided, exc)
            continue
    logger.warning("[voice/answer] JSON 파싱 실패, content=%r", content[:200])
    return {"summary": "", "days": [], "tips": []}


class AnswerPlace(BaseModel):
    place_id: int
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    hours: Optional[str] = None
    website: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_url: Optional[str] = None
    source: Optional[str] = None
    license: Optional[str] = None
    blurb: Optional[str] = None
    # 콘텐츠 저작권 게이트 통과 미디어(Wikimedia 등). 각 항목: url/license_label/attribution/...
    media: list[dict] = []


class AnswerDay(BaseModel):
    day: int
    title: str = ""
    items: list[AnswerPlace] = []


class AnswerFestival(BaseModel):
    name: str
    month: Optional[int] = None
    season: Optional[str] = None
    description: Optional[str] = None


class AnswerFood(BaseModel):
    name: str
    description: Optional[str] = None
    scope: Optional[str] = None  # 'city' | 'country'


class AnswerCityContext(BaseModel):
    """그래프 KG(도시↔축제↔음식) 컨텍스트. 미해석 시 None."""
    city_id: str
    city_name: str
    country_code: Optional[str] = None
    festivals: list[AnswerFestival] = []
    foods: list[AnswerFood] = []


class AnswerResponse(BaseModel):
    query: str
    language: str
    location_hint: Optional[str] = None
    summary: str = ""
    days: list[AnswerDay] = []
    tips: list[str] = []
    attribution: str = "© OpenStreetMap contributors (ODbL)"
    candidate_count: int = 0
    city_context: Optional[AnswerCityContext] = None
    # 추천 투명성(법·윤리 체크리스트: 스팸·광고). 본 추천은 오픈데이터 기반 비광고/비제휴 결과.
    sponsored: bool = False
    disclosure: str = "오픈데이터(OSM·Wikidata) 기반 추천 · 광고/제휴 미포함"
    # 응답속도 KPI 측정용 서버측 타이밍(ms): {retrieval, generation, media, total}.
    timing_ms: Optional[dict] = None


class AnswerRequest(BaseModel):
    query: Optional[str] = None
    transcript: Optional[str] = None  # 별칭(음성 경로 호환)
    language: Optional[str] = None
    region_hint: Optional[str] = None
    country_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    days: Optional[int] = None
    max_places: Optional[int] = None
    correlation_id: Optional[str] = None
    feature_id: Optional[str] = None


def _answer_city_context(
    region_hint: Optional[str],
    country_code: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
) -> Optional[AnswerCityContext]:
    """그래프 KG 에서 도시 컨텍스트(이번 달 축제 + 향토 음식) 해석. 미가동 시 None."""
    try:
        from backend.services.tourism_kb.graph import get_city_context

        # 월 필터는 두지 않고 도시의 전 축제를 월순으로 반환 → 클라이언트가 '이번 달' 강조.
        name = (region_hint or "").strip() or None
        ctx = get_city_context(name=name, latitude=latitude, longitude=longitude)
        city = ctx.get("city") if isinstance(ctx, dict) else None
        if not city:
            return None
        festivals = [
            AnswerFestival(
                name=str(f.get("name") or ""),
                month=f.get("month"),
                season=f.get("season") or None,
                description=f.get("description") or None,
            )
            for f in (ctx.get("festivals") or []) if str(f.get("name") or "").strip()
        ][:6]
        foods = [
            AnswerFood(
                name=str(f.get("name") or ""),
                description=f.get("description") or None,
                scope=f.get("scope_type") or None,
            )
            for f in (ctx.get("foods") or []) if str(f.get("name") or "").strip()
        ][:8]
        return AnswerCityContext(
            city_id=str(city.get("id")),
            city_name=str(city.get("name") or city.get("id")),
            country_code=city.get("country_code") or None,
            festivals=festivals,
            foods=foods,
        )
    except Exception as exc:
        logger.warning("[voice/answer] city_context 해석 실패: %s", exc)
        return None


def _assemble_answer_days(plan: dict, candidates: list[dict], max_days: int) -> list[AnswerDay]:
    """LLM plan + 후보 사실 → place_id 검증·서버 사실주입한 일자별 일정."""
    days_out: list[AnswerDay] = []
    raw_days = plan.get("days") if isinstance(plan, dict) else None
    for d in (raw_days or [])[:max_days]:
        if not isinstance(d, dict):
            continue
        items_out: list[AnswerPlace] = []
        seen: set[int] = set()
        for it in (d.get("items") or []):
            if not isinstance(it, dict):
                continue
            try:
                pid = int(it.get("place_id"))
            except (TypeError, ValueError):
                continue
            if pid < 0 or pid >= len(candidates) or pid in seen:
                continue
            seen.add(pid)
            c = candidates[pid]
            blurb = str(it.get("blurb") or "").strip()
            items_out.append(AnswerPlace(
                place_id=pid,
                name=c["name"],
                category=c.get("category") or None,
                address=c.get("address") or None,
                phone=c.get("phone") or None,
                hours=c.get("hours") or None,
                website=c.get("website") or None,
                latitude=c.get("lat"),
                longitude=c.get("lon"),
                map_url=c.get("map_url"),
                source=c.get("source") or None,
                license=c.get("license") or None,
                blurb=_sanitize_friend_reply_for_speech(blurb) or None,
            ))
        if items_out:
            try:
                day_num = int(d.get("day"))
            except (TypeError, ValueError):
                day_num = len(days_out) + 1
            days_out.append(AnswerDay(
                day=day_num,
                title=_sanitize_friend_reply_for_speech(str(d.get("title") or "")),
                items=items_out,
            ))
    return days_out


# ── /answer 결과 캐시(공통 질의 즉시 반환 → E2E <1s) ──────────────────────
def _answer_cache_enabled() -> bool:
    return os.getenv("TOURISM_ANSWER_CACHE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off", ""}


def _answer_cache_ttl() -> int:
    try:
        return max(1, int(os.getenv("TOURISM_ANSWER_CACHE_TTL", "21600")))  # 기본 6h
    except ValueError:
        return 21600


def _answer_cache_key(request: "AnswerRequest", query: str, language: str) -> str:
    # 좌표는 ~11km(소수1자리)로 거칠게 → PII 최소화 + 캐시 적중률 향상.
    def _round(v):
        try:
            return round(float(v), 1)
        except (TypeError, ValueError):
            return None

    parts = [
        "ans", query.strip().lower(), language,
        _round(request.latitude), _round(request.longitude),
        (request.region_hint or "").strip().lower(), (request.country_code or "").strip().lower(),
        request.days or "", request.max_places or "",
    ]
    raw = "|".join(str(p) for p in parts)
    return "tourism:answer:" + hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:32]


def _answer_cache_get(key: str) -> Optional[dict]:
    if not _answer_cache_enabled():
        return None
    try:
        from backend.marketplace.cache_service import cache_service

        return cache_service.get(key)
    except Exception:
        return None


def _answer_cache_store(key: str, payload: dict) -> None:
    if not _answer_cache_enabled():
        return
    try:
        from backend.marketplace.cache_service import cache_service

        cache_service.set(key, payload, _answer_cache_ttl())
    except Exception as exc:
        logger.debug("[voice/answer] 캐시 저장 실패(무시): %s", exc)


def _place_media_enabled() -> bool:
    return os.getenv("TOURISM_PLACE_MEDIA_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off", ""}


async def _attach_place_media(days: list[AnswerDay], candidates: list[dict], *, cap: int = 8) -> None:
    """일정 장소 중 이미지 참조(commons/wikidata)가 있는 것만 Wikimedia 게이트로 보강.

    참조 없는 장소는 네트워크 호출을 하지 않으므로(현 OSM 데이터엔 참조 없음) 지연이 없다.
    실패는 fail-open(미보강) — 추론·응답에 영향 없음.
    """
    if not _place_media_enabled():
        return
    try:
        import asyncio

        from backend.services.tourism_media import has_media_ref, place_media
    except Exception:
        return
    targets: list[AnswerPlace] = []
    for day in days:
        for place in day.items:
            if len(targets) >= cap:
                break
            if 0 <= place.place_id < len(candidates) and has_media_ref(candidates[place.place_id]):
                targets.append(place)
    if not targets:
        return
    try:
        results = await asyncio.gather(
            *[asyncio.to_thread(place_media, candidates[p.place_id]) for p in targets],
            return_exceptions=True,
        )
    except Exception as exc:
        logger.debug("[voice/answer] media 보강 실패(무시): %s", exc)
        return
    for place, media in zip(targets, results):
        if isinstance(media, list) and media:
            place.media = media


@router.post("/voice/answer", response_model=AnswerResponse)
async def voice_answer(request: AnswerRequest):
    """관광 특화 구조화 답변 — RAG(자체 인덱스) → LLM(스키마) → 일자별 일정 JSON.

    /voice/friend-chat(자연어 음성 대화)과 분리된, 화면 카드/일정용 구조화 엔드포인트.
    장소 사실(이름·주소·좌표·지도URL)은 서버가 검색결과에서 주입 → 환각 불가.
    """
    import time as _time

    _t_start = _time.perf_counter()
    _timing = {"retrieval": 0.0, "generation": 0.0, "media": 0.0, "total": 0.0}

    query = (request.query or request.transcript or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query(또는 transcript)가 필요합니다")
    language = (request.language or "ko").strip() or "ko"

    # 캐시 적중 시 LLM 생성 없이 즉시 반환(E2E <1s). 좌표는 거칠게 키잉(PII 최소화).
    _cache_key = _answer_cache_key(request, query, language)
    _cached = _answer_cache_get(_cache_key)
    if _cached:
        try:
            _cached["timing_ms"] = {
                "retrieval": 0.0, "generation": 0.0, "media": 0.0,
                "total": round((_time.perf_counter() - _t_start) * 1000.0, 1),
                "cached": True,
            }
            return AnswerResponse(**_cached)
        except Exception:
            pass  # 캐시 역직렬화 실패 시 정상 경로로 폴백.

    try:
        from backend.services.nadotongryoksa.translator import _llm_lang_label

        language_label = _llm_lang_label(language)
    except Exception:
        language_label = language

    location_hint = _friend_location_hint(
        request.region_hint, request.country_code, request.latitude, request.longitude
    )
    max_places = max(4, min(int(request.max_places or VOICE_ANSWER_MAX_PLACES), 60))

    # 0) 그래프 KG — 도시 컨텍스트(이번 달 축제 + 향토 음식). 미가동 시 None.
    city_context = await asyncio.to_thread(
        _answer_city_context, request.region_hint, request.country_code, request.latitude, request.longitude
    )

    # 1) RAG — 후보 장소 수집. 검색엔 '계획' 표현을 제거한 핵심어를 써 관련도를 높인다.
    _t_r0 = _time.perf_counter()
    search_query = _answer_search_query(query)
    candidates = await asyncio.to_thread(
        _answer_collect_candidates, search_query, request.latitude, request.longitude, limit=max_places
    )
    if not candidates and location_hint:
        candidates = await asyncio.to_thread(
            _answer_collect_candidates,
            f"{location_hint} {search_query}",
            request.latitude,
            request.longitude,
            limit=max_places,
        )
    _timing["retrieval"] = round((_time.perf_counter() - _t_r0) * 1000.0, 1)
    if not candidates:
        # 인덱스 미적재/무결과 → 빈 일정으로 graceful 반환(상위 UI 가 안내).
        _timing["total"] = round((_time.perf_counter() - _t_start) * 1000.0, 1)
        return AnswerResponse(
            query=query, language=language, location_hint=location_hint or None,
            summary="", days=[], tips=[], candidate_count=0, city_context=city_context,
            timing_ms=_timing,
        )

    # 2) LLM 구조화 일정 생성.
    max_days = max(1, min(int(request.days or VOICE_ANSWER_MAX_DAYS), VOICE_ANSWER_MAX_DAYS))
    _t_g0 = _time.perf_counter()
    plan = await _answer_generate(query, language_label, location_hint, candidates, max_days)
    _timing["generation"] = round((_time.perf_counter() - _t_g0) * 1000.0, 1)

    # 3) 서버측 사실 주입 + place_id 검증 → 응답 조립.
    days_out = _assemble_answer_days(plan, candidates, max_days)

    # 3-b) 콘텐츠 저작권 게이트 경유 이미지 보강(참조 있는 장소만, best-effort).
    _t_m0 = _time.perf_counter()
    await _attach_place_media(days_out, candidates)
    _timing["media"] = round((_time.perf_counter() - _t_m0) * 1000.0, 1)

    tips_raw = plan.get("tips") if isinstance(plan, dict) else None
    tips = [
        _sanitize_friend_reply_for_speech(str(t))
        for t in (tips_raw or []) if str(t or "").strip()
    ][:4]
    summary = _sanitize_friend_reply_for_speech(str((plan or {}).get("summary") or ""))

    _timing["total"] = round((_time.perf_counter() - _t_start) * 1000.0, 1)
    logger.info(
        "[voice/answer] lang=%s loc=%s q_len=%d cands=%d days=%d tips=%d t_total=%.0fms t_ret=%.0fms t_gen=%.0fms",
        language, _anonymize_loc_for_log(location_hint), len(query), len(candidates), len(days_out), len(tips),
        _timing["total"], _timing["retrieval"], _timing["generation"],
    )
    response = AnswerResponse(
        query=query,
        language=language,
        location_hint=location_hint or None,
        summary=summary,
        days=days_out,
        tips=tips,
        candidate_count=len(candidates),
        city_context=city_context,
        timing_ms=_timing,
    )
    # 유의미한 결과만 캐시(일정이 있는 경우).
    if days_out:
        _answer_cache_store(_cache_key, response.model_dump())
    return response


def _candidates_preview(candidates: list[dict], limit: int = 12) -> list[dict]:
    """스트리밍 preview 용 장소 목록(LLM 큐레이션 전, 검색 직후 즉시 표시용)."""
    out: list[dict] = []
    for i, c in enumerate(candidates[:limit]):
        out.append({
            "place_id": i,
            "name": c.get("name"),
            "category": c.get("category") or None,
            "address": c.get("address") or None,
            "latitude": c.get("lat"),
            "longitude": c.get("lon"),
            "map_url": c.get("map_url"),
            "source": c.get("source") or None,
        })
    return out


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/voice/answer/stream")
async def voice_answer_stream(request: AnswerRequest):
    """SSE 스트리밍 — 검색 직후 `preview`(장소·도시컨텍스트, <1s)를 먼저 보내고,
    LLM 일정 완료 후 `final`(전체 일정)을 전송. 체감/실측 첫 콘텐츠 지연을 1초 미만으로.

    이벤트: preview → final → done. 캐시 적중 시 final 즉시 전송.
    """
    import time as _time

    _t_start = _time.perf_counter()

    query = (request.query or request.transcript or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query(또는 transcript)가 필요합니다")
    language = (request.language or "ko").strip() or "ko"

    async def _gen():
        cache_key = _answer_cache_key(request, query, language)
        cached = _answer_cache_get(cache_key)
        if cached:
            cached["timing_ms"] = {
                "retrieval": 0.0, "generation": 0.0, "media": 0.0,
                "total": round((_time.perf_counter() - _t_start) * 1000.0, 1), "cached": True,
            }
            yield _sse("final", cached)
            yield _sse("done", {"cached": True})
            return

        try:
            from backend.services.nadotongryoksa.translator import _llm_lang_label

            language_label = _llm_lang_label(language)
        except Exception:
            language_label = language

        location_hint = _friend_location_hint(
            request.region_hint, request.country_code, request.latitude, request.longitude
        )
        max_places = max(4, min(int(request.max_places or VOICE_ANSWER_MAX_PLACES), 60))

        city_context = await asyncio.to_thread(
            _answer_city_context, request.region_hint, request.country_code, request.latitude, request.longitude
        )

        t_r0 = _time.perf_counter()
        search_query = _answer_search_query(query)
        candidates = await asyncio.to_thread(
            _answer_collect_candidates, search_query, request.latitude, request.longitude, limit=max_places
        )
        if not candidates and location_hint:
            candidates = await asyncio.to_thread(
                _answer_collect_candidates, f"{location_hint} {search_query}",
                request.latitude, request.longitude, limit=max_places,
            )
        retrieval_ms = round((_time.perf_counter() - t_r0) * 1000.0, 1)

        # preview — 검색 직후 즉시(<1s) 장소·도시컨텍스트 전송.
        yield _sse("preview", {
            "query": query, "language": language, "location_hint": location_hint or None,
            "city_context": city_context.model_dump() if city_context else None,
            "places": _candidates_preview(candidates),
            "candidate_count": len(candidates),
            "timing_ms": {"retrieval": retrieval_ms, "total": round((_time.perf_counter() - _t_start) * 1000.0, 1)},
        })

        if not candidates:
            empty = AnswerResponse(
                query=query, language=language, location_hint=location_hint or None,
                summary="", days=[], tips=[], candidate_count=0, city_context=city_context,
                timing_ms={"retrieval": retrieval_ms, "generation": 0.0, "media": 0.0,
                           "total": round((_time.perf_counter() - _t_start) * 1000.0, 1)},
            )
            yield _sse("final", empty.model_dump())
            yield _sse("done", {"cached": False})
            return

        # 2) LLM 구조화 일정 생성 → final.
        max_days = max(1, min(int(request.days or VOICE_ANSWER_MAX_DAYS), VOICE_ANSWER_MAX_DAYS))
        t_g0 = _time.perf_counter()
        plan = await _answer_generate(query, language_label, location_hint, candidates, max_days)
        generation_ms = round((_time.perf_counter() - t_g0) * 1000.0, 1)

        days_out = _assemble_answer_days(plan, candidates, max_days)
        await _attach_place_media(days_out, candidates)
        tips = [
            _sanitize_friend_reply_for_speech(str(t))
            for t in ((plan.get("tips") if isinstance(plan, dict) else None) or []) if str(t or "").strip()
        ][:4]
        summary = _sanitize_friend_reply_for_speech(str((plan or {}).get("summary") or ""))
        timing = {"retrieval": retrieval_ms, "generation": generation_ms, "media": 0.0,
                  "total": round((_time.perf_counter() - _t_start) * 1000.0, 1)}
        response = AnswerResponse(
            query=query, language=language, location_hint=location_hint or None,
            summary=summary, days=days_out, tips=tips, candidate_count=len(candidates),
            city_context=city_context, timing_ms=timing,
        )
        if days_out:
            _answer_cache_store(cache_key, response.model_dump())
        yield _sse("final", response.model_dump())
        yield _sse("done", {"cached": False})

    return StreamingResponse(_gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
