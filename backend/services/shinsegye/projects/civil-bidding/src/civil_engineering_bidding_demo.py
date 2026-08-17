#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏗️ 토목 입찰 시스템 데모
Civil Engineering Bidding System Demo

소리새 AI 토목 입찰 시스템의 주요 기능을 시연합니다.
"""

from sorisae_civil_engineering_bidding import CivilEngineeringBiddingSystem


def print_header():
    """헤더 출력"""
    print("🏗️" + "=" * 70 + "🏗️")
    print("🏗️" + " " * 15 + "소리새 지능형 토목 입찰 시스템 데모" + " " * 15 + "🏗️")
    print("🏗️" + " " * 10 + "Sorisae AI Civil Engineering Bidding Demo" + " " * 11 + "🏗️")
    print("🏗️" + "=" * 70 + "🏗️\n")


def demo_bridge_project():
    """교량 프로젝트 데모"""
    print("\n" + "=" * 72)
    print("📍 데모 1: 부산 해상 교량 건설 프로젝트")
    print("=" * 72)
    
    bidding_system = CivilEngineeringBiddingSystem()
    
    project = {
        "id": "DEMO_001",
        "type": "교량",
        "scale": 800,  # 800m
        "location": "부산",
        "deadline": "2027-06-30",
        "mountainous_terrain": False,
        "underwater": True,
        "urban_area": True,
        "environmental_protection_required": True,
        "heritage_site_nearby": False
    }
    
    print("\n📋 프로젝트 정보:")
    print(f"   • 프로젝트명: 부산 해상 교량")
    print(f"   • 유형: {project['type']}")
    print(f"   • 규모: {project['scale']}m")
    print(f"   • 위치: {project['location']}")
    print(f"   • 마감일: {project['deadline']}")
    print(f"   • 특이사항: 해상 교량, 환경 보호 지역")
    
    result = bidding_system.run_full_bidding_process(project)
    
    return result


def demo_subway_project():
    """지하철 프로젝트 데모"""
    print("\n" + "=" * 72)
    print("📍 데모 2: 서울 신규 지하철 노선 건설 프로젝트")
    print("=" * 72)
    
    bidding_system = CivilEngineeringBiddingSystem()
    
    project = {
        "id": "DEMO_002",
        "type": "지하철",
        "scale": 12,  # 12km
        "location": "서울",
        "deadline": "2029-12-31",
        "mountainous_terrain": False,
        "underwater": False,
        "urban_area": True,
        "environmental_protection_required": True,
        "heritage_site_nearby": True
    }
    
    print("\n📋 프로젝트 정보:")
    print(f"   • 프로젝트명: 서울 지하철 신규 노선")
    print(f"   • 유형: {project['type']}")
    print(f"   • 규모: {project['scale']}km")
    print(f"   • 위치: {project['location']}")
    print(f"   • 마감일: {project['deadline']}")
    print(f"   • 특이사항: 도심지, 문화재 보호구역 인접")
    
    result = bidding_system.run_full_bidding_process(project)
    
    return result


def demo_dam_project():
    """댐 프로젝트 데모"""
    print("\n" + "=" * 72)
    print("📍 데모 3: 강원도 다목적 댐 건설 프로젝트")
    print("=" * 72)
    
    bidding_system = CivilEngineeringBiddingSystem()
    
    project = {
        "id": "DEMO_003",
        "type": "댐",
        "scale": 1,
        "location": "강원",
        "deadline": "2030-12-31",
        "mountainous_terrain": True,
        "underwater": False,
        "urban_area": False,
        "environmental_protection_required": True,
        "heritage_site_nearby": False
    }
    
    print("\n📋 프로젝트 정보:")
    print(f"   • 프로젝트명: 강원도 다목적 댐")
    print(f"   • 유형: {project['type']}")
    print(f"   • 위치: {project['location']}")
    print(f"   • 마감일: {project['deadline']}")
    print(f"   • 특이사항: 산악 지형, 대규모 환경 영향 평가")
    
    result = bidding_system.run_full_bidding_process(project)
    
    return result


def demo_road_project():
    """도로 프로젝트 데모"""
    print("\n" + "=" * 72)
    print("📍 데모 4: 경기도 간선도로 확장 프로젝트")
    print("=" * 72)
    
    bidding_system = CivilEngineeringBiddingSystem()
    
    project = {
        "id": "DEMO_004",
        "type": "도로",
        "scale": 25,  # 25km
        "location": "경기",
        "deadline": "2026-12-31",
        "mountainous_terrain": False,
        "underwater": False,
        "urban_area": True,
        "environmental_protection_required": False,
        "heritage_site_nearby": False
    }
    
    print("\n📋 프로젝트 정보:")
    print(f"   • 프로젝트명: 경기 간선도로 확장")
    print(f"   • 유형: {project['type']}")
    print(f"   • 규모: {project['scale']}km")
    print(f"   • 위치: {project['location']}")
    print(f"   • 마감일: {project['deadline']}")
    print(f"   • 특이사항: 기존 도로 확장")
    
    result = bidding_system.run_full_bidding_process(project)
    
    return result


def show_comparison(results):
    """프로젝트 비교 분석"""
    print("\n" + "=" * 72)
    print("📊 전체 프로젝트 비교 분석")
    print("=" * 72)
    
    print("\n프로젝트별 요약:")
    print("-" * 72)
    print(f"{'프로젝트':<20} {'입찰가':>15} {'낙찰률':>10} {'이윤율':>10} {'결과':>10}")
    print("-" * 72)
    
    total_bid_amount = 0
    wins = 0
    
    for i, result in enumerate(results, 1):
        project_name = result['analysis']['project_type']
        bid_amount = result['bid']['bid_amount']
        bid_ratio = result['strategy']['bid_ratio']
        profit_margin = result['strategy']['profit_margin']
        bid_result = result['bid']['result']
        
        total_bid_amount += bid_amount
        if bid_result == "낙찰":
            wins += 1
        
        print(f"데모 {i} ({project_name:<10}) {bid_amount:>15,}원 {bid_ratio*100:>9.2f}% {profit_margin:>9.2f}% {bid_result:>10}")
    
    print("-" * 72)
    print(f"\n총 입찰액: {total_bid_amount:,}원")
    print(f"낙찰 건수: {wins}/{len(results)}")
    print(f"낙찰률: {(wins/len(results)*100):.1f}%")


def main():
    """메인 함수"""
    print_header()
    
    print("🎯 소리새 AI 토목 입찰 시스템의 주요 기능을 시연합니다.\n")
    print("이 데모에서는 다음 4가지 프로젝트에 대한 AI 입찰 프로세스를 보여줍니다:")
    print("  1️⃣  부산 해상 교량 건설")
    print("  2️⃣  서울 지하철 신규 노선")
    print("  3️⃣  강원도 다목적 댐")
    print("  4️⃣  경기도 간선도로 확장\n")
    
    input("시작하려면 Enter를 누르세요...")
    
    results = []
    
    # 데모 1: 교량
    result1 = demo_bridge_project()
    results.append(result1)
    input("\n다음 데모로 진행하려면 Enter를 누르세요...")
    
    # 데모 2: 지하철
    result2 = demo_subway_project()
    results.append(result2)
    input("\n다음 데모로 진행하려면 Enter를 누르세요...")
    
    # 데모 3: 댐
    result3 = demo_dam_project()
    results.append(result3)
    input("\n다음 데모로 진행하려면 Enter를 누르세요...")
    
    # 데모 4: 도로
    result4 = demo_road_project()
    results.append(result4)
    
    # 비교 분석
    show_comparison(results)
    
    print("\n" + "=" * 72)
    print("✅ 데모 완료!")
    print("=" * 72)
    print("\n💡 소리새 AI 토목 입찰 시스템의 주요 특징:")
    print("   • 5명의 전문 AI 에이전트가 협업하여 입찰 분석")
    print("   • 프로젝트 복잡도, 위험도, 경쟁 강도를 종합 분석")
    print("   • 최적 입찰가 자동 산정 (낙찰 확률 최대화)")
    print("   • 실시간 권장사항 및 전략 제시")
    print("   • 데이터 기반 의사결정 지원\n")
    
    print("🏗️ 전체 시스템을 사용하려면 다음 명령어를 실행하세요:")
    print("   python sorisae_civil_engineering_bidding.py\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 사용자가 데모를 종료했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
