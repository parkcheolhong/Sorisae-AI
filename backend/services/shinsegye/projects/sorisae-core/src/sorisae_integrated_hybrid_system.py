#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🌐🛰️ 소리새 통합 하이브리드 시스템
Sorisae Integrated Hybrid System

모든 모듈을 하이브리드로 통합:
- 평상시: 일반 인터넷/데이터 사용 (저비용)
- 비상시: 자동 위성 전환 (고신뢰성)
- 지능형: 상황별 최적 연결 선택
- 음성제어: 통합 음성 명령 지원
"""

import json
import os
import platform
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict

import requests

# 음성 합성
try:
    import pyttsx3
    TTS_OK = True
except ImportError:
    TTS_OK = False


@dataclass
class HybridConnection:
    """하이브리드 연결 정보"""
    name: str
    type: str  # 'terrestrial', 'satellite', 'mobile'
    status: str  # 'connected', 'standby', 'disconnected'
    priority: int  # 1=최우선, 2=백업, 3=비상용
    speed_mbps: float
    latency_ms: float
    cost_per_gb: float  # USD
    data_usage_gb: float
    reliability: float  # 0.0-1.0
    coverage: str  # 'local', 'national', 'global'


@dataclass
class SystemModule:
    """시스템 모듈 정보"""
    name: str
    type: str  # 'communication', 'security', 'iot', 'ai'
    status: str
    connection_type: str  # 현재 사용 중인 연결
    data_usage: float
    last_update: str


class SorisaeIntegratedHybridSystem:
    """소리새 통합 하이브리드 시스템"""

    def __init__(self):
        print("🌐🛰️" + "=" * 60 + "🌐🛰️")
        print("   소리새 통합 하이브리드 시스템")
        print("   Sorisae Integrated Hybrid System")
        print("🌐🛰️" + "=" * 60 + "🌐🛰️")
        print()

        # 시스템 상태
        self.active = True
        self.monitoring = False

        # 🔒 Thread safety locks
        self._connections_lock = threading.RLock()
        self._modules_lock = threading.RLock()
        self._status_lock = threading.Lock()

        # 연결 관리
        self.connections: Dict[str, HybridConnection] = {}
        self.current_primary = 'terrestrial'
        self.auto_switch = True

        # 모듈 관리
        self.modules: Dict[str, SystemModule] = {}

        # 데이터 저장
        self.data_dir = "hybrid_system_data"
        os.makedirs(self.data_dir, exist_ok=True)

        # 음성 엔진
        self.audio_io_enabled = os.environ.get("SORISAE_DISABLE_AUDIO_IO", "0") != "1"
        self.tts = None
        if TTS_OK and self.audio_io_enabled:
            try:
                self.tts = pyttsx3.init()
                self.setup_voice()
            except Exception as e:
                print(f"⚠️ 통합 하이브리드 TTS 비활성화: {e}")
        elif TTS_OK:
            print("ℹ️ 통합 하이브리드 헤드리스 오디오 모드")

        # 시스템 초기화
        self.initialize_connections()
        self.initialize_modules()
        self.start_monitoring()

        print("✅ 통합 하이브리드 시스템 초기화 완료!")
        self.speak("소리새 통합 하이브리드 시스템이 준비되었습니다!")

    def setup_voice(self):
        """음성 설정"""
        if TTS_OK and self.tts:
            self.tts.setProperty('rate', 180)
            self.tts.setProperty('volume', 0.8)

    def speak(self, text: str):
        """음성 출력"""
        if TTS_OK and self.audio_io_enabled and self.tts:

            def _speak():
                try:
                    self.tts.say(text)
                    self.tts.runAndWait()
                except Exception:
                    pass
            threading.Thread(target=_speak, daemon=True).start()
        print(f"🗣️ {text}")

    def initialize_connections(self):
        """연결 초기화"""
        print("🔌 연결 시스템 초기화 중...")

        # 1. 지상파 인터넷 (WiFi/유선)
        with self._connections_lock:
            self.connections['terrestrial'] = HybridConnection(
                name='지상파 인터넷',
                type='terrestrial',
                status='unknown',
                priority=1,
                speed_mbps=0.0,
                latency_ms=0.0,
                cost_per_gb=0.001,
                data_usage_gb=0.0,
                reliability=0.85,
                coverage='local'
            )

        # 2. 모바일 데이터 (4G/5G)
        with self._connections_lock:
            self.connections['mobile'] = HybridConnection(
                name='모바일 데이터',
                type='mobile',
                status='unknown',
                priority=2,
                speed_mbps=0.0,
                latency_ms=0.0,
                cost_per_gb=0.01,
                data_usage_gb=0.0,
                reliability=0.75,
                coverage='national'
            )

        # 3. 위성 인터넷 (Starlink 등)
        with self._connections_lock:
            self.connections['satellite'] = HybridConnection(
                name='위성 인터넷',
                type='satellite',
                status='standby',
                priority=3,
                speed_mbps=0.0,
                latency_ms=0.0,
                cost_per_gb=0.1,
                data_usage_gb=0.0,
                reliability=0.95,
                coverage='global'
            )

        # 연결 상태 확인
        self.check_all_connections()

    def initialize_modules(self):
        """모듈 초기화"""
        print("📦 시스템 모듈 초기화 중...")

        modules_config = {
            'voice_processor': {
                'name': '음성 처리기',
                'type': 'communication',
                'bandwidth_requirement': 0.5  # Mbps
            },
            'iot_controller': {
                'name': 'IoT 제어기',
                'type': 'iot',
                'bandwidth_requirement': 0.1
            },
            'security_system': {
                'name': '보안 시스템',
                'type': 'security',
                'bandwidth_requirement': 1.0
            },
            'ai_assistant': {
                'name': 'AI 어시스턴트',
                'type': 'ai',
                'bandwidth_requirement': 2.0
            },
            'satellite_manager': {
                'name': '위성 관리자',
                'type': 'communication',
                'bandwidth_requirement': 0.5
            }
        }

        for module_id, config in modules_config.items():
            self.modules[module_id] = SystemModule(
                name=config['name'],
                type=config['type'],
                status='initialized',
                connection_type=self.current_primary,
                data_usage=0.0,
                last_update=datetime.now().isoformat()
            )

        print(f"✅ {len(self.modules)}개 모듈 초기화 완료")

    def check_all_connections(self):
        """모든 연결 상태 확인"""
        print("🔍 전체 연결 상태 확인 중...")

        # 지상파 인터넷 테스트
        terrestrial_ok = self.test_terrestrial_connection()

        # 모바일 데이터 테스트
        mobile_ok = self.test_mobile_connection()

        # 위성 하드웨어 확인
        satellite_hw = self.detect_satellite_hardware()

        # 우선순위에 따라 주 연결 설정
        if terrestrial_ok:
            self.set_primary_connection('terrestrial')
            print("✅ 지상파 인터넷을 주 연결로 설정")
        elif mobile_ok:
            self.set_primary_connection('mobile')
            print("✅ 모바일 데이터를 주 연결로 설정")
        elif satellite_hw:
            self.set_primary_connection('satellite')
            print("✅ 위성 인터넷을 주 연결로 설정")
        else:
            print("❌ 사용 가능한 연결이 없습니다!")
            self.speak("인터넷 연결을 찾을 수 없습니다.")

    def test_terrestrial_connection(self) -> bool:
        """지상파 인터넷 테스트"""
        try:
            start_time = time.time()
            response = requests.get('https://www.google.com', timeout=5)
            end_time = time.time()

            if response.status_code == 200:
                with self._connections_lock:
                    self.connections['terrestrial'].status = 'connected'
                    self.connections['terrestrial'].latency_ms = (end_time - start_time) * 1000
                    self.connections['terrestrial'].speed_mbps = self.estimate_speed()
                return True
        except Exception:
            pass

        with self._connections_lock:
            self.connections['terrestrial'].status = 'disconnected'
        return False

    def test_mobile_connection(self) -> bool:
        """모바일 데이터 테스트"""
        # 실제로는 모바일 네트워크 인터페이스 확인
        try:
            # Windows에서 모바일 연결 확인
            if platform.system() == "Windows":
                result = subprocess.run(['netsh', 'interface', 'show', 'interface'],
                                        capture_output=True, text=True)
                if 'cellular' in result.stdout.lower() or 'mobile' in result.stdout.lower():
                    with self._connections_lock:
                        self.connections['mobile'].status = 'connected'
                        self.connections['mobile'].speed_mbps = 50.0  # 5G 평균
                        self.connections['mobile'].latency_ms = 20.0
                    return True
        except Exception:
            pass

        # 시뮬레이션: 30% 확률로 모바일 데이터 사용 가능
        import random
        if random.random() < 0.3:
            with self._connections_lock:
                self.connections['mobile'].status = 'connected'
                self.connections['mobile'].speed_mbps = 30.0
                self.connections['mobile'].latency_ms = 25.0
            return True

        with self._connections_lock:
            self.connections['mobile'].status = 'disconnected'
        return False

    def detect_satellite_hardware(self) -> bool:
        """위성 하드웨어 감지"""
        # 실제로는 Starlink, Viasat 등의 하드웨어 감지
        import random
        if random.random() < 0.2:  # 20% 확률로 위성 장비 존재
            with self._connections_lock:
                self.connections['satellite'].status = 'connected'
                self.connections['satellite'].speed_mbps = 150.0
                self.connections['satellite'].latency_ms = 25.0
            return True

        return False

    def estimate_speed(self) -> float:
        """간단한 속도 추정"""
        try:
            start_time = time.time()
            response = requests.get('https://httpbin.org/bytes/102400', timeout=10)  # 100KB
            end_time = time.time()

            if response.status_code == 200:
                duration = end_time - start_time
                kb_per_sec = 100 / duration
                mbps = (kb_per_sec * 8) / 1000
                return max(mbps, 1.0)
        except Exception:
            pass

        return 10.0  # 기본값

    def set_primary_connection(self, connection_type: str):
        """주 연결 설정"""
        if connection_type in self.connections:
            old_primary = self.current_primary
            self.current_primary = connection_type

            # 모든 모듈을 새 연결로 전환
            for module in self.modules.values():
                module.connection_type = connection_type
                module.last_update = datetime.now().isoformat()

            conn = self.connections[connection_type]
            print(f"🔄 주 연결 변경: {old_primary} → {connection_type}")
            print(f"   📡 {conn.name}")
            print(f"   📶 속도: {conn.speed_mbps:.1f} Mbps")
            print(f"   🏓 지연: {conn.latency_ms:.1f} ms")
            print(f"   💰 비용: ${conn.cost_per_gb:.3f}/GB")

            self.speak(f"{conn.name}으로 연결을 전환했습니다.")

    def start_monitoring(self):
        """모니터링 시작"""
        if self.monitoring:
            return

        self.monitoring = True
        print("🔄 지능형 하이브리드 모니터링 시작")

        def monitor_loop():
            while self.monitoring and self.active:
                try:
                    # 현재 연결 상태 확인
                    self.check_current_connection()

                    # 모듈별 데이터 사용량 업데이트
                    self.update_module_usage()

                    # 자동 전환 로직
                    if self.auto_switch:
                        self.intelligent_connection_switch()

                    # 비용 및 사용량 체크
                    self.check_usage_limits()

                    time.sleep(30)  # 30초마다 체크

                except Exception as e:
                    print(f"⚠️ 모니터링 오류: {e}")
                    time.sleep(60)

        threading.Thread(target=monitor_loop, daemon=True).start()

    def check_current_connection(self):
        """현재 연결 상태 확인"""
        current_conn = self.connections[self.current_primary]

        # 연결 품질 테스트
        if current_conn.type == 'terrestrial':
            is_ok = self.test_terrestrial_connection()
        elif current_conn.type == 'mobile':
            is_ok = self.test_mobile_connection()
        elif current_conn.type == 'satellite':
            is_ok = True  # 위성은 보통 안정적
        else:
            is_ok = False

        if not is_ok:
            print(f"⚠️ {current_conn.name} 연결 문제 감지!")
            self.speak(f"{current_conn.name} 연결에 문제가 있습니다.")
            current_conn.status = 'disconnected'

    def intelligent_connection_switch(self):
        """지능형 연결 전환"""
        current_conn = self.connections[self.current_primary]

        # 현재 연결에 문제가 있으면 백업으로 전환
        if current_conn.status == 'disconnected':
            # 우선순위에 따라 백업 연결 찾기
            backup_options = sorted(
                [(k, v) for k, v in self.connections.items()
                 if k != self.current_primary and v.status == 'connected'],
                key=lambda x: x[1].priority
            )

            if backup_options:
                backup_type, backup_conn = backup_options[0]
                print(f"🔄 자동 전환: {current_conn.name} → {backup_conn.name}")
                self.speak(f"연결이 끊어져 {backup_conn.name}으로 자동 전환합니다.")
                self.set_primary_connection(backup_type)

    def update_module_usage(self):
        """모듈별 데이터 사용량 업데이트"""
        for module_id, module in self.modules.items():
            # 시뮬레이션: 모듈별 데이터 사용량 증가
            usage_increment = {
                'voice_processor': 0.05,
                'iot_controller': 0.02,
                'security_system': 0.1,
                'ai_assistant': 0.2,
                'satellite_manager': 0.03
            }.get(module_id, 0.05)

            module.data_usage += usage_increment

            # 연결별 데이터 사용량 업데이트
            if module.connection_type in self.connections:
                self.connections[module.connection_type].data_usage_gb += usage_increment

    def check_usage_limits(self):
        """사용량 제한 확인"""
        # 위성 연결 비용 모니터링
        satellite_conn = self.connections['satellite']
        satellite_cost = satellite_conn.data_usage_gb * satellite_conn.cost_per_gb

        if satellite_cost > 50.0:  # $50 초과시 경고
            print(f"💰 위성 인터넷 비용 경고: ${satellite_cost:.2f}")
            self.speak("위성 인터넷 사용 비용이 높습니다. 다른 연결을 고려하세요.")

    def get_system_status(self) -> str:
        """시스템 상태 보고서"""
        status = "\n🌐🛰️ 통합 하이브리드 시스템 상태\n"
        status += "=" * 50 + "\n"

        # 현재 주 연결
        current = self.connections[self.current_primary]
        status += f"📡 현재 주 연결: {current.name}\n"
        status += f"📶 상태: {current.status}\n"
        status += f"⚡ 속도: {current.speed_mbps:.1f} Mbps\n"
        status += f"🏓 지연: {current.latency_ms:.1f} ms\n"
        status += f"📊 사용량: {current.data_usage_gb:.2f} GB\n"
        status += f"💰 비용: ${current.data_usage_gb * current.cost_per_gb:.2f}\n"

        # 모든 연결 상태
        status += f"\n📋 전체 연결 상태:\n"
        for conn_type, conn in self.connections.items():
            icon = "🟢" if conn.status == "connected" else "🟡" if conn.status == "standby" else "🔴"
            status += f"  {icon} {conn.name} (우선순위 {conn.priority})\n"
            status += f"     속도: {conn.speed_mbps:.1f} Mbps, 비용: ${conn.cost_per_gb:.3f}/GB\n"

        # 모듈 상태
        status += f"\n📦 모듈 상태:\n"
        for module_id, module in self.modules.items():
            status += f"  📱 {module.name}: {module.status}\n"
            status += f"     연결: {self.connections[module.connection_type].name}\n"
            status += f"     사용량: {module.data_usage:.2f} GB\n"

        return status

    def voice_command_handler(self, command: str) -> str:
        """음성 명령 처리"""
        cmd = command.lower().strip()

        # 종료 명령 우선 처리
        if self.is_exit_command(cmd):
            self.handle_exit_command()
            return "시스템을 종료합니다."

        elif 'status' in cmd or cmd == '1':
            status = self.get_system_status()
            self.speak("통합 시스템 상태를 확인합니다.")
            return status

        elif 'satellite' in cmd or cmd == '2':
            if 'satellite' in self.connections and self.connections['satellite'].status != 'disconnected':
                self.set_primary_connection('satellite')
                return "위성 인터넷으로 전환했습니다."
            else:
                return "위성 인터넷을 사용할 수 없습니다."

        elif 'mobile' in cmd or cmd == '3':
            if 'mobile' in self.connections and self.connections['mobile'].status != 'disconnected':
                self.set_primary_connection('mobile')
                return "모바일 데이터로 전환했습니다."
            else:
                return "모바일 데이터를 사용할 수 없습니다."

        elif 'terrestrial' in cmd or cmd == '4':
            if 'terrestrial' in self.connections and self.connections['terrestrial'].status != 'disconnected':
                self.set_primary_connection('terrestrial')
                return "일반 인터넷으로 전환했습니다."
            else:
                return "일반 인터넷을 사용할 수 없습니다."

        elif 'auto' in cmd or cmd == '5':
            self.auto_switch = not self.auto_switch
            mode = "활성화" if self.auto_switch else "비활성화"
            self.speak(f"자동 전환을 {mode}했습니다.")
            return f"자동 전환 {mode}"

        elif 'save' in cmd or cmd == '6':
            # 가장 저렴한 연결로 전환
            cheapest = min(
                [(k, v) for k, v in self.connections.items() if v.status == 'connected'],
                key=lambda x: x[1].cost_per_gb
            )
            if cheapest:
                self.set_primary_connection(cheapest[0])
                return f"비용 절약을 위해 {cheapest[1].name}으로 전환했습니다."

        elif 'quit' in cmd or cmd == '7':
            self.handle_exit_command()
            return "시스템을 종료합니다."

        return "하이브리드 시스템 명령을 이해하지 못했습니다."

    def is_exit_command(self, command: str) -> bool:
        """종료 명령 확인"""
        exit_keywords = [
            'quit', 'exit', '종료', '끝', '그만', 'stop', 'end',
            '7', 'seven', '나가기', '멈춰', '중지', 'bye', 'goodbye'
        ]

        cmd_lower = command.lower().strip()
        return cmd_lower in exit_keywords or any(keyword in cmd_lower for keyword in exit_keywords)

    def handle_exit_command(self):
        """종료 명령 처리"""
        print("🛑 종료 명령 수신")
        self.speak("하이브리드 시스템을 종료합니다.")
        self.shutdown()

    def shutdown(self):
        """시스템 종료"""
        print("🛑 통합 하이브리드 시스템 종료 중...")
        self.active = False
        self.monitoring = False

        # 모든 모듈 정리
        for module in self.modules.values():
            module.status = 'shutdown'

        # 상태 저장
        self.save_system_state()

        print("✅ 시스템 종료 완료")
        self.speak("하이브리드 시스템을 종료했습니다.")

    def save_system_state(self):
        """시스템 상태 저장"""
        try:
            state = {
                'connections': {k: asdict(v) for k, v in self.connections.items()},
                'modules': {k: asdict(v) for k, v in self.modules.items()},
                'current_primary': self.current_primary,
                'timestamp': datetime.now().isoformat()
            }

            with open(os.path.join(self.data_dir, 'system_state.json'), 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            print("💾 시스템 상태 저장 완료")
        except Exception as e:
            print(f"⚠️ 상태 저장 실패: {e}")


def main():
    """메인 실행"""
    hybrid_system = SorisaeIntegratedHybridSystem()

    try:
        while hybrid_system.active:
            print("\n📋 하이브리드 시스템 명령:")
            print("1. status - 시스템 상태")
            print("2. satellite - 위성으로 전환")
            print("3. mobile - 모바일로 전환")
            print("4. terrestrial - 일반 인터넷으로 전환")
            print("5. auto - 자동 전환 토글")
            print("6. save - 절약 모드")
            print("7. quit - 종료")

            user_input = input("\n명령 입력: ").strip()

            if user_input.lower() in ['quit', 'exit', '종료']:
                break
            else:
                result = hybrid_system.voice_command_handler(user_input)
                print(result)

    except KeyboardInterrupt:
        print("\n사용자가 시스템을 중단했습니다.")

    finally:
        hybrid_system.shutdown()


if __name__ == "__main__":
    main()
