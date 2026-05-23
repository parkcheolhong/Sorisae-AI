# -*- coding: utf-8 -*-
"""
🎨 감정 색채 치료사 (Emotion Color Therapist)
감정 분석을 통한 맞춤형 색채 치료 및 심리 케어 시스템
"""

import colorsys
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class EmotionType(Enum):
    """감정 유형"""
    JOY = "기쁨"
    SADNESS = "슬픔"
    ANGER = "분노"
    FEAR = "두려움"
    SURPRISE = "놀라움"
    DISGUST = "혐오"
    LOVE = "사랑"
    PEACE = "평온"
    ANXIETY = "불안"
    EXCITEMENT = "흥분"
    MELANCHOLY = "우울"
    CONFIDENCE = "자신감"


class ColorFamily(Enum):
    """색상 계열"""
    RED = "빨강계열"
    ORANGE = "주황계열"
    YELLOW = "노랑계열"
    GREEN = "초록계열"
    BLUE = "파랑계열"
    PURPLE = "보라계열"
    PINK = "분홍계열"
    BROWN = "갈색계열"
    GRAY = "회색계열"
    WHITE = "흰색계열"
    BLACK = "검정계열"


class TherapyType(Enum):
    """치료 유형"""
    CALMING = "진정 치료"
    ENERGIZING = "활력 치료"
    BALANCING = "균형 치료"
    HEALING = "치유 치료"
    CREATIVE = "창의 치료"
    FOCUS = "집중 치료"


@dataclass
class ColorTherapyColor:
    """색채 치료용 색상"""
    name: str
    hex_code: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[float, float, float]
    emotion_effects: List[str]
    psychological_benefits: List[str]
    usage_recommendations: List[str]
    intensity: float  # 0.0-1.0
    warmth: float     # 0.0(차가움)-1.0(따뜻함)


@dataclass
class TherapySession:
    """치료 세션 데이터"""
    session_id: str
    emotion_analysis: Dict
    recommended_colors: List[ColorTherapyColor]
    therapy_type: TherapyType
    session_duration: int  # 분
    created_at: datetime
    effectiveness_score: float
    user_feedback: Optional[str] = None


class EmotionColorTherapist:
    """감정 색채 치료사"""

    def __init__(self):
        self.setup_logging()

        # 색채 치료 데이터베이스
        self.color_database = {}
        self.emotion_color_mapping = {}
        self.therapy_history = {}
        self.session_counter = 0

        # 치료사 설정
        self.therapist_personality = {
            "empathy_level": 0.9,
            "professional_tone": 0.8,
            "creativity_factor": 0.85,
            "intuition_strength": 0.75
        }

        # 분석 엔진들
        self.emotion_analyzer = EmotionAnalyzer()
        self.color_matcher = ColorMatcher()
        self.therapy_planner = TherapyPlanner()
        self.progress_tracker = ProgressTracker()

        # 초기화
        self._initialize_color_database()
        self._build_emotion_color_mapping()

    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _initialize_color_database(self):
        """색채 데이터베이스 초기화"""

        # 치료용 색상들 정의
        therapy_colors = [
            # 빨강 계열 (에너지, 열정, 활력)
            {
                "name": "코랄 레드", "hex": "#FF6B6B", "rgb": (255, 107, 107),
                "effects": ["활력 증진", "자신감 향상", "적극성 강화"],
                "benefits": ["우울감 완화", "에너지 부족 해결", "동기 부여"],
                "usage": ["아침 시간", "운동 전", "중요한 발표 전"]
            },
            {
                "name": "로즈 핑크", "hex": "#FF8A95", "rgb": (255, 138, 149),
                "effects": ["사랑 느낌", "따뜻함", "포근함"],
                "benefits": ["외로움 해소", "자기애 증진", "관계 개선"],
                "usage": ["휴식 시간", "명상 중", "인간관계 스트레스"]
            },

            # 주황 계열 (따뜻함, 사교성, 창의성)
            {
                "name": "선셋 오렌지", "hex": "#FFA726", "rgb": (255, 167, 38),
                "effects": ["사교성 증진", "창의력 자극", "따뜻한 감정"],
                "benefits": ["사회적 불안 완화", "창작 능력 향상", "소통 능력 개선"],
                "usage": ["팀 작업", "브레인스토밍", "새로운 만남"]
            },

            # 노랑 계열 (기쁨, 낙관, 지적 자극)
            {
                "name": "선샤인 옐로우", "hex": "#FFF176", "rgb": (255, 241, 118),
                "effects": ["기분 향상", "낙관적 사고", "집중력 향상"],
                "benefits": ["우울감 해소", "학습 능력 증진", "긍정적 마인드"],
                "usage": ["공부할 때", "우울할 때", "새로운 도전"]
            },
            {
                "name": "레몬 민트", "hex": "#F4FF81", "rgb": (244, 255, 129),
                "effects": ["정신 맑음", "신선함", "활기"],
                "benefits": ["정신적 피로 회복", "명료한 사고", "스트레스 해소"],
                "usage": ["작업 집중", "결정이 필요할 때", "멘탈 리셋"]
            },

            # 초록 계열 (평온, 성장, 균형)
            {
                "name": "포레스트 그린", "hex": "#81C784", "rgb": (129, 199, 132),
                "effects": ["마음의 평화", "안정감", "성장 욕구"],
                "benefits": ["스트레스 완화", "감정 균형", "자연 치유"],
                "usage": ["명상", "휴식", "자연 속에서"]
            },
            {
                "name": "민트 그린", "hex": "#A8E6CF", "rgb": (168, 230, 207),
                "effects": ["신선함", "평온함", "치유감"],
                "benefits": ["정신적 안정", "회복력 증진", "평화로움"],
                "usage": ["스트레스 상황", "회복 기간", "평온이 필요할 때"]
            },

            # 파랑 계열 (신뢰, 평온, 소통)
            {
                "name": "스카이 블루", "hex": "#81D4FA", "rgb": (129, 212, 250),
                "effects": ["마음의 평화", "신뢰감", "소통 향상"],
                "benefits": ["불안감 완화", "신뢰 관계 구축", "마음의 안정"],
                "usage": ["중요한 대화", "불안할 때", "신뢰 구축"]
            },
            {
                "name": "딥 네이비", "hex": "#3F51B5", "rgb": (63, 81, 181),
                "effects": ["깊은 사고", "집중력", "지혜"],
                "benefits": ["깊은 성찰", "논리적 사고", "내적 평화"],
                "usage": ["깊은 사고", "중요한 결정", "성찰 시간"]
            },

            # 보라 계열 (창의성, 영성, 변화)
            {
                "name": "라벤더", "hex": "#CE93D8", "rgb": (206, 147, 216),
                "effects": ["창의적 영감", "영적 평화", "상상력"],
                "benefits": ["창작 능력 향상", "영적 성장", "내면의 평화"],
                "usage": ["창작 활동", "명상", "예술 활동"]
            },
            {
                "name": "로얄 퍼플", "hex": "#9C27B0", "rgb": (156, 39, 176),
                "effects": ["고귀함", "변화 욕구", "개성"],
                "benefits": ["자존감 향상", "개성 표현", "변화 수용"],
                "usage": ["자기 표현", "변화 시기", "특별한 순간"]
            },

            # 중성 계열 (균형, 안정, 포근함)
            {
                "name": "웜 그레이", "hex": "#BCAAA4", "rgb": (188, 170, 164),
                "effects": ["균형감", "안정감", "포근함"],
                "benefits": ["감정 중립", "안정된 마음", "균형 회복"],
                "usage": ["감정 과부하", "균형이 필요할 때", "중립적 상황"]
            },
            {
                "name": "아이보리", "hex": "#FFF8E1", "rgb": (255, 248, 225),
                "effects": ["순수함", "평화", "새로운 시작"],
                "benefits": ["마음 정화", "새 출발", "순수한 마음"],
                "usage": ["새로운 시작", "마음 정리", "순수한 감정"]
            }
        ]

        # 색상 객체 생성
        for color_data in therapy_colors:
            rgb = color_data["rgb"]
            hsl = self._rgb_to_hsl(rgb)

            color_obj = ColorTherapyColor(
                name=color_data["name"],
                hex_code=color_data["hex"],
                rgb=rgb,
                hsl=hsl,
                emotion_effects=color_data["effects"],
                psychological_benefits=color_data["benefits"],
                usage_recommendations=color_data["usage"],
                intensity=self._calculate_intensity(rgb),
                warmth=self._calculate_warmth(hsl[0])
            )

            self.color_database[color_data["name"]] = color_obj

    def _rgb_to_hsl(self, rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """RGB를 HSL로 변환"""
        r, g, b = [x / 255.0 for x in rgb]
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return (h * 360, s, l)

    def _calculate_intensity(self, rgb: Tuple[int, int, int]) -> float:
        """색상 강도 계산"""
        r, g, b = rgb
        # 색상의 채도와 명도를 기반으로 강도 계산
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        intensity = (max_val - min_val) / 255.0
        return round(intensity, 2)

    def _calculate_warmth(self, hue: float) -> float:
        """색상 온도 계산 (0: 차가움, 1: 따뜻함)"""
        # 빨강-노랑 (0-60, 300-360): 따뜻함
        # 파랑-초록 (120-240): 차가움
        if 0 <= hue <= 60 or 300 <= hue <= 360:
            return 0.8 + (random.uniform(-0.1, 0.2))
        elif 120 <= hue <= 240:
            return 0.2 + (random.uniform(-0.1, 0.2))
        else:
            return 0.5 + (random.uniform(-0.2, 0.2))

    def _build_emotion_color_mapping(self):
        """감정-색상 매핑 구축"""
        self.emotion_color_mapping = {
            EmotionType.JOY: ["선샤인 옐로우", "선셋 오렌지", "코랄 레드"],
            EmotionType.SADNESS: ["스카이 블루", "포레스트 그린", "라벤더"],
            EmotionType.ANGER: ["딥 네이비", "포레스트 그린", "웜 그레이"],
            EmotionType.FEAR: ["민트 그린", "아이보리", "라벤더"],
            EmotionType.ANXIETY: ["포레스트 그린", "스카이 블루", "웜 그레이"],
            EmotionType.LOVE: ["로즈 핑크", "라벤더", "아이보리"],
            EmotionType.PEACE: ["민트 그린", "스카이 블루", "아이보리"],
            EmotionType.EXCITEMENT: ["코랄 레드", "선셋 오렌지", "로얄 퍼플"],
            EmotionType.MELANCHOLY: ["딥 네이비", "웜 그레이", "라벤더"],
            EmotionType.CONFIDENCE: ["코랄 레드", "로얄 퍼플", "선샤인 옐로우"]
        }

    def analyze_emotion(self, emotion_input: str, context: str = "") -> Dict:
        """감정 분석"""
        try:
            # 기본 감정 분석
            detected_emotions = self._detect_emotions_from_text(emotion_input)

            # 컨텍스트 분석
            context_factors = self._analyze_context(context)

            # 감정 강도 측정
            intensity_score = self._measure_emotion_intensity(emotion_input)

            # 감정 복합성 분석
            complexity = self._analyze_emotion_complexity(detected_emotions)

            analysis_result = {
                "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "primary_emotion": detected_emotions[0] if detected_emotions else EmotionType.PEACE,
                "secondary_emotions": detected_emotions[1:3] if len(detected_emotions) > 1 else [],
                "emotion_intensity": intensity_score,
                "emotion_complexity": complexity,
                "context_factors": context_factors,
                "recommended_approach": self._determine_therapy_approach(detected_emotions, intensity_score),
                "urgency_level": self._assess_urgency(detected_emotions, intensity_score)
            }

            return analysis_result

        except Exception as e:
            self.logger.error(f"감정 분석 오류: {e}")
            return {"error": str(e)}

    def _detect_emotions_from_text(self, text: str) -> List[EmotionType]:
        """텍스트에서 감정 감지"""
        emotion_keywords = {
            EmotionType.JOY: ["기쁘", "행복", "즐거", "좋", "신나", "기분좋", "만족", "웃음"],
            EmotionType.SADNESS: ["슬프", "우울", "눈물", "서러", "아프", "힘들", "괴로", "그리워"],
            EmotionType.ANGER: ["화나", "짜증", "분노", "억울", "열받", "빡쳐", "미치", "약올려"],
            EmotionType.FEAR: ["무서", "두려", "걱정", "불안", "떨려", "겁나", "공포", "심장"],
            EmotionType.ANXIETY: ["불안", "초조", "걱정", "긴장", "스트레스", "압박", "부담"],
            EmotionType.LOVE: ["사랑", "좋아해", "소중", "따뜻", "애정", "마음", "설레"],
            EmotionType.EXCITEMENT: ["신나", "흥분", "기대", "두근", "활기", "열정"],
            EmotionType.MELANCHOLY: ["우울", "쓸쓸", "외로", "허전", "공허", "막막"],
            EmotionType.CONFIDENCE: ["자신", "확신", "당당", "믿어", "할수있", "가능"]
        }

        text_lower = text.lower()
        detected = []

        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected.append(emotion)
                    break

        # 감정이 감지되지 않으면 기본 평온 상태
        if not detected:
            detected.append(EmotionType.PEACE)

        return detected[:3]  # 최대 3개까지

    def _analyze_context(self, context: str) -> Dict:
        """컨텍스트 분석"""
        context_keywords = {
            "work": ["일", "업무", "회사", "직장", "프로젝트", "업무"],
            "relationship": ["사람", "친구", "가족", "연인", "관계", "소통"],
            "health": ["몸", "건강", "아픔", "병", "치료", "회복"],
            "finance": ["돈", "경제", "재정", "비용", "수입", "지출"],
            "study": ["공부", "학습", "시험", "성적", "학교", "교육"],
            "personal": ["자아", "성장", "발전", "꿈", "목표", "미래"]
        }

        context_lower = context.lower()
        detected_contexts = []

        for category, keywords in context_keywords.items():
            for keyword in keywords:
                if keyword in context_lower:
                    detected_contexts.append(category)
                    break

        return {
            "primary_context": detected_contexts[0] if detected_contexts else "general",
            "context_categories": detected_contexts,
            "context_complexity": len(detected_contexts)
        }

    def _measure_emotion_intensity(self, text: str) -> float:
        """감정 강도 측정"""
        intensity_indicators = [
            "정말", "너무", "완전", "진짜", "엄청", "매우", "굉장히", "심각하게",
            "!!!!", "!!", "ㅠㅠ", "ㅜㅜ", "ㅎㅎ", "ㅋㅋ", "하하"
        ]

        base_intensity = 0.5
        text_lower = text.lower()

        for indicator in intensity_indicators:
            if indicator in text_lower:
                base_intensity += 0.1

        # 텍스트 길이도 감정 강도에 영향
        length_factor = min(len(text) / 100, 0.3)

        return min(base_intensity + length_factor, 1.0)

    def _analyze_emotion_complexity(self, emotions: List[EmotionType]) -> str:
        """감정 복합성 분석"""
        if len(emotions) == 1:
            return "단순감정"
        elif len(emotions) == 2:
            return "이중감정"
        else:
            return "복합감정"

    def _determine_therapy_approach(self, emotions: List[EmotionType], intensity: float) -> TherapyType:
        """치료 접근법 결정"""
        if not emotions:
            return TherapyType.BALANCING

        primary_emotion = emotions[0]

        # 고강도 감정 처리
        if intensity > 0.8:
            if primary_emotion in [EmotionType.ANGER, EmotionType.ANXIETY]:
                return TherapyType.CALMING
            elif primary_emotion in [EmotionType.SADNESS, EmotionType.MELANCHOLY]:
                return TherapyType.HEALING

        # 일반적인 접근법
        emotion_therapy_map = {
            EmotionType.JOY: TherapyType.BALANCING,
            EmotionType.SADNESS: TherapyType.HEALING,
            EmotionType.ANGER: TherapyType.CALMING,
            EmotionType.ANXIETY: TherapyType.CALMING,
            EmotionType.FEAR: TherapyType.CALMING,
            EmotionType.EXCITEMENT: TherapyType.BALANCING,
            EmotionType.MELANCHOLY: TherapyType.ENERGIZING,
            EmotionType.CONFIDENCE: TherapyType.CREATIVE
        }

        return emotion_therapy_map.get(primary_emotion, TherapyType.BALANCING)

    def _assess_urgency(self, emotions: List[EmotionType], intensity: float) -> str:
        """긴급성 평가"""
        high_urgency_emotions = [EmotionType.ANGER, EmotionType.ANXIETY, EmotionType.FEAR]

        if any(emotion in high_urgency_emotions for emotion in emotions) and intensity > 0.7:
            return "높음"
        elif intensity > 0.6:
            return "보통"
        else:
            return "낮음"

    def recommend_colors(self, emotion_analysis: Dict, preference: str = "균형") -> List[ColorTherapyColor]:
        """색상 추천"""
        try:
            primary_emotion = emotion_analysis.get("primary_emotion")
            therapy_approach = emotion_analysis.get("recommended_approach")
            intensity = emotion_analysis.get("emotion_intensity", 0.5)

            # 기본 추천 색상들
            base_colors = self.emotion_color_mapping.get(primary_emotion, ["웜 그레이"])

            # 치료 접근법에 따른 색상 조정
            adjusted_colors = self._adjust_colors_for_therapy(base_colors, therapy_approach, intensity)

            # 사용자 선호도 반영
            final_colors = self._apply_user_preference(adjusted_colors, preference)

            # 색상 객체 반환
            recommended = []
            for color_name in final_colors[:4]:  # 최대 4개
                if color_name in self.color_database:
                    recommended.append(self.color_database[color_name])

            # 추가 맞춤 색상 생성
            if len(recommended) < 3:
                custom_colors = self._generate_custom_colors(primary_emotion, therapy_approach)
                recommended.extend(custom_colors[:3 - len(recommended)])

            return recommended

        except Exception as e:
            self.logger.error(f"색상 추천 오류: {e}")
            return [self.color_database["웜 그레이"]]

    def _adjust_colors_for_therapy(
            self,
            base_colors: List[str],
            therapy_type: TherapyType,
            intensity: float) -> List[str]:
        """치료 접근법에 따른 색상 조정"""
        therapy_adjustments = {
            TherapyType.CALMING: {
                "add": ["민트 그린", "스카이 블루", "라벤더"],
                "remove": ["코랄 레드", "선셋 오렌지"]
            },
            TherapyType.ENERGIZING: {
                "add": ["코랄 레드", "선셋 오렌지", "선샤인 옐로우"],
                "remove": ["딥 네이비", "웜 그레이"]
            },
            TherapyType.HEALING: {
                "add": ["포레스트 그린", "라벤더", "아이보리"],
                "remove": ["로얄 퍼플"]
            },
            TherapyType.BALANCING: {
                "add": ["웜 그레이", "민트 그린"],
                "remove": []
            }
        }

        adjustments = therapy_adjustments.get(therapy_type, {"add": [], "remove": []})

        # 기본 색상에서 제거할 색상들 제거
        adjusted = [color for color in base_colors if color not in adjustments["remove"]]

        # 추가할 색상들 추가
        for add_color in adjustments["add"]:
            if add_color not in adjusted:
                adjusted.append(add_color)

        return adjusted

    def _apply_user_preference(self, colors: List[str], preference: str) -> List[str]:
        """사용자 선호도 반영"""
        preference_filters = {
            "따뜻함": lambda c: self.color_database[c].warmth > 0.6,
            "차가움": lambda c: self.color_database[c].warmth < 0.4,
            "강렬함": lambda c: self.color_database[c].intensity > 0.6,
            "부드러움": lambda c: self.color_database[c].intensity < 0.4,
            "균형": lambda c: True  # 모든 색상 허용
        }

        filter_func = preference_filters.get(preference, preference_filters["균형"])

        # 선호도에 맞는 색상 필터링
        filtered = [color for color in colors if filter_func(color)]

        # 필터링 결과가 부족하면 원본 반환
        if len(filtered) < 2:
            return colors

        return filtered

    def _generate_custom_colors(self, emotion: EmotionType, therapy_type: TherapyType) -> List[ColorTherapyColor]:
        """맞춤형 색상 생성"""
        # 간단한 맞춤 색상 생성 (실제로는 더 복잡한 알고리즘 사용)
        custom_colors = []

        if emotion == EmotionType.PEACE and therapy_type == TherapyType.BALANCING:
            custom_color = ColorTherapyColor(
                name="평화의 청록",
                hex_code="#7FCDCD",
                rgb=(127, 205, 205),
                hsl=self._rgb_to_hsl((127, 205, 205)),
                emotion_effects=["마음의 평화", "균형감", "안정감"],
                psychological_benefits=["정신적 안정", "균형 회복", "평온함"],
                usage_recommendations=["명상", "휴식", "균형 필요시"],
                intensity=0.4,
                warmth=0.3
            )
            custom_colors.append(custom_color)

        return custom_colors

    def create_therapy_session(self, emotion_input: str, context: str = "",
                               preference: str = "균형", duration: int = 15) -> TherapySession:
        """치료 세션 생성"""
        try:
            self.session_counter += 1
            session_id = f"CT-{datetime.now().strftime('%Y%m%d')}-{self.session_counter:03d}"

            # 감정 분석
            emotion_analysis = self.analyze_emotion(emotion_input, context)

            # 색상 추천
            recommended_colors = self.recommend_colors(emotion_analysis, preference)

            # 치료 유형 결정
            therapy_type = emotion_analysis.get("recommended_approach", TherapyType.BALANCING)

            # 효과성 점수 예측
            effectiveness = self._predict_effectiveness(emotion_analysis, recommended_colors)

            # 세션 생성
            session = TherapySession(
                session_id=session_id,
                emotion_analysis=emotion_analysis,
                recommended_colors=recommended_colors,
                therapy_type=therapy_type,
                session_duration=duration,
                created_at=datetime.now(),
                effectiveness_score=effectiveness
            )

            # 세션 저장
            self.therapy_history[session_id] = session

            return session

        except Exception as e:
            self.logger.error(f"치료 세션 생성 오류: {e}")
            return None

    def _predict_effectiveness(self, emotion_analysis: Dict, colors: List[ColorTherapyColor]) -> float:
        """치료 효과성 예측"""
        base_score = 0.7

        # 감정 분석 품질
        if emotion_analysis.get("emotion_complexity") == "단순감정":
            base_score += 0.1

        # 색상 매칭 품질
        if len(colors) >= 3:
            base_score += 0.1

        # 긴급성 고려
        urgency = emotion_analysis.get("urgency_level", "낮음")
        if urgency == "높음":
            base_score += 0.05  # 높은 긴급성일 때 더 효과적

        return min(base_score, 0.95)

    def generate_therapy_plan(self, session: TherapySession) -> Dict:
        """치료 계획 생성"""
        try:
            plan = {
                "session_info": {
                    "session_id": session.session_id,
                    "therapy_type": session.therapy_type.value,
                    "duration": session.session_duration,
                    "created_at": session.created_at.strftime("%Y-%m-%d %H:%M")
                },
                "color_therapy": {
                    "primary_colors": [],
                    "secondary_colors": [],
                    "usage_schedule": [],
                    "application_methods": []
                },
                "activities": [],
                "mindfulness_exercises": [],
                "progress_indicators": [],
                "follow_up": {}
            }

            # 색상 치료 계획
            colors = session.recommended_colors
            if colors:
                plan["color_therapy"]["primary_colors"] = [
                    {
                        "name": color.name,
                        "hex": color.hex_code,
                        "effects": color.emotion_effects,
                        "usage": color.usage_recommendations
                    }
                    for color in colors[:2]
                ]

                plan["color_therapy"]["secondary_colors"] = [
                    {
                        "name": color.name,
                        "hex": color.hex_code,
                        "effects": color.emotion_effects
                    }
                    for color in colors[2:4]
                ]

            # 사용 일정
            plan["color_therapy"]["usage_schedule"] = self._create_usage_schedule(session)

            # 적용 방법
            plan["color_therapy"]["application_methods"] = self._suggest_application_methods(session)

            # 활동 추천
            plan["activities"] = self._recommend_activities(session)

            # 마음챙김 연습
            plan["mindfulness_exercises"] = self._suggest_mindfulness_exercises(session)

            # 진행 지표
            plan["progress_indicators"] = self._define_progress_indicators(session)

            # 후속 조치
            plan["follow_up"] = self._plan_follow_up(session)

            return plan

        except Exception as e:
            self.logger.error(f"치료 계획 생성 오류: {e}")
            return {"error": str(e)}

    def _create_usage_schedule(self, session: TherapySession) -> List[Dict]:
        """사용 일정 생성"""
        schedule = []
        colors = session.recommended_colors

        if not colors:
            return schedule

        # 기본 일정 템플릿
        time_slots = [
            {"time": "아침 (07:00-09:00)", "purpose": "하루 시작 에너지"},
            {"time": "오전 (10:00-12:00)", "purpose": "집중력 향상"},
            {"time": "오후 (14:00-16:00)", "purpose": "활력 충전"},
            {"time": "저녁 (18:00-20:00)", "purpose": "감정 정리"},
            {"time": "밤 (21:00-23:00)", "purpose": "마음 안정"}
        ]

        # 치료 유형별 일정 조정
        if session.therapy_type == TherapyType.CALMING:
            priority_times = ["저녁 (18:00-20:00)", "밤 (21:00-23:00)"]
        elif session.therapy_type == TherapyType.ENERGIZING:
            priority_times = ["아침 (07:00-09:00)", "오전 (10:00-12:00)"]
        else:
            priority_times = ["오후 (14:00-16:00)", "저녁 (18:00-20:00)"]

        # 우선 시간대에 주요 색상 배정
        for i, time_slot in enumerate(time_slots):
            if time_slot["time"] in priority_times and i < len(colors):
                color = colors[i % len(colors)]
                schedule.append({
                    "time": time_slot["time"],
                    "color": color.name,
                    "hex": color.hex_code,
                    "purpose": time_slot["purpose"],
                    "method": "시각적 집중 (5-10분)"
                })

        return schedule[:3]  # 최대 3개 시간대

    def _suggest_application_methods(self, session: TherapySession) -> List[str]:
        """적용 방법 제안"""
        methods = [
            "🖼️ 색상 이미지나 그림을 벽에 걸어두고 바라보기",
            "🎨 해당 색상으로 간단한 그림이나 만다라 그리기",
            "👔 추천 색상의 옷이나 액세서리 착용하기",
            "💡 색상 조명이나 컬러 전구 사용하기",
            "🧘 색상을 시각화하며 명상하기",
            "📱 스마트폰 배경화면을 추천 색상으로 설정",
            "🌈 색상 카드를 만들어 수시로 보기",
            "🎵 색상과 어울리는 음악과 함께 감상"
        ]

        # 치료 유형별 맞춤 방법
        if session.therapy_type == TherapyType.CREATIVE:
            return methods[:6] + ["🎨 창작 활동에 추천 색상 적극 활용"]
        elif session.therapy_type == TherapyType.CALMING:
            return [methods[4], methods[3], methods[0]] + ["🛁 컬러 테라피 입욕"]

        return methods[:5]

    def _recommend_activities(self, session: TherapySession) -> List[str]:
        """활동 추천"""
        base_activities = [
            "색상 일기 작성하기 - 하루 감정을 색으로 표현",
            "색상 명상 - 추천 색상을 마음 속으로 그리며 호흡",
            "색상 산책 - 주변에서 추천 색상 찾아보기",
            "색상 음식 섭취 - 추천 색상과 비슷한 건강한 음식"
        ]

        # 감정별 특화 활동
        primary_emotion = session.emotion_analysis.get("primary_emotion")

        if primary_emotion == EmotionType.SADNESS:
            base_activities.extend([
                "따뜻한 색상의 차나 음료 마시기",
                "밝은 색상의 꽃이나 식물 키우기"
            ])
        elif primary_emotion == EmotionType.ANGER:
            base_activities.extend([
                "차가운 색상의 물로 세수하기",
                "푸른 하늘이나 바다 사진 보기"
            ])
        elif primary_emotion == EmotionType.ANXIETY:
            base_activities.extend([
                "초록색 자연 환경에서 시간 보내기",
                "부드러운 색상의 음악 듣기"
            ])

        return base_activities[:5]

    def _suggest_mindfulness_exercises(self, session: TherapySession) -> List[str]:
        """마음챙김 연습 제안"""
        exercises = [
            "색상 호흡법 - 숨을 들이쉴 때 치유 색상을 상상하고, 내쉴 때 부정적 감정을 배출",
            "색상 바디스캔 - 몸 각 부위에 치유 색상이 스며들어가는 것을 상상",
            "색상 감사 명상 - 좋아하는 색상과 관련된 감사한 일들 떠올리기",
            "색상 시각화 - 마음의 눈으로 치유 색상이 감싸주는 것을 느끼기"
        ]

        return exercises

    def _define_progress_indicators(self, session: TherapySession) -> List[str]:
        """진행 지표 정의"""
        return [
            "감정 안정도 (1-10 척도로 매일 체크)",
            "색상에 대한 반응 변화 기록",
            "수면의 질 개선 정도",
            "일상 활동에서의 기분 변화",
            "스트레스 수준 변화 추이"
        ]

    def _plan_follow_up(self, session: TherapySession) -> Dict:
        """후속 조치 계획"""
        return {
            "check_in_schedule": "3일 후, 1주일 후, 2주일 후",
            "session_duration": f"{session.session_duration}분씩 매일",
            "adjustment_timeline": "1주일 후 색상 조정 검토",
            "emergency_colors": ["민트 그린", "스카이 블루"] if session.therapy_type == TherapyType.CALMING else ["선샤인 옐로우"],
            "progress_review": "2주일 후 전체 프로그램 평가"
        }

    def get_session_report(self, session_id: str) -> str:
        """세션 보고서 생성"""
        if session_id not in self.therapy_history:
            return "세션을 찾을 수 없습니다."

        session = self.therapy_history[session_id]
        plan = self.generate_therapy_plan(session)

        # 보고서 생성
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("🎨 감정 색채 치료 세션 보고서")
        report_lines.append("=" * 60)
        report_lines.append(f"세션 ID: {session.session_id}")
        report_lines.append(f"생성 시간: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"치료 유형: {session.therapy_type.value}")
        report_lines.append(f"예상 효과: {session.effectiveness_score:.1%}")
        report_lines.append("")

        # 감정 분석 결과
        emotion_analysis = session.emotion_analysis
        report_lines.append("📊 감정 분석")
        _pe = emotion_analysis.get('primary_emotion', '미상')
        _pe_val = _pe.value if hasattr(_pe, 'value') else '미상'
        report_lines.append(f"  주감정: {_pe_val}")
        report_lines.append(f"  감정 강도: {emotion_analysis.get('emotion_intensity', 0):.1%}")
        report_lines.append(f"  복합성: {emotion_analysis.get('emotion_complexity', '미상')}")
        report_lines.append(f"  긴급도: {emotion_analysis.get('urgency_level', '미상')}")
        report_lines.append("")

        # 추천 색상
        report_lines.append("🎨 추천 색상")
        for i, color in enumerate(session.recommended_colors[:3], 1):
            report_lines.append(f"  {i}. {color.name} ({color.hex_code})")
            report_lines.append(f"     효과: {', '.join(color.emotion_effects[:2])}")
            report_lines.append(f"     온도: {'따뜻함' if color.warmth > 0.6 else '차가움' if color.warmth < 0.4 else '중성'}")
        report_lines.append("")

        # 사용 방법
        methods = plan.get("color_therapy", {}).get("application_methods", [])
        if methods:
            report_lines.append("💡 사용 방법")
            for method in methods[:3]:
                report_lines.append(f"  • {method}")

        report_lines.append("")

        # 권장 활동
        activities = plan.get("activities", [])
        if activities:
            report_lines.append("🎯 권장 활동")
            for activity in activities[:3]:
                report_lines.append(f"  • {activity}")

        report_lines.append("=" * 60)
        return "\n".join(report_lines)

    def get_therapist_stats(self) -> Dict:
        """치료사 통계"""
        total_sessions = len(self.therapy_history)

        if total_sessions == 0:
            return {
                "total_sessions": 0,
                "average_effectiveness": 0.0,
                "most_common_emotion": "없음",
                "most_used_therapy": "없음"
            }

        # 효과성 평균
        effectiveness_scores = [s.effectiveness_score for s in self.therapy_history.values()]
        avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores)

        # 가장 많이 다룬 감정
        emotions = [s.emotion_analysis.get("primary_emotion") for s in self.therapy_history.values()]
        emotion_counts = {}
        for emotion in emotions:
            if emotion and hasattr(emotion, 'value'):
                emotion_counts[emotion.value] = emotion_counts.get(emotion.value, 0) + 1

        most_common_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else "없음"

        # 가장 많이 사용된 치료법
        therapies = [s.therapy_type.value for s in self.therapy_history.values()]
        therapy_counts = {}
        for therapy in therapies:
            therapy_counts[therapy] = therapy_counts.get(therapy, 0) + 1

        most_used_therapy = max(therapy_counts.items(), key=lambda x: x[1])[0] if therapy_counts else "없음"

        return {
            "total_sessions": total_sessions,
            "average_effectiveness": avg_effectiveness,
            "most_common_emotion": most_common_emotion,
            "most_used_therapy": most_used_therapy,
            "color_database_size": len(self.color_database),
            "therapist_experience": total_sessions * 0.1  # 경험치
        }


# 보조 클래스들


class EmotionAnalyzer:
    """감정 분석기"""

    def analyze_text_emotion(self, text: str) -> Dict:
        return {"primary": "평온", "intensity": 0.5}


class ColorMatcher:
    """색상 매처"""

    def match_emotion_to_color(self, emotion: str) -> str:
        return "웜 그레이"


class TherapyPlanner:
    """치료 계획자"""

    def create_plan(self, session_data: Dict) -> Dict:
        return {"plan": "기본 계획"}


class ProgressTracker:
    """진행 추적기"""

    def track_progress(self, session_id: str) -> Dict:
        return {"progress": "진행 중"}



def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 감정 색채 치료"""
    context = context or {}
    emotion_text = str(context.get('emotion_text', '요즘 많이 지치고 힘들어요'))
    try:
        therapist = EmotionColorTherapist()
        emotion_analysis = therapist.analyze_emotion(emotion_text)
        colors = therapist.recommend_colors(emotion_analysis)
        return {
            'status': 'ok',
            'input_text': emotion_text,
            'emotion_detected': emotion_analysis.get('primary_emotion', '알 수 없음') if isinstance(emotion_analysis, dict) else str(emotion_analysis),
            'recommended_colors': [
                {'name': c.name, 'hex': c.hex_code, 'effect': c.emotion_effects[0] if c.emotion_effects else ''}
                for c in (colors[:3] if hasattr(colors, '__iter__') else [])
            ],
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

if __name__ == "__main__":
    # 테스트 코드
    therapist = EmotionColorTherapist()

    print("🎨 감정 색채 치료사 테스트")
    print("=" * 50)

    # 감정 분석 테스트
    emotion_analysis = therapist.analyze_emotion("요즘 너무 스트레스받고 불안해요", "업무 때문에")
    print(f"✅ 감정 분석: {emotion_analysis.get('primary_emotion', '미상')}")

    # 치료 세션 생성
    session = therapist.create_therapy_session(
        "우울하고 기분이 안 좋아요",
        "인간관계 때문에 힘들어요",
        "따뜻함"
    )

    if session:
        print(f"✅ 치료 세션 생성: {session.session_id}")
        print(f"   치료 유형: {session.therapy_type.value}")
        print(f"   추천 색상: {len(session.recommended_colors)}개")

        for color in session.recommended_colors:
            print(f"   🎨 {color.name} ({color.hex_code})")

    # 치료 계획 생성
    if session:
        plan = therapist.generate_therapy_plan(session)
        print(f"✅ 치료 계획 생성 완료")

        primary_colors = plan.get("color_therapy", {}).get("primary_colors", [])
        if primary_colors:
            print(f"   주요 색상: {primary_colors[0]['name']}")

    # 통계
    stats = therapist.get_therapist_stats()
    print(f"✅ 치료사 통계: 세션 {stats['total_sessions']}건")

    print("\n🎯 감정 색채 치료사 테스트 완료!")
