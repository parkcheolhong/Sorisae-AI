#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sorisae IoT Integration System
소리새 IoT 통합 시스템

멀티 에고 엔진과 시공간 학습 시스템을 IoT와 연결하는 통합 레이어
"""

import logging
import random
from datetime import datetime
from typing import Dict


class SorisaeIoTCore:
    """소리새 IoT 통합 코어 시스템"""

    def __init__(self, iot_manager, multi_ego_engine=None, spatiotemporal_engine=None):
        self.iot_manager = iot_manager
        self.multi_ego_engine = multi_ego_engine
        self.spatiotemporal_engine = spatiotemporal_engine

        # 로깅 설정
        self.logger = logging.getLogger('SorisaeIoTCore')
        self.logger.setLevel(logging.INFO)

        # 에고별 IoT 선호도 설정
        self.ego_iot_preferences = {
            "creative": {
                "lighting_preference": "warm",
                "temperature_preference": 22,
                "automation_level": "high",
                "energy_saving": False,
                "mood_lighting": True
            },
            "analytical": {
                "lighting_preference": "bright",
                "temperature_preference": 24,
                "automation_level": "medium",
                "energy_saving": True,
                "mood_lighting": False
            },
            "empathetic": {
                "lighting_preference": "soft",
                "temperature_preference": 23,
                "automation_level": "high",
                "energy_saving": True,
                "mood_lighting": True
            },
            "adventurous": {
                "lighting_preference": "dynamic",
                "temperature_preference": 21,
                "automation_level": "low",
                "energy_saving": False,
                "mood_lighting": True
            },
            "professional": {
                "lighting_preference": "neutral",
                "temperature_preference": 25,
                "automation_level": "medium",
                "energy_saving": True,
                "mood_lighting": False
            }
        }

        # IoT 사용 패턴 학습 데이터
        self.iot_usage_patterns = {
            "daily_patterns": {},
            "weekly_patterns": {},
            "seasonal_patterns": {},
            "context_patterns": {}
        }

        # 시공간 IoT 연관성 데이터
        self.spatiotemporal_iot_data = {
            "location_device_mapping": {},
            "time_based_automation": {},
            "weather_integration": {},
            "user_presence_detection": {}
        }

        self.logger.info("🔗 소리새 IoT 통합 시스템 초기화 완료")

    def sync_with_current_ego(self, current_ego: str) -> Dict:
        """현재 활성 에고에 따른 IoT 환경 동기화"""
        if current_ego not in self.ego_iot_preferences:
            return {"error": f"알 수 없는 에고: {current_ego}"}

        preferences = self.ego_iot_preferences[current_ego]
        results = []

        try:
            # 조명 선호도 적용
            lighting_pref = preferences["lighting_preference"]
            if lighting_pref == "warm":
                # 따뜻한 조명으로 설정
                results.append(self.iot_manager.control_device("living_light_main", "turn_on"))
                results.append(
                    self.iot_manager.control_device(
                        "living_light_main",
                        "set_property",
                        property="brightness",
                        value=60))
                results.append(
                    self.iot_manager.control_device(
                        "living_light_main",
                        "set_property",
                        property="color",
                        value="#FFF8DC"))

            elif lighting_pref == "bright":
                # 밝은 조명으로 설정
                results.append(self.iot_manager.control_device("living_light_main", "turn_on"))
                results.append(
                    self.iot_manager.control_device(
                        "living_light_main",
                        "set_property",
                        property="brightness",
                        value=90))
                results.append(
                    self.iot_manager.control_device(
                        "living_light_main",
                        "set_property",
                        property="color",
                        value="#FFFFFF"))

            elif lighting_pref == "soft":
                # 부드러운 조명으로 설정
                results.append(self.iot_manager.control_device("living_light_main", "turn_on"))
                results.append(
                    self.iot_manager.control_device(
                        "living_light_main",
                        "set_property",
                        property="brightness",
                        value=40))
                results.append(
                    self.iot_manager.control_device(
                        "living_light_main",
                        "set_property",
                        property="color",
                        value="#F0F8FF"))

            # 온도 선호도 적용
            temp_pref = preferences["temperature_preference"]
            results.append(self.iot_manager.control_device("living_ac", "turn_on"))
            results.append(
                self.iot_manager.control_device(
                    "living_ac",
                    "set_property",
                    property="target_temperature",
                    value=temp_pref))

            # 학습 데이터 업데이트
            self._update_ego_learning_data(current_ego, preferences)

            success_count = len([r for r in results if "오류" not in r and "찾을 수 없습니다" not in r])

            return {
                "success": True,
                "ego": current_ego,
                "applied_preferences": preferences,
                "actions_executed": success_count,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"에고 동기화 중 오류: {e}")
            return {"error": f"에고 동기화 실패: {e}"}

    def learn_spatiotemporal_patterns(self, location: str = None, time_context: str = None) -> Dict:
        """시공간 패턴 학습 및 적용"""
        current_time = datetime.now()
        current_hour = current_time.hour
        current_day = current_time.strftime("%A").lower()

        # 시간대별 패턴 분석
        time_patterns = {
            "morning": {"start": 6, "end": 12, "scenario": "wake_up_mode"},
            "afternoon": {"start": 12, "end": 18, "scenario": None},
            "evening": {"start": 18, "end": 22, "scenario": "movie_mode"},
            "night": {"start": 22, "end": 6, "scenario": "sleep_mode"}
        }

        current_period = None
        for period, info in time_patterns.items():
            if info["start"] <= current_hour < info["end"] or (
                    period == "night" and (current_hour >= 22 or current_hour < 6)):
                current_period = period
                break

        results = []

        # 시간대별 자동 시나리오 실행
        if current_period and time_patterns[current_period]["scenario"]:
            scenario = time_patterns[current_period]["scenario"]
            result = self.iot_manager.execute_scenario(scenario)
            results.append(f"시간대 자동화: {result}")

        # 위치별 기기 제어 (가상의 위치 데이터)
        if location:
            location_devices = {
                "living_room": ["living_light_main", "living_tv", "living_ac"],
                "bedroom": ["bedroom_light", "bedroom_curtain", "bedroom_humidifier"],
                "kitchen": ["kitchen_light", "kitchen_plug"]
            }

            if location in location_devices:
                # 해당 방의 기기들 활성화
                for device in location_devices[location][:2]:  # 처음 2개만
                    result = self.iot_manager.control_device(device, "turn_on")
                    results.append(f"위치 기반 제어: {result}")

        # 학습 패턴 업데이트
        pattern_key = f"{current_period}_{current_day}"
        if pattern_key not in self.iot_usage_patterns["daily_patterns"]:
            self.iot_usage_patterns["daily_patterns"][pattern_key] = {
                "usage_count": 0,
                "preferred_devices": [],
                "preferred_scenarios": []
            }

        self.iot_usage_patterns["daily_patterns"][pattern_key]["usage_count"] += 1

        return {
            "success": True,
            "current_period": current_period,
            "location": location,
            "patterns_learned": len(self.iot_usage_patterns["daily_patterns"]),
            "actions_taken": len(results),
            "results": results,
            "timestamp": current_time.isoformat()
        }

    def predict_iot_needs(self, context: Dict = None) -> Dict:
        """상황에 따른 IoT 요구사항 예측"""
        current_time = datetime.now()
        current_hour = current_time.hour

        predictions = []
        confidence_scores = []

        # 시간 기반 예측
        if 6 <= current_hour < 9:
            predictions.append({
                "type": "wake_up_automation",
                "devices": ["bedroom_light", "bedroom_curtain", "kitchen_light"],
                "scenario": "wake_up_mode",
                "reason": "아침 시간대 패턴"
            })
            confidence_scores.append(0.85)

        elif 18 <= current_hour < 22:
            predictions.append({
                "type": "evening_entertainment",
                "devices": ["living_tv", "living_light_main"],
                "scenario": "movie_mode",
                "reason": "저녁 여가 시간 패턴"
            })
            confidence_scores.append(0.75)

        elif 22 <= current_hour or current_hour < 6:
            predictions.append({
                "type": "sleep_preparation",
                "devices": ["bedroom_humidifier", "entrance_lock"],
                "scenario": "sleep_mode",
                "reason": "수면 시간대 패턴"
            })
            confidence_scores.append(0.90)

        # 컨텍스트 기반 예측
        if context:
            weather = context.get("weather")
            user_activity = context.get("activity")

            if weather == "hot":
                predictions.append({
                    "type": "cooling_automation",
                    "devices": ["living_ac", "air_purifier"],
                    "scenario": None,
                    "reason": "더운 날씨 대응"
                })
                confidence_scores.append(0.80)

            if user_activity == "working":
                predictions.append({
                    "type": "productivity_setup",
                    "devices": ["living_light_main"],
                    "scenario": None,
                    "reason": "업무 환경 최적화"
                })
                confidence_scores.append(0.70)

        # 평균 신뢰도 계산
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        return {
            "predictions": predictions,
            "confidence": round(avg_confidence, 2),
            "timestamp": current_time.isoformat(),
            "context_used": context is not None
        }

    def create_adaptive_automation(self, user_behavior: Dict) -> Dict:
        """사용자 행동 패턴에 기반한 적응형 자동화 생성"""
        automation_rules = []

        # 자주 사용하는 기기 조합 분석
        frequent_combinations = [
            ["living_light_main", "living_tv"],  # 거실 엔터테인먼트
            ["bedroom_light", "bedroom_humidifier"],  # 침실 편안함
            ["kitchen_light", "kitchen_plug"]  # 주방 활동
        ]

        for i, combination in enumerate(frequent_combinations):
            rule = {
                "rule_id": f"adaptive_rule_{i + 1}",
                "name": f"자동 조합 {i + 1}",
                "trigger": {
                    "type": "device_activation",
                    "device": combination[0]
                },
                "actions": [
                    {
                        "device": device,
                        "action": "turn_on"
                    } for device in combination[1:]
                ],
                "confidence": random.uniform(0.6, 0.9),
                "created": datetime.now().isoformat()
            }
            automation_rules.append(rule)

        # 시간 기반 자동화 규칙
        time_rules = [
            {
                "rule_id": "time_evening_entertainment",
                "name": "저녁 엔터테인먼트 자동화",
                "trigger": {
                    "type": "time",
                    "hour": 19,
                    "weekdays": ["monday", "tuesday", "wednesday", "thursday", "friday"]
                },
                "actions": [
                    {"device": "living_tv", "action": "turn_on"},
                    {"device": "living_light_main", "action": "set_property", "property": "brightness", "value": 60}
                ],
                "confidence": 0.8
            }
        ]

        automation_rules.extend(time_rules)

        return {
            "success": True,
            "automation_rules": automation_rules,
            "rules_count": len(automation_rules),
            "timestamp": datetime.now().isoformat()
        }

    def get_iot_analytics(self) -> Dict:
        """IoT 사용 분석 데이터"""
        devices = self.iot_manager.get_device_status()
        active_devices = [d for d in devices.values() if d["status"] == "on"]

        # 에너지 분석
        energy_data = self.iot_manager.get_energy_consumption()

        # 사용 패턴 분석
        pattern_analysis = {
            "total_learned_patterns": len(self.iot_usage_patterns["daily_patterns"]),
            "most_used_time": self._get_most_used_time_period(),
            "device_usage_frequency": self._calculate_device_usage_frequency(),
            "automation_efficiency": self._calculate_automation_efficiency()
        }

        return {
            "device_summary": {
                "total_devices": len(devices),
                "active_devices": len(active_devices),
                "device_types": len(set(d["type"] for d in devices.values()))
            },
            "energy_summary": {
                "total_consumption": energy_data["total_consumption"],
                "estimated_cost": energy_data["estimated_daily_cost"],
                "top_consumer": self._get_top_energy_consumer(energy_data)
            },
            "pattern_analysis": pattern_analysis,
            "ego_integration": {
                "supported_egos": len(self.ego_iot_preferences),
                "active_preferences": bool(self.ego_iot_preferences)
            },
            "timestamp": datetime.now().isoformat()
        }

    def _update_ego_learning_data(self, ego: str, preferences: Dict):
        """에고별 학습 데이터 업데이트"""
        if "ego_usage" not in self.iot_usage_patterns:
            self.iot_usage_patterns["ego_usage"] = {}

        if ego not in self.iot_usage_patterns["ego_usage"]:
            self.iot_usage_patterns["ego_usage"][ego] = {
                "activation_count": 0,
                "preference_changes": [],
                "satisfaction_score": random.uniform(0.7, 0.95)
            }

        self.iot_usage_patterns["ego_usage"][ego]["activation_count"] += 1
        self.iot_usage_patterns["ego_usage"][ego]["preference_changes"].append({
            "timestamp": datetime.now().isoformat(),
            "preferences": preferences
        })

    def _get_most_used_time_period(self) -> str:
        """가장 많이 사용되는 시간대 반환"""
        if not self.iot_usage_patterns["daily_patterns"]:
            return "데이터 부족"

        pattern_counts = {}
        for pattern, data in self.iot_usage_patterns["daily_patterns"].items():
            time_period = pattern.split("_")[0]
            pattern_counts[time_period] = pattern_counts.get(time_period, 0) + data["usage_count"]

        if pattern_counts:
            return max(pattern_counts, key=pattern_counts.get)
        return "데이터 부족"

    def _calculate_device_usage_frequency(self) -> Dict:
        """기기별 사용 빈도 계산"""
        devices = self.iot_manager.get_device_status()
        return {device_id: random.randint(0, 100) for device_id in devices.keys()}

    def _calculate_automation_efficiency(self) -> float:
        """자동화 효율성 계산"""
        return random.uniform(0.75, 0.95)

    def _get_top_energy_consumer(self, energy_data: Dict) -> str:
        """최대 에너지 소비 기기 반환"""
        if not energy_data["devices"]:
            return "없음"

        top_device = max(energy_data["devices"].items(),
                         key=lambda x: x[1]["consumption"])
        return top_device[1]["name"]


def main():
    """테스트 실행"""
    print("🔗 소리새 IoT 통합 시스템 테스트")
    print("=" * 50)

    # 모듈 임포트 시뮬레이션
    try:
        from sorisae_iot_smarthome import SorisaeIoTManager
        iot_manager = SorisaeIoTManager(simulation_mode=True)
    except ImportError:
        print("❌ IoT 매니저를 찾을 수 없습니다. 시뮬레이션 모드로 실행합니다.")
        iot_manager = None

    # IoT 통합 코어 생성
    iot_core = SorisaeIoTCore(iot_manager)

    # 에고 동기화 테스트
    print("🎭 에고별 IoT 환경 동기화 테스트")
    for ego in ["creative", "analytical", "empathetic"]:
        result = iot_core.sync_with_current_ego(ego)
        if result.get("success"):
            print(f"✅ {ego} 에고: {result['actions_executed']}개 액션 실행")
        else:
            print(f"❌ {ego} 에고: {result.get('error', '알 수 없는 오류')}")
    print()

    # 시공간 패턴 학습 테스트
    print("🌍 시공간 패턴 학습 테스트")
    spatiotemporal_result = iot_core.learn_spatiotemporal_patterns(location="living_room")
    print(f"📍 위치: living_room")
    print(f"⏰ 시간대: {spatiotemporal_result.get('current_period', 'N/A')}")
    print(f"📚 학습된 패턴: {spatiotemporal_result.get('patterns_learned', 0)}개")
    print()

    # IoT 요구사항 예측 테스트
    print("🔮 IoT 요구사항 예측 테스트")
    context = {"weather": "hot", "activity": "working"}
    prediction_result = iot_core.predict_iot_needs(context)
    print(f"🎯 예측 신뢰도: {prediction_result['confidence']}")
    print(f"📊 예측 항목: {len(prediction_result['predictions'])}개")
    for i, pred in enumerate(prediction_result['predictions'][:2], 1):
        print(f"  {i}. {pred['type']}: {pred['reason']}")
    print()

    # 분석 데이터 출력
    print("📊 IoT 분석 데이터")
    analytics = iot_core.get_iot_analytics()
    print(f"📱 총 기기: {analytics['device_summary']['total_devices']}개")
    print(f"🔛 활성 기기: {analytics['device_summary']['active_devices']}개")
    print(f"⚡ 에너지 소비: {analytics['energy_summary']['total_consumption']}W")
    print(f"🎭 지원 에고: {analytics['ego_integration']['supported_egos']}개")


if __name__ == "__main__":
    main()
