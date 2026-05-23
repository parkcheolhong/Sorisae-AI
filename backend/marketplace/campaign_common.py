from __future__ import annotations

import re
from typing import List, Optional


ROLE_KEYWORDS = {
    "animal": ["강아지", "고양이", "동물", "말", "새", "반려"],
    "human": ["사람", "남자", "여자", "노인", "아이", "학생", "직장인", "여성", "남성", "친구"],
    "character": ["캐릭터", "로봇", "마스코트"],
}

LOCATION_KEYWORDS = {
    "restaurant": ["식당", "짜장면집", "카페", "레스토랑"],
    "home": ["집", "거실", "주방", "방"],
    "street": ["거리", "길", "도로", "시장"],
    "office": ["사무실", "오피스", "회의실"],
    "outdoor": ["공원", "야외", "해변", "산"],
}

EMOTION_KEYWORDS = {
    "surprised": ["놀라", "깜짝"],
    "happy": ["기쁘", "좋아", "행복", "웃"],
    "satisfied": ["만족", "맛있", "흡족"],
    "urgent": ["빨리", "급히", "서둘"],
}

ACTION_KEYWORDS = {
    "eat_drink": ["먹", "마시", "시식"],
    "call": ["전화", "통화", "부르", "오라고"],
    "move": ["가", "오", "걷", "달리", "이동"],
    "showcase": ["보여", "설명", "소개", "시연"],
    "react": ["반응", "감탄", "만족", "놀라"],
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def split_sentences(value: str) -> List[str]:
    normalized = normalize_text(value)
    if not normalized:
        return []
    return [
        item.strip()
        for item in re.sub(r"\s*(그리고|그 뒤|그 후|이후|다음에|then|and then)\s+", "|", normalized, flags=re.IGNORECASE).split("|")
        for item in re.split(r"[.!?。]+", item)
        if item.strip()
    ]


def extract_object(value: str) -> Optional[str]:
    normalized = normalize_text(value)
    matches = list(re.finditer(r"([가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+){0,2})\s*(?:을|를)", normalized))
    if matches:
        return matches[-1].group(1).strip()
    return None


def infer_role_type(value: str) -> str:
    normalized = normalize_text(value)
    for role_type, keywords in ROLE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return role_type
    return "human"


def infer_location_type(value: str) -> str:
    normalized = normalize_text(value)
    for location_type, keywords in LOCATION_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return location_type
    return "mixed"


def infer_emotion(value: str) -> str:
    normalized = normalize_text(value)
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return emotion
    return "neutral"


def infer_action_type(value: str) -> str:
    normalized = normalize_text(value)
    for action, keywords in ACTION_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return action
    return "narrative"


def infer_object_type(value: str) -> str:
    object_name = extract_object(value)
    return object_name or "dynamic_object"
