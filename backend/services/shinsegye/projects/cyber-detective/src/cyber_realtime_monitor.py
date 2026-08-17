#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CYBER-Detective AI 실시간 모니터링 시스템
=====================================

24시간 실시간으로 사이버범죄를 탐지하고 대응하는
지능형 모니터링 시스템입니다.

주요 기능:
- 실시간 네트워크 트래픽 모니터링
- 불법 콘텐츠 자동 탐지
- 위험도 기반 알림 시스템
- 자동 대응 조치
"""

import asyncio
import datetime
import random
from collections import deque
from typing import Dict, List


class RealTimeMonitor:
    def __init__(self):
        self.monitoring_active = False
        self.alert_queue = deque(maxlen=100)
        self.threat_history = []
        self.monitoring_stats = {
            "total_scanned": 0,
            "threats_detected": 0,
            "high_risk_threats": 0,
            "start_time": None
        }

        # 위험 패턴 데이터베이스
        self.threat_patterns = {
            "마약 거래": {
                "keywords": ["떨", "빙두", "몰리", "엑스타시", "대마초", "코카인"],
                "patterns": [r"\d+g", "순도", "직거래", "급처"],
                "risk_level": 10
            },
            "무기 거래": {
                "keywords": ["총", "권총", "폭탄", "화약", "실탄"],
                "patterns": ["개당", "판매", "직거래"],
                "risk_level": 10
            },
            "개인정보 거래": {
                "keywords": ["주민번호", "신분증", "여권", "계좌번호"],
                "patterns": ["판매", "대량", "실명"],
                "risk_level": 9
            },
            "사기": {
                "keywords": ["빠른수익", "무조건", "보장", "100%"],
                "patterns": [r"\d+%", "투자", "수익"],
                "risk_level": 8
            }
        }

    async def start_monitoring(self, duration_minutes: int = 60):
        """실시간 모니터링 시작"""
        print("🚔 CYBER-Detective AI 실시간 모니터링 시작")
        print("=" * 60)

        self.monitoring_active = True
        self.monitoring_stats["start_time"] = datetime.datetime.now()

        # 병렬 모니터링 태스크 시작
        tasks = [
            self.network_traffic_monitor(),
            self.content_scanner(),
            self.threat_analyzer(),
            self.alert_processor()
        ]

        # 지정된 시간 동안 모니터링
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=duration_minutes * 60
            )
        except asyncio.TimeoutError:
            print("\n⏰ 모니터링 시간 종료")
        finally:
            self.monitoring_active = False
            await self.generate_monitoring_report()

    async def network_traffic_monitor(self):
        """네트워크 트래픽 모니터링"""
        print("🌐 네트워크 트래픽 모니터링 시작...")

        suspicious_activities = [
            "포트 스캔 시도",
            "DDoS 공격 시도",
            "데이터 유출 시도",
            "악성코드 다운로드",
            "봇넷 통신",
            "암호화폐 채굴"
        ]

        while self.monitoring_active:
            # 무작위 네트워크 이벤트 시뮬레이션
            if random.random() < 0.3:  # 30% 확률로 이벤트 발생
                activity = random.choice(suspicious_activities)
                source_ip = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
                target = f"external-{random.randint(1000, 9999)}.com"
                risk_level = random.randint(6, 10)

                threat_data = {
                    "type": "network_threat",
                    "activity": activity,
                    "source_ip": source_ip,
                    "target": target,
                    "risk_level": risk_level,
                    "timestamp": datetime.datetime.now().isoformat()
                }

                await self.add_threat_alert(threat_data)
                self.monitoring_stats["total_scanned"] += 1

                if risk_level >= 8:
                    self.monitoring_stats["high_risk_threats"] += 1

            await asyncio.sleep(5)  # 5초마다 체크

    async def content_scanner(self):
        """콘텐츠 스캐너"""
        print("📝 콘텐츠 스캐너 시작...")

        # 샘플 의심 콘텐츠
        suspicious_contents = [
            "떨 20g 판매합니다. 순도 98% 보장. 직거래만",
            "권총 판매. 개당 300만원. 실탄 포함",
            "주민번호 1000개 판매. 실명인증 가능한 것만",
            "투자 보장! 100% 수익! 원금 보장!",
            "신분증 제작해드립니다. 완벽한 위조",
            "계좌 판매. 대포통장 50개. 즉시 사용 가능"
        ]

        while self.monitoring_active:
            if random.random() < 0.2:  # 20% 확률로 의심 콘텐츠 발견
                content = random.choice(suspicious_contents)

                # 콘텐츠 분석
                detected_threats = self.analyze_content(content)

                if detected_threats:
                    threat_data = {
                        "type": "content_threat",
                        "content": content,
                        "detected_patterns": detected_threats,
                        "timestamp": datetime.datetime.now().isoformat()
                    }

                    await self.add_threat_alert(threat_data)
                    self.monitoring_stats["threats_detected"] += 1

            await asyncio.sleep(8)  # 8초마다 체크

    def analyze_content(self, content: str) -> List[Dict]:
        """콘텐츠 분석 및 위협 탐지"""
        detected_threats = []

        for threat_type, threat_info in self.threat_patterns.items():
            # 키워드 매칭
            for keyword in threat_info["keywords"]:
                if keyword in content:
                    detected_threats.append({
                        "threat_type": threat_type,
                        "matched_keyword": keyword,
                        "risk_level": threat_info["risk_level"]
                    })
                    break

        return detected_threats

    async def threat_analyzer(self):
        """위협 분석기"""
        print("🔬 위협 분석기 시작...")

        while self.monitoring_active:
            # 주기적으로 위협 패턴 분석
            if len(self.threat_history) > 10:
                await self.analyze_threat_patterns()

            await asyncio.sleep(30)  # 30초마다 분석

    async def analyze_threat_patterns(self):
        """위협 패턴 분석"""
        recent_threats = self.threat_history[-10:]

        # 위협 유형별 통계
        threat_counts = {}
        for threat in recent_threats:
            threat_type = threat.get("type", "unknown")
            threat_counts[threat_type] = threat_counts.get(threat_type, 0) + 1

        # 급증하는 위협 유형 감지
        for threat_type, count in threat_counts.items():
            if count >= 5:  # 10개 중 5개 이상이면 급증
                print(f"⚠️  {threat_type} 위협 급증 감지! (빈도: {count}/10)")

    async def alert_processor(self):
        """알림 처리기"""
        print("🚨 알림 처리기 시작...")

        while self.monitoring_active:
            if self.alert_queue:
                alert = self.alert_queue.popleft()
                await self.process_alert(alert)

            await asyncio.sleep(2)  # 2초마다 알림 처리

    async def process_alert(self, alert: Dict):
        """알림 처리"""
        risk_level = alert.get("risk_level", 0)
        threat_type = alert.get("type", "unknown")

        # 위험도별 처리
        if risk_level >= 9:
            print(f"🚨 긴급 위협 감지! {threat_type} (위험도: {risk_level}/10)")
            await self.emergency_response(alert)
        elif risk_level >= 7:
            print(f"⚠️  중위험 위협 감지: {threat_type} (위험도: {risk_level}/10)")
        else:
            print(f"ℹ️  저위험 활동 감지: {threat_type} (위험도: {risk_level}/10)")

        # 위협 히스토리에 추가
        self.threat_history.append(alert)

    async def emergency_response(self, alert: Dict):
        """긴급 대응 조치"""
        print("🚑 긴급 대응 조치 실행 중...")

        # 시뮬레이션 대응 조치
        response_actions = [
            "IP 주소 자동 차단",
            "관련 계정 일시 정지",
            "수사기관 자동 신고",
            "증거 자료 자동 보전",
            "관련 네트워크 격리"
        ]

        for action in response_actions[:2]:  # 처음 2개 조치만 실행
            print(f"   📋 {action} 실행 완료")
            await asyncio.sleep(1)

    async def add_threat_alert(self, threat_data: Dict):
        """위협 알림 추가"""
        self.alert_queue.append(threat_data)

    async def generate_monitoring_report(self):
        """모니터링 보고서 생성"""
        print("\n" + "=" * 60)
        print("📊 실시간 모니터링 보고서")
        print("=" * 60)

        duration = datetime.datetime.now() - self.monitoring_stats["start_time"]

        print(f"📅 모니터링 기간: {duration}")
        print(f"🔍 총 스캔 건수: {self.monitoring_stats['total_scanned']:,}")
        print(f"🚨 탐지된 위협: {self.monitoring_stats['threats_detected']:,}")
        print(f"⛔ 고위험 위협: {self.monitoring_stats['high_risk_threats']:,}")

        # 위협 유형별 통계
        if self.threat_history:
            threat_types = {}
            for threat in self.threat_history:
                t_type = threat.get("type", "unknown")
                threat_types[t_type] = threat_types.get(t_type, 0) + 1

            print("\n📈 위협 유형별 통계:")
            for t_type, count in sorted(threat_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {t_type}: {count}건")

        print("\n✅ 모니터링 완료!")


class MonitoringDashboard:
    """모니터링 대시보드"""

    def __init__(self):
        self.monitor = RealTimeMonitor()

    def show_dashboard(self):
        """대시보드 표시"""
        print("🖥️  CYBER-Detective AI 모니터링 대시보드")
        print("=" * 60)
        print("1. 실시간 모니터링 시작 (5분)")
        print("2. 실시간 모니터링 시작 (10분)")
        print("3. 데모 모니터링 (1분)")
        print("4. 모니터링 통계 보기")
        print("5. 종료")
        print("-" * 60)

    async def run_dashboard(self):
        """대시보드 실행"""
        while True:
            self.show_dashboard()

            try:
                choice = input("선택하세요 (1-5): ").strip()

                if choice == "1":
                    await self.monitor.start_monitoring(5)
                elif choice == "2":
                    await self.monitor.start_monitoring(10)
                elif choice == "3":
                    await self.monitor.start_monitoring(1)
                elif choice == "4":
                    self.show_statistics()
                elif choice == "5":
                    print("👋 CYBER-Detective AI 모니터링 종료")
                    break
                else:
                    print("❌ 잘못된 선택입니다.")

            except KeyboardInterrupt:
                print("\n👋 사용자가 모니터링을 중단했습니다.")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")

    def show_statistics(self):
        """통계 표시"""
        print("\n📊 모니터링 통계")
        print("-" * 40)
        print(f"총 스캔: {self.monitor.monitoring_stats['total_scanned']}")
        print(f"위협 탐지: {self.monitor.monitoring_stats['threats_detected']}")
        print(f"고위험 위협: {self.monitor.monitoring_stats['high_risk_threats']}")
        print()


async def main():
    """메인 함수"""
    print("🚔 CYBER-Detective AI 실시간 모니터링 시스템")
    print("=" * 60)

    # 데모 모드로 1분간 모니터링
    monitor = RealTimeMonitor()
    await monitor.start_monitoring(1)  # 1분간 데모 모니터링

if __name__ == "__main__":
    asyncio.run(main())
