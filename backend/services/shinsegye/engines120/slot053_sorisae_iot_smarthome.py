#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sorisae IoT Smart Home System
소리새 IoT 스마트홈 시스템

완전한 스마트홈 자동화 시스템:
- 13가지 스마트 기기 지원
- MQTT 시뮬레이션 모드
- 시나리오 기반 자동화
- 에너지 모니터링
- 실시간 기기 제어
"""

import json
import logging
import random
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

# MQTT 라이브러리 (시뮬레이션 모드도 지원)
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("📦 MQTT 라이브러리가 없습니다. 시뮬레이션 모드로 실행됩니다.")


class DeviceType(Enum):
    LIGHT = "light"
    TEMPERATURE_SENSOR = "temperature_sensor"
    AIR_CONDITIONER = "air_conditioner"
    TV = "tv"
    SECURITY_CAMERA = "security_camera"
    SMART_LOCK = "smart_lock"
    SMOKE_DETECTOR = "smoke_detector"
    HUMIDIFIER = "humidifier"
    CURTAIN = "curtain"
    SMART_PLUG = "smart_plug"
    ROBOT_VACUUM = "robot_vacuum"
    AIR_PURIFIER = "air_purifier"
    SMART_MIRROR = "smart_mirror"


class IoTDevice:
    """스마트 IoT 기기 클래스"""

    def __init__(self, device_id: str, name: str, device_type: DeviceType, room: str):
        self.device_id = device_id
        self.name = name
        self.device_type = device_type
        self.room = room
        self.status = "off"
        self.properties = {}
        self.last_updated = datetime.now()
        self.energy_consumption = 0.0

        # 기기별 초기 속성 설정
        self._initialize_device_properties()

    def _initialize_device_properties(self):
        """기기별 초기 속성 설정"""
        if self.device_type == DeviceType.LIGHT:
            self.properties = {
                "brightness": 0,
                "color": "#FFFFFF",
                "mode": "normal"
            }
        elif self.device_type == DeviceType.TEMPERATURE_SENSOR:
            self.properties = {
                "temperature": random.uniform(20, 25),
                "humidity": random.uniform(40, 60),
                "battery": random.uniform(80, 100)
            }
        elif self.device_type == DeviceType.AIR_CONDITIONER:
            self.properties = {
                "target_temperature": 24,
                "mode": "auto",
                "fan_speed": "medium"
            }
        elif self.device_type == DeviceType.TV:
            self.properties = {
                "channel": 1,
                "volume": 20,
                "input": "HDMI1"
            }
        elif self.device_type == DeviceType.SECURITY_CAMERA:
            self.properties = {
                "recording": False,
                "motion_detected": False,
                "resolution": "1080p"
            }
        elif self.device_type == DeviceType.SMART_LOCK:
            self.properties = {
                "locked": True,
                "battery": random.uniform(70, 100),
                "last_access": None
            }
        elif self.device_type == DeviceType.SMOKE_DETECTOR:
            self.properties = {
                "smoke_level": 0,
                "battery": random.uniform(85, 100),
                "test_mode": False
            }
        elif self.device_type == DeviceType.HUMIDIFIER:
            self.properties = {
                "humidity_target": 50,
                "water_level": random.uniform(60, 100),
                "mode": "auto"
            }
        elif self.device_type == DeviceType.CURTAIN:
            self.properties = {
                "position": 0,  # 0=closed, 100=open
                "mode": "manual"
            }
        elif self.device_type == DeviceType.SMART_PLUG:
            self.properties = {
                "power_consumption": 0.0,
                "schedule_enabled": False
            }
        elif self.device_type == DeviceType.ROBOT_VACUUM:
            self.properties = {
                "battery": random.uniform(80, 100),
                "cleaning_mode": "auto",
                "status": "docked"
            }
        elif self.device_type == DeviceType.AIR_PURIFIER:
            self.properties = {
                "air_quality": random.uniform(20, 80),
                "filter_life": random.uniform(60, 100),
                "fan_speed": "auto"
            }
        elif self.device_type == DeviceType.SMART_MIRROR:
            self.properties = {
                "display_mode": "clock",
                "brightness": 80,
                "weather_display": True
            }

    def turn_on(self):
        """기기 켜기"""
        self.status = "on"
        self.last_updated = datetime.now()
        self._calculate_energy_consumption()
        return f"{self.name} 켜짐"

    def turn_off(self):
        """기기 끄기"""
        self.status = "off"
        self.last_updated = datetime.now()
        self.energy_consumption = 0.0
        return f"{self.name} 꺼짐"

    def set_property(self, property_name: str, value: Any):
        """기기 속성 설정"""
        if property_name in self.properties:
            self.properties[property_name] = value
            self.last_updated = datetime.now()
            return f"{self.name}의 {property_name}을(를) {value}로 설정"
        return f"{self.name}에서 {property_name} 속성을 찾을 수 없음"

    def _calculate_energy_consumption(self):
        """에너지 소비량 계산"""
        base_consumption = {
            DeviceType.LIGHT: 10,
            DeviceType.AIR_CONDITIONER: 150,
            DeviceType.TV: 80,
            DeviceType.HUMIDIFIER: 30,
            DeviceType.SMART_PLUG: 5,
            DeviceType.ROBOT_VACUUM: 25,
            DeviceType.AIR_PURIFIER: 40,
            DeviceType.SMART_MIRROR: 15
        }

        if self.status == "on" and self.device_type in base_consumption:
            self.energy_consumption = base_consumption[self.device_type] * random.uniform(0.8, 1.2)
        else:
            self.energy_consumption = 0.0

    def get_status(self) -> Dict:
        """기기 상태 정보 반환"""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "type": self.device_type.value,
            "room": self.room,
            "status": self.status,
            "properties": self.properties,
            "energy_consumption": self.energy_consumption,
            "last_updated": self.last_updated.isoformat()
        }


class SorisaeIoTManager:
    """소리새 IoT 스마트홈 관리 시스템"""

    def __init__(self, simulation_mode: bool = True):
        self.simulation_mode = simulation_mode or not MQTT_AVAILABLE
        self.devices: Dict[str, IoTDevice] = {}
        self.automation_rules: List[Dict] = []
        self.scenarios: Dict[str, List[Dict]] = {}
        self.mqtt_client = None

        # 로깅 설정
        self.logger = logging.getLogger('SorisaeIoT')
        self.logger.setLevel(logging.INFO)

        # 기본 기기들 생성
        self._create_default_devices()

        # 시나리오 설정
        self._setup_scenarios()

        # MQTT 클라이언트 초기화 (실제 모드일 때만)
        if not self.simulation_mode:
            self._setup_mqtt()

        self.logger.info(f"🏠 소리새 IoT 시스템 초기화 완료 (모드: {'시뮬레이션' if self.simulation_mode else 'MQTT'})")

    def _create_default_devices(self):
        """기본 스마트 기기들 생성"""
        default_devices = [
            # 거실
            ("living_light_main", "거실 메인 조명", DeviceType.LIGHT, "거실"),
            ("living_tv", "거실 TV", DeviceType.TV, "거실"),
            ("living_ac", "거실 에어컨", DeviceType.AIR_CONDITIONER, "거실"),
            ("living_temp_sensor", "거실 온도센서", DeviceType.TEMPERATURE_SENSOR, "거실"),

            # 침실
            ("bedroom_light", "침실 조명", DeviceType.LIGHT, "침실"),
            ("bedroom_curtain", "침실 커튼", DeviceType.CURTAIN, "침실"),
            ("bedroom_humidifier", "침실 가습기", DeviceType.HUMIDIFIER, "침실"),

            # 주방
            ("kitchen_light", "주방 조명", DeviceType.LIGHT, "주방"),
            ("kitchen_plug", "주방 스마트플러그", DeviceType.SMART_PLUG, "주방"),

            # 현관/보안
            ("entrance_lock", "현관 스마트락", DeviceType.SMART_LOCK, "현관"),
            ("security_camera", "보안카메라", DeviceType.SECURITY_CAMERA, "현관"),
            ("smoke_detector", "연기감지기", DeviceType.SMOKE_DETECTOR, "전체"),

            # 기타
            ("robot_vacuum", "로봇청소기", DeviceType.ROBOT_VACUUM, "전체"),
            ("air_purifier", "공기청정기", DeviceType.AIR_PURIFIER, "거실"),
            ("smart_mirror", "스마트거울", DeviceType.SMART_MIRROR, "화장실")
        ]

        for device_id, name, device_type, room in default_devices:
            device = IoTDevice(device_id, name, device_type, room)
            self.devices[device_id] = device
            self.logger.info(f"📱 기기 생성: {name} ({room})")

    def _setup_scenarios(self):
        """미리 정의된 시나리오들 설정"""
        self.scenarios = {
            "movie_mode": [
                {"device": "living_light_main", "action": "turn_off"},
                {"device": "living_tv", "action": "turn_on"},
                {"device": "living_tv", "action": "set_property", "property": "volume", "value": 25},
                {"device": "living_curtain", "action": "set_property", "property": "position", "value": 0},
                {"device": "living_ac", "action": "set_property", "property": "target_temperature", "value": 22}
            ],
            "sleep_mode": [
                {"device": "living_light_main", "action": "turn_off"},
                {"device": "bedroom_light", "action": "turn_off"},
                {"device": "kitchen_light", "action": "turn_off"},
                {"device": "living_tv", "action": "turn_off"},
                {"device": "entrance_lock", "action": "set_property", "property": "locked", "value": True},
                {"device": "bedroom_humidifier", "action": "turn_on"},
                {"device": "bedroom_curtain", "action": "set_property", "property": "position", "value": 0}
            ],
            "wake_up_mode": [
                {"device": "bedroom_light", "action": "turn_on"},
                {"device": "bedroom_light", "action": "set_property", "property": "brightness", "value": 30},
                {"device": "bedroom_curtain", "action": "set_property", "property": "position", "value": 80},
                {"device": "kitchen_light", "action": "turn_on"},
                {"device": "living_temp_sensor", "action": "turn_on"}
            ],
            "away_mode": [
                {"device": "living_light_main", "action": "turn_off"},
                {"device": "bedroom_light", "action": "turn_off"},
                {"device": "kitchen_light", "action": "turn_off"},
                {"device": "living_tv", "action": "turn_off"},
                {"device": "living_ac", "action": "turn_off"},
                {"device": "entrance_lock", "action": "set_property", "property": "locked", "value": True},
                {"device": "security_camera", "action": "turn_on"},
                {"device": "security_camera", "action": "set_property", "property": "recording", "value": True}
            ],
            "energy_save_mode": [
                {"device": "living_light_main", "action": "set_property", "property": "brightness", "value": 20},
                {"device": "bedroom_light", "action": "set_property", "property": "brightness", "value": 20},
                {"device": "living_ac", "action": "set_property", "property": "target_temperature", "value": 26},
                {"device": "living_tv", "action": "set_property", "property": "volume", "value": 15}
            ]
        }

    def _setup_mqtt(self):
        """MQTT 클라이언트 설정"""
        if not MQTT_AVAILABLE:
            return

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message

        try:
            self.mqtt_client.connect("localhost", 1883, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            self.logger.warning(f"MQTT 연결 실패: {e}. 시뮬레이션 모드로 전환됩니다.")
            self.simulation_mode = True

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT 연결 콜백"""
        if rc == 0:
            self.logger.info("MQTT 브로커에 연결됨")
            # 모든 기기 토픽 구독
            for device_id in self.devices:
                client.subscribe(f"sorisae/iot/{device_id}/+")
        else:
            self.logger.error(f"MQTT 연결 실패: {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT 메시지 수신 콜백"""
        try:
            topic_parts = msg.topic.split('/')
            device_id = topic_parts[2]
            command = topic_parts[3]

            if device_id in self.devices:
                payload = json.loads(msg.payload.decode())
                self._handle_device_command(device_id, command, payload)
        except Exception as e:
            self.logger.error(f"MQTT 메시지 처리 오류: {e}")

    def control_device(self, device_id: str, action: str, **kwargs) -> str:
        """기기 제어"""
        if device_id not in self.devices:
            return f"기기를 찾을 수 없습니다: {device_id}"

        device = self.devices[device_id]

        try:
            if action == "turn_on":
                result = device.turn_on()
            elif action == "turn_off":
                result = device.turn_off()
            elif action == "set_property":
                property_name = kwargs.get("property")
                value = kwargs.get("value")
                if property_name and value is not None:
                    result = device.set_property(property_name, value)
                else:
                    return "속성 이름과 값이 필요합니다"
            else:
                return f"알 수 없는 액션: {action}"

            # MQTT 발행 (실제 모드일 때만)
            if not self.simulation_mode and self.mqtt_client:
                self._publish_device_state(device_id)

            return result

        except Exception as e:
            return f"기기 제어 중 오류: {e}"

    def execute_scenario(self, scenario_name: str) -> str:
        """시나리오 실행"""
        if scenario_name not in self.scenarios:
            available_scenarios = ", ".join(self.scenarios.keys())
            return f"알 수 없는 시나리오: {scenario_name}. 사용가능: {available_scenarios}"

        scenario = self.scenarios[scenario_name]
        results = []

        for command in scenario:
            device_id = command["device"]
            action = command["action"]

            # set_property 액션 처리
            if action == "set_property":
                property_name = command.get("property")
                value = command.get("value")
                result = self.control_device(device_id, action, property=property_name, value=value)
            else:
                result = self.control_device(device_id, action)

            results.append(result)
            time.sleep(0.1)  # 기기 간 딜레이

        executed_actions = len([r for r in results if "오류" not in r and "찾을 수 없습니다" not in r])
        return f"시나리오 '{scenario_name}' 실행 완료! {executed_actions}개 액션 수행됨"

    def get_device_status(self, device_id: str = None) -> Dict:
        """기기 상태 조회"""
        if device_id:
            if device_id in self.devices:
                return self.devices[device_id].get_status()
            else:
                return {"error": f"기기를 찾을 수 없습니다: {device_id}"}
        else:
            # 모든 기기 상태 반환
            return {device_id: device.get_status() for device_id, device in self.devices.items()}

    def get_room_devices(self, room: str) -> List[Dict]:
        """특정 방의 기기들 조회"""
        room_devices = []
        for device in self.devices.values():
            if device.room == room:
                room_devices.append(device.get_status())
        return room_devices

    def get_energy_consumption(self) -> Dict:
        """전체 에너지 소비량 조회"""
        total_consumption = 0
        device_consumption = {}

        for device_id, device in self.devices.items():
            consumption = device.energy_consumption
            device_consumption[device_id] = {
                "name": device.name,
                "consumption": consumption,
                "status": device.status
            }
            total_consumption += consumption

        return {
            "total_consumption": round(total_consumption, 2),
            "devices": device_consumption,
            "estimated_daily_cost": round(total_consumption * 24 * 0.1, 2)  # 가정된 요율
        }

    def add_automation_rule(self, rule_name: str, trigger: Dict, actions: List[Dict]):
        """자동화 규칙 추가"""
        rule = {
            "name": rule_name,
            "trigger": trigger,
            "actions": actions,
            "enabled": True,
            "created": datetime.now().isoformat()
        }
        self.automation_rules.append(rule)
        return f"자동화 규칙 '{rule_name}' 추가됨"

    def _publish_device_state(self, device_id: str):
        """MQTT로 기기 상태 발행"""
        if self.mqtt_client and device_id in self.devices:
            device = self.devices[device_id]
            state = device.get_status()
            topic = f"sorisae/iot/{device_id}/state"
            self.mqtt_client.publish(topic, json.dumps(state))

    def get_system_info(self) -> Dict:
        """시스템 정보 조회"""
        active_devices = len([d for d in self.devices.values() if d.status == "on"])
        total_energy = sum(d.energy_consumption for d in self.devices.values())

        return {
            "total_devices": len(self.devices),
            "active_devices": active_devices,
            "simulation_mode": self.simulation_mode,
            "total_energy_consumption": round(total_energy, 2),
            "automation_rules": len(self.automation_rules),
            "available_scenarios": list(self.scenarios.keys())
        }


def main():
    """테스트 실행"""
    print("🏠 소리새 IoT 스마트홈 시스템 테스트")
    print("=" * 50)

    # IoT 매니저 생성
    iot = SorisaeIoTManager(simulation_mode=True)

    # 시스템 정보 출력
    info = iot.get_system_info()
    print(f"📱 총 기기 수: {info['total_devices']}")
    print(f"🔛 활성 기기: {info['active_devices']}")
    print(f"⚡ 총 에너지 소비: {info['total_energy_consumption']}W")
    print(f"🎯 시나리오 수: {len(info['available_scenarios'])}")
    print()

    # 시나리오 테스트
    print("🎬 영화 시청 모드 실행...")
    result = iot.execute_scenario("movie_mode")
    print(result)
    print()

    # 기기 상태 확인
    print("📊 기기 상태:")
    devices = iot.get_device_status()
    for device_id, status in devices.items():
        if status['status'] == 'on':
            print(f"✅ {status['name']} ({status['room']}) - {status['status']}")
    print()

    # 에너지 소비량 확인
    energy = iot.get_energy_consumption()
    print(f"⚡ 총 에너지 소비: {energy['total_consumption']}W")
    print(f"💰 예상 일일 전기요금: {energy['estimated_daily_cost']}원")


if __name__ == "__main__":
    main()
