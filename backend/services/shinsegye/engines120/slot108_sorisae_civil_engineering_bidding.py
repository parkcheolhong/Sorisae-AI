#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏗️ 소리새 지능형 토목 입찰 시스템
Sorisae AI-Powered Civil Engineering Bidding System

AI가 스스로 토목 프로젝트를 분석하고, 입찰 전략을 수립하며,
최적의 입찰가를 산정하는 지능형 시스템
"""

import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class CivilEngineeringBiddingSystem:
    """토목 입찰 지능형 시스템"""

    def __init__(self):
        self.data_file = "data/civil_bidding_data.json"
        self.projects = []
        self.bids = []
        self.contracts = []
        self.competitors = []
        
        # AI 입찰 전문가 에이전트
        self.ai_bidding_agents = []
        
        # 시스템 통계
        self.system_stats = {
            "total_projects_analyzed": 0,
            "total_bids_submitted": 0,
            "win_rate": 0.0,
            "total_contract_value": 0,
            "average_profit_margin": 0.0,
            "success_score": 85.0
        }
        
        # 토목 프로젝트 유형
        self.project_types = {
            "도로": {"base_cost_per_km": 5000000000, "complexity": 1.2, "duration_months": 24},
            "교량": {"base_cost_per_m": 15000000, "complexity": 1.8, "duration_months": 36},
            "터널": {"base_cost_per_m": 25000000, "complexity": 2.5, "duration_months": 48},
            "댐": {"base_cost": 150000000000, "complexity": 3.0, "duration_months": 60},
            "항만": {"base_cost": 80000000000, "complexity": 2.2, "duration_months": 42},
            "공항": {"base_cost": 200000000000, "complexity": 2.8, "duration_months": 54},
            "지하철": {"base_cost_per_km": 100000000000, "complexity": 2.6, "duration_months": 60},
            "하수처리장": {"base_cost": 30000000000, "complexity": 1.5, "duration_months": 30},
            "상하수도": {"base_cost_per_km": 3000000000, "complexity": 1.4, "duration_months": 18},
            "매립지": {"base_cost": 50000000000, "complexity": 1.7, "duration_months": 36}
        }
        
        self.load_data()
        self.initialize_ai_agents()

    def load_data(self):
        """데이터 로드"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.projects = data.get("projects", [])
                    self.bids = data.get("bids", [])
                    self.contracts = data.get("contracts", [])
                    self.competitors = data.get("competitors", [])
                    self.system_stats = data.get("system_stats", self.system_stats)
            except Exception as e:
                print(f"데이터 로드 중 오류: {e}")

    def save_data(self):
        """데이터 저장"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        data = {
            "projects": self.projects,
            "bids": self.bids,
            "contracts": self.contracts,
            "competitors": self.competitors,
            "system_stats": self.system_stats,
            "last_updated": datetime.now().isoformat()
        }
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def initialize_ai_agents(self):
        """AI 입찰 전문가 에이전트 초기화"""
        self.ai_bidding_agents = [
            {
                "id": "agent_001",
                "name": "비용 분석 전문가",
                "specialty": "정확한 원가 산정",
                "personality": "신중한",
                "accuracy_rate": 92,
                "focus": "cost_estimation"
            },
            {
                "id": "agent_002",
                "name": "시장 동향 분석가",
                "specialty": "경쟁 입찰 분석",
                "personality": "분석적",
                "accuracy_rate": 88,
                "focus": "market_analysis"
            },
            {
                "id": "agent_003",
                "name": "전략 수립 전문가",
                "specialty": "입찰 전략 최적화",
                "personality": "전략적",
                "accuracy_rate": 90,
                "focus": "bidding_strategy"
            },
            {
                "id": "agent_004",
                "name": "리스크 관리자",
                "specialty": "위험 요소 평가",
                "personality": "보수적",
                "accuracy_rate": 85,
                "focus": "risk_assessment"
            },
            {
                "id": "agent_005",
                "name": "기술 평가 전문가",
                "specialty": "공법 및 기술 평가",
                "personality": "혁신적",
                "accuracy_rate": 87,
                "focus": "technical_evaluation"
            }
        ]

    def analyze_project(self, project_info: Dict) -> Dict:
        """프로젝트 종합 분석"""
        project_type = project_info.get("type", "도로")
        scale = project_info.get("scale", 10)  # km, m, 또는 기본 규모
        location = project_info.get("location", "서울")
        deadline = project_info.get("deadline", "2025-12-31")
        
        # 기본 비용 산정
        base_cost = self.calculate_base_cost(project_type, scale)
        
        # 지역별 보정 계수
        location_multiplier = self.get_location_multiplier(location)
        
        # 복잡도 분석
        complexity_score = self.analyze_complexity(project_info)
        
        # 예상 공사 기간
        estimated_duration = self.estimate_duration(project_type, scale, complexity_score)
        
        # 위험 요소 분석
        risk_analysis = self.assess_risks(project_info)
        
        # 경쟁사 분석
        competition_analysis = self.analyze_competition(project_info)
        
        analysis_result = {
            "project_id": project_info.get("id", f"PRJ_{len(self.projects) + 1:04d}"),
            "project_type": project_type,
            "scale": scale,
            "location": location,
            "base_cost": base_cost,
            "location_multiplier": location_multiplier,
            "adjusted_cost": int(base_cost * location_multiplier),
            "complexity_score": complexity_score,
            "estimated_duration_months": estimated_duration,
            "risk_analysis": risk_analysis,
            "competition_analysis": competition_analysis,
            "analyzed_at": datetime.now().isoformat(),
            "analyzed_by": [agent["name"] for agent in self.ai_bidding_agents]
        }
        
        return analysis_result

    def calculate_base_cost(self, project_type: str, scale: float) -> int:
        """기본 비용 산정"""
        type_info = self.project_types.get(project_type, {"base_cost": 10000000000})
        
        if "base_cost_per_km" in type_info:
            return int(type_info["base_cost_per_km"] * scale)
        elif "base_cost_per_m" in type_info:
            return int(type_info["base_cost_per_m"] * scale)
        else:
            return type_info.get("base_cost", 10000000000)

    def get_location_multiplier(self, location: str) -> float:
        """지역별 비용 보정 계수"""
        location_factors = {
            "서울": 1.3,
            "경기": 1.2,
            "인천": 1.25,
            "부산": 1.15,
            "대구": 1.1,
            "대전": 1.1,
            "광주": 1.1,
            "울산": 1.12,
            "세종": 1.15,
            "강원": 1.05,
            "충북": 1.0,
            "충남": 1.0,
            "전북": 0.95,
            "전남": 0.95,
            "경북": 0.98,
            "경남": 1.0,
            "제주": 1.4
        }
        
        return location_factors.get(location, 1.0)

    def analyze_complexity(self, project_info: Dict) -> float:
        """프로젝트 복잡도 분석"""
        project_type = project_info.get("type", "도로")
        base_complexity = self.project_types.get(project_type, {}).get("complexity", 1.0)
        
        # 추가 복잡도 요인
        additional_factors = 0
        
        if project_info.get("mountainous_terrain", False):
            additional_factors += 0.3
        
        if project_info.get("underwater", False):
            additional_factors += 0.5
        
        if project_info.get("urban_area", False):
            additional_factors += 0.2
        
        if project_info.get("environmental_protection_required", False):
            additional_factors += 0.25
        
        if project_info.get("heritage_site_nearby", False):
            additional_factors += 0.3
        
        return round(base_complexity + additional_factors, 2)

    def estimate_duration(self, project_type: str, scale: float, complexity: float) -> int:
        """공사 기간 예측"""
        base_duration = self.project_types.get(project_type, {}).get("duration_months", 24)
        
        # 규모에 따른 조정
        scale_factor = 1 + (scale - 10) / 20 if scale > 10 else 1 - (10 - scale) / 30
        
        # 복잡도에 따른 조정
        complexity_factor = complexity / 1.5
        
        estimated_months = int(base_duration * scale_factor * complexity_factor)
        
        return max(6, min(estimated_months, 120))  # 최소 6개월, 최대 120개월

    def assess_risks(self, project_info: Dict) -> Dict:
        """위험 요소 평가"""
        risks = {
            "technical_risk": 0,
            "financial_risk": 0,
            "environmental_risk": 0,
            "schedule_risk": 0,
            "regulatory_risk": 0,
            "overall_risk_level": "낮음"
        }
        
        # 기술적 위험
        complexity = project_info.get("complexity_score", 1.0)
        if complexity > 2.5:
            risks["technical_risk"] = 80
        elif complexity > 2.0:
            risks["technical_risk"] = 60
        elif complexity > 1.5:
            risks["technical_risk"] = 40
        else:
            risks["technical_risk"] = 20
        
        # 재정적 위험
        project_value = project_info.get("base_cost", 0)
        if project_value > 100000000000:  # 1000억 이상
            risks["financial_risk"] = 70
        elif project_value > 50000000000:  # 500억 이상
            risks["financial_risk"] = 50
        else:
            risks["financial_risk"] = 30
        
        # 환경적 위험
        if project_info.get("environmental_protection_required", False):
            risks["environmental_risk"] = 60
        else:
            risks["environmental_risk"] = 20
        
        # 일정 위험
        deadline_str = project_info.get("deadline", "")
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                days_until = (deadline - datetime.now()).days
                if days_until < 365:
                    risks["schedule_risk"] = 80
                elif days_until < 730:
                    risks["schedule_risk"] = 50
                else:
                    risks["schedule_risk"] = 30
            except:
                risks["schedule_risk"] = 40
        
        # 규제 위험
        if project_info.get("heritage_site_nearby", False):
            risks["regulatory_risk"] = 70
        elif project_info.get("urban_area", False):
            risks["regulatory_risk"] = 50
        else:
            risks["regulatory_risk"] = 25
        
        # 종합 위험 수준
        avg_risk = (risks["technical_risk"] + risks["financial_risk"] + 
                   risks["environmental_risk"] + risks["schedule_risk"] + 
                   risks["regulatory_risk"]) / 5
        
        if avg_risk > 70:
            risks["overall_risk_level"] = "높음"
        elif avg_risk > 50:
            risks["overall_risk_level"] = "중간"
        else:
            risks["overall_risk_level"] = "낮음"
        
        risks["average_risk_score"] = round(avg_risk, 1)
        
        return risks

    def analyze_competition(self, project_info: Dict) -> Dict:
        """경쟁사 분석"""
        # 시뮬레이션: 실제로는 과거 입찰 데이터 분석
        num_competitors = random.randint(3, 12)
        
        competition = {
            "estimated_competitors": num_competitors,
            "competition_level": "높음" if num_competitors > 8 else "중간" if num_competitors > 5 else "낮음",
            "average_bid_ratio": random.uniform(0.85, 0.98),  # 예정가 대비 낙찰률
            "top_competitors": [
                {"name": f"경쟁사 {i}", "win_rate": random.randint(15, 35)} 
                for i in range(1, min(4, num_competitors + 1))
            ]
        }
        
        return competition

    def generate_bidding_strategy(self, analysis_result: Dict) -> Dict:
        """입찰 전략 수립"""
        base_cost = analysis_result["adjusted_cost"]
        complexity = analysis_result["complexity_score"]
        risk_level = analysis_result["risk_analysis"]["average_risk_score"]
        competition = analysis_result["competition_analysis"]["competition_level"]
        
        # 기본 이윤율 설정 (5-20%)
        base_profit_margin = 0.12
        
        # 복잡도에 따른 이윤율 조정
        complexity_adjustment = (complexity - 1.5) * 0.02
        
        # 위험도에 따른 이윤율 조정
        risk_adjustment = risk_level / 500  # 0-0.16 범위
        
        # 경쟁 강도에 따른 조정
        competition_adjustment = 0
        if competition == "높음":
            competition_adjustment = -0.03
        elif competition == "중간":
            competition_adjustment = -0.01
        
        # 최종 이윤율
        profit_margin = base_profit_margin + complexity_adjustment + risk_adjustment + competition_adjustment
        profit_margin = max(0.05, min(profit_margin, 0.25))  # 5-25% 범위
        
        # 입찰가 산정
        bid_amount = int(base_cost * (1 + profit_margin))
        
        # 예정가 대비 비율 (일반적으로 85-99%)
        estimated_price = int(base_cost * 1.15)  # 예정가는 원가의 115% 정도로 가정
        bid_ratio = bid_amount / estimated_price
        
        strategy = {
            "recommended_bid_amount": bid_amount,
            "estimated_price": estimated_price,
            "bid_ratio": round(bid_ratio, 4),
            "profit_margin": round(profit_margin * 100, 2),
            "strategy_type": self.determine_strategy_type(bid_ratio, competition),
            "confidence_level": self.calculate_confidence(analysis_result),
            "key_factors": self.identify_key_factors(analysis_result),
            "recommendations": self.generate_recommendations(analysis_result, profit_margin),
            "created_at": datetime.now().isoformat()
        }
        
        return strategy

    def determine_strategy_type(self, bid_ratio: float, competition: str) -> str:
        """입찰 전략 유형 결정"""
        if bid_ratio < 0.88:
            return "공격적 입찰" if competition == "높음" else "초저가 입찰"
        elif bid_ratio < 0.93:
            return "표준 입찰"
        else:
            return "안정적 입찰"

    def calculate_confidence(self, analysis_result: Dict) -> float:
        """입찰 신뢰도 계산"""
        risk_score = analysis_result["risk_analysis"]["average_risk_score"]
        complexity = analysis_result["complexity_score"]
        
        # 기본 신뢰도 90%
        confidence = 90.0
        
        # 위험도에 따른 감소
        confidence -= risk_score / 10
        
        # 복잡도에 따른 감소
        confidence -= (complexity - 1.0) * 5
        
        return max(50.0, min(confidence, 95.0))

    def identify_key_factors(self, analysis_result: Dict) -> List[str]:
        """주요 고려 요인 식별"""
        factors = []
        
        if analysis_result["complexity_score"] > 2.0:
            factors.append("높은 기술적 복잡도")
        
        if analysis_result["risk_analysis"]["average_risk_score"] > 60:
            factors.append("높은 위험 수준")
        
        if analysis_result["competition_analysis"]["competition_level"] == "높음":
            factors.append("치열한 경쟁")
        
        if analysis_result["location_multiplier"] > 1.2:
            factors.append("높은 지역 비용")
        
        if analysis_result["estimated_duration_months"] > 48:
            factors.append("장기 프로젝트")
        
        return factors

    def generate_recommendations(self, analysis_result: Dict, profit_margin: float) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        if profit_margin < 0.08:
            recommendations.append("⚠️ 낮은 이윤율 - 원가 재검토 권장")
        
        if analysis_result["risk_analysis"]["overall_risk_level"] == "높음":
            recommendations.append("🔴 고위험 프로젝트 - 리스크 관리 계획 필수")
        
        if analysis_result["complexity_score"] > 2.5:
            recommendations.append("🔧 기술 검토 필수 - 전문 기술팀 구성 권장")
        
        if analysis_result["estimated_duration_months"] > 60:
            recommendations.append("⏱️ 장기 프로젝트 - 단계별 마일스톤 설정 권장")
        
        if analysis_result["competition_analysis"]["competition_level"] == "높음":
            recommendations.append("💡 경쟁 우위 확보 전략 필요 - 차별화 포인트 강화")
        
        return recommendations

    def submit_bid(self, project_id: str, bid_amount: int, strategy: Dict) -> Dict:
        """입찰 제출"""
        bid = {
            "bid_id": f"BID_{len(self.bids) + 1:05d}",
            "project_id": project_id,
            "bid_amount": bid_amount,
            "strategy": strategy,
            "submitted_at": datetime.now().isoformat(),
            "status": "제출됨",
            "result": None  # 낙찰/탈락 결과
        }
        
        self.bids.append(bid)
        self.system_stats["total_bids_submitted"] += 1
        
        # 낙찰 여부 시뮬레이션 (실제로는 발주처 결과 대기)
        win_probability = strategy.get("confidence_level", 70) / 100
        if random.random() < win_probability:
            bid["result"] = "낙찰"
            bid["status"] = "낙찰"
            self.system_stats["total_contract_value"] += bid_amount
            
            # 계약 생성
            contract = {
                "contract_id": f"CNT_{len(self.contracts) + 1:05d}",
                "bid_id": bid["bid_id"],
                "project_id": project_id,
                "contract_amount": bid_amount,
                "signed_at": datetime.now().isoformat(),
                "status": "진행중"
            }
            self.contracts.append(contract)
        else:
            bid["result"] = "탈락"
            bid["status"] = "탈락"
        
        # 낙찰률 업데이트
        total_completed = len([b for b in self.bids if b.get("result")])
        if total_completed > 0:
            wins = len([b for b in self.bids if b.get("result") == "낙찰"])
            self.system_stats["win_rate"] = round((wins / total_completed) * 100, 2)
        
        self.save_data()
        
        return bid

    def get_system_statistics(self) -> Dict:
        """시스템 통계 조회"""
        return {
            "총_분석_프로젝트": len(self.projects),
            "총_제출_입찰": self.system_stats["total_bids_submitted"],
            "낙찰률": f"{self.system_stats['win_rate']}%",
            "총_계약액": f"{self.system_stats['total_contract_value']:,}원",
            "진행중_계약": len([c for c in self.contracts if c.get("status") == "진행중"]),
            "완료_계약": len([c for c in self.contracts if c.get("status") == "완료"]),
            "AI_에이전트_수": len(self.ai_bidding_agents),
            "시스템_성공_점수": self.system_stats["success_score"]
        }

    def run_full_bidding_process(self, project_info: Dict) -> Dict:
        """전체 입찰 프로세스 실행"""
        print("🏗️ 토목 입찰 프로세스 시작")
        print("=" * 60)
        
        # 1. 프로젝트 분석
        print("\n📊 1단계: 프로젝트 종합 분석 중...")
        analysis = self.analyze_project(project_info)
        self.projects.append(analysis)
        self.system_stats["total_projects_analyzed"] += 1
        
        print(f"   프로젝트 유형: {analysis['project_type']}")
        print(f"   규모: {analysis['scale']} (km/m)")
        print(f"   예상 비용: {analysis['adjusted_cost']:,}원")
        print(f"   복잡도: {analysis['complexity_score']}")
        print(f"   위험 수준: {analysis['risk_analysis']['overall_risk_level']}")
        
        # 2. 입찰 전략 수립
        print("\n🎯 2단계: AI 입찰 전략 수립 중...")
        strategy = self.generate_bidding_strategy(analysis)
        
        print(f"   권장 입찰가: {strategy['recommended_bid_amount']:,}원")
        print(f"   예상 낙찰률: {strategy['bid_ratio'] * 100:.2f}%")
        print(f"   이윤율: {strategy['profit_margin']}%")
        print(f"   전략 유형: {strategy['strategy_type']}")
        print(f"   신뢰도: {strategy['confidence_level']:.1f}%")
        
        if strategy['recommendations']:
            print(f"\n   📌 권장사항:")
            for rec in strategy['recommendations']:
                print(f"      {rec}")
        
        # 3. 입찰 제출
        print("\n✅ 3단계: 입찰 제출...")
        bid = self.submit_bid(
            analysis['project_id'],
            strategy['recommended_bid_amount'],
            strategy
        )
        
        print(f"   입찰 ID: {bid['bid_id']}")
        print(f"   제출 시간: {bid['submitted_at']}")
        print(f"   결과: {bid['result']}")
        
        print("\n" + "=" * 60)
        print("🏗️ 입찰 프로세스 완료\n")
        
        result = {
            "analysis": analysis,
            "strategy": strategy,
            "bid": bid
        }
        
        return result


def main():
    """메인 함수: 토목 입찰 시스템 데모"""
    print("🏗️" + "=" * 58 + "🏗️")
    print("🏗️ 소리새 지능형 토목 입찰 시스템")
    print("🏗️ Sorisae AI Civil Engineering Bidding System")
    print("🏗️" + "=" * 58 + "🏗️\n")
    
    # 시스템 초기화
    bidding_system = CivilEngineeringBiddingSystem()
    
    while True:
        print("\n📋 메뉴:")
        print("1. 🏗️  새 프로젝트 입찰")
        print("2. 📊 시스템 통계 보기")
        print("3. 📜 입찰 이력 조회")
        print("4. 🎯 데모 프로젝트 실행")
        print("5. 🚪 종료")
        
        choice = input("\n선택 (1-5): ").strip()
        
        if choice == "1":
            print("\n🏗️ 새 프로젝트 입찰")
            print("-" * 60)
            
            project_type = input("프로젝트 유형 (도로/교량/터널/댐/항만/공항/지하철/하수처리장/상하수도/매립지): ").strip() or "도로"
            scale = float(input("규모 (km/m/기본값 10): ").strip() or "10")
            location = input("위치 (서울/경기/부산 등): ").strip() or "서울"
            
            project_info = {
                "type": project_type,
                "scale": scale,
                "location": location,
                "deadline": "2026-12-31",
                "mountainous_terrain": False,
                "urban_area": True,
                "environmental_protection_required": False
            }
            
            result = bidding_system.run_full_bidding_process(project_info)
            
        elif choice == "2":
            print("\n📊 시스템 통계")
            print("-" * 60)
            stats = bidding_system.get_system_statistics()
            for key, value in stats.items():
                print(f"   {key}: {value}")
            
        elif choice == "3":
            print("\n📜 입찰 이력")
            print("-" * 60)
            if bidding_system.bids:
                for bid in bidding_system.bids[-5:]:  # 최근 5개
                    print(f"   [{bid['bid_id']}] {bid['bid_amount']:,}원 - {bid['result']}")
            else:
                print("   입찰 이력이 없습니다.")
            
        elif choice == "4":
            print("\n🎯 데모 프로젝트 실행")
            print("-" * 60)
            
            demo_projects = [
                {
                    "type": "교량",
                    "scale": 500,
                    "location": "부산",
                    "deadline": "2026-06-30",
                    "mountainous_terrain": False,
                    "underwater": True,
                    "urban_area": True
                },
                {
                    "type": "지하철",
                    "scale": 15,
                    "location": "서울",
                    "deadline": "2028-12-31",
                    "urban_area": True,
                    "environmental_protection_required": True,
                    "heritage_site_nearby": True
                },
                {
                    "type": "댐",
                    "scale": 1,
                    "location": "강원",
                    "deadline": "2029-12-31",
                    "mountainous_terrain": True,
                    "environmental_protection_required": True
                }
            ]
            
            for i, project in enumerate(demo_projects, 1):
                print(f"\n{'='*60}")
                print(f"데모 프로젝트 {i}/{len(demo_projects)}")
                bidding_system.run_full_bidding_process(project)
                if i < len(demo_projects):
                    input("\n다음 프로젝트로 진행하려면 Enter를 누르세요...")
            
        elif choice == "5":
            print("\n👋 토목 입찰 시스템을 종료합니다.")
            break
        
        else:
            print("❌ 잘못된 선택입니다. 1-5 중에서 선택해주세요.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 사용자가 프로그램을 종료했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
