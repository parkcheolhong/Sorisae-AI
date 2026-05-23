#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
소리새 IoT 통합 코어 시스템
Sorisae IoT Integration Core - Multi-Ego + Spatiotemporal + Voice Control
"""

import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

from multi_ego_engine import MultiEgoEngine
from sorisae_iot_smarthome import DeviceType, IoTDevice, SorisaeIoTManager
from spatiotemporal_learning_system import SpatialScale, SpatiotemporalContext, SpatiotemporalLearningEngine, TimeScale

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class SorisaeIoTCore:
    """소리새 IoT 통합 코어"""

    def __init__(self):
        self.iot_manager = SorisaeIoTManager()
        self.multi_ego_engine = MultiEgoEngine()
        self.spatiotemporal_engine = SpatiotemporalLearningEngine()

        # IoT 명령 히스토리
        self.iot_command_history = []

        # 다중 자아와 IoT 연동
        self._initialize_ego_iot_integration()

        # 시공간 학습과 IoT 연동
        self._initialize_spatiotemporal_iot_integration()

        print("🌟 소리새 IoT 통합 코어 초기화 완료!")

    def _initialize_ego_iot_integration(self):
        """자아와 IoT 연동 초기화"""
        # 각 자아에 IoT 선호도 설정
        iot_preferences = {
            "크리에이터": {
                "preferred_devices": ["light", "speaker", "tv"],
                "automation_style": "creative",
                "energy_consciousness": 0.6
            },
            "로직": {
                "preferred_devices": ["sensor", "thermostat", "smart_plug"],
                "automation_style": "efficient",
                "energy_consciousness": 0.9
            },
            "하트": {
                "preferred_devices": ["light", "humidifier", "speaker"],
                "automation_style": "comfort",
                "energy_consciousness": 0.7
            },
            "프랙티컬": {
                "preferred_devices": ["vacuum", "smart_plug", "door_lock"],
                "automation_style": "practical",
                "energy_consciousness": 0.8
            },
            "소셜": {
                "preferred_devices": ["speaker", "tv", "light"],
                "automation_style": "social",
                "energy_consciousness": 0.5
            },
            "애널리스트": {
                "preferred_devices": ["sensor", "camera", "smart_plug"],
                "automation_style": "data_driven",
                "energy_consciousness": 0.9
            },
            "아티스트": {
                "preferred_devices": ["light", "speaker", "window_blind"],
                "automation_style": "aesthetic",
                "energy_consciousness": 0.4
            },
            "테키": {
                "preferred_devices": ["sensor", "camera", "smart_plug"],
                "automation_style": "technical",
                "energy_consciousness": 0.8
            }
        }

        for ego_name, ego in self.multi_ego_engine.egos.items():
            ego.iot_preferences = iot_preferences.get(ego_name, {})

        print("🧠 자아-IoT 연동 완료")

    def _initialize_spatiotemporal_iot_integration(self):
        """시공간 학습과 IoT 연동 초기화"""
        # IoT 이벤트를 시공간 맥락으로 기록
        self.iot_spatiotemporal_mapping = {
            "device_control": "작업",
            "automation_trigger": "자동화",
            "sensor_alert": "환경변화",
            "energy_optimization": "절약",
            "scene_activation": "시나리오"
        }

        print("🌌 시공간-IoT 연동 완료")

    def process_iot_command(self, command: str, user_location: tuple = (0, 0, 0)) -> str:
        """IoT 명령 처리"""
        command = command.lower().strip()

        # 현재 맥락 생성
        current_context = SpatiotemporalContext(
            timestamp=datetime.now(),
            location=user_location,
            time_scale=TimeScale.MINUTE,
            spatial_scale=SpatialScale.ROOM,
            context_tags=self._extract_iot_context_tags(command),
            user_state="active"
        )

        # 맥락 추가
        context_id = self.spatiotemporal_engine.add_spatiotemporal_context(current_context)

        # 명령 기록
        self.iot_command_history.append({
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'context_id': context_id,
            'location': user_location
        })

        # 명령별 처리
        if any(keyword in command for keyword in ["조명", "불", "light", "램프"]):
            return self._handle_lighting_command(command, current_context)

        elif any(keyword in command for keyword in ["에어컨", "aircon", "ac", "온도", "temperature"]):
            return self._handle_climate_command(command, current_context)

        elif any(keyword in command for keyword in ["tv", "텔레비전", "television", "티비"]):
            return self._handle_tv_command(command, current_context)

        elif any(keyword in command for keyword in ["스피커", "speaker", "음악", "music"]):
            return self._handle_speaker_command(command, current_context)

        elif any(keyword in command for keyword in ["청소기", "vacuum", "로봇청소기"]):
            return self._handle_vacuum_command(command, current_context)

        elif any(keyword in command for keyword in ["시나리오", "scene", "모드", "mode"]):
            return self._handle_scene_command(command, current_context)

        elif any(keyword in command for keyword in ["자동화", "automation", "룰", "rule"]):
            return self._handle_automation_command(command, current_context)

        elif any(keyword in command for keyword in ["상태", "status", "확인", "check"]):
            return self._handle_status_command(command, current_context)

        elif any(keyword in command for keyword in ["센서", "sensor", "환경", "environment"]):
            return self._handle_sensor_command(command, current_context)

        elif any(keyword in command for keyword in ["에너지", "energy", "전력", "power", "절약"]):
            return self._handle_energy_command(command, current_context)

        else:
            return self._handle_general_iot_command(command, current_context)

    def _extract_iot_context_tags(self, command: str) -> list:
        """IoT 명령에서 맥락 태그 추출"""
        tag_keywords = {
            "조명제어": ["조명", "불", "light", "램프"],
            "온도조절": ["에어컨", "온도", "temperature", "냉방", "난방"],
            "엔터테인먼트": ["tv", "스피커", "음악", "영화"],
            "청소": ["청소기", "vacuum", "로봇청소기"],
            "보안": ["도어락", "카메라", "센서"],
            "자동화": ["시나리오", "자동화", "룰"],
            "모니터링": ["상태", "센서", "환경", "에너지"]
        }

        extracted_tags = []
        for tag, keywords in tag_keywords.items():
            if any(keyword in command for keyword in keywords):
                extracted_tags.append(tag)

        return extracted_tags or ["일반IoT"]

    def _handle_lighting_command(self, command: str, context: SpatiotemporalContext) -> str:
        """조명 제어 명령 처리"""
        response = "💡 **조명 제어 결과**\n\n"

        # 다중 자아 협업으로 조명 제어 결정
        ego_responses = []

        # 크리에이터 의견
        creator_response = self.multi_ego_engine.get_ego_response("크리에이터", f"조명 제어: {command}")
        ego_responses.append(creator_response)

        # 아티스트 의견 (조명 색상/분위기)
        artist_response = self.multi_ego_engine.get_ego_response("아티스트", f"조명 분위기: {command}")
        ego_responses.append(artist_response)

        # 실제 조명 제어
        if "켜" in command or "on" in command:
            # 거실 조명 켜기
            success = self.iot_manager.control_device("light_living", {
                "power": True,
                "brightness": 80,
                "color": "#FFFFFF"
            })

            if success:
                response += "🟢 거실 조명이 켜졌습니다.\n"

        elif "꺼" in command or "off" in command:
            # 거실 조명 끄기
            success = self.iot_manager.control_device("light_living", {"power": False})

            if success:
                response += "🔴 거실 조명이 꺼졌습니다.\n"

        elif "밝게" in command or "bright" in command:
            # 조명 밝게
            success = self.iot_manager.control_device("light_living", {
                "power": True,
                "brightness": 100
            })

            if success:
                response += "🔆 조명을 최대 밝기로 설정했습니다.\n"

        elif "어둡게" in command or "dim" in command:
            # 조명 어둡게
            success = self.iot_manager.control_device("light_living", {
                "power": True,
                "brightness": 30
            })

            if success:
                response += "🌙 조명을 어둡게 설정했습니다.\n"

        # 자아들의 조명 제어 의견 추가
        response += "\n🧠 **자아들의 조명 의견**:\n"
        for ego_resp in ego_responses:
            response += f"   {ego_resp}\n"

        return response

    def _handle_climate_command(self, command: str, context: SpatiotemporalContext) -> str:
        """온도 조절 명령 처리"""
        response = "🌡️ **온도 조절 결과**\n\n"

        # 로직 자아의 효율적 온도 제어 의견
        logic_response = self.multi_ego_engine.get_ego_response("로직", f"온도 조절: {command}")

        # 하트 자아의 편안함 중심 의견
        heart_response = self.multi_ego_engine.get_ego_response("하트", f"편안한 온도: {command}")

        if "켜" in command or "on" in command:
            success = self.iot_manager.control_device("ac_living", {
                "power": True,
                "temperature": 24,
                "mode": "auto"
            })

            if success:
                response += "❄️ 에어컨이 켜졌습니다 (24°C, 자동모드).\n"

        elif "꺼" in command or "off" in command:
            success = self.iot_manager.control_device("ac_living", {"power": False})

            if success:
                response += "⏹️ 에어컨이 꺼졌습니다.\n"

        elif any(temp in command for temp in ["18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28"]):
            # 온도 설정
            import re
            temp_match = re.search(r'(\d{2})', command)
            if temp_match:
                target_temp = int(temp_match.group(1))
                success = self.iot_manager.control_device("ac_living", {
                    "power": True,
                    "temperature": target_temp
                })

                if success:
                    response += f"🎯 온도를 {target_temp}°C로 설정했습니다.\n"

        # 현재 환경 상태 표시
        env_status = self.iot_manager.get_environment_status()
        response += f"\n📊 **현재 환경**:\n"
        response += f"   • 실내 온도: {env_status['temperature']:.1f}°C\n"
        response += f"   • 습도: {env_status['humidity']:.1f}%\n"

        # 자아 의견 추가
        response += f"\n🧠 **자아 의견**:\n"
        response += f"   {logic_response}\n"
        response += f"   {heart_response}\n"

        return response

    def _handle_tv_command(self, command: str, context: SpatiotemporalContext) -> str:
        """TV 제어 명령 처리"""
        response = "📺 **TV 제어 결과**\n\n"

        # 소셜 자아의 엔터테인먼트 의견
        social_response = self.multi_ego_engine.get_ego_response("소셜", f"TV 시청: {command}")

        if "켜" in command or "on" in command:
            success = self.iot_manager.control_device("tv_living", {
                "power": True,
                "volume": 20,
                "channel": 1
            })

            if success:
                response += "📺 TV가 켜졌습니다 (볼륨: 20, 채널: 1).\n"

                # 영화감상 시나리오도 제안
                response += "\n💡 **추천**: '영화감상' 시나리오를 활성화하시겠어요?\n"

        elif "꺼" in command or "off" in command:
            success = self.iot_manager.control_device("tv_living", {"power": False})

            if success:
                response += "⏹️ TV가 꺼졌습니다.\n"

        elif "볼륨" in command or "volume" in command:
            if "올려" in command or "up" in command:
                success = self.iot_manager.control_device("tv_living", {"volume": 30})
                response += "🔊 볼륨을 올렸습니다.\n"
            elif "내려" in command or "down" in command:
                success = self.iot_manager.control_device("tv_living", {"volume": 10})
                response += "🔉 볼륨을 내렸습니다.\n"

        response += f"\n🧠 **소셜 자아 의견**:\n   {social_response}\n"

        return response

    def _handle_scene_command(self, command: str, context: SpatiotemporalContext) -> str:
        """시나리오 명령 처리"""
        response = "🎬 **시나리오 실행 결과**\n\n"

        # 시나리오 결정을 위한 다중 자아 협의
        collaboration = self.multi_ego_engine.get_ego_collaboration(
            "시나리오 선택",
            ["사용자 경험", "효율성", "편안함"]
        )

        response += f"🤝 **협업 팀**: {', '.join(collaboration['selected_egos'])}\n"
        response += f"📋 **전략**: {collaboration['collaboration_strategy']}\n\n"

        if "외출" in command or "나가" in command:
            success = self.iot_manager.activate_scene("외출")
            if success:
                response += "🚪 '외출' 시나리오가 실행되었습니다.\n"
                response += "   • 모든 조명 OFF\n   • 에어컨 OFF\n   • TV OFF\n"

        elif "귀가" in command or "집" in command:
            success = self.iot_manager.activate_scene("귀가")
            if success:
                response += "🏠 '귀가' 시나리오가 실행되었습니다.\n"
                response += "   • 거실/주방 조명 ON\n   • 에어컨 24°C로 설정\n"

        elif "취침" in command or "잠" in command:
            success = self.iot_manager.activate_scene("취침")
            if success:
                response += "🌙 '취침' 시나리오가 실행되었습니다.\n"
                response += "   • 거실 조명 OFF\n   • 침실 조명 약하게\n   • 에어컨 22°C로 설정\n"

        elif "영화" in command or "movie" in command:
            success = self.iot_manager.activate_scene("영화감상")
            if success:
                response += "🎬 '영화감상' 시나리오가 실행되었습니다.\n"
                response += "   • 조명 20%로 어둡게\n   • TV ON\n   • 스피커 활성화\n"

        return response

    def _handle_status_command(self, command: str, context: SpatiotemporalContext) -> str:
        """상태 확인 명령 처리"""
        response = "📊 **IoT 시스템 상태**\n\n"

        # 애널리스트 자아의 상태 분석
        analyst_response = self.multi_ego_engine.get_ego_response("애널리스트", "IoT 시스템 상태 분석")

        # 디바이스 상태
        devices = self.iot_manager.get_all_devices()
        online_devices = [d for d in devices if d['status'] == 'online']

        response += f"📱 **디바이스 현황**:\n"
        response += f"   • 총 디바이스: {len(devices)}개\n"
        response += f"   • 온라인: {len(online_devices)}개\n"
        response += f"   • 오프라인: {len(devices) - len(online_devices)}개\n\n"

        # 주요 디바이스 상태
        key_devices = ["light_living", "ac_living", "tv_living"]
        response += f"🔧 **주요 디바이스 상태**:\n"

        for device_id in key_devices:
            device_status = self.iot_manager.get_device_status(device_id)
            if device_status:
                power_status = "🟢 ON" if device_status['properties'].get('power', False) else "🔴 OFF"
                response += f"   • {device_status['name']}: {power_status}\n"

        # 환경 상태
        env_status = self.iot_manager.get_environment_status()
        response += f"\n🌡️ **환경 상태**:\n"
        response += f"   • 온도: {env_status['temperature']:.1f}°C\n"
        response += f"   • 습도: {env_status['humidity']:.1f}%\n"
        response += f"   • 조도: {env_status['light_level']:.0f}lux\n"

        # 에너지 사용량
        energy = self.iot_manager.get_energy_consumption()
        response += f"\n⚡ **에너지 사용량**:\n"
        response += f"   • 현재 소비량: {energy['total_consumption']}W\n"
        response += f"   • 예상 비용: {energy['estimated_cost']}원/시간\n"

        response += f"\n🧠 **애널리스트 분석**:\n   {analyst_response}\n"

        return response

    def _handle_energy_command(self, command: str, context: SpatiotemporalContext) -> str:
        """에너지 관리 명령 처리"""
        response = "⚡ **에너지 관리 결과**\n\n"

        # 로직 자아의 에너지 효율 분석
        logic_response = self.multi_ego_engine.get_ego_response("로직", f"에너지 절약: {command}")

        # 프랙티컬 자아의 실용적 조언
        practical_response = self.multi_ego_engine.get_ego_response("프랙티컬", f"에너지 관리: {command}")

        if "절약" in command or "save" in command:
            # 에너지 절약 모드 활성화
            energy_save_actions = [
                ("light_living", {"brightness": 50}),
                ("ac_living", {"temperature": 26}),
                ("tv_living", {"power": False})
            ]

            saved_devices = 0
            for device_id, settings in energy_save_actions:
                if self.iot_manager.control_device(device_id, settings):
                    saved_devices += 1

            response += f"💚 에너지 절약 모드 활성화!\n"
            response += f"   • {saved_devices}개 디바이스 최적화 완료\n"
            response += f"   • 예상 절약량: 15-25% 감소\n\n"

        # 현재 에너지 사용량
        energy = self.iot_manager.get_energy_consumption()
        response += f"📊 **현재 에너지 현황**:\n"
        response += f"   • 총 소비량: {energy['total_consumption']}W\n"
        response += f"   • 시간당 비용: {energy['estimated_cost']}원\n"
        response += f"   • 일일 예상 비용: {energy['estimated_cost'] * 24:.1f}원\n\n"

        # 디바이스별 소비량
        response += f"🔌 **디바이스별 소비량**:\n"
        for device_id, consumption in energy['device_breakdown'].items():
            device_status = self.iot_manager.get_device_status(device_id)
            if device_status and consumption > 0:
                response += f"   • {device_status['name']}: {consumption}W\n"

        response += f"\n🧠 **에너지 전문가 의견**:\n"
        response += f"   {logic_response}\n"
        response += f"   {practical_response}\n"

        return response

    def _handle_general_iot_command(self, command: str, context: SpatiotemporalContext) -> str:
        """일반 IoT 명령 처리"""
        response = "🏠 **IoT 통합 응답**\n\n"

        # 다중 자아 중에서 IoT에 적합한 자아 선택
        suitable_egos = ["프랙티컬", "테키", "로직"]

        ego_responses = []
        for ego_name in suitable_egos:
            ego_response = self.multi_ego_engine.get_ego_response(ego_name, f"IoT 제어: {command}")
            ego_responses.append(ego_response)

        response += "🤖 **스마트홈 AI 어시스턴트가 분석 중입니다...**\n\n"

        # 명령 분석 결과
        response += f"📝 **명령 분석**:\n"
        response += f"   • 명령: {command}\n"
        response += f"   • 시간: {context.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        response += f"   • 위치: {context.location}\n"
        response += f"   • 맥락: {', '.join(context.context_tags)}\n\n"

        # 추천 액션
        response += f"💡 **추천 액션**:\n"
        response += f"   • 'IoT 상태 확인' - 전체 시스템 상태 조회\n"
        response += f"   • '거실 조명 켜줘' - 조명 제어\n"
        response += f"   • '영화감상 모드' - 시나리오 실행\n"
        response += f"   • '에너지 절약' - 전력 관리\n\n"

        # 자아별 조언
        response += f"🧠 **IoT 전문가 조언**:\n"
        for ego_resp in ego_responses:
            response += f"   {ego_resp}\n"

        return response

    def get_iot_learning_insights(self) -> Dict[str, Any]:
        """IoT 학습 인사이트 조회"""
        # 시공간 학습 데이터와 IoT 사용 패턴 분석
        stats = self.spatiotemporal_engine.get_learning_statistics()

        # 최근 IoT 명령 패턴 분석
        recent_commands = self.iot_command_history[-20:] if len(
            self.iot_command_history) > 20 else self.iot_command_history

        command_patterns = {}
        for cmd_record in recent_commands:
            hour = datetime.fromisoformat(cmd_record['timestamp']).hour
            command_type = cmd_record['command'].split()[0] if cmd_record['command'] else 'unknown'

            if hour not in command_patterns:
                command_patterns[hour] = {}

            command_patterns[hour][command_type] = command_patterns[hour].get(command_type, 0) + 1

        return {
            'total_iot_commands': len(self.iot_command_history),
            'recent_patterns': command_patterns,
            'spatiotemporal_stats': stats,
            'most_used_devices': self._get_most_used_devices(),
            'energy_trends': self._analyze_energy_trends(),
            'automation_effectiveness': self._calculate_automation_effectiveness()
        }

    def _get_most_used_devices(self) -> List[Dict[str, Any]]:
        """가장 많이 사용된 디바이스 분석"""
        device_usage = {}

        for device_id, device in self.iot_manager.devices.items():
            usage_count = len(self.iot_manager.device_history.get(device_id, []))
            device_usage[device_id] = {
                'name': device.name,
                'usage_count': usage_count,
                'device_type': device.device_type.value
            }

        return sorted(device_usage.values(), key=lambda x: x['usage_count'], reverse=True)[:5]

    def _analyze_energy_trends(self) -> Dict[str, float]:
        """에너지 사용 트렌드 분석"""
        # 간단한 에너지 트렌드 시뮬레이션
        energy = self.iot_manager.get_energy_consumption()

        return {
            'current_consumption': energy['total_consumption'],
            'daily_average': energy['total_consumption'] * 0.8,  # 시뮬레이션
            'weekly_trend': 5.2,  # % 증가율
            'efficiency_score': 0.78  # 효율성 점수
        }

    def _calculate_automation_effectiveness(self) -> float:
        """자동화 효과성 계산"""
        total_rules = len(self.iot_manager.automation_rules)
        if total_rules == 0:
            return 0.0

        # 간단한 효과성 계산 (실제로는 더 복잡한 분석이 필요)
        return min(1.0, total_rules * 0.2 + 0.5)


# 전역 IoT 통합 코어 인스턴스
sorisae_iot_core = SorisaeIoTCore()


def test_iot_integration():
    """IoT 통합 시스템 테스트"""
    print("🌟 소리새 IoT 통합 시스템 테스트")
    print("=" * 60)

    core = SorisaeIoTCore()

    # 테스트 명령들
    test_commands = [
        ("IoT 상태 확인해줘", (0, 0, 0)),
        ("거실 조명 켜줘", (10, 20, 0)),
        ("에어컨 24도로 설정해줘", (10, 20, 0)),
        ("TV 켜고 볼륨 올려줘", (10, 20, 0)),
        ("영화감상 모드로 해줘", (10, 20, 0)),
        ("에너지 절약 모드 실행해줘", (10, 20, 0)),
        ("모든 조명 꺼줘", (10, 20, 0)),
        ("취침 모드로 변경해줘", (10, 20, 0))
    ]

    for i, (command, location) in enumerate(test_commands, 1):
        print(f"\n🎯 테스트 {i}: '{command}'")
        print("-" * 40)

        response = core.process_iot_command(command, location)
        print(response)

        # 자연스러운 간격
        time.sleep(1)

    # IoT 학습 인사이트 확인
    print(f"\n📊 IoT 학습 인사이트:")
    insights = core.get_iot_learning_insights()
    print(f"   • 총 IoT 명령: {insights['total_iot_commands']}회")
    print(f"   • 자동화 효과성: {insights['automation_effectiveness']:.1%}")
    print(f"   • 에너지 효율성: {insights['energy_trends']['efficiency_score']:.1%}")

    # 가장 많이 사용된 디바이스
    most_used = insights['most_used_devices'][:3]
    print(f"\n🏆 가장 많이 사용된 디바이스:")
    for device in most_used:
        print(f"   • {device['name']}: {device['usage_count']}회")

    print(f"\n🎉 IoT 통합 시스템 테스트 완료!")
    return True


# 별칭 및 호환성을 위한 클래스
SorisaeIoTIntegration = SorisaeIoTCore  # 별칭


class SmartDevice(IoTDevice):
    """스마트 디바이스 기본 클래스"""

    def __init__(self, device_id: str, name: str, device_type: DeviceType):
        super().__init__(device_id, name, device_type)


class SmartSpeaker(SmartDevice):
    """스마트 스피커"""

    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name, DeviceType.SPEAKER)
        self.volume = 50
        self.is_playing = False

    def play(self, content: str = ""):
        """재생"""
        self.is_playing = True
        return {"success": True, "content": content}

    def stop(self):
        """정지"""
        self.is_playing = False
        return {"success": True}

    def set_volume(self, volume: int):
        """볼륨 설정"""
        self.volume = max(0, min(100, volume))
        return {"success": True, "volume": self.volume}


class SmartLight(SmartDevice):
    """스마트 조명"""

    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name, DeviceType.LIGHT)
        self.brightness = 100
        self.color = "#FFFFFF"

    def set_brightness(self, brightness: int):
        """밝기 설정"""
        self.brightness = max(0, min(100, brightness))
        return {"success": True, "brightness": self.brightness}

    def set_color(self, color: str):
        """색상 설정"""
        self.color = color
        return {"success": True, "color": self.color}


class SmartThermostat(SmartDevice):
    """스마트 온도조절기"""

    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name, DeviceType.THERMOSTAT)
        self.target_temperature = 22.0
        self.current_temperature = 20.0
        self.mode = "auto"  # auto, heat, cool, off

    def set_temperature(self, temperature: float):
        """목표 온도 설정"""
        self.target_temperature = max(16.0, min(30.0, temperature))
        return {"success": True, "target": self.target_temperature}

    def set_mode(self, mode: str):
        """모드 설정"""
        if mode in ["auto", "heat", "cool", "off"]:
            self.mode = mode
            return {"success": True, "mode": self.mode}
        return {"success": False, "error": "Invalid mode"}


if __name__ == "__main__":
    test_iot_integration()
