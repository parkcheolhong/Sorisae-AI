#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎤🌐 소리새 하이브리드 음성 처리기
Sorisae Hybrid Voice Processor

하이브리드 인터넷 연결을 활용한 지능형 음성 명령 시스템:
- 평상시: 일반 인터넷으로 음성 인식
- 지연시: 자동으로 위성 인터넷 전환
- 오프라인: 로컬 명령 처리
"""

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

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


def _play_audio_file_hybrid(file_path: str) -> bool:
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
class HybridVoiceCommand:
    """하이브리드 음성 명령 구조체"""
    raw_text: str
    processed_text: str
    intent: str
    entities: Dict[str, Any]
    confidence: float
    connection_type: str  # 'terrestrial', 'mobile', 'satellite', 'offline'
    response_time_ms: float
    timestamp: str
    response: str = ""
    executed: bool = False


class HybridVoiceProcessor:
    """하이브리드 음성 처리기"""

    def __init__(self):
        print("🎤🌐" + "=" * 50 + "🎤🌐")
        print("   소리새 하이브리드 음성 처리기")
        print("   Sorisae Hybrid Voice Processor")
        print("🎤🌐" + "=" * 50 + "🎤🌐")
        print()

        # 시스템 상태
        self.active = True
        self.listening = False
        self.hybrid_mode = True

        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('HybridVoiceProcessor')

        # 하이브리드 인터넷 연결
        self.connection_manager = None
        self.current_connection = 'terrestrial'
        self.connection_quality = 'good'
        self.audio_io_enabled = os.environ.get("SORISAE_DISABLE_AUDIO_IO", "0") != "1"
        self.recognizer = None
        self.microphone = None
        self.tts_engine = None

        # 음성 엔진 초기화
        if VOICE_AVAILABLE:
            self.recognizer = sr.Recognizer()
            if self.audio_io_enabled:
                try:
                    self.microphone = sr.Microphone()
                except Exception as e:
                    print(f"⚠️ 기본 입력 장치를 찾을 수 없습니다. 헤드리스 음성 모드로 전환합니다: {e}")
                    self.audio_io_enabled = False
                try:
                    self.tts_engine = pyttsx3.init()
                except Exception as e:
                    print(f"⚠️ TTS 엔진 초기화 실패. 텍스트 응답 모드로 유지합니다: {e}")
                    self.tts_engine = None
            else:
                print("ℹ️ 헤드리스 오디오 모드 - 음성 입출력을 비활성화합니다.")
            self.setup_voice_engine()

        # 명령 처리 시스템
        self.command_history = []
        self.offline_commands = self.setup_offline_commands()

        # 하이브리드 연결 초기화
        self.initialize_hybrid_connections()

        print("✅ 하이브리드 음성 처리기 준비 완료!")
        self.speak("하이브리드 음성 시스템이 준비되었습니다!")

    def initialize_hybrid_connections(self):
        """하이브리드 연결 초기화"""
        try:
            # 통합 하이브리드 시스템 연결
            from sorisae_integrated_hybrid_system import SorisaeIntegratedHybridSystem
            self.connection_manager = SorisaeIntegratedHybridSystem()
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

    def setup_voice_engine(self):
        """TTS 엔진 설정"""
        if not VOICE_AVAILABLE or not self.microphone or not self.tts_engine:
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
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("🎤 마이크 환경 보정 완료")
        except Exception as e:
            print(f"⚠️ 마이크 설정 오류: {e}")

    def setup_offline_commands(self) -> Dict[str, str]:
        """오프라인 명령 설정"""
        return {
            # 연결 관리
            '위성 연결': 'satellite_connect',
            '위성 해제': 'satellite_disconnect',
            '모바일 연결': 'mobile_connect',
            '일반 연결': 'terrestrial_connect',

            # 시스템 상태
            '상태 확인': 'status_check',
            '연결 상태': 'connection_status',
            '시스템 종료': 'shutdown',

            # 긴급 상황
            '비상 모드': 'emergency_mode',
            '긴급 연결': 'emergency_connect',

            # 기본 응답
            '안녕': 'greeting',
            '안녕하세요': 'greeting',
            '소리새야': 'activation',
            '종료': 'shutdown',
            '끝': 'shutdown'
        }

    def speak(self, text: str):
        """음성 출력 - pyttsx3 우선, 실패 시 gTTS 대체"""
        print(f"🗣️ {text}")

        if not VOICE_AVAILABLE or not self.audio_io_enabled or not self.tts_engine:
            return

        def _speak():
            pyttsx3_success = False
            if VOICE_AVAILABLE:
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                    pyttsx3_success = True
                except Exception as e:
                    print(f"pyttsx3 TTS 오류, gTTS 대체 시도: {e}")

            # gTTS 대체 시도
            if not pyttsx3_success and GTTS_AVAILABLE:
                try:
                    tts = gTTS(text=text, lang='ko')
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                        temp_path = fp.name
                    tts.save(temp_path)
                    _play_audio_file_hybrid(temp_path)
                    # 임시 파일 정리
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                except Exception as e:
                    print(f"gTTS 오류: {e}")

        threading.Thread(target=_speak, daemon=True).start()

    def start_listening(self):
        """음성 인식 시작"""
        if not VOICE_AVAILABLE or not self.microphone:
            print("❌ 음성 인식 기능을 사용할 수 없습니다.")
            return

        self.listening = True
        print("👂 하이브리드 음성 인식 시작")

        def listen_loop():
            while self.listening and self.active and not SHUTDOWN_REQUESTED:
                try:
                    # 연결 상태 확인
                    self.check_connection_quality()

                    with self.microphone as source:
                        print("🎤 음성 명령 대기 중... ('소리새야'라고 불러주세요)")
                        audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=5)

                    if SHUTDOWN_REQUESTED:
                        break

                    # 음성을 텍스트로 변환 (하이브리드 방식)
                    text = self.hybrid_speech_recognition(audio)

                    if text and self.is_activation_keyword(text):
                        self.speak("네, 말씀하세요!")
                        self.process_voice_command()

                except sr.WaitTimeoutError:
                    if SHUTDOWN_REQUESTED:
                        break
                    continue
                except Exception as e:
                    self.logger.error(f"음성 인식 오류: {e}")
                    time.sleep(1)

            print("👂 음성 인식 종료")

        threading.Thread(target=listen_loop, daemon=True).start()

    def hybrid_speech_recognition(self, audio) -> Optional[str]:
        """하이브리드 음성 인식"""
        start_time = time.time()

        # 1단계: 빠른 온라인 인식 시도 (일반/모바일 인터넷)
        if self.connection_quality in ['good', 'fair'] and self.current_connection != 'satellite':
            try:
                text = self.recognizer.recognize_google(audio, language='ko-KR')
                response_time = (time.time() - start_time) * 1000
                print(f"🌐 온라인 인식 성공 ({response_time:.0f}ms): {text}")
                return text
            except sr.RequestError:
                print("⚠️ 온라인 인식 실패 - 위성 연결 시도")
                self.switch_to_satellite()
            except sr.UnknownValueError:
                return None

        # 2단계: 위성 인터넷으로 인식 시도
        if self.current_connection == 'satellite' or self.connection_quality == 'poor':
            try:
                # 위성 연결은 지연이 크므로 타임아웃 증가
                self.recognizer.timeout = 10
                text = self.recognizer.recognize_google(audio, language='ko-KR')
                response_time = (time.time() - start_time) * 1000
                print(f"🛰️ 위성 인식 성공 ({response_time:.0f}ms): {text}")
                return text
            except (sr.RequestError, sr.UnknownValueError):
                print("⚠️ 위성 인식 실패 - 오프라인 모드")
            finally:
                self.recognizer.timeout = 5  # 원래대로 복원

        # 3단계: 오프라인 명령 매칭
        try:
            # 간단한 패턴 매칭으로 오프라인 처리
            text = self.offline_speech_recognition(audio)
            if text:
                response_time = (time.time() - start_time) * 1000
                print(f"📱 오프라인 인식 ({response_time:.0f}ms): {text}")
                return text
        except Exception as e:
            print(f"오프라인 인식 오류: {e}")

        return None

    def offline_speech_recognition(self, audio) -> Optional[str]:
        """오프라인 음성 인식 (패턴 매칭)"""
        # 실제로는 오프라인 음성 인식 라이브러리 사용
        # 여기서는 시뮬레이션으로 랜덤하게 오프라인 명령 반환
        import random

        if random.random() < 0.3:  # 30% 확률로 인식 성공
            offline_commands = list(self.offline_commands.keys())
            return random.choice(offline_commands)

        return None

    def check_connection_quality(self):
        """연결 품질 확인"""
        if self.connection_manager:
            try:
                # 연결 관리자에서 현재 상태 가져오기
                if hasattr(self.connection_manager, 'current_primary'):
                    self.current_connection = self.connection_manager.current_primary

                if hasattr(self.connection_manager, 'get_connection_quality'):
                    self.connection_quality = self.connection_manager.get_connection_quality()
                else:
                    # 간단한 품질 테스트
                    import requests
                    start_time = time.time()
                    response = requests.get('https://www.google.com', timeout=3)
                    response_time = (time.time() - start_time) * 1000

                    if response_time < 200:
                        self.connection_quality = 'good'
                    elif response_time < 1000:
                        self.connection_quality = 'fair'
                    else:
                        self.connection_quality = 'poor'
            except Exception:
                self.connection_quality = 'poor'
        else:
            # 기본 연결 테스트
            try:
                import requests
                response = requests.get('https://www.google.com', timeout=2)
                self.connection_quality = 'good' if response.status_code == 200 else 'poor'
                self.current_connection = 'terrestrial'
            except Exception:
                self.connection_quality = 'poor'
                self.current_connection = 'offline'

    def switch_to_satellite(self):
        """위성 연결로 전환"""
        if self.connection_manager:
            try:
                if hasattr(self.connection_manager, 'set_primary_connection'):
                    self.connection_manager.set_primary_connection('satellite')
                    self.current_connection = 'satellite'
                    print("🛰️ 위성 연결로 전환")
                    self.speak("위성 인터넷으로 전환합니다.")
            except Exception as e:
                print(f"위성 전환 오류: {e}")

    def is_activation_keyword(self, text: str) -> bool:
        """활성화 키워드 확인"""
        if not text:
            return False

        activation_keywords = [
            '소리새', '소리새야', 'sorisae',
            '음성', '명령', '시스템'
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in activation_keywords)

    def process_voice_command(self):
        """음성 명령 처리"""
        if not self.microphone:
            self.speak("현재 환경에서는 마이크 입력을 사용할 수 없습니다.")
            return

        try:
            with self.microphone as source:
                print("🎤 명령을 말씀해주세요...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

            # 하이브리드 인식
            command_text = self.hybrid_speech_recognition(audio)

            if command_text:
                print(f"📝 인식된 명령: {command_text}")

                # 명령 처리
                response = self.execute_command(command_text)

                # 응답
                if response:
                    self.speak(response)

                # 명령 이력 저장
                command_record = HybridVoiceCommand(
                    raw_text=command_text,
                    processed_text=command_text.lower().strip(),
                    intent=self.detect_intent(command_text),
                    entities={},
                    confidence=0.8,
                    connection_type=self.current_connection,
                    response_time_ms=0.0,
                    timestamp=datetime.now().isoformat(),
                    response=response or "",
                    executed=True
                )

                self.command_history.append(command_record)
            else:
                self.speak("죄송합니다. 명령을 이해하지 못했습니다.")

        except sr.WaitTimeoutError:
            self.speak("시간이 초과되었습니다. 다시 시도해주세요.")
        except Exception as e:
            print(f"명령 처리 오류: {e}")
            self.speak("명령을 처리하는 중 오류가 발생했습니다.")

    def detect_intent(self, text: str) -> str:
        """의도 감지"""
        text_lower = text.lower()

        # 연결 관리
        if '위성' in text_lower and '연결' in text_lower:
            return 'satellite_connect'
        elif '모바일' in text_lower and '연결' in text_lower:
            return 'mobile_connect'
        elif '일반' in text_lower and '연결' in text_lower:
            return 'terrestrial_connect'

        # 상태 확인
        elif '상태' in text_lower:
            return 'status_check'
        elif '연결' in text_lower and '확인' in text_lower:
            return 'connection_status'

        # 시스템 제어
        elif '종료' in text_lower or '끝' in text_lower:
            return 'shutdown'
        elif '비상' in text_lower or '긴급' in text_lower:
            return 'emergency_mode'

        # 인사
        elif '안녕' in text_lower:
            return 'greeting'

        return 'unknown'

    def execute_command(self, command_text: str) -> str:
        """명령 실행"""
        intent = self.detect_intent(command_text)

        if intent == 'satellite_connect':
            return self.handle_satellite_connect()
        elif intent == 'mobile_connect':
            return self.handle_mobile_connect()
        elif intent == 'terrestrial_connect':
            return self.handle_terrestrial_connect()
        elif intent == 'status_check':
            return self.handle_status_check()
        elif intent == 'connection_status':
            return self.handle_connection_status()
        elif intent == 'emergency_mode':
            return self.handle_emergency_mode()
        elif intent == 'shutdown':
            return self.handle_shutdown()
        elif intent == 'greeting':
            return "안녕하세요! 하이브리드 음성 시스템입니다."
        else:
            return "죄송합니다. 해당 명령을 처리할 수 없습니다."

    def handle_satellite_connect(self) -> str:
        """위성 연결 처리"""
        if self.connection_manager:
            try:
                if hasattr(self.connection_manager, 'voice_command_handler'):
                    return self.connection_manager.voice_command_handler('위성 연결')
                else:
                    self.switch_to_satellite()
                    return "위성 인터넷으로 연결했습니다."
            except Exception as e:
                return f"위성 연결 중 오류가 발생했습니다: {e}"
        return "위성 연결 시스템을 찾을 수 없습니다."

    def handle_mobile_connect(self) -> str:
        """모바일 연결 처리"""
        if self.connection_manager:
            try:
                if hasattr(self.connection_manager, 'voice_command_handler'):
                    return self.connection_manager.voice_command_handler('모바일 연결')
                elif hasattr(self.connection_manager, 'set_primary_connection'):
                    self.connection_manager.set_primary_connection('mobile')
                    self.current_connection = 'mobile'
                    return "모바일 데이터로 연결했습니다."
            except Exception as e:
                return f"모바일 연결 중 오류가 발생했습니다: {e}"
        return "모바일 연결을 시도합니다."

    def handle_terrestrial_connect(self) -> str:
        """지상파 연결 처리"""
        if self.connection_manager:
            try:
                if hasattr(self.connection_manager, 'voice_command_handler'):
                    return self.connection_manager.voice_command_handler('일반 연결')
                elif hasattr(self.connection_manager, 'set_primary_connection'):
                    self.connection_manager.set_primary_connection('terrestrial')
                    self.current_connection = 'terrestrial'
                    return "일반 인터넷으로 연결했습니다."
            except Exception as e:
                return f"일반 연결 중 오류가 발생했습니다: {e}"
        return "일반 인터넷에 연결합니다."

    def handle_status_check(self) -> str:
        """상태 확인 처리"""
        if self.connection_manager:
            try:
                if hasattr(self.connection_manager, 'get_system_status'):
                    status = self.connection_manager.get_system_status()
                    print(status)  # 콘솔에 상세 정보 출력
                    return "시스템 상태를 확인했습니다. 콘솔을 확인해주세요."
                elif hasattr(self.connection_manager, 'voice_command_handler'):
                    return self.connection_manager.voice_command_handler('상태')
            except Exception as e:
                return f"상태 확인 중 오류가 발생했습니다: {e}"

        # 기본 상태 정보
        status = f"현재 연결: {self.current_connection}, 품질: {self.connection_quality}"
        status += f", 명령 이력: {len(self.command_history)}개"
        return status

    def handle_connection_status(self) -> str:
        """연결 상태 처리"""
        return f"현재 {self.current_connection} 연결을 사용 중이며, 품질은 {self.connection_quality}입니다."

    def handle_emergency_mode(self) -> str:
        """비상 모드 처리"""
        if self.connection_manager:
            # 가능한 모든 연결 시도
            self.switch_to_satellite()
        return "비상 모드가 활성화되었습니다. 위성 연결을 시도합니다."

    def handle_shutdown(self) -> str:
        """종료 처리"""
        global SHUTDOWN_REQUESTED
        SHUTDOWN_REQUESTED = True
        self.active = False
        self.listening = False

        if self.connection_manager and hasattr(self.connection_manager, 'shutdown'):
            self.connection_manager.shutdown()

        return "하이브리드 음성 시스템을 종료합니다."

    def get_command_history(self) -> List[Dict]:
        """명령 이력 반환"""
        return [asdict(cmd) for cmd in self.command_history]

    def save_command_history(self, filename: str = None):
        """명령 이력 저장"""
        if not filename:
            filename = f"voice_command_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.get_command_history(), f, indent=2, ensure_ascii=False)
            print(f"💾 명령 이력 저장: {filename}")
        except Exception as e:
            print(f"⚠️ 이력 저장 실패: {e}")


def main():
    """메인 실행"""
    # 신호 처리
    import signal

    def signal_handler(signum, frame):
        global SHUTDOWN_REQUESTED
        print("\n🛑 종료 신호 받음")
        SHUTDOWN_REQUESTED = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 하이브리드 음성 처리기 실행
    processor = HybridVoiceProcessor()

    try:
        # 음성 인식 시작
        processor.start_listening()

        # 메인 루프
        while not SHUTDOWN_REQUESTED and processor.active:
            print("\n📋 하이브리드 음성 명령:")
            print("1. 음성으로 '소리새야'라고 부르기")
            print("2. 텍스트 명령 입력")
            print("3. 'quit' 입력하여 종료")

            user_input = input("\n입력: ").strip()

            if user_input.lower() in ['quit', 'exit', '종료']:
                break
            elif user_input:
                # 텍스트 명령 처리
                response = processor.execute_command(user_input)
                print(f"🤖 응답: {response}")
                processor.speak(response)

    except KeyboardInterrupt:
        print("\n사용자가 프로그램을 중단했습니다.")

    finally:
        # 명령 이력 저장
        processor.save_command_history()
        print("👋 하이브리드 음성 처리기 종료")


if __name__ == "__main__":
    main()
