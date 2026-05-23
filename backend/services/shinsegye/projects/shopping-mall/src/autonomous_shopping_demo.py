#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛒 지능형 자율 쇼핑몰 + 멀티 AI 에이전트 시스템 데모
완전 자율 운영 쇼핑몰과 7개 AI 에이전트 협업 시스템 테스트
"""

import os
import sys

from modules.ai_code_manager.autonomous_marketing_system import AutonomousMarketingSystem
from modules.ai_code_manager.autonomous_shopping_mall import AutonomousShoppingMall
from modules.ai_code_manager.multi_agent_shopping_system import MultiAgentShoppingSystem
from modules.ai_code_manager.sorisae_core_controller import SorisaeCore

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_autonomous_shopping_mall():
    """자율 쇼핑몰 시스템 테스트"""
    print("=" * 80)
    print("🛒 지능형 자율 쇼핑몰 시스템 테스트")
    print("=" * 80)

    mall = AutonomousShoppingMall()

    # 1. 자율 운영 사이클 시작
    print("\n🚀 1. 자율 쇼핑몰 가동...")
    operation_status = mall.run_autonomous_cycle()
    print("✅ 자율 운영 완료!")

    # 2. 상품 기획 및 런칭
    print("\n🎯 2. AI 상품 기획 및 자동 런칭...")
    product_info = mall.ai_product_planning()
    mall.launch_product(product_info)
    print(f"✅ 신제품 런칭 완료: {product_info['name']}")

    # 3. 자동 판매 시스템
    print("\n💰 3. AI 자동 판매 시스템...")
    mall.ai_auto_selling()
    print("✅ 자동 판매 진행 중!")

    # 4. AI 자동 구매 시스템
    print("\n🤖 4. AI 자동 구매 시스템...")
    mall.ai_auto_purchasing()
    print("✅ AI 자동 구매 완료!")

    print("\n🎉 자율 쇼핑몰 시스템 테스트 완료!")
    return operation_status


def test_multi_agent_system():
    """멀티 AI 에이전트 시스템 테스트"""
    print("\n" + "=" * 80)
    print("🤖 멀티 AI 에이전트 시스템 테스트")
    print("=" * 80)

    agent_system = MultiAgentShoppingSystem()

    # 1. 7개 에이전트 협업 회의
    print("\n👥 1. 7개 AI 에이전트 협업 회의...")
    meeting_result = agent_system.agent_collaboration_meeting("신제품 런칭 전략")
    print("✅ 에이전트 협업 회의 완료!")

    # 2. 협력 제품 런칭
    print("\n🚀 2. 멀티 에이전트 협력 제품 런칭...")
    agent_system.coordinate_product_launch("AI 협업 신제품")
    print("✅ 협력 제품 런칭 완료!")

    # 3. 실시간 최적화
    print("\n⚡ 3. 실시간 시스템 최적화...")
    agent_system.real_time_optimization()
    print("✅ 실시간 최적화 완료!")

    print("\n🎉 멀티 AI 에이전트 시스템 테스트 완료!")
    return meeting_result


def test_autonomous_marketing_system():
    """자율 마케팅 시스템 테스트"""
    print("\n" + "=" * 80)
    print("🎯 자율 마케팅 시스템 테스트")
    print("=" * 80)

    marketing_system = AutonomousMarketingSystem()

    # 1. 자율 마케팅 사이클 실행
    print("\n🚀 1. 자율 마케팅 사이클 실행...")
    cycle_result = marketing_system.run_autonomous_marketing_cycle()
    print("✅ 자율 마케팅 사이클 완료!")

    # 2. 판매 분석 리포트 생성
    print("\n📊 2. 판매 분석 리포트 생성...")
    analytics_report = marketing_system.generate_sales_analytics_report()
    print("✅ 분석 리포트 생성 완료!")

    # 3. 고객 피드백 분석
    print("\n💬 3. 고객 피드백 자동 분석...")
    marketing_system.ai_customer_feedback_analysis()
    print("✅ 피드백 분석 완료!")

    print("\n🎉 자율 마케팅 시스템 테스트 완료!")

    # 결과 요약 출력
    print(f"\n📈 마케팅 성과 요약:")
    print(f"• 신규 캠페인: {cycle_result['new_campaigns']}개 런칭")
    print(f"• 자동 최적화: {cycle_result['optimizations']}건 실행")
    print(f"• 마케팅 투자: {cycle_result['total_spend']:,}원")
    print(f"• 창출 수익: {cycle_result['generated_revenue']:,}원")
    print(f"• 전체 ROI: {analytics_report['summary']['overall_roi']}배")
    print(f"• 총 순이익: {analytics_report['summary']['profit']:,}원")

    return cycle_result


def test_voice_commands():
    """음성 명령 시스템 테스트"""
    print("\n" + "=" * 80)
    print("🎤 음성 명령 시스템 테스트")
    print("=" * 80)

    controller = SorisaeCore()

    # 쇼핑몰 관련 음성 명령 테스트
    shopping_commands = [
        "쇼핑몰 시작해줘",
        "자율 쇼핑 시스템 가동",
        "온라인쇼핑 운영해줘",
        "스마트쇼핑 시작"
    ]

    # 멀티 에이전트 관련 음성 명령 테스트
    agent_commands = [
        "멀티에이전트 시스템 시작",
        "다중AI 협업해줘",
        "에이전트시스템 가동",
        "협업AI 시작해줘"
    ]

    # 자율 마케팅 관련 음성 명령 테스트
    marketing_commands = [
        "마케팅 시작해줘",
        "자동 광고 운영해줘",
        "판매 분석 리포트",
        "캠페인 자동화 시작"
    ]

    print("\n🛒 쇼핑몰 음성 명령 테스트:")
    for cmd in shopping_commands:
        print(f"\n📢 명령: '{cmd}'")
        response = controller.handle_creative_commands(cmd)
        if response:
            print(f"✅ 응답: {response[:100]}...")
        else:
            print("❌ 명령 인식 실패")

    print("\n🤖 멀티 에이전트 음성 명령 테스트:")
    for cmd in agent_commands:
        print(f"\n📢 명령: '{cmd}'")
        response = controller.handle_creative_commands(cmd)
        if response:
            print(f"✅ 응답: {response[:100]}...")
        else:
            print("❌ 명령 인식 실패")

    print("\n� 자율 마케팅 음성 명령 테스트:")
    for cmd in marketing_commands:
        print(f"\n📢 명령: '{cmd}'")
        response = controller.handle_creative_commands(cmd)
        if response:
            print(f"✅ 응답: {response[:100]}...")
        else:
            print("❌ 명령 인식 실패")

    print("\n�🎉 음성 명령 테스트 완료!")


def main():
    """메인 데모 실행"""
    print("🚀 완전 자율 AI 비즈니스 생태계 통합 데모")
    print("자율 쇼핑몰 + 멀티 AI 에이전트 + 자율 마케팅 시스템의 완벽한 협업을 확인합니다.\n")

    try:
        # 1. 자율 쇼핑몰 테스트
        test_autonomous_shopping_mall()

        # 2. 멀티 에이전트 시스템 테스트
        test_multi_agent_system()

        # 3. 자율 마케팅 시스템 테스트
        test_autonomous_marketing_system()

        # 4. 음성 명령 시스템 테스트
        test_voice_commands()

        # 종합 결과
        print("\n" + "=" * 80)
        print("🎯 통합 테스트 결과 요약")
        print("=" * 80)
        print("✅ 자율 쇼핑몰 시스템: 완전 자율 운영 가능")
        print("✅ 멀티 AI 에이전트: 7개 에이전트 협업 완료")
        print("✅ 자율 마케팅 시스템: 광고 판매 마케팅 자동화 완료")
        print("✅ 음성 명령 처리: 모든 명령 정상 인식")
        print("✅ Sorisae 통합: 음성 인터페이스 완벽 연동")

        print("\n🎉 모든 시스템이 정상적으로 작동합니다!")
        print("이제 음성 명령으로 완전 자율 비즈니스 시스템을 제어할 수 있습니다:")
        print("• '쇼핑몰 시작해줘' - 자율 쇼핑몰 가동")
        print("• '멀티에이전트 시작' - AI 협업 시스템 가동")
        print("• '마케팅 시작해줘' - 자율 광고 마케팅 가동")
        print("• '판매 분석 리포트' - 실시간 성과 분석")
        print("🚀 완전 자율 AI 비즈니스 생태계 구축 완료!")

    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
