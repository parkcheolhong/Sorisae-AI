#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧠🌐 소리새 지능형 하이브리드 메인 시스템
Sorisae Intelligent Hybrid Main System

- 능동적 시스템 상태 판단
- 자동 하이브리드 모드 전환
- 지능형 모듈 관리
- 연결 품질 기반 최적화
"""

import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

# 로깅 설정 import
from modules.logging_config import setup_logger

# 하이브리드 시스템 import
try:
    from sorisae_master_hybrid_system import SorisaeMasterHybridSystem
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False
    print("⚠️ 하이브리드 시스템 선택적 로드 - 기본 모드로 실행")


@dataclass
class SystemDecision:
    """시스템 의사결정 구조체"""
    module_name: str
    action: str
    reasoning: str
    confidence: float
    hybrid_mode: str
    priority: int
    timestamp: str


# 안전한 모듈 import
try:
    from modules.ai_code_manager.sorisae_core_controller import SorisaeCore
    SORISAE_OK = True
except ImportError as e:
    SORISAE_OK = False
    print(f"⚠️ Sorisae 코어 모듈을 불러올 수 없습니다: {e}")

try:
    # 통합 대시보드를 우선적으로 사용
    from sorisae_integrated_dashboard import run_dashboard as run_integrated_dashboard
    DASHBOARD_OK = True
    INTEGRATED_DASHBOARD = True

    def run_dashboard():
        """통합 대시보드 실행 (브라우저 자동 열기 비활성화)"""
        dashboard_host = os.environ.get("SORISAE_DASHBOARD_HOST", "0.0.0.0")
        dashboard_port = int(os.environ.get("SORISAE_DASHBOARD_PORT", "5050"))
        run_integrated_dashboard(host=dashboard_host, port=dashboard_port, open_browser=False)

except ImportError:
    INTEGRATED_DASHBOARD = False
    try:
        from modules.sorisae_dashboard_web import run_dashboard
        DASHBOARD_OK = True
    except ImportError as e:
        DASHBOARD_OK = False
        print(f"⚠️ 대시보드 모듈을 불러올 수 없습니다: {e}")

        def run_dashboard():
            """대시보드 비활성화 시 대체 함수"""
            print("🌐 대시보드가 비활성화되었습니다.")

# 새로운 확장 기능 import
try:
    from sorisae_multilingual_support import SorisaeMultilingualSupport
    MULTILANG_OK = True
except ImportError as e:
    MULTILANG_OK = False
    print(f"⚠️ 다국어 지원 모듈을 불러올 수 없습니다: {e}")

try:
    from sorisae_iot_integration import SorisaeIoTIntegration
    IOT_OK = True
except ImportError as e:
    IOT_OK = False
    print(f"⚠️ IoT 통합 모듈을 불러올 수 없습니다: {e}")

try:
    from sorisae_interpreter import SorisaeInterpreter
    INTERPRETER_OK = True
except ImportError as e:
    INTERPRETER_OK = False
    print(f"⚠️ 통역 모듈을 불러올 수 없습니다: {e}")

try:
    from sorisae_satellite_wifi_system import SorisaeSatelliteWiFiSystem
    SATELLITE_OK = True
except ImportError as e:
    SATELLITE_OK = False
    print(f"⚠️ 위성 와이파이 모듈을 불러올 수 없습니다: {e}")

try:
    from sorisae_civil_engineering_bidding import CivilEngineeringBiddingSystem
    CIVIL_BIDDING_OK = True
except ImportError as e:
    CIVIL_BIDDING_OK = False
    print(f"⚠️ 토목 입찰 모듈을 불러올 수 없습니다: {e}")


class IntelligentSystemManager:
    """지능형 시스템 관리자"""

    def __init__(self):
        self.logger = logging.getLogger('IntelligentSystemManager')
        self.decision_history = []
        self.module_status = {}
        self.hybrid_system = None
        self.autonomous_mode = True

        # 하이브리드 시스템 초기화
        if HYBRID_AVAILABLE:
            try:
                self.hybrid_system = SorisaeMasterHybridSystem()
                print("🧠🌐 마스터 하이브리드 시스템 활성화")
            except Exception as e:
                print(f"⚠️ 하이브리드 시스템 초기화 실패: {e}")

    def analyze_system_requirements(self, user_request: str = None) -> SystemDecision:
        """시스템 요구사항 분석 및 의사결정"""
        current_time = datetime.now()

        # 1. 시스템 상태 분석
        system_load = self._assess_system_load()

        # 2. 연결 품질 분석
        connection_quality = self._assess_connection_quality()

        # 3. 사용자 요청 분석
        request_complexity = self._analyze_request_complexity(user_request)

        # 4. 최적 하이브리드 모드 결정
        optimal_mode = self._decide_hybrid_mode(system_load, connection_quality, request_complexity)

        # 5. 모듈 우선순위 결정
        module_priority = self._decide_module_priority(user_request, optimal_mode)

        decision = SystemDecision(
            module_name=module_priority.get('primary_module', 'sorisae_core'),
            action=optimal_mode,
            reasoning=f"시스템로드: {system_load}, 연결품질: {connection_quality}, 요청복잡도: {request_complexity}",
            confidence=self._calculate_decision_confidence(system_load, connection_quality),
            hybrid_mode=optimal_mode,
            priority=request_complexity,
            timestamp=current_time.isoformat()
        )

        self.decision_history.append(decision)
        return decision

    def _assess_system_load(self) -> str:
        """시스템 부하 평가"""
        # 실제로는 CPU, 메모리, 활성 모듈 수 등을 확인
        active_modules = len([status for status in self.module_status.values() if status.get('active', False)])

        if active_modules >= 5:
            return "heavy"
        elif active_modules >= 3:
            return "moderate"
        else:
            return "light"

    def _assess_connection_quality(self) -> str:
        """연결 품질 평가"""
        if self.hybrid_system:
            try:
                status = self.hybrid_system.get_connection_status()
                quality = status.get('connection_quality', 'unknown')
                return quality
            except Exception:
                return "unknown"
        return "standard"

    def _analyze_request_complexity(self, request: str) -> int:
        """요청 복잡도 분석 (1-5)"""
        if not request:
            return 2  # 기본값

        request_lower = request.lower()

        # 복잡한 요청 키워드
        complex_keywords = ['번역', '통역', '분석', '예측', '학습', '최적화']
        high_priority = ['긴급', '비상', '중요', '즉시']
        multi_module = ['그리고', '동시에', '함께', '또한']

        complexity = 2  # 기본값

        if any(kw in request_lower for kw in complex_keywords):
            complexity += 2
        if any(kw in request_lower for kw in high_priority):
            complexity += 1
        if any(kw in request_lower for kw in multi_module):
            complexity += 1

        return min(complexity, 5)

    def _decide_hybrid_mode(self, system_load: str, connection_quality: str, complexity: int) -> str:
        """최적 하이브리드 모드 결정"""
        if complexity >= 4 or system_load == "heavy":
            return "satellite_priority"  # 고성능이 필요한 경우
        elif complexity >= 3 or connection_quality == "poor":
            return "mobile_priority"  # 중간 성능 필요
        else:
            return "terrestrial_priority"  # 일반적인 경우

    def _decide_module_priority(self, request: str, hybrid_mode: str) -> Dict[str, Any]:
        """모듈 우선순위 결정"""
        if not request:
            return {'primary_module': 'sorisae_core', 'secondary_modules': []}

        request_lower = request.lower()

        # 모듈 키워드 매핑
        module_keywords = {
            'translator': ['번역', '통역', '언어'],
            'iot': ['조명', '온도', '에어컨', '스마트'],
            'music': ['음악', '작곡', '노래'],
            'dashboard': ['대시보드', '웹', '모니터링'],
            'satellite': ['위성', '연결', '네트워크']
        }

        primary_module = 'sorisae_core'
        secondary_modules = []

        for module, keywords in module_keywords.items():
            if any(kw in request_lower for kw in keywords):
                primary_module = module
                break

        return {
            'primary_module': primary_module,
            'secondary_modules': secondary_modules,
            'hybrid_mode': hybrid_mode
        }

    def _calculate_decision_confidence(self, system_load: str, connection_quality: str) -> float:
        """의사결정 신뢰도 계산"""
        base_confidence = 0.7

        load_weights = {'light': 0.15, 'moderate': 0.1, 'heavy': 0.0}
        quality_weights = {'excellent': 0.15, 'good': 0.1, 'fair': 0.05, 'poor': 0.0}

        load_weight = load_weights.get(system_load, 0.05)
        quality_weight = quality_weights.get(connection_quality, 0.05)

        confidence = base_confidence + load_weight + quality_weight
        return min(max(confidence, 0.0), 1.0)

    def _reinitialize_systems(self):
        """시스템 재초기화"""
        try:
            print("🔄 지능형 시스템 재초기화 중...")

            # 하이브리드 시스템 재연결
            if HYBRID_AVAILABLE and not self.hybrid_system:
                try:
                    self.hybrid_system = SorisaeMasterHybridSystem()
                    print("✅ 하이브리드 시스템 재연결 성공")
                except Exception:
                    print("⚠️ 하이브리드 시스템 재연결 실패")

            # 모듈 상태 리셋
            self.module_status.clear()

            print("✅ 지능형 시스템 재초기화 완료")

        except Exception as e:
            print(f"❌ 재초기화 오류: {e}")
            raise

    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 반환"""
        return {
            'autonomous_mode': self.autonomous_mode,
            'hybrid_available': HYBRID_AVAILABLE,
            'hybrid_system_active': self.hybrid_system is not None,
            'total_decisions': len(self.decision_history),
            'active_modules': len([s for s in self.module_status.values() if s.get('active', False)])
        }


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "voice_history.txt")

# 로그 폴더 생성 (권한 오류 처리 포함)
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    # 쓰기 권한 확인
    test_file = os.path.join(LOG_DIR, ".permission_test")
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
except PermissionError:
    print(f"⚠️ 로그 디렉토리 '{LOG_DIR}'에 대한 쓰기 권한이 없습니다.")
    print("💡 대안: 임시 디렉토리를 사용합니다.")
    import tempfile
    LOG_DIR = os.path.join(tempfile.gettempdir(), "sorisae_logs")
    LOG_FILE = os.path.join(LOG_DIR, "voice_history.txt")
    os.makedirs(LOG_DIR, exist_ok=True)
    print(f"✅ 임시 로그 디렉토리 사용: {LOG_DIR}")
except Exception as e:
    print(f"⚠️ 로그 디렉토리 생성 실패: {e}")
    print("💡 로그 기능이 제한될 수 있습니다.")

# 로거 설정
logger = setup_logger('run_all_shinsegye', level='INFO')


def log_voice_command(text):
    """음성 명령을 로그에 기록"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {text}\n")
        logger.info(f"음성 명령 기록: {text}")
    except PermissionError as e:
        logger.error(f"로그 파일 쓰기 권한 없음: {e}")
        print(f"⚠️ 로그 파일 쓰기 권한이 없습니다: {e}")
    except IOError as e:
        logger.error(f"로그 파일 쓰기 오류: {e}", exc_info=True)
        print(f"⚠️ 로그 파일 쓰기 실패: {e}")
    except Exception as e:
        logger.error(f"로그 기록 중 예상치 못한 오류: {e}", exc_info=True)
        print(f"⚠️ 로그 기록 실패: {e}")


def start_dashboard():
    """대시보드 웹 서버를 백그라운드 스레드로 시작"""
    try:
        logger.info("대시보드 웹 서버 시작")
        threading.Thread(target=run_dashboard, daemon=True).start()
        time.sleep(1)
        logger.info("대시보드 웹 서버 시작 완료")
    except Exception as e:
        logger.warning(f"대시보드 시작 중 오류: {e}")
        print(f"⚠️ 대시보드를 시작할 수 없습니다: {e}")


def initialize_enhanced_features():
    """확장 기능 초기화 (다국어, IoT)"""
    enhanced_features = {}

    # 다국어 지원 초기화
    if MULTILANG_OK:
        try:
            logger.info("다국어 지원 시스템 초기화")
            enhanced_features['multilang'] = SorisaeMultilingualSupport()
            print("✅ 다국어 지원 시스템 활성화 (한국어, English, 日本語, 中文)")
        except Exception as e:
            logger.warning(f"다국어 지원 초기화 실패: {e}")
            print(f"⚠️ 다국어 지원을 초기화할 수 없습니다: {e}")

    # IoT 통합 초기화
    if IOT_OK:
        try:
            logger.info("IoT 통합 시스템 초기화")
            iot_system = SorisaeIoTIntegration()

            # 기본 IoT 디바이스 등록 (이미 기본 디바이스가 자동 생성됨)
            # 추가 디바이스가 필요한 경우 iot_system.iot_manager.add_device() 사용

            enhanced_features['iot'] = iot_system
            print("✅ IoT 통합 시스템 활성화 (스마트 디바이스 연결)")
        except Exception as e:
            logger.warning(f"IoT 통합 초기화 실패: {e}")
            print(f"⚠️ IoT 통합을 초기화할 수 없습니다: {e}")

    # 통역 시스템 초기화
    if INTERPRETER_OK:
        try:
            logger.info("나도 통역사 시스템 초기화")
            interpreter_system = SorisaeInterpreter()
            enhanced_features['interpreter'] = interpreter_system
            print("✅ 나도 통역사 시스템 활성화 (12개 언어 실시간 통역)")
        except Exception as e:
            logger.warning(f"통역 시스템 초기화 실패: {e}")
            print(f"⚠️ 통역 시스템을 초기화할 수 없습니다: {e}")

    # 위성 와이파이 시스템 초기화
    if SATELLITE_OK:
        try:
            logger.info("차세대 인공위성 와이파이 시스템 초기화")
            satellite_system = SorisaeSatelliteWiFiSystem()
            enhanced_features['satellite_wifi'] = satellite_system
            print("✅ 차세대 인공위성 와이파이 시스템 활성화 (전 세계 커버리지)")
        except Exception as e:
            logger.warning(f"위성 와이파이 시스템 초기화 실패: {e}")
            print(f"⚠️ 위성 와이파이 시스템을 초기화할 수 없습니다: {e}")

    # 토목 입찰 시스템 초기화
    if CIVIL_BIDDING_OK:
        try:
            logger.info("지능형 토목 입찰 시스템 초기화")
            civil_bidding_system = CivilEngineeringBiddingSystem()
            enhanced_features['civil_bidding'] = civil_bidding_system
            print("✅ 지능형 토목 입찰 시스템 활성화 (AI 기반 입찰 분석 및 전략 수립)")
        except Exception as e:
            logger.warning(f"토목 입찰 시스템 초기화 실패: {e}")
            print(f"⚠️ 토목 입찰 시스템을 초기화할 수 없습니다: {e}")

    return enhanced_features


def run_intelligent_sorisae_engine(system_manager: IntelligentSystemManager = None):
    """지능형 소리새 엔진 실행"""
    try:
        logger.info("🧠🌐 지능형 소리새 엔진 초기화")

        # 시스템 관리자 초기화
        if not system_manager:
            system_manager = IntelligentSystemManager()

        # 초기 시스템 상태 분석
        initial_decision = system_manager.analyze_system_requirements()
        print("🎯 시스템 초기 분석 완료:")
        print(f"   추천 모드: {initial_decision.hybrid_mode}")
        print(f"   신뢰도: {initial_decision.confidence:.2%}")
        print(f"   근거: {initial_decision.reasoning}")

        # 하이브리드 모드 적용
        if system_manager.hybrid_system:
            try:
                # 하이브리드 모드 최적화 (간단한 구현)
                if hasattr(system_manager.hybrid_system, 'optimize_for_mode'):
                    system_manager.hybrid_system.optimize_for_mode(initial_decision.hybrid_mode)
                else:
                    print(f"🌐 하이브리드 모드 설정: {initial_decision.hybrid_mode}")
            except Exception as e:
                print(f"⚠️ 하이브리드 모드 설정 실패: {e}")

        # 소리새 코어 초기화
        sorisae = SorisaeCore()

        print("\n🧠 지능형 음성 처리 시작 - AI가 상황을 분석하여 최적화합니다")

        for text in sorisae.run():  # 제너레이터로 명령어를 받아옴
            print(f"[사용자 명령]: {text}")
            log_voice_command(text)  # 로그 저장

            # 각 명령에 대해 지능형 분석 수행
            if system_manager.autonomous_mode:
                command_decision = system_manager.analyze_system_requirements(text)
                print(f"🧠 AI 분석: {command_decision.reasoning} (신뢰도: {command_decision.confidence:.1%})")

                # 필요시 하이브리드 모드 동적 조정
                if command_decision.hybrid_mode != initial_decision.hybrid_mode:
                    print(f"🔄 하이브리드 모드 동적 전환: {initial_decision.hybrid_mode} → {command_decision.hybrid_mode}")
                    if system_manager.hybrid_system:
                        try:
                            if hasattr(system_manager.hybrid_system, 'optimize_for_mode'):
                                system_manager.hybrid_system.optimize_for_mode(command_decision.hybrid_mode)
                            else:
                                print(f"🌐 하이브리드 모드 전환: {command_decision.hybrid_mode}")
                        except Exception as e:
                            print(f"⚠️ 하이브리드 모드 전환 실패: {e}")
                    initial_decision = command_decision

    except KeyboardInterrupt:
        logger.info("사용자가 수동으로 종료")
        print("\n🧹 사용자가 수동 종료했습니다.")
    except Exception as e:
        logger.error(f"지능형 시스템 실행 중 오류 발생: {e}", exc_info=True)
        print(f"❌ 지능형 시스템 오류: {e}")

        # 자동 복구 시도
        if system_manager and system_manager.autonomous_mode:
            print("🔄 자동 복구 시도 중...")
            try:
                system_manager._reinitialize_systems()
                print("✅ 시스템 자동 복구 완료")
            except Exception:
                print("❌ 자동 복구 실패 - 수동 재시작이 필요합니다")
        raise
    finally:
        logger.info("지능형 시스템 종료 완료")
        print("🛑 지능형 시스템 종료 완료")
        log_voice_command("=== 지능형 세션 종료 ===")

        # 학습 데이터 요약
        if system_manager:
            decision_count = len(system_manager.decision_history)
            print(f"📊 세션 요약: {decision_count}개의 지능적 의사결정 수행")


def run_sorisae_engine():
    """기존 소리새 엔진 (호환성 유지)"""
    return run_intelligent_sorisae_engine()


def run_demo_mode(enhanced_features):
    """데모 모드 - 음성 인식 없이 사용 가능한 기능 시연"""
    print("\n" + "=" * 70)
    print("🎯 소리새 AI 시스템 - 데모 모드")
    print("=" * 70)
    print("\n📋 사용 가능한 기능:")

    # IoT 통합 데모
    if 'iot' in enhanced_features:
        print("\n🏠 IoT 통합 시스템 데모")
        print("-" * 50)
        iot_system = enhanced_features['iot']

        # 디바이스 목록 표시
        print("연결된 디바이스:")
        for device_id, device in iot_system.iot_manager.devices.items():
            status = "ON" if device.status.value == "on" else "OFF"
            print(f"  • {device.name} ({device.device_type.value}): {status}")

        # 간단한 IoT 명령 시연
        print("\n📡 IoT 명령 시연:")
        try:
            print("  • 거실 조명 켜기...")
            result = iot_system.process_iot_command("거실 조명 켜줘")
            print(f"    결과: {result}")

            print("  • 온도 확인...")
            result = iot_system.process_iot_command("온도 확인")
            print(f"    결과: {result}")
        except Exception as e:
            print(f"    ⚠️ IoT 명령 실행 중 오류: {e}")

    # 다국어 지원 데모
    if 'multilang' in enhanced_features:
        print("\n🌐 다국어 지원 시스템 데모")
        print("-" * 50)
        multilang = enhanced_features['multilang']

        # 지원 언어 목록
        print("지원 언어:", ", ".join(multilang.supported_languages))

        # 간단한 번역 예제
        print("\n번역 예제:")
        examples = [
            ("안녕하세요", "ko", "en"),
            ("Hello", "en", "ja"),
            ("こんにちは", "ja", "ko")
        ]

        for text, src, tgt in examples:
            # 실제 번역은 API 없이 시뮬레이션
            print(f"  • {text} ({src} → {tgt})")

    # 통역 시스템 데모
    if 'interpreter' in enhanced_features:
        print("\n🎤 나도 통역사 시스템 데모")
        print("-" * 50)
        enhanced_features['interpreter']

        print("지원 언어 (12개):")
        print("  한국어, English, 日本語, 中文, Español, Français")
        print("  Deutsch, Русский, العربية, Tiếng Việt, ไทย, Bahasa Indonesia")

        print("\n통역 모드:")
        print("  • 빠른 번역: quick_translate()")
        print("  • 대화형 통역: start_conversation_mode()")
        print("  • 문서 번역: translate_document()")

    # 위성 와이파이 시스템 데모
    if 'satellite_wifi' in enhanced_features:
        print("\n🛰️ 차세대 인공위성 와이파이 시스템 데모")
        print("-" * 50)
        satellite_system = enhanced_features['satellite_wifi']

        try:
            # 위성 네트워크 진단 실행
            satellite_system.run_satellite_diagnostic()

            print("\n🌐 위성 네트워크 기능:")
            print("  • 전 세계 125개 위성 네트워크")
            print("  • 소리새 전용 위성 50개 보유")
            print("  • 자동 최적 위성 선택")
            print("  • 실시간 핸드오버")
            print("  • 비상 모드 지원")
            print("  • 최대 1Gbps 다운로드 속도")
            print("  • 15ms 초저지연")

            # 간단한 연결 테스트
            print("\n🔗 연결 테스트 실행 중...")
            satellite_system.start_satellite_connection()
            time.sleep(2)
            satellite_system.display_connection_info()
            satellite_system.disconnect()

        except Exception as e:
            print(f"    ⚠️ 위성 시스템 데모 중 오류: {e}")

    # 토목 입찰 시스템 데모
    if 'civil_bidding' in enhanced_features:
        print("\n🏗️ 지능형 토목 입찰 시스템 데모")
        print("-" * 50)
        civil_system = enhanced_features['civil_bidding']

        try:
            print("AI 기반 토목 프로젝트 입찰 분석 시스템")
            print("\n🎯 주요 기능:")
            print("  • 프로젝트 종합 분석 (비용, 복잡도, 위험도)")
            print("  • 최적 입찰가 자동 산정")
            print("  • 5명의 전문 AI 에이전트 협업")
            print("  • 실시간 경쟁사 분석")
            print("  • 전략적 입찰 권장사항 제시")

            print("\n🏗️ 지원 프로젝트 유형:")
            print("  도로, 교량, 터널, 댐, 항만, 공항, 지하철")
            print("  하수처리장, 상하수도, 매립지 등")

            # 간단한 데모 프로젝트
            print("\n📋 데모 프로젝트 분석 중...")
            demo_project = {
                "type": "도로",
                "scale": 15,
                "location": "서울",
                "deadline": "2026-12-31"
            }

            analysis = civil_system.analyze_project(demo_project)
            print(f"  • 프로젝트: {analysis['project_type']} ({analysis['scale']}km)")
            print(f"  • 예상 비용: {analysis['adjusted_cost']:,}원")
            print(f"  • 복잡도: {analysis['complexity_score']}")
            print(f"  • 위험 수준: {analysis['risk_analysis']['overall_risk_level']}")

            strategy = civil_system.generate_bidding_strategy(analysis)
            print(f"\n💡 AI 권장 입찰가: {strategy['recommended_bid_amount']:,}원")
            print(f"  • 예상 낙찰률: {strategy['bid_ratio']*100:.2f}%")
            print(f"  • 전략 유형: {strategy['strategy_type']}")

        except Exception as e:
            print(f"    ⚠️ 토목 입찰 시스템 데모 중 오류: {e}")

    print("\n" + "=" * 70)
    print("💡 전체 기능을 사용하려면 의존성을 설치하세요:")
    print("   pip install -r requirements.txt")
    print("=" * 70)
    print("\n✅ 데모 완료! 사용 가능한 기능을 확인하셨습니다.")
    print("👋 프로그램을 종료합니다.\n")


def main():
    """메인 함수: 소리새 지능형 하이브리드 AI 시스템 시작"""
    logger.info("🧠🌐 신세계 지능형 하이브리드 프로젝트 시작")
    print("🧠🌐" + "=" * 60 + "🧠🌐")
    print("🚀 신세계 지능형 하이브리드 프로젝트 실행 중...")
    print("🎵 소리새 (Sorisae) AI - 능동적 의사결정 & 하이브리드 연결")
    print("🌐 나도 통역사 (I am also an Interpreter) - 지능형 번역")
    print("🧠 능동적 AI - 스스로 판단하고 최적화하는 지능형 시스템")
    print("🧠🌐" + "=" * 60 + "🧠🌐")

    try:
        # 지능형 시스템 관리자 초기화
        system_manager = IntelligentSystemManager()

        # 초기 시스템 진단 및 최적화
        print("\n🔍 지능형 시스템 진단 중...")
        initial_analysis = system_manager.analyze_system_requirements()

        print("📊 시스템 분석 결과:")
        print(f"   🧠 추천 모드: {initial_analysis.hybrid_mode}")
        print(f"   📈 신뢰도: {initial_analysis.confidence:.1%}")
        print(f"   🎯 우선 모듈: {initial_analysis.module_name}")
        print(f"   💭 AI 판단: {initial_analysis.reasoning}")

        # 확장 기능 초기화 (지능형 관리)
        enhanced_features = initialize_enhanced_features()

        # 하이브리드 시스템 상태 표시
        if system_manager.hybrid_system:
            print("✅ 마스터 하이브리드 시스템 활성화")
            print("   🌐 지상파 → 📱 모바일 → 🛰️ 위성 자동 전환")
        else:
            print("⚠️ 하이브리드 시스템 기본 모드")

        # 대시보드 웹 서버 시작 (지능형 모니터링)
        if DASHBOARD_OK:
            start_dashboard()
            if INTEGRATED_DASHBOARD:
                print("✅ 소리새 통합 대시보드 웹 서버 시작 (http://localhost:5050)")
            else:
                print("✅ 지능형 대시보드 웹 서버 시작")

        if not sys.stdin or not sys.stdin.isatty():
            print("ℹ️ 비대화형 실행 환경 감지 - 대시보드 서비스 모드로 유지합니다.")
            while True:
                time.sleep(60)

        # 메뉴 시스템
        while True:
            print("\n📋 소리새 지능형 하이브리드 시스템 메뉴:")
            print("1. 🧠 지능형 음성 AI 시작 (완전 자동 모드)")
            print("2. 🧪 시스템 분석 & 테스트 모드")
            print("3. ⚙️  AI 설정 및 학습 데이터")
            print("4. 📊 하이브리드 연결 상태")
            print("5. 🎯 데모 모드 (음성 없이 기능 체험)")
            print("6. 🌐 통합 대시보드 열기 (웹 브라우저)")
            print("7. 🚪 종료")

            choice = input("\n선택 (1-7): ").strip()

            if choice == "1":
                # SORISAE_OK 확인
                if not SORISAE_OK:
                    logger.warning("Sorisae 코어 모듈이 로드되지 않아 데모 모드로 전환합니다")
                    print("\n⚠️ 음성 인식 모듈이 없어 데모 모드로 실행합니다.")
                    print("💡 전체 기능 사용: pip install -r requirements.txt")
                    run_demo_mode(enhanced_features)
                    continue

                print("\n🧠🌐 지능형 음성 AI 시작!")
                print("AI가 모든 상황을 분석하여 최적의 응답을 제공합니다")

                # 지능형 소리새 엔진 실행
                run_intelligent_sorisae_engine(system_manager)

            elif choice == "2":
                print("\n🧪 시스템 분석 & 테스트 모드")
                test_analysis = system_manager.analyze_system_requirements("시스템 전체 분석 요청")
                print(f"분석 결과: {test_analysis.reasoning}")
                print(f"추천 설정: {test_analysis.hybrid_mode}")
                print(f"AI 신뢰도: {test_analysis.confidence:.1%}")

                if enhanced_features:
                    run_demo_mode(enhanced_features)

            elif choice == "3":
                print("\n⚙️ AI 설정 및 학습 데이터")
                print(f"능동적 모드: {'활성화' if system_manager.autonomous_mode else '비활성화'}")
                print(f"총 의사결정 수: {len(system_manager.decision_history)}")

                if system_manager.decision_history:
                    print("\n최근 AI 의사결정:")
                    for i, decision in enumerate(system_manager.decision_history[-3:], 1):
                        print(f"  {i}. {decision.action} (신뢰도: {decision.confidence:.1%})")

                # 모드 토글 옵션
                toggle = input("\n능동적 모드를 변경하시겠습니까? (y/N): ").strip().lower()
                if toggle == 'y':
                    system_manager.autonomous_mode = not system_manager.autonomous_mode
                    mode_status = "활성화" if system_manager.autonomous_mode else "비활성화"
                    print(f"✅ 능동적 모드 {mode_status}")

            elif choice == "4":
                print("\n📊 하이브리드 연결 상태")
                if system_manager.hybrid_system:
                    try:
                        status = system_manager.hybrid_system.get_connection_status()
                        print(f"활성 연결: {status.get('active_connection', '알 수 없음')}")
                        print(f"연결 품질: {status.get('connection_quality', '알 수 없음')}")
                        print(f"비용 정보: {status.get('connection_costs', {})}")
                    except Exception as e:
                        print(f"상태 확인 실패: {e}")
                else:
                    print("하이브리드 시스템이 비활성화되어 있습니다")

            elif choice == "5":
                print("\n🎯 데모 모드 - 음성 없이 기능 체험")
                run_demo_mode(enhanced_features)

            elif choice == "6":
                print("\n🌐 소리새 통합 대시보드 열기")
                if DASHBOARD_OK:
                    import webbrowser
                    dashboard_url = "http://localhost:5050"
                    print(f"📍 대시보드 URL: {dashboard_url}")
                    print("🚀 웹 브라우저에서 대시보드를 여는 중...")
                    webbrowser.open(dashboard_url)
                    print("✅ 브라우저에서 대시보드가 열렸습니다!")
                    print("💡 대시보드에서 실시간 시스템 상태를 모니터링하세요.")
                else:
                    print("❌ 대시보드가 비활성화되어 있습니다.")
                    print("💡 flask 및 flask-socketio 설치: pip install flask flask-socketio")

            elif choice == "7":
                print("🧠🌐 소리새 지능형 하이브리드 시스템을 종료합니다.")
                break

            else:
                print("❌ 잘못된 선택입니다. 1-7 중에서 선택해주세요.")

    except ImportError as e:
        logger.error(f"필수 모듈을 불러올 수 없습니다: {e}", exc_info=True)
        print(f"❌ 모듈 로드 실패: {e}")
        print("💡 해결 방법: pip install -r requirements.txt 실행 후 다시 시도하세요.")
    except Exception as e:
        logger.critical(f"지능형 시스템 초기화 중 심각한 오류: {e}", exc_info=True)
        print(f"❌ 지능형 시스템 초기화 실패: {e}")

        # 자동 복구 시도
        print("🔄 자동 복구 시도 중...")
        try:
            print("기본 모드로 전환하여 재시작합니다...")
            # 기본 모드로 대체 실행
            enhanced_features = initialize_enhanced_features()
            run_demo_mode(enhanced_features)
        except Exception:
            print("❌ 자동 복구 실패 - 프로그램을 재시작해주세요.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 사용자가 프로그램을 종료했습니다.")
    except Exception as e:
        print(f"\n❌ 프로그램 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
