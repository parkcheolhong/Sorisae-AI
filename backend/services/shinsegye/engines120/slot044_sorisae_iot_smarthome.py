#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
소리새 IoT 스마트홈 통합 시스템 (Sorisae IoT Smart Home Integration)
스마트 디바이스 제어, 센서 모니터링, 환경 자동화 시스템
"""

import json
import random
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# MQTT 및 IoT 통신을 위한 라이브러리 (설치 필요: pip install paho-mqtt)
try:
    import paho.mqtt.client as mqtt  # type: ignore
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("⚠️ MQTT 라이브러리가 없습니다. 시뮬레이션 모드로 실행됩니다.")


class DeviceType(Enum):
    """IoT 디바이스 타입"""
    LIGHT = "light"                 # 조명
    THERMOSTAT = "thermostat"      # 온도조절기
    SMART_PLUG = "smart_plug"      # 스마트 플러그
    SENSOR = "sensor"              # 센서
    CAMERA = "camera"              # 카메라
    SPEAKER = "speaker"            # 스피커
    TV = "tv"                      # 텔레비전
    AIR_CONDITIONER = "ac"         # 에어컨
    HUMIDIFIER = "humidifier"      # 가습기
    VACUUM = "vacuum"              # 로봇청소기
    DOOR_LOCK = "door_lock"        # 스마트 도어락
    WINDOW_BLIND = "window_blind"  # 스마트 블라인드


class SensorType(Enum):
    """센서 타입"""
    TEMPERATURE = "temperature"    # 온도 센서
    HUMIDITY = "humidity"          # 습도 센서
    LIGHT = "light"               # 조도 센서
    MOTION = "motion"             # 동작 감지 센서
    AIR_QUALITY = "air_quality"   # 공기질 센서
    SOUND = "sound"               # 소음 센서
    DOOR = "door"                 # 도어 센서
    WINDOW = "window"             # 창문 센서


class DeviceStatus(Enum):
    """디바이스 상태"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class IoTDevice:
    """IoT 디바이스"""
    device_id: str
    name: str
    device_type: DeviceType
    location: str
    status: DeviceStatus = DeviceStatus.OFFLINE
    properties: Dict[str, Any] = field(default_factory=dict)
    last_update: datetime = field(default_factory=datetime.now)
    ip_address: Optional[str] = None
    mqtt_topic: Optional[str] = None
    brand: str = "Generic"
    model: str = "Unknown"


@dataclass
class SensorData:
    """센서 데이터"""
    sensor_id: str
    sensor_type: SensorType
    value: Union[float, int, bool, str]
    unit: str
    timestamp: datetime
    location: str
    device_id: str


@dataclass
class AutomationRule:
    """자동화 룰"""
    rule_id: str
    name: str
    trigger_conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None


class SorisaeIoTManager:
    """소리새 IoT 관리자"""

    def __init__(self, mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        self.devices = {}
        self.sensor_data = defaultdict(deque)
        self.automation_rules = {}
        self.device_history = defaultdict(list)

        # MQTT 설정
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_client = None
        self.mqtt_connected = False

        # 스레드 관리
        self.monitoring_thread = None
        self.automation_thread = None
        self.running = True

        # 환경 데이터
        self.environment_status = {
            'temperature': 22.0,
            'humidity': 45.0,
            'light_level': 300,
            'air_quality': 'good',
            'sound_level': 35
        }

        self._initialize_mqtt()
        self._start_background_services()
        self._create_default_devices()

        print("🏠 소리새 IoT 스마트홈 시스템 초기화 완료!")

    def _initialize_mqtt(self):
        """MQTT 클라이언트 초기화"""
        if not MQTT_AVAILABLE:
            print("📡 MQTT 시뮬레이션 모드로 실행")
            return

        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

            # MQTT 브로커 연결 시도
            self.mqtt_client.connect_async(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()

        except Exception as e:
            print(f"⚠️ MQTT 연결 실패: {e}. 시뮬레이션 모드로 실행됩니다.")

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT 연결 콜백"""
        if rc == 0:
            self.mqtt_connected = True
            print("📡 MQTT 브로커 연결 성공")
            # 모든 디바이스 토픽 구독
            client.subscribe("sorisae/+/+/status")
            client.subscribe("sorisae/+/+/data")
        else:
            print(f"❌ MQTT 연결 실패: {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT 메시지 수신 콜백"""
        try:
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 4:
                topic_parts[1]
                device_id = topic_parts[2]
                message_type = topic_parts[3]

                payload = json.loads(msg.payload.decode())

                if message_type == "status":
                    self._update_device_status(device_id, payload)
                elif message_type == "data":
                    self._process_sensor_data(device_id, payload)

        except Exception as e:
            print(f"⚠️ MQTT 메시지 처리 오류: {e}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT 연결 해제 콜백"""
        self.mqtt_connected = False
        print("📡 MQTT 브로커 연결 해제됨")

    def _start_background_services(self):
        """백그라운드 서비스 시작"""
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.automation_thread = threading.Thread(target=self._automation_loop, daemon=True)

        self.monitoring_thread.start()
        self.automation_thread.start()

    def _monitoring_loop(self):
        """디바이스 모니터링 루프"""
        while self.running:
            try:
                # 센서 데이터 시뮬레이션 (실제 환경에서는 실제 센서에서 읽음)
                self._simulate_sensor_data()

                # 디바이스 상태 체크
                self._check_device_health()

                time.sleep(5)  # 5초마다 모니터링

            except Exception as e:
                print(f"⚠️ 모니터링 오류: {e}")
                time.sleep(10)

    def _automation_loop(self):
        """자동화 룰 실행 루프"""
        while self.running:
            try:
                # 활성화된 자동화 룰 실행
                for rule in self.automation_rules.values():
                    if rule.enabled:
                        self._check_automation_rule(rule)

                time.sleep(2)  # 2초마다 자동화 체크

            except Exception as e:
                print(f"⚠️ 자동화 오류: {e}")
                time.sleep(5)

    def _create_default_devices(self):
        """기본 디바이스 생성"""
        default_devices = [
            # 조명
            IoTDevice("light_living", "거실 조명", DeviceType.LIGHT, "거실",
                      properties={"brightness": 80, "color": "#FFFFFF", "power": True}),
            IoTDevice("light_bedroom", "침실 조명", DeviceType.LIGHT, "침실",
                      properties={"brightness": 60, "color": "#FFEEAA", "power": False}),
            IoTDevice("light_kitchen", "주방 조명", DeviceType.LIGHT, "주방",
                      properties={"brightness": 100, "color": "#FFFFFF", "power": True}),

            # 센서
            IoTDevice("sensor_temp_living", "거실 온도센서", DeviceType.SENSOR, "거실",
                      properties={"temperature": 22.5, "humidity": 45}),
            IoTDevice("sensor_motion_entrance", "현관 동작감지", DeviceType.SENSOR, "현관",
                      properties={"motion_detected": False}),
            IoTDevice("sensor_door_main", "현관문 센서", DeviceType.SENSOR, "현관",
                      properties={"door_open": False}),

            # 스마트 가전
            IoTDevice("ac_living", "거실 에어컨", DeviceType.AIR_CONDITIONER, "거실",
                      properties={"power": False, "temperature": 24, "mode": "auto"}),
            IoTDevice("tv_living", "거실 TV", DeviceType.TV, "거실",
                      properties={"power": False, "volume": 15, "channel": 1}),
            IoTDevice("speaker_living", "거실 스피커", DeviceType.SPEAKER, "거실",
                      properties={"power": False, "volume": 50}),

            # 스마트 플러그
            IoTDevice("plug_bedroom", "침실 스마트플러그", DeviceType.SMART_PLUG, "침실",
                      properties={"power": True, "power_consumption": 5.2}),
            IoTDevice("plug_kitchen", "주방 스마트플러그", DeviceType.SMART_PLUG, "주방",
                      properties={"power": True, "power_consumption": 12.8}),

            # 기타
            IoTDevice("vacuum_main", "로봇청소기", DeviceType.VACUUM, "거실",
                      properties={"power": False, "battery": 85, "status": "charging"}),
            IoTDevice("humidifier_bedroom", "침실 가습기", DeviceType.HUMIDIFIER, "침실",
                      properties={"power": False, "humidity_target": 50})
        ]

        for device in default_devices:
            device.status = DeviceStatus.ONLINE
            self.devices[device.device_id] = device
            print(f"  📱 {device.name} ({device.device_type.value}) 등록")

    def _simulate_sensor_data(self):
        """센서 데이터 시뮬레이션"""
        current_time = datetime.now()

        # 온도 센서 시뮬레이션
        temp_variation = random.uniform(-0.5, 0.5)
        new_temp = max(18, min(28, self.environment_status['temperature'] + temp_variation))
        self.environment_status['temperature'] = new_temp

        temp_sensor = SensorData(
            sensor_id="sensor_temp_living",
            sensor_type=SensorType.TEMPERATURE,
            value=round(new_temp, 1),
            unit="°C",
            timestamp=current_time,
            location="거실",
            device_id="sensor_temp_living"
        )

        self.sensor_data["sensor_temp_living"].append(temp_sensor)
        if len(self.sensor_data["sensor_temp_living"]) > 100:
            self.sensor_data["sensor_temp_living"].popleft()

        # 습도 센서 시뮬레이션
        humidity_variation = random.uniform(-2, 2)
        new_humidity = max(30, min(70, self.environment_status['humidity'] + humidity_variation))
        self.environment_status['humidity'] = new_humidity

        humidity_sensor = SensorData(
            sensor_id="sensor_temp_living",
            sensor_type=SensorType.HUMIDITY,
            value=round(new_humidity, 1),
            unit="%",
            timestamp=current_time,
            location="거실",
            device_id="sensor_temp_living"
        )

        # 조도 센서 시뮬레이션 (시간대에 따라)
        hour = current_time.hour
        if 6 <= hour <= 18:  # 낮 시간
            base_light = 800
        elif 19 <= hour <= 22:  # 저녁
            base_light = 300
        else:  # 밤
            base_light = 50

        light_variation = random.uniform(-50, 50)
        new_light = max(0, base_light + light_variation)
        self.environment_status['light_level'] = new_light

        # 동작 감지 시뮬레이션 (랜덤)
        motion_detected = random.random() < 0.05  # 5% 확률로 동작 감지
        if motion_detected:
            motion_sensor = SensorData(
                sensor_id="sensor_motion_entrance",
                sensor_type=SensorType.MOTION,
                value=True,
                unit="boolean",
                timestamp=current_time,
                location="현관",
                device_id="sensor_motion_entrance"
            )

            self.sensor_data["sensor_motion_entrance"].append(motion_sensor)

    def _check_device_health(self):
        """디바이스 상태 체크"""
        for device in self.devices.values():
            # 디바이스 응답 시뮬레이션
            if random.random() < 0.95:  # 95% 확률로 정상
                if device.status == DeviceStatus.OFFLINE:
                    device.status = DeviceStatus.ONLINE
                    print(f"📱 {device.name} 온라인 복구됨")
            else:
                if device.status == DeviceStatus.ONLINE:
                    device.status = DeviceStatus.OFFLINE
                    print(f"⚠️ {device.name} 오프라인됨")

            device.last_update = datetime.now()

    def _check_automation_rule(self, rule: AutomationRule):
        """자동화 룰 체크"""
        try:
            # 트리거 조건 확인
            conditions_met = True
            for condition in rule.trigger_conditions:
                if not self._evaluate_condition(condition):
                    conditions_met = False
                    break

            if conditions_met:
                # 액션 실행
                for action in rule.actions:
                    self._execute_action(action)

                rule.last_triggered = datetime.now()
                print(f"🤖 자동화 룰 '{rule.name}' 실행됨")

        except Exception as e:
            print(f"⚠️ 자동화 룰 '{rule.name}' 실행 오류: {e}")

    def _evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        """조건 평가"""
        condition_type = condition.get("type")

        if condition_type == "time":
            # 시간 조건
            current_time = datetime.now().time()
            start_time = datetime.strptime(condition["start_time"], "%H:%M").time()
            end_time = datetime.strptime(condition["end_time"], "%H:%M").time()
            return start_time <= current_time <= end_time

        elif condition_type == "sensor":
            # 센서 조건
            device_id = condition["device_id"]
            sensor_type = condition["sensor_type"]
            operator = condition["operator"]
            threshold = condition["threshold"]

            # 최근 센서 데이터 확인
            if device_id in self.sensor_data:
                recent_data = list(self.sensor_data[device_id])[-1:]
                if recent_data:
                    sensor_data = recent_data[0]
                    if sensor_data.sensor_type.value == sensor_type:
                        if operator == "gt":
                            return sensor_data.value > threshold
                        elif operator == "lt":
                            return sensor_data.value < threshold
                        elif operator == "eq":
                            return sensor_data.value == threshold

        elif condition_type == "device":
            # 디바이스 상태 조건
            device_id = condition["device_id"]
            property_name = condition["property"]
            expected_value = condition["value"]

            if device_id in self.devices:
                device = self.devices[device_id]
                current_value = device.properties.get(property_name)
                return current_value == expected_value

        return False

    def _execute_action(self, action: Dict[str, Any]):
        """액션 실행"""
        action_type = action.get("type")

        if action_type == "device_control":
            device_id = action["device_id"]
            property_name = action["property"]
            value = action["value"]

            self.control_device(device_id, {property_name: value})

        elif action_type == "notification":
            message = action["message"]
            print(f"🔔 자동화 알림: {message}")

        elif action_type == "scene":
            scene_name = action["scene_name"]
            self.activate_scene(scene_name)

    def add_device(self, device: IoTDevice) -> bool:
        """디바이스 추가"""
        try:
            self.devices[device.device_id] = device
            print(f"📱 디바이스 추가됨: {device.name}")
            return True
        except Exception as e:
            print(f"❌ 디바이스 추가 실패: {e}")
            return False

    def remove_device(self, device_id: str) -> bool:
        """디바이스 제거"""
        try:
            if device_id in self.devices:
                device_name = self.devices[device_id].name
                del self.devices[device_id]
                print(f"🗑️ 디바이스 제거됨: {device_name}")
                return True
            return False
        except Exception as e:
            print(f"❌ 디바이스 제거 실패: {e}")
            return False

    def control_device(self, device_id: str, commands: Dict[str, Any]) -> bool:
        """디바이스 제어"""
        try:
            if device_id not in self.devices:
                print(f"❌ 디바이스를 찾을 수 없음: {device_id}")
                return False

            device = self.devices[device_id]

            for property_name, value in commands.items():
                device.properties[property_name] = value

            device.last_update = datetime.now()

            # MQTT 메시지 발송 (시뮬레이션)
            if self.mqtt_connected and self.mqtt_client:
                topic = f"sorisae/{device.device_type.value}/{device_id}/command"
                payload = json.dumps(commands)
                self.mqtt_client.publish(topic, payload)

            # 히스토리 저장
            self.device_history[device_id].append({
                'timestamp': datetime.now().isoformat(),
                'action': 'control',
                'commands': commands
            })

            print(f"🎛️ {device.name} 제어 완료: {commands}")
            return True

        except Exception as e:
            print(f"❌ 디바이스 제어 실패: {e}")
            return False

    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """디바이스 상태 조회"""
        if device_id in self.devices:
            device = self.devices[device_id]
            return {
                'device_id': device.device_id,
                'name': device.name,
                'type': device.device_type.value,
                'location': device.location,
                'status': device.status.value,
                'properties': device.properties,
                'last_update': device.last_update.isoformat()
            }
        return None

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """모든 디바이스 목록 조회"""
        devices_list = []
        for device in self.devices.values():
            devices_list.append({
                'device_id': device.device_id,
                'name': device.name,
                'type': device.device_type.value,
                'location': device.location,
                'status': device.status.value,
                'properties': device.properties
            })
        return devices_list

    def get_sensor_data(self, sensor_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """센서 데이터 조회"""
        if sensor_id in self.sensor_data:
            recent_data = list(self.sensor_data[sensor_id])[-limit:]
            return [{
                'sensor_id': data.sensor_id,
                'type': data.sensor_type.value,
                'value': data.value,
                'unit': data.unit,
                'timestamp': data.timestamp.isoformat(),
                'location': data.location
            } for data in recent_data]
        return []

    def create_automation_rule(self, rule: AutomationRule) -> bool:
        """자동화 룰 생성"""
        try:
            self.automation_rules[rule.rule_id] = rule
            print(f"🤖 자동화 룰 생성됨: {rule.name}")
            return True
        except Exception as e:
            print(f"❌ 자동화 룰 생성 실패: {e}")
            return False

    def activate_scene(self, scene_name: str) -> bool:
        """시나리오 활성화"""
        scenes = {
            "외출": {
                "light_living": {"power": False},
                "light_bedroom": {"power": False},
                "light_kitchen": {"power": False},
                "ac_living": {"power": False},
                "tv_living": {"power": False}
            },
            "귀가": {
                "light_living": {"power": True, "brightness": 80},
                "light_kitchen": {"power": True, "brightness": 70},
                "ac_living": {"power": True, "temperature": 24}
            },
            "취침": {
                "light_living": {"power": False},
                "light_bedroom": {"power": True, "brightness": 30},
                "tv_living": {"power": False},
                "ac_living": {"temperature": 22}
            },
            "영화감상": {
                "light_living": {"power": True, "brightness": 20},
                "tv_living": {"power": True, "volume": 25},
                "speaker_living": {"power": True, "volume": 60}
            }
        }

        if scene_name in scenes:
            scene_commands = scenes[scene_name]
            success_count = 0

            for device_id, commands in scene_commands.items():
                if self.control_device(device_id, commands):
                    success_count += 1

            print(f"🎬 '{scene_name}' 시나리오 실행 완료: {success_count}개 디바이스 제어")
            return success_count > 0

        return False

    def get_environment_status(self) -> Dict[str, Any]:
        """환경 상태 조회"""
        return {
            'temperature': self.environment_status['temperature'],
            'humidity': self.environment_status['humidity'],
            'light_level': self.environment_status['light_level'],
            'air_quality': self.environment_status['air_quality'],
            'sound_level': self.environment_status['sound_level'],
            'timestamp': datetime.now().isoformat()
        }

    def get_energy_consumption(self) -> Dict[str, Any]:
        """에너지 소비량 조회"""
        total_consumption = 0
        device_consumption = {}

        for device in self.devices.values():
            if device.device_type in [DeviceType.SMART_PLUG, DeviceType.AIR_CONDITIONER, DeviceType.TV]:
                consumption = device.properties.get('power_consumption', 0)
                if device.properties.get('power', False):
                    device_consumption[device.device_id] = consumption
                    total_consumption += consumption
                else:
                    device_consumption[device.device_id] = 0

        return {
            'total_consumption': round(total_consumption, 2),
            'device_breakdown': device_consumption,
            'estimated_cost': round(total_consumption * 0.12, 2),  # 0.12원/W 가정
            'timestamp': datetime.now().isoformat()
        }

    def shutdown(self):
        """시스템 종료"""
        self.running = False

        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

        print("🏠 IoT 시스템 종료됨")


# 전역 IoT 관리자 인스턴스
iot_manager = SorisaeIoTManager()


def test_iot_system():
    """IoT 시스템 테스트"""
    print("\n🏠 소리새 IoT 스마트홈 시스템 테스트")
    print("=" * 60)

    manager = SorisaeIoTManager()

    print("\n1. 📱 등록된 디바이스 목록:")
    devices = manager.get_all_devices()
    for device in devices[:5]:  # 처음 5개만 표시
        print(f"   • {device['name']} ({device['type']}) - {device['location']} - {device['status']}")
    print(f"   ... 총 {len(devices)}개 디바이스")

    print("\n2. 🎛️ 디바이스 제어 테스트:")
    # 거실 조명 제어
    manager.control_device("light_living", {"brightness": 50, "color": "#FFAAAA"})

    # 에어컨 켜기
    manager.control_device("ac_living", {"power": True, "temperature": 23})

    # TV 켜기
    manager.control_device("tv_living", {"power": True, "volume": 20, "channel": 5})

    print("\n3. 📊 센서 데이터 확인:")
    # 잠시 대기하여 센서 데이터 생성
    time.sleep(2)

    temp_data = manager.get_sensor_data("sensor_temp_living", 3)
    for data in temp_data:
        print(f"   • {data['type']}: {data['value']}{data['unit']} ({data['timestamp'][:19]})")

    print("\n4. 🏠 환경 상태:")
    env_status = manager.get_environment_status()
    print(f"   • 온도: {env_status['temperature']:.1f}°C")
    print(f"   • 습도: {env_status['humidity']:.1f}%")
    print(f"   • 조도: {env_status['light_level']:.0f}lux")
    print(f"   • 공기질: {env_status['air_quality']}")

    print("\n5. ⚡ 에너지 소비량:")
    energy = manager.get_energy_consumption()
    print(f"   • 총 소비량: {energy['total_consumption']}W")
    print(f"   • 예상 비용: {energy['estimated_cost']}원/시간")

    print("\n6. 🎬 시나리오 테스트:")
    manager.activate_scene("귀가")
    time.sleep(1)
    manager.activate_scene("영화감상")

    print("\n7. 🤖 자동화 룰 생성:")
    # 동작 감지 시 자동 조명 켜기 룰
    motion_rule = AutomationRule(
        rule_id="auto_light_motion",
        name="동작감지 자동조명",
        trigger_conditions=[{
            "type": "sensor",
            "device_id": "sensor_motion_entrance",
            "sensor_type": "motion",
            "operator": "eq",
            "threshold": True
        }],
        actions=[{
            "type": "device_control",
            "device_id": "light_living",
            "property": "power",
            "value": True
        }]
    )

    manager.create_automation_rule(motion_rule)

    print(f"\n8. 📈 시스템 요약:")
    print(f"   • 등록된 디바이스: {len(manager.devices)}개")
    print(f"   • 자동화 룰: {len(manager.automation_rules)}개")
    print(f"   • MQTT 연결: {'✅' if manager.mqtt_connected else '❌'}")
    print(f"   • 모니터링 상태: {'🟢 활성' if manager.running else '🔴 비활성'}")

    print(f"\n🎉 IoT 시스템 테스트 완료!")

    # 테스트 후 정리
    time.sleep(2)
    manager.shutdown()

    return True



def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 스마트홈 IoT"""
    context = context or {}
    try:
        result = test_iot_system()
        if isinstance(result, dict):
            return {'status': 'ok', **result}
        return {'status': 'ok', 'result': str(result)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

if __name__ == "__main__":
    test_iot_system()
