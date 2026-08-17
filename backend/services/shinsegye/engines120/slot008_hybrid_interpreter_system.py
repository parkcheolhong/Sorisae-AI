#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🌐🛰️ 소리새 하이브리드 통역 시스템
Sorisae Hybrid Interpreter System

하이브리드 인터넷 연결을 통한 지능형 실시간 통역:
- 평상시: 고품질 온라인 번역 API (지상파/모바일)
- 지연시: 위성 연결을 통한 클라우드 번역
- 오프라인: 로컬 번역 패턴 데이터베이스 활용
- 음성통역: 하이브리드 음성 인식 + 번역 + 음성 합성
"""

import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

import requests

# 음성 처리
try:
    import pyttsx3
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False


@dataclass
class TranslationRequest:
    """번역 요청 정보"""
    request_id: str
    source_text: str
    source_lang: str
    target_lang: str
    connection_type: str
    timestamp: str
    method: str  # 'online', 'satellite', 'offline'


@dataclass
class TranslationResult:
    """번역 결과"""
    request_id: str
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    confidence: float
    method: str
    response_time_ms: float
    timestamp: str


class HybridInterpreterSystem:
    """하이브리드 통역 시스템"""

    def __init__(self):
        print("🌐🛰️" + "=" * 50 + "🌐🛰️")
        print("   소리새 하이브리드 통역 시스템")
        print("   Sorisae Hybrid Interpreter System")
        print("   나도 통역사 x 하이브리드 인터넷")
        print("🌐🛰️" + "=" * 50 + "🌐🛰️")
        print()

        # 시스템 상태
        self.active = True
        self.interpreting = False

        # 지원 언어
        self.supported_languages = {
            "ko": "한국어 (Korean)",
            "en": "영어 (English)",
            "ja": "일본어 (Japanese)",
            "zh": "중국어 (Chinese)",
            "es": "스페인어 (Spanish)",
            "fr": "프랑스어 (French)",
            "de": "독일어 (German)",
            "ru": "러시아어 (Russian)",
            "ar": "아랍어 (Arabic)",
            "vi": "베트남어 (Vietnamese)",
            "th": "태국어 (Thai)",
            "id": "인도네시아어 (Indonesian)",
            "sorisae": "소리새어 (Sorisae Language)"
        }

        # 하이브리드 연결 관리
        self.connection_manager = None
        self.current_connection = 'terrestrial'
        self.connection_quality = 'good'

        # 번역 이력 및 캐시
        self.translation_history: List[TranslationResult] = []
        self.translation_cache: Dict[str, str] = {}
        self.offline_patterns = self.initialize_offline_patterns()
        self.audio_io_enabled = os.environ.get("SORISAE_DISABLE_AUDIO_IO", "0") != "1"
        self.recognizer = None
        self.microphone = None
        self.tts = None

        # 음성 엔진
        if VOICE_AVAILABLE:
            self.recognizer = sr.Recognizer()
            if self.audio_io_enabled:
                try:
                    self.microphone = sr.Microphone()
                except Exception as e:
                    print(f"⚠️ 기본 입력 장치를 찾을 수 없습니다. 헤드리스 통역 모드로 전환합니다: {e}")
                    self.audio_io_enabled = False
                try:
                    self.tts = pyttsx3.init()
                except Exception as e:
                    print(f"⚠️ 통역 TTS 엔진 초기화 실패. 텍스트 통역 모드로 유지합니다: {e}")
                    self.tts = None
            else:
                print("ℹ️ 헤드리스 통역 모드 - 음성 입출력을 비활성화합니다.")
            self.setup_voice_engines()

        # 데이터 저장
        self.data_dir = "hybrid_interpreter_data"
        os.makedirs(self.data_dir, exist_ok=True)

        # 시스템 초기화
        self.initialize_hybrid_connection()
        self.load_translation_cache()

        print("✅ 하이브리드 통역 시스템 준비 완료!")
        self.speak("하이브리드 실시간 통역 시스템이 준비되었습니다!")

    def initialize_hybrid_connection(self):
        """하이브리드 연결 초기화"""
        try:
            # 통합 하이브리드 시스템 연결
            from sorisae_integrated_hybrid_system import SorisaeIntegratedHybridSystem
            self.connection_manager = SorisaeIntegratedHybridSystem()
            self.current_connection = self.connection_manager.current_primary
            print("🌐 통합 하이브리드 시스템 연결 완료")
        except ImportError:
            try:
                # 기존 하이브리드 인터넷 시스템 연결
                from hybrid_internet_system import HybridInternetManager
                self.connection_manager = HybridInternetManager()
                print("🌐 하이브리드 인터넷 시스템 연결 완료")
            except ImportError:
                print("⚠️ 하이브리드 연결 시스템을 찾을 수 없음 - 기본 모드로 작동")
                self.connection_manager = None

    def setup_voice_engines(self):
        """음성 엔진 설정"""
        if not VOICE_AVAILABLE or not self.microphone or not self.tts:
            return

        # TTS 설정
        self.tts.setProperty('rate', 180)
        self.tts.setProperty('volume', 0.8)

        # 마이크 환경 보정
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("🎤 음성 통역 환경 설정 완료")
        except Exception as e:
            print(f"⚠️ 음성 설정 오류: {e}")

    def speak(self, text: str, language: str = "ko"):
        """음성 출력 (다국어 지원)"""
        if VOICE_AVAILABLE and self.audio_io_enabled and self.tts:

            def _speak():
                try:
                    # 언어별 음성 설정
                    voices = self.tts.getProperty('voices')
                    for voice in voices:
                        if language == "ko" and ('korea' in voice.name.lower() or 'kr' in voice.id.lower()):
                            self.tts.setProperty('voice', voice.id)
                            break
                        elif language == "en" and ('english' in voice.name.lower() or 'en' in voice.id.lower()):
                            self.tts.setProperty('voice', voice.id)
                            break

                    self.tts.say(text)
                    self.tts.runAndWait()
                except Exception as e:
                    print(f"TTS 오류: {e}")

            threading.Thread(target=_speak, daemon=True).start()

        print(f"🗣️ [{language.upper()}] {text}")

    def initialize_offline_patterns(self) -> Dict[str, Dict[str, str]]:
        """오프라인 번역 패턴 초기화"""
        return {
            # 기본 인사말
            "안녕하세요": {
                "en": "Hello", "ja": "こんにちは", "zh": "你好", "es": "Hola",
                "fr": "Bonjour", "de": "Hallo", "ru": "Здравствуйте", "ar": "مرحبا",
                "vi": "Xin chào", "th": "สวัสดี", "id": "Halo", "sorisae": "Sora-hel"
            },
            "감사합니다": {
                "en": "Thank you", "ja": "ありがとうございます", "zh": "谢谢", "es": "Gracias",
                "fr": "Merci", "de": "Danke", "ru": "Спасибо", "ar": "شكرا",
                "vi": "Cảm ơn", "th": "ขอบคุณ", "id": "Terima kasih", "sorisae": "Sora-gam"
            },
            "안녕히 가세요": {
                "en": "Goodbye", "ja": "さようなら", "zh": "再见", "es": "Adiós",
                "fr": "Au revoir", "de": "Auf Wiedersehen", "ru": "До свидания", "ar": "وداعا",
                "vi": "Tạm biệt", "th": "ลาก่อน", "id": "Selamat tinggal", "sorisae": "Sora-bye"
            },
            "도움이 필요합니다": {
                "en": "I need help", "ja": "助けが必要です", "zh": "我需要帮助", "es": "Necesito ayuda",
                "fr": "J'ai besoin d'aide", "de": "Ich brauche Hilfe", "ru": "Мне нужна помощь", "ar": "أحتاج مساعدة",
                "vi": "Tôi cần giúp đỡ", "th": "ฉันต้องการความช่วยเหลือ", "id": "Saya butuh bantuan", "sorisae": "Sora-help"
            },
            "위성 통신": {
                "en": "Satellite Communication", "ja": "衛星通信", "zh": "卫星通信", "es": "Comunicación por satélite",
                "fr": "Communication par satellite", "de": "Satellitenkommunikation", "ru": "Спутниковая связь", "ar": "الاتصالات الفضائية",
                "vi": "Truyền thông vệ tinh", "th": "การสื่อสารผ่านดาวเทียม", "id": "Komunikasi satelit", "sorisae": "Sora-sat-com"
            },
            "하이브리드 시스템": {
                "en": "Hybrid System", "ja": "ハイブリッドシステム", "zh": "混合系统", "es": "Sistema híbrido",
                "fr": "Système hybride", "de": "Hybridsystem", "ru": "Гибридная система", "ar": "النظام الهجين",
                "vi": "Hệ thống lai", "th": "ระบบไฮบริด", "id": "Sistem hibrida", "sorisae": "Sora-hybrid"
            }
        }

    def hybrid_translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult:
        """하이브리드 번역 실행"""
        request_id = f"TR_{int(time.time() * 1000)}"
        start_time = time.time()

        # 캐시 확인
        cache_key = f"{source_lang}:{target_lang}:{text}"
        if cache_key in self.translation_cache:
            result = TranslationResult(
                request_id=request_id,
                source_text=text,
                translated_text=self.translation_cache[cache_key],
                source_lang=source_lang,
                target_lang=target_lang,
                confidence=0.9,
                method='cache',
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now().isoformat()
            )
            print(f"💾 캐시에서 번역: {text} → {result.translated_text}")
            return result

        # 연결 상태 확인
        self.update_connection_status()

        # 번역 방법 선택
        translation_result = None

        # 1단계: 온라인 번역 시도 (지상파/모바일)
        if self.current_connection in ['terrestrial', 'mobile'] and self.connection_quality in ['good', 'fair']:
            translation_result = self.online_translate(text, source_lang, target_lang, request_id, start_time)

        # 2단계: 위성 번역 시도
        if not translation_result and self.current_connection == 'satellite':
            translation_result = self.satellite_translate(text, source_lang, target_lang, request_id, start_time)

        # 3단계: 오프라인 번역
        if not translation_result:
            translation_result = self.offline_translate(text, source_lang, target_lang, request_id, start_time)

        # 캐시에 저장
        if translation_result and translation_result.confidence > 0.7:
            self.translation_cache[cache_key] = translation_result.translated_text

        # 이력에 추가
        if translation_result:
            self.translation_history.append(translation_result)

        return translation_result

    def online_translate(
            self,
            text: str,
            source_lang: str,
            target_lang: str,
            request_id: str,
            start_time: float) -> Optional[TranslationResult]:
        """온라인 번역 (Google Translate API 시뮬레이션)"""
        try:
            # 실제로는 Google Translate API 호출
            # 여기서는 시뮬레이션으로 패턴 매칭 + 일부 변형
            print(f"🌐 온라인 번역 시도: {text}")

            # 간단한 온라인 번역 시뮬레이션
            translated = self.simulate_online_translation(text, source_lang, target_lang)

            if translated:
                return TranslationResult(
                    request_id=request_id,
                    source_text=text,
                    translated_text=translated,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    confidence=0.95,
                    method='online',
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now().isoformat()
                )
        except Exception as e:
            print(f"온라인 번역 실패: {e}")

        return None

    def satellite_translate(
            self,
            text: str,
            source_lang: str,
            target_lang: str,
            request_id: str,
            start_time: float) -> Optional[TranslationResult]:
        """위성 번역 (지연 시간이 크지만 안정적)"""
        try:
            print(f"🛰️ 위성 번역 시도: {text}")

            # 위성 연결 시뮬레이션 (더 긴 지연 시간)
            time.sleep(0.5)  # 위성 지연 시뮬레이션

            translated = self.simulate_online_translation(text, source_lang, target_lang)

            if translated:
                return TranslationResult(
                    request_id=request_id,
                    source_text=text,
                    translated_text=translated,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    confidence=0.90,
                    method='satellite',
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now().isoformat()
                )
        except Exception as e:
            print(f"위성 번역 실패: {e}")

        return None

    def offline_translate(
            self,
            text: str,
            source_lang: str,
            target_lang: str,
            request_id: str,
            start_time: float) -> TranslationResult:
        """오프라인 번역 (로컬 패턴 매칭)"""
        print(f"📱 오프라인 번역: {text}")

        # 패턴 매칭으로 번역
        translated = None
        confidence = 0.6

        # 정확한 매칭
        if text in self.offline_patterns:
            if target_lang in self.offline_patterns[text]:
                translated = self.offline_patterns[text][target_lang]
                confidence = 0.8

        # 부분 매칭
        if not translated:
            for pattern, translations in self.offline_patterns.items():
                if pattern in text or text in pattern:
                    if target_lang in translations:
                        translated = f"({translations[target_lang]})"
                        confidence = 0.5
                        break

        # 기본 번역
        if not translated:
            translated = f"[{target_lang.upper()}] {text}"
            confidence = 0.3

        return TranslationResult(
            request_id=request_id,
            source_text=text,
            translated_text=translated,
            source_lang=source_lang,
            target_lang=target_lang,
            confidence=confidence,
            method='offline',
            response_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now().isoformat()
        )

    def simulate_online_translation(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """온라인 번역 시뮬레이션"""
        # 기본 패턴 먼저 확인
        if text in self.offline_patterns and target_lang in self.offline_patterns[text]:
            return self.offline_patterns[text][target_lang]

        # 간단한 규칙 기반 번역
        if source_lang == "ko" and target_lang == "en":
            simple_translations = {
                "네": "Yes",
                "아니요": "No",
                "좋습니다": "Good",
                "나쁩니다": "Bad",
                "물": "Water",
                "밥": "Rice",
                "집": "House",
                "학교": "School",
                "병원": "Hospital",
                "공항": "Airport",
                "지금": "Now",
                "내일": "Tomorrow",
                "어제": "Yesterday"
            }
            if text in simple_translations:
                return simple_translations[text]

        # 기본 번역 (언어 코드 표시)
        return f"[AUTO-{target_lang.upper()}] {text}"

    def voice_to_voice_translate(self, source_lang: str, target_lang: str) -> str:
        """음성-음성 실시간 통역"""
        if not VOICE_AVAILABLE or not self.microphone:
            return "음성 기능을 사용할 수 없습니다."

        try:
            print(f"🎤 음성 통역 시작: {source_lang} → {target_lang}")
            self.speak(f"{self.supported_languages[source_lang]}로 말씀해주세요.", "ko")

            # 음성 입력
            with self.microphone as source:
                print("🎤 음성 입력 대기 중...")
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)

            # 하이브리드 음성 인식
            recognized_text = self.hybrid_speech_recognition(audio, source_lang)

            if not recognized_text:
                return "음성을 인식하지 못했습니다."

            print(f"📝 인식된 텍스트: {recognized_text}")

            # 하이브리드 번역
            translation_result = self.hybrid_translate(recognized_text, source_lang, target_lang)

            if translation_result:
                print(f"🌐 번역 결과: {translation_result.translated_text}")
                print(f"⚡ 응답 시간: {translation_result.response_time_ms:.0f}ms")
                print(f"🔧 번역 방법: {translation_result.method}")

                # 번역된 텍스트를 음성으로 출력
                self.speak(translation_result.translated_text, target_lang)

                return f"✅ 음성 통역 완료\n원문: {recognized_text}\n번역: {translation_result.translated_text}"
            else:
                return "번역에 실패했습니다."

        except sr.WaitTimeoutError:
            return "음성 입력 시간이 초과되었습니다."
        except Exception as e:
            return f"음성 통역 오류: {e}"

    def hybrid_speech_recognition(self, audio, language: str) -> Optional[str]:
        """하이브리드 음성 인식"""
        # 1단계: 온라인 음성 인식
        if self.current_connection in ['terrestrial', 'mobile'] and self.connection_quality in ['good', 'fair']:
            try:
                lang_code = language if language != 'sorisae' else 'ko'
                text = self.recognizer.recognize_google(
                    audio, language=f'{lang_code}-KR' if lang_code == 'ko' else lang_code)
                print(f"🌐 온라인 음성 인식: {text}")
                return text
            except Exception as e:
                print(f"온라인 음성 인식 실패: {e}")

        # 2단계: 위성 음성 인식
        if self.current_connection == 'satellite':
            try:
                lang_code = language if language != 'sorisae' else 'ko'
                text = self.recognizer.recognize_google(
                    audio, language=f'{lang_code}-KR' if lang_code == 'ko' else lang_code)
                print(f"🛰️ 위성 음성 인식: {text}")
                return text
            except Exception as e:
                print(f"위성 음성 인식 실패: {e}")

        # 3단계: 오프라인 음성 인식 (기본 패턴)
        print("📱 오프라인 음성 처리 모드")
        return "[음성 인식 결과]"  # 실제로는 오프라인 STT 라이브러리 사용

    def update_connection_status(self):
        """연결 상태 업데이트"""
        if self.connection_manager:
            try:
                if hasattr(self.connection_manager, 'current_primary'):
                    self.current_connection = self.connection_manager.current_primary

                if hasattr(self.connection_manager, 'get_connection_quality'):
                    self.connection_quality = self.connection_manager.get_connection_quality()
                else:
                    # 간단한 연결 품질 테스트
                    try:
                        response = requests.get('https://www.google.com', timeout=3)
                        if response.status_code == 200:
                            self.connection_quality = 'good'
                        else:
                            self.connection_quality = 'poor'
                    except Exception:
                        self.connection_quality = 'poor'
            except Exception as e:
                print(f"연결 상태 업데이트 오류: {e}")

    def voice_command_handler(self, command: str) -> str:
        """음성 명령 처리"""
        cmd = command.lower()

        if '번역' in cmd or '통역' in cmd:
            # 언어 추출
            if '영어' in cmd:
                return self.start_quick_translation('ko', 'en')
            elif '일본어' in cmd:
                return self.start_quick_translation('ko', 'ja')
            elif '중국어' in cmd:
                return self.start_quick_translation('ko', 'zh')
            else:
                return "번역할 언어를 지정해주세요. 예: '영어로 번역'"

        elif '음성' in cmd and '통역' in cmd:
            if '영어' in cmd:
                result = self.voice_to_voice_translate('ko', 'en')
                return result
            elif '일본어' in cmd:
                result = self.voice_to_voice_translate('ko', 'ja')
                return result
            else:
                return "음성 통역할 언어를 지정해주세요."

        elif '지원' in cmd and '언어' in cmd:
            return self.get_supported_languages()

        elif '통역' in cmd and '상태' in cmd:
            return self.get_interpreter_status()

        elif '캐시' in cmd and '초기화' in cmd:
            self.translation_cache.clear()
            return "번역 캐시를 초기화했습니다."

        return "통역 명령을 이해하지 못했습니다."

    def start_quick_translation(self, source_lang: str, target_lang: str) -> str:
        """빠른 번역 시작"""
        if self.microphone:
            self.speak(f"{self.supported_languages[source_lang]}로 텍스트를 입력하거나 말씀해주세요.")
        else:
            print("ℹ️ 현재 환경에서는 텍스트 기반 빠른 번역만 지원합니다.")
        return f"빠른 번역 모드: {source_lang} → {target_lang}"

    def get_supported_languages(self) -> str:
        """지원 언어 목록"""
        langs = "\n".join([f"{code}: {name}" for code, name in self.supported_languages.items()])
        return f"🌐 지원 언어 목록:\n{langs}"

    def get_interpreter_status(self) -> str:
        """통역 시스템 상태"""
        total_translations = len(self.translation_history)
        cache_size = len(self.translation_cache)

        status = f"\n🌐 하이브리드 통역 시스템 상태\n"
        status += f"📡 현재 연결: {self.current_connection}\n"
        status += f"📶 연결 품질: {self.connection_quality}\n"
        status += f"🔤 번역 이력: {total_translations}개\n"
        status += f"💾 캐시 크기: {cache_size}개\n"
        status += f"🌍 지원 언어: {len(self.supported_languages)}개\n"

        # 최근 번역 방법 통계
        if self.translation_history:
            methods = [t.method for t in self.translation_history[-10:]]
            method_counts = {method: methods.count(method) for method in set(methods)}
            status += f"📊 최근 번역 방법: {method_counts}\n"

        return status

    def load_translation_cache(self):
        """번역 캐시 로드"""
        try:
            cache_file = os.path.join(self.data_dir, 'translation_cache.json')
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.translation_cache = json.load(f)
                print(f"💾 번역 캐시 로드: {len(self.translation_cache)}개")
        except Exception as e:
            print(f"캐시 로드 오류: {e}")

    def save_translation_cache(self):
        """번역 캐시 저장"""
        try:
            cache_file = os.path.join(self.data_dir, 'translation_cache.json')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.translation_cache, f, indent=2, ensure_ascii=False)
            print(f"💾 번역 캐시 저장: {len(self.translation_cache)}개")
        except Exception as e:
            print(f"캐시 저장 오류: {e}")

    def save_translation_history(self):
        """번역 이력 저장"""
        try:
            history_file = os.path.join(self.data_dir, f'translation_history_{datetime.now().strftime("%Y%m%d")}.json')
            history_data = [asdict(t) for t in self.translation_history]
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            print(f"📝 번역 이력 저장: {len(self.translation_history)}개")
        except Exception as e:
            print(f"이력 저장 오류: {e}")

    def shutdown(self):
        """시스템 종료"""
        print("🛑 하이브리드 통역 시스템 종료 중...")

        self.active = False
        self.interpreting = False

        # 데이터 저장
        self.save_translation_cache()
        self.save_translation_history()

        print("✅ 하이브리드 통역 시스템 종료 완료")
        self.speak("통역 시스템을 안전하게 종료했습니다.")


def main():
    """메인 실행"""
    interpreter = HybridInterpreterSystem()

    try:
        while interpreter.active:
            print("\n🌐 하이브리드 통역 시스템 메뉴")
            print("=" * 40)
            print("1. 텍스트 번역")
            print("2. 음성-음성 통역")
            print("3. 연속 대화 통역")
            print("4. 지원 언어 확인")
            print("5. 시스템 상태")
            print("6. quit - 종료")
            print("=" * 40)

            choice = input("\n선택하세요: ").strip()

            if choice == '1':
                # 텍스트 번역
                print("\n📝 텍스트 번역 모드")
                source_lang = input("원본 언어 (ko/en/ja/zh/...): ").strip()
                target_lang = input("번역 언어 (ko/en/ja/zh/...): ").strip()
                text = input("번역할 텍스트: ").strip()

                if source_lang in interpreter.supported_languages and target_lang in interpreter.supported_languages:
                    result = interpreter.hybrid_translate(text, source_lang, target_lang)
                    print(f"\n✅ 번역 결과:")
                    print(f"원문: {result.source_text}")
                    print(f"번역: {result.translated_text}")
                    print(f"방법: {result.method}")
                    print(f"신뢰도: {result.confidence:.1%}")
                    print(f"응답시간: {result.response_time_ms:.0f}ms")
                else:
                    print("지원하지 않는 언어입니다.")

            elif choice == '2':
                # 음성-음성 통역
                print("\n🎤 음성-음성 통역 모드")
                source_lang = input("원본 언어 (ko/en/ja/...): ").strip()
                target_lang = input("번역 언어 (ko/en/ja/...): ").strip()

                if source_lang in interpreter.supported_languages and target_lang in interpreter.supported_languages:
                    result = interpreter.voice_to_voice_translate(source_lang, target_lang)
                    print(result)
                else:
                    print("지원하지 않는 언어입니다.")

            elif choice == '3':
                # 연속 대화 통역
                print("\n💬 연속 대화 통역 모드 (구현 예정)")
                print("현재는 개별 번역만 지원됩니다.")

            elif choice == '4':
                # 지원 언어
                print(interpreter.get_supported_languages())

            elif choice == '5':
                # 시스템 상태
                print(interpreter.get_interpreter_status())

            elif choice.lower() in ['6', 'quit', 'exit', '종료']:
                break

            else:
                print("잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n사용자가 시스템을 중단했습니다.")

    finally:
        interpreter.shutdown()


if __name__ == "__main__":
    main()
