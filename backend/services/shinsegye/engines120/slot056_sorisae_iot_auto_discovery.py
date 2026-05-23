#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sorisae IoT Auto-Discovery System
소리새 IoT 자동감지 시스템

주파수 스캔을 통한 IoT 기기 자동 탐지 및 음성 안내
"""

import logging
import random
import threading
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List


class IoTProtocol(Enum):
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    ZIGBEE = "zigbee"
    ZWAVE = "zwave"
    THREAD = "thread"
    MATTER = "matter"
    LORA = "lora"
    RF433 = "rf433"
    RF868 = "rf868"
    INFRARED = "infrared"


class FrequencyBand(Enum):
    # WiFi 대역
    WIFI_24GHZ = "2.4GHz"
    WIFI_5GHZ = "5GHz"
    WIFI_6GHZ = "6GHz"

    # Bluetooth
    BLUETOOTH_24GHZ = "2.4GHz-BT"

    # IoT 전용 주파수
    ZIGBEE_24GHZ = "2.4GHz-ZigBee"
    ZWAVE_868MHZ = "868MHz-Z-Wave"
    ZWAVE_908MHZ = "908MHz-Z-Wave"

    # RF 주파수
    RF433MHZ = "433MHz"
    RF868MHZ = "868MHz"
    RF915MHZ = "915MHz"

    # LoRa
    LORA_868MHZ = "868MHz-LoRa"
    LORA_915MHZ = "915MHz-LoRa"


class DetectedDevice:
    """감지된 IoT 기기"""

    def __init__(self, device_id: str, name: str, protocol: IoTProtocol,
                 frequency: FrequencyBand, signal_strength: int):
        self.device_id = device_id
        self.name = name
        self.protocol = protocol
        self.frequency = frequency
        self.signal_strength = signal_strength
        self.detected_time = datetime.now()
        self.brand = self._detect_brand()
        self.device_type = self._detect_device_type()
        self.is_verified = False
        self.mac_address = self._generate_mac_address()

    def _detect_brand(self) -> str:
        """기기 브랜드 추정"""
        brand_patterns = {
            "삼성": ["samsung", "galaxy", "smartthings"],
            "LG": ["lg", "thinq", "webos"],
            "필립스": ["philips", "hue"],
            "샤오미": ["xiaomi", "mi", "yeelight"],
            "TP-Link": ["tplink", "kasa", "tapo"],
            "아마존": ["amazon", "echo", "alexa"],
            "구글": ["google", "nest"],
            "Apple": ["apple", "homekit"]
        }

        name_lower = self.name.lower()
        for brand, patterns in brand_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                return brand

        return "알 수 없음"

    def _detect_device_type(self) -> str:
        """기기 종류 추정"""
        type_patterns = {
            "스마트 조명": ["light", "bulb", "lamp", "조명", "전구"],
            "스마트 플러그": ["plug", "outlet", "socket", "플러그", "콘센트"],
            "스마트 스피커": ["speaker", "echo", "nest", "스피커", "AI"],
            "온도 센서": ["temp", "sensor", "thermo", "온도", "센서"],
            "보안 카메라": ["camera", "cam", "security", "카메라", "보안"],
            "스마트 TV": ["tv", "television", "display", "TV", "텔레비전"],
            "에어컨": ["ac", "airconditioner", "climate", "에어컨", "냉난방"],
            "로봇 청소기": ["vacuum", "robot", "cleaner", "청소기", "로봇"],
            "스마트 도어락": ["lock", "door", "access", "도어락", "잠금"],
            "가습기": ["humidifier", "moisture", "가습기", "습도"]
        }

        name_lower = self.name.lower()
        for device_type, patterns in type_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                return device_type

        return "일반 IoT 기기"

    def _generate_mac_address(self) -> str:
        """MAC 주소 생성"""
        mac = [random.randint(0x00, 0xff) for _ in range(6)]
        return ':'.join(f'{x:02x}' for x in mac)

    def to_dict(self) -> Dict:
        """딕셔너리 형태로 변환"""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "protocol": self.protocol.value,
            "frequency": self.frequency.value,
            "signal_strength": self.signal_strength,
            "detected_time": self.detected_time.isoformat(),
            "brand": self.brand,
            "device_type": self.device_type,
            "mac_address": self.mac_address,
            "is_verified": self.is_verified
        }


class SorisaeIoTAutoDiscovery:
    """소리새 IoT 자동감지 시스템"""

    def __init__(self, iot_manager=None, voice_callback=None):
        self.iot_manager = iot_manager
        self.voice_callback = voice_callback  # TTS 음성 출력 콜백

        # 로깅 설정
        self.logger = logging.getLogger('SorisaeIoTDiscovery')
        self.logger.setLevel(logging.INFO)

        # 감지된 기기 목록
        self.detected_devices: Dict[str, DetectedDevice] = {}
        self.pending_devices: List[DetectedDevice] = []

        # 스캔 설정
        self.is_scanning = False
        self.scan_interval = 5.0  # 5초마다 스캔
        self.scan_thread = None

        # 주파수 스캔 대역
        self.scan_frequencies = [
            FrequencyBand.WIFI_24GHZ,
            FrequencyBand.WIFI_5GHZ,
            FrequencyBand.BLUETOOTH_24GHZ,
            FrequencyBand.ZIGBEE_24GHZ,
            FrequencyBand.ZWAVE_868MHZ,
            FrequencyBand.RF433MHZ,
            FrequencyBand.RF868MHZ
        ]

        # 브랜드별 기기 데이터베이스
        self.device_database = self._load_device_database()

        self.logger.info("📡 소리새 IoT 자동감지 시스템 초기화 완료")

    def _load_device_database(self) -> Dict:
        """기기 데이터베이스 로드"""
        return {
            "삼성": {
                "patterns": ["samsung", "galaxy", "smartthings"],
                "common_devices": ["스마트 TV", "스마트 냉장고", "세탁기", "에어컨"],
                "frequencies": [FrequencyBand.WIFI_24GHZ, FrequencyBand.WIFI_5GHZ, FrequencyBand.ZIGBEE_24GHZ]
            },
            "LG": {
                "patterns": ["lg", "thinq", "webos"],
                "common_devices": ["스마트 TV", "에어컨", "세탁기", "공기청정기"],
                "frequencies": [FrequencyBand.WIFI_24GHZ, FrequencyBand.WIFI_5GHZ]
            },
            "필립스": {
                "patterns": ["philips", "hue"],
                "common_devices": ["스마트 조명", "스마트 전구", "조명 브리지"],
                "frequencies": [FrequencyBand.ZIGBEE_24GHZ, FrequencyBand.WIFI_24GHZ]
            },
            "샤오미": {
                "patterns": ["xiaomi", "mi", "yeelight"],
                "common_devices": ["스마트 조명", "공기청정기", "로봇청소기", "보안카메라"],
                "frequencies": [FrequencyBand.WIFI_24GHZ, FrequencyBand.BLUETOOTH_24GHZ]
            },
            "아마존": {
                "patterns": ["amazon", "echo", "alexa"],
                "common_devices": ["Echo 스피커", "Fire TV", "Ring 도어벨"],
                "frequencies": [FrequencyBand.WIFI_24GHZ, FrequencyBand.WIFI_5GHZ]
            }
        }

    def start_auto_discovery(self) -> str:
        """자동 감지 시작"""
        if self.is_scanning:
            return "이미 IoT 기기 스캔이 진행 중입니다."

        self.is_scanning = True
        self.scan_thread = threading.Thread(target=self._continuous_scan, daemon=True)
        self.scan_thread.start()

        message = "📡 IoT 기기 자동감지를 시작합니다. 주변의 스마트 기기를 찾고 있어요!"
        self._speak(message)
        self.logger.info("IoT 자동감지 시작")

        return message

    def stop_auto_discovery(self) -> str:
        """자동 감지 중지"""
        self.is_scanning = False
        if self.scan_thread:
            self.scan_thread.join(timeout=1.0)

        message = "📡 IoT 기기 자동감지를 중지했습니다."
        self._speak(message)
        self.logger.info("IoT 자동감지 중지")

        return message

    def _continuous_scan(self):
        """지속적인 스캔 실행"""
        while self.is_scanning:
            try:
                self._scan_frequencies()
                time.sleep(self.scan_interval)
            except Exception as e:
                self.logger.error(f"스캔 중 오류: {e}")
                time.sleep(self.scan_interval)

    def _scan_frequencies(self):
        """주파수 스캔 실행"""
        for frequency in self.scan_frequencies:
            if not self.is_scanning:
                break

            # 시뮬레이션: 실제로는 하드웨어 스캔
            detected = self._simulate_frequency_scan(frequency)

            for device in detected:
                if device.device_id not in self.detected_devices:
                    self.detected_devices[device.device_id] = device
                    self.pending_devices.append(device)

                    # 음성으로 새 기기 발견 알림
                    self._announce_new_device(device)

    def _simulate_frequency_scan(self, frequency: FrequencyBand) -> List[DetectedDevice]:
        """주파수 스캔 시뮬레이션"""
        # 10% 확률로 기기 발견
        if random.random() > 0.1:
            return []

        # 랜덤 기기 생성
        device_names = [
            "Samsung SmartThings Hub",
            "LG ThinQ 에어컨",
            "Philips Hue 전구",
            "Xiaomi Mi 공기청정기",
            "TP-Link Kasa 스마트플러그",
            "Amazon Echo Dot",
            "Google Nest Mini",
            "삼성 스마트 TV",
            "LG 스마트 냉장고",
            "샤오미 로봇청소기"
        ]

        # 주파수에 따른 프로토콜 매핑
        protocol_mapping = {
            FrequencyBand.WIFI_24GHZ: IoTProtocol.WIFI,
            FrequencyBand.WIFI_5GHZ: IoTProtocol.WIFI,
            FrequencyBand.BLUETOOTH_24GHZ: IoTProtocol.BLUETOOTH,
            FrequencyBand.ZIGBEE_24GHZ: IoTProtocol.ZIGBEE,
            FrequencyBand.ZWAVE_868MHZ: IoTProtocol.ZWAVE,
            FrequencyBand.RF433MHZ: IoTProtocol.RF433,
            FrequencyBand.RF868MHZ: IoTProtocol.RF868
        }

        detected_devices = []
        device_name = random.choice(device_names)
        device_id = f"auto_discovered_{uuid.uuid4().hex[:8]}"
        protocol = protocol_mapping.get(frequency, IoTProtocol.WIFI)
        signal_strength = random.randint(-80, -30)  # dBm

        device = DetectedDevice(device_id, device_name, protocol, frequency, signal_strength)
        detected_devices.append(device)

        return detected_devices

    def _announce_new_device(self, device: DetectedDevice):
        """새 기기 발견 음성 안내"""
        signal_quality = "강함" if device.signal_strength > -50 else "보통" if device.signal_strength > -70 else "약함"

        message = f"📡 새로운 {device.brand} {device.device_type}를 발견했습니다! "
        message += f"신호 강도: {signal_quality}. 추가하시겠어요?"

        self._speak(message)
        self.logger.info(f"새 기기 발견: {device.name} ({device.frequency.value})")

        # 자동으로 기기 추가 여부 확인 (시뮬레이션)
        self._prompt_add_device(device)

    def _prompt_add_device(self, device: DetectedDevice):
        """기기 추가 여부 확인"""
        # 실제로는 음성 인식으로 사용자 응답을 받음
        # 여기서는 시뮬레이션으로 50% 확률로 추가
        time.sleep(2)  # 사용자 응답 대기 시뮬레이션

        if random.random() > 0.5:
            self.add_device_to_system(device)
        else:
            message = f"📡 {device.name} 추가를 건너뜁니다."
            self._speak(message)

    def add_device_to_system(self, device: DetectedDevice) -> str:
        """시스템에 기기 추가"""
        try:
            device.is_verified = True

            # IoT 매니저에 기기 추가 (실제 구현 시)
            if self.iot_manager:
                # 기기 타입에 따른 매핑
                device_type_mapping = {
                    "스마트 조명": "light",
                    "스마트 플러그": "smart_plug",
                    "온도 센서": "temperature_sensor",
                    "보안 카메라": "security_camera",
                    "스마트 TV": "tv",
                    "에어컨": "air_conditioner"
                }

                # mapped_type = device_type_mapping.get(device.device_type, "generic")
                # self.iot_manager.add_device(device.device_id, device.name, mapped_type)

            message = f"✅ {device.brand} {device.device_type}가 성공적으로 추가되었습니다!"
            self._speak(message)

            # 기기 초기 설정 제안
            self._suggest_initial_setup(device)

            return message

        except Exception as e:
            error_message = f"❌ {device.name} 추가 중 오류가 발생했습니다: {e}"
            self._speak(error_message)
            return error_message

    def _suggest_initial_setup(self, device: DetectedDevice):
        """기기 초기 설정 제안"""
        setup_suggestions = {
            "스마트 조명": "밝기를 50%로 설정하고 따뜻한 색온도로 조정할까요?",
            "스마트 플러그": "전력 모니터링을 활성화하고 스케줄을 설정할까요?",
            "온도 센서": "온도 알림을 25도로 설정할까요?",
            "보안 카메라": "동작 감지 알림을 활성화할까요?",
            "스마트 TV": "음성 제어를 활성화하고 즐겨찾는 채널을 설정할까요?",
            "에어컨": "자동 온도 조절을 24도로 설정할까요?"
        }

        suggestion = setup_suggestions.get(device.device_type)
        if suggestion:
            time.sleep(1)
            self._speak(f"💡 {suggestion}")

    def get_discovery_status(self) -> Dict:
        """자동감지 상태 조회"""
        return {
            "is_scanning": self.is_scanning,
            "total_detected": len(self.detected_devices),
            "pending_devices": len(self.pending_devices),
            "scan_frequencies": [f.value for f in self.scan_frequencies],
            "last_scan": datetime.now().isoformat() if self.is_scanning else None
        }

    def get_detected_devices(self) -> List[Dict]:
        """감지된 기기 목록 조회"""
        return [device.to_dict() for device in self.detected_devices.values()]

    def remove_device(self, device_id: str) -> str:
        """기기 제거"""
        if device_id in self.detected_devices:
            device = self.detected_devices[device_id]
            del self.detected_devices[device_id]

            # pending 목록에서도 제거
            self.pending_devices = [d for d in self.pending_devices if d.device_id != device_id]

            message = f"🗑️ {device.name}을(를) 제거했습니다."
            self._speak(message)
            return message

        return "❌ 해당 기기를 찾을 수 없습니다."

    def scan_specific_frequency(self, frequency: str) -> Dict:
        """특정 주파수 스캔"""
        try:
            # 문자열을 FrequencyBand로 변환
            freq_band = None
            for band in FrequencyBand:
                if band.value == frequency:
                    freq_band = band
                    break

            if not freq_band:
                return {"error": f"지원하지 않는 주파수: {frequency}"}

            detected = self._simulate_frequency_scan(freq_band)

            results = []
            for device in detected:
                if device.device_id not in self.detected_devices:
                    self.detected_devices[device.device_id] = device
                    self.pending_devices.append(device)
                    results.append(device.to_dict())

            return {
                "frequency": frequency,
                "devices_found": len(results),
                "devices": results,
                "scan_time": datetime.now().isoformat()
            }

        except Exception as e:
            return {"error": f"주파수 스캔 오류: {e}"}

    def _speak(self, message: str):
        """음성 출력"""
        if self.voice_callback:
            self.voice_callback(message)
        else:
            print(f"🔊 {message}")


def main(context: dict = None) -> dict:
    """dispatch API용 메인 - IoT 자동 탐지"""
    context = context or {}
    try:
        discovery = SorisaeIoTAutoDiscovery()
        discovery.start_auto_discovery()
        discovery.stop_auto_discovery()
        status = discovery.get_discovery_status()
        return {
            'status': 'ok',
            'scanning': status.get('is_scanning', False),
            'total_detected': status.get('total_detected', 0),
            'pending_devices': status.get('pending_devices', 0),
            'device_database_size': len(discovery.device_database) if hasattr(discovery, 'device_database') else 0,
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


if __name__ == "__main__":
    main()
