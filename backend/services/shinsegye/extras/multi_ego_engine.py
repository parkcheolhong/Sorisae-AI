#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
소리새 다중 자아 엔진 (Sorisae Multi-Ego Engine)
AI의 다중 페르소나 관리 시스템
"""

import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Ego:
    """개별 자아 클래스"""
    name: str
    personality: str
    expertise: List[str]
    traits: Dict[str, float] = field(default_factory=dict)
    iot_preferences: Dict[str, Any] = field(default_factory=dict)

    def respond(self, query: str) -> Dict[str, Any]:
        """자아의 응답 생성"""
        return {
            'ego': self.name,
            'response': f"{self.name}의 관점: {query}에 대한 응답",
            'personality': self.personality,
            'confidence': random.uniform(0.7, 0.95)
        }


class MultiEgoEngine:
    """다중 자아 엔진 - 여러 AI 페르소나 관리"""

    def __init__(self):
        """다중 자아 엔진 초기화"""
        self.egos: Dict[str, Ego] = {}
        self._initialize_default_egos()
        print("🧠 다중 자아 엔진 초기화 완료!")

    def _initialize_default_egos(self):
        """기본 자아들 초기화"""
        # 크리에이터 자아
        self.egos["크리에이터"] = Ego(
            name="크리에이터",
            personality="창의적이고 혁신적",
            expertise=["창작", "아이디어", "디자인"],
            traits={
                "creativity": 0.95,
                "logic": 0.6,
                "empathy": 0.7
            }
        )

        # 로직 자아
        self.egos["로직"] = Ego(
            name="로직",
            personality="논리적이고 분석적",
            expertise=["분석", "프로그래밍", "수학"],
            traits={
                "creativity": 0.5,
                "logic": 0.98,
                "empathy": 0.4
            }
        )

        # 아티스트 자아
        self.egos["아티스트"] = Ego(
            name="아티스트",
            personality="예술적이고 감성적",
            expertise=["예술", "음악", "디자인"],
            traits={
                "creativity": 0.92,
                "logic": 0.5,
                "empathy": 0.88
            }
        )

        # 과학자 자아
        self.egos["과학자"] = Ego(
            name="과학자",
            personality="체계적이고 실험적",
            expertise=["연구", "실험", "분석"],
            traits={
                "creativity": 0.7,
                "logic": 0.95,
                "empathy": 0.5
            }
        )

        # 상담사 자아
        self.egos["상담사"] = Ego(
            name="상담사",
            personality="공감적이고 따뜻한",
            expertise=["상담", "심리", "소통"],
            traits={
                "creativity": 0.6,
                "logic": 0.7,
                "empathy": 0.98
            }
        )

    def get_ego_response(self, ego_name: str, query: str) -> Dict[str, Any]:
        """특정 자아의 응답 가져오기"""
        if ego_name in self.egos:
            return self.egos[ego_name].respond(query)
        else:
            return {
                'ego': 'unknown',
                'response': f"자아 '{ego_name}'를 찾을 수 없습니다.",
                'confidence': 0.0
            }

    def get_collaborative_response(self, query: str, ego_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """여러 자아의 협업 응답"""
        if ego_names is None:
            ego_names = list(self.egos.keys())

        responses = []
        for ego_name in ego_names:
            if ego_name in self.egos:
                responses.append(self.get_ego_response(ego_name, query))

        return {
            'query': query,
            'collaborative_responses': responses,
            'ego_count': len(responses),
            'timestamp': datetime.now().isoformat()
        }

    def add_ego(self, ego: Ego):
        """새 자아 추가"""
        self.egos[ego.name] = ego
        print(f"✅ 새 자아 '{ego.name}' 추가됨")

    def remove_ego(self, ego_name: str) -> bool:
        """자아 제거"""
        if ego_name in self.egos:
            del self.egos[ego_name]
            print(f"❌ 자아 '{ego_name}' 제거됨")
            return True
        return False

    def list_egos(self) -> List[str]:
        """등록된 모든 자아 목록"""
        return list(self.egos.keys())

    def get_ego_info(self, ego_name: str) -> Optional[Dict[str, Any]]:
        """자아 정보 조회"""
        if ego_name in self.egos:
            ego = self.egos[ego_name]
            return {
                'name': ego.name,
                'personality': ego.personality,
                'expertise': ego.expertise,
                'traits': ego.traits,
                'iot_preferences': ego.iot_preferences
            }
        return None


if __name__ == "__main__":
    # 테스트 코드
    engine = MultiEgoEngine()
    print("\n🧪 다중 자아 엔진 테스트")
    print(f"등록된 자아: {engine.list_egos()}")

    # 개별 자아 응답 테스트
    response = engine.get_ego_response("크리에이터", "새로운 앱 아이디어")
    print(f"\n크리에이터 응답: {response}")

    # 협업 응답 테스트
    collab = engine.get_collaborative_response("IoT 스마트홈 디자인", ["크리에이터", "로직", "아티스트"])
    print(f"\n협업 응답: {json.dumps(collab, ensure_ascii=False, indent=2)}")
