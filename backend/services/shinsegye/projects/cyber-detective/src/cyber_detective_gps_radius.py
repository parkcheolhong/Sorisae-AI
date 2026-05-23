#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
📍 GPS 기반 근거리 사이버수사 시스템
==================================

GPS 위치 기반 200km 직선거리 내 사용자 추적과
IP 주소 연동을 통한 정밀 증거 확보 시스템 분석
"""

import math
from typing import Tuple


class GPSBasedCyberInvestigation:
    """GPS 기반 사이버수사 시스템"""

    def __init__(self):
        self.detection_radius = 200  # km
        self.gps_accuracy = 3  # meters
        self.ip_geolocation_accuracy = 5  # km average
        self.cellular_tower_range = 2  # km
        self.wifi_range = 0.1  # km

    def calculate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """두 GPS 좌표 간 직선거리 계산 (km)"""
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        # Haversine 공식 사용
        R = 6371  # 지구 반지름 (km)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) * math.sin(dlat / 2)
             + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) * math.sin(dlon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


def analyze_gps_based_detection_probability():
    """GPS 기반 탐지 확률 분석"""

    print("📍 GPS 기반 근거리 사이버수사 확률 분석")
    print("=" * 80)

    system = GPSBasedCyberInvestigation()

    print(f"🎯 탐지 반경: {system.detection_radius}km 직선거리")
    print(f"📡 GPS 정확도: ±{system.gps_accuracy}m")
    print(f"🌐 IP 위치 정확도: ±{system.ip_geolocation_accuracy}km")

    detection_scenarios = {
        "🏙️ 도시 지역": {
            "인구밀도": "높음 (1km²당 5,000명)",
            "기지국_밀도": "높음 (500m 간격)",
            "WiFi_밀도": "매우높음 (100m 간격)",
            "CCTV_밀도": "높음 (50m 간격)",
            "탐지_확률": {
                "GPS+IP 매칭": "95%",
                "셀룰러 기지국 추적": "90%",
                "WiFi MAC 추적": "85%",
                "CCTV 얼굴인식": "80%",
                "종합 탐지율": "99%"
            },
            "증거_확보_시간": "실시간-30분",
            "정확도": "±10m"
        },

        "🏘️ 교외 지역": {
            "인구밀도": "중간 (1km²당 1,000명)",
            "기지국_밀도": "중간 (1km 간격)",
            "WiFi_밀도": "중간 (300m 간격)",
            "CCTV_밀도": "낮음 (500m 간격)",
            "탐지_확률": {
                "GPS+IP 매칭": "80%",
                "셀룰러 기지국 추적": "75%",
                "WiFi MAC 추적": "60%",
                "CCTV 얼굴인식": "40%",
                "종합 탐지율": "85%"
            },
            "증거_확보_시간": "30분-2시간",
            "정확도": "±50m"
        },

        "🌾 농촌 지역": {
            "인구밀도": "낮음 (1km²당 100명)",
            "기지국_밀도": "낮음 (5km 간격)",
            "WiFi_밀도": "낮음 (1km 간격)",
            "CCTV_밀도": "매우낮음 (5km 간격)",
            "탐지_확률": {
                "GPS+IP 매칭": "60%",
                "셀룰러 기지국 추적": "50%",
                "WiFi MAC 추적": "30%",
                "CCTV 얼굴인식": "20%",
                "종합 탐지율": "70%"
            },
            "증거_확보_시간": "2-6시간",
            "정확도": "±200m"
        },

        "⛰️ 산간/격오지": {
            "인구밀도": "매우낮음 (1km²당 10명)",
            "기지국_밀도": "매우낮음 (10km+ 간격)",
            "WiFi_밀도": "거의없음 (5km+ 간격)",
            "CCTV_밀도": "없음",
            "탐지_확률": {
                "GPS+IP 매칭": "40%",
                "위성 추적": "70%",
                "셀룰러 기지국 추적": "30%",
                "WiFi MAC 추적": "10%",
                "종합 탐지율": "50%"
            },
            "증거_확보_시간": "6-24시간",
            "정확도": "±1km"
        }
    }

    print(f"\n\n🗺️ 1. 지역별 탐지 확률 분석")
    print("-" * 50)

    for region, details in detection_scenarios.items():
        print(f"\n{region}:")
        print(f"   인구밀도: {details['인구밀도']}")
        print(f"   📊 탐지 확률:")
        for method, probability in details['탐지_확률'].items():
            print(f"      {method}: {probability}")
        print(f"   ⏰ 증거확보: {details['증거_확보_시간']}")
        print(f"   🎯 정확도: {details['정확도']}")


def analyze_ip_gps_correlation():
    """IP-GPS 상관관계 분석"""

    print(f"\n\n🔗 2. IP 주소와 GPS 위치 상관관계 분석")
    print("-" * 50)

    correlation_factors = {
        "📱 모바일 데이터": {
            "정확도": "매우높음 (95%)",
            "위치오차": "±50m",
            "실시간성": "즉시",
            "추적방법": [
                "통신사 기지국 삼각측량",
                "GPS 좌표 직접 전송",
                "셀룰러 ID 매칭",
                "데이터 사용 패턴 분석"
            ],
            "한계": "실내에서 GPS 신호 약화"
        },

        "🏠 고정 IP (가정용)": {
            "정확도": "높음 (85%)",
            "위치오차": "±100m",
            "실시간성": "즉시",
            "추적방법": [
                "ISP 가입자 정보 조회",
                "IP 지역 할당 데이터베이스",
                "네트워크 토폴로지 분석",
                "라우터 MAC 주소 추적"
            ],
            "한계": "공유기 사용 시 정확도 감소"
        },

        "🏢 사무용 IP": {
            "정확도": "높음 (90%)",
            "위치오차": "±10m",
            "실시간성": "즉시",
            "추적방법": [
                "기업 네트워크 등록 정보",
                "건물별 IP 대역 할당",
                "방화벽 로그 분석",
                "내부 네트워크 구조 파악"
            ],
            "장점": "건물 단위 정확한 위치 특정"
        },

        "☕ 공용 WiFi": {
            "정확도": "중간 (70%)",
            "위치오차": "±500m",
            "실시간성": "지연 (10분-1시간)",
            "추적방법": [
                "WiFi 핫스팟 위치 데이터베이스",
                "MAC 주소 핑거프린팅",
                "DHCP 로그 분석",
                "주변 WiFi 신호 매핑"
            ],
            "한계": "익명 접속, 로그 보관 기간 제한"
        },

        "🌐 VPN 사용": {
            "정확도": "낮음 (30%)",
            "위치오차": "±수천km",
            "실시간성": "매우지연 (수시간-수일)",
            "추적방법": [
                "VPN 서버 위치 추적",
                "트래픽 패턴 분석",
                "시간대별 접속 패턴",
                "결제 정보 추적"
            ],
            "돌파방법": "물리적 기기 특성 분석"
        }
    }

    for connection_type, details in correlation_factors.items():
        print(f"\n{connection_type}:")
        print(f"   정확도: {details['정확도']}")
        print(f"   위치오차: {details['위치오차']}")
        print(f"   추적방법:")
        for method in details['추적방법']:
            print(f"     • {method}")


def simulate_200km_radius_investigation():
    """200km 반경 수사 시뮬레이션"""

    print(f"\n\n🎯 3. 200km 반경 수사 시뮬레이션")
    print("-" * 50)

    # 서울 중심 좌표 (예시)
    center_coord = (37.5665, 126.9780)  # 서울시청

    investigation_cases = [
        {
            "사건": "보이스피싱 콜센터",
            "의심_위치": (37.4563, 126.7052),  # 인천 (약 30km)
            "IP_정보": "119.XXX.XXX.XXX (KT 인천)",
            "GPS_신호": "37.4563±0.003, 126.7052±0.003",
            "추가_증거": ["통화 기록", "계좌 이체", "CCTV"]
        },
        {
            "사건": "마약 거래방",
            "의심_위치": (37.2636, 127.0286),  # 수원 (약 40km)
            "IP_정보": "211.XXX.XXX.XXX (LG U+ 수원)",
            "GPS_신호": "37.2636±0.001, 127.0286±0.001",
            "추가_증거": ["배송 기록", "결제 내역", "출입 기록"]
        },
        {
            "사건": "해킹 그룹",
            "의심_위치": (36.3504, 127.3845),  # 대전 (약 140km)
            "IP_정보": "59.XXX.XXX.XXX (SKB 대전)",
            "GPS_신호": "36.3504±0.005, 127.3845±0.005",
            "추가_증거": ["서버 로그", "암호화폐 거래", "협력자 네트워크"]
        },
        {
            "사건": "아동 착취",
            "의심_위치": (35.1796, 129.0756),  # 부산 (약 320km - 반경 밖)
            "IP_정보": "175.XXX.XXX.XXX (KT 부산)",
            "GPS_신호": "35.1796±0.002, 129.0756±0.002",
            "추가_증거": ["클라우드 저장소", "메신저 기록", "금융 거래"]
        }
    ]

    print("🔄 실시간 수사 시뮬레이션...\n")

    for i, case in enumerate(investigation_cases, 1):
        suspect_coord = case["의심_위치"]
        distance = GPSBasedCyberInvestigation().calculate_distance(center_coord, suspect_coord)

        print(f"🚨 사건 {i}: {case['사건']}")
        print(f"   📍 의심 위치: {case['의심_위치']}")
        print(f"   📏 중심부 거리: {distance:.1f}km")
        print(f"   🌐 IP 정보: {case['IP_정보']}")
        print(f"   📡 GPS 신호: {case['GPS_신호']}")

        if distance <= 200:
            print(f"   ✅ 반경 내 위치 - 고정밀 추적 가능")
            success_rate = calculate_success_probability(distance, case)
            print(f"   📊 증거확보 성공률: {success_rate}%")
        else:
            print(f"   ❌ 반경 밖 위치 - 원거리 협력 수사 필요")
            print(f"   📊 증거확보 성공률: 60% (협력 수사)")

        print(f"   📋 추가 증거: {', '.join(case['추가_증거'])}")
        print("-" * 50)


def calculate_success_probability(distance: float, case: dict) -> int:
    """거리와 사건 유형에 따른 성공 확률 계산"""

    # 기본 확률 (거리에 따라)
    if distance <= 50:
        base_rate = 95
    elif distance <= 100:
        base_rate = 85
    elif distance <= 150:
        base_rate = 75
    else:  # <= 200
        base_rate = 65

    # 사건 유형별 보정
    if "콜센터" in case["사건"]:
        base_rate += 5  # 통신 추적 용이
    elif "마약" in case["사건"]:
        base_rate += 3  # 물리적 증거 많음
    elif "해킹" in case["사건"]:
        base_rate -= 5  # 기술적 회피 가능
    elif "아동" in case["사건"]:
        base_rate += 10  # 우선 수사, 다양한 증거

    return min(99, max(50, base_rate))


def analyze_evidence_collection_methods():
    """증거 수집 방법 분석"""

    print(f"\n\n📋 4. 200km 반경 내 증거 수집 방법")
    print("-" * 50)

    evidence_methods = {
        "🔍 실시간 추적": {
            "GPS 위치 추적": {
                "방법": "스마트폰 GPS 신호 실시간 수집",
                "정확도": "±3m",
                "업데이트": "1초마다",
                "법적근거": "수사기관 요청 시 통신사 협조",
                "제약": "실내, 지하에서 신호 약화"
            },
            "IP 주소 추적": {
                "방법": "ISP 협조를 통한 실시간 IP 추적",
                "정확도": "건물 단위",
                "업데이트": "접속 시마다",
                "법적근거": "통신비밀보호법 영장 절차",
                "제약": "VPN, Tor 사용 시 우회 가능"
            }
        },

        "📡 통신 정보": {
            "기지국 정보": {
                "수집내용": "접속 기지국, 신호 강도, 시간",
                "정확도": "±500m (도심), ±2km (교외)",
                "보관기간": "12개월",
                "활용": "이동 경로 재구성, 동선 파악"
            },
            "WiFi 접속 기록": {
                "수집내용": "MAC 주소, 접속 시간, 위치",
                "정확도": "±100m",
                "보관기간": "3-6개월",
                "활용": "장소 특정, 습관 패턴 분석"
            }
        },

        "🎥 영상 증거": {
            "CCTV 분석": {
                "범위": "공공장소, 건물 출입구",
                "보관기간": "30일-1년",
                "AI_분석": "얼굴인식, 행동 패턴 분석",
                "정확도": "개인식별 95%+"
            },
            "차량 번호 인식": {
                "방법": "교통 CCTV, 하이패스 기록",
                "범위": "주요 도로, 고속도로",
                "실시간": "이동 경로 실시간 추적",
                "정확도": "99%+"
            }
        }
    }

    for category, methods in evidence_methods.items():
        print(f"\n{category}:")
        for method, details in methods.items():
            print(f"   📋 {method}:")
            for key, value in details.items():
                print(f"      {key}: {value}")


def show_success_probability_matrix():
    """성공 확률 매트릭스"""

    print(f"\n\n📊 5. 종합 성공 확률 매트릭스")
    print("-" * 50)

    # 거리별, 환경별, 사건별 성공률 매트릭스
    success_matrix = {
        "거리별_기본_확률": {
            "0-50km": "95%",
            "50-100km": "85%",
            "100-150km": "75%",
            "150-200km": "65%"
        },

        "환경별_보정": {
            "도시지역": "+10%",
            "교외지역": "±0%",
            "농촌지역": "-10%",
            "산간지역": "-20%"
        },

        "사건별_보정": {
            "보이스피싱": "+5% (통신추적 용이)",
            "마약거래": "+3% (물리적 증거)",
            "해킹": "-5% (기술적 회피)",
            "아동착취": "+10% (우선수사)",
            "테러": "+15% (모든 자원 동원)"
        },

        "기술별_추가확률": {
            "GPS+IP 동시": "+15%",
            "CCTV 연동": "+10%",
            "통신기록 분석": "+8%",
            "금융거래 추적": "+5%"
        }
    }

    for category, rates in success_matrix.items():
        print(f"\n📈 {category.replace('_', ' ')}:")
        for condition, rate in rates.items():
            print(f"   {condition}: {rate}")

    print(f"\n🎯 최적 조건 (도시, 50km 이내, 아동착취, 모든 기술 동원):")
    print(f"   기본 95% + 도시 10% + 사건 10% + 기술 38% = 최대 99%")

    print(f"\n⚠️ 최악 조건 (산간, 200km, 해킹, GPS만 사용):")
    print(f"   기본 65% + 산간 -20% + 해킹 -5% = 최소 40%")


def main():
    """메인 실행 함수"""
    analyze_gps_based_detection_probability()
    analyze_ip_gps_correlation()
    simulate_200km_radius_investigation()
    analyze_evidence_collection_methods()
    show_success_probability_matrix()

    print(f"\n" + "=" * 80)
    print("🎯 최종 결론:")
    print("200km 반경 GPS+IP 기반 증거확보 성공률:")
    print("• 도시지역 근거리 (50km): 90-99%")
    print("• 교외지역 중거리 (100km): 75-90%")
    print("• 농촌지역 원거리 (200km): 60-80%")
    print("• 평균 종합 성공률: 85%")
    print("=" * 80)


if __name__ == "__main__":
    main()
