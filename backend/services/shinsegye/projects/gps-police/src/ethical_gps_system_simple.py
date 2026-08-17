#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌍 소리새 GPS 기반 윤리의식 및 국가별 법률 준수 시스템 (간소화 버전)
위치 기반으로 해당 국가의 법률과 문화적 윤리 기준을 자동 적용
"""

import time


class EthicalGPSSystem:
    """GPS 기반 윤리의식 및 법률 준수 시스템 (간소화 버전)"""

    def __init__(self):
        """윤리 GPS 시스템 초기화"""
        self.current_location = None
        self.current_country = 'KR'  # 기본값: 한국
        self.current_ethics_profile = None

        # 국가별 윤리 및 법률 데이터베이스 로드
        self.load_country_ethics_database()

        # 기본 윤리 프로파일 설정
        self.set_default_ethics_profile()

        print("🌍 소리새 GPS 기반 윤리의식 시스템이 초기화되었습니다!")

    def load_country_ethics_database(self):
        """국가별 윤리 데이터베이스 로드"""
        self.country_ethics = {
            'KR': {
                'country_name': '대한민국',
                'privacy_level': 8,
                'restricted_topics': ['정치적 비판'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'high',
                    'style': 'respectful'
                },
                'content_restrictions': '개인정보 보호법 준수',
                'legal_framework': 'KPIPA'
            },
            'US': {
                'country_name': '미국',
                'privacy_level': 6,
                'restricted_topics': ['medical_advice'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'medium',
                    'style': 'direct'
                },
                'content_restrictions': 'COPPA, HIPAA 준수',
                'legal_framework': 'Federal Privacy Laws'
            },
            'JP': {
                'country_name': '일본',
                'privacy_level': 9,
                'restricted_topics': ['personal_info', '정치적 의견'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'very_high',
                    'style': 'extremely_polite'
                },
                'content_restrictions': '개인정보보호법 준수',
                'legal_framework': 'APPI'
            },
            'DE': {
                'country_name': '독일',
                'privacy_level': 9,
                'restricted_topics': ['hate_speech', 'holocaust_denial'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'high',
                    'style': 'direct_efficient'
                },
                'content_restrictions': 'GDPR 엄격 준수',
                'legal_framework': 'GDPR + BDSG'
            },
            'CN': {
                'country_name': '중국',
                'privacy_level': 7,
                'restricted_topics': ['정치적 비판', 'government_criticism', 'censored_content'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'high',
                    'style': 'harmonious'
                },
                'content_restrictions': '사이버보안법 준수',
                'legal_framework': 'Cybersecurity Law'
            },
            'GB': {
                'country_name': '영국',
                'privacy_level': 8,
                'restricted_topics': ['defamation'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'medium',
                    'style': 'polite_reserved'
                },
                'content_restrictions': 'UK GDPR 준수',
                'legal_framework': 'UK GDPR + DPA 2018'
            },
            'FR': {
                'country_name': '프랑스',
                'privacy_level': 8,
                'restricted_topics': ['hate_speech'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'high',
                    'style': 'elegant_formal'
                },
                'content_restrictions': 'GDPR + 프랑스 개인정보보호법',
                'legal_framework': 'GDPR + Loi Informatique'
            },
            'CA': {
                'country_name': '캐나다',
                'privacy_level': 8,
                'restricted_topics': ['hate_speech'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'medium',
                    'style': 'polite_friendly'
                },
                'content_restrictions': 'PIPEDA 준수',
                'legal_framework': 'PIPEDA + Privacy Laws'
            },
            'AU': {
                'country_name': '호주',
                'privacy_level': 7,
                'restricted_topics': ['discrimination'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'low',
                    'style': 'friendly_direct'
                },
                'content_restrictions': '프라이버시법 준수',
                'legal_framework': 'Privacy Act 1988'
            },
            'IN': {
                'country_name': '인도',
                'privacy_level': 6,
                'restricted_topics': ['religious_sensitivity', 'caste'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'high',
                    'style': 'respectful_hierarchical'
                },
                'content_restrictions': '정보기술법 준수',
                'legal_framework': 'IT Act + DPDP Act'
            },
            'BR': {
                'country_name': '브라질',
                'privacy_level': 7,
                'restricted_topics': ['child_protection'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'medium',
                    'style': 'warm_social'
                },
                'content_restrictions': 'LGPD 준수',
                'legal_framework': 'LGPD'
            },
            'RU': {
                'country_name': '러시아',
                'privacy_level': 5,
                'restricted_topics': ['political_criticism', 'extremism'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'high',
                    'style': 'formal_cautious'
                },
                'content_restrictions': '개인정보법 준수',
                'legal_framework': 'Federal Law 152-FZ'
            },
            'IT': {
                'country_name': '이탈리아',
                'privacy_level': 8,
                'restricted_topics': ['family_values'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'medium',
                    'style': 'expressive_warm'
                },
                'content_restrictions': 'GDPR + 이탈리아법',
                'legal_framework': 'GDPR + D.Lgs 196/2003'
            },
            'ES': {
                'country_name': '스페인',
                'privacy_level': 8,
                'restricted_topics': ['regional_separatism'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'medium',
                    'style': 'passionate_expressive'
                },
                'content_restrictions': 'GDPR + 스페인법',
                'legal_framework': 'GDPR + LOPD-GDD'
            },
            'NL': {
                'country_name': '네덜란드',
                'privacy_level': 9,
                'restricted_topics': ['discrimination'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'low',
                    'style': 'direct_practical'
                },
                'content_restrictions': 'GDPR + 네덜란드법',
                'legal_framework': 'GDPR + UAVG'
            },
            'SE': {
                'country_name': '스웨덴',
                'privacy_level': 10,
                'restricted_topics': ['gender_discrimination'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'medium',
                    'style': 'humble_cautious'
                },
                'content_restrictions': 'GDPR + 스웨덴법',
                'legal_framework': 'GDPR + Dataskyddsförordningen'
            },
            'CH': {
                'country_name': '스위스',
                'privacy_level': 10,
                'restricted_topics': ['political_bias'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'high',
                    'style': 'precise_neutral'
                },
                'content_restrictions': '스위스 데이터보호법',
                'legal_framework': 'Swiss Data Protection Act'
            },
            'SG': {
                'country_name': '싱가포르',
                'privacy_level': 7,
                'restricted_topics': ['racial_harmony', 'government_criticism'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'medium',
                    'style': 'polite_efficient'
                },
                'content_restrictions': '개인정보보호법 준수',
                'legal_framework': 'PDPA'
            },
            'TH': {
                'country_name': '태국',
                'privacy_level': 6,
                'restricted_topics': ['royal_family', 'buddhism_disrespect'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'high',
                    'style': 'polite_indirect'
                },
                'content_restrictions': '왕실모독죄, 불교 존중',
                'legal_framework': 'Personal Data Protection Act'
            },
            'VN': {
                'country_name': '베트남',
                'privacy_level': 5,
                'restricted_topics': ['political_criticism', 'government_policy'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'high',
                    'style': 'respectful_cautious'
                },
                'content_restrictions': '사이버보안법 준수',
                'legal_framework': 'Cybersecurity Law'
            },
            'MY': {
                'country_name': '말레이시아',
                'privacy_level': 6,
                'restricted_topics': ['racial_harmony', 'religious_sensitivity'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'medium',
                    'style': 'harmonious_polite'
                },
                'content_restrictions': '다종족 조화 우선',
                'legal_framework': 'Personal Data Protection Act'
            },
            'PH': {
                'country_name': '필리핀',
                'privacy_level': 6,
                'restricted_topics': ['family_values', 'child_protection'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'high',
                    'style': 'respectful_warm'
                },
                'content_restrictions': '가족 가치 존중',
                'legal_framework': 'Data Privacy Act'
            },
            'ID': {
                'country_name': '인도네시아',
                'privacy_level': 6,
                'restricted_topics': ['religious_sensitivity', 'SARA_issues'],
                'cultural_adaptations': {
                    'honorifics': False,
                    'formality': 'medium',
                    'style': 'polite_indirect'
                },
                'content_restrictions': 'SARA 이슈 주의',
                'legal_framework': 'Personal Data Protection Law'
            },
            'MM': {
                'country_name': '미얀마',
                'privacy_level': 4,
                'restricted_topics': ['political_sensitivity', 'military_government'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'high',
                    'style': 'humble_traditional'
                },
                'content_restrictions': '정치적 민감성',
                'legal_framework': 'Electronic Transaction Law'
            },
            'KH': {
                'country_name': '캄보디아',
                'privacy_level': 4,
                'restricted_topics': ['royal_family', 'political_criticism'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'high',
                    'style': 'respectful_traditional'
                },
                'content_restrictions': '왕실 존경',
                'legal_framework': 'Cybercrime Law'
            },
            'LA': {
                'country_name': '라오스',
                'privacy_level': 4,
                'restricted_topics': ['political_criticism', 'government_policy'],
                'cultural_adaptations': {
                    'honorifics': True,
                    'formality': 'medium',
                    'style': 'peaceful_harmonious'
                },
                'content_restrictions': '정치적 신중함',
                'legal_framework': 'Cybercrime Law'
            }
        }

    def set_default_ethics_profile(self):
        """기본 윤리 프로파일 설정"""
        if self.current_country in self.country_ethics:
            self.current_ethics_profile = self.country_ethics[self.current_country]
        else:
            # 기본값: 한국
            self.current_ethics_profile = self.country_ethics['KR']
            self.current_country = 'KR'

    def get_current_ethics_profile(self):
        """현재 윤리 프로파일 반환"""
        if not self.current_ethics_profile:
            self.set_default_ethics_profile()

        return {
            'country': self.current_country,
            'privacy_level': self.current_ethics_profile.get('privacy_level', 8),
            'restricted_topics': self.current_ethics_profile.get('restricted_topics', []),
            'cultural_style': self.current_ethics_profile.get('cultural_adaptations', {}).get('style', 'respectful')
        }

    def check_content_compliance(self, content, content_type="text"):
        """콘텐츠 법적 준수성 검사"""
        if not self.current_ethics_profile:
            return True, "윤리 프로필이 로드되지 않음"

        restrictions = self.current_ethics_profile.get('restricted_topics', [])
        content_lower = content.lower()

        # 금지 주제 검사
        for topic in restrictions:
            if topic.lower() in content_lower:
                return False, f"해당 지역({self.current_country})에서 금지된 주제입니다: {topic}"

        return True, "준수함"

    def adapt_response_to_culture(self, response, country_code=None):
        """문화적 적응 응답 생성"""
        if not country_code:
            country_code = self.current_country or 'KR'

        # 국가별 문화 적응
        if country_code == 'KR':
            # 한국: 높임말과 정중한 표현
            if not response.endswith(('다', '요', '까요', '세요')):
                response = response.rstrip('.!?') + "습니다."
            response = response.replace("안녕", "안녕하세요")
            response = response.replace("고마워", "감사합니다")
            response = response.replace("미안", "죄송합니다")

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
            if "." not in response and "!" not in response:
                response += "."

        elif country_code == 'CN':
            # 중국: 조화롭고 간접적인 표현
            if "안 돼" in response:
                response = response.replace("안 돼", "적절하지 않을 수 있습니다")
            response = response.replace("나", "저")

        elif country_code == 'FR':
            # 프랑스: 우아하고 정중한 표현
            response = response.replace("감사", "메르시")
            if not response.startswith(("죄송", "안녕", "Bonjour")):
                response = "Bonjour! " + response

        elif country_code == 'CA':
            # 캐나다: 매우 공손하고 친근한
            response = response.replace("감사합니다", "Thank you, eh!")
            if "Sorry" not in response:
                response = "Sorry, " + response.lower()

        elif country_code == 'AU':
            # 호주: 친근하고 직설적
            response = response.replace("감사합니다", "Cheers mate!")
            response = response.replace("안녕하세요", "G'day!")

        elif country_code == 'IN':
            # 인도: 정중하고 존댓말 (계층적)
            if not response.endswith(('다', '요', 'ji')):
                response = response.rstrip('.!?') + "ji."
            response = response.replace("감사", "Namaste")

        elif country_code == 'BR':
            # 브라질: 따뜻하고 친근한
            response = response.replace("감사", "Obrigado")
            response = response.replace("안녕", "Olá")

        elif country_code == 'RU':
            # 러시아: 공식적이고 신중한
            response = response.replace("감사", "Спасибо")
            response = "Здравствуйте! " + response

        elif country_code == 'IT':
            # 이탈리아: 표현력 풍부하고 따뜻한
            response = response.replace("감사", "Grazie mille!")
            response = response.replace("안녕", "Ciao bella!")

        elif country_code == 'ES':
            # 스페인: 열정적이고 표현력 풍부한
            response = response.replace("감사", "¡Muchas gracias!")
            response = response.replace("안녕", "¡Hola!")

        elif country_code == 'NL':
            # 네덜란드: 직설적이고 실용적
            response = response.replace("아마도", "")
            response = response.replace("감사", "Dank je wel")

        elif country_code == 'SE':
            # 스웨덴: 겸손하고 신중한
            response = response.replace("훌륭한", "괜찮은")
            response = response.replace("감사", "Tack så mycket")

        elif country_code == 'CH':
            # 스위스: 정확하고 절제된
            response = response.replace("아마도", "정확히")
            response = response.replace("대충", "정밀하게")

        elif country_code == 'SG':
            # 싱가포르: 정중하고 실용적
            response = response.replace("감사", "Thank you lah")

        elif country_code == 'TH':
            # 태국: 와이 문화, 공손함
            response = response.replace("안녕", "สวัสดีครับ")
            response = response.replace("감사", "ขอบคุณครับ")

        elif country_code == 'VN':
            # 베트남: 유교 문화, 존댓말
            response = response.replace("안녕", "Xin chào")
            response = response.replace("감사", "Cảm ơn")
            if not response.endswith('ạ'):
                response = response.rstrip('.!?') + "ạ."

        elif country_code == 'MY':
            # 말레이시아: 다종족 조화
            response = response.replace("안녕", "Selamat")
            response = response.replace("감사", "Terima kasih")

        elif country_code == 'PH':
            # 필리핀: 존댓말 문화 (Po/Opo)
            response = response.replace("안녕", "Kumusta")
            response = response.replace("감사", "Salamat")
            if not response.endswith(" po."):
                response = response.rstrip('.!?') + " po."

        elif country_code == 'ID':
            # 인도네시아: 공손하고 간접적
            response = response.replace("안녕", "Selamat")
            response = response.replace("감사", "Terima kasih")

        elif country_code in ['MM', 'KH', 'LA']:
            # 미얀마, 캄보디아, 라오스: 불교 문화권
            if country_code == 'MM':
                response = response.replace("안녕", "မင်္ဂလာပါ")
            elif country_code == 'KH':
                response = response.replace("안녕", "ជំរាបសួរ")
            elif country_code == 'LA':
                response = response.replace("안녕", "ສະບາຍດີ")
            # 불교적 겸손함
            response = response.replace("최고", "좋은")

        return response

    def get_location_aware_greeting(self):
        """위치 인식 인사말"""
        country_name = self.current_ethics_profile.get('country_name', '알 수 없는 지역')

        greetings = {
            'KR': f"안녕하세요! {country_name}에서 접속하신 소리새입니다.",
            'JP': f"こんにちは! {country_name}からアクセスの소리새です。",
            'US': f"Hello! Sorisae here, connecting from {country_name}.",
            'GB': f"Good day! Sorisae here, accessing from {country_name}.",
            'DE': f"Guten Tag! Sorisae hier, Zugriff aus {country_name}.",
            'CN': f"您好! 来自{country_name}的소리새。",
            'FR': f"Bonjour! Sorisae ici, accédant depuis {country_name}."
        }

        return greetings.get(self.current_country, greetings['KR'])

    def simulate_location_change(self, country_code):
        """위치 변경 시뮬레이션 (테스트용)"""
        if country_code in self.country_ethics:
            self.current_country = country_code
            self.current_ethics_profile = self.country_ethics[country_code]
            print(f"📍 위치 변경됨: {self.current_ethics_profile['country_name']} ({country_code})")
        else:
            print(f"⚠️ 지원하지 않는 국가 코드: {country_code}")

    def show_ethics_dashboard(self):
        """현재 윤리 설정 대시보드"""
        print(f"\n🌍 === 소리새 윤리 GPS 대시보드 ===")
        print(f"📍 현재 위치: {self.current_ethics_profile['country_name']} ({self.current_country})")
        print(f"🔒 프라이버시 레벨: {self.current_ethics_profile['privacy_level']}/10")
        print(f"🚫 제한 주제: {len(self.current_ethics_profile['restricted_topics'])}개")
        print(f"📜 법적 프레임워크: {self.current_ethics_profile['legal_framework']}")
        print(f"🎭 문화적 스타일: {self.current_ethics_profile['cultural_adaptations']['style']}")

        if self.current_ethics_profile['restricted_topics']:
            print(f"   제한 주제 목록: {', '.join(self.current_ethics_profile['restricted_topics'])}")

        print("=" * 40)


def demo_ethical_gps_system():
    """윤리 GPS 시스템 데모"""
    print("🌍 === 소리새 윤리 GPS 시스템 데모 ===")

    # 시스템 초기화
    ethics_gps = EthicalGPSSystem()

    # 현재 상태 표시
    ethics_gps.show_ethics_dashboard()

    # 다양한 국가로 이동 시뮬레이션
    countries = ['KR', 'US', 'JP', 'DE', 'CN', 'GB', 'FR', 'CA', 'AU', 'IN', 'BR', 'RU',
                 'IT', 'ES', 'NL', 'SE', 'CH', 'SG', 'TH', 'VN', 'MY', 'PH', 'ID', 'MM', 'KH', 'LA']

    for country in countries:
        print(f"\n🛫 {country}로 이동 중...")
        time.sleep(1)

        ethics_gps.simulate_location_change(country)

        # 위치별 인사말
        greeting = ethics_gps.get_location_aware_greeting()
        print(f"💬 {greeting}")

        # 문화 적응 테스트
        test_response = "감사합니다! 도움을 드리겠습니다."
        adapted = ethics_gps.adapt_response_to_culture(test_response, country)
        print(f"🎭 문화 적응: '{adapted}'")

        # 윤리 프로파일 확인
        profile = ethics_gps.get_current_ethics_profile()
        print(f"📊 프라이버시 레벨: {profile['privacy_level']}, 제한 주제: {len(profile['restricted_topics'])}개")

        time.sleep(1)


if __name__ == "__main__":
    demo_ethical_gps_system()
