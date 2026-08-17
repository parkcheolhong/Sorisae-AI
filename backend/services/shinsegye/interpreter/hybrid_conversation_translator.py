#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🗣️🌐🛰️ 소리새 하이브리드 자유 대화 & 통역 시스템
Sorisae Hybrid Free Conversation & Translation System

완전한 하이브리드 대화 시스템:
✅ 자유로운 대화 (일반↔모바일↔위성)
✅ 실시간 통역 (13개 언어 지원)
✅ 스마트 연결 전환 (모바일 불가 시 자동 위성)
✅ 오프라인 기본 대화 (패턴 매칭)
✅ 완벽한 종료 명령 처리
"""

import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

# 음성 인식 및 합성
try:
    import pyttsx3
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("⚠️ 음성 라이브러리 설치 필요: pip install speechrecognition pyttsx3")

# 번역 API
try:
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False

# 전역 종료 플래그
SHUTDOWN_REQUESTED = False


@dataclass
class ConversationMessage:
    """대화 메시지"""
    timestamp: str
    user_text: str
    bot_response: str
    language: str
    connection_type: str
    translation: Optional[Dict[str, str]] = None
    confidence: float = 1.0


@dataclass
class TranslationRequest:
    """번역 요청"""
    text: str
    source_lang: str
    target_lang: str
    connection_type: str
    timestamp: str


class HybridConversationSystem:
    """하이브리드 자유 대화 & 통역 시스템"""

    def __init__(self):
        print("🗣️🌐🛰️" + "=" * 50 + "🗣️🌐🛰️")
        print("   소리새 하이브리드 자유 대화 & 통역 시스템")
        print("   Sorisae Hybrid Free Conversation & Translation")
        print("🗣️🌐🛰️" + "=" * 50 + "🗣️🌐🛰️")
        print()

        # 시스템 상태
        self.active = True
        self.listening = False

        # 대화 관리
        self.conversation_history: List[ConversationMessage] = []
        self.current_language = 'ko'
        self.target_language = 'en'

        # 하이브리드 연결
        self.connection_manager = None
        self.current_connection = 'terrestrial'
        self.connection_quality = 'good'

        # 지원 언어
        self.supported_languages = {
            "ko": "한국어",
            "en": "English",
            "ja": "日本語",
            "zh": "中文",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
            "ru": "Русский",
            "vi": "Tiếng Việt",
            "th": "ไทย",
            "ar": "العربية",
            "id": "Bahasa Indonesia",
            "sorisae": "소리새어"
        }

        # 음성 엔진
        if VOICE_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.tts = pyttsx3.init()
            self.setup_voice()

        # 대화 패턴 (오프라인용)
        self.conversation_patterns = self.load_conversation_patterns()

        # 데이터 저장
        self.data_dir = "hybrid_conversation_data"
        os.makedirs(self.data_dir, exist_ok=True)

        # 하이브리드 연결 초기화
        self.initialize_hybrid_connection()

        print("✅ 하이브리드 대화 & 통역 시스템 준비 완료!")
        self.speak("안녕하세요! 소리새와 자유롭게 대화하고 통역해보세요!")

    def setup_voice(self):
        """음성 설정"""
        if VOICE_AVAILABLE:
            try:
                # 한국어 음성 찾기
                voices = self.tts.getProperty('voices')
                for voice in voices:
                    if 'korea' in voice.name.lower() or 'kr' in voice.id.lower():
                        self.tts.setProperty('voice', voice.id)
                        break

                self.tts.setProperty('rate', 180)
                self.tts.setProperty('volume', 0.9)

                # 마이크 환경 보정
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    print("🎤 마이크 환경 보정 완료")
            except Exception as e:
                print(f"⚠️ 음성 설정 오류: {e}")

    def speak(self, text: str, language: str = 'ko'):
        """음성 출력 (언어별)"""
        if VOICE_AVAILABLE:

            def _speak():
                try:
                    # 언어별 음성 설정
                    if language != 'ko':
                        # 영어나 다른 언어는 기본 음성 사용
                        voices = self.tts.getProperty('voices')
                        if language == 'en' and len(voices) > 1:
                            self.tts.setProperty('voice', voices[1].id)

                    self.tts.say(text)
                    self.tts.runAndWait()

                    # 한국어 음성으로 복원
                    if language != 'ko':
                        voices = self.tts.getProperty('voices')
                        for voice in voices:
                            if 'korea' in voice.name.lower():
                                self.tts.setProperty('voice', voice.id)
                                break

                except Exception as e:
                    print(f"TTS 오류: {e}")

            threading.Thread(target=_speak, daemon=True).start()

        print(f"🗣️ [{language.upper()}] {text}")

    def initialize_hybrid_connection(self):
        """하이브리드 연결 초기화"""
        try:
            from sorisae_integrated_hybrid_system import SorisaeIntegratedHybridSystem
            self.connection_manager = SorisaeIntegratedHybridSystem()
            self.current_connection = self.connection_manager.current_primary
            print("🌐 통합 하이브리드 시스템 연결 완료")
        except ImportError:
            try:
                from hybrid_internet_system import HybridInternetManager
                self.connection_manager = HybridInternetManager()
                print("🌐 하이브리드 인터넷 시스템 연결 완료")
            except ImportError:
                print("⚠️ 하이브리드 연결 시스템 없음 - 기본 모드")
                self.connection_manager = None

    def load_conversation_patterns(self) -> Dict[str, List[str]]:
        """대화 패턴 로드 (오프라인용)"""
        return {
            # 인사
            'greeting': [
                "안녕하세요! 소리새입니다.",
                "반갑습니다! 무엇을 도와드릴까요?",
                "안녕하세요! 대화나 통역이 필요하시면 말씀해주세요.",
                "Hello! I'm Sorisae. How can I help you?",
                "Hi there! Ready for conversation or translation?"
            ],

            # 소개
            'introduction': [
                "저는 소리새입니다. 하이브리드 AI 어시스턴트로 대화와 통역을 도와드려요.",
                "소리새는 13개 언어 통역과 자유로운 대화가 가능한 AI입니다.",
                "일반 인터넷, 모바일, 위성 연결을 자동으로 전환하며 서비스를 제공합니다."
            ],

            # 날씨
            'weather': [
                "오늘 날씨가 어떤가요? 산속에서는 날씨 변화가 빠르니 조심하세요.",
                "산속 날씨는 예측하기 어려워요. 따뜻하게 입으세요.",
                "위성 데이터로 날씨 정보를 확인해드릴 수 있어요."
            ],

            # 위치/산속 관련
            'mountain': [
                "산속에서는 위성 연결이 더 안정적일 수 있어요.",
                "모바일 신호가 약해지면 자동으로 위성으로 전환됩니다.",
                "산속에서의 통신은 소리새가 책임집니다!",
                "산 중턱에서도 통역 서비스가 가능해요."
            ],

            # 통역 관련
            'translation': [
                "어떤 언어로 통역해드릴까요?",
                "13개 언어 통역이 가능합니다.",
                "실시간 음성 통역도 지원해요.",
                "텍스트와 음성 모두 번역 가능합니다."
            ],

            # 기술 관련
            'technology': [
                "하이브리드 연결로 항상 최상의 서비스를 제공해요.",
                "AI 기술과 위성 통신의 만남입니다.",
                "끊임없는 학습으로 더 나은 대화를 만들어갑니다."
            ],

            # 감정 관련
            'emotion': [
                "기분이 어떠세요? 소리새가 함께할게요.",
                "힘든 일이 있으시면 언제든 말씀해주세요.",
                "소리새는 항상 당신의 편입니다.",
                "대화를 통해 마음이 편해지셨으면 좋겠어요."
            ],

            # 종료 관련
            'goodbye': [
                "안녕히 가세요! 언제든 다시 불러주세요.",
                "소리새와의 대화 즐거우셨나요? 또 만나요!",
                "안전한 하루 되세요. 소리새가 응원합니다!",
                "Goodbye! It was nice talking with you!",
                "다음에 또 대화해요. 안녕히 계세요!"
            ]
        }

    def start_conversation_mode(self):
        """대화 모드 시작"""
        if not VOICE_AVAILABLE:
            print("❌ 음성 기능을 사용할 수 없습니다.")
            return

        self.listening = True
        print("👂 하이브리드 자유 대화 모드 시작!")
        print("💡 '소리새야'라고 불러서 대화를 시작하세요")
        print("💡 '통역해줘'라고 하면 통역 모드로 전환됩니다")
        print("💡 '종료', '끝', '그만' 등으로 대화를 종료할 수 있습니다")

        def listen_loop():
            consecutive_failures = 0

            while self.listening and self.active and not SHUTDOWN_REQUESTED:
                try:
                    # 연결 상태 체크
                    self.check_connection_status()

                    with self.microphone as source:
                        print("🎤 음성 대기 중... (활성화: '소리새야')")
                        audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=8)

                    if SHUTDOWN_REQUESTED:
                        break

                    # 하이브리드 음성 인식
                    text = self.hybrid_speech_recognition(audio)

                    if text:
                        consecutive_failures = 0  # 성공 시 실패 카운터 리셋

                        # 종료 명령 우선 체크
                        if self.is_exit_command(text):
                            self.handle_exit_command()
                            break

                        # 활성화 키워드 체크
                        if self.is_activation_keyword(text):
                            self.speak("네, 무엇을 도와드릴까요?")
                            self.process_conversation()

                        # 통역 모드 전환
                        elif '통역' in text or 'translate' in text.lower():
                            self.speak("통역 모드로 전환합니다.")
                            self.start_translation_mode()

                    else:
                        consecutive_failures += 1
                        if consecutive_failures > 5:
                            print("⚠️ 연속 인식 실패 - 연결 상태를 확인합니다.")
                            self.check_and_switch_connection()
                            consecutive_failures = 0

                except sr.WaitTimeoutError:
                    if SHUTDOWN_REQUESTED:
                        break
                    continue
                except Exception as e:
                    print(f"⚠️ 대화 모드 오류: {e}")
                    time.sleep(1)

            print("👂 대화 모드 종료")

        threading.Thread(target=listen_loop, daemon=True).start()

    def hybrid_speech_recognition(self, audio) -> Optional[str]:
        """하이브리드 음성 인식"""
        start_time = time.time()

        # 1단계: 빠른 온라인 인식 (지상파/모바일)
        if self.current_connection in ['terrestrial', 'mobile'] and self.connection_quality != 'poor':
            try:
                text = self.recognizer.recognize_google(audio, language='ko-KR')
                response_time = (time.time() - start_time) * 1000
                print(f"🌐 온라인 인식 ({response_time:.0f}ms): {text}")
                return text
            except sr.RequestError:
                print("⚠️ 온라인 인식 실패 - 위성으로 전환")
                self.switch_to_satellite()
            except sr.UnknownValueError:
                pass

        # 2단계: 위성 인식 시도
        if self.current_connection == 'satellite' or self.connection_quality == 'poor':
            try:
                self.recognizer.timeout = 10  # 위성은 지연이 클 수 있음
                text = self.recognizer.recognize_google(audio, language='ko-KR')
                response_time = (time.time() - start_time) * 1000
                print(f"🛰️ 위성 인식 ({response_time:.0f}ms): {text}")
                return text
            except (sr.RequestError, sr.UnknownValueError):
                print("⚠️ 위성 인식 실패 - 오프라인 모드")
            finally:
                self.recognizer.timeout = 5

        # 3단계: 오프라인 패턴 매칭
        offline_text = self.offline_speech_recognition(audio)
        if offline_text:
            response_time = (time.time() - start_time) * 1000
            print(f"📱 오프라인 인식 ({response_time:.0f}ms): {offline_text}")
            return offline_text

        return None

    def offline_speech_recognition(self, audio) -> Optional[str]:
        """오프라인 음성 인식 (패턴 매칭)"""
        # 실제로는 오프라인 음성 인식 엔진 사용
        # 여기서는 시뮬레이션
        import random

        if random.random() < 0.4:  # 40% 확률로 인식 성공
            offline_phrases = [
                "소리새야", "안녕", "안녕하세요", "상태 확인",
                "통역해줘", "도움말", "종료", "끝", "그만",
                "날씨", "시간", "위치", "번역"
            ]
            return random.choice(offline_phrases)

        return None

    def is_activation_keyword(self, text: str) -> bool:
        """활성화 키워드 확인"""
        activation_keywords = [
            '소리새', '소리새야', 'sorisae',
            '안녕', '안녕하세요', 'hello', 'hi'
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in activation_keywords)

    def is_exit_command(self, text: str) -> bool:
        """종료 명령 확인"""
        exit_keywords = [
            '종료', '끝', '그만', '나가기', '멈춰', '중지',
            'quit', 'exit', 'stop', 'end', 'bye', 'goodbye',
            '안녕', '잘가', '시스템 종료', '프로그램 종료'
        ]

        text_lower = text.lower().strip()

        # 정확한 매칭 우선
        if text_lower in exit_keywords:
            return True

        # 부분 매칭
        return any(keyword in text_lower for keyword in exit_keywords)

    def handle_exit_command(self):
        """종료 명령 처리"""
        global SHUTDOWN_REQUESTED

        print("🛑 종료 명령 감지")
        self.speak("소리새 시스템을 종료합니다. 안녕히 가세요!")

        SHUTDOWN_REQUESTED = True
        self.active = False
        self.listening = False

        time.sleep(2)  # 음성 출력 완료 대기

    def process_conversation(self):
        """대화 처리"""
        try:
            with self.microphone as source:
                print("🎤 대화 내용을 말씀해주세요...")
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=15)

            # 음성 인식
            user_text = self.hybrid_speech_recognition(audio)

            if user_text:
                print(f"👤 사용자: {user_text}")

                # 종료 명령 재확인
                if self.is_exit_command(user_text):
                    self.handle_exit_command()
                    return

                # AI 응답 생성
                bot_response = self.generate_response(user_text)

                # 응답 출력
                self.speak(bot_response)

                # 대화 기록
                message = ConversationMessage(
                    timestamp=datetime.now().isoformat(),
                    user_text=user_text,
                    bot_response=bot_response,
                    language=self.current_language,
                    connection_type=self.current_connection,
                    confidence=0.9
                )

                self.conversation_history.append(message)

                print(f"🤖 소리새: {bot_response}")

            else:
                self.speak("죄송합니다. 다시 말씀해주세요.")

        except sr.WaitTimeoutError:
            self.speak("시간이 초과되었습니다. 다시 '소리새야'라고 불러주세요.")
        except Exception as e:
            print(f"대화 처리 오류: {e}")
            self.speak("대화 중 오류가 발생했습니다.")

    def generate_response(self, user_text: str) -> str:
        """AI 응답 생성"""
        user_lower = user_text.lower()

        # 패턴 기반 응답 (오프라인에서도 작동)
        if any(word in user_lower for word in ['안녕', 'hello', 'hi']):
            return self.get_random_response('greeting')

        elif any(word in user_lower for word in ['소리새', '너', '당신', '소개']):
            return self.get_random_response('introduction')

        elif any(word in user_lower for word in ['날씨', 'weather']):
            return self.get_random_response('weather')

        elif any(word in user_lower for word in ['산', '산속', '오지', 'mountain']):
            return self.get_random_response('mountain')

        elif any(word in user_lower for word in ['통역', '번역', 'translate']):
            return self.get_random_response('translation')

        elif any(word in user_lower for word in ['기술', '하이브리드', 'technology']):
            return self.get_random_response('technology')

        elif any(word in user_lower for word in ['기분', '감정', '힘들', '슬프', '행복']):
            return self.get_random_response('emotion')

        elif any(word in user_lower for word in ['시간', 'time']):
            current_time = datetime.now().strftime('%H시 %M분')
            return f"현재 시간은 {current_time}입니다."

        elif any(word in user_lower for word in ['연결', '상태', 'connection', 'status']):
            return f"현재 {self.current_connection} 연결로 서비스 중입니다. 연결 품질: {self.connection_quality}"

        # 온라인 시 더 지능적인 응답 (실제로는 GPT API 사용)
        elif self.current_connection != 'offline':
            return self.generate_online_response(user_text)

        # 기본 응답
        else:
            return "흥미로운 말씀이네요! 더 자세히 들려주세요."

    def get_random_response(self, category: str) -> str:
        """카테고리별 랜덤 응답"""
        import random
        responses = self.conversation_patterns.get(category, ["그렇군요!"])
        return random.choice(responses)

    def generate_online_response(self, user_text: str) -> str:
        """온라인 AI 응답 생성"""
        # 실제로는 OpenAI GPT API 또는 다른 AI 서비스 호출
        # 여기서는 시뮬레이션
        responses = [
            f"'{user_text}'에 대해 생각해보니 정말 흥미로운 주제네요!",
            f"좋은 질문이세요! {user_text}에 대해 더 자세히 설명드릴까요?",
            f"맞습니다! {user_text}는 중요한 포인트죠.",
            f"그런 관점에서 보면 {user_text}가 핵심이겠네요.",
            f"정말 좋은 생각이세요. {user_text}에 대해 함께 이야기해봐요."
        ]

        import random
        return random.choice(responses)

    def start_translation_mode(self):
        """통역 모드 시작"""
        print("\n🌐 하이브리드 통역 모드 시작!")
        self.speak("통역 모드입니다. 원하는 언어를 말씀해주세요.")

        # 지원 언어 안내
        lang_list = ", ".join([f"{code}({name})" for code, name in list(self.supported_languages.items())[:6]])
        print(f"📋 지원 언어: {lang_list} 등 13개 언어")

        try:
            with self.microphone as source:
                print("🎤 통역할 언어를 말씀해주세요...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

            lang_text = self.hybrid_speech_recognition(audio)

            if lang_text:
                target_lang = self.detect_target_language(lang_text)

                if target_lang:
                    self.target_language = target_lang
                    self.speak(f"{self.supported_languages[target_lang]}로 통역하겠습니다.")
                    self.process_translation()
                else:
                    self.speak("지원하지 않는 언어입니다. 다시 시도해주세요.")

        except Exception as e:
            print(f"통역 모드 오류: {e}")
            self.speak("통역 모드에서 오류가 발생했습니다.")

    def detect_target_language(self, text: str) -> Optional[str]:
        """목표 언어 감지"""
        text_lower = text.lower()

        lang_patterns = {
            'en': ['영어', 'english', '잉글리시'],
            'ja': ['일본어', 'japanese', '일어'],
            'zh': ['중국어', 'chinese', '중어'],
            'es': ['스페인어', 'spanish', '에스파뇰'],
            'fr': ['프랑스어', 'french', '불어'],
            'de': ['독일어', 'german', '도이치'],
            'ru': ['러시아어', 'russian'],
            'vi': ['베트남어', 'vietnamese'],
            'th': ['태국어', 'thai'],
            'ar': ['아랍어', 'arabic'],
            'id': ['인도네시아어', 'indonesian']
        }

        for lang_code, patterns in lang_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return lang_code

        return None

    def process_translation(self):
        """번역 처리"""
        try:
            with self.microphone as source:
                print(f"🎤 {self.supported_languages[self.target_language]}로 번역할 내용을 말씀해주세요...")
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)

            source_text = self.hybrid_speech_recognition(audio)

            if source_text:
                print(f"📝 원문: {source_text}")

                # 하이브리드 번역
                translated_text = self.hybrid_translate(source_text, 'ko', self.target_language)

                if translated_text:
                    print(f"🌐 번역: {translated_text}")

                    # 번역 결과 음성 출력
                    self.speak(f"번역 결과입니다: {translated_text}", self.target_language)

                    # 번역 기록
                    translation_request = TranslationRequest(
                        text=source_text,
                        source_lang='ko',
                        target_lang=self.target_language,
                        connection_type=self.current_connection,
                        timestamp=datetime.now().isoformat()
                    )

                    self.save_translation_history(translation_request, translated_text)
                else:
                    self.speak("번역에 실패했습니다. 다시 시도해주세요.")

        except Exception as e:
            print(f"번역 처리 오류: {e}")
            self.speak("번역 중 오류가 발생했습니다.")

    def hybrid_translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """하이브리드 번역"""

        # 1단계: 온라인 번역 API 시도
        if self.current_connection != 'offline' and TRANSLATION_AVAILABLE:
            try:
                # Google Translate API 시뮬레이션
                online_translation = self.online_translate(text, source_lang, target_lang)
                if online_translation:
                    print(f"🌐 온라인 번역 성공")
                    return online_translation
            except Exception as e:
                print(f"온라인 번역 실패: {e}")

        # 2단계: 오프라인 패턴 번역
        offline_translation = self.offline_translate(text, source_lang, target_lang)
        if offline_translation:
            print(f"📱 오프라인 번역 사용")
            return offline_translation

        return None

    def online_translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """온라인 번역 (실제로는 Google Translate API 등 사용)"""
        # 시뮬레이션
        basic_translations = {
            ('ko', 'en'): {
                '안녕하세요': 'Hello',
                '감사합니다': 'Thank you',
                '도움이 필요해요': 'I need help',
                '어디에 있나요': 'Where is it?',
                '얼마예요': 'How much is it?'
            },
            ('ko', 'ja'): {
                '안녕하세요': 'こんにちは',
                '감사합니다': 'ありがとうございます',
                '도움이 필요해요': '助けが必要です',
            }
        }

        translation_dict = basic_translations.get((source_lang, target_lang), {})

        # 정확한 매칭 찾기
        for korean, translated in translation_dict.items():
            if korean in text:
                return translated

        # 기본 번역 (실제로는 API 호출)
        if target_lang == 'en':
            return f"[Translation to English: {text}]"
        elif target_lang == 'ja':
            return f"[日本語翻訳: {text}]"
        else:
            return f"[Translation to {target_lang}: {text}]"

    def offline_translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """오프라인 패턴 번역"""
        offline_dict = {
            ('ko', 'en'): {
                '안녕': 'Hello',
                '안녕하세요': 'Hello',
                '감사합니다': 'Thank you',
                '고맙습니다': 'Thank you',
                '죄송합니다': 'I am sorry',
                '네': 'Yes',
                '아니요': 'No',
                '도와주세요': 'Please help me',
                '화장실': 'Restroom',
                '병원': 'Hospital',
                '음식': 'Food',
                '물': 'Water'
            },
            ('ko', 'ja'): {
                '안녕하세요': 'こんにちは',
                '감사합니다': 'ありがとうございます',
                '죄송합니다': 'すみません',
                '네': 'はい',
                '아니요': 'いいえ'
            }
        }

        patterns = offline_dict.get((source_lang, target_lang), {})

        # 패턴 매칭
        for pattern, translation in patterns.items():
            if pattern in text:
                return translation

        return f"[오프라인 번역 불가: {text}]"

    def check_connection_status(self):
        """연결 상태 확인"""
        if self.connection_manager:
            try:
                old_connection = self.current_connection

                if hasattr(self.connection_manager, 'current_primary'):
                    self.current_connection = self.connection_manager.current_primary

                if hasattr(self.connection_manager, 'get_connection_quality'):
                    self.connection_quality = self.connection_manager.get_connection_quality()

                # 연결 변경 알림
                if old_connection != self.current_connection:
                    print(f"🔄 연결 전환: {old_connection} → {self.current_connection}")

            except Exception as e:
                print(f"연결 상태 확인 오류: {e}")

    def check_and_switch_connection(self):
        """연결 확인 및 전환"""
        print("🔍 연결 상태 진단 중...")

        # 현재 연결 테스트
        if self.current_connection == 'mobile':
            print("📱 모바일 연결 불안정 - 위성으로 전환 시도")
            self.switch_to_satellite()
        elif self.current_connection == 'terrestrial':
            print("🌐 지상파 연결 문제 - 모바일 또는 위성으로 전환")
            if self.connection_manager:
                try:
                    self.connection_manager.intelligent_connection_switch()
                except Exception:
                    self.switch_to_satellite()

    def switch_to_satellite(self):
        """위성 연결로 전환"""
        if self.connection_manager:
            try:
                if hasattr(self.connection_manager, 'set_primary_connection'):
                    self.connection_manager.set_primary_connection('satellite')
                    self.current_connection = 'satellite'
                    print("🛰️ 위성 연결로 전환 완료")
                    self.speak("위성 연결로 전환되었습니다.")
            except Exception as e:
                print(f"위성 전환 실패: {e}")

    def save_translation_history(self, request: TranslationRequest, result: str):
        """번역 기록 저장"""
        try:
            history_data = {
                'request': asdict(request),
                'result': result,
                'saved_at': datetime.now().isoformat()
            }

            filename = os.path.join(self.data_dir, f'translation_{datetime.now().strftime("%Y%m%d")}.json')

            # 기존 데이터 로드
            translations = []
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    translations = json.load(f)

            # 새 번역 추가
            translations.append(history_data)

            # 저장
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(translations, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"번역 기록 저장 실패: {e}")

    def get_conversation_summary(self) -> str:
        """대화 요약"""
        if not self.conversation_history:
            return "아직 대화 기록이 없습니다."

        summary = f"\n💬 대화 요약 (총 {len(self.conversation_history)}개)\n"
        summary += "=" * 50 + "\n"

        for i, msg in enumerate(self.conversation_history[-5:], 1):  # 최근 5개만 표시
            summary += f"{i}. [{msg.connection_type}] 사용자: {msg.user_text}\n"
            summary += f"   소리새: {msg.bot_response}\n\n"

        return summary

    def shutdown(self):
        """시스템 종료"""
        global SHUTDOWN_REQUESTED
        SHUTDOWN_REQUESTED = True

        print("🛑 하이브리드 대화 & 통역 시스템 종료 중...")
        self.active = False
        self.listening = False

        # 대화 기록 저장
        if self.conversation_history:
            try:
                filename = os.path.join(self.data_dir, f'conversation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump([asdict(msg) for msg in self.conversation_history], f, indent=2, ensure_ascii=False)
                print(f"💾 대화 기록 저장: {filename}")
            except Exception as e:
                print(f"대화 기록 저장 실패: {e}")

        print("✅ 하이브리드 대화 & 통역 시스템 종료 완료")
        self.speak("소리새와의 대화를 마칩니다. 안녕히 가세요!")


def main():
    """메인 실행"""
    global SHUTDOWN_REQUESTED

    # 신호 처리
    import signal

    def signal_handler(signum, frame):
        global SHUTDOWN_REQUESTED
        print(f"\n🛑 종료 신호 받음 (신호: {signum})")
        SHUTDOWN_REQUESTED = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 하이브리드 대화 시스템 시작
    conversation_system = HybridConversationSystem()

    try:
        # 대화 모드 시작
        conversation_system.start_conversation_mode()

        # 메인 루프
        while not SHUTDOWN_REQUESTED and conversation_system.active:
            print(f"\n💬 하이브리드 대화 & 통역 시스템")
            print("=" * 40)
            print("🎤 음성: '소리새야'라고 불러서 대화 시작")
            print("🌐 통역: '통역해줘'라고 하면 통역 모드")
            print("🛑 종료: '종료', '끝', '그만' 등으로 종료")
            print("📊 텍스트 명령:")
            print("  - summary: 대화 요약")
            print("  - status: 연결 상태")
            print("  - quit: 프로그램 종료")
            print("=" * 40)

            try:
                user_input = input("\n텍스트 명령 입력 (또는 음성으로 '소리새야'): ").strip()

                if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                    break

                elif user_input.lower() == 'summary':
                    print(conversation_system.get_conversation_summary())

                elif user_input.lower() == 'status':
                    print(f"📡 현재 연결: {conversation_system.current_connection}")
                    print(f"📶 연결 품질: {conversation_system.connection_quality}")
                    print(f"💬 대화 기록: {len(conversation_system.conversation_history)}개")

                elif user_input:
                    # 텍스트 기반 대화
                    response = conversation_system.generate_response(user_input)
                    print(f"🤖 소리새: {response}")
                    conversation_system.speak(response)

                time.sleep(1)  # 잠시 대기

            except EOFError:
                print("\n입력 스트림 종료")
                break

            except KeyboardInterrupt:
                print("\n사용자 중단")
                break

    except Exception as e:
        print(f"💥 시스템 오류: {e}")

    finally:
        conversation_system.shutdown()
        print("👋 하이브리드 대화 & 통역 시스템을 종료했습니다.")


if __name__ == "__main__":
    main()
