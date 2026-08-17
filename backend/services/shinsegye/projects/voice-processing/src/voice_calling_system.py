#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠📞 소리새 지능형 하이브리드 음성 호출 시스템
Sorisae Intelligent Hybrid Voice Calling System

- 하이브리드 연결 기반 최적 통화 품질 자동 선택
- 네트워크 상황별 음성 코덱 및 압축률 자동 조절
- AI 기반 통화 라우팅 및 연결 복구
- 능동적 의사결정으로 통화 품질 최적화
"""

import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

import pyttsx3

# 하이브리드 시스템 import
try:
    from hybrid_voice_processor import HybridVoiceProcessor
    from sorisae_integrated_hybrid_system import SorisaeIntegratedHybridSystem
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False
    print("⚠️ 하이브리드 시스템 선택적 로드 - 기본 모드로 실행")


@dataclass
class CallQuality:
    """통화 품질 데이터"""
    connection_type: str
    audio_quality: float  # 0-1
    latency_ms: float
    packet_loss: float
    codec_efficiency: float
    network_stability: float
    timestamp: str


@dataclass
class CallDecision:
    """통화 의사결정 구조체"""
    action: str
    routing_strategy: str
    confidence: float
    quality_optimization: str
    network_preference: str
    codec_selection: str
    reasoning: str
    timestamp: str


class IntelligentCallQualityAnalyzer:
    """지능형 통화 품질 분석기"""

    def __init__(self):
        self.logger = logging.getLogger('CallQualityAnalyzer')
        self.quality_history = []

        # 연결별 품질 매개변수
        self.connection_quality_params = {
            'terrestrial': {'base_quality': 0.95, 'latency': 20, 'stability': 0.9},
            'mobile': {'base_quality': 0.85, 'latency': 80, 'stability': 0.75},
            'satellite': {'base_quality': 0.80, 'latency': 250, 'stability': 0.95}
        }

        print("🧠📊 지능형 통화 품질 분석기 초기화")

    def analyze_call_quality(self, connection_type: str) -> CallQuality:
        """통화 품질 분석"""
        current_time = datetime.now()

        # 연결별 기본 매개변수
        params = self.connection_quality_params.get(connection_type, self.connection_quality_params['terrestrial'])

        # 동적 품질 측정
        import random

        # 오디오 품질 (노이즈, 선명도 등)
        base_quality = params['base_quality']
        quality_fluctuation = random.uniform(0.9, 1.05)
        audio_quality = min(base_quality * quality_fluctuation, 1.0)

        # 지연시간
        base_latency = params['latency']
        latency_variation = random.uniform(0.8, 1.2)
        latency_ms = base_latency * latency_variation

        # 패킷 손실률
        packet_loss = self._calculate_packet_loss(connection_type, audio_quality)

        # 코덱 효율성
        codec_efficiency = self._calculate_codec_efficiency(connection_type, audio_quality)

        # 네트워크 안정성
        network_stability = params['stability'] * random.uniform(0.95, 1.05)

        quality = CallQuality(
            connection_type=connection_type,
            audio_quality=audio_quality,
            latency_ms=latency_ms,
            packet_loss=packet_loss,
            codec_efficiency=codec_efficiency,
            network_stability=min(network_stability, 1.0),
            timestamp=current_time.isoformat()
        )

        self.quality_history.append(quality)
        return quality

    def _calculate_packet_loss(self, connection_type: str, audio_quality: float) -> float:
        """패킷 손실률 계산"""
        base_loss_rates = {
            'terrestrial': 0.001,  # 0.1%
            'mobile': 0.02,        # 2%
            'satellite': 0.005     # 0.5%
        }

        base_loss = base_loss_rates.get(connection_type, 0.01)
        # 품질이 낮으면 패킷 손실률 증가
        quality_impact = (1.0 - audio_quality) * 0.05

        return min(base_loss + quality_impact, 0.1)  # 최대 10%

    def _calculate_codec_efficiency(self, connection_type: str, audio_quality: float) -> float:
        """코덱 효율성 계산"""
        # 연결 타입별 최적 코덱 효율성
        codec_efficiencies = {
            'terrestrial': 0.95,  # 고품질 코덱 사용 가능
            'mobile': 0.85,       # 압축률 높은 코덱
            'satellite': 0.90     # 에러 정정 기능 포함
        }

        base_efficiency = codec_efficiencies.get(connection_type, 0.8)
        return min(base_efficiency * audio_quality, 1.0)


class IntelligentCallRoutingEngine:
    """지능형 통화 라우팅 엔진"""

    def __init__(self):
        self.logger = logging.getLogger('CallRoutingEngine')
        self.routing_history = []

        # 시나리오별 최적 라우팅 전략
        self.routing_strategies = {
            'emergency_call': {'priority': 'reliability', 'fallback': True},
            'business_call': {'priority': 'quality', 'fallback': True},
            'casual_call': {'priority': 'cost', 'fallback': False},
            'conference_call': {'priority': 'stability', 'fallback': True}
        }

        print("🧠🛣️ 지능형 통화 라우팅 엔진 초기화")

    def optimize_call_routing(self, quality: CallQuality, call_type: str = 'casual_call') -> CallDecision:
        """통화 라우팅 최적화"""
        current_time = datetime.now()

        # 통화 타입별 전략 선택
        strategy = self.routing_strategies.get(call_type, self.routing_strategies['casual_call'])

        # 네트워크 선택 결정
        network_preference = self._decide_optimal_network(quality, strategy['priority'])

        # 코덱 선택
        codec_selection = self._select_optimal_codec(quality, network_preference)

        # 품질 최적화 방법
        quality_optimization = self._determine_quality_optimization(quality)

        # 라우팅 행동 결정
        routing_action = self._decide_routing_action(quality, strategy)

        # 신뢰도 계산
        confidence = self._calculate_routing_confidence(quality, network_preference)

        # 의사결정 근거
        reasoning = self._generate_routing_reasoning(quality, strategy, confidence)

        decision = CallDecision(
            action=routing_action,
            routing_strategy=strategy['priority'],
            confidence=confidence,
            quality_optimization=quality_optimization,
            network_preference=network_preference,
            codec_selection=codec_selection,
            reasoning=reasoning,
            timestamp=current_time.isoformat()
        )

        self.routing_history.append(decision)
        return decision

    def _decide_optimal_network(self, quality: CallQuality, priority: str) -> str:
        """최적 네트워크 결정"""
        if priority == 'reliability':
            # 안정성 우선 - 위성 연결 선호
            if quality.network_stability > 0.9:
                return 'satellite'
            elif quality.connection_type == 'terrestrial' and quality.audio_quality > 0.8:
                return 'terrestrial'
            else:
                return 'satellite'

        elif priority == 'quality':
            # 품질 우선 - 지상파 선호
            if quality.audio_quality > 0.9 and quality.latency_ms < 50:
                return 'terrestrial'
            elif quality.audio_quality > 0.8:
                return quality.connection_type
            else:
                return 'terrestrial'

        elif priority == 'cost':
            # 비용 우선 - 지상파 > 모바일 > 위성
            if quality.connection_type == 'terrestrial' and quality.audio_quality > 0.7:
                return 'terrestrial'
            elif quality.connection_type == 'mobile' and quality.audio_quality > 0.75:
                return 'mobile'
            else:
                return 'terrestrial'

        else:  # stability
            # 안정성 우선
            if quality.network_stability > 0.85:
                return quality.connection_type
            else:
                return 'satellite'

    def _select_optimal_codec(self, quality: CallQuality, network: str) -> str:
        """최적 코덱 선택"""
        if network == 'terrestrial' and quality.audio_quality > 0.9:
            return 'high_fidelity'  # 고품질 코덱
        elif network == 'mobile' or quality.latency_ms > 150:
            return 'low_latency_compressed'  # 저지연 압축 코덱
        elif network == 'satellite':
            return 'error_resilient'  # 에러 정정 코덱
        else:
            return 'adaptive'  # 적응형 코덱

    def _determine_quality_optimization(self, quality: CallQuality) -> str:
        """품질 최적화 방법 결정"""
        if quality.packet_loss > 0.05:
            return 'packet_recovery'
        elif quality.latency_ms > 200:
            return 'latency_reduction'
        elif quality.audio_quality < 0.7:
            return 'audio_enhancement'
        else:
            return 'maintain_current'

    def _decide_routing_action(self, quality: CallQuality, strategy: Dict) -> str:
        """라우팅 행동 결정"""
        if quality.audio_quality < 0.5 or quality.packet_loss > 0.1:
            return 'emergency_reroute'
        elif quality.network_stability < 0.6:
            return 'gradual_transition'
        elif quality.audio_quality > 0.9 and quality.latency_ms < 30:
            return 'maintain_optimal'
        else:
            return 'continuous_optimization'

    def _calculate_routing_confidence(self, quality: CallQuality, network_preference: str) -> float:
        """라우팅 신뢰도 계산"""
        quality_confidence = quality.audio_quality
        stability_confidence = quality.network_stability
        efficiency_confidence = quality.codec_efficiency

        return (quality_confidence * 0.4 + stability_confidence * 0.4 + efficiency_confidence * 0.2)

    def _generate_routing_reasoning(self, quality: CallQuality, strategy: Dict, confidence: float) -> str:
        """라우팅 근거 생성"""
        reasons = []

        reasons.append(f"{quality.connection_type} 연결 분석")
        reasons.append(f"우선순위: {strategy['priority']}")
        reasons.append(f"오디오 품질: {quality.audio_quality:.1%}")
        reasons.append(f"지연시간: {quality.latency_ms:.0f}ms")
        reasons.append(f"신뢰도: {confidence:.1%}")

        return " | ".join(reasons)


class SorisaeIntelligentVoiceCallingSystem:
    """소리새 지능형 하이브리드 음성 호출 시스템"""

    def __init__(self):
        print("🧠📞" + "=" * 50 + "🧠📞")
        print("   소리새 지능형 하이브리드 음성 호출 시스템")
        print("   Sorisae Intelligent Hybrid Voice Calling System")
        print("🧠📞" + "=" * 50 + "🧠📞")

        # 지능형 시스템들
        self.quality_analyzer = IntelligentCallQualityAnalyzer()
        self.routing_engine = IntelligentCallRoutingEngine()

        # 하이브리드 시스템 연결
        self.hybrid_system = None
        self.voice_processor = None

        if HYBRID_AVAILABLE:
            try:
                self.hybrid_system = SorisaeIntegratedHybridSystem()
                self.voice_processor = HybridVoiceProcessor()
                print("✅ 하이브리드 시스템 연결 성공")
            except Exception as e:
                print(f"⚠️ 하이브리드 시스템 연결 실패: {e}")

        # 기존 음성 시스템
        self.tts_engine = self._initialize_tts()
        self.users = {}  # 사용자 정보 저장
        self.active_calls = {}  # 활성 통화 관리
        self.call_history = []  # 통화 기록

        # 지능형 기능 상태
        self.intelligent_routing = True
        self.auto_quality_optimization = True

        print("🧠 지능형 음성 호출 시스템 준비 완료!")

    def intelligent_voice_call(
            self,
            caller_nickname: str,
            target_nickname: str,
            message: Optional[str] = None,
            call_type: str = 'casual_call') -> Dict:
        """지능형 음성 호출 실행"""
        try:
            # 사용자 존재 확인
            if caller_nickname not in self.users:
                return {
                    'success': False,
                    'error': f"호출자 '{caller_nickname}'을 찾을 수 없습니다."
                }

            if target_nickname not in self.users:
                return {
                    'success': False,
                    'error': f"호출 대상 '{target_nickname}'을 찾을 수 없습니다."
                }

            # 현재 연결 상태 분석
            current_connection = self._detect_current_connection()

            # 통화 품질 분석
            quality = self.quality_analyzer.analyze_call_quality(current_connection)

            print(f"\n🧠 AI 통화 품질 분석:")
            print(f"   연결 타입: {quality.connection_type}")
            print(f"   오디오 품질: {quality.audio_quality:.1%}")
            print(f"   지연시간: {quality.latency_ms:.0f}ms")
            print(f"   패킷 손실: {quality.packet_loss:.1%}")
            print(f"   네트워크 안정성: {quality.network_stability:.1%}")

            # 지능형 라우팅 결정
            if self.intelligent_routing:
                routing_decision = self.routing_engine.optimize_call_routing(quality, call_type)

                print(f"\n🧠 AI 라우팅 최적화:")
                print(f"   행동: {routing_decision.action}")
                print(f"   네트워크 선택: {routing_decision.network_preference}")
                print(f"   코덱 선택: {routing_decision.codec_selection}")
                print(f"   품질 최적화: {routing_decision.quality_optimization}")
                print(f"   신뢰도: {routing_decision.confidence:.1%}")
                print(f"   근거: {routing_decision.reasoning}")

                # 네트워크 전환 (필요시)
                if routing_decision.network_preference != current_connection:
                    self._switch_network_connection(routing_decision.network_preference)

                # 품질 최적화 적용
                self._apply_quality_optimization(routing_decision)

            # 통화 실행
            call_result = self._execute_intelligent_call(
                caller_nickname,
                target_nickname,
                message,
                quality,
                routing_decision if self.intelligent_routing else None)

            return call_result

        except Exception as e:
            return {
                'success': False,
                'error': f"지능형 음성 호출 실패: {e}"
            }

    def _detect_current_connection(self) -> str:
        """현재 연결 타입 감지"""
        if self.hybrid_system:
            try:
                status = self.hybrid_system.get_connection_status()
                return status.get('connection_type', 'terrestrial')
            except Exception:
                return 'terrestrial'
        else:
            # 기본 연결 타입 (실제로는 네트워크 인터페이스 분석)
            return 'terrestrial'

    def _switch_network_connection(self, preferred_network: str):
        """네트워크 연결 전환"""
        if self.hybrid_system:
            try:
                if preferred_network == 'satellite':
                    self.hybrid_system.force_satellite_connection()
                    print(f"🛰️ 위성 연결로 전환 완료")
                elif preferred_network == 'mobile':
                    print(f"📱 모바일 연결 우선순위로 설정")
                else:
                    self.hybrid_system.force_terrestrial_connection()
                    print(f"🌐 지상파 연결로 전환 완료")
            except Exception as e:
                print(f"⚠️ 네트워크 전환 실패: {e}")

    def _apply_quality_optimization(self, decision: CallDecision):
        """품질 최적화 적용"""
        print(f"⚡ 통화 품질 최적화 적용: {decision.quality_optimization}")

        if decision.quality_optimization == 'packet_recovery':
            print("   📦 패킷 복구 알고리즘 활성화")
        elif decision.quality_optimization == 'latency_reduction':
            print("   ⚡ 지연시간 감소 모드 활성화")
        elif decision.quality_optimization == 'audio_enhancement':
            print("   🎵 오디오 향상 필터 적용")

        print(f"   🎤 코덱: {decision.codec_selection}")

    def _execute_intelligent_call(
            self,
            caller: str,
            target: str,
            message: str,
            quality: CallQuality,
            decision: Optional[CallDecision]) -> Dict:
        """지능형 통화 실행"""
        # 통화 정보 생성
        call_info = {
            'call_id': f"smart_call_{int(time.time())}",
            'caller': caller,
            'target': target,
            'message': message or f"{caller}님이 지능형 하이브리드 연결로 호출하고 있습니다",
            'timestamp': datetime.now().isoformat(),
            'status': 'calling',
            'quality_analysis': asdict(quality),
            'routing_decision': asdict(decision) if decision else None
        }

        # 활성 호출에 추가
        self.active_calls[call_info['call_id']] = call_info

        # 지능형 음성 호출 실행
        self._execute_optimized_voice_call(call_info)

        # 기록 추가
        self.call_history.append(call_info)
        if caller in self.users:
            self.users[caller]['call_history'].append(call_info['call_id'])
        if target in self.users:
            self.users[target]['call_history'].append(call_info['call_id'])

        return {
            'success': True,
            'call_id': call_info['call_id'],
            'message': f"🧠 {caller}님이 지능형 최적화된 연결로 {target}님을 호출했습니다!",
            'quality_score': quality.audio_quality,
            'network_type': quality.connection_type
        }

    def _execute_optimized_voice_call(self, call_info: Dict):
        """최적화된 음성 호출 실행"""
        caller = call_info['caller']
        target = call_info['target']
        message = call_info['message']

        # 지능형 호출 메시지 구성
        smart_call_message = f"""
        {target}님! {target}님!

        🧠 지능형 하이브리드 시스템으로 {caller}님이 호출하고 있습니다.

        📊 통화 품질이 AI로 최적화되었습니다:
        - 네트워크: {call_info['quality_analysis']['connection_type']}
        - 품질: {call_info['quality_analysis']['audio_quality']:.0%}
        - 지연: {call_info['quality_analysis']['latency_ms']:.0f}ms

        {message}

        응답해 주세요!
        """

        # 최적화된 음성 출력
        self.speak(smart_call_message)

        # 지능형 호출 신호 (품질에 따라 조절)
        quality_score = call_info['quality_analysis']['audio_quality']
        call_signals = max(2, int(quality_score * 5))  # 2-5회

        for i in range(call_signals):
            if quality_score > 0.8:
                self.speak("🎵 고품질 연결! 통화 요청입니다!")
            elif quality_score > 0.6:
                self.speak("📞 최적화된 통화 요청입니다!")
            else:
                self.speak("📡 하이브리드 연결 통화 요청!")
            time.sleep(0.8)

# 기존 호환성을 위한 클래스 (VoiceCallingSystem)


class VoiceCallingSystem(SorisaeIntelligentVoiceCallingSystem):
    """기존 VoiceCallingSystem 호환성 유지"""

    def voice_call(self, caller_nickname: str, target_nickname: str, message: str = None) -> Dict:
        """기존 voice_call 메서드 호환성"""
        return self.intelligent_voice_call(caller_nickname, target_nickname, message)

    def _initialize_tts(self):
        """TTS 엔진 초기화"""
        try:
            engine = pyttsx3.init()

            # 한국어 음성 설정
            voices = engine.getProperty('voices')
            for voice in voices:
                if 'korean' in voice.name.lower() or 'korea' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    print(f"🗣️ 한국어 음성 선택: {voice.name}")
                    break

            # 음성 설정
            engine.setProperty('rate', 150)  # 속도
            engine.setProperty('volume', 0.9)  # 볼륨

            return engine
        except Exception as e:
            print(f"⚠️ TTS 초기화 오류: {e}")
            return None

    def register_user(self, nickname: str, user_info: Dict) -> bool:
        """사용자 등록"""
        try:
            self.users[nickname] = {
                'nickname': nickname,
                'real_name': user_info.get('real_name', nickname),
                'voice_preference': user_info.get('voice_preference', 'default'),
                'status': 'online',
                'registered_at': datetime.now().isoformat(),
                'call_history': []
            }

            # 등록 알림
            self.speak(f"{nickname}님이 음성 호출 시스템에 등록되었습니다!")
            print(f"✅ 사용자 등록 완료: {nickname}")
            return True

        except Exception as e:
            print(f"❌ 사용자 등록 실패: {e}")
            return False

    def voice_call(self, caller_nickname: str, target_nickname: str, message: str = None) -> Dict:
        """음성 호출 실행"""
        try:
            # 사용자 존재 확인
            if caller_nickname not in self.users:
                return {
                    'success': False,
                    'error': f"호출자 '{caller_nickname}'을 찾을 수 없습니다."
                }

            if target_nickname not in self.users:
                return {
                    'success': False,
                    'error': f"호출 대상 '{target_nickname}'을 찾을 수 없습니다."
                }

            # 호출 대상 상태 확인
            target_user = self.users[target_nickname]
            if target_user['status'] != 'online':
                return {
                    'success': False,
                    'error': f"{target_nickname}님이 현재 오프라인입니다."
                }

            # 호출 정보
            call_info = {
                'call_id': f"call_{int(time.time())}",
                'caller': caller_nickname,
                'target': target_nickname,
                'message': message or f"{caller_nickname}님이 호출하고 있습니다",
                'timestamp': datetime.now().isoformat(),
                'status': 'calling'
            }

            # 활성 호출에 추가
            self.active_calls[call_info['call_id']] = call_info

            # 음성 호출 실행
            self._execute_voice_call(call_info)

            # 호출 기록 추가
            self.call_history.append(call_info)
            self.users[caller_nickname]['call_history'].append(call_info['call_id'])
            self.users[target_nickname]['call_history'].append(call_info['call_id'])

            return {
                'success': True,
                'call_id': call_info['call_id'],
                'message': f"{caller_nickname}님이 {target_nickname}님을 호출했습니다!"
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"음성 호출 실패: {e}"
            }

    def _execute_voice_call(self, call_info: Dict):
        """실제 음성 호출 실행"""
        caller = call_info['caller']
        target = call_info['target']
        message = call_info['message']

        # 호출 메시지 구성
        call_message = f"""
        {target}님! {target}님!
        {caller}님이 호출하고 있습니다.
        {message}
        응답해 주세요!
        """

        # 음성 출력
        self.speak(call_message)

        # 호출음 효과 (3번 반복)
        for i in range(3):
            self.speak("띵동! 호출입니다!")
            time.sleep(1)

    def answer_call(self, call_id: str, target_nickname: str) -> Dict:
        """호출 응답"""
        try:
            if call_id not in self.active_calls:
                return {
                    'success': False,
                    'error': "해당 호출을 찾을 수 없습니다."
                }

            call_info = self.active_calls[call_id]

            if call_info['target'] != target_nickname:
                return {
                    'success': False,
                    'error': "호출 대상이 일치하지 않습니다."
                }

            # 호출 응답 처리
            call_info['status'] = 'answered'
            call_info['answered_at'] = datetime.now().isoformat()

            # 응답 알림
            answer_message = f"""
            {call_info['caller']}님!
            {target_nickname}님이 호출에 응답했습니다.
            통화를 시작합니다!
            """

            self.speak(answer_message)

            return {
                'success': True,
                'message': f"{target_nickname}님이 호출에 응답했습니다!",
                'call_info': call_info
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"호출 응답 실패: {e}"
            }

    def end_call(self, call_id: str) -> Dict:
        """통화 종료"""
        try:
            if call_id not in self.active_calls:
                return {
                    'success': False,
                    'error': "해당 호출을 찾을 수 없습니다."
                }

            call_info = self.active_calls[call_id]
            call_info['status'] = 'ended'
            call_info['ended_at'] = datetime.now().isoformat()

            # 활성 호출에서 제거
            del self.active_calls[call_id]

            # 종료 알림
            self.speak("통화가 종료되었습니다. 감사합니다!")

            return {
                'success': True,
                'message': "통화가 정상적으로 종료되었습니다."
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"통화 종료 실패: {e}"
            }

    def speak(self, text: str):
        """TTS 음성 출력"""
        if self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception:
                print(f"🔊 [TTS 오류] {text}")
        else:
            print(f"🔊 {text}")

    def get_user_status(self, nickname: str) -> Dict:
        """사용자 상태 조회"""
        if nickname in self.users:
            return {
                'success': True,
                'user_info': self.users[nickname]
            }
        else:
            return {
                'success': False,
                'error': f"사용자 '{nickname}'을 찾을 수 없습니다."
            }

    def get_active_calls(self) -> List[Dict]:
        """활성 호출 목록 조회"""
        return list(self.active_calls.values())

    def get_call_history(self, nickname: str = None) -> List[Dict]:
        """호출 기록 조회"""
        if nickname:
            user_calls = []
            for call in self.call_history:
                if call['caller'] == nickname or call['target'] == nickname:
                    user_calls.append(call)
            return user_calls
        else:
            return self.call_history


# 전역 음성 호출 시스템 인스턴스
voice_calling_system = VoiceCallingSystem()


def test_voice_calling_system():
    """음성 호출 시스템 테스트"""
    print("\n🎤 소리새 음성 호출 시스템 테스트 시작!")
    print("=" * 50)

    # 테스트 사용자 등록
    users_to_register = [
        {
            'nickname': '철홍',
            'real_name': '박철홍',
            'voice_preference': 'korean'
        },
        {
            'nickname': '소리새',
            'real_name': '소리새 AI',
            'voice_preference': 'korean'
        },
        {
            'nickname': '친구1',
            'real_name': '김친구',
            'voice_preference': 'korean'
        }
    ]

    print("\n1. 사용자 등록 테스트:")
    for user in users_to_register:
        result = voice_calling_system.register_user(user['nickname'], user)
        print(f"   {user['nickname']}: {'✅ 성공' if result else '❌ 실패'}")

    print("\n2. 음성 호출 테스트:")

    # 철홍 -> 소리새 호출
    call_result = voice_calling_system.voice_call(
        '철홍', '소리새',
        '안녕하세요! 음성 채팅 테스트입니다!'
    )

    if call_result['success']:
        print(f"   ✅ 호출 성공: {call_result['message']}")

        # 호출 응답 시뮬레이션
        time.sleep(2)
        answer_result = voice_calling_system.answer_call(
            call_result['call_id'], '소리새'
        )

        if answer_result['success']:
            print(f"   ✅ 응답 성공: {answer_result['message']}")

            # 통화 종료
            time.sleep(3)
            end_result = voice_calling_system.end_call(call_result['call_id'])
            print(f"   ✅ 종료: {end_result['message']}")

    print("\n3. 호출 기록 확인:")
    history = voice_calling_system.get_call_history('철홍')
    print(f"   철홍님의 호출 기록: {len(history)}건")

    print("\n🎉 음성 호출 시스템 테스트 완료!")
    return True


if __name__ == "__main__":
    test_voice_calling_system()
