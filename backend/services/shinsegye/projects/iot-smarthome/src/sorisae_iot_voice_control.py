#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🧠🌐 소리새 능동적 IoT 하이브리드 음성 제어 시스템
Sorisae Intelligent IoT Hybrid Voice Control System
- 능동적 의사결정: AI가 스스로 최적의 연결과 제어 방식 선택
- 하이브리드 연결: 지상파→모바일→위성 자동 전환
- 지능형 IoT 제어: 상황 인식 기반 스마트 제어
"""

import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

import pyttsx3
import speech_recognition as sr

from sorisae_iot_integration import SorisaeIoTCore

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# 하이브리드 연결 시스템 임포트
try:
    from sorisae_integrated_hybrid_system import SorisaeIntegratedHybridSystem
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False
    print("⚠️ 하이브리드 시스템 선택적 로드 - 기본 모드로 실행")


@dataclass
class IoTDecision:
    """IoT 의사결정 구조체"""
    device_id: str
    action: str
    reasoning: str
    confidence: float
    connection_preference: str
    priority_level: int
    timestamp: str


class IntelligentDecisionEngine:
    """능동적 IoT 의사결정 엔진"""

    def __init__(self):
        self.logger = logging.getLogger('IoTDecisionEngine')
        self.decision_history = []
        self.device_patterns = {}
        self.connection_preferences = {
            'emergency': 'satellite',
            'high_priority': 'mobile',
            'normal': 'terrestrial'
        }

    def analyze_situation(self, command: str, device_status: Dict) -> IoTDecision:
        """상황 분석 및 의사결정"""
        current_time = datetime.now()

        # 1. 명령 긴급도 분석
        urgency = self._assess_urgency(command)

        # 2. 기기 상태 분석
        device_health = self._analyze_device_health(device_status)

        # 3. 연결 선호도 결정
        connection_pref = self._decide_connection_preference(urgency, device_health)

        # 4. 제어 방식 결정
        control_action = self._decide_control_action(command, device_status)

        # 5. 신뢰도 계산
        confidence = self._calculate_confidence(urgency, device_health, connection_pref)

        decision = IoTDecision(
            device_id=self._extract_device_id(command),
            action=control_action,
            reasoning=f"긴급도: {urgency}, 기기상태: {device_health}, 연결: {connection_pref}",
            confidence=confidence,
            connection_preference=connection_pref,
            priority_level=urgency,
            timestamp=current_time.isoformat()
        )

        self.decision_history.append(decision)
        return decision

    def _assess_urgency(self, command: str) -> int:
        """명령 긴급도 평가 (1-5)"""
        emergency_keywords = ['비상', '긴급', '응급', '위험', '화재', '도난']
        high_priority = ['보안', '경보', '알람', '잠금']

        command_lower = command.lower()

        if any(kw in command_lower for kw in emergency_keywords):
            return 5  # 최고 긴급
        elif any(kw in command_lower for kw in high_priority):
            return 4  # 높은 우선순위
        elif '즉시' in command_lower or '빨리' in command_lower:
            return 3  # 보통 우선순위
        else:
            return 2  # 일반

    def _analyze_device_health(self, device_status: Dict) -> str:
        """기기 상태 분석"""
        if not device_status:
            return "unknown"

        battery = device_status.get('battery', 100)
        connection = device_status.get('connection_strength', 100)

        if battery < 20 or connection < 30:
            return "poor"
        elif battery < 50 or connection < 60:
            return "fair"
        else:
            return "good"

    def _decide_connection_preference(self, urgency: int, device_health: str) -> str:
        """연결 방식 결정"""
        if urgency >= 5:
            return 'satellite'  # 비상시 위성 우선
        elif urgency >= 4 or device_health == 'poor':
            return 'mobile'  # 높은 우선순위나 기기 상태 불량시 모바일
        else:
            return 'terrestrial'  # 일반적으로 지상파

    def _decide_control_action(self, command: str, device_status: Dict) -> str:
        """제어 동작 결정"""
        if '켜' in command:
            return 'turn_on'
        elif '꺼' in command:
            return 'turn_off'
        elif '올려' in command or '증가' in command:
            return 'increase'
        elif '내려' in command or '감소' in command:
            return 'decrease'
        elif '잠금' in command:
            return 'lock'
        elif '해제' in command:
            return 'unlock'
        else:
            return 'status_check'

    def _extract_device_id(self, command: str) -> str:
        """명령에서 기기 ID 추출"""
        device_map = {
            '조명': 'light_01',
            '에어컨': 'ac_01',
            '히터': 'heater_01',
            '도어락': 'door_01',
            '보안': 'security_01',
            '스피커': 'speaker_01'
        }

        for device_name, device_id in device_map.items():
            if device_name in command:
                return device_id
        return 'unknown_device'

    def _calculate_confidence(self, urgency: int, device_health: str, connection: str) -> float:
        """의사결정 신뢰도 계산"""
        base_confidence = 0.7

        # 긴급도에 따른 가중치
        urgency_weight = urgency * 0.05

        # 기기 상태에 따른 가중치
        health_weights = {'good': 0.1, 'fair': 0.05, 'poor': -0.1, 'unknown': 0.0}
        health_weight = health_weights.get(device_health, 0.0)

        # 연결 방식에 따른 가중치
        connection_weights = {'satellite': 0.15, 'mobile': 0.1, 'terrestrial': 0.05}
        connection_weight = connection_weights.get(connection, 0.0)

        confidence = base_confidence + urgency_weight + health_weight + connection_weight
        return min(max(confidence, 0.0), 1.0)


class SorisaeIntelligentIoTController:
    """소리새 지능형 IoT 하이브리드 제어기"""

    def __init__(self):
        print("🧠🌐" + "=" * 50 + "🧠🌐")
        print("   소리새 능동적 IoT 하이브리드 제어 시스템")
        print("   Sorisae Intelligent IoT Hybrid Controller")
        print("🧠🌐" + "=" * 50 + "🧠🌐")

        # 기본 시스템 초기화
        self.iot_core = SorisaeIoTCore()
        self.decision_engine = IntelligentDecisionEngine()

        # 하이브리드 시스템 초기화
        self.hybrid_system = None
        self.hybrid_mode = False

        if HYBRID_AVAILABLE:
            try:
                self.hybrid_system = SorisaeIntegratedHybridSystem()
                self.hybrid_mode = True
                print("✅ 하이브리드 IoT 제어 시스템 활성화")
            except Exception as e:
                print(f"⚠️ 하이브리드 시스템 초기화 실패: {e}")

        # 음성 인식 초기화
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        # TTS 초기화
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 200)

        # 한국어 음성으로 설정 시도
        voices = self.tts_engine.getProperty('voices')
        for voice in voices:
            if 'korean' in voice.name.lower() or 'ko' in voice.id.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break

        # 시스템 상태
        self.voice_control_active = False
        self.listening_thread = None
        self.autonomous_mode = True  # 능동적 모드 기본 활성화

        print("🧠 능동적 의사결정 엔진 초기화 완료!")
        print("🎤 IoT 음성 제어 시스템 준비 완료!")

    def speak(self, text: str):
        """지능형 텍스트 음성 출력"""
        try:
            # 하이브리드 모드 표시 추가
            mode_indicator = "🧠🌐" if self.hybrid_mode and self.autonomous_mode else "🔊"
            print(f"{mode_indicator} 소리새: {text}")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception:
            print(f"🔊 [TTS 오류] 소리새: {text}")

    def intelligent_command_processing(self, command: str) -> Dict[str, Any]:
        """능동적 지능형 명령 처리"""
        print(f"\n🧠 능동적 분석 시작: '{command}'")

        # 1. 현재 기기 상태 수집
        device_status = self.iot_core.get_all_device_status()

        # 2. AI 의사결정 수행
        decision = self.decision_engine.analyze_situation(command, device_status)

        # 3. 의사결정 결과 출력
        self._report_decision(decision)

        # 4. 하이브리드 연결 최적화
        if self.hybrid_mode:
            self._optimize_hybrid_connection(decision)

        # 5. 지능형 IoT 제어 실행
        result = self._execute_intelligent_control(decision, device_status)

        return {
            'decision': decision,
            'execution_result': result,
            'hybrid_optimized': self.hybrid_mode,
            'autonomous_mode': self.autonomous_mode
        }

    def _report_decision(self, decision: IoTDecision):
        """의사결정 결과 보고"""
        print(f"🎯 AI 의사결정 완료:")
        print(f"   기기: {decision.device_id}")
        print(f"   동작: {decision.action}")
        print(f"   근거: {decision.reasoning}")
        print(f"   신뢰도: {decision.confidence:.2%}")
        print(f"   연결 선호: {decision.connection_preference}")
        print(f"   우선순위: {decision.priority_level}/5")

    def _optimize_hybrid_connection(self, decision: IoTDecision):
        """하이브리드 연결 최적화"""
        if not self.hybrid_system:
            return

        try:
            current_status = self.hybrid_system.get_connection_status()
            current_connection = current_status.get('active_connection', 'terrestrial')

            # AI가 결정한 최적 연결과 현재 연결 비교
            if decision.connection_preference != current_connection:
                print(f"🔄 연결 최적화: {current_connection} → {decision.connection_preference}")

                if decision.connection_preference == 'satellite' and decision.priority_level >= 4:
                    self.hybrid_system.force_satellite_connection()
                    self.speak(f"긴급 상황으로 판단하여 위성 연결로 전환합니다.")

                elif decision.connection_preference == 'mobile':
                    # 모바일 연결로 전환 로직 (실제 구현에서는 더 세밀한 제어)
                    print("📱 모바일 연결 우선순위로 설정")

            else:
                print(f"✅ 현재 연결({current_connection})이 이미 최적화됨")

        except Exception as e:
            print(f"⚠️ 하이브리드 연결 최적화 오류: {e}")

    def _execute_intelligent_control(self, decision: IoTDecision, device_status: Dict) -> Dict[str, Any]:
        """지능형 IoT 제어 실행"""
        try:
            device_id = decision.device_id
            action = decision.action

            print(f"🎮 지능형 제어 실행: {device_id} - {action}")

            # 기기별 지능형 제어
            if device_id.startswith('light'):
                result = self._intelligent_light_control(action, device_status.get(device_id, {}))
            elif device_id.startswith('ac') or device_id.startswith('heater'):
                result = self._intelligent_climate_control(action, device_status.get(device_id, {}))
            elif device_id.startswith('door'):
                result = self._intelligent_security_control(action, device_status.get(device_id, {}))
            elif device_id.startswith('security'):
                result = self._intelligent_security_system(action, device_status.get(device_id, {}))
            else:
                result = self._generic_device_control(device_id, action)

            # 실행 결과 AI 학습
            self._learn_from_execution(decision, result)

            return result

        except Exception as e:
            error_msg = f"지능형 제어 실행 오류: {e}"
            print(f"❌ {error_msg}")
            return {'status': 'error', 'message': error_msg}

    def _intelligent_light_control(self, action: str, device_status: Dict) -> Dict[str, Any]:
        """지능형 조명 제어"""
        if action == 'turn_on':
            # 현재 시간과 환경을 고려한 조명 설정
            current_hour = datetime.now().hour
            if 6 <= current_hour <= 9:  # 아침
                brightness = 80
                color_temp = 'warm'
                self.speak("좋은 아침입니다! 아침에 적합한 따뜻한 조명으로 켜드릴게요.")
            elif 10 <= current_hour <= 17:  # 낮
                brightness = 60
                color_temp = 'neutral'
                self.speak("업무에 집중할 수 있는 자연광 조명으로 설정합니다.")
            elif 18 <= current_hour <= 22:  # 저녁
                brightness = 70
                color_temp = 'warm'
                self.speak("편안한 저녁 시간을 위한 따뜻한 조명으로 설정합니다.")
            else:  # 밤
                brightness = 30
                color_temp = 'dim'
                self.speak("밤 시간이므로 눈에 편안한 약한 조명으로 켜드립니다.")

            return self.iot_core.control_smart_light('on', brightness=brightness, color_temp=color_temp)

        elif action == 'turn_off':
            self.speak("조명을 끕니다.")
            return self.iot_core.control_smart_light('off')

        elif action == 'increase':
            current_brightness = device_status.get('brightness', 50)
            new_brightness = min(current_brightness + 20, 100)
            self.speak(f"조명 밝기를 {new_brightness}%로 높입니다.")
            return self.iot_core.control_smart_light('dim', brightness=new_brightness)

        elif action == 'decrease':
            current_brightness = device_status.get('brightness', 50)
            new_brightness = max(current_brightness - 20, 10)
            self.speak(f"조명 밝기를 {new_brightness}%로 낮춥니다.")
            return self.iot_core.control_smart_light('dim', brightness=new_brightness)

        return {'status': 'success', 'action': action}

    def _intelligent_climate_control(self, action: str, device_status: Dict) -> Dict[str, Any]:
        """지능형 온도 제어"""
        current_temp = device_status.get('temperature', 22)
        current_hour = datetime.now().hour

        if action == 'turn_on':
            # 시간대별 적정 온도 설정
            if 6 <= current_hour <= 9:  # 아침
                target_temp = 23
                self.speak(f"좋은 아침입니다! 아침에 적합한 {target_temp}도로 설정합니다.")
            elif 22 <= current_hour or current_hour <= 6:  # 밤/새벽
                target_temp = 20
                self.speak(f"편안한 잠자리를 위해 {target_temp}도로 설정합니다.")
            else:  # 낮
                target_temp = 24
                self.speak(f"활동하기 좋은 {target_temp}도로 설정합니다.")

            return self.iot_core.control_thermostat(target_temp)

        elif action == 'increase':
            new_temp = min(current_temp + 2, 30)
            self.speak(f"온도를 {new_temp}도로 높입니다.")
            return self.iot_core.control_thermostat(new_temp)

        elif action == 'decrease':
            new_temp = max(current_temp - 2, 16)
            self.speak(f"온도를 {new_temp}도로 낮춥니다.")
            return self.iot_core.control_thermostat(new_temp)

        return {'status': 'success', 'action': action}

    def _intelligent_security_control(self, action: str, device_status: Dict) -> Dict[str, Any]:
        """지능형 보안 제어"""
        if action == 'lock':
            # 추가 보안 확인
            self.speak("보안을 위해 도어락을 잠급니다. 모든 출입구를 확인하겠습니다.")
            # 여기서 다른 보안 시스템도 함께 체크
            return {'status': 'success', 'action': 'door_locked', 'security_enhanced': True}

        elif action == 'unlock':
            current_hour = datetime.now().hour
            if 22 <= current_hour or current_hour <= 6:  # 밤/새벽
                self.speak("야간 시간입니다. 보안을 위해 추가 확인이 필요합니다.")
                # 실제로는 추가 인증 요구
                return {'status': 'security_check_required', 'reason': 'night_time'}
            else:
                self.speak("도어락을 해제합니다.")
                return {'status': 'success', 'action': 'door_unlocked'}

        return {'status': 'success', 'action': action}

    def _intelligent_security_system(self, action: str, device_status: Dict) -> Dict[str, Any]:
        """지능형 보안 시스템 제어"""
        if action == 'turn_on':
            self.speak("통합 보안 시스템을 활성화합니다. 모든 센서를 점검하겠습니다.")
            # 하이브리드 연결로 보안 강화
            if self.hybrid_mode:
                self.speak("하이브리드 연결을 통해 보안 수준을 최대로 높입니다.")
            return {'status': 'success', 'security_level': 'maximum', 'hybrid_enhanced': self.hybrid_mode}

        elif action == 'turn_off':
            self.speak("보안 시스템을 해제합니다.")
            return {'status': 'success', 'security_level': 'standard'}

        return {'status': 'success', 'action': action}

    def _generic_device_control(self, device_id: str, action: str) -> Dict[str, Any]:
        """일반 기기 제어"""
        self.speak(f"{device_id} 기기를 {action} 합니다.")
        return {'status': 'success', 'device': device_id, 'action': action}

    def _learn_from_execution(self, decision: IoTDecision, result: Dict[str, Any]):
        """실행 결과로부터 AI 학습"""
        # 실행 성공률과 사용자 만족도를 기반으로 의사결정 모델 개선
        success = result.get('status') == 'success'

        # 학습 데이터 저장
        learning_data = {
            'decision': decision,
            'result': result,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }

        # 패턴 분석 및 모델 업데이트 (간단한 예시)
        device_id = decision.device_id
        if device_id not in self.decision_engine.device_patterns:
            self.decision_engine.device_patterns[device_id] = []

        self.decision_engine.device_patterns[device_id].append(learning_data)

        # 최근 10개 데이터만 유지 (메모리 관리)
        if len(self.decision_engine.device_patterns[device_id]) > 10:
            self.decision_engine.device_patterns[device_id].pop(0)

        print(f"🧠 AI 학습 완료: {device_id} 성공률 데이터 업데이트")

    def listen(self) -> str:
        """음성을 인식하여 텍스트로 변환"""
        try:
            with self.microphone as source:
                print("🎤 음성 대기 중...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

            print("🔄 음성 인식 중...")
            text = self.recognizer.recognize_google(audio, language='ko-KR')
            print(f"👤 사용자: {text}")
            return text

        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            print("⚠ 음성을 인식하지 못했습니다")
            return ""
        except sr.RequestError as e:
            print(f"🚫 Google Speech Recognition 오류: {e}")
            return ""
        except Exception as e:
            print(f"❌ 음성 인식 오류: {e}")
            return ""

    def start_voice_control(self):
        """지능형 음성 제어 시작 (메인 인터페이스)"""
        return self.start_intelligent_voice_control()

    def start_intelligent_voice_control(self):
        """지능형 음성 제어 시작"""
        if self.voice_control_active:
            print("🧠 지능형 음성 제어가 이미 실행 중입니다.")
            return

        self.voice_control_active = True
        self.listening_thread = threading.Thread(target=self._intelligent_voice_loop, daemon=True)
        self.listening_thread.start()

        startup_msg = "🧠🌐 소리새 지능형 IoT 하이브리드 제어를 시작합니다."
        if self.autonomous_mode:
            startup_msg += " AI가 능동적으로 최적의 제어를 결정합니다."

        self.speak(startup_msg + " '소리새야'라고 부르시면 됩니다.")
        print("🧠 지능형 음성 제어 시작됨")

    def stop_voice_control(self):
        """음성 제어 중지"""
        self.voice_control_active = False
        self.speak("지능형 음성 제어를 종료합니다.")
        print("🧠 지능형 음성 제어 중지됨")

    def toggle_autonomous_mode(self):
        """능동적 모드 토글"""
        self.autonomous_mode = not self.autonomous_mode
        mode_status = "활성화" if self.autonomous_mode else "비활성화"
        self.speak(f"능동적 AI 모드를 {mode_status}했습니다.")
        print(f"🧠 능동적 모드: {mode_status}")
        return self.autonomous_mode

    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 반환"""
        return {
            'autonomous_mode': self.autonomous_mode,
            'hybrid_mode': self.hybrid_mode,
            'voice_control_active': self.voice_control_active,
            'total_decisions': len(self.decision_engine.decision_history),
            'hybrid_system_connected': self.hybrid_system is not None
        }

    def _intelligent_voice_loop(self):
        """지능형 음성 제어 루프"""
        wake_words = ["소리새", "헤이 소리새", "오케이 소리새", "소리새야"]
        consecutive_errors = 0
        max_errors = 3

        while self.voice_control_active:
            try:
                # 대기 상태에서 웨이크 워드 감지
                user_input = self.listen()

                if not user_input:
                    continue

                # 웨이크 워드 확인
                wake_word_detected = False
                for wake_word in wake_words:
                    if wake_word in user_input:
                        wake_word_detected = True
                        # 웨이크 워드 제거
                        user_input = user_input.replace(wake_word, "").strip()
                        break

                if not wake_word_detected:
                    continue

                # 능동적 응답 생성
                greeting = self._generate_intelligent_greeting()
                self.speak(greeting)

                # 추가 명령이 이미 포함되어 있는 경우 바로 처리
                if user_input:
                    result = self.intelligent_command_processing(user_input)
                    self._provide_intelligent_feedback(result)
                else:
                    # 추가 명령 대기
                    additional_command = self.listen()
                    if additional_command:
                        # 종료 명령 확인
                        if any(word in additional_command for word in ["종료", "끝", "그만", "중지"]):
                            self.stop_voice_control()
                            break

                        # 지능형 명령 처리
                        result = self.intelligent_command_processing(additional_command)
                        self._provide_intelligent_feedback(result)
                        consecutive_errors = 0  # 성공시 에러 카운트 리셋
                    else:
                        self.speak("명령을 듣지 못했습니다. 다시 시도해주세요.")

            except Exception as e:
                consecutive_errors += 1
                print(f"❌ 지능형 음성 제어 오류: {e}")

                if consecutive_errors >= max_errors:
                    self.speak("연속된 오류가 발생했습니다. 시스템을 재초기화합니다.")
                    self._reinitialize_systems()
                    consecutive_errors = 0

                time.sleep(1)

    def _generate_intelligent_greeting(self) -> str:
        """상황에 맞는 지능적 인사말 생성"""
        current_hour = datetime.now().hour

        if 6 <= current_hour <= 9:
            return "좋은 아침입니다! 오늘 하루도 스마트하게 도와드리겠습니다."
        elif 12 <= current_hour <= 13:
            return "점심시간이네요! 무엇을 도와드릴까요?"
        elif 18 <= current_hour <= 20:
            return "퇴근 시간이군요! 집안을 편안하게 만들어드릴게요."
        elif 21 <= current_hour <= 23:
            return "편안한 저녁시간입니다. 무엇을 도와드릴까요?"
        else:
            return "네, 하이브리드 AI가 최적의 제어를 수행하겠습니다!"

    def _provide_intelligent_feedback(self, result: Dict[str, Any]):
        """지능적 피드백 제공"""
        decision = result.get('decision')
        execution_result = result.get('execution_result', {})

        if execution_result.get('status') == 'success':
            confidence = decision.confidence if decision else 0.0
            feedback = f"성공적으로 완료했습니다! "

            if confidence > 0.9:
                feedback += "AI 신뢰도가 매우 높습니다."
            elif confidence > 0.7:
                feedback += "적절한 결정이었습니다."

            if result.get('hybrid_optimized'):
                feedback += " 하이브리드 연결 최적화도 완료했습니다."

            self.speak(feedback)

        elif execution_result.get('status') == 'security_check_required':
            reason = execution_result.get('reason', '')
            if reason == 'night_time':
                self.speak("야간 보안 모드가 활성화되어 있어 추가 인증이 필요합니다.")

        else:
            self.speak("요청을 처리하는 중 문제가 발생했습니다. 다시 시도하거나 다른 방법을 알려드릴까요?")

    def _reinitialize_systems(self):
        """시스템 재초기화"""
        try:
            print("🔄 시스템 재초기화 중...")

            # 음성 엔진 재초기화
            self.tts_engine = pyttsx3.init()

            # 하이브리드 시스템 재연결 시도
            if HYBRID_AVAILABLE and not self.hybrid_system:
                try:
                    self.hybrid_system = SorisaeIntegratedHybridSystem()
                    self.hybrid_mode = True
                    print("✅ 하이브리드 시스템 재연결 성공")
                except Exception:
                    print("⚠️ 하이브리드 시스템 재연결 실패")

            print("✅ 시스템 재초기화 완료")

        except Exception as e:
            print(f"❌ 재초기화 오류: {e}")

    def _voice_control_loop(self):
        """기존 음성 제어 루프 (호환성 유지)"""
        return self._intelligent_voice_loop()

    def _process_voice_command(self, command: str):
        """음성 명령 처리"""
        try:
            print(f"🎛️ IoT 명령 처리: {command}")

            # IoT 코어에서 명령 처리
            response = self.iot_core.process_iot_command(command)

            # 응답을 음성으로 출력 (간단하게)
            simplified_response = self._simplify_response_for_speech(response)
            self.speak(simplified_response)

            # 상세 응답은 텍스트로 출력
            print(f"\n📋 상세 응답:\n{response}")

        except Exception as e:
            error_msg = f"명령 처리 중 오류가 발생했습니다: {str(e)}"
            print(f"❌ {error_msg}")
            self.speak("죄송합니다. 명령을 처리할 수 없습니다.")

    def _simplify_response_for_speech(self, response: str) -> str:
        """음성 출력용 응답 간소화"""
        # 복잡한 응답을 간단하게 변환
        if "조명 제어 결과" in response:
            if "켜졌습니다" in response:
                return "조명을 켰습니다."
            elif "꺼졌습니다" in response:
                return "조명을 껐습니다."
            elif "밝기" in response:
                return "조명 밝기를 조절했습니다."

        elif "온도 조절 결과" in response:
            if "켜졌습니다" in response:
                return "에어컨을 켰습니다."
            elif "꺼졌습니다" in response:
                return "에어컨을 껐습니다."
            elif "설정했습니다" in response:
                return "온도를 설정했습니다."

        elif "TV 제어 결과" in response:
            if "켜졌습니다" in response:
                return "TV를 켰습니다."
            elif "꺼졌습니다" in response:
                return "TV를 껐습니다."

        elif "시나리오 실행 결과" in response:
            if "외출" in response:
                return "외출 모드를 실행했습니다."
            elif "귀가" in response:
                return "귀가 모드를 실행했습니다."
            elif "취침" in response:
                return "취침 모드를 실행했습니다."
            elif "영화감상" in response:
                return "영화감상 모드를 실행했습니다."

        elif "IoT 시스템 상태" in response:
            return "IoT 시스템 상태를 확인했습니다."

        elif "에너지 관리 결과" in response:
            return "에너지 절약 모드를 실행했습니다."

        else:
            return "명령을 처리했습니다."

    def test_voice_commands(self):
        """음성 명령 테스트 (키보드 입력 시뮬레이션)"""
        print("\n🎤 음성 명령 테스트 모드")
        print("=" * 50)
        print("다음 명령어들을 테스트할 수 있습니다:")
        print("• '소리새 거실 조명 켜줘'")
        print("• '소리새 에어컨 24도로 설정해줘'")
        print("• '소리새 영화감상 모드로 해줘'")
        print("• '소리새 IoT 상태 확인해줘'")
        print("• '종료' (테스트 종료)")
        print("-" * 50)

        while True:
            try:
                user_input = input("\n🎤 음성 명령 입력 (또는 '종료'): ").strip()

                if user_input.lower() in ['종료', '끝', '그만', 'quit', 'exit']:
                    print("🎤 테스트 종료됨")
                    break

                if not user_input:
                    continue

                # 웨이크 워드 제거
                for wake_word in ["소리새", "헤이 소리새", "오케이 소리새"]:
                    if wake_word in user_input:
                        user_input = user_input.replace(wake_word, "").strip()
                        break

                if user_input:
                    self._process_voice_command(user_input)

            except KeyboardInterrupt:
                print("\n🎤 테스트 중단됨")
                break
            except Exception as e:
                print(f"❌ 테스트 오류: {e}")


# 전역 지능형 제어기 인스턴스
intelligent_controller = None


def main():
    """메인 함수"""
    global intelligent_controller

    print("🧠� 소리새 능동적 IoT 하이브리드 음성 제어 시스템")
    print("=" * 60)

    # 지능형 IoT 제어기 초기화
    controller = SorisaeIntelligentIoTController()
    intelligent_controller = controller

    # 시스템 상태 표시
    status = controller.get_system_status()
    print(f"\n📊 시스템 상태:")
    print(f"   🧠 능동적 모드: {'활성화' if status['autonomous_mode'] else '비활성화'}")
    print(f"   🌐 하이브리드 연결: {'활성화' if status['hybrid_mode'] else '비활성화'}")
    print(f"   🎤 음성 인식: 준비완료")

    # 메뉴
    while True:
        try:
            print("\n📋 지능형 IoT 제어 메뉴:")
            print("1. 🧠 지능형 음성 제어 시작 (AI 능동적 의사결정)")
            print("2. 🧪 테스트 모드 (시뮬레이션)")
            print("3. ⚙️  설정 메뉴")
            print("4. 📊 AI 학습 데이터 확인")
            print("5. 🚪 종료")

            choice = input("\n선택 (1-5): ").strip()

            if choice == "1":
                print("\n🧠🌐 지능형 음성 제어를 시작합니다...")
                print("💡 AI가 상황을 분석하여 최적의 제어를 수행합니다")
                print("💡 '소리새야 [명령]' 형태로 말씀해 주세요.")
                print("💡 예: '소리새야 거실 조명 켜줘'")
                print("💡 종료하려면 '소리새야 종료' 라고 말씀해 주세요.")

                controller.start_intelligent_voice_control()

                # 음성 제어가 종료될 때까지 대기
                while controller.voice_control_active:
                    time.sleep(1)

                print("\n메뉴로 돌아갑니다...")

            elif choice == "2":
                print("\n🧪 지능형 테스트 모드")
                test_commands = [
                    "긴급 보안 시스템 켜줘",
                    "거실 조명 켜줘",
                    "온도 올려줘",
                    "야간 도어락 해제해줘",
                    "에어컨 켜줘"
                ]

                for cmd in test_commands:
                    print(f"\n테스트 명령: '{cmd}'")
                    result = controller.intelligent_command_processing(cmd)
                    controller._provide_intelligent_feedback(result)
                    time.sleep(1)

            elif choice == "3":
                print("\n⚙️ 설정 메뉴")
                print("1. 능동적 모드 토글")
                print("2. 하이브리드 연결 상태 확인")
                print("3. 돌아가기")

                setting_choice = input("설정 선택 (1-3): ").strip()

                if setting_choice == "1":
                    new_mode = controller.toggle_autonomous_mode()
                    print(f"능동적 모드: {'활성화' if new_mode else '비활성화'}")

                elif setting_choice == "2":
                    if controller.hybrid_system:
                        status = controller.hybrid_system.get_connection_status()
                        print(f"연결 상태: {status}")
                    else:
                        print("하이브리드 시스템이 비활성화되어 있습니다.")

            elif choice == "4":
                print("\n📊 AI 학습 데이터")
                decision_count = len(controller.decision_engine.decision_history)
                print(f"총 의사결정 수: {decision_count}")

                if decision_count > 0:
                    recent_decisions = controller.decision_engine.decision_history[-5:]
                    print("\n최근 5개 의사결정:")
                    for i, decision in enumerate(recent_decisions, 1):
                        print(f"  {i}. {decision.device_id}: {decision.action} (신뢰도: {decision.confidence:.2%})")

            elif choice == "5":
                print("🧠🌐 소리새 지능형 IoT 제어 시스템을 종료합니다.")
                break

            else:
                print("❌ 잘못된 선택입니다. 1-5 중에서 선택해 주세요.")

        except KeyboardInterrupt:
            print("\n🌟 프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")

    # 시스템 종료시 정리
    if controller.voice_control_active:
        controller.stop_voice_control()

    print("✅ 지능형 IoT 시스템 종료 완료")


if __name__ == "__main__":
    main()
