#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 소리새 게임 컨셉 디자인 & 브랜딩 시스템
게임 이름, 컨셉, 세계관, 수익 모델 통합 설계
"""

import json
import time
from datetime import datetime


class SorisaeGameConcept:
    """소리새 게임 컨셉 및 브랜딩 매니저"""

    def __init__(self):
        self.game_concept = self.define_game_concept()
        self.branding = self.define_branding()
        self.revenue_model = self.define_revenue_model()

    def define_game_concept(self):
        """게임 핵심 컨셉 정의"""
        return {
            "main_concept": {
                "korean_name": "소리새 월드 (SoriSay World)",
                "english_name": "SoriSay World: AI Collaboration Universe",
                "tagline_kr": "AI와 함께 창조하며 수익을 얻는 세상",
                "tagline_en": "Create with AI, Earn Real Income",

                "core_philosophy": "상대성 게임 (Relativity Game)",
                "concept_description": """
                🌟 소리새 월드는 '상대성 게임' 컨셉입니다:
                - 플레이어가 놀면서도 실제 수익이 발생하는 경제 생태계
                - AI 파트너와의 창작 협업을 통한 가치 창출
                - 가상과 현실이 연결된 하이브리드 경제 시스템
                - 창의성과 생산성이 직접적인 수익으로 변환되는 구조
                """
            },

            "game_universe": {
                "setting": "미래 메타버스 경제 도시",
                "time_period": "2030년 AI 협업 시대",
                "location": "소리새 시티 (SoriSay City)",

                "world_description": """
                🏙️ 소리새 시티는 AI와 인간이 공존하는 경제 메타버스입니다:
                - 창작 구역: AI 파트너와 콘텐츠 제작
                - 거래 구역: 실시간 수익 분배 시스템
                - 협업 구역: 멀티플레이어 프로젝트 진행
                - 투자 구역: 듀얼브레인 주식 예측 시스템
                """
            },

            "gameplay_mechanics": {
                "core_activities": [
                    "AI 파트너와의 창작 협업",
                    "콘텐츠 품질 향상 미션",
                    "실시간 수익 분배 체험",
                    "듀얼브레인 주식 투자",
                    "창의성 점수 경쟁"
                ],

                "progression_system": {
                    "creativity_level": "창의성 레벨 (1-100)",
                    "ai_partnership": "AI 파트너십 단계 (Bronze-Diamond)",
                    "earning_tier": "수익 등급 (Beginner-Master)",
                    "reputation_score": "평판 점수 (0-10,000)"
                }
            }
        }

    def define_branding(self):
        """브랜딩 및 마케팅 요소"""
        return {
            "visual_identity": {
                "color_scheme": {
                    "primary": "#4A90E2",  # 소리새 블루
                    "secondary": "#7ED321",  # 성장 그린
                    "accent": "#F5A623",  # 골드 수익
                    "background": "#2C3E50"  # 다크 베이스
                },

                "logo_concept": "🐦 소리새 + 💰 동전 + 🤖 AI 조합",
                "mascot": "소리새 캐릭터 '쏘리' (Sori the Bird)"
            },

            "marketing_messages": {
                "value_proposition": "게임하면서 실제 돈을 벌 수 있는 유일한 플랫폼",
                "target_audience": "창의적 콘텐츠 제작자, AI 협업 관심자, 부수입 추구자",

                "key_selling_points": [
                    "월 $150-225 실제 수익 보장",
                    "AI 파트너와의 창의적 협업",
                    "놀면서 배우는 투자 시스템",
                    "실시간 수익 분배 체험"
                ]
            }
        }

    def define_revenue_model(self):
        """상세 수익 모델 정의"""
        return {
            "player_earning_streams": {
                "content_creation": {
                    "description": "AI와 협업한 콘텐츠 제작",
                    "earning_rate": "$15-25 per content",
                    "frequency": "Daily",
                    "monthly_potential": "$450-750"
                },

                "advertisement_sharing": {
                    "description": "게임 내 광고 수익 70% 분배",
                    "earning_rate": "$0.50-2.00 per view",
                    "frequency": "Per interaction",
                    "monthly_potential": "$150-600"
                },

                "quality_bonuses": {
                    "description": "고품질 창작물 보너스",
                    "earning_rate": "20-50% bonus",
                    "frequency": "Per quality content",
                    "monthly_potential": "$100-300"
                },

                "investment_returns": {
                    "description": "듀얼브레인 주식 예측 수익",
                    "earning_rate": "5-15% returns",
                    "frequency": "Weekly",
                    "monthly_potential": "$50-200"
                }
            },

            "business_model": {
                "revenue_sources": [
                    "광고 파트너십 (30% 플랫폼 수수료)",
                    "프리미엄 AI 파트너 구독",
                    "고급 투자 도구 판매",
                    "기업 창작 서비스 제공"
                ],

                "sustainability": "70% 수익 분배로 플레이어 충성도 확보"
            }
        }


class GameConceptDemo:
    """게임 컨셉 데모 시스템"""

    def __init__(self):
        self.concept = SorisaeGameConcept()

    def display_concept_overview(self):
        """컨셉 개요 표시"""
        concept = self.concept.game_concept['main_concept']
        print("=" * 60)
        print("🎮 소리새 월드 (SoriSay World) - 게임 컨셉")
        print("=" * 60)
        print(f"📌 한글명: {concept['korean_name']}")
        print(f"🌍 영문명: {concept['english_name']}")
        print(f"💫 태그라인: {concept['tagline_kr']}")
        print(f"🎯 핵심 철학: {concept['core_philosophy']}")
        print()
        print("📋 컨셉 설명:")
        print(concept['concept_description'])

    def display_world_setting(self):
        """세계관 설정 표시"""
        world = self.concept.game_concept['game_universe']
        print("\n" + "=" * 60)
        print("🌎 게임 세계관 & 설정")
        print("=" * 60)
        print(f"🏙️ 배경: {world['setting']}")
        print(f"⏰ 시대: {world['time_period']}")
        print(f"📍 장소: {world['location']}")
        print()
        print("🌟 세계 설명:")
        print(world['world_description'])

    def display_gameplay_mechanics(self):
        """게임플레이 메커니즘 표시"""
        gameplay = self.concept.game_concept['gameplay_mechanics']
        print("\n" + "=" * 60)
        print("🎮 게임플레이 메커니즘")
        print("=" * 60)
        print("🎯 핵심 활동들:")
        for i, activity in enumerate(gameplay['core_activities'], 1):
            print(f"  {i}. {activity}")

        print("\n📈 성장 시스템:")
        progression = gameplay['progression_system']
        for key, value in progression.items():
            print(f"  • {value}")

    def display_revenue_projection(self):
        """수익 예상 표시"""
        revenue = self.concept.revenue_model['player_earning_streams']
        print("\n" + "=" * 60)
        print("💰 플레이어 수익 모델")
        print("=" * 60)

        total_min = 0
        total_max = 0

        for stream_name, details in revenue.items():
            print(f"\n💵 {details['description']}:")
            print(f"   📊 수익률: {details['earning_rate']}")
            print(f"   🔄 빈도: {details['frequency']}")
            print(f"   💎 월 예상: {details['monthly_potential']}")

            # 월 예상 수익에서 숫자 추출
            potential = details['monthly_potential']
            if '$' in potential and '-' in potential:
                min_val = int(potential.split('$')[1].split('-')[0])
                max_val = int(potential.split('-')[1])
                total_min += min_val
                total_max += max_val

        print(f"\n🎯 총 월 수익 예상: ${total_min}-{total_max}")
        print(f"💡 평균 예상 수익: ${(total_min + total_max) // 2}")

    def display_branding_identity(self):
        """브랜딩 아이덴티티 표시"""
        branding = self.concept.branding
        print("\n" + "=" * 60)
        print("🎨 브랜딩 & 마케팅 아이덴티티")
        print("=" * 60)

        visual = branding['visual_identity']
        print("🎨 비주얼 아이덴티티:")
        print(f"   🎯 메인 컬러: {visual['color_scheme']['primary']} (소리새 블루)")
        print(f"   🌱 서브 컬러: {visual['color_scheme']['secondary']} (성장 그린)")
        print(f"   ✨ 포인트 컬러: {visual['color_scheme']['accent']} (골드 수익)")
        print(f"   🖤 베이스 컬러: {visual['color_scheme']['background']} (다크 베이스)")
        print(f"   🐦 로고 컨셉: {visual['logo_concept']}")
        print(f"   🎭 마스코트: {visual['mascot']}")

        marketing = branding['marketing_messages']
        print(f"\n📢 핵심 가치 제안:")
        print(f"   {marketing['value_proposition']}")
        print(f"\n🎯 타겟 오디언스:")
        print(f"   {marketing['target_audience']}")

        print(f"\n⭐ 주요 셀링 포인트:")
        for i, point in enumerate(marketing['key_selling_points'], 1):
            print(f"   {i}. {point}")

    def run_concept_presentation(self):
        """전체 컨셉 프레젠테이션 실행"""
        print("🚀 소리새 월드 - 게임 컨셉 프레젠테이션 시작!")
        print("   (AI와 함께 창조하며 수익을 얻는 상대성 게임)")
        time.sleep(2)

        self.display_concept_overview()
        time.sleep(3)

        self.display_world_setting()
        time.sleep(3)

        self.display_gameplay_mechanics()
        time.sleep(3)

        self.display_revenue_projection()
        time.sleep(3)

        self.display_branding_identity()

        print("\n" + "=" * 60)
        print("✨ 소리새 월드 컨셉 프레젠테이션 완료!")
        print("🎮 상대성 게임의 새로운 패러다임을 제시합니다!")
        print("💰 놀면서도 실제 수익을 얻을 수 있는 혁신적 플랫폼")
        print("=" * 60)


def main():
    """메인 실행 함수"""
    print("🎯 소리새 월드 게임 컨셉 디자인 시스템")
    print("=" * 50)

    demo = GameConceptDemo()

    while True:
        print("\n📋 메뉴를 선택하세요:")
        print("1. 🎮 전체 컨셉 프레젠테이션")
        print("2. 📌 게임 컨셉 개요")
        print("3. 🌎 세계관 & 설정")
        print("4. 🎯 게임플레이 메커니즘")
        print("5. 💰 수익 모델")
        print("6. 🎨 브랜딩 아이덴티티")
        print("7. 💾 컨셉 데이터 저장")
        print("0. 🚪 종료")

        choice = input("\n선택: ").strip()

        if choice == "1":
            demo.run_concept_presentation()
        elif choice == "2":
            demo.display_concept_overview()
        elif choice == "3":
            demo.display_world_setting()
        elif choice == "4":
            demo.display_gameplay_mechanics()
        elif choice == "5":
            demo.display_revenue_projection()
        elif choice == "6":
            demo.display_branding_identity()
        elif choice == "7":
            # 컨셉 데이터를 JSON으로 저장
            with open('sorisae_game_concept_data.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'game_concept': demo.concept.game_concept,
                    'branding': demo.concept.branding,
                    'revenue_model': demo.concept.revenue_model,
                    'created_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            print("💾 컨셉 데이터가 'sorisae_game_concept_data.json'에 저장되었습니다!")
        elif choice == "0":
            print("👋 소리새 월드 컨셉 시스템을 종료합니다!")
            break
        else:
            print("❌ 잘못된 선택입니다. 다시 입력해주세요.")


if __name__ == "__main__":
    main()
