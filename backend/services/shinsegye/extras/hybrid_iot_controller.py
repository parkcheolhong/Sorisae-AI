#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏠🌐 소리새 하이브리드 IoT 제어 시스템
Sorisae Hybrid IoT Control System

하이브리드 인터넷 연결을 통한 지능형 IoT 디바이스 관리:
- 평상시: WiFi/유선 인터넷으로 IoT 제어
- 불안정시: 모바일 데이터로 자동 전환
- 비상시: 위성 인터넷으로 원격 제어
- 오프라인: 로컬 캐시된 명령 실행
"""

import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List

# 음성 합성
try:
    import pyttsx3
    TTS_OK = True
except ImportError:
    TTS_OK = False


@dataclass
class IoTDevice:
    """IoT 디바이스 정보"""
    device_id: str
    name: str
    type: str  # 'light', 'airconditioner', 'heater', 'sensor', 'camera'
    location: str
    status: str  # 'online', 'offline', 'error'
    current_state: Dict[str, Any]
    last_update: str
    connection_type: str  # 현재 사용 중인 연결
    local_cache: Dict[str, Any]  # 오프라인 시 사용할 캐시


@dataclass
class IoTCommand:
    """IoT 명령"""
    command_id: str
    device_id: str
    action: str
    parameters: Dict[str, Any]
    connection_type: str
    timestamp: str
    executed: bool = False
    result: str = ""


class HybridIoTController:
    """하이브리드 IoT 제어기"""

    def __init__(self):
        print("🏠🌐" + "=" * 50 + "🏠🌐")
        print("   소리새 하이브리드 IoT 제어 시스템")
        print("   Sorisae Hybrid IoT Control System")
        print("🏠🌐" + "=" * 50 + "🏠🌐")
        print()

        # 시스템 상태
        self.active = True
        self.monitoring = False

        # IoT 디바이스 관리
        self.devices: Dict[str, IoTDevice] = {}
        self.command_queue: List[IoTCommand] = []
        self.command_history: List[IoTCommand] = []

        # 하이브리드 연결 관리
        self.connection_manager = None
        self.current_connection = 'terrestrial'
        self.connection_quality = 'good'

        # 데이터 저장
        self.data_dir = "hybrid_iot_data"
        os.makedirs(self.data_dir, exist_ok=True)

        # 음성 엔진
        self.audio_io_enabled = os.environ.get("SORISAE_DISABLE_AUDIO_IO", "0") != "1"
        self.tts = None
        if TTS_OK and self.audio_io_enabled:
            try:
                self.tts = pyttsx3.init()
                self.setup_voice()
            except Exception as e:
                print(f"⚠️ 하이브리드 IoT TTS 비활성화: {e}")
        elif TTS_OK:
            print("ℹ️ 하이브리드 IoT 헤드리스 오디오 모드")

        # 시스템 초기화
        self.initialize_hybrid_connection()
        self.initialize_iot_devices()
        self.start_monitoring()

        print("✅ 하이브리드 IoT 시스템 준비 완료!")
        self.speak("하이브리드 IoT 제어 시스템이 준비되었습니다!")

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

    def initialize_iot_devices(self):
        """IoT 디바이스 초기화"""
        print("🏠 IoT 디바이스 초기화 중...")

        # 샘플 IoT 디바이스들
        sample_devices = {
            'living_room_light': {
                'name': '거실 조명',
                'type': 'light',
                'location': '거실',
                'current_state': {'power': False, 'brightness': 50, 'color': 'white'}
            },
            'bedroom_light': {
                'name': '침실 조명',
                'type': 'light',
                'location': '침실',
                'current_state': {'power': False, 'brightness': 30, 'color': 'warm_white'}
            },
            'living_room_ac': {
                'name': '거실 에어컨',
                'type': 'airconditioner',
                'location': '거실',
                'current_state': {'power': False, 'temperature': 24, 'mode': 'cool', 'fan_speed': 'auto'}
            },
            'kitchen_heater': {
                'name': '주방 히터',
                'type': 'heater',
                'location': '주방',
                'current_state': {'power': False, 'temperature': 20, 'timer': 0}
            },
            'entrance_camera': {
                'name': '현관 카메라',
                'type': 'camera',
                'location': '현관',
                'current_state': {'recording': True, 'motion_detection': True, 'night_vision': False}
            },
            'living_room_sensor': {
                'name': '거실 센서',
                'type': 'sensor',
                'location': '거실',
                'current_state': {'temperature': 22.5, 'humidity': 45, 'motion': False, 'light_level': 300}
            }
        }

        for device_id, config in sample_devices.items():
            self.devices[device_id] = IoTDevice(
                device_id=device_id,
                name=config['name'],
                type=config['type'],
                location=config['location'],
                status='online',
                current_state=config['current_state'].copy(),
                last_update=datetime.now().isoformat(),
                connection_type=self.current_connection,
                local_cache=config['current_state'].copy()
            )

        print(f"✅ {len(self.devices)}개 IoT 디바이스 초기화 완료")

        # 디바이스 상태 확인
        self.check_all_devices()

    def check_all_devices(self):
        """모든 디바이스 상태 확인"""
        online_count = 0

        for device_id, device in self.devices.items():
            # 연결 상태에 따른 디바이스 접근성 확인
            if self.check_device_connectivity(device):
                device.status = 'online'
                online_count += 1
            else:
                device.status = 'offline'
                # 오프라인 시 로컬 캐시 사용
                print(f"⚠️ {device.name} 오프라인 - 로컬 캐시 사용")

        print(f"📊 디바이스 상태: {online_count}/{len(self.devices)} 온라인")

    def check_device_connectivity(self, device: IoTDevice) -> bool:
        """디바이스 연결성 확인"""
        # 연결 타입별 접근성 시뮬레이션
        if self.current_connection == 'terrestrial':
            return True  # 로컬 WiFi로 모든 디바이스 접근 가능
        elif self.current_connection == 'mobile':
            # 모바일 데이터로는 원격 접근만 가능 (클라우드 기반)
            return device.type in ['camera', 'sensor']  # 일부 디바이스만 가능
        elif self.current_connection == 'satellite':
            # 위성으로는 클라우드 기반 디바이스만 접근
            return device.type in ['camera', 'sensor']
        else:
            return False  # 오프라인

    def start_monitoring(self):
        """모니터링 시작"""
        if self.monitoring:
            return

        self.monitoring = True
        print("🔄 하이브리드 IoT 모니터링 시작")

        def monitor_loop():
            while self.monitoring and self.active:
                try:
                    # 연결 상태 업데이트
                    self.update_connection_status()

                    # 디바이스 상태 확인
                    self.check_all_devices()

                    # 큐에 대기 중인 명령 처리
                    self.process_command_queue()

                    # 센서 데이터 업데이트
                    self.update_sensor_data()

                    time.sleep(10)  # 10초마다 체크

                except Exception as e:
                    print(f"⚠️ 모니터링 오류: {e}")
                    time.sleep(30)

        threading.Thread(target=monitor_loop, daemon=True).start()

    def update_connection_status(self):
        """연결 상태 업데이트"""
        if self.connection_manager:
            try:
                if hasattr(self.connection_manager, 'current_primary'):
                    old_connection = self.current_connection
                    self.current_connection = self.connection_manager.current_primary

                    if old_connection != self.current_connection:
                        print(f"🔄 IoT 연결 변경: {old_connection} → {self.current_connection}")
                        self.handle_connection_change()

                if hasattr(self.connection_manager, 'get_connection_quality'):
                    self.connection_quality = self.connection_manager.get_connection_quality()
            except Exception as e:
                print(f"연결 상태 업데이트 오류: {e}")

    def handle_connection_change(self):
        """연결 변경 처리"""
        # 새로운 연결에 맞게 디바이스 상태 재조정
        self.check_all_devices()

        # 연결별 최적화 설정
        if self.current_connection == 'satellite':
            print("🛰️ 위성 모드: 중요한 디바이스만 제어")
            self.speak("위성 연결로 전환하여 핵심 디바이스만 제어합니다.")
        elif self.current_connection == 'mobile':
            print("📱 모바일 모드: 데이터 절약 모드 활성화")
            self.speak("모바일 데이터 모드로 데이터를 절약합니다.")
        elif self.current_connection == 'terrestrial':
            print("🌐 일반 모드: 모든 디바이스 제어 가능")
            self.speak("일반 인터넷으로 모든 IoT 기능을 사용할 수 있습니다.")

    def process_command_queue(self):
        """명령 큐 처리"""
        if not self.command_queue:
            return

        # 연결 상태에 따라 명령 우선순위 조정
        processed_commands = []

        for command in self.command_queue[:]:
            try:
                success = self.execute_iot_command(command)
                command.executed = success
                command.result = "성공" if success else "실패"

                processed_commands.append(command)
                self.command_queue.remove(command)

            except Exception as e:
                command.result = f"오류: {e}"
                print(f"명령 실행 오류: {e}")

        # 처리된 명령을 이력에 추가
        self.command_history.extend(processed_commands)

    def update_sensor_data(self):
        """센서 데이터 업데이트"""
        import random

        for device_id, device in self.devices.items():
            if device.type == 'sensor' and device.status == 'online':
                # 시뮬레이션: 센서 데이터 업데이트
                device.current_state.update({
                    'temperature': round(22 + random.uniform(-3, 3), 1),
                    'humidity': max(20, min(80, device.current_state.get('humidity', 45) + random.randint(-5, 5))),
                    'motion': random.random() < 0.1,  # 10% 확률로 움직임 감지
                    'light_level': max(0, min(1000, device.current_state.get('light_level', 300) + random.randint(-50, 50)))
                })
                device.last_update = datetime.now().isoformat()

    def control_device(self, device_id: str, action: str, parameters: Dict[str, Any] = None) -> str:
        """디바이스 제어"""
        if device_id not in self.devices:
            return f"디바이스 '{device_id}'를 찾을 수 없습니다."

        device = self.devices[device_id]
        parameters = parameters or {}

        # 명령 생성
        command = IoTCommand(
            command_id=f"cmd_{int(time.time() * 1000)}",
            device_id=device_id,
            action=action,
            parameters=parameters,
            connection_type=self.current_connection,
            timestamp=datetime.now().isoformat()
        )

        # 즉시 실행 또는 큐에 추가
        if device.status == 'online':
            success = self.execute_iot_command(command)
            command.executed = success
            command.result = "성공" if success else "실패"
            self.command_history.append(command)

            if success:
                return f"{device.name} {action} 명령을 실행했습니다."
            else:
                return f"{device.name} {action} 명령 실행에 실패했습니다."
        else:
            # 오프라인 시 큐에 추가
            self.command_queue.append(command)
            return f"{device.name}이 오프라인입니다. 연결 시 자동으로 실행됩니다."

    def execute_iot_command(self, command: IoTCommand) -> bool:
        """IoT 명령 실행"""
        device = self.devices[command.device_id]

        try:
            # 디바이스 타입별 명령 처리
            if device.type == 'light':
                return self.execute_light_command(device, command)
            elif device.type == 'airconditioner':
                return self.execute_ac_command(device, command)
            elif device.type == 'heater':
                return self.execute_heater_command(device, command)
            elif device.type == 'camera':
                return self.execute_camera_command(device, command)
            elif device.type == 'sensor':
                return self.execute_sensor_command(device, command)
            else:
                print(f"⚠️ 지원하지 않는 디바이스 타입: {device.type}")
                return False

        except Exception as e:
            print(f"명령 실행 오류: {e}")
            return False

    def execute_light_command(self, device: IoTDevice, command: IoTCommand) -> bool:
        """조명 제어 명령 실행"""
        action = command.action.lower()
        params = command.parameters

        if action in ['켜기', 'on', 'turn_on']:
            device.current_state['power'] = True
            if 'brightness' in params:
                device.current_state['brightness'] = max(0, min(100, params['brightness']))
            if 'color' in params:
                device.current_state['color'] = params['color']

        elif action in ['끄기', 'off', 'turn_off']:
            device.current_state['power'] = False

        elif action in ['밝기조절', 'brightness']:
            if 'value' in params:
                device.current_state['brightness'] = max(0, min(100, params['value']))

        elif action in ['색상변경', 'color']:
            if 'value' in params:
                device.current_state['color'] = params['value']

        device.last_update = datetime.now().isoformat()
        device.connection_type = self.current_connection
        print(f"💡 {device.name}: {action} 실행 완료")
        return True

    def execute_ac_command(self, device: IoTDevice, command: IoTCommand) -> bool:
        """에어컨 제어 명령 실행"""
        action = command.action.lower()
        params = command.parameters

        if action in ['켜기', 'on', 'turn_on']:
            device.current_state['power'] = True
            if 'temperature' in params:
                device.current_state['temperature'] = max(16, min(30, params['temperature']))
            if 'mode' in params:
                device.current_state['mode'] = params['mode']

        elif action in ['끄기', 'off', 'turn_off']:
            device.current_state['power'] = False

        elif action in ['온도설정', 'temperature']:
            if 'value' in params:
                device.current_state['temperature'] = max(16, min(30, params['value']))

        elif action in ['모드변경', 'mode']:
            if 'value' in params:
                device.current_state['mode'] = params['value']

        device.last_update = datetime.now().isoformat()
        device.connection_type = self.current_connection
        print(f"❄️ {device.name}: {action} 실행 완료")
        return True

    def execute_heater_command(self, device: IoTDevice, command: IoTCommand) -> bool:
        """히터 제어 명령 실행"""
        action = command.action.lower()
        params = command.parameters

        if action in ['켜기', 'on', 'turn_on']:
            device.current_state['power'] = True
            if 'temperature' in params:
                device.current_state['temperature'] = max(10, min(35, params['temperature']))

        elif action in ['끄기', 'off', 'turn_off']:
            device.current_state['power'] = False

        elif action in ['온도설정', 'temperature']:
            if 'value' in params:
                device.current_state['temperature'] = max(10, min(35, params['value']))

        device.last_update = datetime.now().isoformat()
        device.connection_type = self.current_connection
        print(f"🔥 {device.name}: {action} 실행 완료")
        return True

    def execute_camera_command(self, device: IoTDevice, command: IoTCommand) -> bool:
        """카메라 제어 명령 실행"""
        action = command.action.lower()
        params = command.parameters

        if action in ['녹화시작', 'start_recording']:
            device.current_state['recording'] = True

        elif action in ['녹화중지', 'stop_recording']:
            device.current_state['recording'] = False

        elif action in ['움직임감지', 'motion_detection']:
            if 'enable' in params:
                device.current_state['motion_detection'] = params['enable']

        elif action in ['야간모드', 'night_vision']:
            if 'enable' in params:
                device.current_state['night_vision'] = params['enable']

        device.last_update = datetime.now().isoformat()
        device.connection_type = self.current_connection
        print(f"📷 {device.name}: {action} 실행 완료")
        return True

    def execute_sensor_command(self, device: IoTDevice, command: IoTCommand) -> bool:
        """센서 명령 실행"""
        action = command.action.lower()

        if action in ['데이터읽기', 'read_data']:
            print(f"📊 {device.name} 센서 데이터:")
            for key, value in device.current_state.items():
                print(f"   {key}: {value}")

        device.last_update = datetime.now().isoformat()
        device.connection_type = self.current_connection
        return True

    def voice_command_handler(self, command: str) -> str:
        """음성 명령 처리"""
        cmd = command.lower()

        # 조명 제어
        if '조명' in cmd or '불' in cmd or '라이트' in cmd:
            location = self.extract_location(cmd)
            if '켜' in cmd:
                return self.handle_light_on(location)
            elif '꺼' in cmd:
                return self.handle_light_off(location)

        # 에어컨 제어
        elif '에어컨' in cmd:
            location = self.extract_location(cmd)
            if '켜' in cmd:
                temp = self.extract_temperature(cmd)
                return self.handle_ac_on(location, temp)
            elif '꺼' in cmd:
                return self.handle_ac_off(location)

        # 히터 제어
        elif '히터' in cmd:
            location = self.extract_location(cmd)
            if '켜' in cmd:
                temp = self.extract_temperature(cmd)
                return self.handle_heater_on(location, temp)
            elif '꺼' in cmd:
                return self.handle_heater_off(location)

        # 상태 확인
        elif '상태' in cmd:
            return self.get_device_status_summary()

        # 카메라 제어
        elif '카메라' in cmd:
            if '녹화' in cmd:
                if '시작' in cmd:
                    return self.control_device('entrance_camera', '녹화시작')
                elif '중지' in cmd:
                    return self.control_device('entrance_camera', '녹화중지')

        return "IoT 명령을 이해하지 못했습니다."

    def extract_location(self, command: str) -> str:
        """명령에서 위치 추출"""
        locations = ['거실', '침실', '주방', '화장실', '현관']
        for location in locations:
            if location in command:
                return location
        return '거실'  # 기본값

    def extract_temperature(self, command: str) -> int:
        """명령에서 온도 추출"""
        import re
        temp_match = re.search(r'(\d+)도?', command)
        return int(temp_match.group(1)) if temp_match else 24

    def handle_light_on(self, location: str = '거실') -> str:
        """조명 켜기 처리"""
        device_map = {
            '거실': 'living_room_light',
            '침실': 'bedroom_light'
        }

        device_id = device_map.get(location, 'living_room_light')
        result = self.control_device(device_id, '켜기')
        self.speak(f"{location} 조명을 켰습니다.")
        return result

    def handle_light_off(self, location: str = '거실') -> str:
        """조명 끄기 처리"""
        device_map = {
            '거실': 'living_room_light',
            '침실': 'bedroom_light'
        }

        device_id = device_map.get(location, 'living_room_light')
        result = self.control_device(device_id, '끄기')
        self.speak(f"{location} 조명을 껐습니다.")
        return result

    def handle_ac_on(self, location: str = '거실', temperature: int = 24) -> str:
        """에어컨 켜기 처리"""
        device_id = 'living_room_ac'
        result = self.control_device(device_id, '켜기', {'temperature': temperature})
        self.speak(f"{location} 에어컨을 {temperature}도로 설정하여 켰습니다.")
        return result

    def handle_ac_off(self, location: str = '거실') -> str:
        """에어컨 끄기 처리"""
        device_id = 'living_room_ac'
        result = self.control_device(device_id, '끄기')
        self.speak(f"{location} 에어컨을 껐습니다.")
        return result

    def handle_heater_on(self, location: str = '주방', temperature: int = 22) -> str:
        """히터 켜기 처리"""
        device_id = 'kitchen_heater'
        result = self.control_device(device_id, '켜기', {'temperature': temperature})
        self.speak(f"{location} 히터를 {temperature}도로 설정하여 켰습니다.")
        return result

    def handle_heater_off(self, location: str = '주방') -> str:
        """히터 끄기 처리"""
        device_id = 'kitchen_heater'
        result = self.control_device(device_id, '끄기')
        self.speak(f"{location} 히터를 껐습니다.")
        return result

    def get_device_status_summary(self) -> str:
        """디바이스 상태 요약"""
        status = f"\n🏠 하이브리드 IoT 시스템 상태\n"
        status += f"📡 현재 연결: {self.current_connection}\n"
        status += f"📊 연결 품질: {self.connection_quality}\n\n"

        online_devices = [d for d in self.devices.values() if d.status == 'online']
        offline_devices = [d for d in self.devices.values() if d.status == 'offline']

        status += f"✅ 온라인 디바이스 ({len(online_devices)}):\n"
        for device in online_devices:
            power_status = "ON" if device.current_state.get('power', False) else "OFF"
            status += f"  🟢 {device.name} ({device.location}): {power_status}\n"

        if offline_devices:
            status += f"\n❌ 오프라인 디바이스 ({len(offline_devices)}):\n"
            for device in offline_devices:
                status += f"  🔴 {device.name} ({device.location})\n"

        status += f"\n📋 명령 이력: {len(self.command_history)}개"
        status += f"\n⏳ 대기 명령: {len(self.command_queue)}개"

        return status

    def save_device_states(self):
        """디바이스 상태 저장"""
        try:
            device_data = {
                'devices': {k: asdict(v) for k, v in self.devices.items()},
                'connection_type': self.current_connection,
                'timestamp': datetime.now().isoformat()
            }

            filename = os.path.join(self.data_dir, 'device_states.json')
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(device_data, f, indent=2, ensure_ascii=False)

            print("💾 디바이스 상태 저장 완료")
        except Exception as e:
            print(f"⚠️ 상태 저장 실패: {e}")

    def load_device_states(self):
        """디바이스 상태 로드"""
        try:
            filename = os.path.join(self.data_dir, 'device_states.json')
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 디바이스 상태 복원
                for device_id, device_data in data['devices'].items():
                    if device_id in self.devices:
                        self.devices[device_id].current_state = device_data['current_state']
                        self.devices[device_id].local_cache = device_data['local_cache']

                print("💾 디바이스 상태 로드 완료")
        except Exception as e:
            print(f"⚠️ 상태 로드 실패: {e}")

    def shutdown(self):
        """시스템 종료"""
        print("🛑 하이브리드 IoT 시스템 종료 중...")

        self.active = False
        self.monitoring = False

        # 모든 디바이스 상태 저장
        self.save_device_states()

        # 대기 중인 명령들 처리
        if self.command_queue:
            print(f"⏳ {len(self.command_queue)}개 대기 명령을 저장합니다...")
            # 명령 큐를 파일로 저장
            queue_file = os.path.join(self.data_dir, 'pending_commands.json')
            try:
                with open(queue_file, 'w', encoding='utf-8') as f:
                    json.dump([asdict(cmd) for cmd in self.command_queue], f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"명령 큐 저장 실패: {e}")

        print("✅ 하이브리드 IoT 시스템 종료 완료")
        self.speak("IoT 시스템을 안전하게 종료했습니다.")


def main():
    """메인 실행"""
    iot_controller = HybridIoTController()

    try:
        while iot_controller.active:
            print("\n🏠 하이브리드 IoT 제어 명령:")
            print("1. '거실 조명 켜줘' - 조명 제어")
            print("2. '에어컨 24도로 켜줘' - 에어컨 제어")
            print("3. '주방 히터 켜줘' - 히터 제어")
            print("4. 'status' - 상태 확인")
            print("5. 'quit' - 종료")

            user_input = input("\n명령 입력: ").strip()

            if user_input.lower() in ['quit', 'exit', '종료']:
                break
            else:
                result = iot_controller.voice_command_handler(user_input)
                print(result)

    except KeyboardInterrupt:
        print("\n사용자가 시스템을 중단했습니다.")

    finally:
        iot_controller.shutdown()


if __name__ == "__main__":
    main()
