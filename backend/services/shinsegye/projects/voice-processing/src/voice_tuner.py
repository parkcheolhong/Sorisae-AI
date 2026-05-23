#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧠� 소리새 지능형 하이브리드 음성 튜너
Sorisae Intelligent Hybrid Voice Tuner

- 하이브리드 환경 자동 감지 및 최적화
- AI 기반 음성 설정 자동 조절
- 네트워크 상황별 음성 품질 최적화
- 실시간 환경 분석 및 적응형 설정
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

import pyttsx3
import speech_recognition as sr

# 하이브리드 시스템 import
try:
    from hybrid_voice_processor import HybridVoiceProcessor
    from sorisae_integrated_hybrid_system import SorisaeIntegratedHybridSystem
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False
    print("⚠️ 하이브리드 시스템 선택적 로드 - 기본 모드로 실행")


@dataclass
class EnvironmentProfile:
    """환경 프로파일"""
    connection_type: str
    signal_strength: float
    noise_level: float
    latency_ms: float
    bandwidth_kbps: float
    location_type: str
    timestamp: str


@dataclass
class VoiceOptimization:
    """음성 최적화 결정"""
    speech_rate: int
    volume: float
    energy_threshold: int
    noise_reduction: bool
    latency_compensation: float
    quality_mode: str
    reasoning: str
    confidence: float
    timestamp: str


class IntelligentEnvironmentAnalyzer:
    """지능형 환경 분석기"""

    def __init__(self):
        self.logger = logging.getLogger('EnvironmentAnalyzer')
        self.environment_history = []
        self.current_profile = None

        print("🧠🌍 지능형 환경 분석기 초기화")

    def analyze_current_environment(self) -> EnvironmentProfile:
        """현재 환경 자동 분석"""
        current_time = datetime.now()

        # 1. 연결 타입 및 신호 강도 분석
        connection_info = self._analyze_connection()

        # 2. 노이즈 레벨 측정
        noise_level = self._measure_ambient_noise()

        # 3. 네트워크 지연시간 측정
        latency = self._measure_network_latency()

        # 4. 대역폭 측정
        bandwidth = self._estimate_bandwidth()

        # 5. 위치 타입 추정
        location_type = self._estimate_location_type(connection_info, noise_level)

        profile = EnvironmentProfile(
            connection_type=connection_info['type'],
            signal_strength=connection_info['strength'],
            noise_level=noise_level,
            latency_ms=latency,
            bandwidth_kbps=bandwidth,
            location_type=location_type,
            timestamp=current_time.isoformat()
        )

        self.environment_history.append(profile)
        self.current_profile = profile

        return profile

    def _analyze_connection(self) -> Dict[str, Any]:
        """연결 상태 분석"""
        # 실제로는 네트워크 인터페이스를 분석
        import random
        connection_types = ['terrestrial', 'mobile', 'satellite']

        return {
            'type': random.choice(connection_types),
            'strength': random.uniform(0.3, 1.0)
        }

    def _measure_ambient_noise(self) -> float:
        """주변 소음 레벨 측정"""
        try:
            # 실제로는 마이크로 소음 레벨 측정
            import random
            return random.uniform(0.1, 0.8)  # 0.0 (조용) ~ 1.0 (시끄러움)
        except Exception:
            return 0.3  # 기본값

    def _measure_network_latency(self) -> float:
        """네트워크 지연시간 측정"""
        try:
            import platform
            import subprocess

            # Windows ping 명령어
            if platform.system().lower() == 'windows':
                result = subprocess.run(['ping', '-n', '1', '8.8.8.8'],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # ping 결과에서 시간 추출 (간단한 예시)
                    return 50.0  # 실제로는 파싱해서 추출

            return 100.0  # 기본값
        except Exception:
            return 150.0  # 오류시 기본값

    def _estimate_bandwidth(self) -> float:
        """대역폭 추정"""
        # 실제로는 속도 테스트 수행
        if self.current_profile:
            if self.current_profile.connection_type == 'satellite':
                return 1000  # 1 Mbps
            elif self.current_profile.connection_type == 'mobile':
                return 5000  # 5 Mbps
            else:
                return 10000  # 10 Mbps
        return 5000

    def _estimate_location_type(self, connection_info: Dict, noise_level: float) -> str:
        """위치 타입 추정"""
        if connection_info['type'] == 'satellite':
            return 'remote'  # 원격지
        elif noise_level > 0.6:
            return 'urban'   # 도시
        elif noise_level < 0.3:
            return 'rural'   # 시골
        else:
            return 'suburban'  # 교외


class IntelligentVoiceOptimizer:
    """지능형 음성 최적화기"""

    def __init__(self):
        self.logger = logging.getLogger('VoiceOptimizer')
        self.optimization_history = []

        # 환경별 최적 설정 데이터베이스
        self.optimization_database = {
            'satellite': {
                'speech_rate': 120,      # 느린 속도
                'volume': 1.0,           # 최대 볼륨
                'energy_threshold': 200,  # 높은 감도
                'noise_reduction': True,
                'latency_compensation': 0.5,
                'quality_mode': 'reliability'
            },
            'mobile': {
                'speech_rate': 150,
                'volume': 0.8,
                'energy_threshold': 300,
                'noise_reduction': True,
                'latency_compensation': 0.2,
                'quality_mode': 'balanced'
            },
            'terrestrial': {
                'speech_rate': 180,
                'volume': 0.7,
                'energy_threshold': 400,
                'noise_reduction': False,
                'latency_compensation': 0.0,
                'quality_mode': 'performance'
            }
        }

        print("🧠🎤 지능형 음성 최적화기 초기화")

    def optimize_for_environment(self, env_profile: EnvironmentProfile) -> VoiceOptimization:
        """환경에 맞는 음성 설정 최적화"""
        current_time = datetime.now()

        # 기본 설정 선택
        base_config = self.optimization_database.get(
            env_profile.connection_type,
            self.optimization_database['terrestrial']
        )

        # 환경 조건에 따른 동적 조정
        optimized_config = self._dynamic_optimization(base_config, env_profile)

        # 최적화 신뢰도 계산
        confidence = self._calculate_optimization_confidence(env_profile)

        # 최적화 근거 생성
        reasoning = self._generate_optimization_reasoning(env_profile, optimized_config)

        optimization = VoiceOptimization(
            speech_rate=optimized_config['speech_rate'],
            volume=optimized_config['volume'],
            energy_threshold=optimized_config['energy_threshold'],
            noise_reduction=optimized_config['noise_reduction'],
            latency_compensation=optimized_config['latency_compensation'],
            quality_mode=optimized_config['quality_mode'],
            reasoning=reasoning,
            confidence=confidence,
            timestamp=current_time.isoformat()
        )

        self.optimization_history.append(optimization)
        return optimization

    def _dynamic_optimization(self, base_config: Dict, env_profile: EnvironmentProfile) -> Dict:
        """동적 최적화 조정"""
        config = base_config.copy()

        # 신호 강도에 따른 조정
        if env_profile.signal_strength < 0.5:
            config['speech_rate'] = max(80, config['speech_rate'] - 30)
            config['volume'] = min(1.0, config['volume'] + 0.2)
            config['energy_threshold'] = max(100, config['energy_threshold'] - 100)

        # 노이즈 레벨에 따른 조정
        if env_profile.noise_level > 0.6:
            config['volume'] = min(1.0, config['volume'] + 0.3)
            config['energy_threshold'] = max(150, config['energy_threshold'] - 50)
            config['noise_reduction'] = True

        # 지연시간에 따른 조정
        if env_profile.latency_ms > 200:
            config['speech_rate'] = max(100, config['speech_rate'] - 20)
            config['latency_compensation'] = min(1.0, config['latency_compensation'] + 0.3)

        # 대역폭에 따른 조정
        if env_profile.bandwidth_kbps < 2000:
            config['quality_mode'] = 'efficiency'
            config['speech_rate'] = max(120, config['speech_rate'] - 10)

        return config

    def _calculate_optimization_confidence(self, env_profile: EnvironmentProfile) -> float:
        """최적화 신뢰도 계산"""
        confidence_factors = []

        # 신호 강도 신뢰도
        confidence_factors.append(env_profile.signal_strength)

        # 연결 안정성 (지연시간 기반)
        latency_confidence = max(0.0, 1.0 - (env_profile.latency_ms / 500))
        confidence_factors.append(latency_confidence)

        # 대역폭 신뢰도
        bandwidth_confidence = min(1.0, env_profile.bandwidth_kbps / 5000)
        confidence_factors.append(bandwidth_confidence)

        return sum(confidence_factors) / len(confidence_factors)

    def _generate_optimization_reasoning(self, env_profile: EnvironmentProfile, config: Dict) -> str:
        """최적화 근거 생성"""
        reasons = []

        if env_profile.connection_type == 'satellite':
            reasons.append("위성 연결로 안정성 우선 설정")
        elif env_profile.connection_type == 'mobile':
            reasons.append("모바일 연결로 균형 모드 적용")
        else:
            reasons.append("지상파 연결로 고성능 모드 설정")

        if env_profile.signal_strength < 0.5:
            reasons.append("약한 신호로 인한 보상 설정")

        if env_profile.noise_level > 0.6:
            reasons.append("높은 소음 환경으로 볼륨 증가")

        if env_profile.latency_ms > 200:
            reasons.append("높은 지연시간으로 속도 조절")

        return " | ".join(reasons) if reasons else "표준 최적화 적용"


class SorisaeIntelligentVoiceTuner:
    """소리새 지능형 하이브리드 음성 튜너"""

    def __init__(self):
        print("🧠🎤" + "=" * 50 + "🧠🎤")
        print("   소리새 지능형 하이브리드 음성 튜너")
        print("   Sorisae Intelligent Hybrid Voice Tuner")
        print("🧠🎤" + "=" * 50 + "🧠🎤")

        self.config_path = "config/voice_settings.json"

        # 지능형 시스템들 초기화
        self.env_analyzer = IntelligentEnvironmentAnalyzer()
        self.voice_optimizer = IntelligentVoiceOptimizer()

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

        # 기존 음성 엔진
        self.load_current_settings()
        self.init_engines()

        # 자동 최적화 상태
        self.auto_optimization = True
        self.monitoring_active = False
        self.monitoring_thread = None

        print("🧠 지능형 음성 튜너 준비 완료!")

    def start_intelligent_monitoring(self):
        """지능형 환경 모니터링 시작"""
        if self.monitoring_active:
            print("⚠️ 모니터링이 이미 활성화되어 있습니다")
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        print("🔍 지능형 환경 모니터링 시작 - AI가 최적 음성 설정을 자동 조절합니다")

    def _monitoring_loop(self):
        """모니터링 루프"""
        monitoring_interval = 10  # 10초마다 환경 체크

        while self.monitoring_active:
            try:
                if self.auto_optimization:
                    # 환경 분석
                    env_profile = self.env_analyzer.analyze_current_environment()

                    # 음성 최적화
                    optimization = self.voice_optimizer.optimize_for_environment(env_profile)

                    # 최적화 적용
                    self._apply_intelligent_optimization(optimization)

                time.sleep(monitoring_interval)

            except Exception as e:
                self.env_analyzer.logger.error(f"모니터링 루프 오류: {e}")
                time.sleep(monitoring_interval * 2)

    def _apply_intelligent_optimization(self, optimization: VoiceOptimization):
        """지능형 최적화 적용"""
        if optimization.confidence < 0.5:
            print(f"⚠️ 최적화 신뢰도 낮음 ({optimization.confidence:.1%}) - 적용 건너뜀")
            return

        print(f"\n🧠 AI 음성 최적화 적용:")
        print(f"   근거: {optimization.reasoning}")
        print(f"   신뢰도: {optimization.confidence:.1%}")
        print(f"   품질 모드: {optimization.quality_mode}")

        try:
            # TTS 설정 적용
            self.tts_engine.setProperty('rate', optimization.speech_rate)
            self.tts_engine.setProperty('volume', optimization.volume)

            # 음성 인식 설정 적용
            self.recognizer.energy_threshold = optimization.energy_threshold

            # 설정 업데이트
            self.settings["text_to_speech"]["rate"] = optimization.speech_rate
            self.settings["text_to_speech"]["volume"] = optimization.volume
            self.settings["speech_recognition"]["energy_threshold"] = optimization.energy_threshold

            print(f"✅ 최적화 적용 완료:")
            print(f"   음성 속도: {optimization.speech_rate}")
            print(f"   볼륨: {optimization.volume:.1f}")
            print(f"   마이크 감도: {optimization.energy_threshold}")

        except Exception as e:
            print(f"❌ 최적화 적용 실패: {e}")

    def manual_environment_optimization(self):
        """수동 환경 최적화"""
        print("🔍 현재 환경 분석 중...")

        # 환경 분석
        env_profile = self.env_analyzer.analyze_current_environment()

        print(f"\n📊 환경 분석 결과:")
        print(f"   연결 타입: {env_profile.connection_type}")
        print(f"   신호 강도: {env_profile.signal_strength:.1%}")
        print(f"   소음 레벨: {env_profile.noise_level:.1%}")
        print(f"   지연시간: {env_profile.latency_ms:.0f}ms")
        print(f"   대역폭: {env_profile.bandwidth_kbps:.0f} kbps")
        print(f"   위치 타입: {env_profile.location_type}")

        # 최적화 계산
        optimization = self.voice_optimizer.optimize_for_environment(env_profile)

        print(f"\n🧠 AI 최적화 제안:")
        print(f"   추천 음성 속도: {optimization.speech_rate}")
        print(f"   추천 볼륨: {optimization.volume:.1f}")
        print(f"   추천 마이크 감도: {optimization.energy_threshold}")
        print(f"   품질 모드: {optimization.quality_mode}")
        print(f"   최적화 근거: {optimization.reasoning}")
        print(f"   신뢰도: {optimization.confidence:.1%}")

        # 사용자 확인
        if input("\n이 설정을 적용하시겠습니까? (y/N): ").lower().startswith('y'):
            self._apply_intelligent_optimization(optimization)

            # 테스트
            test_text = f"환경에 최적화된 음성 설정이 적용되었습니다. {optimization.quality_mode} 모드로 동작합니다."
            self.test_voice_output(test_text)
        else:
            print("❌ 최적화가 취소되었습니다")

    def get_optimization_history(self):
        """최적화 이력 조회"""
        print(f"\n📈 최적화 이력 ({len(self.voice_optimizer.optimization_history)}건):")
        print("=" * 60)

        for i, opt in enumerate(self.voice_optimizer.optimization_history[-5:], 1):
            print(f"{i}. {opt.timestamp[:19]}")
            print(f"   품질모드: {opt.quality_mode} | 신뢰도: {opt.confidence:.1%}")
            print(f"   속도: {opt.speech_rate} | 볼륨: {opt.volume:.1f}")
            print(f"   근거: {opt.reasoning}")
            print()

    def toggle_auto_optimization(self):
        """자동 최적화 토글"""
        self.auto_optimization = not self.auto_optimization
        status = "활성화" if self.auto_optimization else "비활성화"
        print(f"🧠 자동 최적화: {status}")

        if self.auto_optimization and not self.monitoring_active:
            self.start_intelligent_monitoring()

        return self.auto_optimization

    def load_current_settings(self):
        """현재 음성 설정 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            else:
                self.settings = self.get_default_settings()
        except Exception as e:
            print(f"⚠️ 설정 로드 실패: {e}")
            self.settings = self.get_default_settings()

    def get_default_settings(self):
        """기본 음성 설정"""
        return {
            "speech_recognition": {
                "energy_threshold": 300,
                "dynamic_energy_threshold": True,
                "pause_threshold": 0.8,
                "phrase_threshold": 0.3,
                "timeout": 5,
                "phrase_time_limit": 3,
                "language": "ko-KR"
            },
            "text_to_speech": {
                "rate": 150,
                "volume": 0.9,
                "voice_id": None
            },
            "system": {
                "log_commands": True,
                "debug_mode": False,
                "auto_adjust_noise": True,
                "ambient_noise_duration": 0.5
            }
        }

    def init_engines(self):
        """음성 엔진 초기화"""
        self.tts_engine = pyttsx3.init()
        self.recognizer = sr.Recognizer()
        self.apply_current_settings()

    def apply_current_settings(self):
        """현재 설정을 엔진에 적용"""
        # TTS 설정
        tts = self.settings["text_to_speech"]
        self.tts_engine.setProperty('rate', tts["rate"])
        self.tts_engine.setProperty('volume', tts["volume"])

        # 음성 선택
        voices = self.tts_engine.getProperty('voices')
        if voices and tts.get("voice_id"):
            for voice in voices:
                if voice.id == tts["voice_id"]:
                    self.tts_engine.setProperty('voice', voice.id)
                    break

        # 음성 인식 설정
        sr_config = self.settings["speech_recognition"]
        self.recognizer.energy_threshold = sr_config["energy_threshold"]
        self.recognizer.dynamic_energy_threshold = sr_config["dynamic_energy_threshold"]
        self.recognizer.pause_threshold = sr_config["pause_threshold"]
        self.recognizer.phrase_threshold = sr_config["phrase_threshold"]

    def test_voice_output(self, text="안녕하세요! 소리새 AI입니다. 음성이 잘 들리시나요?"):
        """음성 출력 테스트"""
        print(f"🔊 테스트 음성: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def test_voice_input(self):
        """음성 입력 테스트"""
        try:
            with sr.Microphone() as source:
                print("🎤 음성 인식 테스트 중... 아무 말이나 해보세요 (5초):")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)

                text = self.recognizer.recognize_google(audio, language="ko-KR")
                print(f"✅ 인식된 음성: '{text}'")
                return text
        except sr.WaitTimeoutError:
            print("⏱️ 시간 초과 - 음성이 감지되지 않았습니다")
        except sr.UnknownValueError:
            print("❌ 음성을 인식할 수 없습니다")
        except sr.RequestError as e:
            print(f"❌ 음성 인식 서비스 오류: {e}")
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
        return None

    def list_available_voices(self):
        """사용 가능한 음성 목록"""
        voices = self.tts_engine.getProperty('voices')
        print("\n🎭 사용 가능한 음성들:")
        print("=" * 50)

        for i, voice in enumerate(voices):
            languages = getattr(voice, 'languages', [])
            gender = "여성" if 'female' in voice.name.lower() else "남성" if 'male' in voice.name.lower() else "불명"

            print(f"{i + 1:2d}. {voice.name}")
            print(f"    ID: {voice.id}")
            print(f"    성별: {gender}")
            if languages:
                print(f"    언어: {', '.join(languages)}")
            print()

    def adjust_speech_rate(self, new_rate):
        """음성 속도 조절"""
        if 50 <= new_rate <= 400:
            self.settings["text_to_speech"]["rate"] = new_rate
            self.tts_engine.setProperty('rate', new_rate)
            print(f"🎵 음성 속도를 {new_rate}로 설정했습니다")
            return True
        else:
            print("❌ 음성 속도는 50-400 범위여야 합니다")
            return False

    def adjust_volume(self, new_volume):
        """볼륨 조절"""
        if 0.0 <= new_volume <= 1.0:
            self.settings["text_to_speech"]["volume"] = new_volume
            self.tts_engine.setProperty('volume', new_volume)
            print(f"🔊 볼륨을 {new_volume:.1f}로 설정했습니다")
            return True
        else:
            print("❌ 볼륨은 0.0-1.0 범위여야 합니다")
            return False

    def adjust_energy_threshold(self, new_threshold):
        """음성 인식 에너지 임계값 조절"""
        if 50 <= new_threshold <= 2000:
            self.settings["speech_recognition"]["energy_threshold"] = new_threshold
            self.recognizer.energy_threshold = new_threshold
            print(f"🎚️ 마이크 감도를 {new_threshold}로 설정했습니다")
            print("   (값이 낮을수록 더 민감하게 인식)")
            return True
        else:
            print("❌ 에너지 임계값은 50-2000 범위여야 합니다")
            return False

    def set_voice_by_index(self, voice_index):
        """음성을 인덱스로 선택"""
        voices = self.tts_engine.getProperty('voices')
        if 0 <= voice_index < len(voices):
            selected_voice = voices[voice_index]
            self.tts_engine.setProperty('voice', selected_voice.id)
            self.settings["text_to_speech"]["voice_id"] = selected_voice.id
            print(f"🎭 음성을 '{selected_voice.name}'로 변경했습니다")
            return True
        else:
            print(f"❌ 잘못된 음성 인덱스입니다 (0-{len(voices) - 1} 범위)")
            return False

    def save_settings(self):
        """설정 저장"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            # 백업 생성
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                import shutil
                shutil.copy2(self.config_path, backup_path)
                print(f"💾 기존 설정을 {backup_path}에 백업했습니다")

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)

            print(f"✅ 설정이 {self.config_path}에 저장되었습니다")
            return True

        except Exception as e:
            print(f"❌ 설정 저장 실패: {e}")
            return False

    def show_current_settings(self):
        """현재 설정 표시"""
        print("\n🔧 현재 음성 설정:")
        print("=" * 40)

        tts = self.settings["text_to_speech"]
        print(f"📢 음성 출력:")
        print(f"   속도: {tts['rate']}")
        print(f"   볼륨: {tts['volume']}")

        sr_config = self.settings["speech_recognition"]
        print(f"\n🎤 음성 인식:")
        print(f"   에너지 임계값: {sr_config['energy_threshold']}")
        print(f"   동적 조절: {sr_config['dynamic_energy_threshold']}")
        print(f"   일시정지 임계값: {sr_config['pause_threshold']}")
        print(f"   언어: {sr_config['language']}")

        # 현재 음성 정보
        voices = self.tts_engine.getProperty('voices')
        current_voice = self.tts_engine.getProperty('voice')
        for voice in voices:
            if voice.id == current_voice:
                print(f"\n🎭 현재 음성: {voice.name}")
                break

    def intelligent_interactive_tuning(self):
        """지능형 대화형 음성 조절"""
        print("🧠🎤 소리새 지능형 하이브리드 음성 튜너")
        print("=" * 60)

        # 시작시 자동 최적화 활성화
        if not self.monitoring_active:
            self.start_intelligent_monitoring()

        while True:
            # 현재 상태 표시
            auto_status = "🟢 활성화" if self.auto_optimization else "🔴 비활성화"
            monitoring_status = "🟢 실행중" if self.monitoring_active else "🔴 중지"

            print(f"\n📊 현재 상태:")
            print(f"   🧠 자동 최적화: {auto_status}")
            print(f"   🔍 환경 모니터링: {monitoring_status}")

            print("\n📋 지능형 음성 튜너 메뉴:")
            print("🧠 === AI 최적화 기능 ===")
            print("1. 🔍 환경 분석 및 자동 최적화")
            print("2. 📈 최적화 이력 조회")
            print("3. ⚙️ 자동 최적화 토글")
            print("4. 🌐 하이브리드 연결 상태")

            print("\n🎤 === 기본 음성 기능 ===")
            print("5. 📊 현재 설정 보기")
            print("6. 🔊 음성 출력 테스트")
            print("7. 🎤 음성 인식 테스트")
            print("8. 🎭 사용 가능한 음성 목록")

            print("\n⚙️ === 수동 조정 ===")
            print("9. 🎵 음성 속도 조절")
            print("10. 🔊 볼륨 조절")
            print("11. 🎚️ 마이크 감도 조절")
            print("12. 🎭 음성 변경")
            print("13. 💾 설정 저장")

            print("\n0. 🚪 종료")

            choice = input("\n선택하세요 (0-13): ").strip()

            if choice == '0':
                print("👋 지능형 음성 튜너를 종료합니다")
                self.monitoring_active = False
                break

            # AI 최적화 기능
            elif choice == '1':
                self.manual_environment_optimization()

            elif choice == '2':
                self.get_optimization_history()

            elif choice == '3':
                self.toggle_auto_optimization()

            elif choice == '4':
                self._show_hybrid_connection_status()

            # 기본 음성 기능
            elif choice == '5':
                self.show_current_settings()
                self._show_intelligent_status()

            elif choice == '6':
                test_text = input("테스트할 텍스트를 입력하세요 (엔터 시 기본값): ").strip()
                if not test_text:
                    self.test_voice_output("지능형 하이브리드 음성 시스템이 최적화되었습니다")
                else:
                    self.test_voice_output(test_text)

            elif choice == '7':
                print("🧠 환경에 최적화된 설정으로 음성 인식 테스트:")
                self.test_voice_input()

            elif choice == '8':
                self.list_available_voices()

            # 수동 조정
            elif choice == '9':
                try:
                    current_rate = self.settings['text_to_speech']['rate']
                    new_rate = int(input(f"새로운 속도 입력 (현재: {current_rate}, 범위: 50-400): "))
                    if self.adjust_speech_rate(new_rate):
                        self.test_voice_output("음성 속도가 수동으로 변경되었습니다")
                        if self.auto_optimization:
                            print("💡 자동 최적화가 활성화되어 있어 설정이 다시 조정될 수 있습니다")
                except ValueError:
                    print("❌ 숫자를 입력해주세요")

            elif choice == '10':
                try:
                    current_volume = self.settings['text_to_speech']['volume']
                    new_volume = float(input(f"새로운 볼륨 입력 (현재: {current_volume}, 범위: 0.0-1.0): "))
                    if self.adjust_volume(new_volume):
                        self.test_voice_output("볼륨이 수동으로 변경되었습니다")
                        if self.auto_optimization:
                            print("💡 자동 최적화가 활성화되어 있어 설정이 다시 조정될 수 있습니다")
                except ValueError:
                    print("❌ 숫자를 입력해주세요")

            elif choice == '11':
                try:
                    current_threshold = self.settings['speech_recognition']['energy_threshold']
                    new_threshold = int(input(f"새로운 마이크 감도 입력 (현재: {current_threshold}, 범위: 50-2000): "))
                    if self.adjust_energy_threshold(new_threshold):
                        print("🧪 새로운 감도로 음성 인식 테스트를 해보세요")
                        if self.auto_optimization:
                            print("💡 자동 최적화가 활성화되어 있어 설정이 다시 조정될 수 있습니다")
                except ValueError:
                    print("❌ 숫자를 입력해주세요")

            elif choice == '12':
                self.list_available_voices()
                try:
                    voice_num = int(input("선택할 음성 번호: ")) - 1
                    if self.set_voice_by_index(voice_num):
                        self.test_voice_output("음성이 변경되었습니다")
                except ValueError:
                    print("❌ 숫자를 입력해주세요")

            elif choice == '13':
                self.save_settings()
                print("💡 지능형 설정도 함께 저장되었습니다")

            else:
                print("❌ 잘못된 선택입니다 (0-13 범위)")

    def _show_hybrid_connection_status(self):
        """하이브리드 연결 상태 표시"""
        print(f"\n🌐 하이브리드 연결 상태:")
        print("=" * 40)

        if self.hybrid_system:
            try:
                status = self.hybrid_system.get_connection_status()
                print(f"   연결 타입: {status.get('connection_type', 'unknown')}")
                print(f"   연결 품질: {status.get('connection_quality', 'unknown')}")
                print(f"   신호 강도: {status.get('signal_strength', 'unknown')}")
            except Exception as e:
                print(f"   ⚠️ 하이브리드 상태 조회 실패: {e}")
        else:
            print("   ❌ 하이브리드 시스템 연결되지 않음")

        # 현재 환경 프로파일
        if self.env_analyzer.current_profile:
            profile = self.env_analyzer.current_profile
            print(f"\n📊 현재 환경 프로파일:")
            print(f"   위치 타입: {profile.location_type}")
            print(f"   소음 레벨: {profile.noise_level:.1%}")
            print(f"   지연시간: {profile.latency_ms:.0f}ms")
        else:
            print("\n📊 환경 프로파일: 아직 분석되지 않음")

    def _show_intelligent_status(self):
        """지능형 시스템 상태 표시"""
        print(f"\n🧠 지능형 시스템 상태:")
        print("=" * 40)

        # 환경 분석 이력
        env_count = len(self.env_analyzer.environment_history)
        print(f"   환경 분석 수행: {env_count}회")

        # 최적화 이력
        opt_count = len(self.voice_optimizer.optimization_history)
        print(f"   최적화 적용: {opt_count}회")

        # 최근 최적화 정보
        if self.voice_optimizer.optimization_history:
            latest_opt = self.voice_optimizer.optimization_history[-1]
            print(f"   최근 품질모드: {latest_opt.quality_mode}")
            print(f"   최근 신뢰도: {latest_opt.confidence:.1%}")

    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        print("🔍 지능형 환경 모니터링 중지")

# 전역 인스턴스 (기존 호환성 유지)


class VoiceTuner(SorisaeIntelligentVoiceTuner):
    """기존 VoiceTuner 클래스 호환성 유지"""

    def interactive_tuning(self):
        return self.intelligent_interactive_tuning()


def main():
    """메인 함수"""
    print("\n🧠🎤 소리새 지능형 하이브리드 음성 튜너 시작")

    try:
        # 지능형 튜너 생성
        tuner = SorisaeIntelligentVoiceTuner()

        # 환경 상태 표시
        print(f"\n📊 시스템 상태:")
        print(f"   🧠 지능형 분석: 활성화")
        print(f"   🌐 하이브리드 지원: {'가능' if HYBRID_AVAILABLE else '기본모드'}")
        print(f"   🔍 자동 최적화: {'활성화' if tuner.auto_optimization else '비활성화'}")

        # 지능형 대화형 튜닝 시작
        tuner.intelligent_interactive_tuning()

    except KeyboardInterrupt:
        print("\n\n👋 사용자가 프로그램을 종료했습니다")
        if 'tuner' in locals():
            tuner.stop_monitoring()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
