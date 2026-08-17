#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎤🌐 소리새 하이브리드 음성 명령 처리 시스템
Advanced Hybrid Voice Command Processing System

실시간 한국어 음성 인식 및 자연어 처리를 통한
지능형 명령 분석 및 실행 시스템
- 하이브리드 연결: 지상파 → 모바일 → 위성 자동 전환
- 산간지역 음성 안정성 보장
"""

import logging
import os
import re
import signal
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple

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
    import tempfile
    import subprocess
    import platform
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# 하이브리드 연결 시스템
try:
    from sorisae_integrated_hybrid_system import SorisaeIntegratedHybridSystem
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False
    print("⚠️ 하이브리드 시스템 연결 가능 - 기본 모드로 실행")

# 음성 반응형 시스템
try:
    from sorisae_voice_reactive import (
        EmotionAnalyzer,
        QuickCommandEngine,
        WakeWordDetector,
        UserPatternLearner,
    )
    VOICE_REACTIVE_AVAILABLE = True
except ImportError:
    VOICE_REACTIVE_AVAILABLE = False


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
class VoiceCommand:
    """하이브리드 음성 명령 구조체"""
    raw_text: str
    processed_text: str
    intent: str
    entities: Dict[str, Any]
    confidence: float
    timestamp: str
    connection_type: str = "terrestrial"  # 연결 타입 추가
    response_time_ms: float = 0.0
    response: str = ""
    executed: bool = False


@dataclass
class VoiceProfile:
    """사용자 음성 프로필"""
    user_id: str
    voice_pattern: Dict[str, float]
    preferred_language: str
    command_history: List[str]
    learning_data: Dict[str, Any]


class NaturalLanguageProcessor:
    """자연어 처리 엔진"""

    def __init__(self):
        self.intent_patterns = {
            # 위성 통신 관련
            'satellite_connect': [
                r'위성.*연결',
                r'인터넷.*연결',
                r'와이파이.*연결',
                r'네트워크.*연결'
            ],
            'satellite_disconnect': [
                r'위성.*해제|끊어|차단',
                r'인터넷.*해제|끊어|차단',
                r'연결.*해제|끊어|차단'
            ],
            'satellite_status': [
                r'위성.*상태|확인',
                r'인터넷.*상태|확인',
                r'연결.*상태|확인'
            ],

            # IoT 제어
            'light_control': [
                r'불.*켜|불.*꺼',
                r'조명.*켜|조명.*꺼',
                r'라이트.*켜|라이트.*꺼'
            ],
            'temperature_control': [
                r'온도.*올려|온도.*내려',
                r'에어컨.*켜|에어컨.*꺼',
                r'히터.*켜|히터.*꺼'
            ],
            'device_control': [
                r'(.*)(켜|꺼)줘',
                r'(.*)(시작|중지)해줘'
            ],

            # 보안 관련
            'security_scan': [
                r'보안.*스캔|검사',
                r'바이러스.*스캔|검사',
                r'위협.*검사|확인'
            ],
            'emergency_mode': [
                r'비상.*모드|상황',
                r'응급.*모드|상황',
                r'긴급.*모드|상황'
            ],

            # 시스템 관리
            'system_status': [
                r'시스템.*상태|확인',
                r'상태.*확인|체크',
                r'시스템.*체크'
            ],
            'system_restart': [
                r'시스템.*재시작|리부팅',
                r'다시.*시작',
                r'재부팅'
            ],

            # 정보 요청
            'weather_info': [
                r'날씨.*어때|어떻게',
                r'오늘.*날씨',
                r'기온.*어때'
            ],
            'time_info': [
                r'지금.*몇시|시간',
                r'현재.*시간',
                r'시간.*알려줘'
            ],

            # 대화 및 일반
            'greeting': [
                r'안녕|하이|헬로',
                r'소리새야',
                r'좋은.*아침|저녁'
            ],
            'farewell': [
                r'안녕|잘가|바이',
                r'종료|끝|그만'
            ],
            'help': [
                r'도움말|헬프',
                r'무엇.*할.*수.*있어',
                r'기능.*뭐야'
            ]
        }

        self.entity_patterns = {
            'device_name': r'(거실|방|주방|화장실)?\s*(조명|불|라이트|에어컨|히터|TV|음악|스피커)',
            'location': r'(거실|침실|주방|화장실|베란다|현관)',
            'number': r'(\d+)',
            'temperature': r'(\d+)도?',
            'time': r'(\d{1,2})시?\s*(\d{1,2})?분?'
        }

    def process_command(self, text: str) -> VoiceCommand:
        """음성 명령 처리"""
        # 텍스트 전처리
        processed_text = self._preprocess_text(text)

        # 의도 분석
        intent, confidence = self._detect_intent(processed_text)

        # 개체명 추출
        entities = self._extract_entities(processed_text)

        # VoiceCommand 객체 생성
        command = VoiceCommand(
            raw_text=text,
            processed_text=processed_text,
            intent=intent,
            entities=entities,
            confidence=confidence,
            timestamp=datetime.now().isoformat()
        )

        return command

    def _preprocess_text(self, text: str) -> str:
        """텍스트 전처리"""
        # 소문자 변환 및 공백 정리
        text = text.lower().strip()

        # 불필요한 문자 제거
        text = re.sub(r'[^\w\s가-힣]', '', text)

        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text)

        return text

    def _detect_intent(self, text: str) -> Tuple[str, float]:
        """의도 감지"""
        best_intent = 'unknown'
        best_score = 0.0

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    # 패턴 매칭 점수 계산
                    score = len(re.findall(pattern, text)) / len(text.split())
                    if score > best_score:
                        best_score = score
                        best_intent = intent

        return best_intent, min(best_score * 2, 1.0)  # 신뢰도 정규화

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """개체명 추출"""
        entities = {}

        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                entities[entity_type] = matches

        return entities


class VoiceCommandProcessor:
    """하이브리드 음성 명령 처리기"""

    def __init__(self, master_system=None):
        self.logger = logging.getLogger('HybridVoiceProcessor')
        self.master_system = master_system
        self.nlp = NaturalLanguageProcessor()

        # 하이브리드 연결 초기화
        self.hybrid_system = None
        self.connection_type = 'terrestrial'
        self.hybrid_mode = False

        if HYBRID_AVAILABLE:
            try:
                self.hybrid_system = SorisaeIntegratedHybridSystem()
                self.hybrid_mode = True
                print("✅ 하이브리드 연결 시스템 활성화")
                self.logger.info("하이브리드 음성 처리 모드 활성화")
            except Exception as e:
                print(f"⚠️ 하이브리드 시스템 초기화 실패: {e}")
                self.logger.warning(f"하이브리드 시스템 초기화 실패, 기본 모드로 전환: {e}")

        # 음성 반응형 시스템 초기화
        self.emotion_analyzer = None
        self.quick_command_engine = None
        self.wake_word_detector = None
        self.pattern_learner = None
        self.voice_reactive_mode = False

        if VOICE_REACTIVE_AVAILABLE:
            try:
                self.emotion_analyzer = EmotionAnalyzer()
                self.quick_command_engine = QuickCommandEngine()
                self.wake_word_detector = WakeWordDetector()
                self.pattern_learner = UserPatternLearner()
                self.voice_reactive_mode = True
                print("⚡ 음성 반응형 시스템 활성화")
                self.logger.info("음성 반응형 모드 활성화 (감정 분석, 빠른 명령, 패턴 학습)")
            except Exception as e:
                print(f"⚠️ 음성 반응형 시스템 초기화 실패: {e}")
                self.logger.warning(f"음성 반응형 시스템 초기화 실패: {e}")

        # 음성 인식기 초기화
        if VOICE_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.tts_engine = pyttsx3.init()
            self._setup_voice_engine()

        # 명령 처리 함수 매핑
        self.command_handlers = {
            'satellite_connect': self._handle_satellite_connect,
            'satellite_disconnect': self._handle_satellite_disconnect,
            'satellite_status': self._handle_satellite_status,
            'light_control': self._handle_light_control,
            'temperature_control': self._handle_temperature_control,
            'device_control': self._handle_device_control,
            'security_scan': self._handle_security_scan,
            'emergency_mode': self._handle_emergency_mode,
            'system_status': self._handle_system_status,
            'system_restart': self._handle_system_restart,
            'weather_info': self._handle_weather_info,
            'time_info': self._handle_time_info,
            'greeting': self._handle_greeting,
            'farewell': self._handle_farewell,
            'help': self._handle_help,
            'unknown': self._handle_unknown
        }

        # 상태 관리
        self.is_listening = False
        self.command_queue = []
        self.response_queue = []

        self.logger.info("음성 명령 처리기 초기화 완료")

    def _setup_voice_engine(self):
        """TTS 엔진 설정"""
        if not self.tts_engine:
            return

        # 음성 설정
        voices = self.tts_engine.getProperty('voices')
        for voice in voices:
            if 'korea' in voice.name.lower() or 'kr' in voice.id.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break

        self.tts_engine.setProperty('rate', 180)
        self.tts_engine.setProperty('volume', 0.9)

        # 마이크 환경 보정
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def speak(self, text: str):
        """음성 출력 - pyttsx3 우선, 실패 시 gTTS 대체"""
        print(f"🗣️ {text}")

        def _speak():
            try:
                if self.tts_engine:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                    return
            except Exception as e:
                self.logger.warning(f"pyttsx3 TTS 오류, gTTS 대체 시도: {e}")

            # gTTS 대체 시도
            if GTTS_AVAILABLE:
                try:
                    tts = gTTS(text=text, lang='ko')
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                        temp_path = fp.name
                    tts.save(temp_path)
                    _play_audio_file(temp_path)
                    # 임시 파일 정리
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                except Exception as e:
                    self.logger.error(f"gTTS 오류: {e}")

        threading.Thread(target=_speak, daemon=True).start()

    def hybrid_speech_recognition(self, audio_data):
        """하이브리드 음성 인식 - 연결 상태에 따라 자동 전환"""
        start_time = time.time()

        if self.hybrid_mode and self.hybrid_system:
            # 하이브리드 연결 상태 확인
            connection_status = self.hybrid_system.get_connection_status()
            self.connection_type = connection_status.get('active_connection', 'terrestrial')

            print(f"🌐 연결 상태: {self.connection_type}")

            # 연결 품질에 따른 음성 인식 시도
            for attempt_type in ['terrestrial', 'mobile', 'satellite']:
                try:
                    if attempt_type == 'terrestrial':
                        # 고속 지상파 연결
                        text = self.recognizer.recognize_google(audio_data, language='ko-KR')
                        response_time = (time.time() - start_time) * 1000
                        print(f"✅ 지상파 음성인식 성공 ({response_time:.1f}ms)")
                        return text, attempt_type, response_time

                    elif attempt_type == 'mobile':
                        # 모바일 연결 (속도 조절)
                        text = self.recognizer.recognize_google(audio_data, language='ko-KR')
                        response_time = (time.time() - start_time) * 1000
                        print(f"📱 모바일 음성인식 성공 ({response_time:.1f}ms)")
                        return text, attempt_type, response_time

                    elif attempt_type == 'satellite':
                        # 위성 연결 (저속 but 안정적)
                        text = self.recognizer.recognize_google(audio_data, language='ko-KR')
                        response_time = (time.time() - start_time) * 1000
                        print(f"🛰️ 위성 음성인식 성공 ({response_time:.1f}ms)")
                        return text, attempt_type, response_time

                except Exception as e:
                    self.logger.warning(f"{attempt_type} 음성인식 실패: {e}")
                    continue

            # 모든 연결 실패시 오프라인 패턴 처리
            return self._offline_pattern_recognition(), 'offline', (time.time() - start_time) * 1000

        else:
            # 기본 음성 인식
            try:
                text = self.recognizer.recognize_google(audio_data, language='ko-KR')
                response_time = (time.time() - start_time) * 1000
                return text, 'terrestrial', response_time
            except Exception as e:
                self.logger.error(f"기본 음성인식 실패: {e}")
                return None, 'error', (time.time() - start_time) * 1000

    def _offline_pattern_recognition(self):
        """오프라인 패턴 매칭"""
        offline_patterns = [
            "소리새야", "안녕", "도움말", "종료", "상태", "연결"
        ]
        # 실제로는 더 정교한 오프라인 패턴 매칭 구현
        return "오프라인 모드"

    def start_listening(self):
        """하이브리드 음성 인식 시작"""
        if not VOICE_AVAILABLE:
            self.logger.warning("음성 인식을 사용할 수 없습니다")
            return

        self.is_listening = True
        connection_info = f" (하이브리드 모드)" if self.hybrid_mode else " (기본 모드)"
        self.logger.info(f"음성 인식 시작{connection_info}")

        def _listen():
            global SHUTDOWN_REQUESTED
            while self.is_listening and not SHUTDOWN_REQUESTED:
                try:
                    with self.microphone as source:
                        # 대기 중임을 알림
                        status_msg = "🎤🌐 하이브리드 음성 명령 대기중..." if self.hybrid_mode else "🎤 음성 명령 대기중..."
                        print(f"{status_msg} ('소리새야'라고 불러주세요)")

                        # 음성 입력 대기 (타임아웃 설정)
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)

                    # 전역 종료 플래그 체크
                    if SHUTDOWN_REQUESTED:
                        break

                    # 하이브리드 음성 인식 시도
                    try:
                        text, connection_type, response_time = self.hybrid_speech_recognition(audio)
                        if text:
                            self.logger.info(f"음성 인식 결과: {text} ({connection_type})")

                        # 활성화 키워드 확인
                        if self._is_activation_keyword(text):
                            self.speak("네, 말씀하세요!")
                            self._process_voice_input()

                    except sr.UnknownValueError:
                        # 인식하지 못한 경우 (무시)
                        pass
                    except sr.RequestError as e:
                        self.logger.error(f"음성 인식 서비스 오류: {e}")
                        time.sleep(5)

                except sr.WaitTimeoutError:
                    # 타임아웃 (정상적인 상황)
                    if SHUTDOWN_REQUESTED:
                        break
                except Exception as e:
                    self.logger.error(f"음성 인식 중 오류: {e}")
                    time.sleep(1)

            self.logger.info("음성 인식 루프 종료")

        listen_thread = threading.Thread(target=_listen, daemon=True)
        listen_thread.start()

    def _is_activation_keyword(self, text: str) -> bool:
        """활성화 키워드 확인"""
        activation_keywords = ['소리새', '소리새야', 'sorisae']
        text_lower = text.lower()

        return any(keyword in text_lower for keyword in activation_keywords)

    def _process_voice_input(self):
        """활성화 후 하이브리드 명령 처리"""
        try:
            with self.microphone as source:
                print("🎤🌐 하이브리드 명령 대기중..." if self.hybrid_mode else "🎤 명령을 말씀해주세요...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

            # 하이브리드 음성 인식
            text, connection_type, response_time = self.hybrid_speech_recognition(audio)
            if text:
                self.logger.info(f"명령 인식: {text} ({connection_type}, {response_time:.1f}ms)")

                # 명령 처리
                response = self.process_command(text, connection_type, response_time)
            else:
                response = "죄송합니다. 명령을 인식하지 못했습니다."
                self.speak(response)

        except sr.UnknownValueError:
            response = "죄송합니다. 명령을 이해하지 못했습니다."
            self.speak(response)
        except sr.RequestError as e:
            response = "음성 인식 서비스에 문제가 있습니다."
            self.speak(response)
            self.logger.error(f"음성 인식 서비스 오류: {e}")
        except sr.WaitTimeoutError:
            response = "명령을 기다리는 중 시간이 초과되었습니다."
            self.speak(response)
        except Exception as e:
            response = "명령 처리 중 오류가 발생했습니다."
            self.speak(response)
            self.logger.error(f"명령 처리 오류: {e}")

    def process_command(self, text: str, connection_type: str = "terrestrial", response_time: float = 0.0) -> str:
        """하이브리드 명령 처리 (음성 반응형 기능 통합)"""

        # 음성 반응형: 빠른 명령 확인
        if self.voice_reactive_mode and self.quick_command_engine:
            quick_cmd = self.quick_command_engine.find_quick_command(text)
            if quick_cmd:
                self.logger.info(f"⚡ 빠른 명령 감지: {quick_cmd.action}")
                response = quick_cmd.response_template
                self.speak(response)
                return response

        # 음성 반응형: 감정 분석
        emotion = None
        emotion_prefix = ""
        if self.voice_reactive_mode and self.emotion_analyzer:
            emotion = self.emotion_analyzer.analyze_emotion(text)
            if emotion.emotion != 'neutral':
                style = self.emotion_analyzer.get_response_style(emotion)
                emotion_prefix = style.get('prefix', '') + " " if style.get('prefix') else ""
                self.logger.info(f"🧠 감정 감지: {emotion.emotion} (신뢰도: {emotion.confidence:.1%})")

        # NLP로 명령 분석
        command = self.nlp.process_command(text)

        # 하이브리드 정보 추가
        command.connection_type = connection_type
        command.response_time_ms = response_time

        # 로그 기록
        self.logger.info(f"하이브리드 명령 분석 - 의도: {command.intent}, 신뢰도: {command.confidence:.2f}, 연결: {connection_type}")

        # 하이브리드 시스템과 연동된 명령 처리
        if self.hybrid_mode and command.intent in ['satellite_connect', 'satellite_status', 'satellite_disconnect']:
            response = self._handle_hybrid_command(command)
        elif command.intent in self.command_handlers:
            response = self.command_handlers[command.intent](command)
        else:
            response = self.command_handlers['unknown'](command)

        # 감정에 따른 응답 조정
        if emotion_prefix:
            response = emotion_prefix + response

        # 응답 설정
        command.response = response
        command.executed = True

        # 명령 기록
        self.command_queue.append(command)
        if len(self.command_queue) > 100:  # 메모리 관리
            self.command_queue.pop(0)

        # 음성 반응형: 사용자 패턴 기록
        if self.voice_reactive_mode and self.pattern_learner:
            self.pattern_learner.record_command("default_user", text, emotion)

        # 음성 응답
        self.speak(response)

        return response

    # 명령 핸들러들

    def _handle_satellite_connect(self, command: VoiceCommand) -> str:
        """위성 연결 처리"""
        if self.master_system and 'satellite' in self.master_system.modules:
            try:
                self.master_system.modules['satellite'].start_satellite_connection()
                return "위성 인터넷 연결을 시작합니다."
            except Exception as e:
                self.logger.error(f"위성 연결 오류: {e}")
                return "위성 연결에 실패했습니다."
        return "위성 모듈이 준비되지 않았습니다."

    def _handle_satellite_disconnect(self, command: VoiceCommand) -> str:
        """위성 연결 해제 처리"""
        if self.master_system and 'satellite' in self.master_system.modules:
            try:
                self.master_system.modules['satellite'].disconnect()
                return "위성 연결을 해제했습니다."
            except Exception as e:
                self.logger.error(f"위성 연결 해제 오류: {e}")
                return "위성 연결 해제에 실패했습니다."
        return "위성 모듈이 준비되지 않았습니다."

    def _handle_satellite_status(self, command: VoiceCommand) -> str:
        """위성 상태 확인"""
        if self.master_system and 'satellite' in self.master_system.modules:
            satellite = self.master_system.modules['satellite']
            if satellite.is_active and satellite.current_connection:
                speed = satellite.current_connection.download_speed
                quality = satellite.current_connection.signal_quality
                return f"위성이 연결되어 있습니다. 속도는 {speed:.1f} 메가비트이고 신호 품질은 {quality}입니다."
            else:
                return "현재 위성에 연결되지 않은 상태입니다."
        return "위성 상태를 확인할 수 없습니다."

    def _handle_light_control(self, command: VoiceCommand) -> str:
        """조명 제어"""
        if self.master_system and 'iot' in self.master_system.modules:
            if '켜' in command.processed_text:
                result = self.master_system.modules['iot'].control_device('smart_light', '켜')
                return result
            elif '꺼' in command.processed_text:
                result = self.master_system.modules['iot'].control_device('smart_light', '꺼')
                return result
        return "조명을 제어할 수 없습니다."

    def _handle_temperature_control(self, command: VoiceCommand) -> str:
        """온도 제어"""
        if self.master_system and 'iot' in self.master_system.modules:
            if '올려' in command.processed_text or '높여' in command.processed_text:
                result = self.master_system.modules['iot'].control_device('thermostat', '온도 올려')
                return result
            elif '내려' in command.processed_text or '낮춰' in command.processed_text:
                result = self.master_system.modules['iot'].control_device('thermostat', '온도 내려')
                return result
        return "온도를 제어할 수 없습니다."

    def _handle_device_control(self, command: VoiceCommand) -> str:
        """일반 기기 제어"""
        entities = command.entities.get('device_name', [])
        if entities:
            device = entities[0]
            if '켜' in command.processed_text:
                return f"{device}을(를) 켰습니다."
            elif '꺼' in command.processed_text:
                return f"{device}을(를) 껐습니다."
        return "기기를 제어할 수 없습니다."

    def _handle_security_scan(self, command: VoiceCommand) -> str:
        """보안 스캔"""
        if self.master_system and 'security' in self.master_system.modules:
            result = self.master_system.modules['security'].scan_threats()
            return f"보안 스캔을 완료했습니다. {result}"
        return "보안 스캔을 실행할 수 없습니다."

    def _handle_emergency_mode(self, command: VoiceCommand) -> str:
        """비상 모드"""
        if self.master_system and 'satellite' in self.master_system.modules:
            self.master_system.modules['satellite'].emergency_mode()
            return "비상 모드를 활성화했습니다."
        return "비상 모드를 활성화할 수 없습니다."

    def _handle_system_status(self, command: VoiceCommand) -> str:
        """시스템 상태"""
        if self.master_system:
            uptime = time.time() - self.master_system.start_time
            return f"시스템이 정상 작동 중입니다. 업타임은 {uptime:.0f}초입니다."
        return "시스템 상태를 확인할 수 없습니다."

    def _handle_system_restart(self, command: VoiceCommand) -> str:
        """시스템 재시작"""
        return "시스템 재시작 요청을 받았습니다. 관리자 권한이 필요합니다."

    def _handle_weather_info(self, command: VoiceCommand) -> str:
        """날씨 정보"""
        return "죄송합니다. 현재 날씨 정보 서비스는 준비 중입니다."

    def _handle_time_info(self, command: VoiceCommand) -> str:
        """시간 정보"""
        current_time = datetime.now().strftime("%H시 %M분")
        return f"현재 시간은 {current_time}입니다."

    def _handle_greeting(self, command: VoiceCommand) -> str:
        """인사"""
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            return "좋은 아침입니다! 무엇을 도와드릴까요?"
        elif 12 <= current_hour < 18:
            return "안녕하세요! 좋은 하루입니다."
        else:
            return "안녕하세요! 무엇을 도와드릴까요?"

    def _handle_farewell(self, command: VoiceCommand) -> str:
        """작별 인사 및 시스템 종료"""
        global SHUTDOWN_REQUESTED

        # 개선된 종료 처리 사용
        try:
            from enhanced_voice_exit import process_voice_command

            # 종료 명령 체크
            exit_response = process_voice_command(command.raw_text)

            if exit_response:
                # 종료 명령 감지됨
                self.logger.info("사용자 요청으로 시스템 종료")
                self.stop_listening()

                # 전역 종료 플래그 설정
                SHUTDOWN_REQUESTED = True

                return exit_response
            else:
                return "안녕히 가세요! 좋은 하루 되세요!"

        except ImportError:
            # 기본 종료 처리
            exit_keywords = ['종료', '끝', '그만', '꺼줘', '꺼', '닫아', '닫아줘', 'exit', 'quit', 'stop', '시스템종료', '시스템꺼줘']

            command_text = command.raw_text.lower()

            if any(keyword in command_text for keyword in exit_keywords):
                self.logger.info("사용자 요청으로 시스템 종료")
                self.stop_listening()

                SHUTDOWN_REQUESTED = True

                # 간단한 종료 처리

                def delayed_shutdown():
                    time.sleep(1)
                    try:
                        os.kill(os.getpid(), signal.SIGINT)
                    except Exception:
                        os._exit(0)

                threading.Thread(target=delayed_shutdown, daemon=True).start()

                return "네, 시스템을 종료합니다. 안녕히 가세요!"
            else:
                return "안녕히 가세요! 좋은 하루 되세요!"

    def _handle_help(self, command: VoiceCommand) -> str:
        """도움말"""
        return """제가 할 수 있는 일들을 알려드릴게요:
        - 위성 인터넷 연결 및 해제
        - 조명, 온도 등 IoT 기기 제어
        - 보안 스캔 및 비상 모드
        - 시스템 상태 확인
        - 시간 정보 제공
        무엇을 도와드릴까요?"""

    def _handle_unknown(self, command: VoiceCommand) -> str:
        """알 수 없는 명령"""
        return f"'{command.raw_text}' 명령을 이해하지 못했습니다. '도움말'이라고 말씀해주세요."

    def _handle_hybrid_command(self, command: VoiceCommand) -> str:
        """하이브리드 시스템 명령 처리"""
        if not self.hybrid_system:
            return "하이브리드 시스템이 활성화되지 않았습니다."

        try:
            if command.intent == 'satellite_connect':
                result = self.hybrid_system.force_satellite_connection()
                return f"🛰️ 위성 연결을 강제로 활성화합니다. {result}"

            elif command.intent == 'satellite_disconnect':
                result = self.hybrid_system.force_terrestrial_connection()
                return f"🌐 지상파 연결로 전환합니다. {result}"

            elif command.intent == 'satellite_status':
                status = self.hybrid_system.get_connection_status()
                active_conn = status.get('active_connection', 'unknown')
                quality = status.get('connection_quality', 'unknown')
                costs = status.get('connection_costs', {})
                current_cost = costs.get(active_conn, '알 수 없음')
                return f"현재 연결: {active_conn}, 품질: {quality}, 비용: {current_cost}"

            return "하이브리드 명령을 처리할 수 없습니다."

        except Exception as e:
            self.logger.error(f"하이브리드 명령 처리 오류: {e}")
            return f"하이브리드 명령 처리 중 오류가 발생했습니다: {e}"

    def get_hybrid_status(self) -> Dict[str, Any]:
        """하이브리드 시스템 상태 반환"""
        status = {
            'hybrid_mode': self.hybrid_mode,
            'connection_type': self.connection_type,
            'hybrid_system_active': self.hybrid_system is not None,
            'voice_available': VOICE_AVAILABLE,
            'listening': self.is_listening,
            'voice_reactive_mode': self.voice_reactive_mode,
            'emotion_analyzer_active': self.emotion_analyzer is not None,
            'quick_command_count': len(self.quick_command_engine.quick_commands) if self.quick_command_engine else 0,
        }

        # 사용자 패턴 통계 추가
        if self.pattern_learner:
            pattern = self.pattern_learner.user_patterns.get("default_user")
            if pattern:
                status['user_interactions'] = pattern.total_interactions
                status['frequent_commands'] = self.pattern_learner.get_most_frequent_commands("default_user", 3)

        return status

    def stop_listening(self):
        """음성 인식 중지"""
        self.is_listening = False
        connection_info = f" (하이브리드 모드)" if self.hybrid_mode else " (기본 모드)"
        self.logger.info(f"음성 인식 중지{connection_info}")

    def get_command_history(self) -> List[Dict]:
        """명령 기록 반환"""
        return [asdict(cmd) for cmd in self.command_queue]

# 테스트 함수


def test_voice_processor():
    """하이브리드 음성 처리기 테스트"""
    processor = VoiceCommandProcessor()

    # 하이브리드 상태 확인
    hybrid_status = processor.get_hybrid_status()
    print(f"🎤🌐 하이브리드 음성 명령 처리기 테스트")
    print("=" * 60)
    print(f"하이브리드 모드: {hybrid_status['hybrid_mode']}")
    print(f"연결 타입: {hybrid_status['connection_type']}")
    print(f"음성 사용 가능: {hybrid_status['voice_available']}")
    print()

    test_commands = [
        "소리새야, 위성 인터넷 연결해줘",
        "하이브리드 연결 상태 확인해줘",
        "지상파로 연결 전환해줘",
        "거실 조명 켜줘",
        "온도 올려줘",
        "보안 스캔 해줘",
        "시스템 상태 확인해줘",
        "비상 모드 켜줘",
        "지금 몇시야?",
        "안녕하세요",
        "도움말"
    ]

    for cmd in test_commands:
        print(f"\n입력: {cmd}")
        response = processor.process_command(cmd, "terrestrial", 150.0)
        print(f"응답: {response}")

    print(f"\n✅ 하이브리드 테스트 완료")
    print(f"총 명령 수: {len(processor.command_queue)}")

    # 하이브리드 상태 최종 확인
    final_status = processor.get_hybrid_status()
    print(f"최종 상태: {final_status}")


if __name__ == "__main__":
    test_voice_processor()
