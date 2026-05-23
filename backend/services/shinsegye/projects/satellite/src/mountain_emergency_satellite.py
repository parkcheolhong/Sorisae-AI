#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏔️ 오지 산속 긴급 위성 인터넷 연결 시스템
Emergency Satellite Internet for Remote Mountain Areas

현재 위치: 오지 산속
상황: 일반 인터넷 불가, 위성 인터넷 필요
목적: 긴급 통신, 안전 확보, 외부 연락
"""

import json
import platform
import subprocess
from datetime import datetime


class MountainEmergencySatellite:
    """산속 긴급 위성 인터넷 시스템"""

    def __init__(self):
        print("🏔️" + "=" * 60 + "🏔️")
        print("   오지 산속 긴급 위성 인터넷 연결 시스템")
        print("   Emergency Satellite Internet System")
        print("🏔️" + "=" * 60 + "🏔️")
        print()

        self.location = "오지 산속"
        self.emergency_mode = True
        self.available_satellites = []
        self.current_connection = None

        print("📍 현재 위치: 오지 산속")
        print("🚨 긴급 모드 활성화")
        print("🛰️ 위성 검색 시작...")
        print()

    def scan_available_networks(self):
        """사용 가능한 네트워크 스캔"""
        print("🔍 네트워크 스캔 중...")

        # Windows WiFi 네트워크 스캔
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'],
                                        capture_output=True, text=True, encoding='cp949')

                print("📶 감지된 WiFi 네트워크:")
                if result.stdout:
                    lines = result.stdout.split('\n')
                    wifi_count = 0
                    for line in lines:
                        if '모든 사용자 프로필' in line or 'All User Profile' in line:
                            network_name = line.split(':')[-1].strip()
                            if network_name:
                                print(f"   📶 {network_name}")
                                wifi_count += 1

                    if wifi_count == 0:
                        print("   ❌ 사용 가능한 WiFi 없음")
                else:
                    print("   ❌ WiFi 어댑터 없음 또는 비활성화")

        except Exception as e:
            print(f"   ⚠️ 네트워크 스캔 오류: {e}")

        print()

        # 위성 인터넷 서비스 확인
        satellite_services = [
            {
                'name': 'Starlink',
                'frequency': '10.7-12.7 GHz (Ku-band)',
                'coverage': '전 세계 (극지방 제외)',
                'status': '상용 서비스'
            },
            {
                'name': 'Iridium',
                'frequency': '1616-1626.5 MHz (L-band)',
                'coverage': '전 세계 (극지방 포함)',
                'status': '위성 전화/데이터'
            },
            {
                'name': 'Inmarsat',
                'frequency': '1525-1559 MHz (L-band)',
                'coverage': '전 세계 (극지방 제외)',
                'status': '위성 통신'
            }
        ]

        print("🛰️ 사용 가능한 위성 서비스:")
        for service in satellite_services:
            print(f"   🛰️ {service['name']}")
            print(f"      주파수: {service['frequency']}")
            print(f"      커버리지: {service['coverage']}")
            print(f"      상태: {service['status']}")
            print()

    def check_internet_connectivity(self):
        """인터넷 연결 상태 확인"""
        print("🌐 인터넷 연결 테스트...")

        test_sites = [
            'google.com',
            'naver.com',
            'daum.net',
            '1.1.1.1'  # Cloudflare DNS
        ]

        connected_sites = []

        for site in test_sites:
            try:
                if platform.system() == "Windows":
                    result = subprocess.run(['ping', '-n', '1', '-w', '3000', site],
                                            capture_output=True, text=True)
                else:
                    result = subprocess.run(['ping', '-c', '1', '-W', '3', site],
                                            capture_output=True, text=True)

                if result.returncode == 0:
                    connected_sites.append(site)
                    print(f"   ✅ {site} - 연결 성공")
                else:
                    print(f"   ❌ {site} - 연결 실패")

            except Exception as e:
                print(f"   ⚠️ {site} - 테스트 오류: {e}")

        print()

        if connected_sites:
            print(f"🎉 인터넷 연결 확인! ({len(connected_sites)}/{len(test_sites)} 사이트)")
            self.current_connection = "기존 인터넷"
            return True
        else:
            print("❌ 인터넷 연결 없음 - 위성 인터넷 필요!")
            return False

    def emergency_contact_info(self):
        """긴급 연락처 정보"""
        print("🚨 긴급 연락 정보")
        print("-" * 40)
        print("📞 긴급전화:")
        print("   119 - 소방서 (화재, 응급의료)")
        print("   112 - 경찰서 (사고, 신고)")
        print("   1339 - 응급의료정보센터")
        print()
        print("🏔️ 산악 구조:")
        print("   119 - 산악 구조대")
        print("   지역 소방서 - 산악 안전")
        print()
        print("📡 위성 통신 업체:")
        print("   KT 위성통신: 1588-0010")
        print("   SK 위성통신: 1588-0011")
        print()

    def satellite_internet_guide(self):
        """위성 인터넷 사용 가이드"""
        print("📖 오지에서 위성 인터넷 사용 가이드")
        print("=" * 50)
        print()

        print("1️⃣ Starlink (추천):")
        print("   💰 비용: 월 99$ + 장비 599$")
        print("   📶 속도: 100-200 Mbps")
        print("   🌍 커버리지: 전 세계 대부분")
        print("   🔧 설치: 간단 (전원만 연결)")
        print()

        print("2️⃣ 위성 전화 + 데이터:")
        print("   📱 Iridium 위성폰: 긴급용")
        print("   💰 비용: 분당 7-15$")
        print("   📶 속도: 2.4-384 kbps")
        print("   🌍 커버리지: 전 세계 100%")
        print()

        print("3️⃣ 휴대용 위성 인터넷:")
        print("   📡 BGAN 터미널")
        print("   💰 비용: MB당 5-15$")
        print("   📶 속도: 최대 492 kbps")
        print("   🎒 휴대 가능")
        print()

    def create_emergency_plan(self):
        """긴급 계획 생성"""
        plan = {
            "location": "오지 산속",
            "timestamp": datetime.now().isoformat(),
            "emergency_contacts": [
                {"service": "소방서", "number": "119"},
                {"service": "경찰서", "number": "112"},
                {"service": "응급의료", "number": "1339"}
            ],
            "satellite_options": [
                {
                    "name": "Starlink",
                    "priority": 1,
                    "reason": "높은 속도, 비교적 저렴"
                },
                {
                    "name": "Iridium 위성폰",
                    "priority": 2,
                    "reason": "전 세계 커버리지, 긴급용"
                }
            ],
            "backup_plans": [
                "가까운 마을로 이동",
                "높은 지대에서 휴대폰 신호 찾기",
                "위성 전화 대여점 방문"
            ]
        }

        # 계획을 파일로 저장
        try:
            with open('mountain_emergency_plan.json', 'w', encoding='utf-8') as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)
            print("📝 긴급 계획이 'mountain_emergency_plan.json'에 저장되었습니다.")
        except Exception as e:
            print(f"⚠️ 계획 저장 실패: {e}")

        return plan

    def run_emergency_check(self):
        """긴급 상황 체크 실행"""
        print("🚨 긴급 위성 인터넷 체크 시작")
        print("⏰ 시간:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()

        # 1. 네트워크 스캔
        self.scan_available_networks()

        # 2. 인터넷 연결 확인
        has_internet = self.check_internet_connectivity()

        # 3. 긴급 정보 제공
        self.emergency_contact_info()

        # 4. 위성 인터넷 가이드
        self.satellite_internet_guide()

        # 5. 긴급 계획 생성
        self.create_emergency_plan()

        # 최종 권장사항
        print("🎯 현재 상황 권장사항:")
        print("=" * 40)

        if has_internet:
            print("✅ 현재 인터넷 연결이 있습니다!")
            print("💡 백업으로 위성 인터넷 준비 고려")
        else:
            print("🚨 인터넷 연결이 없습니다!")
            print("🆘 긴급 상황 시 119 신고")
            print("📡 위성 인터넷 설치 강력 권장:")
            print("   1순위: Starlink 구매/설치")
            print("   2순위: 위성폰 대여")
            print("   3순위: 가까운 마을로 이동")

        print()
        print("🏔️ 산속에서 안전하시길 바랍니다! 🏔️")


def main():
    """메인 실행"""
    emergency_system = MountainEmergencySatellite()
    emergency_system.run_emergency_check()


if __name__ == "__main__":
    main()
