#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🛡️🌐 소리새 하이브리드 사이버 보안 시스템
Sorisae Hybrid Cyber Security System

하이브리드 인터넷 연결을 통한 다층 보안 방어:
- 평상시: 실시간 위협 정보 업데이트 (일반 인터넷)
- 공격 시: 긴급 대응을 위한 위성 통신 백업
- 고립 시: 오프라인 보안 정책 자동 적용
- DDoS 시: 트래픽 분산 및 우회 경로 활성화
"""

import json
import os
import platform
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List

# 음성 합성
try:
    import pyttsx3
    TTS_OK = True
except ImportError:
    TTS_OK = False


@dataclass
class SecurityThreat:
    """보안 위협 정보"""
    threat_id: str
    type: str  # 'malware', 'ddos', 'intrusion', 'data_breach'
    severity: str  # 'low', 'medium', 'high', 'critical'
    source_ip: str
    target: str
    description: str
    detected_time: str
    status: str  # 'detected', 'analyzing', 'blocked', 'resolved'
    connection_type: str  # 탐지 시 사용된 연결


@dataclass
class SecurityPolicy:
    """보안 정책"""
    policy_id: str
    name: str
    description: str
    rules: List[Dict[str, Any]]
    active: bool
    connection_dependent: bool
    last_updated: str


class HybridCyberSecuritySystem:
    """하이브리드 사이버 보안 시스템"""

    def __init__(self):
        print("🛡️🌐" + "=" * 50 + "🛡️🌐")
        print("   소리새 하이브리드 사이버 보안 시스템")
        print("   Sorisae Hybrid Cyber Security System")
        print("🛡️🌐" + "=" * 50 + "🛡️🌐")
        print()

        # 시스템 상태
        self.active = True
        self.monitoring = False
        self.security_level = 'normal'  # 'normal', 'elevated', 'high', 'critical'

        # 위협 관리
        self.threats: List[SecurityThreat] = []
        self.blocked_ips: set = set()
        self.security_policies: Dict[str, SecurityPolicy] = {}

        # 하이브리드 연결 관리
        self.connection_manager = None
        self.current_connection = 'terrestrial'
        self.connection_quality = 'good'
        self.attack_detected = False

        # 데이터 저장
        self.data_dir = "hybrid_security_data"
        os.makedirs(self.data_dir, exist_ok=True)

        # 음성 엔진
        self.audio_io_enabled = os.environ.get("SORISAE_DISABLE_AUDIO_IO", "0") != "1"
        self.tts = None
        if TTS_OK and self.audio_io_enabled:
            try:
                self.tts = pyttsx3.init()
                self.setup_voice()
            except Exception as e:
                print(f"⚠️ 하이브리드 보안 TTS 비활성화: {e}")
        elif TTS_OK:
            print("ℹ️ 하이브리드 보안 헤드리스 오디오 모드")

        # 보안 시스템 초기화
        self.initialize_hybrid_connection()
        self.initialize_security_policies()
        self.start_monitoring()

        print("✅ 하이브리드 보안 시스템 준비 완료!")
        self.speak("하이브리드 사이버 보안 시스템이 활성화되었습니다!")

    def setup_voice(self):
        """음성 설정"""
        if TTS_OK and self.tts:
            self.tts.setProperty('rate', 200)
            self.tts.setProperty('volume', 0.9)

    def speak(self, text: str):
        """음성 출력"""
        if TTS_OK and self.audio_io_enabled and self.tts:

            def _speak():
                try:
                    self.tts.say(text)
                    self.tts.runAndWait()
                except Exception:
                    pass
            threading.Thread(target=_speak, daemon=True).start()
        print(f"🗣️ {text}")

    def initialize_hybrid_connection(self):
        """하이브리드 연결 초기화"""
        try:
            # 통합 하이브리드 시스템 연결
            from sorisae_integrated_hybrid_system import SorisaeIntegratedHybridSystem
            self.connection_manager = SorisaeIntegratedHybridSystem()
            self.current_connection = self.connection_manager.current_primary
            print("🌐 통합 하이브리드 시스템 연결 완료")
        except ImportError:
            try:
                # 기존 하이브리드 인터넷 시스템 연결
                from hybrid_internet_system import HybridInternetManager
                self.connection_manager = HybridInternetManager()
                print("🌐 하이브리드 인터넷 시스템 연결 완료")
            except ImportError:
                print("⚠️ 하이브리드 연결 시스템을 찾을 수 없음 - 독립 모드로 작동")
                self.connection_manager = None

    def initialize_security_policies(self):
        """보안 정책 초기화"""
        print("🛡️ 보안 정책 초기화 중...")

        # 기본 보안 정책들
        policies = {
            'ddos_protection': SecurityPolicy(
                policy_id='ddos_protection',
                name='DDoS 방어',
                description='DDoS 공격 탐지 및 차단',
                rules=[
                    {'type': 'rate_limit', 'max_requests': 100, 'time_window': 60},
                    {'type': 'ip_blacklist', 'suspicious_ips': []},
                    {'type': 'traffic_analysis', 'anomaly_threshold': 0.8}
                ],
                active=True,
                connection_dependent=False,
                last_updated=datetime.now().isoformat()
            ),

            'intrusion_detection': SecurityPolicy(
                policy_id='intrusion_detection',
                name='침입 탐지',
                description='무단 접근 시도 탐지',
                rules=[
                    {'type': 'port_scan_detection', 'threshold': 10},
                    {'type': 'failed_login_monitoring', 'max_attempts': 5},
                    {'type': 'file_integrity_check', 'critical_files': []}
                ],
                active=True,
                connection_dependent=False,
                last_updated=datetime.now().isoformat()
            ),

            'malware_protection': SecurityPolicy(
                policy_id='malware_protection',
                name='악성코드 방어',
                description='악성코드 탐지 및 격리',
                rules=[
                    {'type': 'real_time_scan', 'enabled': True},
                    {'type': 'signature_update', 'auto_update': True},
                    {'type': 'heuristic_analysis', 'sensitivity': 'medium'}
                ],
                active=True,
                connection_dependent=True,  # 온라인 업데이트 필요
                last_updated=datetime.now().isoformat()
            ),

            'satellite_security': SecurityPolicy(
                policy_id='satellite_security',
                name='위성 연결 보안',
                description='위성 인터넷 사용 시 보안 강화',
                rules=[
                    {'type': 'encryption', 'level': 'high'},
                    {'type': 'vpn_mandatory', 'enabled': True},
                    {'type': 'data_compression', 'enabled': True}
                ],
                active=False,  # 위성 연결 시에만 활성화
                connection_dependent=True,
                last_updated=datetime.now().isoformat()
            )
        }

        self.security_policies.update(policies)
        print(f"✅ {len(policies)}개 보안 정책 로드 완료")

    def start_monitoring(self):
        """보안 모니터링 시작"""
        if self.monitoring:
            return

        self.monitoring = True
        print("🔄 하이브리드 보안 모니터링 시작")

        # 여러 모니터링 스레드 시작
        threading.Thread(target=self.network_monitor_loop, daemon=True).start()
        threading.Thread(target=self.threat_analysis_loop, daemon=True).start()
        threading.Thread(target=self.connection_security_loop, daemon=True).start()

    def network_monitor_loop(self):
        """네트워크 모니터링 루프"""
        while self.monitoring and self.active:
            try:
                # 네트워크 트래픽 분석
                self.analyze_network_traffic()

                # DDoS 공격 탐지
                self.detect_ddos_attack()

                # 포트 스캔 탐지
                self.detect_port_scanning()

                time.sleep(5)  # 5초마다 체크

            except Exception as e:
                print(f"⚠️ 네트워크 모니터링 오류: {e}")
                time.sleep(30)

    def threat_analysis_loop(self):
        """위협 분석 루프"""
        while self.monitoring and self.active:
            try:
                # 위협 정보 업데이트 (연결 상태에 따라)
                self.update_threat_intelligence()

                # 기존 위협 재분석
                self.reanalyze_threats()

                # 보안 정책 업데이트
                self.update_security_policies()

                time.sleep(60)  # 1분마다 체크

            except Exception as e:
                print(f"⚠️ 위협 분석 오류: {e}")
                time.sleep(120)

    def connection_security_loop(self):
        """연결 보안 루프"""
        while self.monitoring and self.active:
            try:
                # 연결 상태 확인
                self.update_connection_status()

                # 연결별 보안 정책 적용
                self.apply_connection_security()

                # 공격 상황 시 연결 전환
                if self.attack_detected:
                    self.handle_attack_scenario()

                time.sleep(30)  # 30초마다 체크

            except Exception as e:
                print(f"⚠️ 연결 보안 오류: {e}")
                time.sleep(60)

    def update_connection_status(self):
        """연결 상태 업데이트"""
        if self.connection_manager:
            try:
                old_connection = self.current_connection

                if hasattr(self.connection_manager, 'current_primary'):
                    self.current_connection = self.connection_manager.current_primary

                if hasattr(self.connection_manager, 'get_connection_quality'):
                    self.connection_quality = self.connection_manager.get_connection_quality()

                # 연결 변경 시 보안 정책 재조정
                if old_connection != self.current_connection:
                    print(f"🔄 보안 연결 변경: {old_connection} → {self.current_connection}")
                    self.adjust_security_for_connection()

            except Exception as e:
                print(f"연결 상태 업데이트 오류: {e}")

    def adjust_security_for_connection(self):
        """연결별 보안 조정"""
        if self.current_connection == 'satellite':
            # 위성 연결 시 보안 강화
            self.security_policies['satellite_security'].active = True
            self.security_level = 'elevated'
            print("🛰️ 위성 연결 보안 모드 활성화")
            self.speak("위성 연결로 전환하여 보안을 강화합니다.")

        elif self.current_connection == 'mobile':
            # 모바일 연결 시 중간 보안
            self.security_policies['satellite_security'].active = False
            self.security_level = 'normal'
            print("📱 모바일 연결 보안 모드")

        elif self.current_connection == 'terrestrial':
            # 일반 연결 시 표준 보안
            self.security_policies['satellite_security'].active = False
            self.security_level = 'normal'
            print("🌐 일반 연결 보안 모드")

        else:
            # 오프라인 시 높은 보안
            self.security_level = 'high'
            print("📱 오프라인 고보안 모드")

    def apply_connection_security(self):
        """현재 연결/보안 레벨에 맞는 정책 적용"""
        # 연결별 보안 모드 기본값을 먼저 동기화
        self.adjust_security_for_connection()

        # 연결 유형에 따라 정책별 룰 강도를 조정
        ddos_policy = self.security_policies.get('ddos_protection')
        intrusion_policy = self.security_policies.get('intrusion_detection')
        malware_policy = self.security_policies.get('malware_protection')
        satellite_policy = self.security_policies.get('satellite_security')

        if ddos_policy:
            for rule in ddos_policy.rules:
                if rule.get('type') == 'rate_limit':
                    if self.current_connection == 'satellite' or self.security_level in ('high', 'critical'):
                        rule['max_requests'] = 50
                    else:
                        rule['max_requests'] = 100

        if intrusion_policy:
            for rule in intrusion_policy.rules:
                if rule.get('type') == 'failed_login_monitoring':
                    if self.security_level == 'critical':
                        rule['max_attempts'] = 3
                    elif self.security_level == 'high':
                        rule['max_attempts'] = 4
                    else:
                        rule['max_attempts'] = 5

        if malware_policy:
            for rule in malware_policy.rules:
                if rule.get('type') == 'heuristic_analysis':
                    if self.security_level in ('high', 'critical') or self.current_connection == 'satellite':
                        rule['sensitivity'] = 'high'
                    else:
                        rule['sensitivity'] = 'medium'

        if satellite_policy:
            satellite_policy.active = self.current_connection == 'satellite'

        # 연결 관리자가 보안 프로파일 API를 제공하면 같이 동기화
        if self.connection_manager and hasattr(self.connection_manager, 'apply_security_profile'):
            try:
                self.connection_manager.apply_security_profile(
                    {
                        'security_level': self.security_level,
                        'connection_type': self.current_connection,
                        'blocked_ip_count': len(self.blocked_ips),
                    }
                )
            except Exception as e:
                print(f"연결 보안 프로파일 동기화 실패: {e}")

    def analyze_network_traffic(self):
        """네트워크 트래픽 분석"""
        # 실제로는 네트워크 패킷 캡처 및 분석
        # 여기서는 시뮬레이션
        import random

        # 랜덤하게 의심스러운 활동 생성
        if random.random() < 0.05:  # 5% 확률
            suspicious_ip = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
            threat_type = random.choice(['port_scan', 'brute_force', 'unusual_traffic'])

            if threat_type == 'ddos' or random.random() < 0.1:
                self.create_threat_alert(threat_type, suspicious_ip)

    def detect_ddos_attack(self):
        """DDoS 공격 탐지"""
        # 실제로는 트래픽 패턴 분석
        # 시뮬레이션: 랜덤하게 DDoS 공격 탐지
        import random

        if random.random() < 0.02:  # 2% 확률로 DDoS 탐지
            attacker_ip = ".".join(
                [
                    str(random.randint(1, 223)),
                    str(random.randint(1, 254)),
                    str(random.randint(1, 254)),
                    str(random.randint(1, 254)),
                ]
            )
            self.handle_ddos_attack(attacker_ip)

    def detect_port_scanning(self):
        """포트 스캔 탐지"""
        # 시뮬레이션: 포트 스캔 탐지
        import random

        if random.random() < 0.03:  # 3% 확률
            scanner_ip = ".".join(
                [
                    str(random.randint(1, 223)),
                    str(random.randint(1, 254)),
                    str(random.randint(1, 254)),
                    str(random.randint(1, 254)),
                ]
            )
            self.create_threat_alert('port_scan', scanner_ip)

    def create_threat_alert(self, threat_type: str, source_ip: str):
        """위협 알림 생성"""
        threat = SecurityThreat(
            threat_id=f"THR_{int(time.time() * 1000)}",
            type=threat_type,
            severity=self.calculate_threat_severity(threat_type),
            source_ip=source_ip,
            target='localhost',
            description=f"{threat_type} 활동이 {source_ip}에서 탐지됨",
            detected_time=datetime.now().isoformat(),
            status='detected',
            connection_type=self.current_connection
        )

        self.threats.append(threat)
        self.handle_threat(threat)

    def calculate_threat_severity(self, threat_type: str) -> str:
        """위협 심각도 계산"""
        severity_map = {
            'ddos': 'critical',
            'brute_force': 'high',
            'port_scan': 'medium',
            'malware': 'high',
            'intrusion': 'critical',
            'unusual_traffic': 'low'
        }
        return severity_map.get(threat_type, 'medium')

    def handle_threat(self, threat: SecurityThreat):
        """위협 처리"""
        print(f"🚨 보안 위협 탐지: {threat.type} ({threat.severity})")
        print(f"   출처: {threat.source_ip}")
        print(f"   연결: {threat.connection_type}")

        # 심각도에 따른 대응
        if threat.severity == 'critical':
            self.handle_critical_threat(threat)
        elif threat.severity == 'high':
            self.handle_high_threat(threat)
        else:
            self.handle_medium_low_threat(threat)

    def handle_critical_threat(self, threat: SecurityThreat):
        """중대 위협 처리"""
        self.security_level = 'critical'
        self.attack_detected = True

        # IP 즉시 차단
        self.block_ip(threat.source_ip)

        # 긴급 알림
        self.speak(f"중대한 보안 위협이 탐지되었습니다. {threat.type} 공격입니다.")

        # 위성 연결로 긴급 전환 (가능한 경우)
        if self.current_connection != 'satellite':
            self.request_satellite_backup()

        threat.status = 'blocked'
        print(f"🛡️ 중대 위협 차단: {threat.source_ip}")

    def handle_high_threat(self, threat: SecurityThreat):
        """높은 위협 처리"""
        self.security_level = 'high'

        # IP 차단
        self.block_ip(threat.source_ip)

        # 추가 모니터링 강화
        print(f"⚠️ 높은 위협 탐지 - 모니터링 강화: {threat.source_ip}")
        threat.status = 'blocked'

    def handle_medium_low_threat(self, threat: SecurityThreat):
        """중간/낮은 위협 처리"""
        # 로깅 및 모니터링
        print(f"📋 위협 기록: {threat.type} from {threat.source_ip}")
        threat.status = 'analyzing'

    def handle_ddos_attack(self, attacker_ip: str):
        """DDoS 공격 처리"""
        print(f"🚨 DDoS 공격 탐지! 공격자: {attacker_ip}")

        # 즉시 차단
        self.block_ip(attacker_ip)

        # 트래픽 분산 및 우회
        self.activate_traffic_distribution()

        # 위성 백업 요청
        self.request_satellite_backup()

        # 긴급 알림
        self.speak("디도스 공격이 탐지되어 방어 체계를 활성화합니다.")

        # 위협 기록
        threat = SecurityThreat(
            threat_id=f"DDOS_{int(time.time())}",
            type='ddos',
            severity='critical',
            source_ip=attacker_ip,
            target='system',
            description=f"DDoS 공격 from {attacker_ip}",
            detected_time=datetime.now().isoformat(),
            status='blocking',
            connection_type=self.current_connection
        )
        self.threats.append(threat)

    def block_ip(self, ip_address: str):
        """IP 주소 차단"""
        if ip_address not in self.blocked_ips:
            self.blocked_ips.add(ip_address)

            # 실제로는 방화벽 규칙 추가
            # 여기서는 시뮬레이션
            print(f"🚫 IP 차단: {ip_address}")

            # Windows 방화벽 규칙 추가 (실제 환경에서)
            if platform.system() == "Windows":
                try:
                    # cmd = f'netsh advfirewall firewall add rule name="Block {ip_address}" dir=in action=block remoteip={ip_address}'
                    # subprocess.run(cmd, shell=True, capture_output=True)
                    pass
                except Exception as e:
                    print(f"방화벽 규칙 추가 실패: {e}")

    def activate_traffic_distribution(self):
        """트래픽 분산 활성화"""
        print("🔄 트래픽 분산 시스템 활성화")

        # 다중 연결 경로 활용
        if self.connection_manager:
            try:
                # 모든 가용 연결 활성화
                if hasattr(self.connection_manager, 'activate_all_connections'):
                    self.connection_manager.activate_all_connections()
                print("🌐 다중 연결 경로 활성화")
            except Exception as e:
                print(f"트래픽 분산 오류: {e}")

    def request_satellite_backup(self):
        """위성 백업 요청"""
        if self.connection_manager and self.current_connection != 'satellite':
            try:
                print("🛰️ 위성 백업 연결 요청")

                if hasattr(self.connection_manager, 'emergency_satellite_switch'):
                    self.connection_manager.emergency_satellite_switch()
                elif hasattr(self.connection_manager, 'set_primary_connection'):
                    self.connection_manager.set_primary_connection('satellite')

                self.speak("보안 위협으로 인해 위성 백업 연결을 활성화합니다.")

            except Exception as e:
                print(f"위성 백업 요청 실패: {e}")

    def handle_attack_scenario(self):
        """공격 시나리오 처리"""
        # 공격 상황에서의 자동 대응
        if self.security_level == 'critical':
            # 모든 보안 정책 최대 강화
            for policy in self.security_policies.values():
                policy.active = True

            # 연결 보안 강화
            if self.current_connection == 'terrestrial':
                print("🛰️ 공격 상황 - 위성 연결로 긴급 전환")
                self.request_satellite_backup()

    def update_threat_intelligence(self):
        """위협 정보 업데이트"""
        # 연결 상태에 따라 위협 정보 업데이트
        if self.current_connection in ['terrestrial', 'mobile', 'satellite']:
            # 온라인 위협 정보 업데이트
            try:
                # 실제로는 보안 업체 API 호출
                print("🔄 위협 정보 업데이트 중...")
                # 시뮬레이션
                time.sleep(1)
                print("✅ 위협 정보 업데이트 완료")
            except Exception as e:
                print(f"위협 정보 업데이트 실패: {e}")
        else:
            # 오프라인 시 로컬 정보 사용
            print("📱 오프라인 모드 - 로컬 위협 정보 사용")

    def reanalyze_threats(self):
        """기존 위협 재분석"""
        active_threats = [t for t in self.threats if t.status in ['detected', 'analyzing']]

        for threat in active_threats:
            # 위험도 재평가
            if threat.type == 'ddos' and (datetime.now() - datetime.fromisoformat(threat.detected_time)).seconds > 300:
                # 5분 경과한 DDoS는 해결된 것으로 간주
                threat.status = 'resolved'
                print(f"✅ 위협 해결: {threat.threat_id}")

    def update_security_policies(self):
        """보안 정책 업데이트"""
        # 현재 연결과 위협 수준에 맞게 정책 조정
        for policy_id, policy in self.security_policies.items():
            if policy.connection_dependent and self.current_connection == 'offline':
                # 오프라인 시 온라인 의존적 정책 비활성화
                policy.active = False
            elif self.security_level == 'critical':
                # 중대 위협 시 모든 정책 활성화
                policy.active = True

    def voice_command_handler(self, command: str) -> str:
        """음성 명령 처리"""
        cmd = command.lower()

        if '보안' in cmd and '상태' in cmd:
            return self.get_security_status()

        elif '위협' in cmd and '스캔' in cmd:
            return self.start_threat_scan()

        elif '방화벽' in cmd:
            if '켜' in cmd:
                return self.enable_firewall()
            elif '꺼' in cmd:
                return self.disable_firewall()

        elif '차단' in cmd and '해제' in cmd:
            return self.unblock_recent_ips()

        elif '비상' in cmd or '긴급' in cmd:
            return self.activate_emergency_mode()

        elif '보안' in cmd and '강화' in cmd:
            return self.enhance_security()

        return "보안 명령을 이해하지 못했습니다."

    def get_security_status(self) -> str:
        """보안 상태 보고"""
        active_threats = len([t for t in self.threats if t.status in ['detected', 'analyzing']])
        blocked_count = len(self.blocked_ips)

        status = f"\n🛡️ 하이브리드 보안 시스템 상태\n"
        status += f"📡 현재 연결: {self.current_connection}\n"
        status += f"🚨 보안 수준: {self.security_level}\n"
        status += f"⚠️ 활성 위협: {active_threats}개\n"
        status += f"🚫 차단된 IP: {blocked_count}개\n"
        status += f"📋 전체 위협 기록: {len(self.threats)}개\n"

        # 활성 보안 정책
        active_policies = [p.name for p in self.security_policies.values() if p.active]
        status += f"🛡️ 활성 정책: {', '.join(active_policies)}\n"

        return status

    def start_threat_scan(self) -> str:
        """위협 스캔 시작"""
        print("🔍 전체 보안 스캔 시작...")
        self.speak("보안 스캔을 시작합니다.")

        # 시뮬레이션
        time.sleep(2)

        # 가상의 스캔 결과
        import random
        found_threats = random.randint(0, 3)

        if found_threats == 0:
            result = "✅ 스캔 완료: 위협이 발견되지 않았습니다."
        else:
            result = f"⚠️ 스캔 완료: {found_threats}개의 잠재적 위협이 발견되었습니다."

            # 가상 위협 생성
            for i in range(found_threats):
                fake_ip = f"192.168.1.{random.randint(100, 200)}"
                self.create_threat_alert('malware', fake_ip)

        self.speak("보안 스캔이 완료되었습니다.")
        return result

    def enable_firewall(self) -> str:
        """방화벽 활성화"""
        print("🛡️ 방화벽 활성화")
        self.speak("방화벽을 활성화합니다.")
        return "방화벽이 활성화되었습니다."

    def disable_firewall(self) -> str:
        """방화벽 비활성화"""
        print("⚠️ 방화벽 비활성화")
        self.speak("방화벽을 비활성화합니다.")
        return "방화벽이 비활성화되었습니다."

    def unblock_recent_ips(self) -> str:
        """최근 차단 IP 해제"""
        if self.blocked_ips:
            # 최근 5개 IP 해제
            recent_ips = list(self.blocked_ips)[-5:]
            for ip in recent_ips:
                self.blocked_ips.remove(ip)

            result = f"{len(recent_ips)}개 IP 차단을 해제했습니다."
            self.speak("차단된 아이피 주소를 해제했습니다.")
            return result
        else:
            return "차단된 IP가 없습니다."

    def activate_emergency_mode(self) -> str:
        """비상 모드 활성화"""
        self.security_level = 'critical'
        self.attack_detected = True

        # 모든 보안 정책 활성화
        for policy in self.security_policies.values():
            policy.active = True

        # 위성 백업 요청
        self.request_satellite_backup()

        self.speak("비상 보안 모드가 활성화되었습니다.")
        return "🚨 비상 보안 모드 활성화 완료"

    def enhance_security(self) -> str:
        """보안 강화"""
        self.security_level = 'high'

        # 추가 보안 규칙 적용
        for policy in self.security_policies.values():
            policy.active = True

        self.speak("보안을 강화했습니다.")
        return "🛡️ 보안 강화 모드 활성화"

    def save_security_log(self):
        """보안 로그 저장"""
        try:
            security_data = {
                'threats': [asdict(t) for t in self.threats],
                'blocked_ips': list(self.blocked_ips),
                'security_level': self.security_level,
                'current_connection': self.current_connection,
                'timestamp': datetime.now().isoformat()
            }

            filename = os.path.join(self.data_dir, f'security_log_{datetime.now().strftime("%Y%m%d")}.json')
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(security_data, f, indent=2, ensure_ascii=False)

            print("💾 보안 로그 저장 완료")
        except Exception as e:
            print(f"⚠️ 보안 로그 저장 실패: {e}")

    def shutdown(self):
        """시스템 종료"""
        print("🛑 하이브리드 보안 시스템 종료 중...")

        self.active = False
        self.monitoring = False

        # 보안 로그 저장
        self.save_security_log()

        # 차단된 IP 정리 (선택적)
        print(f"🚫 {len(self.blocked_ips)}개 IP 차단 유지")

        print("✅ 하이브리드 보안 시스템 종료 완료")
        self.speak("보안 시스템을 안전하게 종료했습니다.")


def main():
    """메인 실행"""
    security_system = HybridCyberSecuritySystem()

    try:
        while security_system.active:
            print("\n🛡️ 하이브리드 보안 시스템 명령:")
            print("1. '보안 상태' - 시스템 상태 확인")
            print("2. '위협 스캔' - 전체 보안 스캔")
            print("3. '비상 모드' - 긴급 보안 강화")
            print("4. '보안 강화' - 보안 수준 향상")
            print("5. 'quit' - 종료")

            user_input = input("\n명령 입력: ").strip()

            if user_input.lower() in ['quit', 'exit', '종료']:
                break
            else:
                result = security_system.voice_command_handler(user_input)
                print(result)

    except KeyboardInterrupt:
        print("\n사용자가 시스템을 중단했습니다.")

    finally:
        security_system.shutdown()


if __name__ == "__main__":
    main()
