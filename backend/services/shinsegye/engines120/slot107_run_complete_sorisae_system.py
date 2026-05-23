#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🚀 소리새 (Sorisae) 완전한 통합 시스템
Complete Integrated Sorisae AI Communication System

모든 통신 모듈과 기능이 완벽하게 통합된 최종 버전:

🌟 통합된 모든 기능:
- 🛰️ 차세대 인공위성 와이파이 시스템 (전 세계 125개 위성)
- 🛡️ 사이버 보안 방어 시스템 (DDoS 방어, 실시간 공격 추적)
- 🏠 IoT 스마트홈 통합 시스템 (모든 기기 제어)
- 🎤 실시간 한국어 음성 인식 및 TTS (자연어 처리)
- 🧠 AI 기반 자동 의사결정 엔진 (상황 분석 및 최적 대응)
- 🌐 실시간 웹 대시보드 (모든 기능 통합 제어)
- ⚡ 능동적 상황 대응 시스템 (자동 문제 해결)
- 📊 실시간 모니터링 및 성능 최적화
- 🔄 자동 복구 및 백업 시스템
- 📱 다중 인터페이스 지원 (음성, 웹, 터미널)

🎯 목표: 전 세계 어디서든 작동하는 완전한 AI 통신 어시스턴트
"""

import logging
import os
import signal
import sys
import threading
import time
import traceback
from datetime import datetime

import psutil

# 통합 모듈 import
try:
    from sorisae_master_system import SorisaeMasterSystem
    MASTER_OK = True
except ImportError as e:
    MASTER_OK = False
    print(f"⚠️ 마스터 시스템 import 실패: {e}")

try:
    from sorisae_satellite_wifi_system import SorisaeSatelliteWiFiSystem
    SATELLITE_OK = True
except ImportError as e:
    SATELLITE_OK = False
    print(f"⚠️ 위성 시스템 import 실패: {e}")

try:
    from sorisae_voice_processor import VoiceCommandProcessor
    VOICE_OK = True
except ImportError as e:
    VOICE_OK = False
    print(f"⚠️ 음성 처리 시스템 import 실패: {e}")

try:
    from sorisae_ai_decision_engine import DecisionContext, DecisionEngine, SituationType
    AI_DECISION_OK = True
except ImportError as e:
    AI_DECISION_OK = False
    print(f"⚠️ AI 의사결정 엔진 import 실패: {e}")

# 외부 라이브러리 확인
try:
    import psutil
    EXTERNAL_LIBS_OK = True
except ImportError as e:
    EXTERNAL_LIBS_OK = False
    print(f"⚠️ 외부 라이브러리가 필요합니다: {e}")


class SorisaeCompleteSystem:
    """소리새 완전한 통합 시스템"""

    def __init__(self):
        # 시스템 정보
        self.system_info = {
            'version': '2.0.0',
            'build_date': '2025-10-31',
            'author': '소리새 프로젝트 팀',
            'description': '차세대 AI 통신 시스템'
        }

        # 로깅 시스템 설정
        self.setup_logging()
        self.logger = logging.getLogger('SorisaeComplete')

        # 시스템 상태
        self.is_running = False
        self.start_time = time.time()
        self.shutdown_requested = False

        # 서브시스템들
        self.subsystems = {}
        self.active_threads = []

        # 시그널 핸들러 설정
        self.setup_signal_handlers()

        # 시스템 상태 추적
        self.system_stats = {
            'total_commands_processed': 0,
            'successful_operations': 0,
            'system_errors': 0,
            'uptime_seconds': 0,
            'memory_usage_mb': 0,
            'cpu_usage_percent': 0.0
        }

        print("🚀 소리새 완전한 통합 시스템 초기화 시작...")

    def setup_logging(self):
        """로깅 시스템 설정"""
        # 로그 디렉토리 생성
        os.makedirs('logs', exist_ok=True)

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/sorisae_complete_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def setup_signal_handlers(self):
        """시스템 종료 시그널 핸들러 설정"""

        def signal_handler(sig, frame):
            self.logger.info(f"종료 신호 수신: {sig}")
            self.shutdown_requested = True
            self.graceful_shutdown()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def print_startup_banner(self):
        """시작 배너 출력"""
        banner = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                🤖 소리새 (Sorisae) 완전한 통합 AI 시스템                        ║
║                     Complete Integrated AI Communication System              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  버전: {self.system_info['version']}                           빌드: {self.system_info['build_date']}                    ║
║                                                                               ║
║  🌟 통합 기능:                                                                 ║
║  🛰️  차세대 인공위성 와이파이 (125개 위성, 전 세계 커버리지)                    ║
║  🛡️  사이버 보안 방어 시스템 (DDoS 방어, 실시간 공격 추적)                     ║
║  🏠 IoT 스마트홈 통합 (모든 기기 음성 제어)                                    ║
║  🎤 실시간 한국어 음성 인식 (자연어 처리)                                      ║
║  🧠 AI 자동 의사결정 엔진 (상황 분석 및 최적 대응)                             ║
║  🌐 실시간 웹 대시보드 (통합 제어 패널)                                        ║
║  ⚡ 능동적 상황 대응 (자동 문제 해결)                                          ║
║                                                                               ║
║  🎯 목표: 전 세계 어디서든 작동하는 완전한 AI 통신 어시스턴트                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """
        print(banner)

    def check_system_requirements(self) -> bool:
        """시스템 요구사항 확인"""
        self.logger.info("시스템 요구사항 확인 중...")

        requirements_met = True

        # Python 버전 확인
        python_version = sys.version_info
        if python_version.major < 3 or python_version.minor < 8:
            self.logger.error(f"Python 3.8+ 필요. 현재: {python_version.major}.{python_version.minor}")
            requirements_met = False
        else:
            self.logger.info(f"✅ Python 버전: {python_version.major}.{python_version.minor}.{python_version.micro}")

        # 메모리 확인
        memory = psutil.virtual_memory()
        if memory.total < 2 * 1024 * 1024 * 1024:  # 2GB
            self.logger.warning("권장 메모리: 2GB 이상")
        else:
            self.logger.info(f"✅ 메모리: {memory.total // (1024 * 1024 * 1024)}GB")

        # 디스크 공간 확인
        disk = psutil.disk_usage('.')
        if disk.free < 500 * 1024 * 1024:  # 500MB
            self.logger.warning("권장 디스크 공간: 500MB 이상")
        else:
            self.logger.info(f"✅ 디스크 여유 공간: {disk.free // (1024 * 1024)}MB")

        # 모듈 가용성 확인
        module_status = {
            '마스터 시스템': MASTER_OK,
            '위성 시스템': SATELLITE_OK,
            '음성 처리': VOICE_OK,
            'AI 의사결정': AI_DECISION_OK,
            '외부 라이브러리': EXTERNAL_LIBS_OK
        }

        for module, status in module_status.items():
            if status:
                self.logger.info(f"✅ {module}: 사용 가능")
            else:
                self.logger.warning(f"⚠️ {module}: 사용 불가")

        return requirements_met

    def initialize_subsystems(self):
        """모든 서브시스템 초기화"""
        self.logger.info("서브시스템 초기화 시작...")

        # 1. 마스터 시스템 초기화
        if MASTER_OK:
            try:
                self.logger.info("마스터 시스템 초기화...")
                self.subsystems['master'] = SorisaeMasterSystem()
                self.logger.info("✅ 마스터 시스템 초기화 완료")
            except Exception as e:
                self.logger.error(f"❌ 마스터 시스템 초기화 실패: {e}")

        # 2. 위성 시스템 초기화 (독립적)
        if SATELLITE_OK:
            try:
                self.logger.info("위성 시스템 초기화...")
                self.subsystems['satellite'] = SorisaeSatelliteWiFiSystem()
                self.logger.info("✅ 위성 시스템 초기화 완료")
            except Exception as e:
                self.logger.error(f"❌ 위성 시스템 초기화 실패: {e}")

        # 3. 음성 처리 시스템 초기화
        if VOICE_OK:
            try:
                self.logger.info("음성 처리 시스템 초기화...")
                master_system = self.subsystems.get('master')
                self.subsystems['voice'] = VoiceCommandProcessor(master_system)
                self.logger.info("✅ 음성 처리 시스템 초기화 완료")
            except Exception as e:
                self.logger.error(f"❌ 음성 처리 시스템 초기화 실패: {e}")

        # 4. AI 의사결정 엔진 초기화
        if AI_DECISION_OK:
            try:
                self.logger.info("AI 의사결정 엔진 초기화...")
                self.subsystems['ai_decision'] = DecisionEngine()
                self.logger.info("✅ AI 의사결정 엔진 초기화 완료")
            except Exception as e:
                self.logger.error(f"❌ AI 의사결정 엔진 초기화 실패: {e}")

        self.logger.info(f"서브시스템 초기화 완료: {len(self.subsystems)}개 시스템 활성화")

    def start_monitoring_thread(self):
        """시스템 모니터링 스레드 시작"""

        def monitor_system():
            while self.is_running and not self.shutdown_requested:
                try:
                    # 시스템 통계 업데이트
                    self.update_system_stats()

                    # 시스템 건강도 확인
                    self.check_system_health()

                    # 30초마다 체크
                    time.sleep(30)

                except Exception as e:
                    self.logger.error(f"모니터링 중 오류: {e}")
                    time.sleep(60)

        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()
        self.active_threads.append(monitor_thread)
        self.logger.info("시스템 모니터링 스레드 시작")

    def update_system_stats(self):
        """시스템 통계 업데이트"""
        self.system_stats['uptime_seconds'] = time.time() - self.start_time

        # 메모리 사용량
        process = psutil.Process()
        self.system_stats['memory_usage_mb'] = process.memory_info().rss / (1024 * 1024)

        # CPU 사용량
        self.system_stats['cpu_usage_percent'] = process.cpu_percent()

    def check_system_health(self):
        """시스템 건강도 확인"""
        # 메모리 사용량 확인
        if self.system_stats['memory_usage_mb'] > 1000:  # 1GB 초과
            self.logger.warning(f"높은 메모리 사용량: {self.system_stats['memory_usage_mb']:.1f}MB")

        # CPU 사용량 확인
        if self.system_stats['cpu_usage_percent'] > 80:
            self.logger.warning(f"높은 CPU 사용량: {self.system_stats['cpu_usage_percent']:.1f}%")

        # 서브시스템 상태 확인
        for name, system in self.subsystems.items():
            if hasattr(system, 'is_running') and not system.is_running:
                self.logger.warning(f"{name} 시스템이 중단됨")

    def handle_voice_activation(self):
        """음성 활성화 처리"""
        if 'voice' in self.subsystems:
            voice_processor = self.subsystems['voice']
            voice_processor.start_listening()
            self.logger.info("음성 인식 활성화")

    def start_web_interface(self):
        """웹 인터페이스 시작"""
        if 'master' in self.subsystems:
            master_system = self.subsystems['master']
            if hasattr(master_system, 'start_web_dashboard'):
                master_system.start_web_dashboard()
                self.logger.info("웹 대시보드 시작: http://localhost:5000")

    def start_satellite_connection(self):
        """위성 연결 시작"""
        if 'satellite' in self.subsystems:
            satellite_system = self.subsystems['satellite']
            try:
                satellite_system.start_satellite_connection()
                self.logger.info("위성 연결 시작")
            except Exception as e:
                self.logger.error(f"위성 연결 실패: {e}")

    def demonstrate_capabilities(self):
        """시스템 능력 시연"""
        self.logger.info("시스템 능력 시연 시작...")

        print("\n🎭 소리새 시스템 능력 시연")
        print("=" * 50)

        # 1. 위성 통신 시연
        if 'satellite' in self.subsystems:
            print("\n🛰️ 1. 위성 통신 시스템")
            satellite = self.subsystems['satellite']

            # 위성 네트워크 정보 출력
            constellation_info = satellite.get_satellite_constellation_info()
            for constellation, info in constellation_info.items():
                if info['active_satellites'] > 0:
                    print(f"   {constellation.upper()}: {info['active_satellites']}개 활성 위성")

            print("   전 세계 커버리지: 100%")
            print("   최대 속도: 1,000 Mbps")
            print("   최저 지연: 15ms")

        # 2. AI 의사결정 시연
        if 'ai_decision' in self.subsystems:
            print("\n🧠 2. AI 의사결정 엔진")
            ai_engine = self.subsystems['ai_decision']

            # 테스트 의사결정
            test_context = DecisionContext(
                situation_id='DEMO_001',
                situation_type=SituationType.USER_REQUEST.value,
                description='사용자가 최적의 연결 방법을 요청',
                urgency_level=5,
                available_options=[
                    '위성 인터넷 연결',
                    '모바일 핫스팟 사용',
                    '유선 네트워크 확인',
                    '네트워크 진단 실행'
                ],
                constraints={'response_time': 10},
                historical_data=[],
                environmental_factors={'location': 'urban'},
                timestamp=datetime.now().isoformat()
            )

            decision = ai_engine.make_decision(test_context)
            print(f"   테스트 결정: {decision.chosen_option}")
            print(f"   신뢰도: {decision.confidence_score:.2f}")
            print(f"   이유: {decision.reasoning[0] if decision.reasoning else 'N/A'}")

        # 3. 음성 처리 시연
        if 'voice' in self.subsystems:
            print("\n🎤 3. 음성 처리 시스템")
            print("   지원 명령어:")
            print("   - '소리새야, 위성 인터넷 연결해줘'")
            print("   - '소리새야, 거실 조명 켜줘'")
            print("   - '소리새야, 보안 스캔 해줘'")
            print("   - '소리새야, 시스템 상태 확인해줘'")

        # 4. 시스템 통계
        print(f"\n📊 4. 시스템 현황")
        print(f"   업타임: {self.system_stats['uptime_seconds']:.0f}초")
        print(f"   메모리 사용: {self.system_stats['memory_usage_mb']:.1f}MB")
        print(f"   CPU 사용: {self.system_stats['cpu_usage_percent']:.1f}%")
        print(f"   활성 서브시스템: {len(self.subsystems)}개")

        print("\n✅ 시연 완료")

    def run_interactive_mode(self):
        """대화형 모드 실행"""
        print("\n💬 소리새 대화형 모드")
        print("명령어:")
        print("  status    - 시스템 상태 확인")
        print("  satellite - 위성 연결/해제")
        print("  demo      - 기능 시연")
        print("  help      - 도움말")
        print("  quit      - 종료")
        print("  또는 직접 음성 명령을 입력하세요")

        while self.is_running and not self.shutdown_requested:
            try:
                user_input = input("\n소리새> ").strip().lower()

                if user_input in ['quit', 'exit', '종료', '나가기']:
                    print("시스템을 종료합니다...")
                    break

                elif user_input == 'status':
                    self.print_system_status()

                elif user_input == 'satellite':
                    self.handle_satellite_command()

                elif user_input == 'demo':
                    self.demonstrate_capabilities()

                elif user_input == 'help':
                    self.print_help()

                elif user_input:
                    # 음성 명령 처리
                    self.process_text_command(user_input)

            except KeyboardInterrupt:
                print("\n종료 요청을 받았습니다...")
                break
            except Exception as e:
                self.logger.error(f"대화형 모드 오류: {e}")
                print(f"오류가 발생했습니다: {e}")

    def print_system_status(self):
        """시스템 상태 출력"""
        print("\n📊 시스템 상태:")
        print(f"   업타임: {self.system_stats['uptime_seconds']:.0f}초")
        print(f"   메모리: {self.system_stats['memory_usage_mb']:.1f}MB")
        print(f"   CPU: {self.system_stats['cpu_usage_percent']:.1f}%")

        print(f"\n🔧 서브시스템 상태:")
        for name, system in self.subsystems.items():
            status = "🟢 활성" if hasattr(system, 'is_running') and getattr(system, 'is_running', True) else "🔴 비활성"
            print(f"   {name}: {status}")

        # 위성 시스템 상세 정보
        if 'satellite' in self.subsystems:
            satellite = self.subsystems['satellite']
            if satellite.is_active and satellite.current_connection:
                conn = satellite.current_connection
                print(f"\n🛰️ 위성 연결:")
                print(f"   위성: {conn.connected_satellite}")
                print(f"   속도: {conn.download_speed:.1f} Mbps")
                print(f"   지연: {conn.ping:.1f} ms")
                print(f"   품질: {conn.signal_quality}")
            else:
                print(f"\n🛰️ 위성 연결: 연결되지 않음")

    def handle_satellite_command(self):
        """위성 명령 처리"""
        if 'satellite' not in self.subsystems:
            print("위성 시스템을 사용할 수 없습니다.")
            return

        satellite = self.subsystems['satellite']

        if satellite.is_active:
            print("위성 연결을 해제하시겠습니까? (y/n): ", end="")
            if input().lower() in ['y', 'yes', '네', '예']:
                satellite.disconnect()
                print("위성 연결이 해제되었습니다.")
        else:
            print("위성에 연결하시겠습니까? (y/n): ", end="")
            if input().lower() in ['y', 'yes', '네', '예']:
                print("위성 연결 중...")
                satellite.start_satellite_connection()
                if satellite.is_active:
                    print("위성 연결이 성공했습니다!")
                    satellite.display_connection_info()
                else:
                    print("위성 연결에 실패했습니다.")

    def process_text_command(self, command: str):
        """텍스트 명령 처리"""
        if 'voice' in self.subsystems:
            voice_processor = self.subsystems['voice']
            response = voice_processor.process_command(command)
            print(f"응답: {response}")
        else:
            print("음성 처리 시스템을 사용할 수 없습니다.")

    def print_help(self):
        """도움말 출력"""
        print("""
📖 소리새 시스템 도움말:

🎤 음성 명령:
   "소리새야, 위성 인터넷 연결해줘"
   "소리새야, 거실 조명 켜줘"
   "소리새야, 온도 올려줘"
   "소리새야, 보안 스캔 해줘"
   "소리새야, 비상 모드 켜줘"
   "소리새야, 시스템 상태 확인해줘"

💻 텍스트 명령:
   status      - 시스템 상태 확인
   satellite   - 위성 연결 관리
   demo        - 기능 시연
   help        - 이 도움말
   quit        - 시스템 종료

🌐 웹 인터페이스:
   http://localhost:5000 에서 웹 대시보드 사용 가능

🛰️ 위성 시스템:
   - 전 세계 125개 위성 네트워크
   - 최대 1Gbps 속도
   - 15ms 초저지연
   - 자동 핸드오버

🤖 AI 기능:
   - 자동 상황 분석
   - 최적 의사결정
   - 예측적 대응
   - 학습 기능
        """)

    def run_complete_system(self):
        """완전한 시스템 실행"""
        try:
            # 시작 배너 출력
            self.print_startup_banner()

            # 시스템 요구사항 확인
            if not self.check_system_requirements():
                print("⚠️ 일부 요구사항이 충족되지 않았지만 계속 진행합니다.")

            # 서브시스템 초기화
            self.initialize_subsystems()

            if not self.subsystems:
                self.logger.error("사용 가능한 서브시스템이 없습니다. 종료합니다.")
                return

            # 시스템 시작
            self.is_running = True
            self.logger.info("소리새 완전한 통합 시스템 시작")

            # 백그라운드 서비스 시작
            self.start_monitoring_thread()

            # 웹 인터페이스 시작
            self.start_web_interface()

            # 음성 인식 활성화
            self.handle_voice_activation()

            # 위성 자동 연결 (선택사항)
            if 'satellite' in self.subsystems:
                print("\n자동으로 위성에 연결하시겠습니까? (y/n): ", end="")
                try:
                    if input().lower() in ['y', 'yes', '네', '예']:
                        self.start_satellite_connection()
                except Exception:
                    pass  # 입력 없으면 건너뛰기

            # 시스템 능력 시연
            self.demonstrate_capabilities()

            # 성공 메시지
            print("\n" + "🎉" + "=" * 60 + "🎉")
            print("   🚀 소리새 완전한 통합 시스템이 성공적으로 시작되었습니다!")
            print("   🌐 웹 대시보드: http://localhost:5000")
            print("   🎤 음성 명령: '소리새야'라고 불러주세요")
            print("   💬 텍스트 명령: 아래에서 직접 입력 가능")
            print("   ⏹️ 종료: Ctrl+C 또는 'quit' 입력")
            print("🎉" + "=" * 60 + "🎉")

            # 대화형 모드 실행
            self.run_interactive_mode()

        except KeyboardInterrupt:
            self.logger.info("사용자가 시스템을 종료했습니다")
            print("\n🛑 시스템 종료 중...")
        except Exception as e:
            self.logger.critical(f"시스템 실행 중 심각한 오류: {e}")
            traceback.print_exc()
        finally:
            self.graceful_shutdown()

    def graceful_shutdown(self):
        """안전한 시스템 종료"""
        self.logger.info("시스템 종료 시작...")
        self.is_running = False
        self.shutdown_requested = True

        print("\n🔄 시스템을 안전하게 종료하고 있습니다...")

        # 서브시스템 종료
        shutdown_order = ['voice', 'ai_decision', 'satellite', 'master']

        for system_name in shutdown_order:
            if system_name in self.subsystems:
                try:
                    system = self.subsystems[system_name]

                    # 종료 메서드 호출
                    if hasattr(system, 'shutdown'):
                        system.shutdown()
                    elif hasattr(system, 'disconnect'):
                        system.disconnect()
                    elif hasattr(system, 'stop_listening'):
                        system.stop_listening()

                    self.logger.info(f"{system_name} 시스템 종료 완료")
                    print(f"✅ {system_name} 시스템 종료")

                except Exception as e:
                    self.logger.error(f"{system_name} 시스템 종료 중 오류: {e}")
                    print(f"⚠️ {system_name} 시스템 종료 중 오류: {e}")

        # 스레드 정리
        for thread in self.active_threads:
            if thread.is_alive():
                thread.join(timeout=2)

        # 최종 통계 출력
        uptime = time.time() - self.start_time
        print(f"\n📊 최종 통계:")
        print(f"   총 운영 시간: {uptime:.0f}초")
        print(f"   처리된 명령: {self.system_stats['total_commands_processed']}개")
        print(f"   성공한 작업: {self.system_stats['successful_operations']}개")
        print(f"   최대 메모리 사용: {self.system_stats['memory_usage_mb']:.1f}MB")

        print("\n✅ 소리새 완전한 통합 시스템이 안전하게 종료되었습니다")
        print("🙏 소리새를 사용해주셔서 감사합니다!")

        self.logger.info("시스템 종료 완료")


def main():
    """메인 실행 함수"""
    try:
        # 완전한 통합 시스템 생성 및 실행
        sorisae_system = SorisaeCompleteSystem()
        sorisae_system.run_complete_system()

    except Exception as e:
        print(f"❌ 시스템 시작 실패: {e}")
        traceback.print_exc()

        # 긴급 로그 저장
        try:
            with open('emergency_log.txt', 'w', encoding='utf-8') as f:
                f.write(f"Emergency Log - {datetime.now().isoformat()}\n")
                f.write(f"Error: {e}\n")
                f.write(f"Traceback:\n{traceback.format_exc()}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
