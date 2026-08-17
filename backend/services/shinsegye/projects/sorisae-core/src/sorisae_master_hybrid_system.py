#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🌐🛰️🎤🏠🛡️ 소리새 마스터 하이브리드 시스템
Sorisae Master Hybrid System

모든 하이브리드 모듈을 통합 관리하는 마스터 시스템:
✅ 통합 하이브리드 인터넷 관리 (지상파↔모바일↔위성)
✅ 하이브리드 음성 처리 (온라인↔오프라인)
✅ 하이브리드 IoT 제어 (로컬↔클라우드↔위성)
✅ 하이브리드 사이버 보안 (실시간↔백업↔격리)
✅ 지능형 자동 전환 및 최적화
"""

import json
import os
import signal
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict

# 음성 합성
try:
    import pyttsx3
    TTS_OK = True
except ImportError:
    TTS_OK = False

# 전역 종료 플래그
SHUTDOWN_REQUESTED = False


@dataclass
class SystemModule:
    """시스템 모듈 상태"""
    name: str
    type: str
    status: str  # 'running', 'stopped', 'error'
    connection_type: str
    last_update: str
    health_score: float  # 0.0-1.0


class SorisaeMasterHybridSystem:
    """소리새 마스터 하이브리드 시스템"""

    def __init__(self):
        print("🌐🛰️🎤🏠🛡️" + "=" * 40 + "🌐🛰️🎤🏠🛡️")
        print("    소리새 마스터 하이브리드 시스템")
        print("    Sorisae Master Hybrid System")
        print("    All-in-One Hybrid Intelligence Platform")
        print("🌐🛰️🎤🏠🛡️" + "=" * 40 + "🌐🛰️🎤🏠🛡️")
        print()

        # 시스템 상태
        self.active = True
        self.modules: Dict[str, SystemModule] = {}
        
        # 🔒 동시성 제어 추가 (Thread Safety)
        self._modules_lock = threading.RLock()
        self._status_lock = threading.Lock()

        # 하이브리드 모듈들
        self.integrated_hybrid = None
        self.voice_processor = None
        self.iot_controller = None
        self.security_system = None
        self.conversation_translator = None
        self.interpreter_system = None

        # 음성 엔진
        self.audio_io_enabled = os.environ.get("SORISAE_DISABLE_AUDIO_IO", "0") != "1"
        self.tts = None
        if TTS_OK and self.audio_io_enabled:
            try:
                self.tts = pyttsx3.init()
                self.setup_voice()
            except Exception as e:
                print(f"⚠️ 마스터 하이브리드 TTS 비활성화: {e}")
        elif TTS_OK:
            print("ℹ️ 마스터 하이브리드 헤드리스 오디오 모드")

        # 데이터 저장
        self.data_dir = "master_hybrid_data"
        os.makedirs(self.data_dir, exist_ok=True)

        # 시스템 초기화
        self.initialize_all_modules()
        self.start_system_monitoring()

        print("✅ 마스터 하이브리드 시스템 완전 가동!")
        self.speak("소리새 마스터 하이브리드 시스템이 완전히 준비되었습니다!")

    def setup_voice(self):
        """음성 설정"""
        if TTS_OK and self.tts:
            self.tts.setProperty('rate', 180)
            self.tts.setProperty('volume', 0.9)

    def speak(self, text: str):
        """음성 출력"""
        if TTS_OK and self.audio_io_enabled and self.tts:

            def _speak():
                try:
                    self.tts.say(text)
                    self.tts.runAndWait()
                except Exception as e:
                    print(f"TTS 오류: {e}")
            threading.Thread(target=_speak, daemon=True).start()

        print(f"🗣️ [마스터] {text}")

    def initialize_all_modules(self):
        """모든 모듈 초기화"""
        print("🔧 하이브리드 모듈 초기화 중...")

        # 1. 통합 하이브리드 인터넷 시스템 (핵심)
        try:
            from sorisae_integrated_hybrid_system import SorisaeIntegratedHybridSystem
            self.integrated_hybrid = SorisaeIntegratedHybridSystem()
            with self._modules_lock:
                self.modules['integrated_hybrid'] = SystemModule(
                    name='통합 하이브리드 인터넷',
                    type='core',
                    status='running',
                    connection_type='hybrid',
                    last_update=datetime.now().isoformat(),
                    health_score=1.0
                )
            print("✅ 통합 하이브리드 인터넷 시스템 로드")
        except Exception as e:
            print(f"⚠️ 통합 하이브리드 시스템 로드 실패: {e}")
            with self._modules_lock:
                self.modules['integrated_hybrid'] = SystemModule(
                    name='통합 하이브리드 인터넷',
                    type='core',
                    status='error',
                    connection_type='unknown',
                    last_update=datetime.now().isoformat(),
                    health_score=0.0
                )

        # 2. 하이브리드 음성 처리기
        try:
            from hybrid_voice_processor import HybridVoiceProcessor
            self.voice_processor = HybridVoiceProcessor()
            with self._modules_lock:
                self.modules['voice_processor'] = SystemModule(
                    name='하이브리드 음성 처리기',
                    type='interface',
                    status='running',
                    connection_type='hybrid',
                    last_update=datetime.now().isoformat(),
                    health_score=1.0
                )
            print("✅ 하이브리드 음성 처리기 로드")
        except Exception as e:
            print(f"⚠️ 음성 처리기 로드 실패: {e}")
            with self._modules_lock:
                self.modules['voice_processor'] = SystemModule(
                    name='하이브리드 음성 처리기',
                    type='interface',
                    status='error',
                    connection_type='unknown',
                    last_update=datetime.now().isoformat(),
                    health_score=0.0
                )

        # 3. 하이브리드 IoT 제어기
        try:
            from hybrid_iot_controller import HybridIoTController
            self.iot_controller = HybridIoTController()
            with self._modules_lock:
                self.modules['iot_controller'] = SystemModule(
                    name='하이브리드 IoT 제어기',
                    type='automation',
                    status='running',
                    connection_type='hybrid',
                    last_update=datetime.now().isoformat(),
                    health_score=1.0
                )
            print("✅ 하이브리드 IoT 제어기 로드")
        except Exception as e:
            print(f"⚠️ IoT 제어기 로드 실패: {e}")
            with self._modules_lock:
                self.modules['iot_controller'] = SystemModule(
                    name='하이브리드 IoT 제어기',
                    type='automation',
                    status='error',
                    connection_type='unknown',
                    last_update=datetime.now().isoformat(),
                    health_score=0.0
                )

        # 4. 하이브리드 사이버 보안 시스템
        try:
            from hybrid_cyber_security_system import HybridCyberSecuritySystem
            self.security_system = HybridCyberSecuritySystem()
            with self._modules_lock:
                self.modules['security_system'] = SystemModule(
                    name='하이브리드 사이버 보안',
                    type='security',
                    status='running',
                    connection_type='hybrid',
                    last_update=datetime.now().isoformat(),
                    health_score=1.0
                )
            print("✅ 하이브리드 사이버 보안 시스템 로드")
        except Exception as e:
            print(f"⚠️ 보안 시스템 로드 실패: {e}")
            with self._modules_lock:
                self.modules['security_system'] = SystemModule(
                    name='하이브리드 사이버 보안',
                    type='security',
                    status='error',
                    connection_type='unknown',
                    last_update=datetime.now().isoformat(),
                    health_score=0.0
                )

        # 5. 하이브리드 대화 & 통역 시스템
        try:
            from hybrid_conversation_translator import HybridConversationSystem
            self.conversation_translator = HybridConversationSystem()
            with self._modules_lock:
                self.modules['conversation_translator'] = SystemModule(
                    name='하이브리드 대화 & 통역',
                    type='communication',
                    status='running',
                    connection_type='hybrid',
                    last_update=datetime.now().isoformat(),
                    health_score=1.0
                )
            print("✅ 하이브리드 대화 & 통역 시스템 로드")
        except Exception as e:
            print(f"⚠️ 대화 & 통역 시스템 로드 실패: {e}")
            with self._modules_lock:
                self.modules['conversation_translator'] = SystemModule(
                    name='하이브리드 대화 & 통역',
                    type='communication',
                    status='error',
                    connection_type='unknown',
                    last_update=datetime.now().isoformat(),
                    health_score=0.0
                )

        # 5. 하이브리드 통역 시스템 (나도 통역사)
        try:
            from hybrid_interpreter_system import HybridInterpreterSystem
            self.interpreter_system = HybridInterpreterSystem()
            with self._modules_lock:
                self.modules['interpreter_system'] = SystemModule(
                    name='하이브리드 통역 시스템',
                    type='communication',
                    status='running',
                    connection_type='hybrid',
                    last_update=datetime.now().isoformat(),
                    health_score=1.0
                )
            print("✅ 하이브리드 통역 시스템 로드")
        except Exception as e:
            print(f"⚠️ 통역 시스템 로드 실패: {e}")
            with self._modules_lock:
                self.modules['interpreter_system'] = SystemModule(
                    name='하이브리드 통역 시스템',
                    type='communication',
                    status='error',
                    connection_type='unknown',
                    last_update=datetime.now().isoformat(),
                    health_score=0.0
                )

        # 모듈 로드 결과
        running_modules = len([m for m in self.modules.values() if m.status == 'running'])
        total_modules = len(self.modules)

        print(f"\n📊 모듈 로드 완료: {running_modules}/{total_modules} 성공")
        if running_modules == total_modules:
            print("🎉 모든 하이브리드 모듈이 완벽하게 로드되었습니다!")
        else:
            print("⚠️ 일부 모듈에서 문제가 발생했지만 시스템은 작동합니다.")

    def start_system_monitoring(self):
        """시스템 모니터링 시작"""
        print("🔄 마스터 시스템 모니터링 시작")

        def monitor_loop():
            while self.active and not SHUTDOWN_REQUESTED:
                try:
                    # 모든 모듈 상태 확인
                    self.check_all_modules()

                    # 연결 상태 동기화
                    self.synchronize_connections()

                    # 자동 최적화
                    self.auto_optimize_system()

                    time.sleep(30)  # 30초마다 체크

                except Exception as e:
                    print(f"⚠️ 마스터 모니터링 오류: {e}")
                    time.sleep(60)

        threading.Thread(target=monitor_loop, daemon=True).start()

    def check_all_modules(self):
        """모든 모듈 상태 확인"""
        for module_id, module in self.modules.items():
            try:
                # 모듈별 상태 확인
                if module_id == 'integrated_hybrid' and self.integrated_hybrid:
                    module.health_score = self.check_integrated_hybrid_health()
                elif module_id == 'voice_processor' and self.voice_processor:
                    module.health_score = self.check_voice_processor_health()
                elif module_id == 'iot_controller' and self.iot_controller:
                    module.health_score = self.check_iot_controller_health()
                elif module_id == 'security_system' and self.security_system:
                    module.health_score = self.check_security_system_health()
                elif module_id == 'conversation_translator' and self.conversation_translator:
                    module.health_score = self.check_conversation_translator_health()
                elif module_id == 'interpreter_system' and self.interpreter_system:
                    module.health_score = self.check_interpreter_system_health()

                # 상태 업데이트
                if module.health_score > 0.8:
                    module.status = 'running'
                elif module.health_score > 0.3:
                    module.status = 'degraded'
                else:
                    module.status = 'error'

                module.last_update = datetime.now().isoformat()

            except Exception as e:
                print(f"모듈 상태 확인 오류 ({module_id}): {e}")
                module.health_score = 0.0
                module.status = 'error'

    def check_integrated_hybrid_health(self) -> float:
        """통합 하이브리드 시스템 건강도 확인"""
        if not self.integrated_hybrid:
            return 0.0

        try:
            # 활성 연결 수
            if hasattr(self.integrated_hybrid, 'connections'):
                active_connections = len([c for c in self.integrated_hybrid.connections.values()
                                          if c.status == 'connected'])
                return min(1.0, active_connections / 2.0)  # 2개 이상 연결시 완전한 건강도
            return 0.8  # 기본값
        except Exception:
            return 0.5

    def check_voice_processor_health(self) -> float:
        """음성 처리기 건강도 확인"""
        if not self.voice_processor:
            return 0.0

        try:
            if hasattr(self.voice_processor, 'active') and self.voice_processor.active:
                return 0.9
            return 0.3
        except Exception:
            return 0.5

    def check_iot_controller_health(self) -> float:
        """IoT 제어기 건강도 확인"""
        if not self.iot_controller:
            return 0.0

        try:
            if hasattr(self.iot_controller, 'devices'):
                online_devices = len([d for d in self.iot_controller.devices.values()
                                      if d.status == 'online'])
                total_devices = len(self.iot_controller.devices)
                if total_devices > 0:
                    return online_devices / total_devices
            return 0.7  # 기본값
        except Exception:
            return 0.5

    def check_security_system_health(self) -> float:
        """보안 시스템 건강도 확인"""
        if not self.security_system:
            return 0.0

        try:
            if hasattr(self.security_system, 'monitoring') and self.security_system.monitoring:
                # 활성 위협 수에 따라 건강도 조정
                if hasattr(self.security_system, 'threats'):
                    active_threats = len([t for t in self.security_system.threats
                                          if t.status in ['detected', 'analyzing']])
                    if active_threats == 0:
                        return 1.0
                    elif active_threats < 5:
                        return 0.8
                    else:
                        return 0.6
                return 0.9
            return 0.3
        except Exception:
            return 0.5

    def check_conversation_translator_health(self) -> float:
        """대화 & 통역 시스템 건강도 확인"""
        if not self.conversation_translator:
            return 0.0

        try:
            if hasattr(self.conversation_translator, 'active') and self.conversation_translator.active:
                # 대화 기록 수와 연결 상태로 건강도 판단
                if hasattr(self.conversation_translator, 'conversation_history'):
                    len(self.conversation_translator.conversation_history)

                # 연결 상태 확인
                if hasattr(self.conversation_translator, 'current_connection'):
                    if self.conversation_translator.current_connection != 'offline':
                        return 1.0
                    else:
                        return 0.7  # 오프라인도 기본 기능 제공
                return 0.8
            return 0.3
        except Exception:
            return 0.5

    def check_interpreter_system_health(self) -> float:
        """통역 시스템 건강도 확인"""
        if not self.interpreter_system:
            return 0.0

        try:
            if hasattr(self.interpreter_system, 'active') and self.interpreter_system.active:
                # 번역 캐시 크기에 따라 건강도 조정
                if hasattr(self.interpreter_system, 'translation_cache'):
                    cache_size = len(self.interpreter_system.translation_cache)
                    if cache_size > 100:
                        return 1.0
                    elif cache_size > 50:
                        return 0.9
                    else:
                        return 0.8
                return 0.8
            return 0.3
        except Exception:
            return 0.5

    def synchronize_connections(self):
        """연결 상태 동기화"""
        if not self.integrated_hybrid:
            return

        try:
            # 마스터 연결 상태 가져오기
            master_connection = self.integrated_hybrid.current_primary

            # 모든 서브 모듈에 연결 상태 동기화
            if self.voice_processor and hasattr(self.voice_processor, 'current_connection'):
                self.voice_processor.current_connection = master_connection

            if self.iot_controller and hasattr(self.iot_controller, 'current_connection'):
                self.iot_controller.current_connection = master_connection

            if self.security_system and hasattr(self.security_system, 'current_connection'):
                self.security_system.current_connection = master_connection

            if self.conversation_translator and hasattr(self.conversation_translator, 'current_connection'):
                self.conversation_translator.current_connection = master_connection

            if self.interpreter_system and hasattr(self.interpreter_system, 'current_connection'):
                self.interpreter_system.current_connection = master_connection

            # 모듈 정보 업데이트
            for module in self.modules.values():
                module.connection_type = master_connection

        except Exception as e:
            print(f"연결 동기화 오류: {e}")

    def auto_optimize_system(self):
        """시스템 자동 최적화"""
        try:
            # 전체 시스템 건강도 계산
            total_health = sum(m.health_score for m in self.modules.values())
            avg_health = total_health / len(self.modules) if self.modules else 0

            # 최적화 필요 시
            if avg_health < 0.7:
                print(f"🔧 시스템 최적화 필요 (건강도: {avg_health:.2f})")
                self.optimize_system()

            # 연결 품질에 따른 자동 조정
            if self.integrated_hybrid and hasattr(self.integrated_hybrid, 'auto_switch'):
                if not self.integrated_hybrid.auto_switch:
                    # 자동 전환이 비활성화된 경우 다시 활성화
                    self.integrated_hybrid.auto_switch = True
                    print("🔄 자동 연결 전환 재활성화")

        except Exception as e:
            print(f"자동 최적화 오류: {e}")

    def optimize_system(self):
        """시스템 최적화 실행"""
        print("⚡ 시스템 최적화 실행 중...")

        # 1. 연결 최적화
        if self.integrated_hybrid:
            try:
                # 최적 연결 재선택
                self.integrated_hybrid.intelligent_connection_switch()
                print("🌐 연결 최적화 완료")
            except Exception as e:
                print(f"연결 최적화 오류: {e}")

        # 2. 메모리 정리
        try:
            # 각 모듈의 캐시 정리
            if self.voice_processor and hasattr(self.voice_processor, 'command_history'):
                # 오래된 명령 이력 정리 (최근 100개만 유지)
                if len(self.voice_processor.command_history) > 100:
                    self.voice_processor.command_history = self.voice_processor.command_history[-100:]

            if self.security_system and hasattr(self.security_system, 'threats'):
                # 해결된 위협 정리 (최근 50개만 유지)
                resolved_threats = [t for t in self.security_system.threats if t.status == 'resolved']
                if len(resolved_threats) > 50:
                    self.security_system.threats = [t for t in self.security_system.threats
                                                    if t.status != 'resolved'] + resolved_threats[-50:]

            print("🧹 메모리 정리 완료")
        except Exception as e:
            print(f"메모리 정리 오류: {e}")

        print("✅ 시스템 최적화 완료")

    def voice_command_handler(self, command: str) -> str:
        """통합 음성 명령 처리"""
        cmd = command.lower()

        # 시스템 전체 명령
        if '전체' in cmd and '상태' in cmd:
            return self.get_master_status()

        elif '모든' in cmd and '모듈' in cmd:
            if '재시작' in cmd:
                return self.restart_all_modules()
            elif '상태' in cmd:
                return self.get_all_modules_status()

        elif '시스템' in cmd and '최적화' in cmd:
            self.optimize_system()
            return "시스템 최적화를 실행했습니다."

        elif '하이브리드' in cmd and '모드' in cmd:
            return self.toggle_hybrid_mode()

        # 개별 모듈 명령 라우팅
        elif '대화' in cmd or '통역' in cmd or '번역' in cmd or 'translate' in cmd:
            if self.conversation_translator:
                try:
                    # 대화 모드 시작
                    if '대화' in cmd:
                        self.conversation_translator.start_conversation_mode()
                        return "자유 대화 모드를 시작했습니다. '소리새야'라고 불러주세요!"
                    # 통역 모드 시작
                    elif '통역' in cmd or '번역' in cmd:
                        self.conversation_translator.start_translation_mode()
                        return "통역 모드를 시작했습니다."
                    else:
                        return self.conversation_translator.generate_response(command)
                except Exception as e:
                    return f"대화/통역 처리 오류: {e}"
            return "대화/통역 시스템을 사용할 수 없습니다."

        elif '음성' in cmd or '소리새야' in cmd:
            if self.voice_processor:
                try:
                    return self.voice_processor.voice_command_handler(command)
                except Exception as e:
                    return f"음성 처리 오류: {e}"
            return "음성 처리기가 사용할 수 없습니다."

        elif 'iot' in cmd or '조명' in cmd or '에어컨' in cmd or '히터' in cmd:
            if self.iot_controller:
                try:
                    return self.iot_controller.voice_command_handler(command)
                except Exception as e:
                    return f"IoT 제어 오류: {e}"
            return "IoT 제어기가 사용할 수 없습니다."

        elif '보안' in cmd or '위협' in cmd or '방화벽' in cmd:
            if self.security_system:
                try:
                    return self.security_system.voice_command_handler(command)
                except Exception as e:
                    return f"보안 시스템 오류: {e}"
            return "보안 시스템이 사용할 수 없습니다."

        elif '번역' in cmd or '통역' in cmd or '나도통역사' in cmd:
            if self.interpreter_system:
                try:
                    return self.interpreter_system.voice_command_handler(command)
                except Exception as e:
                    return f"통역 시스템 오류: {e}"
            return "통역 시스템이 사용할 수 없습니다."

        elif '연결' in cmd or '인터넷' in cmd or '위성' in cmd:
            if self.integrated_hybrid:
                try:
                    return self.integrated_hybrid.voice_command_handler(command)
                except Exception as e:
                    return f"연결 관리 오류: {e}"
            return "연결 관리자가 사용할 수 없습니다."

        return "마스터 시스템에서 해당 명령을 이해하지 못했습니다."

    def get_master_status(self) -> str:
        """마스터 시스템 상태"""
        status = "\n🌐🛰️🎤🏠🛡️ 마스터 하이브리드 시스템 상태\n"
        status += "=" * 60 + "\n"

        # 전체 건강도
        total_health = sum(m.health_score for m in self.modules.values())
        avg_health = total_health / len(self.modules) if self.modules else 0
        status += f"💚 전체 시스템 건강도: {avg_health:.1%}\n"

        # 현재 연결
        if self.integrated_hybrid:
            current_conn = self.integrated_hybrid.current_primary
            status += f"📡 현재 주 연결: {current_conn}\n"

        # 모듈별 상태
        status += f"\n📦 모듈 상태 ({len(self.modules)}개):\n"
        for module_id, module in self.modules.items():
            icon = "🟢" if module.status == "running" else "🟡" if module.status == "degraded" else "🔴"
            status += f"  {icon} {module.name}: {module.status} ({module.health_score:.1%})\n"

        # 통계
        running_count = len([m for m in self.modules.values() if m.status == 'running'])
        status += "\n📊 운영 통계:\n"
        status += f"  ✅ 정상 작동: {running_count}/{len(self.modules)} 모듈\n"
        status += f"  🔄 마지막 최적화: {datetime.now().strftime('%H:%M:%S')}\n"

        return status

    def get_all_modules_status(self) -> str:
        """모든 모듈 상세 상태"""
        status = "\n📋 전체 모듈 상세 상태\n"
        status += "=" * 50 + "\n"

        for module_id, module in self.modules.items():
            status += f"\n🔹 {module.name} ({module.type})\n"
            status += f"   상태: {module.status}\n"
            status += f"   건강도: {module.health_score:.1%}\n"
            status += f"   연결: {module.connection_type}\n"
            status += f"   업데이트: {module.last_update.split('T')[-1][:8]}\n"

        return status

    def restart_all_modules(self) -> str:
        """모든 모듈 재시작"""
        print("🔄 모든 모듈 재시작 중...")
        self.speak("모든 하이브리드 모듈을 재시작합니다.")

        # 실제로는 각 모듈의 재시작 메서드 호출
        # 여기서는 시뮬레이션
        for module_id, module in self.modules.items():
            try:
                print(f"🔄 {module.name} 재시작 중...")
                time.sleep(0.5)  # 시뮬레이션
                module.status = 'running'
                module.health_score = 1.0
                module.last_update = datetime.now().isoformat()
                print(f"✅ {module.name} 재시작 완료")
            except Exception as e:
                print(f"❌ {module.name} 재시작 실패: {e}")
                module.status = 'error'

        return "모든 모듈 재시작이 완료되었습니다."

    def toggle_hybrid_mode(self) -> str:
        """하이브리드 모드 토글"""
        if self.integrated_hybrid:
            try:
                # 자동 전환 모드 토글
                current_auto = self.integrated_hybrid.auto_switch
                self.integrated_hybrid.auto_switch = not current_auto

                mode = "활성화" if not current_auto else "비활성화"
                self.speak(f"하이브리드 자동 전환을 {mode}했습니다.")
                return f"하이브리드 자동 전환 {mode}"
            except Exception as e:
                return f"하이브리드 모드 전환 오류: {e}"

        return "하이브리드 시스템을 사용할 수 없습니다."

    def save_master_state(self):
        """마스터 시스템 상태 저장"""
        try:
            master_state = {
                'modules': {k: asdict(v) for k, v in self.modules.items()},
                'timestamp': datetime.now().isoformat(),
                'version': '1.0',
                'total_uptime': time.time()
            }

            filename = os.path.join(self.data_dir, 'master_state.json')
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(master_state, f, indent=2, ensure_ascii=False)

            print("💾 마스터 시스템 상태 저장 완료")
        except Exception as e:
            print(f"⚠️ 마스터 상태 저장 실패: {e}")

    def shutdown(self):
        """마스터 시스템 종료"""
        global SHUTDOWN_REQUESTED
        SHUTDOWN_REQUESTED = True

        print("🛑 마스터 하이브리드 시스템 종료 시작...")
        self.speak("마스터 시스템을 안전하게 종료합니다.")

        self.active = False

        # 모든 서브 모듈 종료
        shutdown_order = [
            'conversation_translator',
            'security_system',
            'iot_controller',
            'voice_processor',
            'integrated_hybrid']

        for module_name in shutdown_order:
            try:
                module_obj = getattr(self, module_name, None)
                if module_obj and hasattr(module_obj, 'shutdown'):
                    print(f"🔄 {module_name} 종료 중...")
                    module_obj.shutdown()
                    print(f"✅ {module_name} 종료 완료")

                    # 모듈 상태 업데이트
                    if module_name in self.modules:
                        self.modules[module_name].status = 'stopped'

            except Exception as e:
                print(f"⚠️ {module_name} 종료 중 오류: {e}")

        # 마스터 상태 저장
        self.save_master_state()

        print("✅ 마스터 하이브리드 시스템 완전 종료")
        self.speak("모든 하이브리드 모듈이 안전하게 종료되었습니다.")


def signal_handler(signum, frame):
    """신호 처리"""
    global SHUTDOWN_REQUESTED
    print(f"\n🛑 종료 신호 받음 (신호: {signum})")
    SHUTDOWN_REQUESTED = True


def main():
    """메인 실행"""

    # 신호 처리 설정
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("🚀 소리새 마스터 하이브리드 시스템 시작!")

    # 마스터 시스템 생성
    master_system = SorisaeMasterHybridSystem()

    try:
        # 음성 인식 시작 (가능한 경우)
        if master_system.voice_processor:
            master_system.voice_processor.start_listening()

        # 메인 상호작용 루프
        while not SHUTDOWN_REQUESTED and master_system.active:
            print("\n🎛️ 마스터 하이브리드 시스템 제어판")
            print("=" * 50)
            print("1. '전체 상태' - 마스터 시스템 상태")
            print("2. '모든 모듈 상태' - 상세 모듈 정보")
            print("3. '시스템 최적화' - 성능 최적화")
            print("4. '거실 조명 켜줘' - IoT 제어")
            print("5. '보안 상태' - 보안 시스템")
            print("6. '위성 연결' - 연결 전환")
            print("7. '영어로 번역' - 통역 시스템")
            print("8. '음성으로 소리새야' - 음성 명령")
            print("9. 'quit' - 종료")
            print("=" * 50)

            try:
                user_input = input("\n🎤 명령 입력: ").strip()

                if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                    print("👋 사용자가 종료를 요청했습니다.")
                    break

                elif user_input:
                    # 명령 처리
                    response = master_system.voice_command_handler(user_input)
                    print(f"\n🤖 응답: {response}")

                    # 중요한 응답은 음성으로도 출력
                    if any(keyword in response for keyword in ['완료', '성공', '오류', '실패']):
                        master_system.speak(response.split('\n')[0])  # 첫 번째 줄만 음성 출력

            except EOFError:
                print("\n입력 스트림이 종료되었습니다.")
                break

    except KeyboardInterrupt:
        print("\n⚠️ 사용자가 프로그램을 중단했습니다.")

    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")

    finally:
        # 안전한 종료
        print("\n🛑 마스터 시스템 종료 절차 시작...")
        master_system.shutdown()
        print("👋 소리새 마스터 하이브리드 시스템을 종료했습니다.")


if __name__ == "__main__":
    main()
