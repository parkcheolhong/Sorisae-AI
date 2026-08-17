#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sorisae Smart Car Control System
소리새 스마트 자동차 제어 시스템

유명 브랜드 자동차의 원격 제어 및 모니터링
"""

import logging
import random
import threading
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class CarBrand(Enum):
    HYUNDAI = "현대"
    KIA = "기아"
    GENESIS = "제네시스"
    BMW = "BMW"
    MERCEDES = "벤츠"
    AUDI = "아우디"
    TESLA = "테슬라"
    VOLKSWAGEN = "폭스바겐"
    TOYOTA = "도요타"
    HONDA = "혼다"
    NISSAN = "닛산"
    FORD = "포드"
    CHEVROLET = "쉐보레"
    LEXUS = "렉서스"
    VOLVO = "볼보"


class CarSystem(Enum):
    ENGINE = "engine"
    DOOR_LOCK = "door_lock"
    WINDOW = "window"
    AIR_CONDITIONING = "air_conditioning"
    HEATING = "heating"
    LIGHTS = "lights"
    HORN = "horn"
    TRUNK = "trunk"
    SUNROOF = "sunroof"
    SEAT = "seat"
    MUSIC = "music"
    NAVIGATION = "navigation"
    SECURITY = "security"
    CHARGING = "charging"  # 전기차용


class CarStatus(Enum):
    PARKED = "주차됨"
    RUNNING = "주행중"
    CHARGING = "충전중"
    MAINTENANCE = "정비중"
    LOCKED = "잠김"
    UNLOCKED = "열림"


class SmartCar:
    """스마트 자동차 클래스"""

    def __init__(self, car_id: str, brand: CarBrand, model: str, year: int,
                 plate_number: str, is_electric: bool = False):
        self.car_id = car_id
        self.brand = brand
        self.model = model
        self.year = year
        self.plate_number = plate_number
        self.is_electric = is_electric

        # 차량 상태
        self.status = CarStatus.PARKED
        self.engine_on = False
        self.doors_locked = True
        self.location = {"lat": 37.5665, "lng": 126.9780}  # 서울 시청
        self.fuel_level = random.uniform(20, 80)  # 연료/배터리 %
        self.mileage = random.randint(10000, 150000)  # 주행거리

        # 시스템 상태
        self.systems = {
            CarSystem.ENGINE: {"status": "off", "temperature": 20},
            CarSystem.DOOR_LOCK: {"status": "locked", "all_doors": True},
            CarSystem.WINDOW: {"front_left": "closed", "front_right": "closed",
                               "rear_left": "closed", "rear_right": "closed"},
            CarSystem.AIR_CONDITIONING: {"status": "off", "temperature": 22, "fan_speed": 0},
            CarSystem.HEATING: {"status": "off", "temperature": 22},
            CarSystem.LIGHTS: {"headlights": "off", "parking_lights": "off", "hazard": "off"},
            CarSystem.HORN: {"status": "off"},
            CarSystem.TRUNK: {"status": "closed"},
            CarSystem.SUNROOF: {"status": "closed", "position": 0},
            CarSystem.SEAT: {"driver_heat": "off", "passenger_heat": "off"},
            CarSystem.MUSIC: {"status": "off", "volume": 15, "source": "radio"},
            CarSystem.NAVIGATION: {"status": "off", "destination": None},
            CarSystem.SECURITY: {"alarm": "armed", "motion_detected": False},
            CarSystem.CHARGING: {"status": "not_charging", "charge_level": 0} if is_electric else None
        }

        # 브랜드별 고유 기능
        self.brand_features = self._get_brand_features()

        # 마지막 업데이트 시간
        self.last_updated = datetime.now()

    def _get_brand_features(self) -> Dict:
        """브랜드별 고유 기능"""
        features = {
            CarBrand.HYUNDAI: {
                "bluelink": True,
                "remote_start": True,
                "remote_climate": True,
                "find_my_car": True,
                "smart_key": True
            },
            CarBrand.KIA: {
                "uvo": True,
                "remote_start": True,
                "remote_climate": True,
                "vehicle_health": True
            },
            CarBrand.GENESIS: {
                "genesis_connected": True,
                "remote_start": True,
                "valet_mode": True,
                "luxury_features": True
            },
            CarBrand.BMW: {
                "bmw_connected": True,
                "remote_services": True,
                "concierge_service": True,
                "smart_key": True
            },
            CarBrand.MERCEDES: {
                "mercedes_me": True,
                "remote_services": True,
                "mbrace": True,
                "luxury_climate": True
            },
            CarBrand.TESLA: {
                "tesla_app": True,
                "summon": True,
                "autopilot": True,
                "supercharger": True,
                "over_air_updates": True
            },
            CarBrand.AUDI: {
                "audi_connect": True,
                "remote_services": True,
                "quattro": True,
                "virtual_cockpit": True
            }
        }

        return features.get(self.brand, {})

    def start_engine(self) -> str:
        """엔진 시동"""
        if self.engine_on:
            return "엔진이 이미 켜져 있습니다."

        if self.is_electric and self.systems[CarSystem.CHARGING]["charge_level"] < 10:
            return "배터리가 부족합니다. 충전이 필요해요."

        if not self.is_electric and self.fuel_level < 5:
            return "연료가 부족합니다. 주유가 필요해요."

        self.engine_on = True
        self.status = CarStatus.RUNNING
        self.systems[CarSystem.ENGINE]["status"] = "on"
        self.systems[CarSystem.ENGINE]["temperature"] = random.randint(80, 95)
        self.last_updated = datetime.now()

        return f"✅ {self.brand.value} {self.model} 엔진 시동 완료!"

    def stop_engine(self) -> str:
        """엔진 정지"""
        if not self.engine_on:
            return "엔진이 이미 꺼져 있습니다."

        self.engine_on = False
        self.status = CarStatus.PARKED
        self.systems[CarSystem.ENGINE]["status"] = "off"
        self.systems[CarSystem.ENGINE]["temperature"] = random.randint(20, 40)
        self.last_updated = datetime.now()

        return f"⏹️ {self.brand.value} {self.model} 엔진 정지 완료!"

    def lock_doors(self) -> str:
        """도어 잠금"""
        if self.doors_locked:
            return "도어가 이미 잠겨 있습니다."

        self.doors_locked = True
        self.systems[CarSystem.DOOR_LOCK]["status"] = "locked"
        self.systems[CarSystem.SECURITY]["alarm"] = "armed"
        self.last_updated = datetime.now()

        return f"🔒 {self.brand.value} {self.model} 도어 잠금 완료!"

    def unlock_doors(self) -> str:
        """도어 잠금 해제"""
        if not self.doors_locked:
            return "도어가 이미 열려 있습니다."

        self.doors_locked = False
        self.systems[CarSystem.DOOR_LOCK]["status"] = "unlocked"
        self.systems[CarSystem.SECURITY]["alarm"] = "disarmed"
        self.last_updated = datetime.now()

        return f"🔓 {self.brand.value} {self.model} 도어 잠금 해제 완료!"

    def control_climate(self, action: str, temperature: int = None) -> str:
        """에어컨/히터 제어"""
        if action == "start_ac":
            self.systems[CarSystem.AIR_CONDITIONING]["status"] = "on"
            if temperature:
                self.systems[CarSystem.AIR_CONDITIONING]["temperature"] = temperature
            self.systems[CarSystem.AIR_CONDITIONING]["fan_speed"] = 3
            return f"❄️ 에어컨 작동 시작 ({self.systems[CarSystem.AIR_CONDITIONING]['temperature']}도)"

        elif action == "start_heat":
            self.systems[CarSystem.HEATING]["status"] = "on"
            if temperature:
                self.systems[CarSystem.HEATING]["temperature"] = temperature
            return f"🔥 히터 작동 시작 ({self.systems[CarSystem.HEATING]['temperature']}도)"

        elif action == "stop":
            self.systems[CarSystem.AIR_CONDITIONING]["status"] = "off"
            self.systems[CarSystem.HEATING]["status"] = "off"
            return "🌡️ 온도 조절 시스템 정지"

        return "잘못된 명령입니다."

    def control_lights(self, light_type: str, action: str) -> str:
        """조명 제어"""
        if light_type == "headlights":
            self.systems[CarSystem.LIGHTS]["headlights"] = action
            return f"💡 전조등 {action}"
        elif light_type == "hazard":
            self.systems[CarSystem.LIGHTS]["hazard"] = action
            return f"⚠️ 비상등 {action}"
        elif light_type == "parking":
            self.systems[CarSystem.LIGHTS]["parking_lights"] = action
            return f"🚨 주차등 {action}"

        return "지원하지 않는 조명입니다."

    def horn_beep(self, duration: int = 1) -> str:
        """경적 울리기"""
        self.systems[CarSystem.HORN]["status"] = "beeping"
        # 실제로는 비동기로 처리
        threading.Timer(duration, lambda: self._reset_horn()).start()
        return f"📯 경적 울림 ({duration}초)"

    def _reset_horn(self):
        """경적 리셋"""
        self.systems[CarSystem.HORN]["status"] = "off"

    def open_trunk(self) -> str:
        """트렁크 열기"""
        if self.systems[CarSystem.TRUNK]["status"] == "open":
            return "트렁크가 이미 열려 있습니다."

        self.systems[CarSystem.TRUNK]["status"] = "open"
        return "🚗 트렁크 열림"

    def close_trunk(self) -> str:
        """트렁크 닫기"""
        if self.systems[CarSystem.TRUNK]["status"] == "closed":
            return "트렁크가 이미 닫혀 있습니다."

        self.systems[CarSystem.TRUNK]["status"] = "closed"
        return "🚗 트렁크 닫힘"

    def find_my_car(self) -> str:
        """차량 찾기"""
        if "find_my_car" not in self.brand_features:
            return "이 차량은 차량 찾기 기능을 지원하지 않습니다."

        # 조명과 경적으로 차량 위치 표시
        self.control_lights("hazard", "on")
        self.horn_beep(3)

        # 3초 후 자동으로 비상등 끄기
        threading.Timer(3, lambda: self.control_lights("hazard", "off")).start()

        return f"📍 차량 위치: 위도 {self.location['lat']:.4f}, 경도 {self.location['lng']:.4f}\n💡 비상등과 경적으로 위치를 표시했습니다!"

    def get_vehicle_status(self) -> Dict:
        """차량 상태 조회"""
        status = {
            "basic_info": {
                "brand": self.brand.value,
                "model": self.model,
                "year": self.year,
                "plate_number": self.plate_number,
                "is_electric": self.is_electric
            },
            "current_status": {
                "status": self.status.value,
                "engine_on": self.engine_on,
                "doors_locked": self.doors_locked,
                "fuel_level": f"{self.fuel_level:.1f}%",
                "mileage": f"{self.mileage:,}km"
            },
            "location": self.location,
            "systems": self.systems,
            "last_updated": self.last_updated.isoformat()
        }

        if self.is_electric:
            status["current_status"]["battery_level"] = f"{self.systems[CarSystem.CHARGING]['charge_level']}%"

        return status


class SorisaeSmartCarControl:
    """소리새 스마트 자동차 제어 시스템"""

    def __init__(self, voice_callback=None):
        self.voice_callback = voice_callback

        # 로깅 설정
        self.logger = logging.getLogger('SorisaeCarControl')
        self.logger.setLevel(logging.INFO)

        # 등록된 차량들
        self.registered_cars: Dict[str, SmartCar] = {}

        # 현재 선택된 차량
        self.current_car_id: Optional[str] = None

        # 음성 명령 패턴
        self.voice_patterns = {
            "engine_start": [
                r"(?:엔진|시동)\s*(?:켜|틀어|작동|시작)",
                r"(?:차|자동차)\s*(?:켜|틀어|시동)",
                r"start\s+engine",
                r"turn\s+on\s+car"
            ],
            "engine_stop": [
                r"(?:엔진|시동)\s*(?:꺼|끄|정지|종료)",
                r"(?:차|자동차)\s*(?:꺼|끄|정지)",
                r"stop\s+engine",
                r"turn\s+off\s+car"
            ],
            "lock_doors": [
                r"(?:문|도어)\s*(?:잠가|잠금|락)",
                r"(?:차|자동차)\s*(?:잠가|잠금)",
                r"lock\s+(?:door|car)",
                r"보안\s*(?:설정|활성화)"
            ],
            "unlock_doors": [
                r"(?:문|도어)\s*(?:열어|잠금해제|언락)",
                r"(?:차|자동차)\s*(?:열어|잠금해제)",
                r"unlock\s+(?:door|car)",
                r"보안\s*(?:해제|비활성화)"
            ],
            "climate_control": [
                r"(?:에어컨|에어콘|AC)\s*(?:켜|틀어|작동)",
                r"(?:히터|난방)\s*(?:켜|틀어|작동)",
                r"온도\s*(\d+)(?:도|℃)?\s*(?:로|으로)?\s*(?:설정|맞춰)",
                r"(?:더위|덥|춥|추위)\s*(?:때문에|해서)?\s*(?:에어컨|히터)"
            ],
            "horn": [
                r"(?:경적|클랙슨|빵빵)\s*(?:울려|눌러|소리)",
                r"horn\s*(?:beep|sound)",
                r"삐\s*빵"
            ],
            "find_car": [
                r"(?:차|자동차)\s*(?:찾아|어디|위치)",
                r"find\s+(?:my\s+)?car",
                r"where\s+is\s+my\s+car"
            ],
            "status": [
                r"(?:차|자동차)\s*(?:상태|현황|정보)",
                r"(?:연료|기름|배터리)\s*(?:상태|레벨|얼마)",
                r"car\s+status",
                r"vehicle\s+info"
            ]
        }

        # 기본 차량 등록 (테스트용)
        self._register_demo_cars()

        self.logger.info("🚗 소리새 스마트 자동차 제어 시스템 초기화 완료")

    def _register_demo_cars(self):
        """데모 차량 등록"""
        demo_cars = [
            {
                "car_id": "hyundai_sonata_2023",
                "brand": CarBrand.HYUNDAI,
                "model": "소나타",
                "year": 2023,
                "plate_number": "12가3456",
                "is_electric": False
            },
            {
                "car_id": "tesla_model3_2023",
                "brand": CarBrand.TESLA,
                "model": "Model 3",
                "year": 2023,
                "plate_number": "78나9012",
                "is_electric": True
            },
            {
                "car_id": "bmw_320i_2022",
                "brand": CarBrand.BMW,
                "model": "320i",
                "year": 2022,
                "plate_number": "34다5678",
                "is_electric": False
            }
        ]

        for car_data in demo_cars:
            car = SmartCar(**car_data)
            self.registered_cars[car.car_id] = car

        # 첫 번째 차량을 기본 선택
        if self.registered_cars:
            self.current_car_id = list(self.registered_cars.keys())[0]

    def process_voice_command(self, voice_input: str) -> str:
        """음성 명령 처리"""
        if not voice_input or not voice_input.strip():
            return "음성 명령이 입력되지 않았습니다."

        voice_input = voice_input.strip().lower()
        self.logger.info(f"🎤 자동차 음성 명령 수신: {voice_input}")

        # 현재 선택된 차량 확인
        if not self.current_car_id or self.current_car_id not in self.registered_cars:
            return "등록된 차량이 없습니다. 먼저 차량을 등록해주세요."

        current_car = self.registered_cars[self.current_car_id]

        # 패턴 매칭으로 명령 분류
        import re

        # 엔진 시동
        for pattern in self.voice_patterns["engine_start"]:
            if re.search(pattern, voice_input):
                result = current_car.start_engine()
                self._speak(result)
                return result

        # 엔진 정지
        for pattern in self.voice_patterns["engine_stop"]:
            if re.search(pattern, voice_input):
                result = current_car.stop_engine()
                self._speak(result)
                return result

        # 도어 잠금
        for pattern in self.voice_patterns["lock_doors"]:
            if re.search(pattern, voice_input):
                result = current_car.lock_doors()
                self._speak(result)
                return result

        # 도어 잠금 해제
        for pattern in self.voice_patterns["unlock_doors"]:
            if re.search(pattern, voice_input):
                result = current_car.unlock_doors()
                self._speak(result)
                return result

        # 에어컨/히터 제어
        for pattern in self.voice_patterns["climate_control"]:
            match = re.search(pattern, voice_input)
            if match:
                if "에어컨" in voice_input or "ac" in voice_input or "더" in voice_input:
                    temp = self._extract_temperature(voice_input) or 22
                    result = current_car.control_climate("start_ac", temp)
                elif "히터" in voice_input or "난방" in voice_input or "추" in voice_input:
                    temp = self._extract_temperature(voice_input) or 25
                    result = current_car.control_climate("start_heat", temp)
                else:
                    result = current_car.control_climate("stop")

                self._speak(result)
                return result

        # 경적
        for pattern in self.voice_patterns["horn"]:
            if re.search(pattern, voice_input):
                result = current_car.horn_beep(2)
                self._speak(result)
                return result

        # 차량 찾기
        for pattern in self.voice_patterns["find_car"]:
            if re.search(pattern, voice_input):
                result = current_car.find_my_car()
                self._speak(result)
                return result

        # 상태 확인
        for pattern in self.voice_patterns["status"]:
            if re.search(pattern, voice_input):
                status = current_car.get_vehicle_status()
                result = self._format_status_message(status)
                self._speak(result)
                return result

        return "자동차 제어 명령을 인식하지 못했습니다."

    def _extract_temperature(self, voice_input: str) -> Optional[int]:
        """음성에서 온도 추출"""
        import re
        match = re.search(r'(\d+)(?:도|℃)', voice_input)
        if match:
            return int(match.group(1))
        return None

    def _format_status_message(self, status: Dict) -> str:
        """상태 정보를 음성 메시지로 포맷"""
        basic = status["basic_info"]
        current = status["current_status"]

        message = f"🚗 {basic['brand']} {basic['model']} 상태 정보:\n"
        message += f"📊 현재 상태: {current['status']}\n"
        message += f"🔑 엔진: {'켜짐' if current['engine_on'] else '꺼짐'}\n"
        message += f"🔒 도어: {'잠김' if current['doors_locked'] else '열림'}\n"

        if basic['is_electric']:
            message += f"🔋 배터리: {current.get('battery_level', 'N/A')}"
        else:
            message += f"⛽ 연료: {current['fuel_level']}"

        message += f"\n📏 주행거리: {current['mileage']}"

        return message

    def register_car(self, brand: str, model: str, year: int, plate_number: str,
                     is_electric: bool = False) -> str:
        """새 차량 등록"""
        try:
            # 브랜드 변환
            car_brand = None
            for brand_enum in CarBrand:
                if brand_enum.value.lower() == brand.lower() or brand.lower() in brand_enum.value.lower():
                    car_brand = brand_enum
                    break

            if not car_brand:
                return f"지원하지 않는 브랜드입니다: {brand}"

            car_id = f"{brand.lower()}_{model.lower()}_{year}_{uuid.uuid4().hex[:6]}"

            new_car = SmartCar(car_id, car_brand, model, year, plate_number, is_electric)
            self.registered_cars[car_id] = new_car

            # 첫 번째 차량이면 기본 선택
            if len(self.registered_cars) == 1:
                self.current_car_id = car_id

            message = f"✅ {brand} {model} ({plate_number}) 등록 완료!"
            self._speak(message)
            return message

        except Exception as e:
            error_message = f"❌ 차량 등록 중 오류: {e}"
            self._speak(error_message)
            return error_message

    def select_car(self, identifier: str) -> str:
        """차량 선택 (번호판 또는 모델명으로)"""
        found_car = None

        for car_id, car in self.registered_cars.items():
            if (identifier in car.plate_number
                or identifier.lower() in car.model.lower()
                    or identifier.lower() in car.brand.value.lower()):
                found_car = car
                self.current_car_id = car_id
                break

        if found_car:
            message = f"🚗 {found_car.brand.value} {found_car.model} 선택됨"
            self._speak(message)
            return message
        else:
            return f"❌ '{identifier}' 차량을 찾을 수 없습니다."

    def get_registered_cars(self) -> List[Dict]:
        """등록된 차량 목록"""
        cars = []
        for car_id, car in self.registered_cars.items():
            basic_info = car.get_vehicle_status()["basic_info"]
            basic_info["car_id"] = car_id
            basic_info["is_current"] = car_id == self.current_car_id
            cars.append(basic_info)

        return cars

    def _speak(self, message: str):
        """음성 출력"""
        if self.voice_callback:
            self.voice_callback(message)
        else:
            print(f"🔊 {message}")

    def get_voice_commands_help(self) -> str:
        """음성 명령어 도움말"""
        help_text = """🚗 소리새 스마트 자동차 음성 명령어 가이드

🔑 엔진 제어:
  • "엔진 켜줘" / "시동 걸어줘"
  • "엔진 꺼줘" / "시동 끄기"

🔒 도어 제어:
  • "문 잠가줘" / "도어 락"
  • "문 열어줘" / "도어 언락"

🌡️ 온도 제어:
  • "에어컨 켜줘"
  • "히터 틀어줘"
  • "온도 24도로 설정"

🔊 기타 제어:
  • "경적 울려줘"
  • "차 찾아줘"
  • "차 상태 알려줘"

🚗 지원 브랜드:
  현대, 기아, 제네시스, BMW, 벤츠, 아우디, 테슬라,
  폭스바겐, 도요타, 혼다, 닛산, 포드, 쉐보레, 렉서스, 볼보
"""
        return help_text


def main(context: dict = None) -> dict:
    """dispatch API용 메인 - 스마트 자동차 제어"""
    context = context or {}
    command = str(context.get('command', '엔진 켜줘'))
    try:
        car_control = SorisaeSmartCarControl()
        registered_cars = car_control.get_registered_cars()
        response = car_control.process_voice_command(command)
        return {
            'status': 'ok',
            'command': command,
            'response': response,
            'registered_cars': len(registered_cars),
            'current_car': next((c for c in registered_cars if c.get('is_current')), None),
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


if __name__ == "__main__":
    main()
