#!/usr/bin/env python3
"""
🌟 통합 AI 시스템 런처
Shopping Mall + AI Tutor + AI Designer Launcher

간편하게 통합 시스템을 실행하고 관리할 수 있는 인터랙티브 런처
"""

import sys
from integrated_shopping_tutor_designer import (
    IntegratedAISystem,
    AutonomousShoppingMall,
    PersonalAITutor,
    AIDesigner
)


def print_banner():
    """배너 출력"""
    print("\n" + "=" * 80)
    print("🌟 통합 AI 시스템: 쇼핑몰 + AI 튜터 + AI 디자이너")
    print("=" * 80)
    print("3개의 AI 시스템이 하나로! 완전 자율 운영 플랫폼")
    print("=" * 80 + "\n")


def print_menu():
    """메인 메뉴 출력"""
    print("\n📋 메인 메뉴")
    print("-" * 80)
    print("1. 🚀 통합 시스템 데모 실행")
    print("2. 🛒 쇼핑몰 단독 실행")
    print("3. 🎓 AI 튜터 단독 실행")
    print("4. 🎨 AI 디자이너 단독 실행")
    print("5. 📊 시스템 대시보드 보기")
    print("6. 💡 통합 워크플로우 실행")
    print("0. 🚪 종료")
    print("-" * 80)


def run_integrated_demo():
    """통합 시스템 데모"""
    print("\n" + "=" * 80)
    print("🚀 통합 시스템 데모 실행")
    print("=" * 80)
    
    system = IntegratedAISystem()
    system.start_autonomous_system()
    
    # 통합 상품 생성
    print("\n🌟 통합 상품 생성 데모...")
    result = system.create_integrated_product("AI 스마트 글래스")
    print(f"\n✅ 결과:")
    print(f"  상품명: {result['product']['name']}")
    print(f"  가격: {result['product']['price']:,}원")
    print(f"  디자인: {result['design']['style']}")
    print(f"  협업 점수: {result['collaboration_score']}/100")
    
    # 대시보드
    print("\n📊 시스템 대시보드:")
    dashboard = system.get_system_dashboard()
    print(f"  쇼핑몰 매출: {dashboard['쇼핑몰']['총_매출']:,}원")
    print(f"  활성 상품: {dashboard['쇼핑몰']['활성_상품']}개")
    print(f"  총 디자인: {dashboard['AI_디자이너']['총_디자인']}개")


def run_shopping_mall():
    """쇼핑몰 단독 실행"""
    print("\n" + "=" * 80)
    print("🛒 자율 쇼핑몰 실행")
    print("=" * 80)
    
    mall = AutonomousShoppingMall()
    
    print("\n1️⃣ 시장 동향 분석 중...")
    trends = mall.analyze_market_trends()
    print(f"  분석 완료: {len(trends)}개 카테고리")
    
    print("\n2️⃣ 신규 상품 기획 중...")
    product = mall.ai_product_planning()
    print(f"  상품명: {product['name']}")
    print(f"  카테고리: {product['category']}")
    print(f"  가격: {product['price']:,}원")
    
    print("\n3️⃣ 상품 출시 중...")
    result = mall.launch_product(product)
    print(f"  {result['message']}")
    print(f"  초기 재고: {result['initial_stock']}개")
    
    print("\n4️⃣ 자동 판매 실행 중...")
    sales = mall.ai_auto_selling()
    if sales:
        total_revenue = sum(s['revenue'] for s in sales)
        total_sales = sum(s['sales_count'] for s in sales)
        print(f"  판매 완료: {total_sales}건")
        print(f"  매출: {total_revenue:,}원")
    else:
        print("  현재 판매 가능한 상품이 없습니다.")


def run_ai_tutor():
    """AI 튜터 단독 실행"""
    print("\n" + "=" * 80)
    print("🎓 AI 튜터 실행")
    print("=" * 80)
    
    tutor = PersonalAITutor()
    
    print("\n📚 개인 맞춤 학습 경로:")
    learning_path = tutor.suggest_learning_path()
    for i, step in enumerate(learning_path, 1):
        print(f"  {i}. {step}")
    
    print("\n🎯 오늘의 도전 과제:")
    challenge = tutor.generate_personalized_challenge()
    print(f"  {challenge}")
    
    print("\n💪 격려 메시지:")
    encouragement = tutor.get_personalized_encouragement()
    print(f"  {encouragement}")
    
    print("\n📊 학습 현황:")
    profile = tutor.user_profile
    print(f"  레벨: {profile['skill_level']}")
    print(f"  학습 스타일: {profile['learning_style']}")
    print(f"  세션 수: {profile['session_count']}회")
    print(f"  총 학습 시간: {profile['total_learning_time']}분")


def run_ai_designer():
    """AI 디자이너 단독 실행"""
    print("\n" + "=" * 80)
    print("🎨 AI 디자이너 실행")
    print("=" * 80)
    
    designer = AIDesigner()
    
    print("\n1️⃣ 디자인 트렌드 분석 중...")
    trends = designer.analyze_design_trends()
    print("  인기 트렌드:")
    for trend, data in list(trends.items())[:3]:
        print(f"    • {trend}: 인기도 {data['popularity']}%")
    
    print("\n2️⃣ 컬러 팔레트 생성 중...")
    palette = designer.generate_color_palette("modern")
    print("  모던 스타일 팔레트:")
    print(f"    Primary: {palette['primary']}")
    print(f"    Secondary: {palette['secondary']}")
    print(f"    Accent: {palette['accent']}")
    
    print("\n3️⃣ 제품 디자인 생성 중...")
    design = designer.design_product_mockup("프리미엄 이어폰", "전자제품")
    print(f"  디자인 ID: {design['design_id']}")
    print(f"  스타일: {design['style']}")
    print(f"  접근성 점수: {design['accessibility_score']}/100")
    
    print("\n4️⃣ 브랜딩 패키지 생성 중...")
    branding = designer.create_branding_package("테크노바", "기술")
    print(f"  브랜드: {branding['brand_name']}")
    print(f"  톤앤매너: {branding['brand_voice']['tone']}")
    print(f"  로고 컨셉: {len(branding['logo_concepts'])}종")


def show_dashboard():
    """시스템 대시보드"""
    print("\n" + "=" * 80)
    print("📊 통합 시스템 대시보드")
    print("=" * 80)
    
    system = IntegratedAISystem()
    dashboard = system.get_system_dashboard()
    
    print("\n🛒 쇼핑몰 현황:")
    for key, value in dashboard["쇼핑몰"].items():
        if isinstance(value, (int, float)):
            print(f"  {key}: {value:,}" if isinstance(value, int) else f"  {key}: {value:.1f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n🎓 AI 튜터 현황:")
    for key, value in dashboard["AI_튜터"].items():
        print(f"  {key}: {value}")
    
    print("\n🎨 AI 디자이너 현황:")
    for key, value in dashboard["AI_디자이너"].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.1f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n🌟 통합 시스템 지표:")
    for key, value in dashboard["통합_지표"].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.1f}")
        else:
            print(f"  {key}: {value}")


def run_integrated_workflows():
    """통합 워크플로우 실행"""
    print("\n" + "=" * 80)
    print("💡 통합 워크플로우 메뉴")
    print("=" * 80)
    print("\n1. 신제품 출시 (디자인 + 기획 + 출시 + 브랜딩)")
    print("2. 교육 상품 만들기 (커리큘럼 + 플랫폼 + 등록)")
    print("3. 마케팅 캠페인 실행 (디자인 + 캠페인)")
    print("4. 창업자 학습 프로그램")
    print("0. 돌아가기")
    
    choice = input("\n선택: ").strip()
    
    system = IntegratedAISystem()
    
    if choice == "1":
        product_name = input("\n제품명을 입력하세요: ").strip() or "AI 스마트 밴드"
        print(f"\n🌟 '{product_name}' 출시 프로세스 시작...")
        result = system.create_integrated_product(product_name)
        print(f"\n✅ 완료!")
        print(f"  상품명: {result['product']['name']}")
        print(f"  가격: {result['product']['price']:,}원")
        print(f"  디자인: {result['design']['style']}")
        
    elif choice == "2":
        course_name = input("\n강좌명을 입력하세요: ").strip() or "웹 개발 마스터"
        print(f"\n🎓 '{course_name}' 생성 중...")
        result = system.launch_educational_product(course_name)
        print(f"\n✅ 완료!")
        print(f"  코스명: {result['product']['name']}")
        print(f"  가격: {result['product']['price']:,}원")
        print(f"  커리큘럼: {len(result['curriculum'])}개 모듈")
        
    elif choice == "3":
        if system.shopping_mall.products:
            print(f"\n📢 마케팅 캠페인 실행 중...")
            result = system.run_marketing_campaign(
                "특별 할인 이벤트",
                system.shopping_mall.products[0]["id"]
            )
            print(f"\n✅ 완료!")
            print(f"  캠페인: {result['campaign_name']}")
            print(f"  예상 매출 증대: {result['estimated_sales_boost']}")
        else:
            print("\n⚠️  먼저 상품을 출시해주세요.")
            
    elif choice == "4":
        print(f"\n👔 창업자 맞춤형 학습 프로그램")
        result = system.personalized_learning_for_entrepreneurs()
        print(f"\n✅ 프로그램 준비 완료!")
        print(f"\n학습 경로:")
        for i, step in enumerate(result['learning_path'], 1):
            print(f"  {i}. {step}")
        print(f"\n도전 과제: {result['challenge']}")
        print(f"예상 기간: {result['estimated_completion']}")


def main():
    """메인 함수"""
    print_banner()
    
    while True:
        print_menu()
        choice = input("\n선택하세요 (0-6): ").strip()
        
        if choice == "0":
            print("\n👋 통합 AI 시스템을 종료합니다. 감사합니다!")
            sys.exit(0)
            
        elif choice == "1":
            run_integrated_demo()
            
        elif choice == "2":
            run_shopping_mall()
            
        elif choice == "3":
            run_ai_tutor()
            
        elif choice == "4":
            run_ai_designer()
            
        elif choice == "5":
            show_dashboard()
            
        elif choice == "6":
            run_integrated_workflows()
            
        else:
            print("\n❌ 잘못된 선택입니다. 0-6 사이의 숫자를 입력하세요.")
        
        input("\n⏎ 계속하려면 Enter를 누르세요...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1)
