#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 소리새 (Sorisae) 통합 마스터 시스템
Complete Integrated AI Communication System

모든 통신 모듈과 기능이 통합된 완전한 소리새 AI 시스템:

🌟 통합 기능:
- 🛰️ 차세대 인공위성 와이파이 시스템
- 🛡️ 사이버 보안 방어 시스템 (DDoS 방어, 공격 추적)
- 🏠 IoT 스마트홈 통합 시스템
- 🎤 실시간 음성 인식 및 TTS
- 🌐 다국어 지원 시스템
- 📊 실시간 모니터링 대시보드
- 🤖 AI 기반 자동 의사결정
- ⚡ 능동적 상황 대응 시스템
- 📱 웹 기반 통합 제어 패널
"""

import logging
import os
import threading
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List

# 음성 합성 및 인식
try:
    import pyttsx3
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("⚠️ 음성 라이브러리를 설치하세요: pip install pyttsx3 speechrecognition")

# gTTS 대체 TTS (pyttsx3 실패 시 사용)
try:
    from gtts import gTTS
    import tempfile
    import subprocess
    import platform
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# 웹 서버
try:
    from flask import Flask, jsonify, render_template, request
    from flask_socketio import SocketIO, emit
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False
    print("⚠️ 웹 서버 라이브러리를 설치하세요: pip install flask flask-socketio")

# 기존 모듈들 import
try:
    from sorisae_satellite_wifi_system import SorisaeSatelliteWiFiSystem
    SATELLITE_OK = True
except ImportError:
    SATELLITE_OK = False
    print("⚠️ 위성 와이파이 모듈을 불러올 수 없습니다")


def _play_audio_file_master(file_path: str) -> bool:
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
class SystemStatus:
    """시스템 전체 상태"""
    timestamp: str
    satellite_connected: bool
    satellite_speed: float
    security_active: bool
    iot_devices_count: int
    voice_active: bool
    web_dashboard_active: bool
    ai_decision_active: bool
    total_data_usage: float
    system_uptime: float


@dataclass
class VoiceCommand:
    """음성 명령 데이터"""
    text: str
    confidence: float
    timestamp: str
    processed: bool
    response: str


class SorisaeMasterSystem:
    """소리새 통합 마스터 시스템"""

    def __init__(self):
        self.logger = self._setup_logging()
        self.start_time = time.time()

        # 시스템 상태
        self.is_running = False
        self.system_status = SystemStatus(
            timestamp=datetime.now().isoformat(),
            satellite_connected=False,
            satellite_speed=0.0,
            security_active=False,
            iot_devices_count=0,
            voice_active=False,
            web_dashboard_active=False,
            ai_decision_active=False,
            total_data_usage=0.0,
            system_uptime=0.0
        )

        # 모듈 저장소
        self.modules = {}
        self.command_history = []
        self.active_threads = []

        # 음성 시스템 초기화
        self.voice_engine = None
        self.speech_recognizer = None
        if VOICE_AVAILABLE:
            self._initialize_voice_system()

        # 웹 대시보드 초기화
        self.web_app = None
        self.socketio = None
        if WEB_AVAILABLE:
            self._initialize_web_dashboard()

        print("🤖 소리새 통합 마스터 시스템 초기화 완료!")
        self.speak("소리새 통합 시스템이 준비되었습니다!")

    def _setup_logging(self):
        """로깅 시스템 설정"""
        logger = logging.getLogger('SorisaeMaster')
        logger.setLevel(logging.INFO)

        # 로그 디렉토리 생성
        os.makedirs('logs', exist_ok=True)

        # 파일 핸들러
        file_handler = logging.FileHandler(
            f'logs/sorisae_master_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def _initialize_voice_system(self):
        """음성 시스템 초기화"""
        try:
            # TTS 엔진
            self.voice_engine = pyttsx3.init()
            voices = self.voice_engine.getProperty('voices')

            # 한국어 음성 찾기
            for voice in voices:
                if 'korea' in voice.name.lower() or 'kr' in voice.id.lower():
                    self.voice_engine.setProperty('voice', voice.id)
                    break

            self.voice_engine.setProperty('rate', 180)
            self.voice_engine.setProperty('volume', 0.8)

            # 음성 인식
            self.speech_recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()

            # 환경 소음 보정
            with self.microphone as source:
                self.speech_recognizer.adjust_for_ambient_noise(source)

            self.system_status.voice_active = True
            self.logger.info("음성 시스템 초기화 완료")

        except Exception as e:
            self.logger.error(f"음성 시스템 초기화 실패: {e}")
            self.system_status.voice_active = False

    def _initialize_web_dashboard(self):
        """웹 대시보드 초기화"""
        try:
            self.web_app = Flask(__name__, static_folder='static', template_folder='templates')
            self.web_app.config['SECRET_KEY'] = 'sorisae_secret_2025'
            self.socketio = SocketIO(self.web_app, cors_allowed_origins="*")

            self._setup_web_routes()
            self.system_status.web_dashboard_active = True
            self.logger.info("웹 대시보드 초기화 완료")

        except Exception as e:
            self.logger.error(f"웹 대시보드 초기화 실패: {e}")
            self.system_status.web_dashboard_active = False

    def _setup_web_routes(self):
        """웹 라우트 설정"""
        @self.web_app.route('/')
        def dashboard():
            return render_template('dashboard.html')

        @self.web_app.route('/api/status')
        def get_status():
            self._update_system_status()
            return jsonify(asdict(self.system_status))

        @self.web_app.route('/api/command', methods=['POST'])
        def execute_command():
            command = request.json.get('command', '')
            result = self.process_text_command(command)
            return jsonify({'result': result})

        @self.web_app.route('/api/satellite/connect', methods=['POST'])
        def satellite_connect():
            if 'satellite' in self.modules:
                self.modules['satellite'].start_satellite_connection()
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': '위성 모듈이 없습니다'})

        @self.web_app.route('/api/satellite/disconnect', methods=['POST'])
        def satellite_disconnect():
            if 'satellite' in self.modules:
                self.modules['satellite'].disconnect()
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': '위성 모듈이 없습니다'})

        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info("웹 클라이언트 연결됨")
            emit('status_update', asdict(self.system_status))

        @self.socketio.on('voice_command')
        def handle_voice_command(data):
            command = data.get('command', '')
            result = self.process_text_command(command)
            emit('command_result', {'command': command, 'result': result})

    def speak(self, text: str):
        """음성 출력 - pyttsx3 우선, 실패 시 gTTS 대체"""
        print(f"🗣️ {text}")

        def _speak():
            pyttsx3_success = False
            if self.voice_engine:
                try:
                    self.voice_engine.say(text)
                    self.voice_engine.runAndWait()
                    pyttsx3_success = True
                except Exception as e:
                    self.logger.warning(f"pyttsx3 음성 출력 오류, gTTS 대체 시도: {e}")

            # gTTS 대체 시도
            if not pyttsx3_success and GTTS_AVAILABLE:
                try:
                    tts = gTTS(text=text, lang='ko')
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                        temp_path = fp.name
                    tts.save(temp_path)
                    _play_audio_file_master(temp_path)
                    # 임시 파일 정리
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                except Exception as e:
                    self.logger.error(f"gTTS 오류: {e}")

        thread = threading.Thread(target=_speak, daemon=True)
        thread.start()

    def listen_for_voice_commands(self):
        """음성 명령 대기"""
        if not self.speech_recognizer:
            return

        def _listen():
            while self.is_running:
                try:
                    with self.microphone as source:
                        print("🎤 음성 명령을 기다리고 있습니다...")
                        audio = self.speech_recognizer.listen(source, timeout=1, phrase_time_limit=5)

                    try:
                        # Google Speech Recognition 사용
                        text = self.speech_recognizer.recognize_google(audio, language='ko-KR')

                        if text:
                            self.logger.info(f"음성 명령 인식: {text}")

                            # 음성 명령 기록
                            voice_command = VoiceCommand(
                                text=text,
                                confidence=1.0,
                                timestamp=datetime.now().isoformat(),
                                processed=False,
                                response=""
                            )

                            # 명령 처리
                            response = self.process_voice_command(text)
                            voice_command.response = response
                            voice_command.processed = True

                            self.command_history.append(voice_command)

                            # 웹 클라이언트에 전송
                            if self.socketio:
                                self.socketio.emit('voice_command_received', {
                                    'command': text,
                                    'response': response,
                                    'timestamp': voice_command.timestamp
                                })

                    except sr.UnknownValueError:
                        pass  # 음성을 인식하지 못함
                    except sr.RequestError as e:
                        self.logger.error(f"음성 인식 서비스 오류: {e}")

                except sr.WaitTimeoutError:
                    pass  # 타임아웃
                except Exception as e:
                    self.logger.error(f"음성 인식 중 오류: {e}")
                    time.sleep(1)

        thread = threading.Thread(target=_listen, daemon=True)
        thread.start()
        self.active_threads.append(thread)

    def initialize_all_modules(self):
        """모든 모듈 초기화"""
        self.logger.info("모든 모듈 초기화 시작")

        # 위성 와이파이 모듈
        if SATELLITE_OK:
            try:
                self.modules['satellite'] = SorisaeSatelliteWiFiSystem()
                self.logger.info("위성 와이파이 모듈 초기화 완료")
            except Exception as e:
                self.logger.error(f"위성 모듈 초기화 실패: {e}")

        # 사이버 보안 모듈 (시뮬레이션)
        self.modules['security'] = self._create_security_module()

        # IoT 모듈 (시뮬레이션)
        self.modules['iot'] = self._create_iot_module()

        # AI 의사결정 모듈
        self.modules['ai_decision'] = self._create_ai_decision_module()

        self.logger.info("모든 모듈 초기화 완료")

        # 시스템 상태 업데이트
        self._update_system_status()

    def _create_security_module(self):
        """사이버 보안 모듈 생성 (시뮬레이션)"""

        class SecurityModule:
            def __init__(self):
                self.active = True
                self.threats_blocked = 0
                self.last_scan = datetime.now()

            def scan_threats(self):
                # 위협 스캔 시뮬레이션
                import random
                threats = random.randint(0, 5)
                self.threats_blocked += threats
                self.last_scan = datetime.now()
                return f"{threats}개의 위협을 차단했습니다"

            def get_status(self):
                return {
                    'active': self.active,
                    'threats_blocked': self.threats_blocked,
                    'last_scan': self.last_scan.isoformat()
                }

        return SecurityModule()

    def _create_iot_module(self):
        """IoT 모듈 생성 (시뮬레이션)"""

        class IoTModule:
            def __init__(self):
                self.devices = {
                    'smart_light': {'name': '거실 조명', 'status': 'on', 'brightness': 80},
                    'thermostat': {'name': '온도조절기', 'status': 'auto', 'temperature': 22},
                    'security_camera': {'name': '현관 카메라', 'status': 'recording', 'alerts': 0},
                    'smart_speaker': {'name': '소리새 스피커', 'status': 'listening', 'volume': 60}
                }

            def control_device(self, device_id, command):
                if device_id in self.devices:
                    # 간단한 명령 처리
                    if 'on' in command or '켜' in command:
                        self.devices[device_id]['status'] = 'on'
                        return f"{self.devices[device_id]['name']}을(를) 켰습니다"
                    elif 'off' in command or '꺼' in command:
                        self.devices[device_id]['status'] = 'off'
                        return f"{self.devices[device_id]['name']}을(를) 껐습니다"
                return "명령을 처리할 수 없습니다"

            def get_device_count(self):
                return len([d for d in self.devices.values() if d['status'] != 'off'])

        return IoTModule()

    def _create_ai_decision_module(self):
        """AI 의사결정 모듈 생성"""

        class AIDecisionModule:
            def __init__(self):
                self.active = True
                self.decisions_made = 0
                self.context_memory = []

            def make_decision(self, situation: str, options: List[str]) -> Dict[str, Any]:
                """상황에 따른 AI 의사결정"""
                self.decisions_made += 1

                # 간단한 의사결정 로직
                decision_weights = {}
                for option in options:
                    # 키워드 기반 가중치 계산
                    weight = 0.5  # 기본 가중치

                    if '비상' in situation or '긴급' in situation:
                        if '비상' in option or '응급' in option:
                            weight += 0.4

                    if '연결' in situation:
                        if '위성' in option or '인터넷' in option:
                            weight += 0.3

                    if '보안' in situation:
                        if '방어' in option or '차단' in option:
                            weight += 0.3

                    decision_weights[option] = weight

                # 최고 가중치 옵션 선택
                best_option = max(decision_weights, key=decision_weights.get)
                confidence = decision_weights[best_option]

                decision = {
                    'situation': situation,
                    'chosen_option': best_option,
                    'confidence': confidence,
                    'all_options': decision_weights,
                    'timestamp': datetime.now().isoformat()
                }

                self.context_memory.append(decision)
                if len(self.context_memory) > 100:  # 메모리 관리
                    self.context_memory.pop(0)

                return decision

        return AIDecisionModule()

    def process_voice_command(self, command: str) -> str:
        """음성 명령 처리"""
        command_lower = command.lower()

        try:
            # 위성 관련 명령
            if any(word in command_lower for word in ['위성', '인터넷', '연결']):
                if '연결' in command_lower:
                    if 'satellite' in self.modules:
                        self.modules['satellite'].start_satellite_connection()
                        response = "위성 인터넷 연결을 시작합니다"
                    else:
                        response = "위성 모듈이 준비되지 않았습니다"
                elif '해제' in command_lower or '끊어' in command_lower:
                    if 'satellite' in self.modules:
                        self.modules['satellite'].disconnect()
                        response = "위성 연결을 해제했습니다"
                    else:
                        response = "위성 모듈이 준비되지 않았습니다"
                else:
                    response = "위성 상태를 확인합니다"

            # IoT 제어 명령
            elif any(word in command_lower for word in ['조명', '불', '라이트']):
                if 'iot' in self.modules:
                    result = self.modules['iot'].control_device('smart_light', command)
                    response = result
                else:
                    response = "IoT 시스템이 준비되지 않았습니다"

            # 온도 제어
            elif any(word in command_lower for word in ['온도', '에어컨', '히터']):
                if 'iot' in self.modules:
                    result = self.modules['iot'].control_device('thermostat', command)
                    response = result
                else:
                    response = "온도 제어 시스템이 준비되지 않았습니다"

            # 보안 관련 명령
            elif any(word in command_lower for word in ['보안', '스캔', '위협']):
                if 'security' in self.modules:
                    result = self.modules['security'].scan_threats()
                    response = f"보안 스캔 완료: {result}"
                else:
                    response = "보안 시스템이 준비되지 않았습니다"

            # 상태 확인
            elif any(word in command_lower for word in ['상태', '확인', '체크']):
                self._update_system_status()
                response = f"시스템 정상 작동 중. 업타임: {self.system_status.system_uptime:.1f}초"

            # 비상 모드
            elif any(word in command_lower for word in ['비상', '응급', '긴급']):
                # AI 의사결정으로 비상 대응
                if 'ai_decision' in self.modules:
                    decision = self.modules['ai_decision'].make_decision(
                        "비상 상황 발생",
                        ["위성 비상 연결", "보안 강화", "모든 시스템 점검", "관리자 알림"]
                    )
                    response = f"비상 모드 활성화: {decision['chosen_option']}"

                    # 선택된 옵션 실행
                    if "위성" in decision['chosen_option'] and 'satellite' in self.modules:
                        self.modules['satellite'].emergency_mode()
                else:
                    response = "비상 모드를 활성화합니다"

            # 일반 대화
            else:
                response = f"'{command}' 명령을 처리하고 있습니다"

            self.speak(response)
            return response

        except Exception as e:
            self.logger.error(f"음성 명령 처리 중 오류: {e}")
            error_response = "명령 처리 중 오류가 발생했습니다"
            self.speak(error_response)
            return error_response

    def process_text_command(self, command: str) -> str:
        """텍스트 명령 처리 (웹에서 사용)"""
        return self.process_voice_command(command)  # 같은 로직 사용

    def _update_system_status(self):
        """시스템 상태 업데이트"""
        current_time = time.time()
        self.system_status.timestamp = datetime.now().isoformat()
        self.system_status.system_uptime = current_time - self.start_time

        # 위성 상태
        if 'satellite' in self.modules:
            satellite = self.modules['satellite']
            self.system_status.satellite_connected = satellite.is_active
            if satellite.current_connection:
                self.system_status.satellite_speed = satellite.current_connection.download_speed
                self.system_status.total_data_usage = satellite.current_connection.data_usage

        # 보안 상태
        if 'security' in self.modules:
            self.system_status.security_active = self.modules['security'].active

        # IoT 상태
        if 'iot' in self.modules:
            self.system_status.iot_devices_count = self.modules['iot'].get_device_count()

        # AI 의사결정 상태
        if 'ai_decision' in self.modules:
            self.system_status.ai_decision_active = self.modules['ai_decision'].active

    def start_web_dashboard(self):
        """웹 대시보드 시작"""
        if not self.socketio:
            self.logger.warning("웹 대시보드가 초기화되지 않았습니다")
            return

        def _run_web():
            try:
                self.logger.info("웹 대시보드 시작: http://localhost:5050")
                self.socketio.run(self.web_app, host='0.0.0.0', port=5050, debug=False)
            except Exception as e:
                self.logger.error(f"웹 대시보드 실행 오류: {e}")

        web_thread = threading.Thread(target=_run_web, daemon=True)
        web_thread.start()
        self.active_threads.append(web_thread)

    def start_status_broadcaster(self):
        """상태 정보 브로드캐스터 시작"""

        def _broadcast():
            while self.is_running:
                try:
                    self._update_system_status()

                    if self.socketio:
                        self.socketio.emit('status_update', asdict(self.system_status))

                    time.sleep(5)  # 5초마다 업데이트
                except Exception as e:
                    self.logger.error(f"상태 브로드캐스트 오류: {e}")
                    time.sleep(10)

        broadcast_thread = threading.Thread(target=_broadcast, daemon=True)
        broadcast_thread.start()
        self.active_threads.append(broadcast_thread)

    def run_master_system(self):
        """마스터 시스템 실행"""
        self.logger.info("소리새 마스터 시스템 시작")
        self.is_running = True

        try:
            # 모든 모듈 초기화
            self.initialize_all_modules()

            # 웹 대시보드 시작
            if WEB_AVAILABLE:
                self.start_web_dashboard()
                print("🌐 웹 대시보드: http://localhost:5050")

            # 음성 명령 대기 시작
            if VOICE_AVAILABLE:
                self.listen_for_voice_commands()
                print("🎤 음성 명령 대기 중...")

            # 상태 브로드캐스터 시작
            self.start_status_broadcaster()

            # 시작 메시지
            self.speak("소리새 통합 시스템이 완전히 실행되었습니다!")

            print("\n" + "🤖" + "=" * 60 + "🤖")
            print("   소리새 (Sorisae) 통합 마스터 시스템 실행 중")
            print("   모든 통신 모듈이 활성화되었습니다!")
            print("🤖" + "=" * 60 + "🤖")
            print("\n💬 음성 명령 예시:")
            print("   '소리새야, 위성 인터넷 연결해줘'")
            print("   '소리새야, 거실 조명 켜줘'")
            print("   '소리새야, 보안 스캔 해줘'")
            print("   '소리새야, 시스템 상태 확인해줘'")
            print("   '소리새야, 비상 모드 켜줘'")
            print("\n🌐 웹 제어: http://localhost:5050")
            print("⏹️ 종료: Ctrl+C")

            # 메인 루프
            while self.is_running:
                time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("사용자가 시스템을 종료했습니다")
            print("\n🛑 시스템 종료 중...")
            self.speak("시스템을 안전하게 종료합니다")
        except Exception as e:
            self.logger.critical(f"시스템 실행 중 심각한 오류: {e}")
            traceback.print_exc()
        finally:
            self.shutdown()

    def shutdown(self):
        """시스템 안전 종료"""
        self.logger.info("시스템 종료 시작")
        self.is_running = False

        # 모든 모듈 종료
        for name, module in self.modules.items():
            try:
                if hasattr(module, 'disconnect'):
                    module.disconnect()
                elif hasattr(module, 'shutdown'):
                    module.shutdown()
                self.logger.info(f"{name} 모듈 종료 완료")
            except Exception as e:
                self.logger.error(f"{name} 모듈 종료 중 오류: {e}")

        # 스레드 정리
        for thread in self.active_threads:
            if thread.is_alive():
                thread.join(timeout=1)

        print("✅ 소리새 통합 시스템이 안전하게 종료되었습니다")
        self.logger.info("시스템 종료 완료")


def main():
    """메인 실행 함수"""
    print("🚀 소리새 통합 마스터 시스템 시작...")

    try:
        # 마스터 시스템 생성 및 실행
        master_system = SorisaeMasterSystem()
        master_system.run_master_system()

    except Exception as e:
        print(f"❌ 시스템 시작 실패: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
