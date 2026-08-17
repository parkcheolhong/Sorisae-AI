#!/usr/bin/env python3
"""
🎤⚡ 소리새 음성 반응형 업그레이드 시스템
Sorisae Voice Reactive Upgrade System

음성 반응형 기능을 통해 더 빠르고 지능적인 음성 상호작용을 제공합니다:
- 실시간 감정 분석 (Real-time Emotion Detection)
- 적응형 응답 생성 (Adaptive Response Generation)
- 빠른 음성 명령 (Quick Voice Commands)
- 다중 웨이크 워드 감지 (Multi Wake Word Detection)
- 음성 피드백 시스템 (Voice Feedback System)
- 사용자 패턴 학습 (User Pattern Learning)
"""

import logging
import os
import platform
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

# 전역 종료 플래그
SHUTDOWN_REQUESTED = False

# 음성 인식 및 합성
try:
    import pyttsx3
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("⚠️ 음성 라이브러리 설치 필요: pip install speechrecognition pyttsx3")

# gTTS 대체 TTS (pyttsx3 실패 시 사용)
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


def _play_audio_file(file_path: str) -> bool:
    """플랫폼별 오디오 파일 재생 헬퍼 함수"""
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["afplay", file_path], check=True)
            return True
        elif system == "Linux":
            for player in ["mpg123", "mpg321", "ffplay", "aplay"]:
                try:
                    subprocess.run([player, "-q", file_path], check=True, timeout=30)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                    continue
        elif system == "Windows":
            os.startfile(file_path)
            return True
    except Exception:
        pass
    return False


@dataclass
class VoiceEmotion:
    """음성 감정 분석 결과"""
    emotion: str  # happy, sad, angry, neutral, excited, worried
    confidence: float
    intensity: float  # 0.0 ~ 1.0
    timestamp: str


@dataclass
class QuickCommand:
    """빠른 음성 명령"""
    trigger_phrase: str
    action: str
    response_template: str
    priority: int = 0


@dataclass
class UserPattern:
    """사용자 패턴"""
    user_id: str
    command_frequency: Dict[str, int] = field(default_factory=dict)
    preferred_response_style: str = "default"
    emotion_history: List[VoiceEmotion] = field(default_factory=list)
    last_active: str = ""
    total_interactions: int = 0


@dataclass
class ReactiveResponse:
    """반응형 응답"""
    text: str
    emotion_adapted: bool
    user_pattern_applied: bool
    response_time_ms: float
    feedback_type: str  # audio, visual, haptic


class EmotionAnalyzer:
    """음성 감정 분석기"""

    def __init__(self):
        self.logger = logging.getLogger('EmotionAnalyzer')

        # 감정 키워드 패턴
        self.emotion_keywords = {
            'happy': ['행복', '기쁘', '좋아', '즐거', '신나', '최고', '짱', 'happy', 'great', 'good', 'wonderful'],
            'sad': ['슬프', '우울', '힘들', '지쳐', '외로', '괴로', 'sad', 'tired', 'lonely'],
            'angry': ['화나', '짜증', '열받', '빡치', '싫어', 'angry', 'annoyed', 'hate'],
            'excited': ['신나', '흥분', '두근', '설레', '기대', 'excited', 'thrilled'],
            'worried': ['걱정', '불안', '긴장', '두려', '무서', 'worried', 'anxious', 'nervous'],
            'neutral': []
        }

        # 감정별 응답 스타일
        self.emotion_response_styles = {
            'happy': {'tone': 'cheerful', 'emoji': '😊', 'prefix': '기쁘시네요!'},
            'sad': {'tone': 'empathetic', 'emoji': '🤗', 'prefix': '힘내세요.'},
            'angry': {'tone': 'calm', 'emoji': '🌿', 'prefix': '차분히 도와드릴게요.'},
            'excited': {'tone': 'enthusiastic', 'emoji': '🎉', 'prefix': '좋은 일이 있으신가요?'},
            'worried': {'tone': 'reassuring', 'emoji': '💪', 'prefix': '걱정 마세요.'},
            'neutral': {'tone': 'normal', 'emoji': '', 'prefix': ''}
        }

        print("🧠 감정 분석기 초기화 완료")

    def analyze_emotion(self, text: str) -> VoiceEmotion:
        """텍스트에서 감정 분석"""
        text_lower = text.lower()

        # 각 감정별 점수 계산
        emotion_scores = {}
        for emotion, keywords in self.emotion_keywords.items():
            if emotion == 'neutral':
                continue
            score = sum(1 for keyword in keywords if keyword in text_lower)
            emotion_scores[emotion] = score

        # 가장 높은 점수의 감정 찾기
        if emotion_scores:
            max_emotion = max(emotion_scores, key=emotion_scores.get)
            max_score = emotion_scores[max_emotion]

            if max_score > 0:
                # 신뢰도와 강도 계산
                confidence = min(max_score / 3.0, 1.0)  # 최대 3개 키워드로 100%
                intensity = min(max_score / 2.0, 1.0)  # 최대 2개 키워드로 100%

                return VoiceEmotion(
                    emotion=max_emotion,
                    confidence=confidence,
                    intensity=intensity,
                    timestamp=datetime.now().isoformat()
                )

        # 중립 감정 반환
        return VoiceEmotion(
            emotion='neutral',
            confidence=0.8,
            intensity=0.0,
            timestamp=datetime.now().isoformat()
        )

    def get_response_style(self, emotion: VoiceEmotion) -> Dict[str, Any]:
        """감정에 따른 응답 스타일 반환"""
        return self.emotion_response_styles.get(emotion.emotion, self.emotion_response_styles['neutral'])


class QuickCommandEngine:
    """빠른 음성 명령 엔진"""

    def __init__(self):
        self.logger = logging.getLogger('QuickCommandEngine')
        self.quick_commands: List[QuickCommand] = []
        self._setup_default_commands()

        print("⚡ 빠른 명령 엔진 초기화 완료")

    def _setup_default_commands(self):
        """기본 빠른 명령 설정"""
        default_commands = [
            # 조명 제어
            QuickCommand("불 켜", "light_on", "조명을 켭니다", priority=10),
            QuickCommand("불 꺼", "light_off", "조명을 끕니다", priority=10),
            QuickCommand("조명 켜", "light_on", "조명을 켭니다", priority=10),
            QuickCommand("조명 꺼", "light_off", "조명을 끕니다", priority=10),

            # 음악 제어
            QuickCommand("음악 틀어", "music_play", "음악을 재생합니다", priority=9),
            QuickCommand("음악 멈춰", "music_stop", "음악을 정지합니다", priority=9),
            QuickCommand("다음 곡", "music_next", "다음 곡으로 넘어갑니다", priority=8),
            QuickCommand("이전 곡", "music_prev", "이전 곡으로 돌아갑니다", priority=8),

            # 날씨/시간
            QuickCommand("날씨", "weather", "날씨 정보를 알려드립니다", priority=7),
            QuickCommand("몇 시", "time", "현재 시간을 알려드립니다", priority=7),
            QuickCommand("시간", "time", "현재 시간을 알려드립니다", priority=7),

            # 시스템 상태
            QuickCommand("상태", "status", "시스템 상태를 확인합니다", priority=6),
            QuickCommand("배터리", "battery", "배터리 상태를 확인합니다", priority=6),

            # 긴급 명령
            QuickCommand("비상", "emergency", "비상 모드를 활성화합니다", priority=15),
            QuickCommand("긴급", "emergency", "긴급 모드를 활성화합니다", priority=15),
            QuickCommand("도움", "help", "도움말을 표시합니다", priority=5),

            # 종료 명령
            QuickCommand("종료", "shutdown", "시스템을 종료합니다", priority=12),
            QuickCommand("그만", "stop", "현재 작업을 중지합니다", priority=11),
            QuickCommand("취소", "cancel", "작업을 취소합니다", priority=10),
        ]

        for cmd in default_commands:
            self.add_quick_command(cmd)

    def add_quick_command(self, command: QuickCommand):
        """빠른 명령 추가"""
        self.quick_commands.append(command)
        # 우선순위로 정렬
        self.quick_commands.sort(key=lambda x: x.priority, reverse=True)

    def find_quick_command(self, text: str) -> Optional[QuickCommand]:
        """텍스트에서 빠른 명령 찾기"""
        text_lower = text.lower()

        for cmd in self.quick_commands:
            if cmd.trigger_phrase in text_lower:
                return cmd

        return None

    def get_all_commands(self) -> List[Dict[str, Any]]:
        """모든 빠른 명령 반환"""
        return [asdict(cmd) for cmd in self.quick_commands]


class WakeWordDetector:
    """다중 웨이크 워드 감지기"""

    def __init__(self):
        self.logger = logging.getLogger('WakeWordDetector')

        # 기본 웨이크 워드
        self.wake_words = [
            '소리새',
            '소리새야',
            'sorisae',
            '헤이 소리새',
            'hey sorisae',
            '안녕 소리새',
        ]

        # 별칭 (닉네임)
        self.aliases = [
            '새야',
            '소리야',
            '친구야',
            'ai',
            '비서',
        ]

        # 비상 웨이크 워드 (높은 우선순위)
        self.emergency_wake_words = [
            '도와줘',
            '살려줘',
            '비상',
            '긴급',
            '헬프',
            'help',
            'emergency',
        ]

        print("🔔 웨이크 워드 감지기 초기화 완료")

    def detect(self, text: str) -> Tuple[bool, str, bool]:
        """
        웨이크 워드 감지
        Returns: (detected, matched_word, is_emergency)
        """
        text_lower = text.lower()

        # 비상 웨이크 워드 먼저 체크 (긴 것부터)
        for word in sorted(self.emergency_wake_words, key=len, reverse=True):
            if word in text_lower:
                return True, word, True

        # 기본 웨이크 워드 체크 (긴 것부터)
        for word in sorted(self.wake_words, key=len, reverse=True):
            if word in text_lower:
                return True, word, False

        # 별칭 체크 (긴 것부터)
        for alias in sorted(self.aliases, key=len, reverse=True):
            if alias in text_lower:
                return True, alias, False

        return False, '', False

    def add_wake_word(self, word: str, is_emergency: bool = False):
        """웨이크 워드 추가"""
        if is_emergency:
            if word not in self.emergency_wake_words:
                self.emergency_wake_words.append(word)
        else:
            if word not in self.wake_words:
                self.wake_words.append(word)

    def add_alias(self, alias: str):
        """별칭 추가"""
        if alias not in self.aliases:
            self.aliases.append(alias)


class UserPatternLearner:
    """사용자 패턴 학습기"""

    def __init__(self):
        self.logger = logging.getLogger('UserPatternLearner')
        self.user_patterns: Dict[str, UserPattern] = {}
        self.default_user_id = "default_user"

        # 기본 사용자 패턴 생성
        self._get_or_create_pattern(self.default_user_id)

        print("📊 사용자 패턴 학습기 초기화 완료")

    def _get_or_create_pattern(self, user_id: str) -> UserPattern:
        """사용자 패턴 가져오기 또는 생성"""
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = UserPattern(
                user_id=user_id,
                last_active=datetime.now().isoformat()
            )
        return self.user_patterns[user_id]

    def record_command(self, user_id: str, command: str, emotion: Optional[VoiceEmotion] = None):
        """명령 기록"""
        pattern = self._get_or_create_pattern(user_id)

        # 명령 빈도 업데이트
        command_type = self._categorize_command(command)
        if command_type in pattern.command_frequency:
            pattern.command_frequency[command_type] += 1
        else:
            pattern.command_frequency[command_type] = 1

        # 감정 이력 기록
        if emotion:
            pattern.emotion_history.append(emotion)
            # 최근 50개만 유지
            if len(pattern.emotion_history) > 50:
                pattern.emotion_history = pattern.emotion_history[-50:]

        # 상호작용 카운트 증가
        pattern.total_interactions += 1
        pattern.last_active = datetime.now().isoformat()

    def _categorize_command(self, command: str) -> str:
        """명령 카테고리화"""
        command_lower = command.lower()

        categories = {
            'light': ['불', '조명', 'light'],
            'music': ['음악', '노래', 'music'],
            'weather': ['날씨', 'weather'],
            'time': ['시간', '몇시', 'time'],
            'status': ['상태', 'status'],
            'control': ['켜', '꺼', '시작', '멈춰', '정지'],
            'emergency': ['비상', '긴급', 'emergency'],
        }

        for category, keywords in categories.items():
            if any(kw in command_lower for kw in keywords):
                return category

        return 'other'

    def get_most_frequent_commands(self, user_id: str, top_n: int = 5) -> List[Tuple[str, int]]:
        """가장 자주 사용하는 명령 반환"""
        pattern = self._get_or_create_pattern(user_id)

        sorted_commands = sorted(
            pattern.command_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_commands[:top_n]

    def get_average_emotion(self, user_id: str) -> Optional[str]:
        """평균 감정 상태 반환"""
        pattern = self._get_or_create_pattern(user_id)

        if not pattern.emotion_history:
            return None

        emotion_counts = {}
        for emotion in pattern.emotion_history:
            if emotion.emotion in emotion_counts:
                emotion_counts[emotion.emotion] += 1
            else:
                emotion_counts[emotion.emotion] = 1

        if emotion_counts:
            return max(emotion_counts, key=emotion_counts.get)
        return 'neutral'


class VoiceFeedbackSystem:
    """음성 피드백 시스템"""

    def __init__(self):
        self.logger = logging.getLogger('VoiceFeedbackSystem')
        self.tts_engine = None
        self.feedback_enabled = True

        if VOICE_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self._setup_tts_engine()
            except Exception as e:
                self.logger.warning(f"TTS 엔진 초기화 실패: {e}")

        print("🔊 음성 피드백 시스템 초기화 완료")

    def _setup_tts_engine(self):
        """TTS 엔진 설정"""
        if not self.tts_engine:
            return

        # 한국어 음성 찾기
        voices = self.tts_engine.getProperty('voices')
        for voice in voices:
            voice_name = getattr(voice, 'name', '') or ''
            voice_id = getattr(voice, 'id', '') or ''
            if 'korea' in voice_name.lower() or 'kr' in voice_id.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break

        self.tts_engine.setProperty('rate', 180)
        self.tts_engine.setProperty('volume', 0.9)

    def speak(self, text: str, emotion_style: Optional[Dict[str, Any]] = None):
        """음성 출력"""
        if not self.feedback_enabled:
            return

        # 감정 스타일 적용
        display_text = text
        if emotion_style and emotion_style.get('emoji'):
            display_text = f"{emotion_style['emoji']} {text}"

        print(f"🗣️ {display_text}")

        def _speak_async():
            pyttsx3_success = False

            if self.tts_engine:
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                    pyttsx3_success = True
                except Exception as e:
                    self.logger.warning(f"pyttsx3 오류, gTTS 대체 시도: {e}")

            # gTTS 대체
            if not pyttsx3_success and GTTS_AVAILABLE:
                temp_path = None
                try:
                    tts = gTTS(text=text, lang='ko')
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                        temp_path = fp.name
                    tts.save(temp_path)
                    _play_audio_file(temp_path)
                except Exception as e:
                    self.logger.error(f"gTTS 오류: {e}")
                finally:
                    # 임시 파일 정리 보장
                    if temp_path:
                        try:
                            os.unlink(temp_path)
                        except OSError:
                            pass

        thread = threading.Thread(target=_speak_async, daemon=True)
        thread.start()

    def play_notification_sound(self, sound_type: str = "notification"):
        """알림음 재생 (사운드 파일이 있는 경우)"""
        sound_files = {
            "notification": "sounds/notification.mp3",
            "success": "sounds/success.mp3",
            "error": "sounds/error.mp3",
            "wake": "sounds/wake.mp3",
        }

        sound_path = sound_files.get(sound_type)
        if sound_path and os.path.exists(sound_path):
            _play_audio_file(sound_path)

    def enable_feedback(self, enabled: bool = True):
        """피드백 활성화/비활성화"""
        self.feedback_enabled = enabled


class SorisaeVoiceReactive:
    """소리새 음성 반응형 시스템 메인 클래스"""

    def __init__(self):
        print("🎤⚡" + "=" * 55 + "🎤⚡")
        print("       소리새 음성 반응형 업그레이드 시스템")
        print("       Sorisae Voice Reactive Upgrade System")
        print("🎤⚡" + "=" * 55 + "🎤⚡")
        print()

        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('VoiceReactive')

        # 하위 시스템 초기화
        self.emotion_analyzer = EmotionAnalyzer()
        self.quick_command_engine = QuickCommandEngine()
        self.wake_word_detector = WakeWordDetector()
        self.pattern_learner = UserPatternLearner()
        self.feedback_system = VoiceFeedbackSystem()

        # 음성 인식기
        self.recognizer = None
        self.microphone = None
        if VOICE_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
            except Exception as e:
                self.logger.warning(f"마이크 초기화 오류: {e}")

        # 시스템 상태
        self.is_active = True
        self.is_listening = False
        self.current_user_id = "default_user"
        self.command_handlers: Dict[str, Callable] = {}
        self.last_response_time_ms = 0.0

        # 통계
        self.total_commands_processed = 0
        self.total_quick_commands = 0
        self.total_emotion_detected = 0

        # 기본 명령 핸들러 등록
        self._register_default_handlers()

        print("\n✅ 음성 반응형 시스템 준비 완료!")
        print("   📊 빠른 명령: {}개".format(len(self.quick_command_engine.quick_commands)))
        print("   🔔 웨이크 워드: {}개".format(len(self.wake_word_detector.wake_words)))
        print("   🧠 감정 분석: 활성화")
        print("   📈 패턴 학습: 활성화")

    def _register_default_handlers(self):
        """기본 명령 핸들러 등록"""
        self.command_handlers = {
            'light_on': lambda: "거실 조명을 켰습니다",
            'light_off': lambda: "거실 조명을 껐습니다",
            'music_play': lambda: "음악을 재생합니다",
            'music_stop': lambda: "음악을 정지합니다",
            'music_next': lambda: "다음 곡으로 넘어갑니다",
            'music_prev': lambda: "이전 곡으로 돌아갑니다",
            'weather': lambda: "오늘 날씨는 맑고 기온은 22도입니다",
            'time': lambda: f"현재 시간은 {datetime.now().strftime('%H시 %M분')}입니다",
            'status': lambda: "시스템이 정상 작동 중입니다",
            'battery': lambda: "배터리 잔량은 85%입니다",
            'emergency': lambda: "비상 모드를 활성화합니다. 긴급 연락처로 알림을 보냅니다",
            'help': self._get_help_message,
            'shutdown': lambda: "시스템을 종료합니다",
            'stop': lambda: "현재 작업을 중지합니다",
            'cancel': lambda: "작업을 취소합니다",
        }

    def _get_help_message(self) -> str:
        """도움말 메시지 생성"""
        return """
🤖 소리새 음성 반응형 시스템 도움말

⚡ 빠른 명령:
- "불 켜" / "불 꺼" - 조명 제어
- "음악 틀어" / "음악 멈춰" - 음악 제어
- "날씨" - 날씨 정보
- "시간" / "몇 시" - 현재 시간
- "상태" - 시스템 상태
- "도움" - 이 도움말

🔔 웨이크 워드:
- "소리새야", "소리새", "새야", "친구야"

🧠 감정 반응:
- 기쁜, 슬픈, 화난, 걱정되는 표현에 맞춰 응답합니다

📊 패턴 학습:
- 자주 사용하는 명령을 학습하여 더 빠르게 응답합니다
        """.strip()

    def register_command_handler(self, action: str, handler: Callable):
        """명령 핸들러 등록"""
        self.command_handlers[action] = handler

    def process_voice_input(self, text: str) -> ReactiveResponse:
        """
        음성 입력 처리 - 반응형 응답 생성
        """
        start_time = time.time()

        # 1. 감정 분석
        emotion = self.emotion_analyzer.analyze_emotion(text)
        emotion_style = self.emotion_analyzer.get_response_style(emotion)
        emotion_adapted = emotion.emotion != 'neutral'

        if emotion_adapted:
            self.total_emotion_detected += 1

        # 2. 빠른 명령 확인
        quick_cmd = self.quick_command_engine.find_quick_command(text)

        if quick_cmd:
            # 빠른 명령 처리
            self.total_quick_commands += 1
            response_text = self._execute_quick_command(quick_cmd)
        else:
            # 일반 명령 처리
            response_text = self._process_general_command(text)

        # 3. 감정에 따른 응답 조정
        if emotion_adapted and emotion_style.get('prefix'):
            response_text = f"{emotion_style['prefix']} {response_text}"

        # 4. 사용자 패턴 기록
        self.pattern_learner.record_command(self.current_user_id, text, emotion)

        # 5. 응답 시간 계산
        response_time = (time.time() - start_time) * 1000
        self.last_response_time_ms = response_time

        # 6. 통계 업데이트
        self.total_commands_processed += 1

        # 7. 음성 피드백
        self.feedback_system.speak(response_text, emotion_style)

        return ReactiveResponse(
            text=response_text,
            emotion_adapted=emotion_adapted,
            user_pattern_applied=True,
            response_time_ms=response_time,
            feedback_type="audio"
        )

    def _execute_quick_command(self, command: QuickCommand) -> str:
        """빠른 명령 실행"""
        handler = self.command_handlers.get(command.action)

        if handler:
            return handler()
        else:
            return command.response_template

    def _process_general_command(self, text: str) -> str:
        """일반 명령 처리"""
        text_lower = text.lower()

        # 인사
        if any(word in text_lower for word in ['안녕', '하이', '헬로', '반가']):
            return "안녕하세요! 무엇을 도와드릴까요?"

        # 감사
        if any(word in text_lower for word in ['고마워', '감사', '땡큐', 'thanks']):
            return "천만에요! 또 도움이 필요하시면 말씀해주세요."

        # 작별
        if any(word in text_lower for word in ['잘가', '바이', 'bye', '다음에']):
            return "안녕히 가세요! 좋은 하루 되세요!"

        # 칭찬
        if any(word in text_lower for word in ['잘했어', '최고', '짱', '멋지']):
            return "감사합니다! 더 열심히 하겠습니다!"

        # 기본 응답
        return f"'{text}' 명령을 처리하고 있습니다."

    def start_listening(self):
        """음성 인식 시작"""
        if not VOICE_AVAILABLE or not self.recognizer:
            print("❌ 음성 인식 기능을 사용할 수 없습니다")
            return

        self.is_listening = True
        print("🎤 음성 반응형 시스템 시작 - '소리새야'라고 불러주세요")

        def _listen_loop():
            while self.is_listening and self.is_active and not SHUTDOWN_REQUESTED:
                try:
                    with self.microphone as source:
                        audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=5)

                    if SHUTDOWN_REQUESTED:
                        break

                    try:
                        text = self.recognizer.recognize_google(audio, language='ko-KR')

                        if text:
                            # 웨이크 워드 감지
                            detected, matched_word, is_emergency = self.wake_word_detector.detect(text)

                            if is_emergency:
                                # 비상 상황 처리
                                print(f"🚨 비상 키워드 감지: {matched_word}")
                                self.process_voice_input("비상 모드 활성화")
                            elif detected:
                                # 웨이크 워드 감지됨
                                print(f"🔔 웨이크 워드 감지: {matched_word}")
                                self.feedback_system.speak("네, 말씀하세요!")
                                self._wait_for_command()

                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        self.logger.error(f"음성 인식 서비스 오류: {e}")

                except sr.WaitTimeoutError:
                    if SHUTDOWN_REQUESTED:
                        break
                except Exception as e:
                    self.logger.error(f"음성 인식 오류: {e}")
                    time.sleep(1)

            print("👂 음성 인식 종료")

        thread = threading.Thread(target=_listen_loop, daemon=True)
        thread.start()

    def _wait_for_command(self):
        """명령 대기"""
        try:
            with self.microphone as source:
                print("🎤 명령을 말씀해주세요...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

            text = self.recognizer.recognize_google(audio, language='ko-KR')

            if text:
                print(f"📝 인식된 명령: {text}")
                self.process_voice_input(text)

        except sr.WaitTimeoutError:
            self.feedback_system.speak("시간이 초과되었습니다. 다시 시도해주세요.")
        except sr.UnknownValueError:
            self.feedback_system.speak("명령을 이해하지 못했습니다.")
        except Exception as e:
            self.logger.error(f"명령 대기 오류: {e}")

    def stop_listening(self):
        """음성 인식 중지"""
        self.is_listening = False

    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            "total_commands_processed": self.total_commands_processed,
            "total_quick_commands": self.total_quick_commands,
            "total_emotion_detected": self.total_emotion_detected,
            "last_response_time_ms": self.last_response_time_ms,
            "quick_command_ratio": self.total_quick_commands / max(self.total_commands_processed, 1),
            "emotion_detection_ratio": self.total_emotion_detected / max(self.total_commands_processed, 1),
            "current_user_frequent_commands": self.pattern_learner.get_most_frequent_commands(self.current_user_id),
            "current_user_average_emotion": self.pattern_learner.get_average_emotion(self.current_user_id),
        }

    def add_quick_command(self, trigger: str, action: str, response: str, priority: int = 5):
        """빠른 명령 추가"""
        self.quick_command_engine.add_quick_command(
            QuickCommand(trigger, action, response, priority)
        )

    def add_wake_word(self, word: str, is_emergency: bool = False):
        """웨이크 워드 추가"""
        self.wake_word_detector.add_wake_word(word, is_emergency)

    def shutdown(self):
        """시스템 종료"""
        global SHUTDOWN_REQUESTED
        SHUTDOWN_REQUESTED = True
        self.is_active = False
        self.is_listening = False
        print("🛑 음성 반응형 시스템이 종료되었습니다")


def test_voice_reactive():
    """음성 반응형 시스템 테스트"""
    print("\n🧪 음성 반응형 시스템 테스트")
    print("=" * 60)

    # 시스템 생성
    reactive = SorisaeVoiceReactive()

    # 테스트 명령들
    test_commands = [
        "불 켜줘",
        "기뻐서 음악 틀어줘",
        "날씨 어때?",
        "지금 몇 시야?",
        "슬픈데 위로해줘",
        "화나니까 진정시켜줘",
        "시스템 상태 확인해",
        "도움말 보여줘",
        "안녕하세요",
        "고마워",
    ]

    print("\n📋 테스트 명령 처리:")
    print("-" * 60)

    for cmd in test_commands:
        print(f"\n입력: '{cmd}'")
        response = reactive.process_voice_input(cmd)
        print(f"   응답: {response.text}")
        print(f"   감정 적용: {response.emotion_adapted}")
        print(f"   응답 시간: {response.response_time_ms:.2f}ms")

    # 통계 출력
    stats = reactive.get_statistics()
    print("\n📊 통계:")
    print("-" * 60)
    print(f"   총 처리 명령: {stats['total_commands_processed']}")
    print(f"   빠른 명령: {stats['total_quick_commands']}")
    print(f"   감정 감지: {stats['total_emotion_detected']}")
    print(f"   빠른 명령 비율: {stats['quick_command_ratio']:.1%}")
    print(f"   감정 감지 비율: {stats['emotion_detection_ratio']:.1%}")
    print(f"   자주 사용한 명령: {stats['current_user_frequent_commands']}")

    print("\n✅ 테스트 완료!")

    return reactive


def main():
    """메인 실행"""
    print("\n🚀 소리새 음성 반응형 시스템 시작")

    try:
        reactive = SorisaeVoiceReactive()

        # 대화형 모드
        print("\n📋 명령어:")
        print("   - 텍스트 명령을 입력하세요")
        print("   - 'test' - 자동 테스트 실행")
        print("   - 'stats' - 통계 보기")
        print("   - 'voice' - 음성 인식 시작")
        print("   - 'quit' - 종료")

        while reactive.is_active:
            try:
                user_input = input("\n소리새> ").strip()

                if not user_input:
                    continue

                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'test':
                    test_voice_reactive()
                elif user_input.lower() == 'stats':
                    stats = reactive.get_statistics()
                    import json
                    print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
                elif user_input.lower() == 'voice':
                    reactive.start_listening()
                    input("음성 인식 중... (Enter 키로 중지)")
                    reactive.stop_listening()
                else:
                    response = reactive.process_voice_input(user_input)
                    # 응답은 process_voice_input에서 이미 출력됨

            except KeyboardInterrupt:
                print("\n사용자가 프로그램을 중단했습니다")
                break

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'reactive' in locals():
            reactive.shutdown()

    print("👋 프로그램을 종료합니다")


if __name__ == "__main__":
    main()
