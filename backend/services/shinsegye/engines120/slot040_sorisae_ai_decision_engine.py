#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧠 소리새 AI 기반 자동 의사결정 엔진
Sorisae AI-Based Autonomous Decision Engine

복잡한 상황을 분석하고 최적의 의사결정을 내리는
지능형 자동 의사결정 시스템
"""

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List


@dataclass
class DecisionContext:
    """의사결정 컨텍스트"""
    situation_id: str
    situation_type: str
    description: str
    urgency_level: int  # 1-10 (10이 가장 긴급)
    available_options: List[str]
    constraints: Dict[str, Any]
    historical_data: List[Dict]
    environmental_factors: Dict[str, Any]
    timestamp: str


@dataclass
class DecisionResult:
    """의사결정 결과"""
    decision_id: str
    context: DecisionContext
    chosen_option: str
    confidence_score: float
    reasoning: List[str]
    expected_outcomes: Dict[str, float]
    risk_assessment: Dict[str, float]
    execution_plan: List[str]
    monitoring_points: List[str]
    timestamp: str


class SituationType(Enum):
    """상황 유형"""
    COMMUNICATION_FAILURE = "통신 장애"
    SECURITY_THREAT = "보안 위협"
    SYSTEM_OVERLOAD = "시스템 과부하"
    EMERGENCY_SITUATION = "비상 상황"
    PERFORMANCE_DEGRADATION = "성능 저하"
    RESOURCE_SHORTAGE = "자원 부족"
    USER_REQUEST = "사용자 요청"
    MAINTENANCE_REQUIRED = "유지보수 필요"
    OPTIMIZATION_OPPORTUNITY = "최적화 기회"
    UNKNOWN_ANOMALY = "알 수 없는 이상"


class DecisionEngine:
    """AI 의사결정 엔진"""

    def __init__(self):
        self.logger = logging.getLogger('DecisionEngine')

        # 의사결정 기록
        self.decision_history: List[DecisionResult] = []
        self.context_memory: Dict[str, Any] = {}
        self.learning_data: Dict[str, float] = {}

        # 의사결정 가중치 (학습을 통해 조정됨)
        self.decision_weights = {
            'urgency': 0.3,
            'success_probability': 0.25,
            'resource_efficiency': 0.2,
            'risk_minimization': 0.15,
            'user_satisfaction': 0.1
        }

        # 상황별 전략
        self.situation_strategies = {
            SituationType.COMMUNICATION_FAILURE: self._handle_communication_failure,
            SituationType.SECURITY_THREAT: self._handle_security_threat,
            SituationType.SYSTEM_OVERLOAD: self._handle_system_overload,
            SituationType.EMERGENCY_SITUATION: self._handle_emergency_situation,
            SituationType.PERFORMANCE_DEGRADATION: self._handle_performance_degradation,
            SituationType.RESOURCE_SHORTAGE: self._handle_resource_shortage,
            SituationType.USER_REQUEST: self._handle_user_request,
            SituationType.MAINTENANCE_REQUIRED: self._handle_maintenance_required,
            SituationType.OPTIMIZATION_OPPORTUNITY: self._handle_optimization_opportunity,
            SituationType.UNKNOWN_ANOMALY: self._handle_unknown_anomaly
        }

        # 성능 지표
        self.performance_metrics = {
            'total_decisions': 0,
            'successful_decisions': 0,
            'average_confidence': 0.0,
            'response_time': 0.0,
            'success_rate': 0.0
        }

        self.logger.info("AI 의사결정 엔진 초기화 완료")

    def make_decision(self, context: DecisionContext) -> DecisionResult:
        """주요 의사결정 함수"""
        start_time = time.time()

        self.logger.info(f"의사결정 시작: {context.situation_type} - {context.description}")

        try:
            # 상황 분석
            situation_analysis = self._analyze_situation(context)

            # 옵션 평가
            option_scores = self._evaluate_options(context, situation_analysis)

            # 최적 옵션 선택
            chosen_option = max(option_scores.keys(), key=lambda x: option_scores[x]['total_score'])

            # 의사결정 신뢰도 계산
            confidence = self._calculate_confidence(option_scores, chosen_option)

            # 추론 과정 생성
            reasoning = self._generate_reasoning(context, option_scores, chosen_option)

            # 예상 결과 및 위험 평가
            expected_outcomes = self._predict_outcomes(context, chosen_option)
            risk_assessment = self._assess_risks(context, chosen_option)

            # 실행 계획 생성
            execution_plan = self._create_execution_plan(context, chosen_option)

            # 모니터링 포인트 설정
            monitoring_points = self._set_monitoring_points(context, chosen_option)

            # 의사결정 결과 생성
            decision_result = DecisionResult(
                decision_id=f"DEC_{int(time.time())}_{random.randint(1000, 9999)}",
                context=context,
                chosen_option=chosen_option,
                confidence_score=confidence,
                reasoning=reasoning,
                expected_outcomes=expected_outcomes,
                risk_assessment=risk_assessment,
                execution_plan=execution_plan,
                monitoring_points=monitoring_points,
                timestamp=datetime.now().isoformat()
            )

            # 의사결정 기록
            self.decision_history.append(decision_result)
            if len(self.decision_history) > 1000:  # 메모리 관리
                self.decision_history.pop(0)

            # 성능 지표 업데이트
            self._update_performance_metrics(decision_result, time.time() - start_time)

            self.logger.info(f"의사결정 완료: {chosen_option} (신뢰도: {confidence:.2f})")

            return decision_result

        except Exception as e:
            self.logger.error(f"의사결정 중 오류: {e}")

            # 기본 안전 결정
            safe_option = context.available_options[0] if context.available_options else "상황 모니터링"

            return DecisionResult(
                decision_id=f"SAFE_{int(time.time())}",
                context=context,
                chosen_option=safe_option,
                confidence_score=0.5,
                reasoning=["오류로 인한 안전 모드 실행"],
                expected_outcomes={"안전성": 0.8},
                risk_assessment={"시스템_위험": 0.3},
                execution_plan=["안전 모드로 전환", "관리자 알림"],
                monitoring_points=["시스템 상태 확인"],
                timestamp=datetime.now().isoformat()
            )

    def _analyze_situation(self, context: DecisionContext) -> Dict[str, Any]:
        """상황 분석"""
        analysis = {
            'urgency_factor': context.urgency_level / 10.0,
            'complexity_score': len(context.available_options) / 10.0,
            'historical_success_rate': self._get_historical_success_rate(context.situation_type),
            'environmental_impact': self._assess_environmental_impact(context.environmental_factors),
            'resource_availability': self._check_resource_availability(context.constraints)
        }

        # 상황별 특수 분석
        if context.situation_type in [member.value for member in SituationType]:
            situation_enum = None
            for member in SituationType:
                if member.value == context.situation_type:
                    situation_enum = member
                    break

            if situation_enum and situation_enum in self.situation_strategies:
                specific_analysis = self.situation_strategies[situation_enum](context)
                analysis.update(specific_analysis)

        return analysis

    def _evaluate_options(self, context: DecisionContext, analysis: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """옵션 평가"""
        option_scores = {}

        for option in context.available_options:
            scores = {
                'urgency_response': self._score_urgency_response(option, context, analysis),
                'success_probability': self._score_success_probability(option, context, analysis),
                'resource_efficiency': self._score_resource_efficiency(option, context, analysis),
                'risk_level': self._score_risk_level(option, context, analysis),
                'user_satisfaction': self._score_user_satisfaction(option, context, analysis)
            }

            # 가중 평균 계산
            total_score = sum(
                scores[criterion] * self.decision_weights[criterion.replace('_response', '').replace('_level', '_minimization')]
                for criterion in scores.keys()
                if criterion.replace('_response', '').replace('_level', '_minimization') in self.decision_weights
            )

            scores['total_score'] = total_score
            option_scores[option] = scores

        return option_scores

    def _score_urgency_response(self, option: str, context: DecisionContext, analysis: Dict[str, Any]) -> float:
        """긴급도 대응 점수"""
        # 키워드 기반 긴급도 대응 평가
        urgent_keywords = ['즉시', '비상', '응급', '긴급', '자동']
        option_lower = option.lower()

        base_score = 0.5
        if any(keyword in option_lower for keyword in urgent_keywords):
            base_score += 0.3

        if context.urgency_level > 7:
            if '자동' in option_lower or '즉시' in option_lower:
                base_score += 0.2

        return min(base_score, 1.0)

    def _score_success_probability(self, option: str, context: DecisionContext, analysis: Dict[str, Any]) -> float:
        """성공 확률 점수"""
        # 과거 성공률 기반
        base_score = analysis.get('historical_success_rate', 0.5)

        # 옵션 복잡도 고려
        if len(option.split()) < 3:  # 간단한 옵션
            base_score += 0.1
        elif len(option.split()) > 5:  # 복잡한 옵션
            base_score -= 0.1

        # 시스템 상태 고려
        if analysis.get('resource_availability', 0) > 0.7:
            base_score += 0.1

        return max(0.1, min(base_score, 1.0))

    def _score_resource_efficiency(self, option: str, context: DecisionContext, analysis: Dict[str, Any]) -> float:
        """자원 효율성 점수"""
        # 자원 사용량 추정
        resource_keywords = ['최적화', '효율', '자동', '스마트']
        option_lower = option.lower()

        base_score = 0.5
        if any(keyword in option_lower for keyword in resource_keywords):
            base_score += 0.2

        # 자원 가용성 고려
        resource_availability = analysis.get('resource_availability', 0.5)
        base_score *= resource_availability

        return min(base_score, 1.0)

    def _score_risk_level(self, option: str, context: DecisionContext, analysis: Dict[str, Any]) -> float:
        """위험 수준 점수 (낮을수록 좋음, 점수는 높게)"""
        high_risk_keywords = ['강제', '삭제', '초기화', '재부팅']
        low_risk_keywords = ['모니터링', '확인', '알림', '분석']

        option_lower = option.lower()

        if any(keyword in option_lower for keyword in high_risk_keywords):
            return 0.3
        elif any(keyword in option_lower for keyword in low_risk_keywords):
            return 0.8
        else:
            return 0.6

    def _score_user_satisfaction(self, option: str, context: DecisionContext, analysis: Dict[str, Any]) -> float:
        """사용자 만족도 점수"""
        # 사용자 친화적 키워드
        user_friendly_keywords = ['자동', '스마트', '최적화', '개선']
        option_lower = option.lower()

        base_score = 0.5
        if any(keyword in option_lower for keyword in user_friendly_keywords):
            base_score += 0.2

        # 과거 사용자 피드백 고려 (시뮬레이션)
        feedback_score = random.uniform(0.4, 0.9)
        base_score = (base_score + feedback_score) / 2

        return min(base_score, 1.0)

    def _calculate_confidence(self, option_scores: Dict[str, Dict[str, float]], chosen_option: str) -> float:
        """의사결정 신뢰도 계산"""
        if not option_scores:
            return 0.5

        chosen_score = option_scores[chosen_option]['total_score']
        all_scores = [scores['total_score'] for scores in option_scores.values()]

        # 최고점과 차이
        score_gap = chosen_score - (sum(all_scores) - chosen_score) / (len(all_scores) - 1)

        # 정규화
        confidence = min(0.95, max(0.1, 0.5 + score_gap))

        return confidence

    def _generate_reasoning(self, context: DecisionContext,
                            option_scores: Dict[str, Dict[str, float]], chosen_option: str) -> List[str]:
        """추론 과정 생성"""
        reasoning = []

        # 상황 분석 결과
        reasoning.append(f"상황: {context.description} (긴급도: {context.urgency_level}/10)")

        # 선택된 옵션의 강점
        chosen_scores = option_scores[chosen_option]

        if chosen_scores['urgency_response'] > 0.7:
            reasoning.append("긴급 상황에 효과적으로 대응 가능")

        if chosen_scores['success_probability'] > 0.7:
            reasoning.append("높은 성공 확률을 보유")

        if chosen_scores['resource_efficiency'] > 0.7:
            reasoning.append("자원 효율성이 우수함")

        if chosen_scores['risk_level'] > 0.7:
            reasoning.append("위험도가 낮아 안전함")

        # 종합 평가
        reasoning.append(f"총 점수: {chosen_scores['total_score']:.2f}/1.0")

        return reasoning

    def _predict_outcomes(self, context: DecisionContext, chosen_option: str) -> Dict[str, float]:
        """예상 결과 예측"""
        outcomes = {}

        # 기본 결과 예측
        if '연결' in chosen_option:
            outcomes['연결_성공률'] = random.uniform(0.7, 0.95)
            outcomes['성능_개선'] = random.uniform(0.5, 0.8)

        if '보안' in chosen_option:
            outcomes['보안_강화'] = random.uniform(0.8, 0.95)
            outcomes['위협_차단'] = random.uniform(0.6, 0.9)

        if '최적화' in chosen_option:
            outcomes['성능_향상'] = random.uniform(0.6, 0.9)
            outcomes['자원_절약'] = random.uniform(0.5, 0.8)

        if '모니터링' in chosen_option:
            outcomes['상황_파악'] = random.uniform(0.8, 0.95)
            outcomes['예방_효과'] = random.uniform(0.4, 0.7)

        # 기본값 설정
        if not outcomes:
            outcomes['일반_효과'] = random.uniform(0.5, 0.8)

        return outcomes

    def _assess_risks(self, context: DecisionContext, chosen_option: str) -> Dict[str, float]:
        """위험 평가"""
        risks = {}

        # 기본 위험 평가
        if '강제' in chosen_option or '재부팅' in chosen_option:
            risks['시스템_중단'] = random.uniform(0.3, 0.7)
            risks['데이터_손실'] = random.uniform(0.1, 0.4)

        if '자동' in chosen_option:
            risks['예상외_동작'] = random.uniform(0.1, 0.3)

        if context.urgency_level > 8:
            risks['시간_부족'] = random.uniform(0.2, 0.5)

        # 기본 위험도
        if not risks:
            risks['일반_위험'] = random.uniform(0.1, 0.3)

        return risks

    def _create_execution_plan(self, context: DecisionContext, chosen_option: str) -> List[str]:
        """실행 계획 생성"""
        plan = []

        # 기본 실행 단계
        plan.append("1. 현재 시스템 상태 백업")

        if '연결' in chosen_option:
            plan.extend([
                "2. 네트워크 인터페이스 확인",
                "3. 최적 연결 지점 탐색",
                "4. 연결 시도 및 품질 확인"
            ])
        elif '보안' in chosen_option:
            plan.extend([
                "2. 보안 시스템 활성화",
                "3. 위협 탐지 및 분석",
                "4. 대응 조치 실행"
            ])
        elif '최적화' in chosen_option:
            plan.extend([
                "2. 성능 지표 수집",
                "3. 최적화 대상 식별",
                "4. 점진적 최적화 적용"
            ])
        else:
            plan.extend([
                "2. 선택된 옵션 실행",
                "3. 결과 모니터링"
            ])

        plan.append("5. 실행 결과 검증 및 보고")

        return plan

    def _set_monitoring_points(self, context: DecisionContext, chosen_option: str) -> List[str]:
        """모니터링 포인트 설정"""
        points = []

        # 기본 모니터링
        points.append("시스템 전반 상태")
        points.append("성능 지표 변화")

        if '연결' in chosen_option:
            points.extend([
                "네트워크 연결 상태",
                "데이터 전송 품질",
                "연결 안정성"
            ])

        if '보안' in chosen_option:
            points.extend([
                "보안 이벤트 로그",
                "위협 탐지 알림",
                "시스템 무결성"
            ])

        if context.urgency_level > 7:
            points.append("긴급 상황 진행도")

        return points

    # 상황별 처리 함수들

    def _handle_communication_failure(self, context: DecisionContext) -> Dict[str, Any]:
        """통신 장애 처리"""
        return {
            'failure_severity': context.urgency_level / 10.0,
            'backup_available': random.choice([True, False]),
            'recovery_time': random.uniform(1, 10)
        }

    def _handle_security_threat(self, context: DecisionContext) -> Dict[str, Any]:
        """보안 위협 처리"""
        return {
            'threat_level': context.urgency_level / 10.0,
            'attack_type': random.choice(['DDoS', 'Malware', 'Intrusion', 'Unknown']),
            'isolation_required': context.urgency_level > 7
        }

    def _handle_system_overload(self, context: DecisionContext) -> Dict[str, Any]:
        """시스템 과부하 처리"""
        return {
            'load_level': context.urgency_level / 10.0,
            'bottleneck_identified': random.choice([True, False]),
            'scaling_possible': random.choice([True, False])
        }

    def _handle_emergency_situation(self, context: DecisionContext) -> Dict[str, Any]:
        """비상 상황 처리"""
        return {
            'emergency_type': 'critical_system_failure',
            'backup_systems': random.choice([True, False]),
            'manual_intervention': context.urgency_level > 8
        }

    def _handle_performance_degradation(self, context: DecisionContext) -> Dict[str, Any]:
        """성능 저하 처리"""
        return {
            'degradation_level': context.urgency_level / 10.0,
            'optimization_potential': random.uniform(0.3, 0.8),
            'resource_constraint': random.choice([True, False])
        }

    def _handle_resource_shortage(self, context: DecisionContext) -> Dict[str, Any]:
        """자원 부족 처리"""
        return {
            'shortage_severity': context.urgency_level / 10.0,
            'alternative_resources': random.choice([True, False]),
            'procurement_time': random.uniform(1, 24)
        }

    def _handle_user_request(self, context: DecisionContext) -> Dict[str, Any]:
        """사용자 요청 처리"""
        return {
            'request_complexity': len(context.available_options) / 10.0,
            'user_priority': context.urgency_level / 10.0,
            'feasibility': random.uniform(0.5, 0.9)
        }

    def _handle_maintenance_required(self, context: DecisionContext) -> Dict[str, Any]:
        """유지보수 처리"""
        return {
            'maintenance_urgency': context.urgency_level / 10.0,
            'system_downtime': random.uniform(0.1, 2.0),
            'preventive': context.urgency_level < 5
        }

    def _handle_optimization_opportunity(self, context: DecisionContext) -> Dict[str, Any]:
        """최적화 기회 처리"""
        return {
            'optimization_potential': random.uniform(0.4, 0.9),
            'implementation_complexity': random.uniform(0.2, 0.8),
            'roi_estimate': random.uniform(0.5, 2.0)
        }

    def _handle_unknown_anomaly(self, context: DecisionContext) -> Dict[str, Any]:
        """알 수 없는 이상 처리"""
        return {
            'anomaly_severity': context.urgency_level / 10.0,
            'investigation_required': True,
            'safe_mode_recommended': context.urgency_level > 6
        }

    # 헬퍼 함수들

    def _get_historical_success_rate(self, situation_type: str) -> float:
        """과거 성공률 조회"""
        relevant_decisions = [
            d for d in self.decision_history
            if d.context.situation_type == situation_type
        ]

        if not relevant_decisions:
            return 0.7  # 기본값

        # 성공률 계산 (시뮬레이션)
        success_count = sum(1 for d in relevant_decisions if d.confidence_score > 0.6)
        return success_count / len(relevant_decisions)

    def _assess_environmental_impact(self, environmental_factors: Dict[str, Any]) -> float:
        """환경 영향 평가"""
        if not environmental_factors:
            return 0.5

        # 환경 요인들의 영향도 계산
        impact_score = 0.5

        for factor, value in environmental_factors.items():
            if isinstance(value, (int, float)):
                if factor in ['cpu_usage', 'memory_usage', 'network_load']:
                    if value > 0.8:
                        impact_score -= 0.1
                    elif value < 0.3:
                        impact_score += 0.1

        return max(0.0, min(1.0, impact_score))

    def _check_resource_availability(self, constraints: Dict[str, Any]) -> float:
        """자원 가용성 확인"""
        if not constraints:
            return 0.7

        availability = 0.7

        # 제약 조건 분석
        for constraint, value in constraints.items():
            if constraint == 'max_response_time' and isinstance(value, (int, float)):
                if value < 5:  # 5초 미만 요구
                    availability -= 0.1
            elif constraint == 'min_success_rate' and isinstance(value, (int, float)):
                if value > 0.9:  # 90% 이상 요구
                    availability -= 0.1

        return max(0.1, min(1.0, availability))

    def _update_performance_metrics(self, decision_result: DecisionResult, response_time: float):
        """성능 지표 업데이트"""
        self.performance_metrics['total_decisions'] += 1

        if decision_result.confidence_score > 0.6:
            self.performance_metrics['successful_decisions'] += 1

        # 평균 신뢰도 업데이트
        total = self.performance_metrics['total_decisions']
        current_avg = self.performance_metrics['average_confidence']
        new_confidence = decision_result.confidence_score
        self.performance_metrics['average_confidence'] = (current_avg * (total - 1) + new_confidence) / total

        # 응답 시간 업데이트
        current_response_time = self.performance_metrics['response_time']
        self.performance_metrics['response_time'] = (current_response_time * (total - 1) + response_time) / total

        # 성공률 계산
        self.performance_metrics['success_rate'] = (
            self.performance_metrics['successful_decisions'] / self.performance_metrics['total_decisions']
        )

    def get_performance_report(self) -> Dict[str, Any]:
        """성능 보고서 생성"""
        return {
            'metrics': self.performance_metrics.copy(),
            'recent_decisions': len([d for d in self.decision_history if
                                     datetime.fromisoformat(d.timestamp) > datetime.now() - timedelta(hours=24)]),
            'decision_types': self._get_decision_type_stats(),
            'learning_progress': self._assess_learning_progress()
        }

    def _get_decision_type_stats(self) -> Dict[str, int]:
        """의사결정 유형별 통계"""
        type_stats = {}
        for decision in self.decision_history:
            situation_type = decision.context.situation_type
            type_stats[situation_type] = type_stats.get(situation_type, 0) + 1
        return type_stats

    def _assess_learning_progress(self) -> Dict[str, float]:
        """학습 진행도 평가"""
        if len(self.decision_history) < 10:
            return {'learning_stage': 'initial', 'progress': 0.1}

        recent_confidence = [
            d.confidence_score for d in self.decision_history[-10:]
        ]
        early_confidence = [
            d.confidence_score for d in self.decision_history[:10]
        ]

        improvement = sum(recent_confidence) / len(recent_confidence) - sum(early_confidence) / len(early_confidence)

        return {
            'learning_stage': 'improving' if improvement > 0 else 'stabilizing',
            'progress': min(1.0, max(0.0, 0.5 + improvement))
        }

# 테스트 함수


def test_decision_engine():
    """의사결정 엔진 테스트"""
    engine = DecisionEngine()

    # 테스트 시나리오들
    test_scenarios = [
        {
            'situation_id': 'TEST_001',
            'situation_type': SituationType.COMMUNICATION_FAILURE.value,
            'description': '위성 통신 연결 불안정',
            'urgency_level': 8,
            'available_options': [
                '위성 재연결 시도',
                '백업 통신망 전환',
                '비상 모드 활성화',
                '상황 모니터링'
            ],
            'constraints': {'max_response_time': 30, 'min_success_rate': 0.8},
            'environmental_factors': {'network_load': 0.9, 'system_load': 0.7}
        },
        {
            'situation_id': 'TEST_002',
            'situation_type': SituationType.SECURITY_THREAT.value,
            'description': 'DDoS 공격 탐지',
            'urgency_level': 9,
            'available_options': [
                '트래픽 차단',
                '방화벽 강화',
                '비상 연락',
                'IP 블랙리스트 추가'
            ],
            'constraints': {'max_response_time': 10},
            'environmental_factors': {'threat_level': 0.9}
        },
        {
            'situation_id': 'TEST_003',
            'situation_type': SituationType.USER_REQUEST.value,
            'description': '사용자 음성 명령: 조명 제어',
            'urgency_level': 3,
            'available_options': [
                '거실 조명 켜기',
                '모든 조명 켜기',
                '조명 상태 확인',
                '사용자 확인 요청'
            ],
            'constraints': {'user_satisfaction': 0.9},
            'environmental_factors': {'time_of_day': 'evening'}
        }
    ]

    print("🧠 AI 의사결정 엔진 테스트")
    print("=" * 60)

    for scenario in test_scenarios:
        context = DecisionContext(
            situation_id=scenario['situation_id'],
            situation_type=scenario['situation_type'],
            description=scenario['description'],
            urgency_level=scenario['urgency_level'],
            available_options=scenario['available_options'],
            constraints=scenario['constraints'],
            historical_data=[],
            environmental_factors=scenario['environmental_factors'],
            timestamp=datetime.now().isoformat()
        )

        print(f"\n🔍 시나리오: {scenario['description']}")
        print(f"   긴급도: {scenario['urgency_level']}/10")
        print(f"   옵션들: {', '.join(scenario['available_options'])}")

        # 의사결정 실행
        result = engine.make_decision(context)

        print(f"✅ 결정: {result.chosen_option}")
        print(f"   신뢰도: {result.confidence_score:.2f}")
        print(f"   주요 이유: {result.reasoning[0] if result.reasoning else 'N/A'}")
        print(f"   예상 결과: {list(result.expected_outcomes.keys())}")
        print(f"   위험 요소: {list(result.risk_assessment.keys())}")

    # 성능 보고서
    print(f"\n📊 성능 보고서:")
    report = engine.get_performance_report()
    metrics = report['metrics']
    print(f"   총 의사결정: {metrics['total_decisions']}회")
    print(f"   성공률: {metrics['success_rate']:.1%}")
    print(f"   평균 신뢰도: {metrics['average_confidence']:.2f}")
    print(f"   평균 응답시간: {metrics['response_time']:.3f}초")

    print("\n✅ 테스트 완료")


def main(context: dict = None) -> dict:
    context = context or {}
    problem = str(context.get('problem', 'AI 기술 혁신 방향 결정'))
    engine = DecisionEngine()
    from datetime import datetime
    dc = DecisionContext(
        situation_id='main_dispatch',
        situation_type='general',
        description=problem,
        available_options=['혁신', '안정', '균형'],
        urgency_level=5,
        constraints={},
        historical_data=[],
        environmental_factors={},
        timestamp=datetime.now().isoformat()
    )
    result = engine.make_decision(dc)
    return {
        'status': 'ok',
        'problem': problem,
        'chosen_option': result.chosen_option,
        'confidence_score': result.confidence_score,
        'reasoning': result.reasoning[:2] if result.reasoning else [],
    }


if __name__ == "__main__":
    test_decision_engine()
