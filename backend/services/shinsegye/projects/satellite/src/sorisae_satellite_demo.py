#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🛰️ 소리새 차세대 인공위성 와이파이 데모
Sorisae Next-Generation Satellite WiFi Demo

사용자가 "소리새야, 위성 인터넷 연결해줘"라고 말하면
차세대 인공위성 네트워크를 통해 전 세계 어디서든 연결!
"""

import random
import time

from sorisae_satellite_wifi_system import SorisaeSatelliteWiFiSystem


def main():
    """차세대 인공위성 와이파이 데모"""
    print("🛰️" + "=" * 60 + "🛰️")
    print("   소리새 차세대 인공위성 와이파이 시스템")
    print("   Sorisae Next-Generation Satellite WiFi")
    print("🛰️" + "=" * 60 + "🛰️")
    print()

    # 시스템 초기화
    print("🚀 시스템 초기화 중...")
    satellite_system = SorisaeSatelliteWiFiSystem()

    print("\n✅ 초기화 완료!")
    print("\n" + "🌍" + "=" * 58 + "🌍")
    print("   전 세계 125개 위성이 대기 중입니다!")
    print("   소리새 전용 위성 50개 포함")
    print("🌍" + "=" * 58 + "🌍")

    # 자동 데모 시퀀스 실행
    demo_scenarios = [
        {
            'location': '서울, 대한민국',
            'lat': 37.5665,
            'lon': 126.9780,
            'description': '도심에서의 고속 인터넷'
        },
        {
            'location': '에베레스트 베이스캠프',
            'lat': 28.0026,
            'lon': 86.8528,
            'description': '극한 환경에서의 연결'
        },
        {
            'location': '사하라 사막 중심부',
            'lat': 23.8060,
            'lon': 11.1540,
            'description': '지구 최고 오지에서의 통신'
        },
        {
            'location': '태평양 한가운데',
            'lat': 0.0,
            'lon': -160.0,
            'description': '바다 위에서의 위성 인터넷'
        }
    ]

    try:
        for i, scenario in enumerate(demo_scenarios, 1):
            print(f"\n🌐 시나리오 {i}: {scenario['location']}")
            print(f"📍 위치: {scenario['description']}")
            print(f"🎯 좌표: {scenario['lat']:.4f}, {scenario['lon']:.4f}")
            print("-" * 60)

            # 위성 연결 시도
            print("🔍 최적 위성 검색 중...")
            time.sleep(1)

            satellite_system.start_satellite_connection(scenario['lat'], scenario['lon'])

            if satellite_system.is_active:
                print("✅ 연결 성공!")

                # 연결 품질 모니터링 (5초간)
                print("📊 연결 품질 모니터링...")
                for j in range(3):
                    time.sleep(1)
                    if satellite_system.current_connection:
                        speed = satellite_system.current_connection.download_speed
                        ping = satellite_system.current_connection.ping
                        print(f"   ⚡ 속도: {speed:.1f} Mbps | 🏓 지연: {ping:.1f}ms")

                # 간단한 인터넷 활동 시뮬레이션
                print("\n🌐 인터넷 활동 시뮬레이션:")
                activities = [
                    "📺 4K 동영상 스트리밍",
                    "🎮 온라인 게임",
                    "📞 화상 회의",
                    "☁️ 클라우드 동기화",
                    "📱 SNS 업로드"
                ]

                for activity in random.sample(activities, 3):
                    print(f"   {activity} - 원활히 작동 중 ✅")
                    time.sleep(0.5)

                # 연결 해제
                satellite_system.disconnect()
                print("🔌 연결 해제 완료")
            else:
                print("❌ 연결 실패 - 다음 시나리오로 진행")

            if i < len(demo_scenarios):
                print(f"\n⏳ 다음 시나리오까지 3초...")
                time.sleep(3)

        # 최종 데모: 비상 모드
        print("\n" + "🚨" + "=" * 58 + "🚨")
        print("   🆘 비상 상황 시뮬레이션")
        print("   재해 지역에서의 긴급 통신")
        print("🚨" + "=" * 58 + "🚨")

        print("\n🌪️ 상황: 자연재해로 모든 통신망 두절")
        print("📡 소리새 비상 모드 자동 활성화...")

        satellite_system.emergency_mode()

        if satellite_system.is_active:
            print("\n✅ 비상 통신 확보!")
            print("🆘 긴급 구조 요청 전송 가능")
            print("📞 응급 의료진과 연결 가능")
            print("📡 실시간 재해 상황 공유 가능")

            time.sleep(2)
            satellite_system.disconnect()

        print("\n" + "🎉" + "=" * 58 + "🎉")
        print("   소리새 차세대 인공위성 와이파이 데모 완료!")
        print("   전 세계 어디서든 연결 가능!")
        print("🎉" + "=" * 58 + "🎉")

        # 최종 통계
        print("\n📊 시스템 성능 요약:")
        constellation_stats = satellite_system.get_satellite_constellation_info()

        for constellation, stats in constellation_stats.items():
            if stats['active_satellites'] > 0:
                print(f"🛰️ {constellation.upper()}: {stats['active_satellites']}개 활성")
                print(f"   평균 속도: {stats['avg_bandwidth']:.0f} Mbps")
                print(f"   평균 지연: {stats['avg_latency']:.0f} ms")

        print(f"\n🌐 총 커버리지: 지구 전체 100%")
        print(f"🚀 최대 속도: 1,000 Mbps")
        print(f"⚡ 최저 지연: 15 ms")
        print(f"🛰️ 전용 위성: 50개 (소리새 constellation)")

        print("\n💬 음성 명령 예시:")
        print("   '소리새야, 위성 인터넷 연결해줘'")
        print("   '소리새야, 연결 상태 확인해줘'")
        print("   '소리새야, 비상 모드 켜줘'")
        print("   '소리새야, 위성 바꿔줘'")

    except KeyboardInterrupt:
        print("\n\n🛑 사용자가 데모를 중단했습니다.")
        if satellite_system.is_active:
            satellite_system.disconnect()
    except Exception as e:
        print(f"\n❌ 데모 중 오류 발생: {e}")
        if satellite_system.is_active:
            satellite_system.disconnect()

    print("\n👋 데모를 종료합니다. 감사합니다!")


if __name__ == "__main__":
    main()
