#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌍 소리새 GPS 기반 윤리의식 및 국가별 법률 준수 시스템
위치 기반으로 해당 국가의 법률과 문화적 윤리 기준을 자동 적용
"""

import sqlite3
import time
from datetime import datetime

import requests
from geopy.geocoders import Nominatim  # type: ignore # type: ignore


class EthicalGPSSystem:
    """GPS 기반 윤리의식 및 법률 준수 시스템"""

    def __init__(self):
        """윤리 GPS 시스템 초기화"""
        self.geolocator = None
        self.current_location = None
        self.current_country = None
        self.current_ethics_profile = None

        # 데이터베이스 초기화
        self.init_database()

        # 국가별 윤리 및 법률 데이터베이스 로드
        self.load_country_ethics_database()

        # 위치 서비스 초기화
        self.init_location_services()

        print("🌍 소리새 GPS 기반 윤리의식 시스템이 초기화되었습니다!")

    def init_database(self):
        """윤리 데이터베이스 초기화"""
        self.conn = sqlite3.connect('sorisae_ethics.db')
        cursor = self.conn.cursor()

        # 국가별 윤리 프로필 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS country_ethics (
                country_code TEXT PRIMARY KEY,
                country_name TEXT,
                ethics_profile TEXT,
                legal_restrictions TEXT,
                cultural_guidelines TEXT,
                privacy_level INTEGER,
                content_restrictions TEXT,
                communication_style TEXT,
                last_updated DATETIME
            )
        ''')

        # 위치 기록 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS location_history (
                timestamp DATETIME,
                latitude REAL,
                longitude REAL,
                country_code TEXT,
                city TEXT,
                ethics_applied TEXT
            )
        ''')

        self.conn.commit()
        print("📊 윤리 데이터베이스 초기화 완료")

    def init_location_services(self):
        """위치 서비스 초기화"""
        try:
            self.geolocator = Nominatim(user_agent="sorisae_ethical_gps")
            print("📍 GPS 위치 서비스 초기화 완료")
        except Exception as e:
            print(f"⚠️ GPS 서비스 초기화 오류: {e} (시뮬레이션 모드)")
            self.geolocator = None

    def load_country_ethics_database(self):
        """국가별 윤리 및 법률 데이터베이스 로드"""
        ethics_data = {
            "KR": {  # 대한민국
                "country_name": "대한민국",
                "ethics_profile": "높은 예의, 계층 의식, 집단주의",
                "legal_restrictions": "개인정보보호법, 정보통신망법, 저작권법",
                "cultural_guidelines": "존댓말 사용, 나이/지위 고려, 겸손한 표현",
                "privacy_level": 9,
                "content_restrictions": "정치적 중립, 종교적 배려, 성인 콘텐츠 제한",
                "communication_style": "정중하고 간접적"
            },
            "US": {  # 미국
                "country_name": "미국",
                "ethics_profile": "개인주의, 자유 중시, 다양성 존중",
                "legal_restrictions": "COPPA, GDPR준수, 차별금지법",
                "cultural_guidelines": "직접적 소통, 개인 권리 존중, 포용성",
                "privacy_level": 7,
                "content_restrictions": "차별 금지, 혐오 발언 제한",
                "communication_style": "친근하고 직접적"
            },
            "JP": {  # 일본
                "country_name": "일본",
                "ethics_profile": "고맥락 문화, 화합 중시, 예의 중시",
                "legal_restrictions": "개인정보보호법, 저작권법, 청소년보호법",
                "cultural_guidelines": "겸손함, 집단 조화, 간접적 표현",
                "privacy_level": 8,
                "content_restrictions": "성인 콘텐츠 엄격 제한, 폭력성 제한",
                "communication_style": "정중하고 우회적"
            },
            "CN": {  # 중국
                "country_name": "중국",
                "ethics_profile": "집단주의, 권위 존중, 조화 추구",
                "legal_restrictions": "사이버보안법, 데이터보안법, 개인정보보호법",
                "cultural_guidelines": "정치적 민감성, 사회 안정 중시",
                "privacy_level": 6,
                "content_restrictions": "정치적 내용 제한, 사회 안정 우선",
                "communication_style": "공손하고 신중한"
            },
            "DE": {  # 독일
                "country_name": "독일",
                "ethics_profile": "규칙 준수, 프라이버시 중시, 직접성",
                "legal_restrictions": "GDPR, 연방데이터보호법, 청소년보호법",
                "cultural_guidelines": "프라이버시 존중, 정확성 중시",
                "privacy_level": 10,
                "content_restrictions": "나치 관련 금지, 개인정보 엄격 보호",
                "communication_style": "직접적이고 정확한"
            },
            "GB": {  # 영국
                "country_name": "영국",
                "ethics_profile": "예의, 절제, 개인주의와 전통의 균형",
                "legal_restrictions": "UK GDPR, 데이터보호법, 온라인 안전법",
                "cultural_guidelines": "정중함, 프라이버시 존중, 유머 감각",
                "privacy_level": 8,
                "content_restrictions": "아동 보호 우선, 혐오 발언 제한",
                "communication_style": "정중하고 절제된"
            },
            "FR": {  # 프랑스
                "country_name": "프랑스",
                "ethics_profile": "개인주의, 문화적 자부심, 라이시테",
                "legal_restrictions": "GDPR, 디지털공화국법, 종교중립법",
                "cultural_guidelines": "세속주의, 문화적 예외, 언어 순수성",
                "privacy_level": 9,
                "content_restrictions": "종교적 상징 제한, 혐오 발언 금지",
                "communication_style": "우아하고 논리적"
            },
            "CA": {  # 캐나다
                "country_name": "캐나다",
                "ethics_profile": "다문화주의, 포용성, 공손함",
                "legal_restrictions": "PIPEDA, 프라이버시법, 인권법",
                "cultural_guidelines": "다양성 존중, 양개 공용어, 원주민 권리",
                "privacy_level": 8,
                "content_restrictions": "혐오 발언 금지, 다문화 존중",
                "communication_style": "친근하고 공손한"
            },
            "AU": {  # 호주
                "country_name": "호주",
                "ethics_profile": "평등주의, 직설적, 여유로움",
                "legal_restrictions": "프라이버시법, 차별금지법, 방송법",
                "cultural_guidelines": "공정함, 직설적 소통, 원주민 존중",
                "privacy_level": 7,
                "content_restrictions": "차별 금지, 원주민 문화 존중",
                "communication_style": "친근하고 직설적"
            },
            "IN": {  # 인도
                "country_name": "인도",
                "ethics_profile": "다양성, 계층구조, 가족중심",
                "legal_restrictions": "정보기술법, 개인정보보호법, 종교법",
                "cultural_guidelines": "종교 존중, 카스트 민감성, 가족 가치",
                "privacy_level": 6,
                "content_restrictions": "종교적 민감성, 카스트 차별 금지",
                "communication_style": "정중하고 존댓말"
            },
            "BR": {  # 브라질
                "country_name": "브라질",
                "ethics_profile": "사교성, 가족중심, 다양성",
                "legal_restrictions": "LGPD, 헌법, 아동청소년법",
                "cultural_guidelines": "친밀감, 개인 공간 존중, 사회적 계층",
                "privacy_level": 7,
                "content_restrictions": "아동 보호, 인종 차별 금지",
                "communication_style": "따뜻하고 친근한"
            },
            "RU": {  # 러시아
                "country_name": "러시아",
                "ethics_profile": "권위주의, 전통주의, 집단주의",
                "legal_restrictions": "개인정보법, 정보보안법, 극단주의방지법",
                "cultural_guidelines": "국가 권위 존중, 전통 가치, 정치적 신중",
                "privacy_level": 5,
                "content_restrictions": "정치적 내용 제한, 극단주의 금지",
                "communication_style": "공식적이고 신중한"
            },
            "IT": {  # 이탈리아
                "country_name": "이탈리아",
                "ethics_profile": "가족중심, 전통존중, 사교성",
                "legal_restrictions": "GDPR, 개인정보보호법, 저작권법",
                "cultural_guidelines": "가족 가치, 지역 정체성, 문화 유산",
                "privacy_level": 8,
                "content_restrictions": "가족 가치 존중, 문화유산 보호",
                "communication_style": "표현력 풍부하고 따뜻한"
            },
            "ES": {  # 스페인
                "country_name": "스페인",
                "ethics_profile": "개인주의와 집단주의 균형, 여유로운 생활",
                "legal_restrictions": "GDPR, 개인정보보호법, 언어법",
                "cultural_guidelines": "지역 언어 존중, 시에스타 문화, 가족 중심",
                "privacy_level": 8,
                "content_restrictions": "지역 언어 배려, 분리주의 민감성",
                "communication_style": "열정적이고 표현력 풍부한"
            },
            "NL": {  # 네덜란드
                "country_name": "네덜란드",
                "ethics_profile": "관용, 직설적, 평등주의",
                "legal_restrictions": "GDPR, 개인정보보호법, 차별금지법",
                "cultural_guidelines": "직설적 소통, 관용 정신, 자전거 문화",
                "privacy_level": 9,
                "content_restrictions": "차별 금지, 개인 자유 존중",
                "communication_style": "직설적이고 실용적"
            },
            "SE": {  # 스웨덴
                "country_name": "스웨덴",
                "ethics_profile": "평등주의, 환경의식, 복지국가",
                "legal_restrictions": "GDPR, 개인정보보호법, 환경법",
                "cultural_guidelines": "성평등, 환경보호, 사회복지",
                "privacy_level": 10,
                "content_restrictions": "성차별 금지, 환경 보호 우선",
                "communication_style": "겸손하고 신중한"
            },
            "CH": {  # 스위스
                "country_name": "스위스",
                "ethics_profile": "중립성, 정확성, 프라이버시",
                "legal_restrictions": "연방데이터보호법, 금융법, 중립법",
                "cultural_guidelines": "중립성 유지, 정확성, 다국어 존중",
                "privacy_level": 10,
                "content_restrictions": "정치적 중립, 금융 정보 보호",
                "communication_style": "정확하고 절제된"
            },
            "SG": {  # 싱가포르
                "country_name": "싱가포르",
                "ethics_profile": "다문화주의, 실용주의, 규율",
                "legal_restrictions": "개인정보보호법, 사이버보안법, 조화법",
                "cultural_guidelines": "인종 조화, 종교 관용, 법규 준수",
                "privacy_level": 7,
                "content_restrictions": "인종/종교 갈등 방지, 정부 정책 존중",
                "communication_style": "정중하고 실용적"
            },
            "AE": {  # 아랍에미리트
                "country_name": "아랍에미리트",
                "ethics_profile": "전통과 현대의 조화, 관용, 존중",
                "legal_restrictions": "사이버범죄법, 개인정보보호법, 이슬람법",
                "cultural_guidelines": "이슬람 가치, 문화적 민감성, 손님 대접",
                "privacy_level": 6,
                "content_restrictions": "이슬람 가치 존중, 문화적 적절성",
                "communication_style": "존중하고 예의바른"
            },
            "NO": {  # 노르웨이
                "country_name": "노르웨이",
                "ethics_profile": "평등주의, 환경보호, 복지",
                "legal_restrictions": "GDPR, 개인정보보호법, 환경법",
                "cultural_guidelines": "양성평등, 환경의식, 사회연대",
                "privacy_level": 10,
                "content_restrictions": "성차별 금지, 환경 가치 우선",
                "communication_style": "겸손하고 직설적"
            },
            "DK": {  # 덴마크
                "country_name": "덴마크",
                "ethics_profile": "휘게, 평등주의, 신뢰",
                "legal_restrictions": "GDPR, 개인정보보호법, 복지법",
                "cultural_guidelines": "생활의 질, 사회적 신뢰, 균형",
                "privacy_level": 9,
                "content_restrictions": "사회적 조화, 개인 웰빙 중시",
                "communication_style": "편안하고 신뢰하는"
            },
            "TH": {  # 태국
                "country_name": "태국",
                "ethics_profile": "불교 문화, 계층 존중, 미소의 나라",
                "legal_restrictions": "개인정보보호법, 컴퓨터범죄법, 왕실모독죄",
                "cultural_guidelines": "왕실 존경, 불교 가치, 와이 인사법",
                "privacy_level": 6,
                "content_restrictions": "왕실 비판 금지, 종교적 배려",
                "communication_style": "공손하고 우회적"
            },
            "VN": {  # 베트남
                "country_name": "베트남",
                "ethics_profile": "유교 문화, 가족 중심, 공동체 의식",
                "legal_restrictions": "사이버보안법, 개인정보보호법, 정보법",
                "cultural_guidelines": "나이 존중, 가족 가치, 집단 조화",
                "privacy_level": 5,
                "content_restrictions": "정치적 민감성, 정부 정책 존중",
                "communication_style": "예의바르고 신중한"
            },
            "MY": {  # 말레이시아
                "country_name": "말레이시아",
                "ethics_profile": "다종족 조화, 이슬람 가치, 1Malaysia",
                "legal_restrictions": "개인정보보호법, 사이버보안법, 선동방지법",
                "cultural_guidelines": "종족 조화, 이슬람 가치 존중, 다문화",
                "privacy_level": 6,
                "content_restrictions": "종족/종교 갈등 방지, 정치적 신중",
                "communication_style": "정중하고 조화로운"
            },
            "PH": {  # 필리핀
                "country_name": "필리핀",
                "ethics_profile": "가족주의, 존경 문화, 바야니한 정신",
                "legal_restrictions": "데이터프라이버시법, 사이버범죄법, 아동보호법",
                "cultural_guidelines": "나이 존경(Po/Opo), 가족 중심, 공동체 정신",
                "privacy_level": 6,
                "content_restrictions": "가족 가치 존중, 아동 보호 우선",
                "communication_style": "존댓말과 따뜻함"
            },
            "ID": {  # 인도네시아
                "country_name": "인도네시아",
                "ethics_profile": "다양성 속 통일, 종교적 관용, 고톤 로용",
                "legal_restrictions": "개인정보보호법, 정보전자거래법, 종교모독죄",
                "cultural_guidelines": "종교 존중, 다양성 인정, 공동체 협력",
                "privacy_level": 6,
                "content_restrictions": "종교적 민감성, SARA 이슈 주의",
                "communication_style": "공손하고 간접적"
            },
            "MM": {  # 미얀마
                "country_name": "미얀마",
                "ethics_profile": "불교 전통, 존경 문화, 공동체 중심",
                "legal_restrictions": "전자거래법, 통신법, 종교법",
                "cultural_guidelines": "불교 가치, 나이 존경, 전통 존중",
                "privacy_level": 4,
                "content_restrictions": "정치적 민감성, 종교적 배려",
                "communication_style": "겸손하고 전통적"
            },
            "KH": {  # 캄보디아
                "country_name": "캄보디아",
                "ethics_profile": "크메르 문화, 불교 전통, 왕실 존경",
                "legal_restrictions": "개인정보보호법, 사이버범죄법, 왕실법",
                "cultural_guidelines": "왕실 존경, 불교 가치, 나이 존중",
                "privacy_level": 4,
                "content_restrictions": "왕실 비판 금지, 정치적 신중",
                "communication_style": "정중하고 전통적"
            },
            "LA": {  # 라오스
                "country_name": "라오스",
                "ethics_profile": "불교 전통, 평온함, 공동체 조화",
                "legal_restrictions": "사이버범죄법, 정보법, 전통문화보호법",
                "cultural_guidelines": "불교 가치, 전통 존중, 평화로운 공존",
                "privacy_level": 4,
                "content_restrictions": "정치적 민감성, 문화적 적절성",
                "communication_style": "온화하고 평온한"
            }
        }

        # 데이터베이스에 저장
        cursor = self.conn.cursor()
        for country_code, data in ethics_data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO country_ethics
                (country_code, country_name, ethics_profile, legal_restrictions,
                 cultural_guidelines, privacy_level, content_restrictions,
                 communication_style, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                country_code, data["country_name"], data["ethics_profile"],
                data["legal_restrictions"], data["cultural_guidelines"],
                data["privacy_level"], data["content_restrictions"],
                data["communication_style"], datetime.now()
            ))

        self.conn.commit()
        print(f"🗃️ {len(ethics_data)}개 국가 윤리 데이터베이스 로드 완료")

    def get_current_location(self):
        """현재 위치 확인 (실제 또는 시뮬레이션)"""
        try:
            if self.geolocator:
                # 실제 IP 기반 위치 확인 시도
                try:
                    response = requests.get('https://ipapi.co/json/', timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        location_info = {
                            "latitude": data.get('latitude'),
                            "longitude": data.get('longitude'),
                            "country_code": data.get('country_code'),
                            "country_name": data.get('country_name'),
                            "city": data.get('city'),
                            "region": data.get('region')
                        }
                        print(f"📍 실제 위치 확인: {location_info['city']}, {location_info['country_name']}")
                        return location_info
                except Exception as e:
                    print(f"실제 위치 확인 실패: {e}")

            # 시뮬레이션 모드
            import random
            simulation_locations = [
                {"latitude": 37.5665, "longitude": 126.9780, "country_code": "KR",
                 "country_name": "대한민국", "city": "서울", "region": "서울특별시"},
                {"latitude": 35.6762, "longitude": 139.6503, "country_code": "JP",
                 "country_name": "일본", "city": "도쿄", "region": "간토"},
                {"latitude": 40.7128, "longitude": -74.0060, "country_code": "US",
                 "country_name": "미국", "city": "뉴욕", "region": "뉴욕주"},
                {"latitude": 51.5074, "longitude": -0.1278, "country_code": "GB",
                 "country_name": "영국", "city": "런던", "region": "잉글랜드"},
                {"latitude": 52.5200, "longitude": 13.4050, "country_code": "DE",
                 "country_name": "독일", "city": "베를린", "region": "베를린"}
            ]

            location = random.choice(simulation_locations)
            print(f"📍 시뮬레이션 위치: {location['city']}, {location['country_name']}")
            return location

        except Exception as e:
            print(f"❌ 위치 확인 오류: {e}")
            return None

    def get_country_ethics_profile(self, country_code):
        """국가별 윤리 프로필 조회"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM country_ethics WHERE country_code = ?
        ''', (country_code,))

        result = cursor.fetchone()
        if result:
            return {
                "country_code": result[0],
                "country_name": result[1],
                "ethics_profile": result[2],
                "legal_restrictions": result[3],
                "cultural_guidelines": result[4],
                "privacy_level": result[5],
                "content_restrictions": result[6],
                "communication_style": result[7],
                "last_updated": result[8]
            }
        else:
            # 기본 국제 윤리 프로필
            return {
                "country_code": "INTL",
                "country_name": "국제 기준",
                "ethics_profile": "보편적 인권, 다양성 존중",
                "legal_restrictions": "국제 인권법, 개인정보보호",
                "cultural_guidelines": "문화적 중립, 포용성",
                "privacy_level": 7,
                "content_restrictions": "혐오 발언 금지, 아동 보호",
                "communication_style": "정중하고 중립적"
            }

    def apply_location_based_ethics(self):
        """위치 기반 윤리 적용"""
        print("\n🌍 GPS 기반 윤리의식 시스템 활성화")
        print("=" * 50)

        # 현재 위치 확인
        location = self.get_current_location()
        if not location:
            print("❌ 위치를 확인할 수 없습니다.")
            return None

        self.current_location = location
        self.current_country = location['country_code']

        # 해당 국가의 윤리 프로필 로드
        ethics_profile = self.get_country_ethics_profile(self.current_country)
        self.current_ethics_profile = ethics_profile

        # 위치 기록 저장
        self.log_location_change(location, ethics_profile)

        # 윤리 적용 결과 출력
        self.display_applied_ethics(location, ethics_profile)

        return ethics_profile

    def log_location_change(self, location, ethics_profile):
        """위치 변경 기록"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO location_history
            (timestamp, latitude, longitude, country_code, city, ethics_applied)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(),
            location['latitude'],
            location['longitude'],
            location['country_code'],
            location['city'],
            ethics_profile['country_name']
        ))
        self.conn.commit()

    def display_applied_ethics(self, location, ethics_profile):
        """적용된 윤리 프로필 표시"""
        print(f"📍 현재 위치: {location['city']}, {location['country_name']}")
        print(f"🏛️ 적용된 윤리 프로필: {ethics_profile['country_name']}")
        print()

        print("🎯 윤리 가이드라인:")
        print(f"  • 문화적 특성: {ethics_profile['ethics_profile']}")
        print(f"  • 소통 방식: {ethics_profile['communication_style']}")
        print(f"  • 문화적 지침: {ethics_profile['cultural_guidelines']}")
        print()

        print("⚖️ 법적 준수사항:")
        print(f"  • 관련 법률: {ethics_profile['legal_restrictions']}")
        print(f"  • 콘텐츠 제한: {ethics_profile['content_restrictions']}")
        print(f"  • 프라이버시 레벨: {ethics_profile['privacy_level']}/10")

    def get_ethical_response_filter(self, message, context="general"):
        """윤리적 응답 필터링"""
        if not self.current_ethics_profile:
            return message

        ethics = self.current_ethics_profile
        country = ethics['country_code']

        # 국가별 응답 조정
        if country == "KR":
            # 한국: 존댓말, 겸손한 표현
            if not any(ending in message for ending in ["습니다", "세요", "께서"]):
                message = self.convert_to_honorific(message)

        elif country == "JP":
            # 일본: 더욱 정중하고 우회적 표현
            message = self.add_japanese_politeness(message)

        elif country == "US":
            # 미국: 직접적이고 친근한 표현
            message = self.make_american_friendly(message)

        elif country == "DE":
            # 독일: 정확하고 직접적
            message = self.make_german_precise(message)

        elif country == "CN":
            # 중국: 신중하고 조화로운 표현
            message = self.make_chinese_harmonious(message)

        # 프라이버시 레벨에 따른 개인정보 필터링
        if ethics['privacy_level'] >= 8:
            message = self.filter_personal_info(message)

        return message

    def convert_to_honorific(self, message):
        """한국어 존댓말 변환"""
        honorific_replacements = {
            "이야": "입니다",
            "야": "요",
            "해": "하세요",
            "줘": "주세요",
            "봐": "보세요"
        }

        for informal, formal in honorific_replacements.items():
            if message.endswith(informal):
                message = message[:-len(informal)] + formal

        return message

    def add_japanese_politeness(self, message):
        """일본식 정중함 추가"""
        if not message.endswith(("습니다", "세요")):
            return f"정중히 말씀드리면, {message}입니다"
        return message

    def make_american_friendly(self, message):
        """미국식 친근함 추가"""
        friendly_prefixes = ["Sure!", "Absolutely!", "Of course!", "You bet!"]
        import random
        if not message.startswith(tuple(friendly_prefixes)):
            prefix = random.choice(friendly_prefixes)
            return f"{prefix} {message}"
        return message

    def make_german_precise(self, message):
        """독일식 정확성 강화"""
        return f"정확히 말씀드리면: {message}"

    def make_chinese_harmonious(self, message):
        """중국식 조화로운 표현"""
        return f"조화롭게 말씀드리면, {message}"

    def filter_personal_info(self, message):
        """개인정보 필터링"""
        import re

        # 전화번호, 이메일 등 패턴 제거
        message = re.sub(r'\d{3}-\d{4}-\d{4}', '[전화번호]', message)
        message = re.sub(r'\w+@\w+\.\w+', '[이메일]', message)
        return message

    def check_content_compliance(self, content, content_type="text"):
        """콘텐츠 법적 준수성 검사"""
        if not self.current_ethics_profile:
            return True, "윤리 프로필이 로드되지 않음"

        ethics = self.current_ethics_profile
        restrictions = ethics['content_restrictions'].lower()

        # 금지 키워드 검사
        forbidden_topics = []
        if "정치적" in restrictions:
            forbidden_topics.extend(["정치", "선거", "정당"])
        if "종교적" in restrictions:
            forbidden_topics.extend(["종교", "신앙"])
        if "성인" in restrictions:
            forbidden_topics.extend(["성인", "성적"])

        content_lower = content.lower()
        for topic in forbidden_topics:
            if topic in content_lower:
                return False, f"해당 지역에서 금지된 주제입니다: {topic}"

        return True, "준수함"

    def adapt_response_to_culture(self, response, country_code=None):
        """문화적 적응 응답 생성"""
        if not country_code:
            country_code = self.current_country or 'KR'

        # 국가별 문화 적응
        if country_code == 'KR':
            # 한국: 높임말과 정중한 표현
            if not response.endswith('다') and not response.endswith('요'):
                response = response.rstrip('.!?') + "습니다."
            response = response.replace("안녕", "안녕하세요")
            response = response.replace("고마워", "감사합니다")

        elif country_code == 'JP':
            # 일본: 극도로 정중한 표현
            response = response.replace(".", "。")
            if "죄송" not in response and ("안 돼" in response or "불가능" in response):
                response = "죄송하지만, " + response.lower()
            response = response.replace("감사", "아리가토")

        elif country_code in ['US', 'GB']:
            # 영어권: 직접적이고 친근한 표현
            response = response.replace("죄송하지만", "Sorry, but")
            response = response.replace("감사합니다", "Thanks!")
            if "네" in response:
                response = response.replace("네", "Yes")

        elif country_code == 'DE':
            # 독일: 매우 직접적이고 효율적인 표현
            response = response.replace("죄송하지만", "")
            response = response.replace("아마도", "")
            if "." not in response:
                response += "."

        elif country_code == 'CN':
            # 중국: 조화롭고 간접적인 표현
            if "안 돼" in response:
                response = response.replace("안 돼", "적절하지 않을 수 있습니다")
            response = response.replace("나", "저")

        elif country_code == 'FR':
            # 프랑스: 우아하고 정중한 표현
            response = response.replace("감사", "메르시")
            if not response.startswith(("죄송", "안녕")):
                response = "Bonjour! " + response

        elif country_code == 'CA':
            # 캐나다: 매우 공손하고 친근한
            response = response.replace("감사합니다", "Thank you very much, eh!")
            if "죄송" not in response and "Sorry" not in response:
                response = "Sorry, " + response.lower()

        elif country_code == 'AU':
            # 호주: 친근하고 직설적
            response = response.replace("감사합니다", "Cheers mate!")
            response = response.replace("안녕하세요", "G'day!")

        elif country_code == 'IN':
            # 인도: 정중하고 존댓말
            if not response.endswith(('다', '요', 'ji')):
                response = response.rstrip('.!?') + "ji."
            response = response.replace("감사", "धन्यवाद")

        elif country_code == 'BR':
            # 브라질: 따뜻하고 친근한
            response = response.replace("감사", "Obrigado")
            response = response.replace("안녕", "Olá")

        elif country_code == 'RU':
            # 러시아: 공식적이고 신중한
            response = response.replace("감사", "Спасибо")
            if not response.startswith("Уважаемый"):
                response = "Здравствуйте! " + response

        elif country_code == 'IT':
            # 이탈리아: 표현력 풍부하고 따뜻한
            response = response.replace("감사", "Grazie")
            response = response.replace("안녕", "Ciao")

        elif country_code == 'ES':
            # 스페인: 열정적이고 표현력 풍부한
            response = response.replace("감사", "Gracias")
            response = response.replace("안녕", "¡Hola!")

        elif country_code == 'NL':
            # 네덜란드: 직설적이고 실용적
            response = response.replace("아마도", "")
            response = response.replace("감사", "Dank je")

        elif country_code in ['SE', 'NO', 'DK']:
            # 북유럽: 겸손하고 신중한
            response = response.replace("훌륭한", "괜찮은")
            response = response.replace("최고", "좋은")
            if country_code == 'SE':
                response = response.replace("감사", "Tack")
            elif country_code == 'NO':
                response = response.replace("감사", "Takk")
            elif country_code == 'DK':
                response = response.replace("감사", "Tak")

        elif country_code == 'CH':
            # 스위스: 정확하고 절제된
            response = response.replace("아마도", "정확히")
            response = response.replace("대충", "정밀하게")

        elif country_code == 'SG':
            # 싱가포르: 정중하고 실용적
            response = response.replace("감사", "Thank you lah")

        elif country_code == 'AE':
            # 아랍에미리트: 존중하고 예의바른
            response = response.replace("안녕", "As-salamu alaykum")
            response = response.replace("감사", "Shukran")

        elif country_code == 'TH':
            # 태국: 공손하고 우회적 (와이 문화)
            response = response.replace("안녕", "สวัสดีครับ/ค่ะ")
            response = response.replace("감사", "ขอบคุณครับ/ค่ะ")
            if not response.startswith("ครับ") and not response.startswith("ค่ะ"):
                response = "ครับ/ค่ะ " + response

        elif country_code == 'VN':
            # 베트남: 예의바르고 신중한 (유교 문화)
            response = response.replace("안녕", "Xin chào")
            response = response.replace("감사", "Cảm ơn")
            if not response.endswith(('다', '요', 'ạ')):
                response = response.rstrip('.!?') + "ạ."

        elif country_code == 'MY':
            # 말레이시아: 정중하고 조화로운 (다종족)
            response = response.replace("안녕", "Selamat")
            response = response.replace("감사", "Terima kasih")

        elif country_code == 'PH':
            # 필리핀: 존댓말과 따뜻함 (Po/Opo 문화)
            response = response.replace("안녕", "Kumusta")
            response = response.replace("감사", "Salamat")
            if not response.endswith(('po', 'Po')):
                response = response.rstrip('.!?') + " po."

        elif country_code == 'ID':
            # 인도네시아: 공손하고 간접적
            response = response.replace("안녕", "Selamat")
            response = response.replace("감사", "Terima kasih")
            if "죄송" not in response:
                response = "Maaf, " + response.lower()

        elif country_code in ['MM', 'KH', 'LA']:
            # 미얀마, 캄보디아, 라오스: 불교 문화권
            if country_code == 'MM':
                response = response.replace("안녕", "မင်္ဂလာပါ")
                response = response.replace("감사", "ကျေးဇူးတင်ပါတယ်")
            elif country_code == 'KH':
                response = response.replace("안녕", "ជំរាបសួរ")
                response = response.replace("감사", "អរគុណ")
            elif country_code == 'LA':
                response = response.replace("안녕", "ສະບາຍດີ")
                response = response.replace("감사", "ຂອບໃຈ")

            # 공통: 불교적 겸손함
            response = response.replace("훌륭한", "괜찮은")
            response = response.replace("최고", "좋은")

        return response

    def get_location_aware_greeting(self):
        """위치 인식 인사말"""
        if not self.current_location:
            return "안녕하세요! 소리새입니다."

        country = self.current_location['country_code']
        city = self.current_location['city']

        greetings = {
            "KR": f"안녕하세요! {city}에서 인사드리는 소리새입니다. 정중히 도와드리겠습니다.",
            "US": f"Hey there! Sorisae here from {city}. How can I help you today?",
            "JP": f"こんにちは！{city}からご挨拶申し上げます、소리새です。",
            "CN": f"您好！我是来自{city}的소리새，很高兴为您服务。",
            "DE": f"Guten Tag! Ich bin Sorisae aus {city}. Wie kann ich Ihnen helfen?",
            "GB": f"Good day! I'm Sorisae, speaking to you from {city}. How may I assist?",
            "FR": f"Bonjour! Je suis Sorisae depuis {city}. Comment puis-je vous aider?"
        }

        return greetings.get(country, f"Hello! I'm Sorisae from {city}. How can I help you?")

    def show_ethics_dashboard(self):
        """윤리 대시보드 표시"""
        print("\n🌍 소리새 윤리의식 대시보드")
        print("=" * 60)

        if self.current_location and self.current_ethics_profile:
            location = self.current_location
            ethics = self.current_ethics_profile

            print(f"📍 현재 위치: {location['city']}, {location['country_name']}")
            print(f"🏛️ 윤리 프로필: {ethics['country_name']}")
            print(f"🛡️ 프라이버시 레벨: {ethics['privacy_level']}/10")
            print(f"💬 소통 스타일: {ethics['communication_style']}")
            print()

            print("📋 적용 중인 가이드라인:")
            print(f"  🎯 문화적 특성: {ethics['ethics_profile']}")
            print(f"  ⚖️ 법적 준수: {ethics['legal_restrictions']}")
            print(f"  🚫 콘텐츠 제한: {ethics['content_restrictions']}")
            print()

            # 최근 위치 기록
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT timestamp, city, country_code, ethics_applied
                FROM location_history
                ORDER BY timestamp DESC LIMIT 5
            ''')

            history = cursor.fetchall()
            if history:
                print("📜 최근 위치 기록:")
                for record in history:
                    timestamp = record[0][:19]  # 초까지만
                    print(f"  • {timestamp}: {record[1]} ({record[2]}) - {record[3]}")
        else:
            print("❌ 위치 정보가 없습니다. GPS 시스템을 먼저 활성화하세요.")


def demo_ethical_gps_system():
    """GPS 기반 윤리 시스템 데모"""
    print("🌍 소리새 GPS 기반 윤리의식 시스템 데모")
    print("=" * 60)

    # 윤리 GPS 시스템 초기화
    ethics_gps = EthicalGPSSystem()

    # 위치 기반 윤리 적용
    ethics_profile = ethics_gps.apply_location_based_ethics()

    if ethics_profile:
        # 위치별 인사말 테스트
        greeting = ethics_gps.get_location_aware_greeting()
        print(f"\n💬 위치 인식 인사말:")
        print(f"   {greeting}")

        # 윤리적 응답 필터링 테스트
        test_messages = [
            "안녕하세요",
            "도움이 필요해",
            "정보를 알려줘"
        ]

        print(f"\n🔄 윤리적 응답 필터링 테스트:")
        for msg in test_messages:
            filtered = ethics_gps.get_ethical_response_filter(msg)
            print(f"   원본: {msg}")
            print(f"   필터링: {filtered}")
            print()

        # 콘텐츠 준수성 검사
        test_contents = [
            "일반적인 대화입니다",
            "정치적인 내용을 포함한 메시지",
            "종교적 내용에 대한 질문"
        ]

        print(f"⚖️ 콘텐츠 법적 준수성 검사:")
        for content in test_contents:
            compliant, message = ethics_gps.check_content_compliance(content)
            status = "✅" if compliant else "❌"
            print(f"   {status} '{content}' - {message}")

        time.sleep(2)

        # 윤리 대시보드 표시
        ethics_gps.show_ethics_dashboard()

    print(f"\n🎊 GPS 기반 윤리의식 시스템 데모 완료!")
    print("소리새가 이제 전 세계 어디서든 현지 문화와 법률을 존중합니다! 🌏")


def main():
    """메인 실행 함수"""
    try:
        demo_ethical_gps_system()
    except KeyboardInterrupt:
        print("\n⏹️ 윤리 GPS 시스템 데모 중단")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
