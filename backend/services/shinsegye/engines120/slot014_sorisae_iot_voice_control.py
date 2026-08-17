#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sorisae IoT Voice Control System
소리새 IoT 음성 제어 시스템

자연어 음성 명령을 IoT 기기 제어로 변환하는 시스템
"""

import logging
import re
from typing import Optional, Tuple


class SorisaeIoTVoiceControl:
    """소리새 IoT 음성 제어 시스템"""

    def __init__(self, iot_manager):
        self.iot_manager = iot_manager

        # 로깅 설정
        self.logger = logging.getLogger('SorisaeIoTVoice')
        self.logger.setLevel(logging.INFO)

        # 음성 명령 패턴 정의
        self.voice_patterns = {
            # 기기 전원 제어
            "turn_on": [
                r"(.+?)\s*(?:켜|틀어|작동|시작|온)",
                r"(?:켜|틀어|작동|시작|온)\s*(.+?)",
                r"(.+?)\s*(?:을|를)\s*(?:켜|틀어|작동|시작)",
                r"turn\s+on\s+(.+)",
                r"(.+?)\s+on"
            ],
            "turn_off": [
                r"(.+?)\s*(?:꺼|끄|정지|종료|오프)",
                r"(?:꺼|끄|정지|종료|오프)\s*(.+?)",
                r"(.+?)\s*(?:을|를)\s*(?:꺼|끄|정지|종료)",
                r"turn\s+off\s+(.+)",
                r"(.+?)\s+off"
            ],

            # 조명 제어
            "light_control": [
                r"(?:조명|불|빛|라이트|light)\s*(?:밝기|brightness)\s*(\d+)",
                r"(?:조명|불|빛|라이트|light)\s*(?:을|를)?\s*(\d+)(?:%|퍼센트)?(?:로|으로)?\s*(?:조절|설정|맞춰)",
                r"(?:밝기|brightness)\s*(\d+)(?:%|퍼센트)?",
                r"(?:조명|불|빛|라이트|light)\s*(?:색|color|컬러)\s*(.+?)(?:로|으로)?\s*(?:바꿔|변경|설정)"
            ],

            # 온도 제어
            "temperature_control": [
                r"(?:온도|temp|temperature)\s*(\d+)(?:도|℃)?(?:로|으로)?\s*(?:설정|맞춰|조절)",
                r"(?:에어컨|에어콘|airconditioner|AC)\s*(\d+)(?:도|℃)?(?:로|으로)?\s*(?:설정|맞춰|조절)",
                r"(\d+)(?:도|℃)\s*(?:로|으로)?\s*(?:온도|temp|temperature)?\s*(?:설정|맞춰|조절)"
            ],

            # TV 제어
            "tv_control": [
                r"(?:티비|TV|tv|텔레비전)\s*(?:채널|channel)\s*(\d+)(?:번)?(?:으로|로)?\s*(?:바꿔|변경|돌려)",
                r"(?:채널|channel)\s*(\d+)(?:번)?(?:으로|로)?\s*(?:바꿔|변경|돌려)",
                r"(?:티비|TV|tv|텔레비전)\s*(?:볼륨|volume|소리)\s*(\d+)(?:으로|로)?\s*(?:조절|설정|맞춰)"
            ],

            # 시나리오 실행
            "scenario": [
                r"(?:영화|movie|무비)\s*(?:모드|mode|시청|감상)",
                r"(?:수면|잠|sleep|취침)\s*(?:모드|mode)",
                r"(?:기상|일어|wake|모닝|morning)\s*(?:모드|mode)",
                r"(?:외출|나가|away|leaving)\s*(?:모드|mode)",
                r"(?:에너지|energy|절약|절전|save)\s*(?:모드|mode)"
            ],

            # 상태 확인
            "status": [
                r"(?:상태|status|현황|정보)\s*(?:확인|체크|알려줘|보여줘)",
                r"(?:스마트홈|smart\s*home|집|home)\s*(?:상태|status|현황|정보)",
                r"(?:기기|device|디바이스)\s*(?:상태|status|현황|정보)"
            ]
        }

        # 기기 이름 매핑
        self.device_name_mapping = {
            # 조명
            "거실조명": "living_light_main",
            "거실불": "living_light_main",
            "침실조명": "bedroom_light",
            "침실불": "bedroom_light",
            "주방조명": "kitchen_light",
            "주방불": "kitchen_light",
            "조명": "living_light_main",
            "불": "living_light_main",
            "라이트": "living_light_main",
            "light": "living_light_main",

            # TV
            "티비": "living_tv",
            "텔레비전": "living_tv",
            "TV": "living_tv",
            "tv": "living_tv",

            # 에어컨
            "에어컨": "living_ac",
            "에어콘": "living_ac",
            "airconditioner": "living_ac",
            "AC": "living_ac",
            "ac": "living_ac",

            # 기타
            "가습기": "bedroom_humidifier",
            "humidifier": "bedroom_humidifier",
            "커튼": "bedroom_curtain",
            "curtain": "bedroom_curtain",
            "로봇청소기": "robot_vacuum",
            "청소기": "robot_vacuum",
            "vacuum": "robot_vacuum",
            "공기청정기": "air_purifier",
            "정수기": "air_purifier",
            "purifier": "air_purifier"
        }

        # 시나리오 매핑
        self.scenario_mapping = {
            "영화": "movie_mode",
            "movie": "movie_mode",
            "무비": "movie_mode",
            "수면": "sleep_mode",
            "잠": "sleep_mode",
            "sleep": "sleep_mode",
            "취침": "sleep_mode",
            "기상": "wake_up_mode",
            "일어": "wake_up_mode",
            "wake": "wake_up_mode",
            "모닝": "wake_up_mode",
            "morning": "wake_up_mode",
            "외출": "away_mode",
            "나가": "away_mode",
            "away": "away_mode",
            "leaving": "away_mode",
            "에너지": "energy_save_mode",
            "energy": "energy_save_mode",
            "절약": "energy_save_mode",
            "절전": "energy_save_mode",
            "save": "energy_save_mode"
        }

        self.logger.info("🎤 소리새 IoT 음성 제어 시스템 초기화 완료")

    def process_voice_command(self, voice_input: str) -> str:
        """음성 명령 처리"""
        if not voice_input or not voice_input.strip():
            return "음성 명령이 입력되지 않았습니다."

        voice_input = voice_input.strip().lower()
        self.logger.info(f"🎤 음성 명령 수신: {voice_input}")

        # 시나리오 실행 확인
        scenario_result = self._process_scenario_command(voice_input)
        if scenario_result:
            return scenario_result

        # 기기 제어 확인
        device_result = self._process_device_command(voice_input)
        if device_result:
            return device_result

        # 상태 확인 명령
        status_result = self._process_status_command(voice_input)
        if status_result:
            return status_result

        # IoT 관련 명령이 아닌 경우
        return "IoT 명령이 아닙니다."

    def _process_scenario_command(self, voice_input: str) -> Optional[str]:
        """시나리오 실행 명령 처리"""
        for pattern in self.voice_patterns["scenario"]:
            match = re.search(pattern, voice_input)
            if match:
                # 시나리오 키워드 추출
                for keyword, scenario in self.scenario_mapping.items():
                    if keyword in voice_input:
                        result = self.iot_manager.execute_scenario(scenario)
                        return f"🎬 {keyword} 모드 실행: {result}"

        return None

    def _process_device_command(self, voice_input: str) -> Optional[str]:
        """기기 제어 명령 처리"""
        # 전원 제어
        device_id, action = self._extract_device_and_action(voice_input)
        if device_id and action:
            if action == "turn_on":
                result = self.iot_manager.control_device(device_id, "turn_on")
                return f"✅ {result}"
            elif action == "turn_off":
                result = self.iot_manager.control_device(device_id, "turn_off")
                return f"✅ {result}"

        # 조명 제어
        light_result = self._process_light_command(voice_input)
        if light_result:
            return light_result

        # 온도 제어
        temp_result = self._process_temperature_command(voice_input)
        if temp_result:
            return temp_result

        # TV 제어
        tv_result = self._process_tv_command(voice_input)
        if tv_result:
            return tv_result

        return None

    def _extract_device_and_action(self, voice_input: str) -> Tuple[Optional[str], Optional[str]]:
        """음성 입력에서 기기와 액션 추출"""
        # turn_on 패턴 확인
        for pattern in self.voice_patterns["turn_on"]:
            match = re.search(pattern, voice_input)
            if match:
                device_name = match.group(1).strip()
                device_id = self._find_device_id(device_name)
                if device_id:
                    return device_id, "turn_on"

        # turn_off 패턴 확인
        for pattern in self.voice_patterns["turn_off"]:
            match = re.search(pattern, voice_input)
            if match:
                device_name = match.group(1).strip()
                device_id = self._find_device_id(device_name)
                if device_id:
                    return device_id, "turn_off"

        return None, None

    def _find_device_id(self, device_name: str) -> Optional[str]:
        """기기 이름으로 기기 ID 찾기"""
        device_name = device_name.strip().lower()

        # 직접 매핑 확인
        if device_name in self.device_name_mapping:
            return self.device_name_mapping[device_name]

        # 부분 일치 확인
        for name, device_id in self.device_name_mapping.items():
            if device_name in name or name in device_name:
                return device_id

        return None

    def _process_light_command(self, voice_input: str) -> Optional[str]:
        """조명 제어 명령 처리"""
        for pattern in self.voice_patterns["light_control"]:
            match = re.search(pattern, voice_input)
            if match:
                value = match.group(1)

                # 밝기 조절
                if value.isdigit():
                    brightness = int(value)
                    if 0 <= brightness <= 100:
                        # 조명 켜기 (꺼져있는 경우)
                        self.iot_manager.control_device("living_light_main", "turn_on")
                        result = self.iot_manager.control_device("living_light_main", "set_property",
                                                                 property="brightness", value=brightness)
                        return f"💡 조명 밝기 조절: {result}"
                    else:
                        return "❌ 밝기는 0~100 사이의 값이어야 합니다."

                # 색상 변경
                else:
                    color_mapping = {
                        "빨강": "#FF0000", "빨간": "#FF0000", "red": "#FF0000",
                        "파랑": "#0000FF", "파란": "#0000FF", "blue": "#0000FF",
                        "초록": "#00FF00", "녹색": "#00FF00", "green": "#00FF00",
                        "노랑": "#FFFF00", "노란": "#FFFF00", "yellow": "#FFFF00",
                        "흰색": "#FFFFFF", "하얀": "#FFFFFF", "white": "#FFFFFF",
                        "따뜻한": "#FFF8DC", "warm": "#FFF8DC",
                        "차가운": "#F0F8FF", "cool": "#F0F8FF"
                    }

                    color = color_mapping.get(value.strip(), "#FFFFFF")
                    self.iot_manager.control_device("living_light_main", "turn_on")
                    result = self.iot_manager.control_device("living_light_main", "set_property",
                                                             property="color", value=color)
                    return f"🎨 조명 색상 변경: {result}"

        return None

    def _process_temperature_command(self, voice_input: str) -> Optional[str]:
        """온도 제어 명령 처리"""
        for pattern in self.voice_patterns["temperature_control"]:
            match = re.search(pattern, voice_input)
            if match:
                temp_str = match.group(1)
                if temp_str.isdigit():
                    temperature = int(temp_str)
                    if 16 <= temperature <= 30:
                        # 에어컨 켜기 (꺼져있는 경우)
                        self.iot_manager.control_device("living_ac", "turn_on")
                        result = self.iot_manager.control_device("living_ac", "set_property",
                                                                 property="target_temperature", value=temperature)
                        return f"🌡️ 온도 설정: {result}"
                    else:
                        return "❌ 온도는 16~30도 사이의 값이어야 합니다."

        return None

    def _process_tv_command(self, voice_input: str) -> Optional[str]:
        """TV 제어 명령 처리"""
        for pattern in self.voice_patterns["tv_control"]:
            match = re.search(pattern, voice_input)
            if match:
                value_str = match.group(1)
                if value_str.isdigit():
                    value = int(value_str)

                    # 채널 변경
                    if "채널" in voice_input or "channel" in voice_input:
                        if 1 <= value <= 999:
                            self.iot_manager.control_device("living_tv", "turn_on")
                            result = self.iot_manager.control_device("living_tv", "set_property",
                                                                     property="channel", value=value)
                            return f"📺 TV 채널 변경: {result}"
                        else:
                            return "❌ 채널은 1~999 사이의 값이어야 합니다."

                    # 볼륨 조절
                    elif "볼륨" in voice_input or "volume" in voice_input or "소리" in voice_input:
                        if 0 <= value <= 100:
                            self.iot_manager.control_device("living_tv", "turn_on")
                            result = self.iot_manager.control_device("living_tv", "set_property",
                                                                     property="volume", value=value)
                            return f"🔊 TV 볼륨 조절: {result}"
                        else:
                            return "❌ 볼륨은 0~100 사이의 값이어야 합니다."

        return None

    def _process_status_command(self, voice_input: str) -> Optional[str]:
        """상태 확인 명령 처리"""
        for pattern in self.voice_patterns["status"]:
            match = re.search(pattern, voice_input)
            if match:
                devices = self.iot_manager.get_device_status()
                active_devices = [d for d in devices.values() if d["status"] == "on"]

                response = f"📊 스마트홈 현재 상태:\n"
                response += f"✅ 활성 기기: {len(active_devices)}개\n"
                response += f"📱 총 기기: {len(devices)}개\n"

                if active_devices:
                    response += f"🔛 작동중인 기기:\n"
                    for device in active_devices[:5]:  # 최대 5개만 표시
                        response += f"  • {device['name']} ({device['room']})\n"

                    if len(active_devices) > 5:
                        response += f"  ... 외 {len(active_devices) - 5}개"

                # 에너지 정보 추가
                energy = self.iot_manager.get_energy_consumption()
                response += f"\n⚡ 총 에너지 소비: {energy['total_consumption']}W"

                return response

        return None

    def get_voice_commands_help(self) -> str:
        """음성 명령어 도움말"""
        help_text = """🎤 소리새 IoT 음성 명령어 가이드

📱 기기 전원 제어:
  • "거실 조명 켜줘"
  • "TV 꺼줘"
  • "에어컨 작동시켜"

💡 조명 제어:
  • "조명 밝기 80으로 설정"
  • "불 빨간색으로 바꿔줘"
  • "라이트 따뜻한 색으로"

🌡️ 온도 제어:
  • "온도 24도로 맞춰줘"
  • "에어컨 22도로 설정"

📺 TV 제어:
  • "TV 채널 7번으로 바꿔"
  • "볼륨 30으로 조절"

🎬 시나리오 실행:
  • "영화 모드"
  • "수면 모드"
  • "기상 모드"
  • "외출 모드"
  • "에너지 절약 모드"

📊 상태 확인:
  • "스마트홈 상태 알려줘"
  • "기기 현황 보여줘"
"""
        return help_text


def main():
    """테스트 실행"""
    print("🎤 소리새 IoT 음성 제어 시스템 테스트")
    print("=" * 50)

    # 모듈 임포트 시뮬레이션
    try:
        from sorisae_iot_smarthome import SorisaeIoTManager
        iot_manager = SorisaeIoTManager(simulation_mode=True)
    except ImportError:
        print("❌ IoT 매니저를 찾을 수 없습니다.")
        return

    # 음성 제어 시스템 생성
    voice_control = SorisaeIoTVoiceControl(iot_manager)

    # 테스트 명령들
    test_commands = [
        "거실 조명 켜줘",
        "조명 밝기 80으로 설정",
        "온도 24도로 맞춰줘",
        "TV 채널 7번으로 바꿔",
        "영화 모드",
        "스마트홈 상태 알려줘",
        "이것은 IoT 명령이 아닙니다"
    ]

    print("🧪 음성 명령 테스트:")
    for i, command in enumerate(test_commands, 1):
        print(f"\n{i}. 명령: '{command}'")
        response = voice_control.process_voice_command(command)
        print(f"   응답: {response}")

    print("\n" + "=" * 50)
    print("📖 도움말:")
    print(voice_control.get_voice_commands_help())


if __name__ == "__main__":
    main()
