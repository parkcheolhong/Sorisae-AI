#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
창의적 워크플로우 엔진
소리새의 창의적 작업 프로세스를 관리하고 최적화하는 엔진입니다.
"""

import json
import random
from datetime import datetime
from typing import Any, Dict


class CreativeWorkflowEngine:
    def __init__(self):
        self.workflow_templates = {
            'music_creation': {
                'steps': ['장르선택', '멜로디생성', '화성진행', '리듬패턴', '편곡', '믹싱'],
                'creativity_factors': ['emotion', 'style', 'tempo', 'key_signature']
            },
            'story_writing': {
                'steps': ['주제설정', '캐릭터개발', '플롯구성', '대화작성', '묘사추가', '편집'],
                'creativity_factors': ['genre', 'mood', 'perspective', 'conflict']
            },
            'code_development': {
                'steps': ['요구사항분석', '설계', '구현', '테스트', '리팩토링', '문서화'],
                'creativity_factors': ['architecture', 'patterns', 'optimization', 'user_experience']
            }
        }

        self.active_workflows = []
        self.creativity_boost_techniques = [
            'random_inspiration',
            'cross_domain_mixing',
            'constraint_based_creation',
            'iterative_refinement',
            'collaborative_filtering'
        ]

    def create_workflow(self, workflow_type: str, project_name: str) -> Dict[str, Any]:
        """새로운 창의적 워크플로우 생성"""
        if workflow_type not in self.workflow_templates:
            raise ValueError(f"지원하지 않는 워크플로우 타입: {workflow_type}")

        template = self.workflow_templates[workflow_type]

        workflow = {
            'id': len(self.active_workflows) + 1,
            'type': workflow_type,
            'project_name': project_name,
            'steps': template['steps'].copy(),
            'current_step': 0,
            'completed_steps': [],
            'creativity_factors': template['creativity_factors'].copy(),
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            'progress': 0.0,
            'creative_insights': []
        }

        self.active_workflows.append(workflow)
        return workflow

    def advance_workflow_step(self, workflow_id: int) -> Dict[str, Any]:
        """워크플로우의 다음 단계로 진행"""
        workflow = self.get_workflow_by_id(workflow_id)
        if not workflow:
            raise ValueError(f"워크플로우를 찾을 수 없습니다: {workflow_id}")

        if workflow['current_step'] < len(workflow['steps']):
            # 현재 단계 완료 처리
            current_step_name = workflow['steps'][workflow['current_step']]
            workflow['completed_steps'].append(current_step_name)

            # 창의적 인사이트 생성
            insight = self.generate_creative_insight(workflow)
            workflow['creative_insights'].append(insight)

            # 다음 단계로 진행
            workflow['current_step'] += 1
            workflow['progress'] = (workflow['current_step'] / len(workflow['steps'])) * 100

            # 워크플로우 완료 체크
            if workflow['current_step'] >= len(workflow['steps']):
                workflow['status'] = 'completed'
                workflow['completed_at'] = datetime.now().isoformat()

        return workflow

    def generate_creative_insight(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """창의적 인사이트 생성"""
        current_step = workflow['steps'][workflow['current_step']]
        creativity_technique = random.choice(self.creativity_boost_techniques)

        insights = {
            'random_inspiration': f"{current_step} 단계에서 예상치 못한 아이디어를 탐험해보세요",
            'cross_domain_mixing': f"다른 분야의 {current_step} 접근법을 혼합해보세요",
            'constraint_based_creation': f"{current_step}에 제약을 두어 더 창의적인 해결책을 찾아보세요",
            'iterative_refinement': f"{current_step}를 여러 번 반복하며 점진적으로 개선해보세요",
            'collaborative_filtering': f"다른 사람의 {current_step} 경험을 참고해보세요"
        }

        return {
            'step': current_step,
            'technique': creativity_technique,
            'suggestion': insights[creativity_technique],
            'timestamp': datetime.now().isoformat()
        }

    def get_workflow_by_id(self, workflow_id: int) -> Dict[str, Any]:
        """ID로 워크플로우 조회"""
        for workflow in self.active_workflows:
            if workflow['id'] == workflow_id:
                return workflow
        return None

    def get_workflow_status(self, workflow_id: int) -> Dict[str, Any]:
        """워크플로우 상태 조회"""
        workflow = self.get_workflow_by_id(workflow_id)
        if not workflow:
            return {'error': '워크플로우를 찾을 수 없습니다'}

        status_report = {
            'id': workflow['id'],
            'project_name': workflow['project_name'],
            'type': workflow['type'],
            'status': workflow['status'],
            'progress': f"{workflow['progress']:.1f}%",
            'current_step': workflow['steps'][workflow['current_step']] if workflow['current_step'] < len(workflow['steps']) else 'Completed',
            'completed_steps': len(workflow['completed_steps']),
            'total_steps': len(workflow['steps']),
            'creative_insights_count': len(workflow['creative_insights'])
        }

        return status_report

    def boost_creativity(self, workflow_id: int) -> Dict[str, Any]:
        """창의성 부스터 적용"""
        workflow = self.get_workflow_by_id(workflow_id)
        if not workflow:
            return {'error': '워크플로우를 찾을 수 없습니다'}

        # 랜덤 창의성 부스터 선택
        boost_technique = random.choice(self.creativity_boost_techniques)

        # 현재 단계에 맞는 창의성 부스터 적용
        creativity_boost = self.generate_creative_insight(workflow)
        workflow['creative_insights'].append(creativity_boost)

        return {
            'workflow_id': workflow_id,
            'boost_applied': boost_technique,
            'new_insight': creativity_boost,
            'total_insights': len(workflow['creative_insights'])
        }


def main():
    """메인 실행 함수"""
    print("🎨 소리새 창의적 워크플로우 엔진")
    print("================================")

    engine = CreativeWorkflowEngine()

    # 데모 워크플로우 생성
    music_workflow = engine.create_workflow('music_creation', '감성 발라드 프로젝트')
    print(f"✅ 음악 창작 워크플로우 생성: {music_workflow['project_name']}")

    # 몇 단계 진행
    for i in range(3):
        engine.advance_workflow_step(music_workflow['id'])
        status = engine.get_workflow_status(music_workflow['id'])
        print(f"📋 진행 상황: {status['current_step']} ({status['progress']})")

    # 창의성 부스터 적용
    boost_result = engine.boost_creativity(music_workflow['id'])
    print(f"💡 창의성 부스터 적용: {boost_result['boost_applied']}")

    # 최종 상태 출력
    final_status = engine.get_workflow_status(music_workflow['id'])
    print("\n📊 최종 워크플로우 상태:")
    print(json.dumps(final_status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
